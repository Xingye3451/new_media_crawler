"""
视频收藏服务
"""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from utils.db_utils import _get_db_connection
from utils.minio_client import MinioClient

logger = logging.getLogger(__name__)

class VideoFavoriteService:
    """视频收藏服务"""
    
    def __init__(self):
        self.minio_client = MinioClient()
    
    async def add_favorite(self, video_data: Dict[str, Any], download_to_minio: bool = True) -> Dict[str, Any]:
        """
        添加视频收藏
        
        Args:
            video_data: 视频数据，包含以下字段：
                - platform: 平台 (dy, xhs, etc.)
                - content_id: 内容ID
                - task_id: 任务ID (可选)
                - original_url: 原始视频URL
                - title: 视频标题
                - author_name: 作者名称
                - thumbnail_url: 缩略图URL
                - metadata: 扩展元数据 (可选)
            download_to_minio: 是否下载到MinIO
        
        Returns:
            Dict: 收藏结果
        """
        try:
            # 生成文件哈希
            file_hash = self._generate_file_hash(video_data)
            
            # 检查是否已存在
            existing_file = await self._get_file_by_hash(file_hash)
            if existing_file:
                return {
                    "success": True,
                    "message": "视频已收藏",
                    "data": existing_file
                }
            
            # 创建文件记录
            file_record = {
                "file_hash": file_hash,
                "platform": video_data.get("platform"),
                "content_id": video_data.get("content_id"),
                "task_id": video_data.get("task_id"),
                "original_url": video_data.get("original_url"),
                "title": video_data.get("title"),
                "author_name": video_data.get("author_name"),
                "storage_type": "minio" if download_to_minio else "url_only",
                "download_status": "downloading" if download_to_minio else "pending",
                "metadata": json.dumps(video_data.get("metadata", {}), ensure_ascii=False),
                "thumbnail_url": video_data.get("thumbnail_url"),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 保存到数据库
            file_id = await self._save_file_record(file_record)
            
            # 如果需要下载到MinIO
            if download_to_minio:
                # 异步下载到MinIO
                asyncio.create_task(self._download_and_update_minio(file_record))
                
                return {
                    "success": True,
                    "message": "收藏成功，正在下载到MinIO...",
                    "data": {
                        "file_id": file_id,
                        "file_hash": file_hash,
                        "download_status": "downloading"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": "收藏成功",
                    "data": {
                        "file_id": file_id,
                        "file_hash": file_hash
                    }
                }
            
        except Exception as e:
            logger.error(f"添加收藏失败: {str(e)}")
            return {
                "success": False,
                "message": f"收藏失败: {str(e)}",
                "data": None
            }
    
    async def download_and_store(self, file_hash: str, storage_type: str = "minio") -> Dict[str, Any]:
        """
        下载并存储视频文件
        
        Args:
            file_hash: 文件哈希
            storage_type: 存储类型 (minio, local)
        
        Returns:
            Dict: 下载结果
        """
        try:
            # 获取文件记录
            file_record = await self._get_file_by_hash(file_hash)
            if not file_record:
                return {
                    "success": False,
                    "message": "文件记录不存在",
                    "data": None
                }
            
            # 检查是否已下载
            if file_record.get("download_status") == "completed":
                return {
                    "success": True,
                    "message": "文件已存在",
                    "data": file_record
                }
            
            # 更新状态为下载中
            await self._update_download_status(file_hash, "downloading")
            
            # 下载视频
            if storage_type == "minio":
                result = await self._download_to_minio(file_record)
            else:
                result = await self._download_to_local(file_record)
            
            if result["success"]:
                # 更新文件记录
                await self._update_file_record(file_hash, {
                    "storage_type": storage_type,
                    "download_status": "completed",
                    "download_progress": 100.0,
                    "last_accessed_at": datetime.now()
                })
                
                return {
                    "success": True,
                    "message": "下载完成",
                    "data": result["data"]
                }
            else:
                # 更新失败状态
                await self._update_download_status(file_hash, "failed", result.get("error", "下载失败"))
                return result
                
        except Exception as e:
            logger.error(f"下载存储失败 {file_hash}: {str(e)}")
            await self._update_download_status(file_hash, "failed", str(e))
            return {
                "success": False,
                "message": f"下载失败: {str(e)}",
                "data": None
            }
    
    async def get_favorites(self, platform: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取收藏列表
        
        Args:
            platform: 平台筛选
            page: 页码
            page_size: 每页数量
        
        Returns:
            Dict: 收藏列表
        """
        try:
            db = await _get_db_connection()
            
            # 构建查询条件
            where_clause = ""
            params = []
            if platform:
                where_clause = "WHERE platform = %s"
                params.append(platform)
            
            # 查询总数
            count_query = f"SELECT COUNT(*) as total FROM video_files {where_clause}"
            count_result = await db.query(count_query, *params)
            total = count_result[0]["total"] if count_result else 0
            
            # 查询数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT * FROM video_files 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            
            results = await db.query(query, *params)
            
            return {
                "success": True,
                "data": {
                    "items": results,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            logger.error(f"获取收藏列表失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }
    
    async def remove_favorite(self, file_hash: str) -> Dict[str, Any]:
        """
        移除收藏
        
        Args:
            file_hash: 文件哈希
        
        Returns:
            Dict: 移除结果
        """
        try:
            # 获取文件记录
            file_record = await self._get_file_by_hash(file_hash)
            if not file_record:
                return {
                    "success": False,
                    "message": "文件记录不存在",
                    "data": None
                }
            
            # 删除物理文件
            await self._delete_physical_file(file_record)
            
            # 删除数据库记录
            db = await _get_db_connection()
            query = "DELETE FROM video_files WHERE file_hash = %s"
            await db.execute(query, file_hash)
            
            return {
                "success": True,
                "message": "移除成功",
                "data": {"file_hash": file_hash}
            }
            
        except Exception as e:
            logger.error(f"移除收藏失败 {file_hash}: {str(e)}")
            return {
                "success": False,
                "message": f"移除失败: {str(e)}",
                "data": None
            }
    
    def _generate_file_hash(self, video_data: Dict[str, Any]) -> str:
        """生成文件哈希"""
        content = f"{video_data.get('platform')}_{video_data.get('content_id')}_{video_data.get('original_url')}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def _get_file_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """根据哈希获取文件记录"""
        try:
            db = await _get_db_connection()
            query = "SELECT * FROM video_files WHERE file_hash = %s"
            results = await db.query(query, file_hash)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取文件记录失败 {file_hash}: {str(e)}")
            return None
    
    async def _save_file_record(self, file_record: Dict[str, Any]) -> int:
        """保存文件记录"""
        db = await _get_db_connection()
        query = """
            INSERT INTO video_files 
            (file_hash, platform, content_id, task_id, original_url, title, author_name,
             storage_type, download_status, metadata, thumbnail_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        result = await db.execute(query, 
            file_record["file_hash"], file_record["platform"], file_record["content_id"],
            file_record["task_id"], file_record["original_url"], file_record["title"],
            file_record["author_name"], file_record["storage_type"], file_record["download_status"],
            file_record["metadata"], file_record["thumbnail_url"], file_record["created_at"],
            file_record["updated_at"]
        )
        return result
    
    async def _update_download_status(self, file_hash: str, status: str, error: str = None):
        """更新下载状态"""
        try:
            db = await _get_db_connection()
            if error:
                query = """
                    UPDATE video_files 
                    SET download_status = %s, download_error = %s, updated_at = %s
                    WHERE file_hash = %s
                """
                await db.execute(query, status, error, datetime.now(), file_hash)
            else:
                query = """
                    UPDATE video_files 
                    SET download_status = %s, updated_at = %s
                    WHERE file_hash = %s
                """
                await db.execute(query, status, datetime.now(), file_hash)
        except Exception as e:
            logger.error(f"更新下载状态失败 {file_hash}: {str(e)}")
    
    async def _update_file_record(self, file_hash: str, updates: Dict[str, Any]):
        """更新文件记录"""
        try:
            db = await _get_db_connection()
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            query = f"UPDATE video_files SET {set_clause}, updated_at = %s WHERE file_hash = %s"
            params = list(updates.values()) + [datetime.now(), file_hash]
            await db.execute(query, *params)
        except Exception as e:
            logger.error(f"更新文件记录失败 {file_hash}: {str(e)}")
    
    async def _download_to_minio(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """下载到MinIO"""
        try:
            import aiohttp
            
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # 下载视频数据
            async with aiohttp.ClientSession() as session:
                async with session.get(file_record["original_url"], headers=headers) as response:
                    if response.status == 200:
                        video_data = await response.read()
                        
                        # 生成MinIO对象名
                        platform = file_record.get("platform", "unknown")
                        content_id = file_record.get("content_id", "unknown")
                        object_name = f"{platform}/{content_id}/{file_record['file_hash']}.mp4"
                        
                        # 上传到MinIO
                        result = await self.minio_client.upload_data(
                            bucket_name=self.minio_client.bucket_name,
                            object_name=object_name,
                            data=video_data,
                            content_type="video/mp4"
                        )
                        
                        if result["success"]:
                            return {
                                "success": True,
                                "data": {
                                    "storage_type": "minio",
                                    "minio_bucket": self.minio_client.bucket_name,
                                    "minio_object_key": object_name,
                                    "file_size": len(video_data),
                                    "minio_url": result.get("url", "")
                                }
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"MinIO上传失败: {result.get('error', '未知错误')}"
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"视频下载失败，状态码: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"下载到MinIO失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _download_to_local(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """下载到本地"""
        try:
            # 这里实现本地下载逻辑
            # 暂时返回成功，实际实现需要下载文件
            return {
                "success": True,
                "data": {
                    "storage_type": "local",
                    "local_path": f"data/videos/{file_record['file_hash']}.mp4"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _download_and_update_minio(self, file_record: Dict[str, Any]):
        """异步下载并更新MinIO信息"""
        try:
            # 下载到MinIO
            result = await self._download_to_minio(file_record)
            
            if result["success"]:
                # 更新文件记录
                await self._update_file_record(file_record["file_hash"], {
                    "download_status": "completed",
                    "download_progress": 100.0,
                    "minio_bucket": result["data"]["minio_bucket"],
                    "minio_object_key": result["data"]["minio_object_key"],
                    "file_size": result["data"]["file_size"],
                    "minio_url": result["data"]["minio_url"],
                    "last_accessed_at": datetime.now()
                })
                logger.info(f"视频下载到MinIO成功: {file_record['file_hash']}")
            else:
                # 更新失败状态
                await self._update_download_status(file_record["file_hash"], "failed", result.get("error", "下载失败"))
                logger.error(f"视频下载到MinIO失败: {file_record['file_hash']}, 错误: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"异步下载失败 {file_record['file_hash']}: {str(e)}")
            await self._update_download_status(file_record["file_hash"], "failed", str(e))
    
    async def get_favorites_statistics(self) -> Dict[str, Any]:
        """获取收藏统计信息"""
        try:
            db = await _get_db_connection()
            if not db:
                return {
                    "success": False,
                    "message": "数据库连接失败"
                }
            
            # 查询总收藏数 - 修复表名
            total_query = "SELECT COUNT(*) as total FROM video_files"
            total_result = await db.get_first(total_query)
            total_favorites = total_result['total'] if total_result else 0
            
            # 查询各平台收藏数 - 修复表名
            platform_query = """
            SELECT platform, COUNT(*) as count 
            FROM video_files 
            GROUP BY platform
            """
            platform_results = await db.query(platform_query)
            platform_stats = {row['platform']: row['count'] for row in platform_results}
            
            # 查询存储类型统计 - 修复表名
            storage_query = """
            SELECT storage_type, COUNT(*) as count 
            FROM video_files 
            GROUP BY storage_type
            """
            storage_results = await db.query(storage_query)
            storage_stats = {row['storage_type']: row['count'] for row in storage_results}
            
            # 查询下载状态统计 - 修复表名
            status_query = """
            SELECT download_status, COUNT(*) as count 
            FROM video_files 
            GROUP BY download_status
            """
            status_results = await db.query(status_query)
            status_stats = {row['download_status']: row['count'] for row in status_results}
            
            # 计算总文件大小 - 修复表名
            size_query = """
            SELECT SUM(file_size) as total_size 
            FROM video_files 
            WHERE file_size IS NOT NULL
            """
            size_result = await db.get_first(size_query)
            total_size = size_result['total_size'] if size_result and size_result['total_size'] else 0
            
            return {
                "success": True,
                "data": {
                    "total_favorites": total_favorites,
                    "platform_stats": platform_stats,
                    "storage_stats": storage_stats,
                    "status_stats": status_stats,
                    "total_size": total_size,
                    "total_size_formatted": self._format_bytes(total_size)
                }
            }
            
        except Exception as e:
            logger.error(f"获取收藏统计失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取统计失败: {str(e)}"
            }
    
    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        if bytes_value == 0:
            return "0 B"
        k = 1024
        sizes = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while bytes_value >= k and i < len(sizes) - 1:
            bytes_value /= k
            i += 1
        return f"{bytes_value:.2f} {sizes[i]}"
    
    async def _delete_physical_file(self, file_record: Dict[str, Any]):
        """删除物理文件"""
        try:
            storage_type = file_record.get("storage_type")
            if storage_type == "local":
                local_path = file_record.get("local_path")
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
            elif storage_type == "minio":
                # 删除MinIO文件
                bucket = file_record.get("minio_bucket")
                object_key = file_record.get("minio_object_key")
                if bucket and object_key:
                    await self.minio_client.delete_object(bucket, object_key)
        except Exception as e:
            logger.error(f"删除物理文件失败: {str(e)}") 