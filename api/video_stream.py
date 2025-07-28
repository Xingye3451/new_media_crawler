"""
视频流API路由
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, FileResponse
from typing import Dict, Any
import logging
import os
import aiofiles

from services.video_stream_service import VideoStreamService

logger = logging.getLogger(__name__)

router = APIRouter()
stream_service = VideoStreamService()

@router.get("/stream/video", response_model=Dict[str, Any])
async def get_stream_info(
    video_url: str = Query(..., description="视频URL"),
    platform: str = Query(..., description="平台"),
    content_id: str = Query(..., description="内容ID")
):
    """获取视频流信息"""
    try:
        result = await stream_service.stream_video(video_url, platform, content_id)
        
        if result["success"]:
            return {
                "code": 200,
                "message": "获取成功",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取流信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.get("/stream/cache/{cache_key}")
async def stream_cache_video(cache_key: str):
    """流式播放缓存视频"""
    try:
        cache_file = os.path.join(stream_service.cache_dir, f"{cache_key}.mp4")
        
        if not os.path.exists(cache_file):
            raise HTTPException(status_code=404, detail="缓存文件不存在")
        
        # 返回文件流
        return FileResponse(
            cache_file,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式播放缓存失败 {cache_key}: {str(e)}")
        raise HTTPException(status_code=500, detail="播放失败")

@router.get("/stream/local/{file_hash}")
async def stream_local_video(file_hash: str):
    """流式播放本地视频"""
    try:
        # 从数据库获取文件记录
        from services.video_favorite_service import VideoFavoriteService
        favorite_service = VideoFavoriteService()
        
        file_record = await favorite_service._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件记录不存在")
        
        local_path = file_record.get("local_path")
        if not local_path or not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="本地文件不存在")
        
        # 返回文件流
        return FileResponse(
            local_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式播放本地视频失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="播放失败")

@router.get("/stream/direct")
async def stream_direct_video(
    video_url: str = Query(..., description="视频URL"),
    platform: str = Query(..., description="平台")
):
    """直接流式传输视频"""
    try:
        import aiohttp
        import urllib.parse
        
        # URL解码
        decoded_url = urllib.parse.unquote(video_url)
        logger.info(f"开始直接流式传输: {decoded_url}, 平台: {platform}")
        
        # 根据平台设置不同的请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }
        
        # 根据平台设置不同的Referer
        if platform == "xhs":
            headers.update({
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com"
            })
            logger.info(f"识别为小红书平台: {platform}")
        elif platform == "dy":
            headers.update({
                "Referer": "https://www.douyin.com/",
                "Origin": "https://www.douyin.com"
            })
            logger.info(f"识别为抖音平台: {platform}")
        elif platform == "ks":
            headers.update({
                "Referer": "https://www.kuaishou.com/",
                "Origin": "https://www.kuaishou.com"
            })
            logger.info(f"识别为快手平台: {platform}")
        elif platform == "bili":
            headers.update({
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com"
            })
            logger.info(f"识别为B站平台: {platform}")
        elif platform == "wb":
            headers.update({
                "Referer": "https://weibo.com/",
                "Origin": "https://weibo.com"
            })
            logger.info(f"识别为微博平台: {platform}")
        elif platform == "zhihu":
            headers.update({
                "Referer": "https://www.zhihu.com/",
                "Origin": "https://www.zhihu.com"
            })
            logger.info(f"识别为知乎平台: {platform}")
        else:
            # 默认使用Google的Referer
            headers.update({
                "Referer": "https://www.google.com/",
                "Origin": "https://www.google.com"
            })
            logger.info(f"使用默认Referer，平台: {platform}")
        
        async def video_stream():
            """视频流生成器"""
            async with aiohttp.ClientSession() as session:
                async with session.get(decoded_url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"开始流式传输视频，状态码: {response.status}")
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    else:
                        logger.error(f"视频下载失败，状态码: {response.status}")
                        yield b""
        
        return StreamingResponse(
            video_stream(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"直接流式传输失败 {video_url}: {str(e)}")
        raise HTTPException(status_code=500, detail="流式传输失败")

@router.get("/stream/cache-info")
async def get_cache_info():
    """获取缓存信息"""
    try:
        info = await stream_service.get_cache_info()
        return {
            "code": 200,
            "message": "获取成功",
            "data": info
        }
    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.post("/stream/cleanup")
async def cleanup_cache():
    """清理过期缓存"""
    try:
        await stream_service.cleanup_expired_cache()
        return {
            "code": 200,
            "message": "清理完成",
            "data": {"cleaned": True}
        }
    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清理失败") 