# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:00
# @Desc    : 混合存储管理器

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO, Union
from datetime import datetime
import asyncio
import aiofiles
import aiohttp
from urllib.parse import urlparse

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from config.config_manager import config_manager
from tools import utils


class StorageManager:
    """混合存储管理器"""
    
    def __init__(self):
        self.config = config_manager.get_storage_config()
        self.local_base_path = Path(self.config.get("local_base_path", "/app/data"))
        self.minio_client = None
        self.minio_bucket = self.config.get("minio_bucket", "mediacrawler-videos")
        
        # 确保本地存储目录存在
        self.local_base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化MinIO客户端
        if MINIO_AVAILABLE and self.config.get("enable_minio", False):
            self._init_minio_client()
    
    def _init_minio_client(self):
        """初始化MinIO客户端"""
        try:
            self.minio_client = Minio(
                endpoint=self.config.get("minio_endpoint", "localhost:9000"),
                access_key=self.config.get("minio_access_key", "minioadmin"),
                secret_key=self.config.get("minio_secret_key", "minioadmin"),
                secure=self.config.get("minio_secure", False)
            )
            
            # 确保bucket存在
            if not self.minio_client.bucket_exists(self.minio_bucket):
                self.minio_client.make_bucket(self.minio_bucket)
                utils.logger.info(f"创建MinIO bucket: {self.minio_bucket}")
            
            utils.logger.info("MinIO客户端初始化成功")
        except Exception as e:
            utils.logger.error(f"MinIO客户端初始化失败: {e}")
            self.minio_client = None
    
    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_storage_strategy(self, file_size: int) -> Dict[str, Any]:
        """根据文件大小确定存储策略"""
        if file_size <= self.config.get("small_file_threshold", 10 * 1024 * 1024):  # 10MB
            return {
                "storage": "local",
                "path": self.local_base_path / "small_files"
            }
        else:
            return {
                "storage": "minio",
                "bucket": self.minio_bucket
            }
    
    def _generate_file_path(self, platform: str, content_id: str, filename: str) -> str:
        """生成文件存储路径"""
        # 使用平台和内容ID生成目录结构
        date_str = datetime.now().strftime("%Y/%m/%d")
        return f"{platform}/{date_str}/{content_id}/{filename}"
    
    async def save_file(self, 
                       file_data: Union[bytes, BinaryIO], 
                       platform: str, 
                       content_id: str, 
                       filename: str,
                       file_size: Optional[int] = None) -> Dict[str, Any]:
        """
        保存文件到合适的存储位置
        Args:
            file_data: 文件数据
            platform: 平台名称
            content_id: 内容ID
            filename: 文件名
            file_size: 文件大小（字节）
        Returns:
            Dict: 存储信息
        """
        try:
            # 确定存储策略
            if file_size is None:
                if isinstance(file_data, bytes):
                    file_size = len(file_data)
                else:
                    # 如果是文件对象，需要获取大小
                    file_data.seek(0, 2)
                    file_size = file_data.tell()
                    file_data.seek(0)
            
            strategy = self._get_storage_strategy(file_size)
            file_path = self._generate_file_path(platform, content_id, filename)
            
            # 获取文件类型
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"
            
            storage_info = {
                "platform": platform,
                "content_id": content_id,
                "filename": filename,
                "file_size": file_size,
                "content_type": content_type,
                "storage_type": strategy["storage"],
                "file_path": file_path,
                "created_at": datetime.now().isoformat()
            }
            
            if strategy["storage"] == "local":
                # 本地存储
                local_path = strategy["path"] / file_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(file_data, bytes):
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(file_data)
                else:
                    async with aiofiles.open(local_path, 'wb') as f:
                        while chunk := file_data.read(8192):
                            await f.write(chunk)
                
                # 计算文件哈希
                file_hash = self._get_file_hash(local_path)
                storage_info["file_hash"] = file_hash
                storage_info["local_path"] = str(local_path)
                
                utils.logger.info(f"文件已保存到本地: {local_path}")
                
            elif strategy["storage"] == "minio" and self.minio_client:
                # MinIO存储
                if isinstance(file_data, bytes):
                    # 创建临时文件
                    temp_path = Path("/tmp") / f"temp_{filename}"
                    async with aiofiles.open(temp_path, 'wb') as f:
                        await f.write(file_data)
                    
                    # 上传到MinIO
                    self.minio_client.fput_object(
                        bucket_name=strategy["bucket"],
                        object_name=file_path,
                        file_path=str(temp_path),
                        content_type=content_type
                    )
                    
                    # 删除临时文件
                    temp_path.unlink()
                else:
                    # 直接上传文件对象
                    self.minio_client.put_object(
                        bucket_name=strategy["bucket"],
                        object_name=file_path,
                        data=file_data,
                        length=file_size,
                        content_type=content_type
                    )
                
                # 获取文件URL
                file_url = self.minio_client.presigned_get_object(
                    bucket_name=strategy["bucket"],
                    object_name=file_path,
                    expires=3600  # 1小时有效期
                )
                
                storage_info["file_url"] = file_url
                utils.logger.info(f"文件已上传到MinIO: {file_path}")
            
            return storage_info
            
        except Exception as e:
            utils.logger.error(f"保存文件失败: {e}")
            raise
    
    async def get_file(self, storage_info: Dict[str, Any]) -> Optional[bytes]:
        """
        获取文件内容
        Args:
            storage_info: 存储信息
        Returns:
            Optional[bytes]: 文件内容
        """
        try:
            if storage_info["storage_type"] == "local":
                # 从本地获取
                local_path = Path(storage_info["local_path"])
                if local_path.exists():
                    async with aiofiles.open(local_path, 'rb') as f:
                        return await f.read()
                else:
                    utils.logger.warning(f"本地文件不存在: {local_path}")
                    return None
                    
            elif storage_info["storage_type"] == "minio" and self.minio_client:
                # 从MinIO获取
                try:
                    response = self.minio_client.get_object(
                        bucket_name=self.minio_bucket,
                        object_name=storage_info["file_path"]
                    )
                    return response.read()
                except S3Error as e:
                    utils.logger.error(f"从MinIO获取文件失败: {e}")
                    return None
            
            return None
            
        except Exception as e:
            utils.logger.error(f"获取文件失败: {e}")
            return None
    
    async def get_file_url(self, storage_info: Dict[str, Any], expires: int = 3600) -> Optional[str]:
        """
        获取文件访问URL
        Args:
            storage_info: 存储信息
            expires: 过期时间（秒）
        Returns:
            Optional[str]: 文件URL
        """
        try:
            if storage_info["storage_type"] == "local":
                # 本地文件，返回相对路径
                return f"/files/{storage_info['file_path']}"
                
            elif storage_info["storage_type"] == "minio" and self.minio_client:
                # MinIO文件，生成预签名URL
                return self.minio_client.presigned_get_object(
                    bucket_name=self.minio_bucket,
                    object_name=storage_info["file_path"],
                    expires=expires
                )
            
            return None
            
        except Exception as e:
            utils.logger.error(f"获取文件URL失败: {e}")
            return None
    
    async def delete_file(self, storage_info: Dict[str, Any]) -> bool:
        """
        删除文件
        Args:
            storage_info: 存储信息
        Returns:
            bool: 是否删除成功
        """
        try:
            if storage_info["storage_type"] == "local":
                # 删除本地文件
                local_path = Path(storage_info["local_path"])
                if local_path.exists():
                    local_path.unlink()
                    utils.logger.info(f"删除本地文件: {local_path}")
                    return True
                return False
                
            elif storage_info["storage_type"] == "minio" and self.minio_client:
                # 删除MinIO文件
                try:
                    self.minio_client.remove_object(
                        bucket_name=self.minio_bucket,
                        object_name=storage_info["file_path"]
                    )
                    utils.logger.info(f"删除MinIO文件: {storage_info['file_path']}")
                    return True
                except S3Error as e:
                    utils.logger.error(f"删除MinIO文件失败: {e}")
                    return False
            
            return False
            
        except Exception as e:
            utils.logger.error(f"删除文件失败: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            "local_files": 0,
            "local_size": 0,
            "minio_files": 0,
            "minio_size": 0,
            "total_files": 0,
            "total_size": 0
        }
        
        try:
            # 统计本地文件
            for file_path in self.local_base_path.rglob("*"):
                if file_path.is_file():
                    stats["local_files"] += 1
                    stats["local_size"] += file_path.stat().st_size
            
            # 统计MinIO文件
            if self.minio_client:
                try:
                    objects = self.minio_client.list_objects(
                        bucket_name=self.minio_bucket,
                        recursive=True
                    )
                    for obj in objects:
                        stats["minio_files"] += 1
                        stats["minio_size"] += obj.size
                except S3Error as e:
                    utils.logger.error(f"获取MinIO统计失败: {e}")
            
            stats["total_files"] = stats["local_files"] + stats["minio_files"]
            stats["total_size"] = stats["local_size"] + stats["minio_size"]
            
        except Exception as e:
            utils.logger.error(f"获取存储统计失败: {e}")
        
        return stats


# 全局存储管理器实例
storage_manager = StorageManager() 