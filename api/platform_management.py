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

@router.get("/platforms/list")
async def get_supported_platforms():
    """获取支持的平台列表"""
    try:
        from models.content_models import PLATFORM_MAPPING, VIDEO_PRIORITY_PLATFORMS, COMING_SOON_PLATFORMS
        
        platforms = []
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            platforms.append({
                "code": platform_key,
                "name": platform_info["name"],
                "description": platform_info.get("description", ""),
                "is_video_priority": platform_key in VIDEO_PRIORITY_PLATFORMS,
                "is_todo": platform_key in COMING_SOON_PLATFORMS,
                "primary_content_type": platform_info.get("primary_content_type", "mixed")
            })
        
        return {
            "code": 200,
            "message": "获取平台列表成功",
            "data": {
                "platforms": platforms,
                "total": len(platforms),
                "video_priority_count": len(VIDEO_PRIORITY_PLATFORMS),
                "todo_count": len(COMING_SOON_PLATFORMS)
            }
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台列表失败: {e}")
        return {
            "code": 500,
            "message": f"获取平台列表失败: {str(e)}",
            "data": None
        }

@router.get("/multi-platform/info")
async def get_multi_platform_info():
    """获取多平台爬取信息"""
    try:
        from models.content_models import (
            PLATFORM_MAPPING, 
            VIDEO_PRIORITY_PLATFORMS, 
            COMING_SOON_PLATFORMS,
            get_platform_description
        )
        
        # 构建平台信息
        platforms_info = {}
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            platforms_info[platform_key] = {
                "name": platform_info["name"],
                "description": get_platform_description(platform_key),
                "is_video_priority": platform_key in VIDEO_PRIORITY_PLATFORMS,
                "is_todo": platform_key in COMING_SOON_PLATFORMS,
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
            "todo_platforms": COMING_SOON_PLATFORMS,
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
        proxy = await proxy_manager.get_proxy(strategy_type, platform)
        
        if not proxy:
            raise HTTPException(status_code=404, detail="没有可用的代理")
        
        # 检查可用性
        if check_availability:
            is_available = await proxy_manager.check_proxy(proxy)
            proxy.is_available = is_available
        
        return {
            "proxy": {
                "id": proxy.id,
                "ip": proxy.ip,
                "port": proxy.port,
                "proxy_type": proxy.proxy_type,
                "country": proxy.country,
                "speed": proxy.speed,
                "anonymity": proxy.anonymity,
                "uptime": proxy.uptime,
                "is_available": getattr(proxy, 'is_available', True)
            } if proxy else None,
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
        from proxy.proxy_manager import ProxyManager
        
        proxy_manager = ProxyManager()
        stats = await proxy_manager.get_proxy_stats()
        
        return {
            "total_proxies": stats.get("total", 0),
            "available_proxies": stats.get("available", 0),
            "unavailable_proxies": stats.get("total", 0) - stats.get("available", 0),
            "platform_stats": {},  # 当前实现不提供平台统计
            "quality_stats": {
                "avg_speed": stats.get("avg_speed", 0),
                "avg_uptime": stats.get("avg_uptime", 0)
            },
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取代理统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理统计失败: {str(e)}")

@router.get("/accounts/{platform}")
async def get_platform_accounts(platform: str):
    """获取平台账号列表"""
    try:
        from api.account_management import get_accounts
        
        accounts_response = await get_accounts(platform=platform)
        
        if accounts_response["code"] != 200:
            return accounts_response
        
        accounts = accounts_response["data"]
        
        return {
            "code": 200,
            "message": f"获取{platform}平台账号成功",
            "data": {
                "platform": platform,
                "accounts": accounts,
                "total": len(accounts),
                "valid_count": len([acc for acc in accounts if acc.login_status == "logged_in"]),
                "expired_count": len([acc for acc in accounts if acc.login_status == "expired"]),
                "invalid_count": len([acc for acc in accounts if acc.login_status == "not_logged_in"])
            }
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台账号失败: {e}")
        return {
            "code": 500,
            "message": f"获取平台账号失败: {str(e)}",
            "data": None
        }

@router.get("/accounts/{platform}/validity")
async def check_platform_token_validity(platform: str, account_id: Optional[str] = None):
    """检查平台账号凭证有效性"""
    try:
        from utils.db_utils import check_token_validity
        
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
            from api.account_management import get_accounts
            accounts = await get_accounts(platform=platform)
            
            validity_results = []
            for account in accounts:
                validity = await check_token_validity(platform, account.id)
                validity_results.append({
                    "account_id": account.id,
                    "account_name": account.account_name,
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
        from utils.db_utils import cleanup_expired_tokens
        
        cleaned_count = await cleanup_expired_tokens()
        
        return {
            "message": "过期凭证清理完成",
            "cleaned_count": cleaned_count,
            "platforms": [],  # 当前实现不返回平台信息
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"清理过期凭证失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理过期凭证失败: {str(e)}")

@router.get("/scheduler/status")
async def get_scheduler_status_api():
    """获取调度器状态"""
    try:
        from utils.scheduler import get_scheduler_status
        
        status = await get_scheduler_status()
        
        return {
            "is_running": status.get("is_running", False),
            "total_tasks": status.get("task_count", 0),
            "running_tasks": status.get("task_count", 0) if status.get("is_running", False) else 0,
            "completed_tasks": 0,  # 当前调度器不跟踪完成的任务
            "failed_tasks": 0,     # 当前调度器不跟踪失败的任务
            "next_run": None,      # 当前调度器不提供下次运行时间
            "last_run": None,      # 当前调度器不提供上次运行时间
            "uptime": None,        # 当前调度器不提供运行时间
            "status": status.get("status", "stopped"),
            "platforms": status.get("platforms", [])
        }
        
    except Exception as e:
        utils.logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")

@router.post("/scheduler/start")
async def start_scheduler_api():
    """启动调度器"""
    try:
        from utils.scheduler import start_scheduler
        
        await start_scheduler()
        
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
        from utils.scheduler import stop_scheduler
        
        await stop_scheduler()
        
        return {
            "message": "调度器停止成功",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}") 