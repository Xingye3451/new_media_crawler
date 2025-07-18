"""
系统管理路由模块
包含健康检查、数据库初始化等功能
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import utils
from var import media_crawler_db_var

router = APIRouter()

# 全局数据库初始化状态
db_initialized = False

@router.get("/")
async def root():
    """根路径 - 返回API信息"""
    return {
        "name": "MediaCrawler API",
        "version": "1.0.0",
        "description": "多平台媒体内容爬虫API服务",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "crawler": "/api/v1/crawler/*",
            "content": "/api/v1/content/*",
            "platforms": "/api/v1/platforms/*",
            "accounts": "/api/v1/accounts/*",
            "system": "/api/v1/system/*"
        }
    }

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db_status = "unknown"
        try:
            async_db_obj = media_crawler_db_var.get()
            if async_db_obj:
                # 执行简单查询测试连接
                await async_db_obj.query("SELECT 1")
                db_status = "connected"
            else:
                db_status = "not_initialized"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # 检查Redis连接
        redis_status = "unknown"
        try:
            from redis_manager import TaskResultRedisManager
            redis_manager = TaskResultRedisManager()
            await redis_manager.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
        
        # 检查配置加载
        config_status = "unknown"
        try:
            from config.env_config_loader import config_loader
            config_loader.get_database_config()
            config_status = "loaded"
        except Exception as e:
            config_status = f"error: {str(e)}"
        
        overall_status = "healthy" if all(
            status in ["connected", "loaded"] 
            for status in [db_status, redis_status, config_status]
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": db_status,
                "redis": redis_status,
                "config": config_status
            },
            "uptime": datetime.now().isoformat()  # 这里可以添加实际的启动时间
        }
        
    except Exception as e:
        utils.logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/database/init")
async def init_database():
    """初始化数据库"""
    try:
        global db_initialized
        
        if db_initialized:
            return {
                "message": "数据库已初始化",
                "status": "already_initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        # 导入数据库初始化模块
        import db
        
        # 初始化数据库连接
        utils.logger.info("[DB_INIT] 开始初始化数据库连接...")
        await db.init_db()
        utils.logger.info("[DB_INIT] 数据库连接初始化完成")
        
        # 检查数据库表结构
        utils.logger.info("[DB_INIT] 检查数据库表结构...")
        async_db_obj = media_crawler_db_var.get()
        
        # 检查核心表是否存在
        core_tables = [
            "crawler_tasks", "crawler_task_logs",
            "douyin_aweme", "xhs_note", "kuaishou_video", "bilibili_video"
        ]
        
        missing_tables = []
        for table in core_tables:
            try:
                await async_db_obj.query(f"SELECT 1 FROM {table} LIMIT 1")
                utils.logger.info(f"[DB_INIT] 表 {table} 存在")
            except Exception as e:
                utils.logger.warning(f"[DB_INIT] 表 {table} 不存在: {e}")
                missing_tables.append(table)
        
        if missing_tables:
            utils.logger.warning(f"[DB_INIT] 缺少表: {missing_tables}")
            utils.logger.info("[DB_INIT] 建议运行数据库升级脚本")
        
        db_initialized = True
        
        return {
            "message": "数据库初始化完成",
            "status": "initialized",
            "missing_tables": missing_tables,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"[DB_INIT] 数据库初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库初始化失败: {str(e)}")

@router.get("/database/status")
async def get_database_status():
    """获取数据库状态"""
    try:
        async_db_obj = media_crawler_db_var.get()
        
        if not async_db_obj:
            return {
                "status": "not_initialized",
                "message": "数据库未初始化",
                "timestamp": datetime.now().isoformat()
            }
        
        # 检查连接
        try:
            await async_db_obj.query("SELECT 1")
            connection_status = "connected"
        except Exception as e:
            connection_status = f"error: {str(e)}"
        
        # 获取表信息
        tables_info = {}
        core_tables = [
            "crawler_tasks", "crawler_task_logs",
            "douyin_aweme", "xhs_note", "kuaishou_video", "bilibili_video"
        ]
        
        for table in core_tables:
            try:
                result = await async_db_obj.query(f"SELECT COUNT(*) as count FROM {table}")
                count = result[0]['count'] if result else 0
                tables_info[table] = {
                    "exists": True,
                    "record_count": count
                }
            except Exception:
                tables_info[table] = {
                    "exists": False,
                    "record_count": 0
                }
        
        return {
            "status": connection_status,
            "initialized": db_initialized,
            "tables": tables_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取数据库状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据库状态失败: {str(e)}")

@router.post("/database/upgrade")
async def upgrade_database():
    """升级数据库结构"""
    try:
        from upgrade_database import upgrade_database_schema
        
        result = await upgrade_database_schema()
        
        return {
            "message": "数据库升级完成",
            "status": "upgraded",
            "details": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"数据库升级失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库升级失败: {str(e)}")

@router.get("/config/status")
async def get_config_status():
    """获取配置状态"""
    try:
        from config.env_config_loader import config_loader
        
        # 获取各种配置
        configs = {}
        
        try:
            db_config = config_loader.get_database_config()
            configs["database"] = {
                "host": db_config.get("host"),
                "port": db_config.get("port"),
                "database": db_config.get("database"),
                "username": db_config.get("username"),
                "password": "***" if db_config.get("password") else None
            }
        except Exception as e:
            configs["database"] = {"error": str(e)}
        
        try:
            storage_config = config_loader.get_storage_config()
            configs["storage"] = {
                "type": storage_config.get("type"),
                "minio_endpoint": storage_config.get("minio", {}).get("endpoint"),
                "minio_bucket": storage_config.get("minio", {}).get("bucket")
            }
        except Exception as e:
            configs["storage"] = {"error": str(e)}
        
        try:
            redis_config = config_loader.get_redis_config()
            configs["redis"] = {
                "host": redis_config.get("host"),
                "port": redis_config.get("port"),
                "database": redis_config.get("database")
            }
        except Exception as e:
            configs["redis"] = {"error": str(e)}
        
        return {
            "configs": configs,
            "environment": config_loader.get_environment(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置状态失败: {str(e)}")

@router.get("/system/info")
async def get_system_info():
    """获取系统信息"""
    try:
        import psutil
        import platform
        
        # 系统信息
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }
        
        # CPU信息
        cpu_info = {
            "count": psutil.cpu_count(),
            "percent": psutil.cpu_percent(interval=1),
            "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }
        
        return {
            "system": system_info,
            "memory": memory_info,
            "cpu": cpu_info,
            "disk": disk_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

@router.get("/logs/recent")
async def get_recent_logs(limit: int = 100):
    """获取最近的日志"""
    try:
        # 这里可以实现从日志文件读取最近日志的逻辑
        # 暂时返回模拟数据
        return {
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "API服务运行正常",
                    "module": "system_management"
                }
            ],
            "total": 1,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        utils.logger.error(f"获取日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.post("/system/restart")
async def restart_system():
    """重启系统（仅开发环境）"""
    try:
        import os
        import signal
        
        # 检查是否为开发环境
        from config.env_config_loader import config_loader
        env = config_loader.get_environment()
        
        if env != "dev":
            raise HTTPException(status_code=403, detail="仅开发环境支持重启")
        
        # 获取当前进程ID
        pid = os.getpid()
        
        # 发送重启信号
        os.kill(pid, signal.SIGTERM)
        
        return {
            "message": "系统重启信号已发送",
            "pid": pid,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"重启系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"重启系统失败: {str(e)}") 