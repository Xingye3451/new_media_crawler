"""
API路由聚合文件
集中管理所有API路由
"""

from fastapi import APIRouter

# 导入各个API路由模块
from api.task_results import router as task_results_router
from api.video_downloads import router as video_downloads_router
# from api.file_management import router as file_management_router  # 已删除，替换为视频收藏管理
from api.minio_management import router as minio_management_router
from api.task_management import router as task_management_router
from api.crawler_core import router as crawler_core_router
from api.crawler_control import router as crawler_control_router
from api.config_management import router as config_management_router
from api.content_management import router as content_management_router
from api.platform_management import router as platform_management_router
from api.system_management import router as system_management_router
from api.account_management import account_router
from api.login_management import login_router
from api.curl_video_proxy import router as curl_video_proxy_router
from api.video_favorites import router as video_favorites_router
from api.video_stream import router as video_stream_router
from api.thumbnail_proxy import router as thumbnail_proxy_router
from api.creator_management import router as creator_management_router
from api.multi_platform_crawler import router as multi_platform_crawler_router
from api.system_monitor import router as system_monitor_router
from api.task_isolation import router as task_isolation_router

# 创建主路由器
api_router = APIRouter()

# 爬虫核心路由
api_router.include_router(
    crawler_core_router,
    prefix="/v1",
    tags=["crawler-core"]
)

# 爬虫控制路由 - 新增
api_router.include_router(
    crawler_control_router,
    prefix="/v1",
    tags=["crawler-control"]
)

# 配置管理路由 - 新增
api_router.include_router(
    config_management_router,
    prefix="/v1",
    tags=["config-management"]
)

# 内容管理路由
api_router.include_router(
    content_management_router,
    prefix="/v1",
    tags=["content-management"]
)

# 平台管理路由
api_router.include_router(
    platform_management_router,
    prefix="/v1",
    tags=["platform-management"]
)

# 系统管理路由
api_router.include_router(
    system_management_router,
    prefix="/v1",
    tags=["system-management"]
)

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

# 文件管理相关路由 (已替换为视频收藏管理)
# api_router.include_router(
#     file_management_router,
#     prefix="/v1",
#     tags=["file-management"]
# )

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

# 账号管理相关路由
api_router.include_router(
    account_router,
    prefix="/v1",
    tags=["account-management"]
)

# 登录管理相关路由
api_router.include_router(
    login_router,
    prefix="/v1",
    tags=["login-management"]
)

# 视频代理相关路由
api_router.include_router(
    curl_video_proxy_router,
    prefix="/v1",
    tags=["video-proxy"]
)

# 视频收藏相关路由
api_router.include_router(
    video_favorites_router,
    prefix="/v1",
    tags=["video-favorites"]
)

# 视频流相关路由
api_router.include_router(
    video_stream_router,
    prefix="/v1",
    tags=["video-stream"]
)

# 缩略图代理相关路由
api_router.include_router(
    thumbnail_proxy_router,
    prefix="/v1",
    tags=["thumbnail-proxy"]
)

# 创作者管理相关路由
api_router.include_router(
    creator_management_router,
    prefix="/v1",
    tags=["creator-management"]
)

# 多平台爬取相关路由
api_router.include_router(
    multi_platform_crawler_router,
    prefix="/v1",
    tags=["multi-platform-crawler"]
)

# 系统监控相关路由
api_router.include_router(
    system_monitor_router,
    prefix="/v1",
    tags=["system-monitor"]
)

# 任务隔离相关路由
api_router.include_router(
    task_isolation_router,
    prefix="/v1",
    tags=["task-isolation"]
) 