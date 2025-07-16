"""
视频下载API路由
"""

from fastapi import APIRouter, HTTPException, Query, Form
from typing import Dict, Any, List
import logging
from pydantic import BaseModel

from services.video_download_service import VideoDownloadService

logger = logging.getLogger(__name__)

router = APIRouter()
download_service = VideoDownloadService()

class VideoDownloadRequest(BaseModel):
    video_url: str
    video_id: str
    platform: str
    download_type: str = "local"  # local 或 server

@router.post("/videos/download", response_model=Dict[str, Any])
async def download_video(request: VideoDownloadRequest):
    """下载视频"""
    try:
        result = await download_service.download_video(
            video_url=request.video_url,
            video_id=request.video_id,
            platform=request.platform,
            download_type=request.download_type
        )
        
        return {
            "code": 200,
            "message": "下载请求已提交",
            "data": result
        }
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail="下载视频失败")

@router.get("/downloads/tasks", response_model=Dict[str, Any])
async def get_download_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取下载任务列表"""
    try:
        results = await download_service.get_download_tasks(page=page, page_size=page_size)
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取下载任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取下载任务列表失败")

@router.get("/downloads/tasks/{task_id}", response_model=Dict[str, Any])
async def get_download_task(task_id: str):
    """获取下载任务详情"""
    try:
        result = await download_service.get_download_task(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="下载任务未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取下载任务详情失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取下载任务详情失败")

@router.put("/downloads/tasks/{task_id}/cancel", response_model=Dict[str, Any])
async def cancel_download_task(task_id: str):
    """取消下载任务"""
    try:
        success = await download_service.cancel_download_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="下载任务未找到或无法取消")
        
        return {
            "code": 200,
            "message": "取消成功",
            "data": {"task_id": task_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消下载任务失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="取消下载任务失败")

@router.delete("/downloads/tasks/{task_id}", response_model=Dict[str, Any])
async def delete_download_task(task_id: str):
    """删除下载任务"""
    try:
        success = await download_service.delete_download_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="下载任务未找到")
        
        return {
            "code": 200,
            "message": "删除成功",
            "data": {"task_id": task_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除下载任务失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="删除下载任务失败")

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