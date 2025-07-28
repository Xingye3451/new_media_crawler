"""
MinIO Client
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
    """MinIO Client"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize MinIO client"""
        try:
            # Load MinIO config from environment config file
            from config.env_config_loader import config_loader
            
            config = config_loader.load_config()
            storage_config = config.get('storage', {})
            
            # Get MinIO configuration
            endpoint = storage_config.get('minio_endpoint', '192.168.31.231:9000')
            access_key = storage_config.get('minio_access_key', 'minioadmin')
            secret_key = storage_config.get('minio_secret_key', 'minioadmin')
            secure = storage_config.get('minio_secure', False)
            bucket = storage_config.get('minio_bucket', 'mediacrawler-videos')
            
            self.bucket_name = bucket
            
            self.client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            logger.info(f"MinIO client initialized successfully: {endpoint}, bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"MinIO client initialization failed: {str(e)}")
            # Use default configuration as fallback
            try:
                self.client = Minio(
                    endpoint='192.168.31.231:9000',
                    access_key='minioadmin',
                    secret_key='minioadmin',
                    secure=False
                )
                self.bucket_name = 'mediacrawler-videos'
                logger.info("Using default MinIO configuration")
            except Exception as fallback_e:
                logger.error(f"Default MinIO configuration also failed: {str(fallback_e)}")
            self.client = None
    
    async def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> Dict[str, Any]:
        """
        Upload file to MinIO
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
            file_path: Local file path
        
        Returns:
            Dict: Upload result
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO client not initialized"}
            
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            
            # Upload file
            self.client.fput_object(bucket_name, object_name, file_path)
            
            logger.info(f"File uploaded successfully: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "url": f"http://{self.client._base_url.host}/{bucket_name}/{object_name}"
            }
            
        except S3Error as e:
            logger.error(f"MinIO upload failed: {str(e)}")
            return {"success": False, "error": f"MinIO error: {str(e)}"}
        except Exception as e:
            logger.error(f"Upload file failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def upload_data(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "video/mp4") -> Dict[str, Any]:
        """
        Upload data stream to MinIO
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
            data: Data content
            content_type: Content type
        
        Returns:
            Dict: Upload result
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO client not initialized"}
            
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            
            # Upload data
            from io import BytesIO
            data_stream = BytesIO(data)
            
            self.client.put_object(
                bucket_name,
                object_name,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            
            logger.info(f"Data uploaded successfully: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "url": f"http://{self.client._base_url.host}/{bucket_name}/{object_name}"
            }
            
        except S3Error as e:
            logger.error(f"MinIO upload failed: {str(e)}")
            return {"success": False, "error": f"MinIO error: {str(e)}"}
        except Exception as e:
            logger.error(f"Upload data failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def download_file(self, bucket_name: str, object_name: str, file_path: str) -> Dict[str, Any]:
        """
        Download file from MinIO
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
            file_path: Local file path
        
        Returns:
            Dict: Download result
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO client not initialized"}
            
            # Download file
            self.client.fget_object(bucket_name, object_name, file_path)
            
            logger.info(f"File downloaded successfully: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "local_path": file_path
            }
            
        except S3Error as e:
            logger.error(f"MinIO download failed: {str(e)}")
            return {"success": False, "error": f"MinIO error: {str(e)}"}
        except Exception as e:
            logger.error(f"Download file failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_object(self, bucket_name: str, object_name: str) -> Dict[str, Any]:
        """
        Delete object from MinIO
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
        
        Returns:
            Dict: Delete result
        """
        try:
            if not self.client:
                return {"success": False, "error": "MinIO client not initialized"}
            
            # Delete object
            self.client.remove_object(bucket_name, object_name)
            
            logger.info(f"Object deleted successfully: {bucket_name}/{object_name}")
            
            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name
            }
            
        except S3Error as e:
            logger.error(f"MinIO delete failed: {str(e)}")
            return {"success": False, "error": f"MinIO error: {str(e)}"}
        except Exception as e:
            logger.error(f"Delete object failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_presigned_url(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """
        Get presigned URL for object
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
            expires: Expiration time in seconds
        
        Returns:
            str: Presigned URL
        """
        try:
            if not self.client:
                return ""
            
            # Generate presigned URL
            from datetime import timedelta
            url = self.client.presigned_get_object(bucket_name, object_name, expires=timedelta(seconds=expires))
            
            logger.info(f"Generated presigned URL: {bucket_name}/{object_name}")
            
            return url
            
        except Exception as e:
            logger.error(f"Generate presigned URL failed: {str(e)}")
            return ""
    
    async def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        Check if object exists
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
        
        Returns:
            bool: True if object exists
        """
        try:
            if not self.client:
                return False
            
            # Check if object exists
            self.client.stat_object(bucket_name, object_name)
            return True
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            else:
                logger.error(f"Check object existence failed: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Check object existence failed: {str(e)}")
            return False
    
    async def get_object_info(self, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get object information
        
        Args:
            bucket_name: Bucket name
            object_name: Object name
        
        Returns:
            Optional[Dict]: Object information
        """
        try:
            if not self.client:
                return None
            
            # Get object info
            stat = self.client.stat_object(bucket_name, object_name)
            
            return {
                "bucket": bucket_name,
                "object": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type
            }
            
        except S3Error as e:
            logger.error(f"Get object info failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Get object info failed: {str(e)}")
            return None 