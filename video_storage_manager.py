# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:00
# @Desc    : 视频存储管理器

import asyncio
import aiohttp
import aiofiles
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import hashlib
import mimetypes
from datetime import datetime
import json

from storage_manager import storage_manager
from model.video_metadata import VideoMetadata, VideoMetadataManager
from config.config_manager import config_manager
from tools import utils


class VideoStorageManager:
    """视频存储管理器"""
    
    def __init__(self):
        self.storage_manager = storage_manager
        self.config = config_manager.get_storage_config()
        
        # 初始化元数据管理器
        self.metadata_manager = VideoMetadataManager(self.config.database_url)
        
        # 下载会话
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.download_timeout),
            connector=aiohttp.TCPConnector(limit=self.config.max_concurrent_downloads)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def download_and_store_video(self, 
                                     video_url: str,
                                     platform: str,
                                     content_id: str,
                                     video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        下载并存储视频
        Args:
            video_url: 视频URL
            platform: 平台名称
            content_id: 内容ID
            video_info: 视频信息
        Returns:
            Dict: 存储结果
        """
        try:
            # 1. 检查是否已存在
            existing_metadata = self.metadata_manager.get_metadata_by_content_id(platform, content_id)
            if existing_metadata:
                utils.logger.info(f"视频已存在: {platform}/{content_id}")
                return {
                    "success": True,
                    "metadata_id": existing_metadata.id,
                    "storage_info": {
                        "storage_type": existing_metadata.storage_type,
                        "file_path": existing_metadata.file_path,
                        "local_path": existing_metadata.local_path
                    },
                    "message": "视频已存在"
                }
            
            # 2. 下载视频
            video_data, filename, content_type = await self._download_video(video_url)
            if not video_data:
                return {
                    "success": False,
                    "message": "视频下载失败"
                }
            
            # 3. 保存到存储
            storage_info = await self.storage_manager.save_file(
                file_data=video_data,
                platform=platform,
                content_id=content_id,
                filename=filename,
                file_size=len(video_data)
            )
            
            # 4. 创建元数据
            metadata = VideoMetadata(
                platform=platform,
                content_id=content_id,
                title=video_info.get("title", ""),
                description=video_info.get("description", ""),
                author=video_info.get("author", ""),
                author_id=video_info.get("author_id", ""),
                storage_type=storage_info["storage_type"],
                file_path=storage_info["file_path"],
                file_size=storage_info["file_size"],
                file_hash=storage_info.get("file_hash", ""),
                content_type=storage_info["content_type"],
                local_path=storage_info.get("local_path", ""),
                duration=video_info.get("duration"),
                width=video_info.get("width"),
                height=video_info.get("height"),
                fps=video_info.get("fps"),
                bitrate=video_info.get("bitrate"),
                format=video_info.get("format"),
                view_count=video_info.get("view_count", 0),
                like_count=video_info.get("like_count", 0),
                comment_count=video_info.get("comment_count", 0),
                share_count=video_info.get("share_count", 0),
                tags=video_info.get("tags", []),
                category=video_info.get("category", ""),
                publish_time=video_info.get("publish_time"),
                crawl_time=datetime.now(),
                extra_data=video_info.get("extra_data", {})
            )
            
            # 5. 保存元数据到数据库
            metadata_id = self.metadata_manager.save_metadata(metadata)
            
            utils.logger.info(f"视频存储成功: {platform}/{content_id}, 元数据ID: {metadata_id}")
            
            return {
                "success": True,
                "metadata_id": metadata_id,
                "storage_info": storage_info,
                "message": "视频存储成功"
            }
            
        except Exception as e:
            utils.logger.error(f"视频存储失败: {e}")
            return {
                "success": False,
                "message": f"视频存储失败: {str(e)}"
            }
    
    async def _download_video(self, video_url: str) -> tuple[Optional[bytes], str, str]:
        """
        下载视频
        Args:
            video_url: 视频URL
        Returns:
            tuple: (视频数据, 文件名, 内容类型)
        """
        try:
            async with self.session.get(video_url) as response:
                if response.status != 200:
                    utils.logger.error(f"下载失败，状态码: {response.status}")
                    return None, "", ""
                
                # 获取文件名和内容类型
                content_type = response.headers.get("content-type", "")
                filename = self._extract_filename(video_url, content_type)
                
                # 分块下载
                video_data = b""
                async for chunk in response.content.iter_chunked(self.config.chunk_size):
                    video_data += chunk
                
                utils.logger.info(f"视频下载成功: {filename}, 大小: {len(video_data)} 字节")
                return video_data, filename, content_type
                
        except Exception as e:
            utils.logger.error(f"视频下载失败: {e}")
            return None, "", ""
    
    def _extract_filename(self, url: str, content_type: str) -> str:
        """提取文件名"""
        # 从URL中提取文件名
        if "?" in url:
            url = url.split("?")[0]
        
        filename = url.split("/")[-1]
        if not filename or "." not in filename:
            # 根据内容类型生成文件名
            ext = mimetypes.guess_extension(content_type) or ".mp4"
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        
        return filename
    
    async def get_video_info(self, metadata_id: int) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        try:
            metadata = self.metadata_manager.get_metadata_by_id(metadata_id)
            if not metadata:
                return None
            
            # 获取文件访问URL
            file_url = await self.storage_manager.get_file_url(metadata.to_dict())
            
            result = metadata.to_dict()
            result["file_url"] = file_url
            
            return result
            
        except Exception as e:
            utils.logger.error(f"获取视频信息失败: {e}")
            return None
    
    async def list_videos(self, 
                         platform: Optional[str] = None,
                         author: Optional[str] = None,
                         limit: int = 100,
                         offset: int = 0) -> List[Dict[str, Any]]:
        """列出视频"""
        try:
            metadata_list = self.metadata_manager.list_metadata(
                platform=platform,
                author=author,
                limit=limit,
                offset=offset
            )
            
            results = []
            for metadata in metadata_list:
                # 获取文件访问URL
                file_url = await self.storage_manager.get_file_url(metadata.to_dict())
                
                result = metadata.to_dict()
                result["file_url"] = file_url
                results.append(result)
            
            return results
            
        except Exception as e:
            utils.logger.error(f"列出视频失败: {e}")
            return []
    
    async def search_videos(self, 
                          keyword: str,
                          platform: Optional[str] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[Dict[str, Any]]:
        """搜索视频"""
        try:
            metadata_list = self.metadata_manager.search_metadata(
                keyword=keyword,
                platform=platform,
                limit=limit,
                offset=offset
            )
            
            results = []
            for metadata in metadata_list:
                # 获取文件访问URL
                file_url = await self.storage_manager.get_file_url(metadata.to_dict())
                
                result = metadata.to_dict()
                result["file_url"] = file_url
                results.append(result)
            
            return results
            
        except Exception as e:
            utils.logger.error(f"搜索视频失败: {e}")
            return []
    
    async def delete_video(self, metadata_id: int, delete_file: bool = True) -> bool:
        """删除视频"""
        try:
            metadata = self.metadata_manager.get_metadata_by_id(metadata_id)
            if not metadata:
                return False
            
            # 删除文件
            if delete_file:
                await self.storage_manager.delete_file(metadata.to_dict())
            
            # 删除元数据
            return self.metadata_manager.delete_metadata(metadata_id, soft_delete=True)
            
        except Exception as e:
            utils.logger.error(f"删除视频失败: {e}")
            return False
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            # 获取存储统计
            storage_stats = await self.storage_manager.get_storage_stats()
            
            # 获取元数据统计
            metadata_stats = self.metadata_manager.get_statistics()
            
            return {
                "storage": storage_stats,
                "metadata": metadata_stats
            }
            
        except Exception as e:
            utils.logger.error(f"获取存储统计失败: {e}")
            return {}
    
    async def batch_download_videos(self, 
                                  video_list: List[Dict[str, Any]],
                                  max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        批量下载视频
        Args:
            video_list: 视频列表，每个元素包含 url, platform, content_id, video_info
            max_concurrent: 最大并发数
        Returns:
            List: 下载结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_single(video_item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.download_and_store_video(
                    video_url=video_item["url"],
                    platform=video_item["platform"],
                    content_id=video_item["content_id"],
                    video_info=video_item["video_info"]
                )
        
        tasks = [download_single(video_item) for video_item in video_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "message": f"下载异常: {str(result)}",
                    "video_item": video_list[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results


# 使用示例
async def example_usage():
    """使用示例"""
    video_info = {
        "title": "测试视频",
        "description": "这是一个测试视频",
        "author": "测试作者",
        "author_id": "123456",
        "duration": 120.5,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "bitrate": 2000000,
        "format": "mp4",
        "view_count": 1000,
        "like_count": 100,
        "comment_count": 50,
        "share_count": 20,
        "tags": ["测试", "视频"],
        "category": "娱乐",
        "publish_time": datetime.now(),
        "extra_data": {"source": "test"}
    }
    
    async with VideoStorageManager() as vsm:
        # 下载单个视频
        result = await vsm.download_and_store_video(
            video_url="https://example.com/video.mp4",
            platform="douyin",
            content_id="test_123",
            video_info=video_info
        )
        print(f"下载结果: {result}")
        
        # 批量下载
        video_list = [
            {
                "url": "https://example.com/video1.mp4",
                "platform": "douyin",
                "content_id": "test_1",
                "video_info": video_info
            },
            {
                "url": "https://example.com/video2.mp4",
                "platform": "douyin",
                "content_id": "test_2",
                "video_info": video_info
            }
        ]
        
        batch_results = await vsm.batch_download_videos(video_list)
        print(f"批量下载结果: {batch_results}")
        
        # 获取统计信息
        stats = await vsm.get_storage_statistics()
        print(f"存储统计: {stats}")


if __name__ == "__main__":
    asyncio.run(example_usage()) 