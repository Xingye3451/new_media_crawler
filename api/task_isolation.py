"""
任务隔离API
提供任务隔离状态查看和管理功能
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from tools import utils
from utils.task_isolation import task_isolation_manager

router = APIRouter()

@router.get("/isolation/status")
async def get_isolation_status():
    """获取任务隔离状态"""
    try:
        stats = await task_isolation_manager.get_task_statistics()
        return {
            "code": 200,
            "message": "获取任务隔离状态成功",
            "data": stats
        }
    except Exception as e:
        utils.logger.error(f"获取任务隔离状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务隔离状态失败")

@router.get("/isolation/tasks")
async def get_running_tasks():
    """获取所有运行中的任务"""
    try:
        tasks = await task_isolation_manager.get_running_tasks()
        return {
            "code": 200,
            "message": "获取运行中任务成功",
            "data": {
                "tasks": tasks,
                "total": len(tasks)
            }
        }
    except Exception as e:
        utils.logger.error(f"获取运行中任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取运行中任务失败")

@router.get("/isolation/tasks/{task_id}")
async def get_task_info(task_id: str):
    """获取特定任务信息"""
    try:
        task_info = await task_isolation_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "code": 200,
            "message": "获取任务信息成功",
            "data": task_info
        }
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"获取任务信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务信息失败")

@router.delete("/isolation/tasks/{task_id}")
async def force_stop_task(task_id: str):
    """强制停止任务"""
    try:
        task_info = await task_isolation_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        await task_isolation_manager.unregister_task(task_id)
        
        return {
            "code": 200,
            "message": "任务已强制停止",
            "data": {
                "task_id": task_id,
                "stopped_at": utils.get_isoformat_utc8()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"强制停止任务失败: {e}")
        raise HTTPException(status_code=500, detail="强制停止任务失败")

@router.get("/isolation/sessions")
async def get_task_sessions():
    """获取任务会话列表"""
    try:
        sessions = task_isolation_manager.task_sessions
        return {
            "code": 200,
            "message": "获取任务会话成功",
            "data": {
                "sessions": sessions,
                "total": len(sessions)
            }
        }
    except Exception as e:
        utils.logger.error(f"获取任务会话失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务会话失败")

@router.post("/isolation/cleanup")
async def trigger_cleanup():
    """触发清理任务"""
    try:
        await task_isolation_manager.cleanup_expired_sessions()
        
        return {
            "code": 200,
            "message": "清理任务已触发",
            "data": {
                "cleaned_at": utils.get_isoformat_utc8()
            }
        }
    except Exception as e:
        utils.logger.error(f"触发清理任务失败: {e}")
        raise HTTPException(status_code=500, detail="触发清理任务失败")
