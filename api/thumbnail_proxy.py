"""
缩略图代理服务
使用Python requests库直接下载缩略图
"""

import requests
import hashlib
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 缩略图缓存目录
THUMBNAIL_CACHE_DIR = "data/thumbnail_cache"
os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)

def get_thumbnail_filename(url: str) -> str:
    """根据URL生成缩略图文件名"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"{url_hash}.jpg"

def get_thumbnail_path(url: str) -> str:
    """获取缩略图本地路径"""
    filename = get_thumbnail_filename(url)
    return os.path.join(THUMBNAIL_CACHE_DIR, filename)

def download_thumbnail(url: str) -> bool:
    """下载缩略图"""
    try:
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        
        # 根据URL设置Referer
        if 'xiaohongshu' in url or 'xhscdn' in url:
            headers['Referer'] = 'https://www.xiaohongshu.com/'
            headers['Origin'] = 'https://www.xiaohongshu.com'
        elif 'douyin' in url:
            headers['Referer'] = 'https://www.douyin.com/'
            headers['Origin'] = 'https://www.douyin.com'
        else:
            parsed_url = urlparse(url)
            headers['Referer'] = f'{parsed_url.scheme}://{parsed_url.netloc}/'
        
        logger.info(f"开始下载缩略图: {url}")
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # 保存文件
            file_path = get_thumbnail_path(url)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 检查文件大小
            if os.path.exists(file_path) and os.path.getsize(file_path) > 100:
                logger.info(f"缩略图下载成功: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
                return True
            else:
                logger.error(f"缩略图文件无效: {file_path}")
                return False
        else:
            logger.error(f"缩略图下载失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"缩略图下载异常: {str(e)}")
        return False

@router.get("/thumbnail-proxy")
async def thumbnail_proxy(url: str, force_download: bool = False):
    """
    缩略图代理
    """
    try:
        # 验证URL
        if not url or not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的缩略图URL")
        
        # 生成缩略图路径
        thumbnail_path = get_thumbnail_path(url)
        
        # 检查本地是否已有文件
        if os.path.exists(thumbnail_path) and not force_download:
            logger.info(f"使用本地缓存缩略图: {thumbnail_path}")
            return FileResponse(
                thumbnail_path,
                media_type='image/jpeg',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': '*',
                    'Cache-Control': 'public, max-age=86400',
                }
            )
        
        # 下载缩略图
        success = download_thumbnail(url)
        
        if success:
            return FileResponse(
                thumbnail_path,
                media_type='image/jpeg',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': '*',
                    'Cache-Control': 'public, max-age=86400',
                }
            )
        else:
            raise HTTPException(status_code=500, detail="缩略图下载失败")
        
    except Exception as e:
        logger.error(f"缩略图代理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"缩略图代理失败: {str(e)}") 