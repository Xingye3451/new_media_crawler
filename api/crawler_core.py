"""
爬虫核心路由模块
包含爬虫任务启动、状态查询等核心功能
"""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from tools import utils
from var import media_crawler_db_var

# 添加独立的数据库连接函数
async def get_db_connection():
    """获取数据库连接"""
    try:
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
            maxsize=10,
        )
        
        async_db_obj = AsyncMysqlDB(pool)
        return async_db_obj
        
    except Exception as e:
        utils.logger.error(f"获取数据库连接失败: {e}")
        return None

from models.content_models import (
    CrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse
)

router = APIRouter()

# 全局任务状态存储
task_status = {}

class PlatformComingSoonException(Exception):
    """平台即将支持异常"""
    pass

class CrawlerFactory:
    # 视频优先平台 - 当前支持
    VIDEO_PLATFORMS = ["xhs", "dy", "ks", "bili"]
    
    # 文字平台 - 即将支持
    COMING_SOON_PLATFORMS = {
        "wb": "微博",
        "tieba": "贴吧", 
        "zhihu": "知乎"
    }

    @staticmethod
    def _get_crawler_class(platform: str):
        """延迟导入爬虫类 - 仅支持视频平台"""
        if platform == "xhs":
            from media_platform.xhs import XiaoHongShuCrawler
            return XiaoHongShuCrawler
        elif platform == "dy":
            from media_platform.douyin import DouYinCrawler
            return DouYinCrawler
        elif platform == "ks":
            from media_platform.kuaishou import KuaishouCrawler
            return KuaishouCrawler
        elif platform == "bili":
            from media_platform.bilibili import BilibiliCrawler
            return BilibiliCrawler
        else:
            raise ValueError(f"不支持的平台: {platform}")

    @staticmethod
    def create_crawler(platform: str, task_id: str = None):
        # 检查是否为即将支持的平台
        if platform in CrawlerFactory.COMING_SOON_PLATFORMS:
            platform_name = CrawlerFactory.COMING_SOON_PLATFORMS[platform]
            raise PlatformComingSoonException(f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。")
        
        # 检查是否为支持的视频平台
        crawler_class = CrawlerFactory._get_crawler_class(platform)
        return crawler_class(task_id=task_id)

async def create_task_record(task_id: str, request: CrawlerRequest) -> None:
    """创建任务记录到数据库"""
    try:
        # 获取数据库连接
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[TASK_RECORD] 无法获取数据库连接")
            return
        
        # 构建任务参数JSON
        task_params = {
            "platform": request.platform,
            "keywords": request.keywords,
            "max_count": request.max_notes_count,
            "account_id": request.account_id,
            "session_id": request.session_id,
            "login_type": request.login_type,
            "crawler_type": request.crawler_type,
            "get_comments": request.get_comments,
            "save_data_option": request.save_data_option,
            "use_proxy": request.use_proxy,
            "proxy_strategy": request.proxy_strategy
        }
        
        # 使用字典方式构建数据
        task_data = {
            'id': task_id,
            'platform': request.platform,
            'task_type': 'single_platform',
            'keywords': request.keywords,
            'status': 'pending',
            'progress': 0.0,
            'result_count': 0,
            'error_message': None,
            'user_id': None,
            'params': json.dumps(task_params),
            'priority': 0,
            'is_favorite': False,
            'deleted': False,
            'is_pinned': False,
            'ip_address': None,
            'user_security_id': None,
            'user_signature': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'started_at': None,
            'completed_at': None
        }
        
        # 使用item_to_table方法，更安全
        await async_db_obj.item_to_table('crawler_tasks', task_data)
        
        utils.logger.info(f"[TASK_RECORD] 任务记录创建成功: {task_id}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_RECORD] 创建任务记录失败: {e}")
        raise

async def update_task_progress(task_id: str, progress: float, status: str = None, result_count: int = None):
    """更新任务进度"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[TASK_PROGRESS] 无法获取数据库连接")
            return
        
        # 构建更新数据字典
        update_data = {
            'progress': progress,
            'updated_at': datetime.now()
        }
        
        if status:
            update_data['status'] = status
        
        if result_count is not None:
            update_data['result_count'] = result_count
        
        # 使用update_table方法
        await async_db_obj.update_table('crawler_tasks', update_data, 'id', task_id)
        
        utils.logger.info(f"[TASK_PROGRESS] 任务进度更新: {task_id}, 进度: {progress}, 状态: {status}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_PROGRESS] 更新任务进度失败: {e}")

async def log_task_step(task_id: str, platform: str, step: str, message: str, log_level: str = "INFO", progress: int = None):
    """记录任务步骤日志"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[TASK_LOG] 无法获取数据库连接")
            return
        
        # 构建日志数据字典
        log_data = {
            'task_id': task_id,
            'platform': platform,
            'account_id': None,
            'log_level': log_level,
            'message': message,
            'step': step,
            'progress': progress or 0,
            'created_at': datetime.now()
        }
        
        # 使用item_to_table方法
        await async_db_obj.item_to_table('crawler_task_logs', log_data)
        
        utils.logger.info(f"[TASK_LOG] {task_id} - {step}: {message}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_LOG] 记录任务日志失败: {e}")

async def run_crawler_task(task_id: str, request: CrawlerRequest):
    """后台运行爬虫任务"""
    try:
        utils.logger.info("█" * 100)
        utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬虫任务")
        utils.logger.info(f"[TASK_{task_id}] 📝 请求参数详情:")
        utils.logger.info(f"[TASK_{task_id}]   ├─ platform: {request.platform}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ keywords: {request.keywords}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ max_count: {request.max_notes_count}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ account_id: {request.account_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ session_id: {request.session_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ login_type: {request.login_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ crawler_type: {request.crawler_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ get_comments: {request.get_comments}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ save_data_option: {request.save_data_option}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ use_proxy: {request.use_proxy}")
        utils.logger.info(f"[TASK_{task_id}]   └─ proxy_strategy: {request.proxy_strategy}")
        
        # 🆕 初始化数据库连接（确保上下文变量可用）
        utils.logger.info(f"[TASK_{task_id}] 📊 初始化数据库连接...")
        try:
            from db import init_mediacrawler_db
            await init_mediacrawler_db()
            utils.logger.info(f"[TASK_{task_id}] ✅ 数据库连接初始化完成")
        except Exception as e:
            utils.logger.error(f"[TASK_{task_id}] ❌ 数据库连接初始化失败: {e}")
            # 继续执行，因为有些存储方式可能不需要数据库
        
        # 🆕 创建任务记录到数据库
        utils.logger.info(f"[TASK_{task_id}] 📝 创建任务记录到数据库...")
        await create_task_record(task_id, request)
        utils.logger.info(f"[TASK_{task_id}] ✅ 任务记录创建成功")
        
        # 更新任务状态
        utils.logger.info(f"[TASK_{task_id}] 🔄 更新任务状态为运行中...")
        task_status[task_id]["status"] = "running"
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        utils.logger.info(f"[TASK_{task_id}] ✅ 任务状态已更新")
        
        # 🆕 更新数据库中的任务状态
        await update_task_progress(task_id, 0.0, "running")
        await log_task_step(task_id, request.platform, "task_start", "任务开始执行", "INFO", 0)
        
        # 设置爬虫配置
        utils.logger.info(f"[TASK_{task_id}] ⚙️ 设置爬虫配置...")
        await log_task_step(task_id, request.platform, "config_setup", "设置爬虫配置", "INFO", 35)
        
        import config
        config.PLATFORM = request.platform
        config.ENABLE_GET_COMMENTS = request.get_comments
        config.SAVE_DATA_OPTION = request.save_data_option
        
        # 创建爬虫实例
        utils.logger.info(f"[TASK_{task_id}] 🔧 创建爬虫实例...")
        await log_task_step(task_id, request.platform, "crawler_init", "创建爬虫实例", "INFO", 40)
        
        try:
            crawler = CrawlerFactory.create_crawler(request.platform, task_id=task_id)
            utils.logger.info(f"[TASK_{task_id}] ✅ 爬虫实例创建成功")
            await log_task_step(task_id, request.platform, "crawler_ready", "爬虫实例就绪", "INFO", 45)
        except PlatformComingSoonException as e:
            utils.logger.warning(f"[TASK_{task_id}] ⚠️ 平台即将支持: {e}")
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = str(e)
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.0, "failed")
            await log_task_step(task_id, request.platform, "platform_coming_soon", str(e), "WARN", 0)
            return
        except Exception as e:
            utils.logger.error(f"[TASK_{task_id}] ❌ 创建爬虫实例失败: {e}")
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = f"创建爬虫实例失败: {str(e)}"
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.0, "failed")
            await log_task_step(task_id, request.platform, "crawler_init_failed", f"创建爬虫实例失败: {str(e)}", "ERROR", 0)
            return
        
        # 开始爬取
        utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬取...")
        await log_task_step(task_id, request.platform, "crawling_start", "开始执行爬取", "INFO", 50)
        
        try:
            # 根据爬虫类型执行不同的爬取逻辑
            if request.crawler_type == "search":
                results = await crawler.search_by_keywords(
                    keywords=request.keywords,
                    max_count=request.max_notes_count,
                    account_id=request.account_id,
                    session_id=request.session_id,
                    login_type=request.login_type,
                    get_comments=request.get_comments,
                    save_data_option=request.save_data_option,
                    use_proxy=request.use_proxy,
                    proxy_strategy=request.proxy_strategy
                )
            elif request.crawler_type == "user":
                results = await crawler.get_user_notes(
                    user_id=request.keywords,  # 这里keywords实际上是user_id
                    max_count=request.max_notes_count,
                    account_id=request.account_id,
                    session_id=request.session_id,
                    login_type=request.login_type,
                    get_comments=request.get_comments,
                    save_data_option=request.save_data_option,
                    use_proxy=request.use_proxy,
                    proxy_strategy=request.proxy_strategy
                )
            else:
                raise ValueError(f"不支持的爬虫类型: {request.crawler_type}")
            
            # 更新任务状态
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["result_count"] = len(results) if results else 0
            task_status[task_id]["results"] = results
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            
            await update_task_progress(task_id, 100.0, "completed", len(results) if results else 0)
            await log_task_step(task_id, request.platform, "crawling_completed", f"爬取完成，共获取 {len(results) if results else 0} 条数据", "INFO", 100)
            
            utils.logger.info(f"[TASK_{task_id}] ✅ 爬取任务完成，共获取 {len(results) if results else 0} 条数据")
            
        except Exception as e:
            utils.logger.error(f"[TASK_{task_id}] ❌ 爬取过程中发生错误: {e}")
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = f"爬取失败: {str(e)}"
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.0, "failed")
            await log_task_step(task_id, request.platform, "crawling_failed", f"爬取失败: {str(e)}", "ERROR", 0)
            raise
        
    except Exception as e:
        utils.logger.error("█" * 100)
        utils.logger.error(f"[TASK_{task_id}] ❌ 爬虫任务执行失败")
        utils.logger.error(f"[TASK_{task_id}] 🐛 错误详情: {e}")
        utils.logger.error(f"[TASK_{task_id}] 📍 错误类型: {type(e).__name__}")
        utils.logger.error(f"[TASK_{task_id}] 📊 错误堆栈:")
        import traceback
        utils.logger.error(f"[TASK_{task_id}] {traceback.format_exc()}")
        
        # 更新任务状态为失败
        utils.logger.error(f"[TASK_{task_id}] 🔄 更新任务状态为失败...")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 0.0, "failed")
        await log_task_step(task_id, request.platform, "task_failed", f"任务执行失败: {str(e)}", "ERROR", 0)
        utils.logger.error(f"[TASK_{task_id}] ✅ 任务状态已更新")
        utils.logger.error("█" * 100)

@router.post("/crawler/start", response_model=CrawlerResponse)
async def start_crawler(request: CrawlerRequest, background_tasks: BackgroundTasks):
    """启动单平台爬虫任务"""
    try:
        utils.logger.info("=" * 100)
        utils.logger.info("[CRAWLER_START] 收到爬虫任务启动请求")
        utils.logger.info(f"[CRAWLER_START] 平台: {request.platform}")
        utils.logger.info(f"[CRAWLER_START] 关键词: {request.keywords}")
        utils.logger.info(f"[CRAWLER_START] 最大数量: {request.max_notes_count}")
        
        # 参数验证
        utils.logger.info("[CRAWLER_START] 参数验证通过")
        
        # 🆕 检查登录状态 - 在任务启动前检查
        utils.logger.info("[CRAWLER_START] 检查登录状态...")
        
        # 直接调用登录检查API
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8100/api/v1/login/check",
                    json={"platform": request.platform},
                    timeout=10.0
                )
                login_result = response.json()
        except Exception as e:
            utils.logger.error(f"[CRAWLER_START] 登录检查API调用失败: {e}")
            login_result = {"code": 500, "message": f"登录检查失败: {str(e)}"}
        
        if login_result["code"] != 200:
            utils.logger.warning(f"[CRAWLER_START] 平台 {request.platform} 未登录，状态: {login_result.get('message', 'unknown')}")
            
            # 返回需要登录的错误信息
            error_message = f"平台 {request.platform} 需要登录，请先进行远程登录"
            
            return CrawlerResponse(
                task_id="",
                status="need_login",
                message=error_message,
                data={
                    "platform": request.platform,
                    "login_status": "not_logged_in",
                    "redirect_url": "/static/account_management.html"
                }
            )
        
        utils.logger.info(f"[CRAWLER_START] 平台 {request.platform} 登录状态正常")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        utils.logger.info(f"[CRAWLER_START] 生成任务ID: {task_id}")
        
        # 初始化任务状态
        task_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "platform": request.platform,
            "keywords": request.keywords,
            "max_count": request.max_notes_count,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "progress": 0.0,
            "result_count": 0,
            "results": None,
            "error": None
        }
        utils.logger.info("[CRAWLER_START] 任务状态已初始化")
        
        # 添加后台任务
        background_tasks.add_task(run_crawler_task, task_id, request)
        utils.logger.info("[CRAWLER_START] 后台任务已添加")
        
        # 构建响应数据
        response_data = {
            "task_id": task_id,
            "status": "pending",
            "message": "爬虫任务已启动，正在执行...",
            "data": None
        }
        utils.logger.info(f"[CRAWLER_START] 响应数据: {response_data}")
        utils.logger.info("=" * 100)
        
        return CrawlerResponse(**response_data)
        
    except Exception as e:
        utils.logger.error(f"[CRAWLER_START] 启动爬虫任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动爬虫任务失败: {str(e)}")

@router.get("/crawler/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(**task_status[task_id])

@router.get("/crawler/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {
        "tasks": list(task_status.values()),
        "total": len(task_status)
    }

@router.delete("/crawler/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del task_status[task_id]
    return {"message": "任务已删除"} 