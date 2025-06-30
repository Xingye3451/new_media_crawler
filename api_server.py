# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import config
import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.zhihu import ZhihuCrawler
from proxy import proxy_router, ProxyManager
from login_api import login_router

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="多平台媒体内容爬虫API服务",
    version="1.0.0"
)

# 注册代理管理路由
app.include_router(proxy_router)

# 注册登录管理路由
app.include_router(login_router)

# 任务状态存储
task_status = {}

class CrawlerRequest(BaseModel):
    platform: str = Field(..., description="平台: xhs, dy, ks, bili, wb, tieba, zhihu")
    login_type: str = Field(default="qrcode", description="登录类型: qrcode, phone, cookie")
    crawler_type: str = Field(default="search", description="爬取类型: search, detail, creator")
    keywords: Optional[str] = Field(default="", description="搜索关键词")
    start_page: int = Field(default=1, description="开始页数")
    get_comments: bool = Field(default=True, description="是否爬取评论")
    get_sub_comments: bool = Field(default=False, description="是否爬取二级评论")
    save_data_option: str = Field(default="json", description="数据保存方式: csv, db, json")
    cookies: Optional[str] = Field(default="", description="Cookie字符串")
    specified_ids: Optional[List[str]] = Field(default=None, description="指定ID列表")
    max_notes_count: int = Field(default=200, description="最大爬取数量")
    enable_images: bool = Field(default=False, description="是否爬取图片")
    # 新增代理相关参数
    use_proxy: bool = Field(default=False, description="是否使用代理")
    proxy_strategy: str = Field(default="round_robin", description="代理策略: round_robin, random, weighted, failover, geo_based, smart")
    # 新增登录会话参数
    session_id: Optional[str] = Field(default=None, description="登录会话ID")

class CrawlerResponse(BaseModel):
    task_id: str
    status: str
    message: str
    data: Optional[Dict] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
        "wb": WeiboCrawler,
        "tieba": TieBaCrawler,
        "zhihu": ZhihuCrawler
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(f"不支持的平台: {platform}")
        return crawler_class()

async def run_crawler_task(task_id: str, request: CrawlerRequest):
    """后台运行爬虫任务"""
    try:
        # 更新任务状态
        task_status[task_id]["status"] = "running"
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 检查登录状态
        from login_manager import login_manager
        
        if request.session_id:
            # 使用指定的会话ID
            session = await login_manager.check_login_status(request.platform, request.session_id)
            if session.status.value == "not_logged_in" or session.status.value == "expired":
                # 需要重新登录
                task_status[task_id]["status"] = "need_login"
                task_status[task_id]["error"] = "需要重新登录"
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                return
            elif session.status.value == "need_verification":
                # 需要验证
                task_status[task_id]["status"] = "need_verification"
                task_status[task_id]["error"] = "需要手动验证"
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                return
            elif session.status.value == "logged_in":
                # 已登录，获取cookies
                cookies = await login_manager.get_session_cookies(request.session_id)
                if cookies:
                    # 将cookies转换为字符串格式
                    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                    config.COOKIES = cookie_str
        else:
            # 查找平台的最新会话
            session = await login_manager.check_login_status(request.platform)
            if session.status.value == "logged_in":
                # 已登录，获取cookies
                cookies = await login_manager.get_session_cookies(session.session_id)
                if cookies:
                    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                    config.COOKIES = cookie_str
            elif session.status.value in ["not_logged_in", "expired", "need_verification"]:
                # 需要登录或验证
                task_status[task_id]["status"] = "need_login"
                task_status[task_id]["error"] = "需要登录"
                task_status[task_id]["session_id"] = session.session_id
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                return
        
        # 配置爬虫参数
        config.PLATFORM = request.platform
        config.LOGIN_TYPE = request.login_type
        config.CRAWLER_TYPE = request.crawler_type
        config.KEYWORDS = request.keywords
        config.START_PAGE = request.start_page
        config.ENABLE_GET_COMMENTS = request.get_comments
        config.ENABLE_GET_SUB_COMMENTS = request.get_sub_comments
        config.SAVE_DATA_OPTION = request.save_data_option
        config.CRAWLER_MAX_NOTES_COUNT = request.max_notes_count
        config.ENABLE_GET_IMAGES = request.enable_images
        
        # 配置代理设置
        if request.use_proxy:
            config.ENABLE_IP_PROXY = True
            # 这里可以设置代理策略，具体实现需要在爬虫基类中支持
            # 暂时通过环境变量传递
            os.environ["PROXY_STRATEGY"] = request.proxy_strategy
        else:
            config.ENABLE_IP_PROXY = False
        
        # 设置指定ID列表
        if request.specified_ids:
            if request.platform == "xhs":
                config.XHS_SPECIFIED_NOTE_URL_LIST = request.specified_ids
            elif request.platform == "dy":
                config.DY_SPECIFIED_ID_LIST = request.specified_ids
            elif request.platform == "ks":
                config.KS_SPECIFIED_ID_LIST = request.specified_ids
            elif request.platform == "bili":
                config.BILI_SPECIFIED_ID_LIST = request.specified_ids
            elif request.platform == "wb":
                config.WEIBO_SPECIFIED_ID_LIST = request.specified_ids
            elif request.platform == "tieba":
                config.TIEBA_SPECIFIED_ID_LIST = request.specified_ids
            elif request.platform == "zhihu":
                config.ZHIHU_SPECIFIED_ID_LIST = request.specified_ids

        # 初始化数据库
        if config.SAVE_DATA_OPTION == "db":
            await db.init_db()

        # 创建爬虫实例并运行
        crawler = CrawlerFactory.create_crawler(platform=request.platform)
        await crawler.start()

        # 获取结果数据
        result_data = {}
        if config.SAVE_DATA_OPTION == "json":
            # 读取JSON文件
            data_file = f"data/{request.platform}_data.json"
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)

        # 更新任务状态为完成
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["result"] = result_data
        task_status[task_id]["updated_at"] = datetime.now().isoformat()

        # 关闭数据库连接
        if config.SAVE_DATA_OPTION == "db":
            await db.close()

    except Exception as e:
        # 更新任务状态为失败
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()

@app.post("/api/v1/crawler/start", response_model=CrawlerResponse)
async def start_crawler(request: CrawlerRequest, background_tasks: BackgroundTasks):
    """启动爬虫任务"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        task_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 在后台运行爬虫任务
        background_tasks.add_task(run_crawler_task, task_id, request)
        
        return CrawlerResponse(
            task_id=task_id,
            status="pending",
            message="爬虫任务已启动，正在检查登录状态..."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")

@app.get("/api/v1/crawler/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(**task_status[task_id])

@app.get("/api/v1/crawler/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {
        "tasks": list(task_status.values()),
        "total": len(task_status)
    }

@app.delete("/api/v1/crawler/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del task_status[task_id]
    return {"message": "任务已删除", "task_id": task_id}

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/v1/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": [
            {"code": "xhs", "name": "小红书", "description": "小红书笔记和评论爬取"},
            {"code": "dy", "name": "抖音", "description": "抖音视频和评论爬取"},
            {"code": "ks", "name": "快手", "description": "快手视频和评论爬取"},
            {"code": "bili", "name": "B站", "description": "B站视频和评论爬取"},
            {"code": "wb", "name": "微博", "description": "微博内容和评论爬取"},
            {"code": "tieba", "name": "贴吧", "description": "贴吧帖子和回复爬取"},
            {"code": "zhihu", "name": "知乎", "description": "知乎问答和评论爬取"}
        ]
    }

@app.get("/api/v1/proxy/quick-get")
async def quick_get_proxy(
    strategy_type: str = "round_robin",
    platform: str = None,
    check_availability: bool = True
):
    """快速获取代理"""
    try:
        proxy_manager = ProxyManager()
        proxy = await proxy_manager.get_proxy(strategy_type, platform=platform)
        
        if not proxy:
            return {"message": "没有可用的代理", "proxy": None}
        
        if check_availability:
            is_available = await proxy_manager.check_proxy(proxy)
            if not is_available:
                return {"message": "代理不可用", "proxy": None}
        
        return {
            "message": "获取代理成功",
            "proxy": {
                "id": proxy.id,
                "ip": proxy.ip,
                "port": proxy.port,
                "proxy_type": proxy.proxy_type,
                "country": proxy.country,
                "speed": proxy.speed,
                "anonymity": proxy.anonymity,
                "success_rate": proxy.success_rate
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理失败: {str(e)}")

@app.get("/api/v1/proxy/quick-stats")
async def quick_proxy_stats():
    """快速获取代理统计"""
    try:
        proxy_manager = ProxyManager()
        stats = await proxy_manager.get_proxy_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理统计失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 