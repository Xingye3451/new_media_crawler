#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
B站视频URL测试API
用于测试视频URL的可访问性和处理403错误
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio
from services.bilibili_video_service import bilibili_video_service
from tools import utils

router = APIRouter(prefix="/api/bilibili", tags=["B站视频测试"])


class VideoUrlTestRequest(BaseModel):
    """视频URL测试请求"""
    video_url: str
    use_proxy: bool = False
    proxy_config: Optional[Dict] = None


class VideoUrlTestResponse(BaseModel):
    """视频URL测试响应"""
    original_url: str
    processed_url: Optional[str]
    accessible: bool
    status_code: Optional[int]
    error_message: Optional[str]
    video_info: Dict


@router.post("/test-video-url")
async def test_video_url(request: VideoUrlTestRequest):
    """
    测试B站视频URL的可访问性
    """
    try:
        utils.logger.info(f"[BilibiliVideoTest] 开始测试视频URL: {request.video_url}")
        
        # 获取视频信息
        video_info = await bilibili_video_service.get_video_info(request.video_url)
        
        # 尝试处理URL
        processed_url = None
        if video_info.get("accessible"):
            processed_url = await bilibili_video_service.get_video_url_with_retry(
                request.video_url, 
                max_retries=3
            )
        
        response = VideoUrlTestResponse(
            original_url=request.video_url,
            processed_url=processed_url,
            accessible=video_info.get("accessible", False),
            status_code=video_info.get("status_code"),
            error_message=video_info.get("error"),
            video_info=video_info
        )
        
        utils.logger.info(f"[BilibiliVideoTest] 测试完成 - 可访问: {response.accessible}")
        return response
        
    except Exception as e:
        utils.logger.error(f"[BilibiliVideoTest] 测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/download-video")
async def download_video(request: VideoUrlTestRequest):
    """
    下载B站视频（测试用）
    """
    try:
        utils.logger.info(f"[BilibiliVideoTest] 开始下载视频: {request.video_url}")
        
        # 处理视频URL
        processed_url = await bilibili_video_service.get_video_url_with_retry(
            request.video_url, 
            max_retries=3
        )
        
        if not processed_url:
            raise HTTPException(status_code=400, detail="无法获取有效的视频URL")
        
        # 下载视频
        video_content = await bilibili_video_service.download_video_with_proxy(
            processed_url, 
            request.proxy_config
        )
        
        if video_content:
            return {
                "success": True,
                "original_url": request.video_url,
                "processed_url": processed_url,
                "content_size": len(video_content),
                "message": "视频下载成功"
            }
        else:
            return {
                "success": False,
                "original_url": request.video_url,
                "processed_url": processed_url,
                "message": "视频下载失败"
            }
            
    except Exception as e:
        utils.logger.error(f"[BilibiliVideoTest] 下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/video-info/{video_url:path}")
async def get_video_info(video_url: str):
    """
    获取视频信息
    """
    try:
        # URL解码
        import urllib.parse
        decoded_url = urllib.parse.unquote(video_url)
        
        utils.logger.info(f"[BilibiliVideoTest] 获取视频信息: {decoded_url}")
        
        video_info = await bilibili_video_service.get_video_info(decoded_url)
        
        return {
            "url": decoded_url,
            "info": video_info
        }
        
    except Exception as e:
        utils.logger.error(f"[BilibiliVideoTest] 获取视频信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频信息失败: {str(e)}") 