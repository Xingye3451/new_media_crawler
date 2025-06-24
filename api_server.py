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

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="多平台媒体内容爬虫API服务",
    version="1.0.0"
)

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
        
        # 配置爬虫参数
        config.PLATFORM = request.platform
        config.LOGIN_TYPE = request.login_type
        config.CRAWLER_TYPE = request.crawler_type
        config.KEYWORDS = request.keywords
        config.START_PAGE = request.start_page
        config.ENABLE_GET_COMMENTS = request.get_comments
        config.ENABLE_GET_SUB_COMMENTS = request.get_sub_comments
        config.SAVE_DATA_OPTION = request.save_data_option
        config.COOKIES = request.cookies
        config.CRAWLER_MAX_NOTES_COUNT = request.max_notes_count
        config.ENABLE_GET_IMAGES = request.enable_images
        
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
            message="爬虫任务已启动",
            data={"task_id": task_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/crawler/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(**task_status[task_id])

@app.get("/api/v1/crawler/tasks")
async def list_tasks():
    """列出所有任务"""
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
    return {"message": "任务已删除"}

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
        "platforms": list(CrawlerFactory.CRAWLERS.keys()),
        "descriptions": {
            "xhs": "小红书",
            "dy": "抖音",
            "ks": "快手",
            "bili": "B站",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 