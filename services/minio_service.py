"""
MinIO服务层
处理对象存储相关的业务逻辑
"""

import os
import asyncio
import aiofiles
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse
import hashlib
import json
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from config.config_manager import config_manager

logger = logging.getLogger(__name__)

class MinIOService:
    """MinIO服务层"""
    
    def __init__(self):
        self.storage_config = config_manager.get_storage_config()
        self.bucket_name = self.storage_config.minio_bucket
        self.client = None
        self.max_local_size = self.storage_config.small_file_threshold
        self._init_client()
    
    def _init_client(self):
        """初始化MinIO客户端"""
        try:
            # 从配置管理器获取MinIO配置
            if not self.storage_config.enable_minio:
                logger.info("MinIO未启用，跳过初始化")
                return
            
            minio_config = {
                'endpoint': self.storage_config.minio_endpoint,
                'access_key': self.storage_config.minio_access_key,
                'secret_key': self.storage_config.minio_secret_key,
                'secure': self.storage_config.minio_secure
            }
            
            self.client = Minio(
                minio_config['endpoint'],
                access_key=minio_config['access_key'],
                secret_key=minio_config['secret_key'],
                secure=minio_config['secure']
            )
            
            # 确保桶存在
            self._ensure_bucket_exists()
            logger.info(f"✅ MinIO客户端初始化成功 - 桶: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ MinIO客户端初始化失败: {str(e)}")
            self.client = None
    
    def _ensure_bucket_exists(self):
        """确保桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"📁 创建MinIO桶: {self.bucket_name}")
        except Exception as e:
            logger.error(f"创建桶失败: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """检查MinIO是否可用"""
        return self.client is not None
    
    async def upload_file(self, file_path: str, object_name: str = None, 
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        上传文件到MinIO
        
        Args:
            file_path: 本地文件路径
            object_name: 对象名称（可选）
            metadata: 元数据（可选）
        
        Returns:
            上传结果字典
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'message': 'MinIO服务不可用'
                }
            
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': '文件不存在'
                }
            
            # 生成对象名称
            if not object_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.basename(file_path)
                object_name = f"videos/{timestamp}_{filename}"
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_stat = os.stat(file_path)
            
            # 准备元数据
            upload_metadata = {
                'upload_time': datetime.now().isoformat(),
                'file_size': str(file_size),
                'original_name': os.path.basename(file_path)
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # 上传文件
            with open(file_path, 'rb') as file_data:
                result = self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=file_size,
                    metadata=upload_metadata
                )
            
            # 生成访问URL
            file_url = f"minio://{self.bucket_name}/{object_name}"
            public_url = self.get_presigned_url(object_name, expires=timedelta(days=7))
            
            logger.info(f"📤 文件上传成功: {object_name} ({file_size} bytes)")
            
            return {
                'success': True,
                'object_name': object_name,
                'file_url': file_url,
                'public_url': public_url,
                'file_size': file_size,
                'bucket_name': self.bucket_name,
                'etag': result.etag,
                'message': '上传成功'
            }
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {str(e)}")
            return {
                'success': False,
                'message': f'MinIO上传失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"上传文件失败: {str(e)}")
            return {
                'success': False,
                'message': f'上传失败: {str(e)}'
            }
    
    async def upload_from_url(self, url: str, object_name: str = None, 
                             metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        从URL下载并上传到MinIO
        
        Args:
            url: 下载URL
            object_name: 对象名称（可选）
            metadata: 元数据（可选）
        
        Returns:
            上传结果字典
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'message': 'MinIO服务不可用'
                }
            
            # 动态导入以避免循环依赖
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'message': f'下载失败: HTTP {response.status}'
                        }
                    
                    # 获取文件信息
                    content_length = int(response.headers.get('content-length', 0))
                    content_type = response.headers.get('content-type', 'application/octet-stream')
                    
                    # 生成对象名称
                    if not object_name:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        # 从URL提取文件名
                        parsed = urlparse(url)
                        filename = os.path.basename(parsed.path) or f"video_{timestamp}"
                        if not filename.endswith('.mp4'):
                            filename += '.mp4'
                        object_name = f"videos/{timestamp}_{filename}"
                    
                    # 准备元数据
                    upload_metadata = {
                        'upload_time': datetime.now().isoformat(),
                        'source_url': url,
                        'content_type': content_type,
                        'file_size': str(content_length)
                    }
                    
                    if metadata:
                        upload_metadata.update(metadata)
                    
                    # 读取数据并上传
                    data = await response.read()
                    data_stream = BytesIO(data)
                    
                    result = self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=object_name,
                        data=data_stream,
                        length=len(data),
                        content_type=content_type,
                        metadata=upload_metadata
                    )
                    
                    # 生成访问URL
                    file_url = f"minio://{self.bucket_name}/{object_name}"
                    public_url = self.get_presigned_url(object_name, expires=timedelta(days=7))
                    
                    logger.info(f"📤 从URL上传成功: {object_name} ({len(data)} bytes)")
                    
                    return {
                        'success': True,
                        'object_name': object_name,
                        'file_url': file_url,
                        'public_url': public_url,
                        'file_size': len(data),
                        'bucket_name': self.bucket_name,
                        'etag': result.etag,
                        'message': '上传成功'
                    }
                    
        except Exception as e:
            logger.error(f"从URL上传失败: {str(e)}")
            return {
                'success': False,
                'message': f'从URL上传失败: {str(e)}'
            }
    
    def get_presigned_url(self, object_name: str, expires: timedelta = None) -> str:
        """获取预签名URL"""
        try:
            if not self.is_available():
                return ""
            
            if expires is None:
                expires = timedelta(hours=1)
            
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            
            return url
            
        except Exception as e:
            logger.error(f"获取预签名URL失败: {str(e)}")
            return ""
    
    def delete_object(self, object_name: str) -> bool:
        """删除对象"""
        try:
            if not self.is_available():
                return False
            
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            logger.info(f"🗑️ 删除对象成功: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除对象失败: {str(e)}")
            return False
    
    def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """获取对象信息"""
        try:
            if not self.is_available():
                return None
            
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            return {
                'object_name': object_name,
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }
            
        except Exception as e:
            logger.error(f"获取对象信息失败: {str(e)}")
            return None
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """列出对象"""
        try:
            if not self.is_available():
                return []
            
            objects = []
            for obj in self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            ):
                objects.append({
                    'object_name': obj.object_name,
                    'size': obj.size,
                    'etag': obj.etag,
                    'last_modified': obj.last_modified,
                    'content_type': obj.content_type
                })
                
                if len(objects) >= max_keys:
                    break
            
            return objects
            
        except Exception as e:
            logger.error(f"列出对象失败: {str(e)}")
            return []
    
    def get_bucket_statistics(self) -> Dict[str, Any]:
        """获取桶统计信息"""
        try:
            if not self.is_available():
                return {
                    'available': False,
                    'message': 'MinIO服务不可用'
                }
            
            objects = self.list_objects()
            total_size = sum(obj['size'] for obj in objects)
            
            # 按类型分类
            video_count = 0
            other_count = 0
            
            for obj in objects:
                if obj['object_name'].startswith('videos/'):
                    video_count += 1
                else:
                    other_count += 1
            
            return {
                'available': True,
                'bucket_name': self.bucket_name,
                'total_objects': len(objects),
                'total_size': total_size,
                'video_count': video_count,
                'other_count': other_count,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取桶统计失败: {str(e)}")
            return {
                'available': False,
                'message': f'获取统计失败: {str(e)}'
            }
    
    def cleanup_expired_objects(self, days: int = 30) -> int:
        """清理过期对象"""
        try:
            if not self.is_available():
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for obj in self.client.list_objects(
                bucket_name=self.bucket_name,
                recursive=True
            ):
                if obj.last_modified < cutoff_date:
                    try:
                        self.client.remove_object(
                            bucket_name=self.bucket_name,
                            object_name=obj.object_name
                        )
                        deleted_count += 1
                        logger.info(f"🧹 清理过期对象: {obj.object_name}")
                    except Exception as e:
                        logger.error(f"清理对象失败 {obj.object_name}: {str(e)}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理过期对象失败: {str(e)}")
            return 0 