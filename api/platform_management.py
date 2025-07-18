"""
平台管理路由模块
包含平台信息、代理管理等功能
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import utils

router = APIRouter()

@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    try:
        from models.content_models import PLATFORM_MAPPING, VIDEO_PRIORITY_PLATFORMS, TODO_PLATFORMS
        
        platforms = []
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            platforms.append({
                "code": platform_key,
                "name": platform_info["name"],
                "description": platform_info.get("description", ""),
                "is_video_priority": platform_key in VIDEO_PRIORITY_PLATFORMS,
                "is_todo": platform_key in TODO_PLATFORMS,
                "primary_content_type": platform_info.get("primary_content_type", "mixed")
            })
        
        return {
            "platforms": platforms,
            "total": len(platforms),
            "video_priority_count": len(VIDEO_PRIORITY_PLATFORMS),
            "todo_count": len(TODO_PLATFORMS)
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台列表失败: {str(e)}")

@router.get("/multi-platform/info")
async def get_multi_platform_info():
    """获取多平台爬取信息"""
    try:
        from models.content_models import (
            PLATFORM_MAPPING, 
            VIDEO_PRIORITY_PLATFORMS, 
            TODO_PLATFORMS,
            get_platform_description
        )
        
        # 构建平台信息
        platforms_info = {}
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            platforms_info[platform_key] = {
                "name": platform_info["name"],
                "description": get_platform_description(platform_key),
                "is_video_priority": platform_key in VIDEO_PRIORITY_PLATFORMS,
                "is_todo": platform_key in TODO_PLATFORMS,
                "primary_content_type": platform_info.get("primary_content_type", "mixed"),
                "supported_crawler_types": platform_info.get("supported_crawler_types", ["search"]),
                "login_required": platform_info.get("login_required", True),
                "proxy_support": platform_info.get("proxy_support", True),
                "comment_support": platform_info.get("comment_support", True)
            }
        
        return {
            "platforms": platforms_info,
            "total_platforms": len(platforms_info),
            "video_priority_platforms": VIDEO_PRIORITY_PLATFORMS,
            "todo_platforms": TODO_PLATFORMS,
            "supported_crawler_types": {
                "search": "关键词搜索",
                "user": "用户主页",
                "hashtag": "话题标签",
                "trending": "热门推荐"
            },
            "login_types": {
                "qrcode": "二维码登录",
                "password": "密码登录",
                "sms": "短信验证码",
                "cookie": "Cookie导入"
            },
            "proxy_strategies": {
                "disabled": "禁用代理",
                "round_robin": "轮询代理",
                "random": "随机代理",
                "weighted": "权重代理",
                "failover": "故障转移",
                "sticky": "粘性会话"
            },
            "save_data_options": {
                "db": "仅数据库",
                "csv": "仅CSV文件",
                "json": "仅JSON文件",
                "db_csv": "数据库+CSV",
                "db_json": "数据库+JSON",
                "all": "全部格式"
            }
        }
        
    except Exception as e:
        utils.logger.error(f"获取多平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取多平台信息失败: {str(e)}")

@router.get("/proxy/quick-get")
async def quick_get_proxy(
    strategy_type: str = Query("round_robin", description="代理策略类型"),
    platform: str = Query(None, description="目标平台"),
    check_availability: bool = Query(True, description="是否检查可用性")
):
    """快速获取代理"""
    try:
        from proxy.proxy_tools import ProxyManager
        
        proxy_manager = ProxyManager()
        
        # 根据策略获取代理
        if strategy_type == "round_robin":
            proxy = await proxy_manager.get_round_robin_proxy(platform)
        elif strategy_type == "random":
            proxy = await proxy_manager.get_random_proxy(platform)
        elif strategy_type == "weighted":
            proxy = await proxy_manager.get_weighted_proxy(platform)
        elif strategy_type == "failover":
            proxy = await proxy_manager.get_failover_proxy(platform)
        elif strategy_type == "sticky":
            proxy = await proxy_manager.get_sticky_proxy(platform)
        else:
            raise HTTPException(status_code=400, detail="不支持的代理策略")
        
        if not proxy:
            raise HTTPException(status_code=404, detail="没有可用的代理")
        
        # 检查可用性
        if check_availability:
            is_available = await proxy_manager.check_proxy_availability(proxy)
            proxy["is_available"] = is_available
        
        return {
            "proxy": proxy,
            "strategy": strategy_type,
            "platform": platform,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"获取代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理失败: {str(e)}")

@router.get("/proxy/quick-stats")
async def quick_proxy_stats():
    """获取代理统计信息"""
    try:
        from proxy.proxy_tools import ProxyManager
        
        proxy_manager = ProxyManager()
        stats = await proxy_manager.get_proxy_stats()
        
        return {
            "total_proxies": stats.get("total", 0),
            "available_proxies": stats.get("available", 0),
            "unavailable_proxies": stats.get("unavailable", 0),
            "platform_stats": stats.get("platform_stats", {}),
            "quality_stats": stats.get("quality_stats", {}),
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取代理统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理统计失败: {str(e)}")

@router.get("/accounts/{platform}")
async def get_platform_accounts(platform: str):
    """获取平台账号列表"""
    try:
        from api.account_management import get_accounts_for_platform
        
        accounts = await get_accounts_for_platform(platform)
        
        return {
            "platform": platform,
            "accounts": accounts,
            "total": len(accounts),
            "valid_count": len([acc for acc in accounts if acc.get("status") == "valid"]),
            "expired_count": len([acc for acc in accounts if acc.get("status") == "expired"]),
            "invalid_count": len([acc for acc in accounts if acc.get("status") == "invalid"])
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台账号失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台账号失败: {str(e)}")

@router.get("/accounts/{platform}/validity")
async def check_platform_token_validity(platform: str, account_id: Optional[str] = None):
    """检查平台账号凭证有效性"""
    try:
        from api.login_management import check_token_validity
        
        if account_id:
            # 检查指定账号
            validity = await check_token_validity(platform, account_id)
            return {
                "platform": platform,
                "account_id": account_id,
                "validity": validity
            }
        else:
            # 检查所有账号
            from api.account_management import get_accounts_for_platform
            accounts = await get_accounts_for_platform(platform)
            
            validity_results = []
            for account in accounts:
                validity = await check_token_validity(platform, account["id"])
                validity_results.append({
                    "account_id": account["id"],
                    "account_name": account["account_name"],
                    "validity": validity
                })
            
            return {
                "platform": platform,
                "accounts": validity_results,
                "total": len(validity_results),
                "valid_count": len([r for r in validity_results if r["validity"]["status"] == "valid"]),
                "expired_count": len([r for r in validity_results if r["validity"]["status"] == "expired"]),
                "invalid_count": len([r for r in validity_results if r["validity"]["status"] == "invalid"])
            }
        
    except Exception as e:
        utils.logger.error(f"检查平台账号有效性失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查平台账号有效性失败: {str(e)}")

@router.post("/tokens/cleanup")
async def cleanup_expired_tokens_api():
    """清理过期凭证"""
    try:
        from api.login_management import cleanup_expired_tokens
        
        result = await cleanup_expired_tokens()
        
        return {
            "message": "过期凭证清理完成",
            "cleaned_count": result.get("cleaned_count", 0),
            "platforms": result.get("platforms", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"清理过期凭证失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理过期凭证失败: {str(e)}")

@router.get("/scheduler/status")
async def get_scheduler_status_api():
    """获取调度器状态"""
    try:
        from scheduler.task_scheduler import TaskScheduler
        
        scheduler = TaskScheduler()
        status = await scheduler.get_status()
        
        return {
            "is_running": status.get("is_running", False),
            "total_tasks": status.get("total_tasks", 0),
            "running_tasks": status.get("running_tasks", 0),
            "completed_tasks": status.get("completed_tasks", 0),
            "failed_tasks": status.get("failed_tasks", 0),
            "next_run": status.get("next_run"),
            "last_run": status.get("last_run"),
            "uptime": status.get("uptime")
        }
        
    except Exception as e:
        utils.logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")

@router.post("/scheduler/start")
async def start_scheduler_api():
    """启动调度器"""
    try:
        from scheduler.task_scheduler import TaskScheduler
        
        scheduler = TaskScheduler()
        await scheduler.start()
        
        return {
            "message": "调度器启动成功",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"启动调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动调度器失败: {str(e)}")

@router.post("/scheduler/stop")
async def stop_scheduler_api():
    """停止调度器"""
    try:
        from scheduler.task_scheduler import TaskScheduler
        
        scheduler = TaskScheduler()
        await scheduler.stop()
        
        return {
            "message": "调度器停止成功",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}") 