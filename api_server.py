"""
MediaCrawler API 服务器
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import ValidationError as RequestValidationError
from datetime import datetime, timedelta
import asyncio
import os
from pathlib import Path

import utils
import db
from tools.time_util import get_isoformat_utc8
from var import media_crawler_db_var
from models.content_models import (
    CrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse,
    ContentListRequest, ContentListResponse, UnifiedContent
)

# 导入API路由
from api.routes import api_router

# 预留：导入认证中间件
from middleware.auth_middleware import auth_middleware, enable_auth_middleware, disable_auth_middleware

def get_app_version():
    """获取应用版本信息"""
    try:
        # 首先尝试从环境变量获取版本
        env_version = os.environ.get('APP_VERSION')
        if env_version:
            return env_version
        
        # 然后尝试从 VERSION 文件读取
        version_file = Path("VERSION")
        if version_file.exists():
            with open(version_file, 'r', encoding='utf-8') as f:
                version = f.read().strip()
                return version
        
        # 最后使用默认版本
        return "v1.0.0"
    except Exception as e:
        utils.logger.warning(f"无法读取版本信息: {e}")
        return "v1.0.0"

def get_build_info():
    """获取构建信息"""
    return {
        "version": get_app_version(),
        "build_date": os.environ.get('BUILD_DATE', 'unknown'),
        "git_commit": os.environ.get('VCS_REF', 'unknown'),
        "environment": os.environ.get('ENV', 'development')
    }

# 获取版本信息
app_version = get_app_version()
build_info = get_build_info()

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="多平台媒体内容爬虫API服务",
    version=app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 预留：添加认证中间件（当前禁用）
# app.middleware("http")(auth_middleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="static/images"), name="images")


# 全局变量
task_status = {}
multi_platform_task_status = {}


async def cleanup_old_logs():
    """清理过期的日志文件"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return
        
        # 从配置文件读取保留天数
        retention_days = 15  # 默认值
        try:
            from config.config_manager import config_manager
            retention_days = config_manager.get("logging.retention_days", 15)
        except Exception as e:
            utils.logger.warning(f"无法从配置文件读取日志保留天数，使用默认值15天: {e}")
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        total_size = 0
        
        utils.logger.debug(f"开始清理过期日志文件，保留天数: {retention_days}")
        
        for log_file in logs_dir.glob("*.log"):
            try:
                # 尝试从文件名中提取日期
                file_date_str = log_file.stem.split('_')[-1] if '_' in log_file.stem else None
                should_delete = False
                
                if file_date_str:
                    try:
                        file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                        should_delete = file_date < cutoff_date
                    except ValueError:
                        # 如果无法解析日期，使用文件修改时间
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        should_delete = file_mtime < cutoff_date
                else:
                    # 如果文件名中没有日期，使用文件修改时间
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    should_delete = file_mtime < cutoff_date
                
                if should_delete:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                    utils.logger.debug(f"已删除过期日志文件: {log_file.name} (大小: {file_size / 1024 / 1024:.2f}MB)")
                
            except Exception as e:
                utils.logger.error(f"处理日志文件 {log_file} 时出错: {e}")
        
        if deleted_count > 0:
            utils.logger.info(f"日志清理完成，共删除 {deleted_count} 个过期文件，释放空间: {total_size / 1024 / 1024:.2f}MB")
        else:
            utils.logger.debug("没有需要清理的过期日志文件")
            
    except Exception as e:
        utils.logger.error(f"清理日志文件时出错: {e}")


async def log_cleanup_scheduler():
    """日志清理定时任务"""
    while True:
        try:
            # 计算到下一个凌晨的时间
            now = datetime.now()
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)  # 凌晨2点执行
            if next_run <= now:
                next_run += timedelta(days=1)
            
            # 等待到下次执行时间
            wait_seconds = (next_run - now).total_seconds()
            utils.logger.debug(f"日志清理定时任务将在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 执行")
            await asyncio.sleep(wait_seconds)
            
            # 执行日志清理
            await cleanup_old_logs()
            
        except Exception as e:
            utils.logger.error(f"日志清理定时任务出错: {e}")
            # 出错后等待1小时再重试
            await asyncio.sleep(3600)


# 异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors(),
            "timestamp": get_isoformat_utc8()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    utils.logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "error": str(exc),
            "timestamp": get_isoformat_utc8()
        }
    )

# 注册API路由
app.include_router(api_router, prefix="/api")

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    try:
        # 显示版本信息
        utils.logger.info("🚀 MediaCrawler API 服务启动中...")
        utils.logger.debug(f"📦 版本信息:")
        utils.logger.debug(f"   - 应用版本: {build_info['version']}")
        utils.logger.debug(f"   - 构建日期: {build_info['build_date']}")
        utils.logger.debug(f"   - Git提交: {build_info['git_commit']}")
        utils.logger.debug(f"   - 运行环境: {build_info['environment']}")
        
        # 初始化数据库连接
        await db.init_db()
        utils.logger.info("✅ 数据库连接初始化完成")
        
        # 初始化Redis连接
        from utils.redis_manager import TaskResultRedisManager
        redis_manager = TaskResultRedisManager()
        await redis_manager.ping()
        utils.logger.info("✅ Redis连接初始化完成")
        
        # 🆕 启动任务清理机制
        try:
            from api.task_cleanup_init import init_task_cleanup
            await init_task_cleanup()
            utils.logger.debug("✅ 任务清理机制初始化完成")
        except Exception as e:
            utils.logger.warning(f"⚠️ 任务清理机制初始化失败: {e}")
        
        # 🆕 启动任务隔离管理器
        try:
            from utils.task_isolation import task_isolation_manager, start_task_cleanup
            import asyncio
            asyncio.create_task(start_task_cleanup())
            utils.logger.debug("✅ 任务隔离管理器初始化完成")
        except Exception as e:
            utils.logger.warning(f"⚠️ 任务隔离管理器初始化失败: {e}")
        
        # 🆕 启动日志清理定时任务
        try:
            asyncio.create_task(log_cleanup_scheduler())
            utils.logger.debug("✅ 日志清理定时任务已启动（每天凌晨2点执行）")
        except Exception as e:
            utils.logger.warning(f"⚠️ 日志清理定时任务启动失败: {e}")
        
        # 🆕 启动定时任务调度器
        try:
            from timetask.task_scheduler import scheduler
            await scheduler.start()
            utils.logger.debug("✅ 定时任务调度器已启动")
        except Exception as e:
            utils.logger.warning(f"⚠️ 定时任务调度器启动失败: {e}")
        
        # 加载配置
        from config.env_config_loader import config_loader
        env = config_loader.get_environment()
        utils.logger.debug(f"✅ 配置加载完成，环境: {env}")
        
        # 🆕 预留：配置认证中间件
        try:
            from config.base_config import AUTH_MIDDLEWARE_ENABLED
            if AUTH_MIDDLEWARE_ENABLED:
                enable_auth_middleware()
                utils.logger.debug("✅ 认证中间件已启用")
            else:
                utils.logger.debug("ℹ️ 认证中间件已禁用（预留功能）")
        except Exception as e:
            utils.logger.warning(f"⚠️ 认证中间件配置失败: {e}")
        
        utils.logger.info("🎉 MediaCrawler API 服务启动完成!")
        
    except Exception as e:
        utils.logger.error(f"❌ 服务启动失败: {e}")
        raise

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    try:
        utils.logger.info("🛑 MediaCrawler API 服务关闭中...")
        
        # 关闭数据库连接
        await db.close()
        utils.logger.info("✅ 数据库连接已关闭")
        
        # 关闭Redis连接
        from utils.redis_manager import TaskResultRedisManager
        redis_manager = TaskResultRedisManager()
        await redis_manager.close()
        utils.logger.info("✅ Redis连接已关闭")
        
        # 🆕 停止定时任务调度器
        try:
            from timetask.task_scheduler import scheduler
            await scheduler.stop()
            utils.logger.info("✅ 定时任务调度器已停止")
        except Exception as e:
            utils.logger.warning(f"⚠️ 停止定时任务调度器失败: {e}")
        
        utils.logger.info("👋 MediaCrawler API 服务已关闭")
        
    except Exception as e:
        utils.logger.error(f"❌ 服务关闭时发生错误: {e}")

# 根路径
@app.get("/")
async def root():
    """根路径 - 返回主页"""
    return FileResponse("static/index.html")

# 任务详情页面
@app.get("/task_detail.html")
async def task_detail_page():
    """任务详情页面"""
    return FileResponse("static/task_detail.html")

# 任务结果页面
@app.get("/task_results.html")
async def task_results_page():
    """任务结果页面"""
    return FileResponse("static/task_results.html")

# 账号管理页面
@app.get("/account_management.html")
async def account_management_page():
    """账号管理页面"""
    return FileResponse("static/account_management.html")

# 视频预览页面
@app.get("/video_preview.html")
async def video_preview_page():
    """视频预览页面"""
    return FileResponse("static/video_preview.html")

# 文件管理页面 (已替换为视频收藏管理)
@app.get("/file_management.html")
async def file_management_page():
    """文件管理页面 - 重定向到视频收藏"""
    return FileResponse("static/video_favorites.html")

# API测试页面
@app.get("/api_test.html")
async def api_test_page():
    """API测试页面"""
    return FileResponse("static/api_test.html")

# API信息路径
@app.get("/api-info")
async def api_info():
    """API信息路径 - 返回API信息"""
    return {
        "name": "MediaCrawler API",
        "version": build_info['version'],
        "description": "多平台媒体内容爬虫API服务",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "build_info": build_info,
        "docs": "/docs",
        "redoc": "/redoc"
    }

# 版本信息路径
@app.get("/version")
async def version_info():
    """版本信息路径 - 返回详细的版本信息"""
    return {
        "version": build_info['version'],
        "build_date": build_info['build_date'],
        "git_commit": build_info['git_commit'],
        "environment": build_info['environment'],
        "timestamp": datetime.now().isoformat()
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db_status = "unknown"
        try:
            # 直接创建数据库连接进行测试
            from config.env_config_loader import config_loader
            from async_db import AsyncMysqlDB
            import aiomysql
            
            db_config = config_loader.get_database_config()
            
            pool = await aiomysql.create_pool(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['username'],
                password=db_config['password'],
                db=db_config['database'],
                autocommit=True,
                minsize=1,
                maxsize=5,
            )
            
            async_db_obj = AsyncMysqlDB(pool)
            await async_db_obj.query("SELECT 1")
            await pool.close()
            db_status = "connected"
            
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # 检查Redis连接
        redis_status = "unknown"
        try:
            from utils.redis_manager import TaskResultRedisManager
            redis_manager = TaskResultRedisManager()
            await redis_manager.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
        
        overall_status = "healthy" if all(
            status == "connected" 
            for status in [db_status, redis_status]
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "version": build_info['version'],
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": db_status,
                "redis": redis_status
            }
        }
        
    except Exception as e:
        utils.logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "version": build_info['version'],
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 主函数
if __name__ == "__main__":
    import uvicorn
    
    # 显示启动信息（简化版）
    print("🚀 MediaCrawler API 服务器启动中...")
    print(f"📦 版本: {build_info['version']}")
    print("=" * 40)
    
    # 启动服务器
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 