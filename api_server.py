"""
MediaCrawler API 服务器
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import ValidationError as RequestValidationError
from datetime import datetime

import utils
import db
from var import media_crawler_db_var
from models.content_models import (
    CrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse,
    ContentListRequest, ContentListResponse, UnifiedContent
)

# 导入API路由
from api.routes import api_router

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="多平台媒体内容爬虫API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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

# 全局变量
task_status = {}
multi_platform_task_status = {}

# 异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors(),
            "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
    )

# 注册API路由
app.include_router(api_router, prefix="/api")

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    try:
        utils.logger.info("🚀 MediaCrawler API 服务启动中...")
        
        # 初始化数据库连接
        utils.logger.info("📊 初始化数据库连接...")
        await db.init_db()
        utils.logger.info("✅ 数据库连接初始化完成")
        
        # 初始化Redis连接
        utils.logger.info("📊 初始化Redis连接...")
        from utils.redis_manager import TaskResultRedisManager
        redis_manager = TaskResultRedisManager()
        await redis_manager.ping()
        utils.logger.info("✅ Redis连接初始化完成")
        
        # 初始化文件管理服务
        utils.logger.info("📁 初始化文件管理服务...")
        from services.file_management_service import FileManagementService
        file_service = FileManagementService()
        await file_service.initialize()
        utils.logger.info("✅ 文件管理服务初始化完成")
        
        # 加载配置
        utils.logger.info("⚙️ 加载配置...")
        from config.env_config_loader import config_loader
        env = config_loader.get_environment()
        utils.logger.info(f"✅ 配置加载完成，环境: {env}")
        
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
        utils.logger.info("📊 关闭数据库连接...")
        await db.close()
        utils.logger.info("✅ 数据库连接已关闭")
        
        # 关闭Redis连接
        utils.logger.info("📊 关闭Redis连接...")
        from utils.redis_manager import TaskResultRedisManager
        redis_manager = TaskResultRedisManager()
        await redis_manager.close()
        utils.logger.info("✅ Redis连接已关闭")
        
        utils.logger.info("👋 MediaCrawler API 服务已关闭")
        
    except Exception as e:
        utils.logger.error(f"❌ 服务关闭时发生错误: {e}")

# 根路径
@app.get("/")
async def root():
    """根路径 - 返回主页"""
    return FileResponse("static/index.html")

# API信息路径
@app.get("/api-info")
async def api_info():
    """API信息路径 - 返回API信息"""
    return {
        "name": "MediaCrawler API",
        "version": "1.0.0",
        "description": "多平台媒体内容爬虫API服务",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "redoc": "/redoc"
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db_status = "unknown"
        try:
            async_db_obj = media_crawler_db_var.get()
            if async_db_obj:
                await async_db_obj.query("SELECT 1")
                db_status = "connected"
            else:
                db_status = "not_initialized"
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
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 主函数
if __name__ == "__main__":
    import uvicorn
    
    # 启动服务器
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 