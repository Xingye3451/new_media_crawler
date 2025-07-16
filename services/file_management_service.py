"""
文件管理服务层
处理文件管理相关的业务逻辑
"""

import os
import asyncio
import aiofiles
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
from pathlib import Path
import mimetypes

from utils.db_utils import _get_db_connection
from config.base_config import *

logger = logging.getLogger(__name__)

class FileManagementService:
    """文件管理服务层"""
    
    def __init__(self):
        self.download_dir = "downloads"
        self.upload_dir = "uploads"
        self.allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保必要目录存在"""
        for directory in [self.download_dir, self.upload_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    async def get_file_list(self, page: int = 1, page_size: int = 20, 
                           storage_type: str = None) -> Dict[str, Any]:
        """获取文件列表"""
        try:
            db = await _get_db_connection()
            
            # 构建查询条件
            where_clause = ""
            params = []
            if storage_type:
                where_clause = "WHERE storage_type = %s"
                params.append(storage_type)
            
            # 查询总数
            count_query = f"SELECT COUNT(*) FROM video_files {where_clause}"
            total_result = await db.get_first(count_query, *params)
            total = total_result[0] if total_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT vf.*, vdt.video_id, vdt.platform, vdt.video_url
                FROM video_files vf
                LEFT JOIN video_download_tasks vdt ON vf.task_id = vdt.task_id
                {where_clause}
                ORDER BY vf.created_at DESC 
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            results = await db.query(query, *params)
            
            files = []
            for file_info in results:
                # 补充文件状态信息
                file_info['exists'] = await self._check_file_exists(file_info)
                file_info['file_type'] = self._get_file_type(file_info.get('file_path', ''))
                
                files.append(file_info)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'files': files,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
                
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return {
                'files': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def _check_file_exists(self, file_info: Dict[str, Any]) -> bool:
        """检查文件是否存在"""
        try:
            storage_type = file_info.get('storage_type', 'local')
            
            if storage_type == 'local':
                file_path = file_info.get('file_path', '')
                return os.path.exists(file_path)
            elif storage_type == 'minio':
                # 这里需要检查MinIO中的文件
                # 暂时返回True
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"检查文件存在性失败: {str(e)}")
            return False
    
    def _get_file_type(self, file_path: str) -> str:
        """获取文件类型"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                if mime_type.startswith('video/'):
                    return 'video'
                elif mime_type.startswith('audio/'):
                    return 'audio'
                elif mime_type.startswith('image/'):
                    return 'image'
            return 'unknown'
        except:
            return 'unknown'
    
    async def get_file_detail(self, file_id: int) -> Optional[Dict[str, Any]]:
        """获取文件详情"""
        try:
            db = await _get_db_connection()
            
            query = """
                SELECT vf.*, vdt.video_id, vdt.platform, vdt.video_url
                FROM video_files vf
                LEFT JOIN video_download_tasks vdt ON vf.task_id = vdt.task_id
                WHERE vf.id = %s
            """
            result = await db.get_first(query, file_id)
            
            if result:
                # 补充详细信息
                result['exists'] = await self._check_file_exists(result)
                result['file_type'] = self._get_file_type(result.get('file_path', ''))
                
                # 获取文件元数据
                metadata = await self._get_file_metadata(result)
                result['metadata'] = metadata
                
                return result
            
            return None
                
        except Exception as e:
            logger.error(f"获取文件详情失败 {file_id}: {str(e)}")
            return None
    
    async def _get_file_metadata(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取文件元数据"""
        try:
            storage_type = file_info.get('storage_type', 'local')
            
            if storage_type == 'local':
                file_path = file_info.get('file_path', '')
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    return {
                        'size': stat.st_size,
                        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'accessed_time': datetime.fromtimestamp(stat.st_atime).isoformat()
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取文件元数据失败: {str(e)}")
            return {}
    
    async def delete_file(self, file_id: int) -> bool:
        """删除文件"""
        try:
            db = await _get_db_connection()
            
            # 先获取文件信息
            query = "SELECT * FROM video_files WHERE id = %s"
            file_info = await db.get_first(query, file_id)
            
            if file_info:
                # 删除数据库记录
                await db.execute("DELETE FROM video_files WHERE id = %s", file_id)
                
                # 删除物理文件
                await self._delete_physical_file(file_info)
                
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"删除文件失败 {file_id}: {str(e)}")
            return False
    
    async def _delete_physical_file(self, file_data: Dict[str, Any]):
        """删除物理文件"""
        try:
            storage_type = file_data.get('storage_type', 'local')
            
            if storage_type == 'local':
                file_path = file_data.get('file_path', '')
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"删除本地文件: {file_path}")
            elif storage_type == 'minio':
                # 这里需要调用MinIO删除接口
                logger.info(f"删除MinIO文件: {file_data.get('file_url', '')}")
                pass
                
        except Exception as e:
            logger.error(f"删除物理文件失败: {str(e)}")
    
    async def move_file(self, file_id: int, target_dir: str) -> bool:
        """移动文件"""
        try:
            db = await _get_db_connection()
            
            # 获取文件信息
            query = "SELECT * FROM video_files WHERE id = %s"
            file_info = await db.get_first(query, file_id)
            
            if file_info:
                old_path = file_info.get('file_path', '')
                if not os.path.exists(old_path):
                    return False
                
                # 创建目标目录
                os.makedirs(target_dir, exist_ok=True)
                
                # 生成新路径
                filename = os.path.basename(old_path)
                new_path = os.path.join(target_dir, filename)
                
                # 移动文件
                os.rename(old_path, new_path)
                
                # 更新数据库记录
                new_url = new_path.replace(self.download_dir, '/downloads')
                query = """
                    UPDATE video_files 
                    SET file_path = %s, file_url = %s, updated_at = %s
                    WHERE id = %s
                """
                await db.execute(query, new_path, new_url, datetime.now(), file_id)
                
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"移动文件失败 {file_id}: {str(e)}")
            return False
    
    async def batch_delete_files(self, file_ids: List[int]) -> Dict[str, Any]:
        """批量删除文件"""
        try:
            success_count = 0
            failed_count = 0
            failed_files = []
            
            for file_id in file_ids:
                try:
                    if await self.delete_file(file_id):
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_files.append(file_id)
                except Exception as e:
                    failed_count += 1
                    failed_files.append(file_id)
                    logger.error(f"批量删除文件失败 {file_id}: {str(e)}")
            
            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'failed_files': failed_files,
                'total_count': len(file_ids)
            }
            
        except Exception as e:
            logger.error(f"批量删除文件失败: {str(e)}")
            return {
                'success_count': 0,
                'failed_count': len(file_ids),
                'failed_files': file_ids,
                'total_count': len(file_ids)
            }
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            db = await _get_db_connection()
            
            # 按存储类型统计
            type_query = """
                SELECT storage_type, COUNT(*) as count, SUM(file_size) as total_size
                FROM video_files
                GROUP BY storage_type
            """
            type_results = await db.query(type_query)
            
            storage_stats = {}
            total_files = 0
            total_size = 0
            
            for result in type_results:
                storage_type = result['storage_type']
                count = result['count']
                size = result['total_size'] if result['total_size'] else 0
                
                storage_stats[storage_type] = {
                    'count': count,
                    'total_size': size
                }
                total_files += count
                total_size += size
            
            # 按平台统计
            platform_query = """
                SELECT vdt.platform, COUNT(*) as count, SUM(vf.file_size) as total_size
                FROM video_files vf
                LEFT JOIN video_download_tasks vdt ON vf.task_id = vdt.task_id
                WHERE vdt.platform IS NOT NULL
                GROUP BY vdt.platform
            """
            platform_results = await db.query(platform_query)
            
            platform_stats = {}
            for result in platform_results:
                platform = result['platform']
                count = result['count']
                size = result['total_size'] if result['total_size'] else 0
                
                platform_stats[platform] = {
                    'count': count,
                    'total_size': size
                }
            
            # 磁盘使用情况
            disk_usage = await self._get_disk_usage()
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'storage_stats': storage_stats,
                'platform_stats': platform_stats,
                'disk_usage': disk_usage,
                'last_updated': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"获取存储统计失败: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'storage_stats': {},
                'platform_stats': {},
                'disk_usage': {},
                'last_updated': datetime.now().isoformat()
            }
    
    async def _get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            import shutil
            
            # 获取下载目录磁盘使用情况
            download_usage = shutil.disk_usage(self.download_dir)
            
            return {
                'total': download_usage.total,
                'used': download_usage.used,
                'free': download_usage.free,
                'usage_percent': (download_usage.used / download_usage.total) * 100
            }
            
        except Exception as e:
            logger.error(f"获取磁盘使用情况失败: {str(e)}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'usage_percent': 0
            }
    
    async def cleanup_orphaned_files(self) -> Dict[str, Any]:
        """清理孤立文件"""
        try:
            orphaned_files = []
            missing_files = []
            
            db = await _get_db_connection()
            
            # 查找数据库中的所有文件记录
            query = "SELECT id, file_path, storage_type FROM video_files"
            results = await db.query(query)
            
            for result in results:
                file_id = result['id']
                file_path = result['file_path']
                storage_type = result['storage_type']
                
                if storage_type == 'local':
                    if not os.path.exists(file_path):
                        missing_files.append({
                            'id': file_id,
                            'path': file_path,
                            'storage_type': storage_type
                        })
            
            # 查找文件系统中的孤立文件
            if os.path.exists(self.download_dir):
                for root, dirs, files in os.walk(self.download_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        
                        # 检查是否在数据库中
                        check_query = "SELECT COUNT(*) FROM video_files WHERE file_path = %s"
                        count_result = await db.get_first(check_query, full_path)
                        
                        if count_result[0] == 0:
                            orphaned_files.append(full_path)
            
            return {
                'orphaned_files': orphaned_files,
                'missing_files': missing_files,
                'orphaned_count': len(orphaned_files),
                'missing_count': len(missing_files)
            }
                
        except Exception as e:
            logger.error(f"清理孤立文件失败: {str(e)}")
            return {
                'orphaned_files': [],
                'missing_files': [],
                'orphaned_count': 0,
                'missing_count': 0
            }
    
    async def remove_orphaned_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """删除孤立文件"""
        try:
            success_count = 0
            failed_count = 0
            failed_files = []
            
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_files.append(file_path)
                except Exception as e:
                    failed_count += 1
                    failed_files.append(file_path)
                    logger.error(f"删除孤立文件失败 {file_path}: {str(e)}")
            
            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'failed_files': failed_files,
                'total_count': len(file_paths)
            }
            
        except Exception as e:
            logger.error(f"删除孤立文件失败: {str(e)}")
            return {
                'success_count': 0,
                'failed_count': len(file_paths),
                'failed_files': file_paths,
                'total_count': len(file_paths)
            }
    
    async def remove_missing_records(self, file_ids: List[int]) -> Dict[str, Any]:
        """删除缺失文件的数据库记录"""
        try:
            success_count = 0
            failed_count = 0
            failed_ids = []
            
            db = await _get_db_connection()
            
            for file_id in file_ids:
                try:
                    await db.execute("DELETE FROM video_files WHERE id = %s", file_id)
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    failed_ids.append(file_id)
                    logger.error(f"删除缺失文件记录失败 {file_id}: {str(e)}")
            
            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'failed_ids': failed_ids,
                'total_count': len(file_ids)
            }
            
        except Exception as e:
            logger.error(f"删除缺失文件记录失败: {str(e)}")
            return {
                'success_count': 0,
                'failed_count': len(file_ids),
                'failed_ids': file_ids,
                'total_count': len(file_ids)
            } 