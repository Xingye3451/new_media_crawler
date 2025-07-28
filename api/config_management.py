#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理API模块
专门处理爬虫配置的保存、加载、重置等功能
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools import utils
from config.config_manager import config_manager
from config.env_config_loader import config_loader
from config.platform_config_store import platform_config_store

router = APIRouter()

# 平台配置模板
PLATFORM_TEMPLATES = {
    "xhs": {
        "defaultKeywords": "编程副业,编程兼职",
        "defaultMaxCount": 20,
        "defaultCrawlerType": "search",
        "defaultLoginType": "qrcode",
        "enableComments": True,
        "enableSubComments": False,
        "enableImages": False,
        "enableVideos": True,
        "maxConcurrency": 2,
        "sleepInterval": 5,
        "timeoutSeconds": 300,
        "useProxy": False,
        "proxyStrategy": "disabled",
        "saveDataOption": "db",
        "dataRetentionDays": 30,
        "platformSpecific": {
            "searchNoteType": "video",
            "enableVideoFilter": True
        }
    },
    "dy": {
        "defaultKeywords": "编程教程,技术分享",
        "defaultMaxCount": 25,
        "defaultCrawlerType": "search",
        "defaultLoginType": "qrcode",
        "enableComments": True,
        "enableSubComments": False,
        "enableImages": False,
        "enableVideos": True,
        "maxConcurrency": 3,
        "sleepInterval": 3,
        "timeoutSeconds": 300,
        "useProxy": False,
        "proxyStrategy": "disabled",
        "saveDataOption": "db",
        "dataRetentionDays": 30,
        "platformSpecific": {
            "publishTimeType": 0,
            "enableVideoFilter": True
        }
    },
    "ks": {
        "defaultKeywords": "编程学习,技术分享",
        "defaultMaxCount": 20,
        "defaultCrawlerType": "search",
        "defaultLoginType": "qrcode",
        "enableComments": True,
        "enableSubComments": False,
        "enableImages": False,
        "enableVideos": True,
        "maxConcurrency": 2,
        "sleepInterval": 4,
        "timeoutSeconds": 300,
        "useProxy": False,
        "proxyStrategy": "disabled",
        "saveDataOption": "db",
        "dataRetentionDays": 30,
        "platformSpecific": {
            "enableVideoFilter": True
        }
    },
    "bili": {
        "defaultKeywords": "编程教程,技术分享",
        "defaultMaxCount": 30,
        "defaultCrawlerType": "search",
        "defaultLoginType": "qrcode",
        "enableComments": True,
        "enableSubComments": False,
        "enableImages": False,
        "enableVideos": True,
        "maxConcurrency": 2,
        "sleepInterval": 5,
        "timeoutSeconds": 300,
        "useProxy": False,
        "proxyStrategy": "disabled",
        "saveDataOption": "db",
        "dataRetentionDays": 30,
        "platformSpecific": {
            "allDay": False,
            "startDay": "2024-01-01",
            "endDay": "2024-01-31",
            "creatorMode": False
        }
    }
}

# 配置预设
CONFIG_PRESETS = {
    "conservative": {
        "maxConcurrency": 1,
        "sleepInterval": 8,
        "defaultMaxCount": 10,
        "enableComments": False,
        "enableImages": False,
        "enableVideos": False
    },
    "balanced": {
        "maxConcurrency": 2,
        "sleepInterval": 5,
        "defaultMaxCount": 20,
        "enableComments": False,
        "enableImages": False,
        "enableVideos": True
    },
    "aggressive": {
        "maxConcurrency": 3,
        "sleepInterval": 3,
        "defaultMaxCount": 30,
        "enableComments": True,
        "enableImages": False,
        "enableVideos": True
    }
}

class PlatformConfigRequest(BaseModel):
    """平台配置请求模型"""
    platform: str = Field(..., description="平台名称", example="xhs")
    defaultKeywords: str = Field(default="", description="默认关键词")
    defaultMaxCount: int = Field(default=20, description="默认爬取数量", ge=1, le=100)
    defaultCrawlerType: str = Field(default="search", description="默认爬虫类型")
    defaultLoginType: str = Field(default="qrcode", description="默认登录类型")
    
    # 功能开关
    enableComments: bool = Field(default=False, description="是否获取评论")
    enableSubComments: bool = Field(default=False, description="是否获取子评论")
    enableImages: bool = Field(default=False, description="是否获取图片")
    enableVideos: bool = Field(default=True, description="是否获取视频")
    
    # 资源控制
    maxConcurrency: int = Field(default=2, description="最大并发数", ge=1, le=5)
    sleepInterval: int = Field(default=5, description="请求间隔(秒)", ge=1, le=30)
    timeoutSeconds: int = Field(default=300, description="超时时间(秒)", ge=60, le=1800)
    
    # 代理设置
    useProxy: bool = Field(default=False, description="是否启用代理")
    proxyStrategy: str = Field(default="disabled", description="代理策略")
    
    # 数据存储
    saveDataOption: str = Field(default="db", description="存储方式")
    dataRetentionDays: int = Field(default=30, description="数据保留天数", ge=1, le=365)
    
    # 平台特定配置
    platformSpecific: Optional[Dict[str, Any]] = Field(None, description="平台特定配置")

class PlatformConfigResponse(BaseModel):
    """平台配置响应模型"""
    platform: str
    config: Dict[str, Any]
    last_updated: str
    status: str

class ConfigPresetRequest(BaseModel):
    """配置预设请求模型"""
    preset: str = Field(..., description="预设名称", example="conservative")
    platform: str = Field(..., description="平台名称", example="xhs")

class ConfigPresetResponse(BaseModel):
    """配置预设响应模型"""
    preset: str
    platform: str
    config: Dict[str, Any]
    description: str

class ConfigOverviewResponse(BaseModel):
    """配置概览响应模型"""
    total_platforms: int
    configured_platforms: List[str]
    last_updated: str
    config_summary: Dict[str, Any]

@router.get("/config/platforms")
async def get_configured_platforms():
    """获取已配置的平台列表"""
    try:
        platforms = list(PLATFORM_TEMPLATES.keys())
        return {
            "platforms": platforms,
            "total": len(platforms),
            "status": "success"
        }
    except Exception as e:
        utils.logger.error(f"获取平台列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台列表失败: {str(e)}")

@router.get("/config/template/{platform}")
async def get_platform_template(platform: str):
    """获取平台配置模板"""
    try:
        if platform not in PLATFORM_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"平台 {platform} 不存在")
        
        template = PLATFORM_TEMPLATES[platform]
        return {
            "platform": platform,
            "template": template,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"获取平台模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台模板失败: {str(e)}")

@router.post("/config/save/{platform}", response_model=PlatformConfigResponse)
async def save_platform_config(platform: str, request: PlatformConfigRequest):
    """保存平台配置"""
    try:
        if platform not in PLATFORM_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"平台 {platform} 不存在")
        
        # 验证请求中的平台与URL中的平台一致
        if request.platform != platform:
            raise HTTPException(status_code=400, detail="平台名称不匹配")
        
        # 构建配置对象
        config = {
            "platform": platform,
            "defaultKeywords": request.defaultKeywords,
            "defaultMaxCount": request.defaultMaxCount,
            "defaultCrawlerType": request.defaultCrawlerType,
            "defaultLoginType": request.defaultLoginType,
            "enableComments": request.enableComments,
            "enableSubComments": request.enableSubComments,
            "enableImages": request.enableImages,
            "enableVideos": request.enableVideos,
            "maxConcurrency": request.maxConcurrency,
            "sleepInterval": request.sleepInterval,
            "timeoutSeconds": request.timeoutSeconds,
            "useProxy": request.useProxy,
            "proxyStrategy": request.proxyStrategy,
            "saveDataOption": request.saveDataOption,
            "dataRetentionDays": request.dataRetentionDays,
            "platformSpecific": request.platformSpecific or {}
        }
        
        # 保存到配置存储
        if platform_config_store.save_config(platform, config):
            last_updated = datetime.now().isoformat()
            
            return PlatformConfigResponse(
                platform=platform,
                config=config,
                last_updated=last_updated,
                status="saved"
            )
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"保存平台配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

@router.get("/config/load/{platform}", response_model=PlatformConfigResponse)
async def load_platform_config(platform: str):
    """加载平台配置"""
    try:
        if platform not in PLATFORM_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"平台 {platform} 不存在")
        
        # 尝试从配置存储加载
        saved_config = platform_config_store.load_config(platform)
        
        if saved_config:
            config = saved_config
            status = "loaded"
        else:
            # 使用默认模板
            config = PLATFORM_TEMPLATES[platform]
            status = "default"
        
        return PlatformConfigResponse(
            platform=platform,
            config=config,
            last_updated=datetime.now().isoformat(),
            status=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"加载平台配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")

@router.post("/config/reset/{platform}")
async def reset_platform_config(platform: str):
    """重置平台配置为默认值"""
    try:
        if platform not in PLATFORM_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"平台 {platform} 不存在")
        
        # 删除保存的配置，恢复默认模板
        if platform_config_store.delete_config(platform):
            utils.logger.info(f"平台 {platform} 配置已重置")
        else:
            raise HTTPException(status_code=500, detail="重置配置失败")
        
        return {
            "platform": platform,
            "status": "reset",
            "message": f"平台 {platform} 配置已重置为默认值"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"重置平台配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")

@router.post("/config/preset", response_model=ConfigPresetResponse)
async def apply_config_preset(request: ConfigPresetRequest):
    """应用配置预设"""
    try:
        if request.preset not in CONFIG_PRESETS:
            raise HTTPException(status_code=404, detail=f"预设 {request.preset} 不存在")
        
        if request.platform not in PLATFORM_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"平台 {request.platform} 不存在")
        
        # 获取预设配置
        preset_config = CONFIG_PRESETS[request.preset]
        
        # 获取平台默认模板
        platform_template = PLATFORM_TEMPLATES[request.platform].copy()
        
        # 应用预设配置
        platform_template.update(preset_config)
        
        # 保存配置
        if platform_config_store.save_config(request.platform, platform_template):
            utils.logger.info(f"已应用预设 {request.preset} 到平台 {request.platform}")
        else:
            raise HTTPException(status_code=500, detail="保存预设配置失败")
        
        return ConfigPresetResponse(
            preset=request.preset,
            platform=request.platform,
            config=platform_template,
            description=f"已应用 {request.preset} 预设配置"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"应用配置预设失败: {e}")
        raise HTTPException(status_code=500, detail=f"应用预设失败: {str(e)}")

@router.get("/config/presets")
async def get_config_presets():
    """获取可用的配置预设"""
    try:
        presets = {}
        for name, config in CONFIG_PRESETS.items():
            presets[name] = {
                "name": name,
                "description": get_preset_description(name),
                "config": config
            }
        
        return {
            "presets": presets,
            "total": len(presets),
            "status": "success"
        }
        
    except Exception as e:
        utils.logger.error(f"获取配置预设失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预设失败: {str(e)}")

@router.post("/config/save-all")
async def save_all_platform_configs():
    """保存所有平台配置"""
    try:
        saved_count = 0
        failed_platforms = []
        
        for platform in PLATFORM_TEMPLATES.keys():
            try:
                # 保存平台配置
                if platform_config_store.save_config(platform, PLATFORM_TEMPLATES[platform]):
                    saved_count += 1
                else:
                    failed_platforms.append(platform)
            except Exception as e:
                utils.logger.error(f"保存平台 {platform} 配置失败: {e}")
                failed_platforms.append(platform)
        
        return {
            "saved_count": saved_count,
            "failed_platforms": failed_platforms,
            "total_platforms": len(PLATFORM_TEMPLATES),
            "status": "completed"
        }
        
    except Exception as e:
        utils.logger.error(f"保存所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存所有配置失败: {str(e)}")

@router.post("/config/reset-all")
async def reset_all_platform_configs():
    """重置所有平台配置"""
    try:
        reset_count = 0
        
        for platform in PLATFORM_TEMPLATES.keys():
            try:
                # 重置平台配置
                if platform_config_store.delete_config(platform):
                    reset_count += 1
                    utils.logger.info(f"重置平台 {platform} 配置")
                else:
                    utils.logger.error(f"重置平台 {platform} 配置失败")
            except Exception as e:
                utils.logger.error(f"重置平台 {platform} 配置失败: {e}")
        
        return {
            "reset_count": reset_count,
            "total_platforms": len(PLATFORM_TEMPLATES),
            "status": "completed"
        }
        
    except Exception as e:
        utils.logger.error(f"重置所有配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置所有配置失败: {str(e)}")

@router.get("/config/export")
async def export_all_configs():
    """导出所有配置"""
    try:
        configs = {}
        
        for platform in PLATFORM_TEMPLATES.keys():
            saved_config = platform_config_store.load_config(platform)
            if saved_config:
                configs[platform] = saved_config
            else:
                configs[platform] = PLATFORM_TEMPLATES[platform]
        
        return {
            "configs": configs,
            "export_time": datetime.now().isoformat(),
            "total_platforms": len(configs),
            "status": "success"
        }
        
    except Exception as e:
        utils.logger.error(f"导出配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")

@router.post("/config/import")
async def import_configs(configs: Dict[str, Any]):
    """导入配置"""
    try:
        imported_count = 0
        failed_platforms = []
        
        for platform, config in configs.items():
            try:
                if platform in PLATFORM_TEMPLATES:
                    if platform_config_store.save_config(platform, config):
                        imported_count += 1
                        utils.logger.info(f"导入平台 {platform} 配置")
                    else:
                        failed_platforms.append(platform)
                else:
                    failed_platforms.append(platform)
            except Exception as e:
                utils.logger.error(f"导入平台 {platform} 配置失败: {e}")
                failed_platforms.append(platform)
        
        return {
            "imported_count": imported_count,
            "failed_platforms": failed_platforms,
            "total_platforms": len(configs),
            "status": "completed"
        }
        
    except Exception as e:
        utils.logger.error(f"导入配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")

@router.get("/config/overview", response_model=ConfigOverviewResponse)
async def get_config_overview():
    """获取配置概览"""
    try:
        configured_platforms = []
        config_summary = {}
        
        for platform in PLATFORM_TEMPLATES.keys():
            saved_config = platform_config_store.load_config(platform)
            if saved_config:
                configured_platforms.append(platform)
                config_summary[platform] = {
                    "has_custom_config": True,
                    "last_updated": saved_config.get("last_updated", "unknown"),
                    "default_keywords": saved_config.get("defaultKeywords", ""),
                    "max_count": saved_config.get("defaultMaxCount", 20),
                    "enable_videos": saved_config.get("enableVideos", True)
                }
            else:
                config_summary[platform] = {
                    "has_custom_config": False,
                    "last_updated": "never",
                    "default_keywords": PLATFORM_TEMPLATES[platform].get("defaultKeywords", ""),
                    "max_count": PLATFORM_TEMPLATES[platform].get("defaultMaxCount", 20),
                    "enable_videos": PLATFORM_TEMPLATES[platform].get("enableVideos", True)
                }
        
        return ConfigOverviewResponse(
            total_platforms=len(PLATFORM_TEMPLATES),
            configured_platforms=configured_platforms,
            last_updated=datetime.now().isoformat(),
            config_summary=config_summary
        )
        
    except Exception as e:
        utils.logger.error(f"获取配置概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置概览失败: {str(e)}")

def get_preset_description(preset: str) -> str:
    """获取预设描述"""
    descriptions = {
        "conservative": "保守模式 - 低并发，长间隔，适合稳定环境",
        "balanced": "平衡模式 - 中等并发，适中间隔，推荐使用",
        "aggressive": "激进模式 - 高并发，短间隔，适合高性能环境"
    }
    return descriptions.get(preset, "未知预设") 