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
        下载视频到本地
        
        Args:
            video_url: 视频URL
            video_id: 视频ID
            platform: 平台标识
            download_type: 下载类型 (local/server)
        
        Returns:
            下载结果字典
        """
        try:
            # 直接下载到本地，不创建数据库记录
            result = await self._download_to_local(video_url, video_id, platform)
            
            return {
                'success': result['success'],
                'file_path': result.get('file_path'),
                'file_url': result.get('file_url'),
                'file_size': result.get('file_size'),
                'storage_type': 'local',
                'message': result.get('message')
            }
            
        except Exception as e:
            logger.error(f"下载视频失败 {video_id}: {str(e)}")
            return {
                'success': False,
                'message': f"下载失败: {str(e)}"
            }
    
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
                               platform: str) -> Dict[str, Any]:
        """下载到本地存储"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{platform}_{video_id}_{timestamp}.mp4"
            file_path = os.path.join(self.download_dir, filename)
            
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 下载文件
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, headers=headers) as response:
                    if response.status == 200:
                        # 确保目录存在
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # 下载文件
                        async with aiofiles.open(file_path, 'wb') as f:
                            total_size = 0
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                total_size += len(chunk)
                        
                        # 验证文件大小
                        actual_size = os.path.getsize(file_path)
                        if actual_size == 0:
                            return {
                                'success': False,
                                'message': '下载的文件为空'
                            }
                        
                        logger.info(f"✅ 视频下载成功: {file_path}, 大小: {actual_size} bytes")
                        
                        return {
                            'success': True,
                            'file_path': file_path,
                            'file_url': f"/downloads/{filename}",
                            'file_size': actual_size,
                            'storage_type': 'local',
                            'message': '下载成功'
                        }
                    else:
                        logger.error(f"❌ 下载失败: HTTP {response.status}")
                        return {
                            'success': False,
                            'message': f'下载失败: HTTP {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"❌ 本地下载失败 {video_id}: {str(e)}")
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
    

    
    async def get_download_statistics(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        try:
            # 统计本地下载目录
            total_files = 0
            total_size = 0
            
            if os.path.exists(self.download_dir):
                for filename in os.listdir(self.download_dir):
                    file_path = os.path.join(self.download_dir, filename)
                    if os.path.isfile(file_path):
                        total_files += 1
                        total_size += os.path.getsize(file_path)
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'download_dir': self.download_dir,
                'last_updated': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"获取下载统计失败: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'download_dir': self.download_dir,
                'last_updated': datetime.now().isoformat()
            } 