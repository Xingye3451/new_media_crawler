"""
API路由聚合文件
集中管理所有API路由
"""

from fastapi import APIRouter

# 导入各个API路由模块
from api.task_results import router as task_results_router
from api.video_downloads import router as video_downloads_router
from api.file_management import router as file_management_router
from api.minio_management import router as minio_management_router
from api.task_management import router as task_management_router

# 创建主路由器
api_router = APIRouter()

# 任务结果相关路由
api_router.include_router(
    task_results_router,
    prefix="/v1",
    tags=["task-results"]
)

# 视频下载相关路由  
api_router.include_router(
    video_downloads_router,
    prefix="/v1",
    tags=["video-downloads"]
)

# 文件管理相关路由
api_router.include_router(
    file_management_router,
    prefix="/v1",
    tags=["file-management"]
)

# MinIO存储管理相关路由
api_router.include_router(
    minio_management_router,
    prefix="/v1",
    tags=["minio-management"]
)

# 任务管理相关路由
api_router.include_router(
    task_management_router,
    prefix="/v1",
    tags=["task-management"]
) 