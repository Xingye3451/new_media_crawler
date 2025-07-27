"""
视频下载API路由
"""

from fastapi import APIRouter, HTTPException, Query, Form
from typing import Dict, Any, List
import logging
from pydantic import BaseModel
from datetime import datetime

from services.video_download_service import VideoDownloadService

logger = logging.getLogger(__name__)

router = APIRouter()
download_service = VideoDownloadService()

class VideoDownloadRequest(BaseModel):
    video_url: str
    video_id: str
    platform: str
    download_type: str = "local"  # local 或 server

@router.post("/videos/download")
async def download_video(request: VideoDownloadRequest):
    """下载视频到用户本地"""
    try:
        # 直接返回文件流，让浏览器下载
        from fastapi.responses import StreamingResponse
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
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{request.platform}_{request.video_id}_{timestamp}.mp4"
        
        async def video_stream():
            async with aiohttp.ClientSession() as session:
                async with session.get(request.video_url, headers=headers) as response:
                    if response.status == 200:
                        # 流式传输视频数据
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    else:
                        raise HTTPException(status_code=response.status, detail="视频下载失败")
        
        return StreamingResponse(
            video_stream(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Accept-Ranges": "bytes"
            }
        )
        
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail="下载视频失败")



@router.get("/downloads/statistics", response_model=Dict[str, Any])
async def get_download_statistics():
    """获取下载统计信息"""
    try:
        results = await download_service.get_download_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取下载统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取下载统计失败") 