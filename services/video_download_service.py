"""
视频下载服务层
处理视频下载和存储相关的业务逻辑
"""

import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from urllib.parse import urlparse
import hashlib
import json

from utils.db_utils import _get_db_connection
from config.base_config import *

logger = logging.getLogger(__name__)

class VideoDownloadService:
    """视频下载服务层"""
    
    def __init__(self):
        self.download_dir = "downloads"
        self.temp_dir = "temp"
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保下载目录存在"""
        for directory in [self.download_dir, self.temp_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    async def download_video(self, video_url: str, video_id: str, platform: str, 
                           download_type: str = "local") -> Dict[str, Any]:
        """
        下载视频
        
        Args:
            video_url: 视频URL
            video_id: 视频ID
            platform: 平台标识
            download_type: 下载类型 (local/server)
        
        Returns:
            下载结果字典
        """
        try:
            # 创建下载任务记录
            task_id = await self._create_download_task(video_id, platform, video_url, download_type)
            
            # 开始下载
            await self._update_task_status(task_id, "downloading")
            
            # 获取视频信息
            video_info = await self._get_video_info(video_url)
            file_size = video_info.get('content_length', 0)
            
            # 决定存储方式
            if file_size > self.max_file_size:
                # 大文件存储到MinIO
                result = await self._download_to_minio(video_url, video_id, platform, task_id)
            else:
                # 小文件存储到本地
                result = await self._download_to_local(video_url, video_id, platform, task_id)
            
            # 更新任务状态
            if result['success']:
                await self._update_task_status(task_id, "completed", result)
                # 创建文件记录
                await self._create_file_record(task_id, result)
            else:
                await self._update_task_status(task_id, "failed", result)
            
            return {
                'success': result['success'],
                'task_id': task_id,
                'file_path': result.get('file_path'),
                'file_url': result.get('file_url'),
                'file_size': result.get('file_size'),
                'storage_type': result.get('storage_type'),
                'message': result.get('message')
            }
            
        except Exception as e:
            logger.error(f"下载视频失败 {video_id}: {str(e)}")
            return {
                'success': False,
                'message': f"下载失败: {str(e)}"
            }
    
    async def _create_download_task(self, video_id: str, platform: str, 
                                  video_url: str, download_type: str) -> str:
        """创建下载任务记录"""
        try:
            task_id = f"{platform}_{video_id}_{int(datetime.now().timestamp())}"
            
            db = await _get_db_connection()
            
            query = """
                INSERT INTO video_download_tasks 
                (task_id, video_id, platform, video_url, download_type, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            await db.execute(query, task_id, video_id, platform, video_url, 
                           download_type, "created", datetime.now())
            
            return task_id
                
        except Exception as e:
            logger.error(f"创建下载任务失败: {str(e)}")
            return f"temp_{video_id}_{int(datetime.now().timestamp())}"
    
    async def _update_task_status(self, task_id: str, status: str, result: Dict[str, Any] = None):
        """更新任务状态"""
        try:
            db = await _get_db_connection()
            
            if result:
                query = """
                    UPDATE video_download_tasks 
                    SET status = %s, result = %s, updated_at = %s
                    WHERE task_id = %s
                """
                await db.execute(query, status, json.dumps(result, ensure_ascii=False), 
                               datetime.now(), task_id)
            else:
                query = """
                    UPDATE video_download_tasks 
                    SET status = %s, updated_at = %s
                    WHERE task_id = %s
                """
                await db.execute(query, status, datetime.now(), task_id)
                
        except Exception as e:
            logger.error(f"更新任务状态失败 {task_id}: {str(e)}")
    
    async def _get_video_info(self, video_url: str) -> Dict[str, Any]:
        """获取视频信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(video_url) as response:
                    return {
                        'content_length': int(response.headers.get('content-length', 0)),
                        'content_type': response.headers.get('content-type', ''),
                        'filename': self._extract_filename(video_url, response.headers)
                    }
        except Exception as e:
            logger.error(f"获取视频信息失败 {video_url}: {str(e)}")
            return {
                'content_length': 0,
                'content_type': 'video/mp4',
                'filename': 'unknown.mp4'
            }
    
    def _extract_filename(self, url: str, headers: Dict[str, str]) -> str:
        """提取文件名"""
        # 从headers获取filename
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
            return filename
        
        # 从URL提取
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if filename and '.' in filename:
            return filename
        
        # 默认文件名
        return f"video_{int(datetime.now().timestamp())}.mp4"
    
    async def _download_to_local(self, video_url: str, video_id: str, 
                               platform: str, task_id: str) -> Dict[str, Any]:
        """下载到本地存储"""
        try:
            # 生成文件名
            filename = f"{platform}_{video_id}_{int(datetime.now().timestamp())}.mp4"
            file_path = os.path.join(self.download_dir, filename)
            
            # 下载文件
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)
                        
                        return {
                            'success': True,
                            'file_path': file_path,
                            'file_url': f"/downloads/{filename}",
                            'file_size': file_size,
                            'storage_type': 'local',
                            'message': '下载成功'
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'下载失败: HTTP {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"本地下载失败 {video_id}: {str(e)}")
            return {
                'success': False,
                'message': f'本地下载失败: {str(e)}'
            }
    
    async def _download_to_minio(self, video_url: str, video_id: str, 
                               platform: str, task_id: str) -> Dict[str, Any]:
        """下载到MinIO存储"""
        try:
            # 导入MinIO服务
            from services.minio_service import MinIOService
            
            minio_service = MinIOService()
            
            if not minio_service.is_available():
                return {
                    'success': False,
                    'message': 'MinIO服务不可用，请检查配置'
                }
            
            # 生成对象名称
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            object_name = f"videos/{platform}/{video_id}_{timestamp}.mp4"
            
            # 准备元数据
            metadata = {
                'platform': platform,
                'video_id': video_id,
                'task_id': task_id,
                'upload_time': datetime.now().isoformat()
            }
            
            # 从URL上传到MinIO
            result = await minio_service.upload_from_url(
                url=video_url,
                object_name=object_name,
                metadata=metadata
            )
            
            if result['success']:
                return {
                    'success': True,
                    'file_path': result['file_url'],
                    'file_url': result['public_url'],
                    'file_size': result['file_size'],
                    'storage_type': 'minio',
                    'object_name': result['object_name'],
                    'bucket_name': result['bucket_name'],
                    'etag': result['etag'],
                    'message': '上传到MinIO成功'
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"MinIO下载失败 {video_id}: {str(e)}")
            return {
                'success': False,
                'message': f'MinIO下载失败: {str(e)}'
            }
    
    async def _create_file_record(self, task_id: str, result: Dict[str, Any]):
        """创建文件记录"""
        try:
            db = await _get_db_connection()
            
            query = """
                INSERT INTO video_files 
                (task_id, file_path, file_url, file_size, storage_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            await db.execute(query, task_id, result.get('file_path'), 
                           result.get('file_url'), result.get('file_size'),
                           result.get('storage_type'), datetime.now())
                
        except Exception as e:
            logger.error(f"创建文件记录失败 {task_id}: {str(e)}")
    
    async def get_download_tasks(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取下载任务列表"""
        try:
            db = await _get_db_connection()
            
            # 查询总数
            count_query = "SELECT COUNT(*) FROM video_download_tasks"
            total_result = await db.get_first(count_query)
            total = total_result[0] if total_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            query = """
                SELECT * FROM video_download_tasks 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            results = await db.query(query, page_size, offset)
            
            tasks = []
            for task in results:
                # 解析result字段
                if task.get('result'):
                    try:
                        task['result'] = json.loads(task['result'])
                    except:
                        pass
                
                tasks.append(task)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'tasks': tasks,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
                
        except Exception as e:
            logger.error(f"获取下载任务列表失败: {str(e)}")
            return {
                'tasks': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def get_download_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取下载任务详情"""
        try:
            db = await _get_db_connection()
            
            query = "SELECT * FROM video_download_tasks WHERE task_id = %s"
            result = await db.get_first(query, task_id)
            
            if result:
                # 解析result字段
                if result.get('result'):
                    try:
                        result['result'] = json.loads(result['result'])
                    except:
                        pass
                
                return result
            
            return None
                
        except Exception as e:
            logger.error(f"获取下载任务详情失败 {task_id}: {str(e)}")
            return None
    
    async def cancel_download_task(self, task_id: str) -> bool:
        """取消下载任务"""
        try:
            db = await _get_db_connection()
            
            query = """
                UPDATE video_download_tasks 
                SET status = 'cancelled', updated_at = %s
                WHERE task_id = %s AND status IN ('created', 'downloading')
            """
            result = await db.execute(query, datetime.now(), task_id)
            
            return result > 0
                
        except Exception as e:
            logger.error(f"取消下载任务失败 {task_id}: {str(e)}")
            return False
    
    async def delete_download_task(self, task_id: str) -> bool:
        """删除下载任务"""
        try:
            db = await _get_db_connection()
            
            # 先获取任务信息
            query = "SELECT * FROM video_download_tasks WHERE task_id = %s"
            task = await db.get_first(query, task_id)
            
            if task:
                # 删除文件记录
                await db.execute("DELETE FROM video_files WHERE task_id = %s", task_id)
                
                # 删除任务记录
                await db.execute("DELETE FROM video_download_tasks WHERE task_id = %s", task_id)
                
                # 删除实际文件
                await self._delete_physical_file(task)
                
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"删除下载任务失败 {task_id}: {str(e)}")
            return False
    
    async def _delete_physical_file(self, task_info: Dict[str, Any]):
        """删除物理文件"""
        try:
            # 这里需要根据存储类型删除文件
            # 本地文件直接删除
            # MinIO文件需要调用MinIO删除接口
            pass
        except Exception as e:
            logger.error(f"删除物理文件失败: {str(e)}")
    
    async def get_download_statistics(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        try:
            db = await _get_db_connection()
            
            # 统计各状态的任务数量
            status_query = """
                SELECT status, COUNT(*) as count 
                FROM video_download_tasks 
                GROUP BY status
            """
            status_results = await db.query(status_query)
            
            status_stats = {}
            for result in status_results:
                status_stats[result['status']] = result['count']
            
            # 统计总文件大小
            size_query = """
                SELECT SUM(file_size) as total_size, COUNT(*) as file_count
                FROM video_files
            """
            size_result = await db.get_first(size_query)
            
            total_size = size_result['total_size'] if size_result and size_result['total_size'] else 0
            file_count = size_result['file_count'] if size_result and size_result['file_count'] else 0
            
            # 统计各平台下载量
            platform_query = """
                SELECT platform, COUNT(*) as count
                FROM video_download_tasks
                GROUP BY platform
            """
            platform_results = await db.query(platform_query)
            
            platform_stats = {}
            for result in platform_results:
                platform_stats[result['platform']] = result['count']
            
            return {
                'status_stats': status_stats,
                'total_size': total_size,
                'file_count': file_count,
                'platform_stats': platform_stats,
                'last_updated': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"获取下载统计失败: {str(e)}")
            return {
                'status_stats': {},
                'total_size': 0,
                'file_count': 0,
                'platform_stats': {},
                'last_updated': datetime.now().isoformat()
            } 