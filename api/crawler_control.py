#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫控制API模块
完全通过API来控制爬虫行为，不依赖配置文件
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from tools import utils
from api.crawler_core import CrawlerFactory, run_crawler_task
from models.content_models import CrawlerRequest, CrawlerResponse, TaskStatusResponse

router = APIRouter()

# 全局任务状态存储
task_status = {}

class CrawlerConfigRequest(BaseModel):
    """爬虫配置请求模型"""
    platform: str = Field(..., description="平台名称", example="xhs")
    keywords: str = Field(..., description="搜索关键词", example="编程副业")
    max_count: int = Field(default=20, description="最大爬取数量", ge=1, le=100)
    
    # 登录相关
    account_id: Optional[int] = Field(None, description="指定账号ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    login_type: str = Field(default="qrcode", description="登录类型")
    
    # 爬取类型
    crawler_type: str = Field(default="search", description="爬虫类型: search/user")
    
    # 功能开关
    get_comments: bool = Field(default=False, description="是否获取评论")
    get_sub_comments: bool = Field(default=False, description="是否获取子评论")
    download_media: bool = Field(default=False, description="是否下载媒体文件")
    
    # 数据保存
    save_data_option: str = Field(default="db", description="数据保存方式: db/csv/json")
    
    # 代理设置
    use_proxy: bool = Field(default=False, description="是否使用代理")
    proxy_strategy: str = Field(default="disabled", description="代理策略")
    
    # 资源控制
    max_concurrency: int = Field(default=2, description="最大并发数", ge=1, le=5)
    sleep_interval: int = Field(default=5, description="请求间隔(秒)", ge=1, le=30)
    timeout_seconds: int = Field(default=300, description="任务超时时间(秒)", ge=60, le=1800)
    
    # 平台特定配置
    platform_config: Optional[Dict[str, Any]] = Field(None, description="平台特定配置")

class CrawlerConfigResponse(BaseModel):
    """爬虫配置响应模型"""
    task_id: str
    config: Dict[str, Any]
    estimated_time: str
    resource_usage: Dict[str, Any]

class CrawlerBatchRequest(BaseModel):
    """批量爬虫请求模型"""
    tasks: List[CrawlerConfigRequest] = Field(..., description="爬虫任务列表")
    batch_name: Optional[str] = Field(None, description="批次名称")
    sequential: bool = Field(default=False, description="是否顺序执行")

class CrawlerBatchResponse(BaseModel):
    """批量爬虫响应模型"""
    batch_id: str
    task_ids: List[str]
    total_tasks: int
    status: str

class ResourceMonitorRequest(BaseModel):
    """资源监控请求模型"""
    enable_monitoring: bool = Field(default=True, description="是否启用监控")
    monitor_interval: int = Field(default=30, description="监控间隔(秒)")
    alert_thresholds: Dict[str, int] = Field(default={
        "cpu": 80,
        "memory": 85,
        "disk": 90
    }, description="告警阈值")

@router.post("/crawler/configure", response_model=CrawlerConfigResponse)
async def configure_crawler(request: CrawlerConfigRequest):
    """配置爬虫参数"""
    try:
        # 验证平台支持
        if request.platform not in CrawlerFactory.VIDEO_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {request.platform}")
        
        # 生成任务ID
        task_id = f"task_{int(time.time())}_{request.platform}"
        
        # 估算执行时间
        estimated_time = estimate_execution_time(request)
        
        # 估算资源使用
        resource_usage = estimate_resource_usage(request)
        
        # 保存配置
        task_status[task_id] = {
            "config": request.dict(),
            "status": "configured",
            "created_at": datetime.now().isoformat(),
            "estimated_time": estimated_time,
            "resource_usage": resource_usage
        }
        
        return CrawlerConfigResponse(
            task_id=task_id,
            config=request.dict(),
            estimated_time=estimated_time,
            resource_usage=resource_usage
        )
        
    except Exception as e:
        utils.logger.error(f"配置爬虫失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")

@router.post("/crawler/start", response_model=CrawlerResponse)
async def start_crawler(request: CrawlerConfigRequest, background_tasks: BackgroundTasks):
    """启动爬虫任务"""
    try:
        # 生成任务ID
        task_id = f"task_{int(time.time())}_{request.platform}"
        
        # 转换为CrawlerRequest格式
        crawler_request = CrawlerRequest(
            platform=request.platform,
            keywords=request.keywords,
            max_notes_count=request.max_count,
            account_id=request.account_id,
            session_id=request.session_id,
            login_type=request.login_type,
            crawler_type=request.crawler_type,
            get_comments=request.get_comments,
            save_data_option=request.save_data_option,
            use_proxy=request.use_proxy,
            proxy_strategy=request.proxy_strategy
        )
        
        # 设置动态配置
        set_dynamic_config(request)
        
        # 启动后台任务
        background_tasks.add_task(run_crawler_task, task_id, crawler_request)
        
        return CrawlerResponse(
            task_id=task_id,
            status="started",
            message="爬虫任务已启动",
            data={"task_id": task_id}
        )
        
    except Exception as e:
        utils.logger.error(f"启动爬虫失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

@router.post("/crawler/batch", response_model=CrawlerBatchResponse)
async def start_batch_crawler(request: CrawlerBatchRequest, background_tasks: BackgroundTasks):
    """启动批量爬虫任务"""
    try:
        batch_id = f"batch_{int(time.time())}"
        task_ids = []
        
        for i, task_config in enumerate(request.tasks):
            task_id = f"{batch_id}_task_{i+1}"
            task_ids.append(task_id)
            
            # 转换为CrawlerRequest格式
            crawler_request = CrawlerRequest(
                platform=task_config.platform,
                keywords=task_config.keywords,
                max_notes_count=task_config.max_count,
                account_id=task_config.account_id,
                session_id=task_config.session_id,
                login_type=task_config.login_type,
                crawler_type=task_config.crawler_type,
                get_comments=task_config.get_comments,
                save_data_option=task_config.save_data_option,
                use_proxy=task_config.use_proxy,
                proxy_strategy=task_config.proxy_strategy
            )
            
            # 设置动态配置
            set_dynamic_config(task_config)
            
            # 启动后台任务
            if request.sequential:
                # 顺序执行
                background_tasks.add_task(run_sequential_task, task_id, crawler_request, i)
            else:
                # 并行执行
                background_tasks.add_task(run_crawler_task, task_id, crawler_request)
        
        return CrawlerBatchResponse(
            batch_id=batch_id,
            task_ids=task_ids,
            total_tasks=len(request.tasks),
            status="started"
        )
        
    except Exception as e:
        utils.logger.error(f"启动批量爬虫失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量启动失败: {str(e)}")

@router.get("/crawler/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(**task_status[task_id])

@router.get("/crawler/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {
        "tasks": [
            {
                "task_id": task_id,
                "status": task_info.get("status", "unknown"),
                "platform": task_info.get("config", {}).get("platform", ""),
                "created_at": task_info.get("created_at", ""),
                "updated_at": task_info.get("updated_at", "")
            }
            for task_id, task_info in task_status.items()
        ]
    }

@router.delete("/crawler/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del task_status[task_id]
    return {"message": "任务已删除"}

@router.post("/crawler/pause/{task_id}")
async def pause_task(task_id: str):
    """暂停任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_status[task_id]["status"] = "paused"
    task_status[task_id]["updated_at"] = datetime.now().isoformat()
    
    return {"message": "任务已暂停"}

@router.post("/crawler/resume/{task_id}")
async def resume_task(task_id: str):
    """恢复任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_status[task_id]["status"] = "running"
    task_status[task_id]["updated_at"] = datetime.now().isoformat()
    
    return {"message": "任务已恢复"}

@router.post("/crawler/stop/{task_id}")
async def stop_task(task_id: str):
    """停止任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_status[task_id]["status"] = "stopped"
    task_status[task_id]["updated_at"] = datetime.now().isoformat()
    
    return {"message": "任务已停止"}

@router.get("/crawler/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    return {
        "video_platforms": CrawlerFactory.VIDEO_PLATFORMS,
        "coming_soon_platforms": list(CrawlerFactory.COMING_SOON_PLATFORMS.keys()),
        "platform_descriptions": CrawlerFactory.COMING_SOON_PLATFORMS
    }

@router.get("/crawler/config/template/{platform}")
async def get_platform_config_template(platform: str):
    """获取平台配置模板"""
    if platform not in CrawlerFactory.VIDEO_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")
    
    templates = {
        "xhs": {
            "max_concurrency": 2,
            "sleep_interval": 5,
            "get_comments": False,
            "download_media": False,
            "video_only": True,
            "search_note_type": "VIDEO"
        },
        "dy": {
            "max_concurrency": 1,
            "sleep_interval": 8,
            "get_comments": False,
            "download_media": False,
            "video_only": True,
            "publish_time_type": 0
        },
        "ks": {
            "max_concurrency": 2,
            "sleep_interval": 5,
            "get_comments": False,
            "download_media": False,
            "video_only": True
        },
        "bili": {
            "max_concurrency": 2,
            "sleep_interval": 5,
            "get_comments": False,
            "download_media": False,
            "video_only": True,
            "all_day": False,
            "start_day": "2024-01-01",
            "end_day": "2024-01-31",
            "creator_mode": False
        }
    }
    
    return {
        "platform": platform,
        "template": templates.get(platform, {}),
        "recommendations": get_platform_recommendations(platform)
    }

def set_dynamic_config(request: CrawlerConfigRequest):
    """设置动态配置"""
    import config
    
    # 设置基础配置
    config.PLATFORM = request.platform
    config.KEYWORDS = request.keywords
    config.CRAWLER_MAX_NOTES_COUNT = request.max_count
    config.ENABLE_GET_COMMENTS = request.get_comments
    config.ENABLE_GET_SUB_COMMENTS = request.get_sub_comments
    config.ENABLE_GET_IMAGES = request.download_media
    config.SAVE_DATA_OPTION = request.save_data_option
    config.ENABLE_IP_PROXY = request.use_proxy
    config.MAX_CONCURRENCY_NUM = request.max_concurrency
    config.MAX_SLEEP_SEC = request.sleep_interval
    
    # 设置平台特定配置
    if request.platform_config:
        for key, value in request.platform_config.items():
            # 处理平台特定的配置项
            if key == "search_note_type" and request.platform == "xhs":
                config.SEARCH_NOTE_TYPE = value
            elif key == "publish_time_type" and request.platform == "dy":
                config.PUBLISH_TIME_TYPE = value
            elif key == "all_day" and request.platform == "bili":
                config.ALL_DAY = value
            elif key == "start_day" and request.platform == "bili":
                config.START_DAY = value
            elif key == "end_day" and request.platform == "bili":
                config.END_DAY = value
            elif key == "creator_mode" and request.platform == "bili":
                config.CREATOR_MODE = value
            else:
                # 通用配置项设置
                setattr(config, key.upper(), value)

def estimate_execution_time(request: CrawlerConfigRequest) -> str:
    """估算执行时间"""
    base_time = 30  # 基础时间30秒
    
    # 根据爬取数量调整
    time_per_item = 5  # 每个项目约5秒
    estimated_seconds = base_time + (request.max_count * time_per_item)
    
    # 根据并发数调整
    if request.max_concurrency > 2:
        estimated_seconds = estimated_seconds * 0.7
    elif request.max_concurrency < 2:
        estimated_seconds = estimated_seconds * 1.3
    
    # 根据功能开关调整
    if request.get_comments:
        estimated_seconds *= 1.5
    if request.download_media:
        estimated_seconds *= 2.0
    
    minutes = int(estimated_seconds // 60)
    seconds = int(estimated_seconds % 60)
    
    return f"{minutes}分{seconds}秒"

def estimate_resource_usage(request: CrawlerConfigRequest) -> Dict[str, Any]:
    """估算资源使用"""
    return {
        "cpu_usage": f"{request.max_concurrency * 20}%",
        "memory_usage": f"{request.max_count * 2}MB",
        "network_usage": f"{request.max_count * 5}MB",
        "disk_usage": f"{request.max_count * 10}MB" if request.download_media else "0MB"
    }

def get_platform_recommendations(platform: str) -> Dict[str, Any]:
    """获取平台建议配置"""
    recommendations = {
        "xhs": {
            "max_concurrency": "建议2-3，避免资源耗尽",
            "sleep_interval": "建议5秒，避免反爬",
            "get_comments": "建议关闭，减少资源消耗",
            "video_only": "建议开启，专注短视频"
        },
        "dy": {
            "max_concurrency": "建议1-2，反爬较强",
            "sleep_interval": "建议8秒，增加间隔",
            "get_comments": "建议关闭，减少资源消耗",
            "video_only": "建议开启，专注短视频"
        },
        "ks": {
            "max_concurrency": "建议2-3，较稳定",
            "sleep_interval": "建议5秒，避免反爬",
            "get_comments": "建议关闭，评论获取较慢",
            "video_only": "建议开启，专注短视频"
        },
        "bili": {
            "max_concurrency": "建议2-3，较稳定",
            "sleep_interval": "建议5秒，避免反爬",
            "get_comments": "建议关闭，减少资源消耗",
            "video_only": "建议开启，专注短视频"
        }
    }
    
    return recommendations.get(platform, {})

async def run_sequential_task(task_id: str, crawler_request: CrawlerRequest, index: int):
    """顺序执行任务"""
    # 等待前一个任务完成
    if index > 0:
        await asyncio.sleep(10)  # 等待10秒
    
    await run_crawler_task(task_id, crawler_request) 