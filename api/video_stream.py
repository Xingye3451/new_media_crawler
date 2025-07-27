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