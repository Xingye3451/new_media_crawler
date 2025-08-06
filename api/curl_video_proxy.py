"""
Curl视频代理服务
使用curl命令模拟真实浏览器请求，绕过防盗链
"""

import subprocess
import os
import hashlib
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import logging
from urllib.parse import urlparse
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

router = APIRouter()

# 本地视频存储目录
VIDEO_CACHE_DIR = "data/video_cache"
os.makedirs(VIDEO_CACHE_DIR, exist_ok=True)

# 线程池执行器
executor = ThreadPoolExecutor(max_workers=4)

def get_video_filename(url: str) -> str:
    """根据URL生成文件名"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"{url_hash}.mp4"

def get_video_path(url: str) -> str:
    """获取视频本地路径"""
    filename = get_video_filename(url)
    return os.path.join(VIDEO_CACHE_DIR, filename)

def download_with_curl(url: str, file_path: str, is_video: bool = True):
    """使用curl下载文件"""
    try:
        # 构建curl命令，使用更简单但有效的方法
        curl_cmd = [
            'curl',
            '-L',  # 跟随重定向
            '-o', file_path,  # 输出文件
            '--compressed',  # 支持压缩
            '--retry', '3',  # 🆕 添加重试机制
            '--retry-delay', '1',  # 🆕 重试延迟1秒
            '--retry-max-time', '10',  # 🆕 最大重试时间10秒
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-H', 'Accept: */*' if is_video else 'image/webp,image/apng,image/*,*/*;q=0.8',
            '-H', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
            '-H', 'Accept-Encoding: gzip, deflate, br',
            '-H', 'Connection: keep-alive',
            '-H', 'Upgrade-Insecure-Requests: 1',
            '-H', 'Sec-Fetch-Dest: ' + ('video' if is_video else 'image'),
            '-H', 'Sec-Fetch-Mode: no-cors',
            '-H', 'Sec-Fetch-Site: cross-site',
        ]
        
        # 设置Referer - 这是关键
        if 'douyin' in url:
            curl_cmd.extend([
                '-H', 'Referer: https://www.douyin.com/',
                '-H', 'Origin: https://www.douyin.com',
            ])
        elif 'xiaohongshu' in url or 'xhscdn' in url:
            curl_cmd.extend([
                '-H', 'Referer: https://www.xiaohongshu.com/',
                '-H', 'Origin: https://www.xiaohongshu.com',
                '-H', 'X-Requested-With: XMLHttpRequest',
                '-H', 'Cache-Control: no-cache',
                '-H', 'Pragma: no-cache',
            ])
        else:
            parsed_url = urlparse(url)
            curl_cmd.extend(['-H', f'Referer: {parsed_url.scheme}://{parsed_url.netloc}/'])
        
        # 设置超时
        timeout = 30 if is_video else 10
        curl_cmd.extend(['--max-time', str(timeout)])
        
        # 添加URL
        curl_cmd.append(url)
        
        logger.info(f"开始使用curl下载{'视频' if is_video else '图片'}: {url}")
        
        # 执行curl命令
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        
        if result.returncode == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > (100 if is_video else 100):  # 确保文件大小合理
            logger.info(f"{'视频' if is_video else '图片'}下载完成: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
            return True
        else:
            logger.error(f"curl下载失败，返回码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr}")
            logger.error(f"标准输出: {result.stdout}")
            logger.error(f"文件存在: {os.path.exists(file_path)}")
            if os.path.exists(file_path):
                logger.error(f"文件大小: {os.path.getsize(file_path)} 字节")
                # 🆕 检查下载的文件内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(500)
                        if '403' in content or 'Forbidden' in content:
                            logger.error("下载的是403错误页面，不是视频文件")
                        elif '404' in content or 'Not Found' in content:
                            logger.error("下载的是404错误页面，文件不存在")
                        elif '500' in content or 'Internal Server Error' in content:
                            logger.error("下载的是500错误页面，服务器内部错误")
                        else:
                            logger.error(f"下载的内容前500字符: {content[:200]}...")
                except UnicodeDecodeError:
                    # 如果文件是二进制文件，检查文件头
                    with open(file_path, 'rb') as f:
                        header = f.read(20)
                        if header.startswith(b'<!DOCTYPE') or header.startswith(b'<html'):
                            logger.error("下载的是HTML页面，不是视频文件")
                        elif header.startswith(b'\xff\xd8\xff'):  # JPEG文件头
                            logger.info("下载的是有效的JPEG图片")
                        elif header.startswith(b'\x89PNG'):  # PNG文件头
                            logger.info("下载的是有效的PNG图片")
                        else:
                            logger.error(f"未知的文件格式，文件头: {header.hex()}")
            return False
            
    except Exception as e:
        logger.error(f"curl下载异常: {str(e)}")
        return False

@router.get("/curl-proxy/video")
async def curl_proxy_video(
    url: str,
    force_download: bool = False
):
    """
    使用curl代理视频
    
    Args:
        url: 视频URL
        force_download: 是否强制重新下载
    """
    try:
        # 验证URL
        if not url or not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        video_path = get_video_path(url)
        
        # 检查本地是否已有文件
        if os.path.exists(video_path) and not force_download:
            logger.info(f"使用本地缓存视频: {video_path}")
            return FileResponse(
                video_path,
                media_type='video/mp4',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': '*',
                    'Cache-Control': 'public, max-age=86400',
                }
            )
        
        # 在线程池中执行下载
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            executor, 
            download_with_curl, 
            url, 
            video_path, 
            True
        )
        
        if success:
            return FileResponse(
                video_path,
                media_type='video/mp4',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': '*',
                    'Cache-Control': 'public, max-age=86400',
                }
            )
        else:
            raise HTTPException(status_code=500, detail="视频下载失败")
        
    except Exception as e:
        logger.error(f"Curl视频代理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Curl视频代理失败: {str(e)}")

@router.get("/curl-proxy/thumbnail")
async def curl_proxy_thumbnail(
    url: str,
    force_download: bool = False
):
    """
    使用curl代理缩略图
    """
    try:
        # 验证URL
        if not url or not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的缩略图URL")
        
        # 生成缩略图文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()
        thumbnail_path = os.path.join(VIDEO_CACHE_DIR, f"{url_hash}.jpg")
        
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
        
        # 在线程池中执行下载
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            executor, 
            download_with_curl, 
            url, 
            thumbnail_path, 
            False
        )
        
        if success:
            # 检查文件是否存在且大小合理
            if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 100:
                logger.info(f"缩略图代理成功: {thumbnail_path}, 大小: {os.path.getsize(thumbnail_path)} 字节")
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
                file_size = os.path.getsize(thumbnail_path) if os.path.exists(thumbnail_path) else 0
                logger.error(f"缩略图文件无效: {thumbnail_path}, 大小: {file_size} 字节")
                # 🆕 提供更详细的错误信息
                error_detail = f"缩略图文件无效，大小: {file_size} 字节"
                if file_size < 100:
                    error_detail += "，文件太小，可能是错误页面"
                raise HTTPException(status_code=500, detail=error_detail)
        else:
            logger.error(f"缩略图下载失败: {url}")
            # 🆕 提供更详细的错误信息
            raise HTTPException(status_code=500, detail=f"缩略图下载失败: {url}")
        
    except Exception as e:
        logger.error(f"Curl缩略图代理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Curl缩略图代理失败: {str(e)}")

@router.get("/curl-proxy/status")
async def get_curl_proxy_status():
    """获取Curl代理状态"""
    try:
        # 统计缓存文件
        cache_files = os.listdir(VIDEO_CACHE_DIR)
        video_files = [f for f in cache_files if f.endswith('.mp4')]
        image_files = [f for f in cache_files if f.endswith(('.jpg', '.png', '.webp'))]
        
        # 计算总大小
        total_size = 0
        for file in cache_files:
            file_path = os.path.join(VIDEO_CACHE_DIR, file)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
        
        return {
            "cache_dir": VIDEO_CACHE_DIR,
            "video_count": len(video_files),
            "image_count": len(image_files),
            "total_files": len(cache_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "status": "ready",
            "method": "curl-command"
        }
        
    except Exception as e:
        logger.error(f"获取Curl代理状态失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.delete("/curl-proxy/clear")
async def clear_curl_proxy_cache():
    """清理Curl代理缓存"""
    try:
        cache_files = os.listdir(VIDEO_CACHE_DIR)
        deleted_count = 0
        
        for file in cache_files:
            file_path = os.path.join(VIDEO_CACHE_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1
        
        return {
            "message": "Curl代理缓存清理完成",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"清理Curl代理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理Curl代理缓存失败: {str(e)}") 