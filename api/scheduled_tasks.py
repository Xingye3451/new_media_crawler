"""
定时任务API路由
提供定时任务的管理和监控功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import utils
from timetask.task_scheduler import scheduler

# 创建路由器
scheduled_tasks_router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应"""
    is_running: bool
    total_tasks: int
    scheduled_tasks: Dict[str, Any]


class ManualTriggerResponse(BaseModel):
    """手动触发响应"""
    success: bool
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@scheduled_tasks_router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = await scheduler.get_scheduler_status()
        return SchedulerStatusResponse(**status)
    except Exception as e:
        utils.logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")


@scheduled_tasks_router.post("/login-check/trigger", response_model=ManualTriggerResponse)
async def manually_trigger_login_check():
    """手动触发登录状态检查"""
    try:
        utils.logger.info("🔧 API手动触发登录状态检查")
        result = await scheduler.manually_trigger_login_check()
        
        return ManualTriggerResponse(
            success=result.get('success', False),
            message=result.get('message', ''),
            result=result if result.get('success') else None,
            error=result.get('error') if not result.get('success') else None
        )
    except Exception as e:
        utils.logger.error(f"手动触发登录状态检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动触发失败: {str(e)}")


@scheduled_tasks_router.post("/start")
async def start_scheduler():
    """启动调度器"""
    try:
        await scheduler.start()
        return {
            "success": True,
            "message": "调度器启动成功",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        utils.logger.error(f"启动调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动调度器失败: {str(e)}")


@scheduled_tasks_router.post("/stop")
async def stop_scheduler():
    """停止调度器"""
    try:
        await scheduler.stop()
        return {
            "success": True,
            "message": "调度器停止成功",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        utils.logger.error(f"停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}")


@scheduled_tasks_router.get("/health")
async def get_scheduler_health():
    """获取调度器健康状态"""
    try:
        status = await scheduler.get_scheduler_status()
        
        # 检查关键指标
        health_status = "healthy"
        issues = []
        
        if not status.get('is_running', False):
            health_status = "unhealthy"
            issues.append("调度器未运行")
        
        # 检查任务状态
        scheduled_tasks = status.get('scheduled_tasks', {})
        for task_name, task_info in scheduled_tasks.items():
            if task_info.get('enabled') and task_info.get('exception'):
                health_status = "warning"
                issues.append(f"任务 {task_name} 存在异常: {task_info.get('exception')}")
        
        return {
            "status": health_status,
            "is_running": status.get('is_running', False),
            "total_tasks": status.get('total_tasks', 0),
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        utils.logger.error(f"获取调度器健康状态失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
