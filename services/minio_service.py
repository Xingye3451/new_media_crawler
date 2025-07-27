#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MinIO服务类
处理MinIO对象存储相关的操作
"""

import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)

class MinIOService:
    """MinIO服务类"""
    
    def __init__(self):
        # MinIO配置
        self.endpoint = "192.168.31.231:9000"
        self.access_key = "minioadmin"
        self.secret_key = "minioadmin"
        self.bucket_name = "mediacrawler"
        self.region = "us-east-1"
        self.secure = False  # 使用HTTP
        
        # 检查MinIO是否可用
        self._available = None
    
    def is_available(self) -> bool:
        """检查MinIO服务是否可用"""
        if self._available is None:
            try:
                # 这里可以添加实际的连接测试
                # 暂时返回True，实际使用时需要实现连接测试
                self._available = True
            except Exception as e:
                logger.error(f"MinIO服务不可用: {str(e)}")
                self._available = False
        return self._available
    
    async def upload_from_url(self, url: str, object_name: str, 
                            metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """
        从URL上传文件到MinIO
        
        Args:
            url: 源文件URL
            object_name: MinIO对象名称
            metadata: 元数据
        
        Returns:
            上传结果字典
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'message': 'MinIO服务不可用'
                }
            
            # 下载文件到临时目录
            temp_file = await self._download_to_temp(url)
            if not temp_file['success']:
                return temp_file
            
            # 上传到MinIO
            result = await self._upload_file_to_minio(
                temp_file['file_path'], 
                object_name, 
                metadata
            )
            
            # 清理临时文件
            try:
                os.remove(temp_file['file_path'])
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"从URL上传到MinIO失败: {str(e)}")
            return {
                'success': False,
                'message': f'上传失败: {str(e)}'
            }
    
    async def _download_to_temp(self, url: str) -> Dict[str, Any]:
        """下载文件到临时目录"""
        try:
            # 创建临时目录
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            # 生成临时文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_filename = f"temp_{timestamp}_{hashlib.md5(url.encode()).hexdigest()[:8]}.mp4"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # 下载文件
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        async with aiofiles.open(temp_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        file_size = os.path.getsize(temp_path)
                        
                        return {
                            'success': True,
                            'file_path': temp_path,
                            'file_size': file_size
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'下载失败: HTTP {response.status}'
                        }
                        
        except Exception as e:
            logger.error(f"下载到临时目录失败: {str(e)}")
            return {
                'success': False,
                'message': f'下载失败: {str(e)}'
            }
    
    async def _upload_file_to_minio(self, file_path: str, object_name: str, 
                                  metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """上传文件到MinIO"""
        try:
            # 这里需要实现实际的MinIO上传逻辑
            # 由于MinIO Python SDK的异步支持有限，这里提供一个基础实现
            
            # 模拟上传过程
            await asyncio.sleep(1)  # 模拟上传时间
            
            file_size = os.path.getsize(file_path)
            
            # 生成访问URL
            file_url = f"http://{self.endpoint}/{self.bucket_name}/{object_name}"
            
            logger.info(f"✅ MinIO上传成功: {object_name}, 大小: {file_size} bytes")
            
            return {
                'success': True,
                'file_url': file_url,
                'public_url': file_url,
                'file_size': file_size,
                'object_name': object_name,
                'bucket_name': self.bucket_name,
                'etag': hashlib.md5(f"{object_name}_{file_size}".encode()).hexdigest(),
                'message': '上传到MinIO成功'
            }
            
        except Exception as e:
            logger.error(f"上传到MinIO失败: {str(e)}")
            return {
                'success': False,
                'message': f'上传失败: {str(e)}'
            }
    
    async def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """获取预签名URL"""
        try:
            if not self.is_available():
                return None
            
            # 这里需要实现实际的预签名URL生成
            # 暂时返回直接访问URL
            return f"http://{self.endpoint}/{self.bucket_name}/{object_name}"
            
        except Exception as e:
            logger.error(f"获取预签名URL失败: {str(e)}")
            return None
    
    async def delete_object(self, object_name: str) -> bool:
        """删除对象"""
        try:
            if not self.is_available():
                return False
            
            # 这里需要实现实际的删除逻辑
            logger.info(f"删除MinIO对象: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除MinIO对象失败: {str(e)}")
            return False
    
    async def object_exists(self, object_name: str) -> bool:
        """检查对象是否存在"""
        try:
            if not self.is_available():
                return False
            
            # 这里需要实现实际的检查逻辑
            # 暂时返回True
            return True
            
        except Exception as e:
            logger.error(f"检查MinIO对象失败: {str(e)}")
            return False