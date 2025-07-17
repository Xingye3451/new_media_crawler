#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务管理API路由
提供任务CRUD、视频管理、日志记录等功能
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from models.task_models import (
    TaskCreateRequest, TaskUpdateRequest, TaskListRequest,
    TaskResponse, TaskListResponse, VideoResponse, VideoListResponse,
    TaskLogResponse, TaskLogListResponse, TaskStatisticsResponse,
    VideoActionRequest, TaskActionRequest
)
from services.task_management_service import TaskManagementService
from services.minio_service import MinIOService

logger = logging.getLogger(__name__)

router = APIRouter()
task_service = TaskManagementService()
minio_service = MinIOService()


@router.post("/tasks", response_model=Dict[str, Any])
async def create_task(request: TaskCreateRequest, http_request: Request):
    """创建任务"""
    try:
        # 获取客户端IP
        client_ip = http_request.client.host if http_request.client else None
        
        task_data = {
            'platform': request.platform,
            'task_type': request.task_type,
            'keywords': request.keywords,
            'user_id': request.user_id,
            'params': request.params,
            'priority': request.priority,
            'ip_address': client_ip,
            'user_security_id': request.user_security_id,
            'user_signature': request.user_signature
        }
        
        task_id = await task_service.create_task(task_data)
        
        return {
            "code": 200,
            "message": "任务创建成功",
            "data": {"task_id": task_id}
        }
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": task
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.put("/tasks/{task_id}", response_model=Dict[str, Any])
async def update_task(task_id: str, request: TaskUpdateRequest):
    """更新任务"""
    try:
        update_data = {}
        if request.status is not None:
            update_data['status'] = request.status
        if request.progress is not None:
            update_data['progress'] = request.progress
        if request.result_count is not None:
            update_data['result_count'] = request.result_count
        if request.error_message is not None:
            update_data['error_message'] = request.error_message
        if request.is_favorite is not None:
            update_data['is_favorite'] = request.is_favorite
        if request.is_pinned is not None:
            update_data['is_pinned'] = request.is_pinned
        
        update_data['updated_at'] = datetime.now()
        
        success = await task_service.update_task(task_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "code": 200,
            "message": "更新成功",
            "data": {"task_id": task_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def delete_task(task_id: str):
    """删除任务（软删除）"""
    try:
        success = await task_service.delete_task(task_id)
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
        logger.error(f"删除任务失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get("/tasks", response_model=Dict[str, Any])
async def list_tasks(
    platform: Optional[str] = Query(None, description="平台筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    task_type: Optional[str] = Query(None, description="任务类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    is_favorite: Optional[bool] = Query(None, description="收藏筛选"),
    is_pinned: Optional[bool] = Query(None, description="置顶筛选"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取任务列表"""
    try:
        filters = {
            'platform': platform,
            'status': status,
            'task_type': task_type,
            'keyword': keyword,
            'is_favorite': is_favorite,
            'is_pinned': is_pinned,
            'user_id': user_id,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        # 移除None值
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = await task_service.list_tasks(filters, page, page_size)
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/tasks/{task_id}/videos", response_model=Dict[str, Any])
async def get_task_videos(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取任务的视频列表"""
    try:
        result = await task_service.get_task_videos(task_id, page, page_size)
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取任务视频列表失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务视频列表失败: {str(e)}")


@router.get("/videos/{video_id}", response_model=Dict[str, Any])
async def get_video_detail(video_id: int):
    """获取视频详情"""
    try:
        video = await task_service.get_video_detail(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="视频未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": video
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频详情失败 {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取视频详情失败: {str(e)}")


@router.post("/videos/{video_id}/action", response_model=Dict[str, Any])
async def video_action(video_id: int, request: VideoActionRequest):
    """视频操作（收藏、下载等）"""
    try:
        if request.action == "favorite":
            # 收藏视频到MinIO
            video = await task_service.get_video_detail(video_id)
            if not video:
                raise HTTPException(status_code=404, detail="视频未找到")
            
            # 调用MinIO服务下载视频并存储
            download_url = video.get('download_url') or video.get('play_url')
            if not download_url:
                raise HTTPException(status_code=404, detail="视频下载链接不存在")
            
            minio_url = await minio_service.upload_video(
                download_url, 
                video['aweme_id'], 
                'douyin'
            )
            
            if not minio_url:
                raise HTTPException(status_code=500, detail="视频上传到MinIO失败")
            
            success = await task_service.update_video_collection(video_id, True, minio_url)
            if not success:
                raise HTTPException(status_code=500, detail="收藏失败")
            
            return {
                "code": 200,
                "message": "收藏成功",
                "data": {"video_id": video_id, "minio_url": minio_url}
            }
            
        elif request.action == "unfavorite":
            success = await task_service.update_video_collection(video_id, False)
            if not success:
                raise HTTPException(status_code=500, detail="取消收藏失败")
            
            return {
                "code": 200,
                "message": "取消收藏成功",
                "data": {"video_id": video_id}
            }
            
        elif request.action == "download":
            # 获取视频下载链接
            video = await task_service.get_video_detail(video_id)
            if not video:
                raise HTTPException(status_code=404, detail="视频未找到")
            
            download_url = video.get('download_url') or video.get('play_url')
            if not download_url:
                raise HTTPException(status_code=404, detail="视频下载链接不存在")
            
            return {
                "code": 200,
                "message": "获取下载链接成功",
                "data": {"video_id": video_id, "download_url": download_url}
            }
            
        else:
            raise HTTPException(status_code=400, detail="不支持的操作类型")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频操作失败 {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"视频操作失败: {str(e)}")


@router.post("/tasks/{task_id}/action", response_model=Dict[str, Any])
async def task_action(task_id: str, request: TaskActionRequest):
    """任务操作（收藏、置顶等）"""
    try:
        if request.action == "favorite":
            success = await task_service.update_task(task_id, {"is_favorite": True})
        elif request.action == "unfavorite":
            success = await task_service.update_task(task_id, {"is_favorite": False})
        elif request.action == "pin":
            success = await task_service.update_task(task_id, {"is_pinned": True})
        elif request.action == "unpin":
            success = await task_service.update_task(task_id, {"is_pinned": False})
        elif request.action == "delete":
            success = await task_service.delete_task(task_id)
        else:
            raise HTTPException(status_code=400, detail="不支持的操作类型")
        
        if not success:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        return {
            "code": 200,
            "message": "操作成功",
            "data": {"task_id": task_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务操作失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"任务操作失败: {str(e)}")


@router.get("/tasks/{task_id}/logs", response_model=Dict[str, Any])
async def get_task_logs(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量")
):
    """获取任务日志"""
    try:
        result = await task_service.get_task_logs(task_id, page, page_size)
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取任务日志失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务日志失败: {str(e)}")


@router.get("/tasks/statistics", response_model=Dict[str, Any])
async def get_task_statistics():
    """获取任务统计信息"""
    try:
        stats = await task_service.get_task_statistics()
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")


@router.get("/videos", response_model=Dict[str, Any])
async def list_videos(
    task_id: Optional[str] = Query(None, description="任务ID筛选"),
    is_collected: Optional[bool] = Query(None, description="收藏状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取视频列表"""
    try:
        # 这里应该实现视频列表查询，暂时返回空结果
        # 实际实现需要根据task_id和is_collected进行筛选
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "items": []
            }
        }
    except Exception as e:
        logger.error(f"获取视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取视频列表失败: {str(e)}") 