"""
任务结果API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from services.task_result_service import TaskResultService

logger = logging.getLogger(__name__)

router = APIRouter()
task_service = TaskResultService()

@router.get("/task-results", response_model=Dict[str, Any])
async def get_task_results(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取任务结果列表"""
    try:
        results = await task_service.get_task_results(page=page, page_size=page_size)
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取任务结果列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务结果列表失败")

@router.get("/task-results/statistics", response_model=Dict[str, Any])
async def get_system_statistics():
    """获取系统统计信息"""
    try:
        results = await task_service.get_system_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统统计失败")

@router.get("/task-results/{task_id}", response_model=Dict[str, Any])
async def get_task_detail(task_id: str):
    """获取任务详情"""
    try:
        result = await task_service.get_task_detail(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")

@router.get("/task-results/{task_id}/videos", response_model=Dict[str, Any])
async def get_task_videos(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取任务的视频列表"""
    try:
        results = await task_service.get_task_videos(task_id, page=page, page_size=page_size)
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取任务视频列表失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务视频列表失败")

@router.get("/videos/{platform}/{video_id}", response_model=Dict[str, Any])
async def get_video_detail(platform: str, video_id: str):
    """获取视频详情"""
    try:
        result = await task_service.get_video_detail(platform, video_id)
        if not result:
            raise HTTPException(status_code=404, detail="视频未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频详情失败 {platform}/{video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取视频详情失败")

@router.get("/platforms/{platform}/videos", response_model=Dict[str, Any])
async def get_platform_videos(
    platform: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取平台视频列表"""
    try:
        results = await task_service.get_platform_videos(platform, page=page, page_size=page_size)
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取平台视频列表失败 {platform}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取平台视频列表失败")

@router.delete("/task-results/{task_id}", response_model=Dict[str, Any])
async def delete_task_result(task_id: str):
    """删除任务结果"""
    try:
        success = await task_service.delete_task_result(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "code": 200,
            "message": "删除成功",
            "data": {"task_id": task_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务结果失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="删除任务结果失败")

@router.post("/task-results/cleanup", response_model=Dict[str, Any])
async def cleanup_expired_tasks(days: int = Query(7, ge=1, description="清理天数")):
    """清理过期任务"""
    try:
        count = await task_service.cleanup_expired_tasks(days)
        return {
            "code": 200,
            "message": "清理成功",
            "data": {"cleaned_count": count}
        }
    except Exception as e:
        logger.error(f"清理过期任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清理过期任务失败") 