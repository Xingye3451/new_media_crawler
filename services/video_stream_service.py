"""
视频流服务 - 后端访问转换
"""

import asyncio
import aiohttp
import aiofiles
import os
import hashlib
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from utils.db_utils import _get_db_connection
from utils.minio_client import MinioClient

logger = logging.getLogger(__name__)

class VideoStreamService:
    """视频流服务"""
    
    def __init__(self):
        self.minio_client = MinioClient()
        self.cache_dir = "data/video_cache"
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def stream_video(self, video_url: str, platform: str, content_id: str) -> Dict[str, Any]:
        """
        流式播放视频（后端访问转换）
        
        Args:
            video_url: 原始视频URL
            platform: 平台
            content_id: 内容ID
        
        Returns:
            Dict: 流式播放信息
        """
        try:
            # 生成缓存文件名
            cache_key = self._generate_cache_key(video_url)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.mp4")
            
            # 检查缓存
            if os.path.exists(cache_file):
                # 检查缓存是否过期（24小时）
                if self._is_cache_valid(cache_file):
                    logger.info(f"使用缓存视频: {cache_file}")
                    return {
                        "success": True,
                        "stream_url": f"/api/v1/stream/cache/{cache_key}",
                        "cache_file": cache_file,
                        "cached": True
                    }
                else:
                    # 删除过期缓存
                    os.remove(cache_file)
            
            # 检查数据库中是否有已下载的文件
            file_record = await self._get_file_record(platform, content_id)
            if file_record and file_record.get("download_status") == "completed":
                storage_type = file_record.get("storage_type")
                if storage_type == "minio":
                    # 从MinIO获取
                    return await self._stream_from_minio(file_record)
                elif storage_type == "local":
                    # 从本地获取
                    local_path = file_record.get("local_path")
                    if local_path and os.path.exists(local_path):
                        return {
                            "success": True,
                            "stream_url": f"/api/v1/stream/local/{file_record['file_hash']}",
                            "local_path": local_path,
                            "cached": True
                        }
            
            # 实时下载并流式播放
            return await self._stream_and_cache(video_url, cache_key, cache_file)
            
        except Exception as e:
            logger.error(f"流式播放失败 {video_url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _stream_and_cache(self, video_url: str, cache_key: str, cache_file: str) -> Dict[str, Any]:
        """实时下载并缓存"""
        try:
            # 使用aiohttp下载
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": "https://www.douyin.com/",
                    "Origin": "https://www.douyin.com"
                }
                
                async with session.get(video_url, headers=headers) as response:
                    if response.status == 200:
                        # 开始下载到缓存
                        async with aiofiles.open(cache_file, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        logger.info(f"视频下载完成: {cache_file}")
                        
                        return {
                            "success": True,
                            "stream_url": f"/api/v1/stream/cache/{cache_key}",
                            "cache_file": cache_file,
                            "cached": False
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"下载失败，状态码: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"下载缓存失败 {video_url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _stream_from_minio(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """从MinIO流式播放"""
        try:
            bucket = file_record.get("minio_bucket")
            object_key = file_record.get("minio_object_key")
            
            if not bucket or not object_key:
                return {
                    "success": False,
                    "error": "MinIO配置不完整"
                }
            
            # 生成预签名URL
            presigned_url = await self.minio_client.get_presigned_url(bucket, object_key)
            
            return {
                "success": True,
                "stream_url": presigned_url,
                "storage_type": "minio",
                "cached": True
            }
            
        except Exception as e:
            logger.error(f"MinIO流式播放失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_file_record(self, platform: str, content_id: str) -> Optional[Dict[str, Any]]:
        """获取文件记录"""
        try:
            db = await _get_db_connection()
            query = "SELECT * FROM video_files WHERE platform = %s AND content_id = %s ORDER BY created_at DESC LIMIT 1"
            results = await db.query(query, platform, content_id)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取文件记录失败: {str(e)}")
            return None
    
    def _generate_cache_key(self, video_url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(video_url.encode('utf-8')).hexdigest()
    
    def _is_cache_valid(self, cache_file: str, max_age_hours: int = 24) -> bool:
        """检查缓存是否有效"""
        try:
            stat = os.stat(cache_file)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            return datetime.now() - file_time < timedelta(hours=max_age_hours)
        except Exception:
            return False
    
    async def cleanup_expired_cache(self, max_age_hours: int = 24):
        """清理过期缓存"""
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    if not self._is_cache_valid(file_path, max_age_hours):
                        os.remove(file_path)
                        logger.info(f"清理过期缓存: {filename}")
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            total_files = 0
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "cache_dir": self.cache_dir
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {str(e)}")
            return {
                "total_files": 0,
                "total_size": 0,
                "cache_dir": self.cache_dir
            } 