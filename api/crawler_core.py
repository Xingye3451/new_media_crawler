"""
爬虫核心路由模块
包含爬虫任务启动、状态查询等核心功能
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

import utils
from models.content_models import (
    CrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse
)
from var import media_crawler_db_var

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
    def create_crawler(platform: str):
        # 检查是否为即将支持的平台
        if platform in CrawlerFactory.COMING_SOON_PLATFORMS:
            platform_name = CrawlerFactory.COMING_SOON_PLATFORMS[platform]
            raise PlatformComingSoonException(f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。")
        
        # 检查是否为支持的视频平台
        crawler_class = CrawlerFactory._get_crawler_class(platform)
        return crawler_class()

async def create_task_record(task_id: str, request: CrawlerRequest) -> None:
    """创建任务记录到数据库"""
    try:
        # 获取数据库连接
        async_db_obj = media_crawler_db_var.get()
        if not async_db_obj:
            utils.logger.error("[TASK_RECORD] 数据库连接未初始化")
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
        
        sql = """
        INSERT INTO crawler_tasks (
            task_id, platform, task_type, keywords, status, progress,
            user_id, task_params, priority, is_favorite, deleted, is_pinned,
            ip_address, user_security_id, user_signature, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            NOW(), NOW()
        )
        """
        
        import json
        await async_db_obj.execute(sql, (
            task_id,
            request.platform,
            "single_platform",
            request.keywords,
            "pending",
            0.0,
            None,  # user_id
            json.dumps(task_params),
            0,  # priority
            False,  # is_favorite
            False,  # deleted
            False,  # is_pinned
            None,  # ip_address
            None,  # user_security_id
            None,  # user_signature
        ))
        
        utils.logger.info(f"[TASK_RECORD] 任务记录创建成功: {task_id}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_RECORD] 创建任务记录失败: {e}")
        raise

async def update_task_progress(task_id: str, progress: float, status: str = None, result_count: int = None):
    """更新任务进度"""
    try:
        update_fields = ["progress = %s"]
        update_values = [progress]
        
        if status:
            update_fields.append("status = %s")
            update_values.append(status)
        
        if result_count is not None:
            update_fields.append("result_count = %s")
            update_values.append(result_count)
        
        update_fields.append("updated_at = NOW()")
        update_values.append(task_id)
        
        async_db_obj = media_crawler_db_var.get()
        sql = f"UPDATE crawler_tasks SET {', '.join(update_fields)} WHERE task_id = %s"
        await async_db_obj.execute(sql, update_values)
        
        utils.logger.info(f"[TASK_PROGRESS] 任务进度更新: {task_id}, 进度: {progress}, 状态: {status}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_PROGRESS] 更新任务进度失败: {e}")

async def log_task_step(task_id: str, platform: str, step: str, message: str, log_level: str = "INFO", progress: int = None):
    """记录任务步骤日志"""
    try:
        sql = """
        INSERT INTO crawler_task_logs (
            task_id, platform, account_id, log_level, message, step, progress, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        async_db_obj = media_crawler_db_var.get()
        await async_db_obj.execute(sql, (
            task_id,
            platform,
            None,  # account_id
            log_level,
            message,
            step,
            progress or 0
        ))
        
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
        
        # 检查登录状态
        utils.logger.info(f"[任务 {task_id}] 检查登录状态...")
        await log_task_step(task_id, request.platform, "login_check", "检查登录状态", "INFO", 10)
        
        from login_manager import login_manager
        
        if request.session_id:
            utils.logger.info(f"[任务 {task_id}] 使用指定的会话ID: {request.session_id}")
            # 使用指定的会话ID
            session = await login_manager.check_login_status(request.platform, request.session_id)
            if session.status.value == "need_verification":
                utils.logger.warning(f"[任务 {task_id}] 需要验证，会话状态: {session.status.value}")
                task_status[task_id]["status"] = "need_verification"
                task_status[task_id]["error"] = "需要验证"
                task_status[task_id]["session_id"] = session.session_id
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "need_verification")
                await log_task_step(task_id, request.platform, "login_failed", "需要验证", "WARN", 0)
                return
            elif session.status.value == "logged_in":
                utils.logger.info(f"[任务 {task_id}] 会话状态正常")
                await log_task_step(task_id, request.platform, "login_success", "登录状态正常", "INFO", 20)
                # 已登录，cookies由爬虫直接从数据库读取
            else:
                utils.logger.warning(f"[任务 {task_id}] 会话状态异常: {session.status.value}")
                await log_task_step(task_id, request.platform, "login_error", f"会话状态异常: {session.status.value}", "ERROR", 0)
        else:
            utils.logger.info(f"[任务 {task_id}] 查找平台 {request.platform} 的最新会话")
            # 查找平台的最新会话
            session = await login_manager.check_login_status(request.platform)
            if session.status.value == "logged_in":
                utils.logger.info(f"[任务 {task_id}] 找到有效会话")
                await log_task_step(task_id, request.platform, "login_success", "找到有效会话", "INFO", 20)
                # 已登录，cookies由爬虫直接从数据库读取
            elif session.status.value in ["not_logged_in", "expired", "need_verification"]:
                utils.logger.warning(f"[任务 {task_id}] 需要登录，会话状态: {session.status.value}")
                # 需要登录或验证
                task_status[task_id]["status"] = "need_login"
                task_status[task_id]["error"] = "需要登录"
                task_status[task_id]["session_id"] = session.session_id
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "need_login")
                await log_task_step(task_id, request.platform, "login_failed", "需要登录", "WARN", 0)
                return
                
        # 检查指定账号的凭证有效性（如果提供了账号ID）
        if request.account_id:
            utils.logger.info(f"[任务 {task_id}] 检查指定账号凭证有效性: {request.account_id}")
            await log_task_step(task_id, request.platform, "account_check", f"检查账号凭证: {request.account_id}", "INFO", 25)
            
            from api.login_management import check_token_validity
            validity = await check_token_validity(request.platform, request.account_id)
            if validity["status"] not in ["valid", "expiring_soon"]:
                utils.logger.error(f"[任务 {task_id}] 指定账号凭证无效: {validity['message']}")
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = f"指定账号凭证无效: {validity['message']}"
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "failed")
                await log_task_step(task_id, request.platform, "account_failed", f"账号凭证无效: {validity['message']}", "ERROR", 0)
                return
            elif validity["status"] == "expiring_soon":
                utils.logger.warning(f"[任务 {task_id}] 指定账号凭证即将过期: {validity['expires_at']}")
                await log_task_step(task_id, request.platform, "account_warning", f"账号凭证即将过期: {validity['expires_at']}", "WARN", 30)
            else:
                await log_task_step(task_id, request.platform, "account_success", "账号凭证有效", "INFO", 30)
        
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
            crawler = CrawlerFactory.create_crawler(request.platform)
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
        
        # 生成任务ID
        import uuid
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
            "message": "爬虫任务已启动，正在检查登录状态...",
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