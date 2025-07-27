"""
MinIO客户端工具类
"""

import asyncio
import os
import yaml
from typing import Optional, Dict, Any
import logging
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

class MinioClient:
    """MinIO客户端"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化MinIO客户端"""
        try:
            # 从配置文件读取MinIO配置
            config_path = "config/config_storage.yaml"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                storage_config = config.get('storage', {})
                endpoint = storage_config.get('minio_endpoint', '192.168.31.231:9000')
                access_key = storage_config.get('minio_access_key', 'minioadmin')
                secret_key = storage_config.get('minio_secret_key', 'minioadmin')
                secure = storage_config.get('minio_secure', False)
                bucket = storage_config.get('minio_bucket', 'mediacrawler-videos')
                
                self.bucket_name = bucket
            else:
                # 使用默认配置
                endpoint = '192.168.31.231:9000'
                access_key = 'minioadmin'
                secret_key = 'minioadmin'
                secure = False
                self.bucket_name = 'mediacrawler-videos'
            
            self.client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            logger.info(f"MinIO客户端初始化成功: {endpoint}, 桶: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"MinIO客户端初始化失败: {str(e)}")
            self.client = None
    
    async def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> Dict[str, Any]:
        """
        上传文件到MinIO
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
            file_path: 本地文件路径
        
        Returns:
            Dict: 上传结果
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO客户端未初始化"}
            
            # 确保桶存在
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"创建桶: {bucket_name}")
            
            # 上传文件
            self.client.fput_object(bucket_name, object_name, file_path)
            
            logger.info(f"文件上传成功: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "url": f"http://{self.client._base_url.host}/{bucket_name}/{object_name}"
            }
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {str(e)}")
            return {"success": False, "error": f"MinIO错误: {str(e)}"}
        except Exception as e:
            logger.error(f"上传文件失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def upload_data(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "video/mp4") -> Dict[str, Any]:
        """
        上传数据流到MinIO
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
            data: 数据内容
            content_type: 内容类型
        
        Returns:
            Dict: 上传结果
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO客户端未初始化"}
            
            # 确保桶存在
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"创建桶: {bucket_name}")
            
            # 上传数据
            from io import BytesIO
            data_stream = BytesIO(data)
            self.client.put_object(bucket_name, object_name, data_stream, length=len(data), content_type=content_type)
            
            logger.info(f"数据上传成功: {bucket_name}/{object_name}, 大小: {len(data)} bytes")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "size": len(data),
                "url": f"http://{self.client._base_url.host}/{bucket_name}/{object_name}"
            }
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {str(e)}")
            return {"success": False, "error": f"MinIO错误: {str(e)}"}
        except Exception as e:
            logger.error(f"上传数据失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def download_file(self, bucket_name: str, object_name: str, file_path: str) -> Dict[str, Any]:
        """
        从MinIO下载文件
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
            file_path: 本地文件路径
        
        Returns:
            Dict: 下载结果
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO客户端未初始化"}
            
            # 下载文件
            self.client.fget_object(bucket_name, object_name, file_path)
            
            logger.info(f"文件下载成功: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            }
            
        except S3Error as e:
            logger.error(f"MinIO下载失败: {str(e)}")
            return {"success": False, "error": f"MinIO错误: {str(e)}"}
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_object(self, bucket_name: str, object_name: str) -> Dict[str, Any]:
        """
        删除MinIO对象
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
        
        Returns:
            Dict: 删除结果
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO客户端未初始化"}
            
            # 删除对象
            self.client.remove_object(bucket_name, object_name)
            
            logger.info(f"对象删除成功: {bucket_name}/{object_name}")
            
            return {"success": True}
            
        except S3Error as e:
            logger.error(f"MinIO删除失败: {str(e)}")
            return {"success": False, "error": f"MinIO错误: {str(e)}"}
        except Exception as e:
            logger.error(f"删除对象失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_presigned_url(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """
        获取预签名URL
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
            expires: 过期时间（秒）
        
        Returns:
            str: 预签名URL
        """
        try:
            if not self.client:
                return ""
            
            # 生成预签名URL - 使用timedelta对象
            from datetime import timedelta
            expires_timedelta = timedelta(seconds=expires)
            url = self.client.presigned_get_object(bucket_name, object_name, expires=expires_timedelta)
            
            logger.info(f"生成预签名URL: {bucket_name}/{object_name}")
            
            return url
            
        except S3Error as e:
            logger.error(f"生成预签名URL失败: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"生成预签名URL失败: {str(e)}")
            return ""
    
    async def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        检查对象是否存在
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
        
        Returns:
            bool: 是否存在
        """
        try:
            if not self.client:
                return False
            
            # 检查对象是否存在
            self.client.stat_object(bucket_name, object_name)
            return True
            
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"检查对象存在失败: {str(e)}")
            return False
    
    async def get_object_info(self, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        """
        获取对象信息
        
        Args:
            bucket_name: 桶名
            object_name: 对象名
        
        Returns:
            Dict: 对象信息
        """
        try:
            if not self.client:
                return None
            
            # 获取对象信息
            stat = self.client.stat_object(bucket_name, object_name)
            
            return {
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type
            }
            
        except S3Error as e:
            logger.error(f"获取对象信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取对象信息失败: {str(e)}")
            return None 