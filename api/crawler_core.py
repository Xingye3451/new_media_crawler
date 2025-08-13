"""
爬虫核心路由模块
包含爬虫任务启动、状态查询等核心功能
"""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from tools import utils
from var import media_crawler_db_var

# 🆕 全局数据库连接池管理
_db_pool = None
_db_async_obj = None

async def get_db_connection():
    """获取数据库连接 - 使用全局连接池"""
    global _db_pool, _db_async_obj
    
    try:
        # 如果连接池已存在且有效，直接返回
        if _db_pool and not _db_pool.closed:
            return _db_async_obj
        
        # 创建新的连接池
        from config.env_config_loader import config_loader
        from async_db import AsyncMysqlDB
        import aiomysql
        
        db_config = config_loader.get_database_config()
        
        _db_pool = await aiomysql.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            db=db_config['database'],
            autocommit=True,
            minsize=1,
            maxsize=20,  # 🆕 增加连接池大小
            echo=False,   # 🆕 关闭SQL日志，减少性能开销
        )
        
        _db_async_obj = AsyncMysqlDB(_db_pool)
        utils.logger.info("数据库连接池创建成功")
        return _db_async_obj
        
    except Exception as e:
        utils.logger.error(f"获取数据库连接失败: {e}")
        return None

async def close_db_connection():
    """关闭数据库连接池"""
    global _db_pool, _db_async_obj
    
    try:
        if _db_pool and not _db_pool.closed:
            _db_pool.close()
            await _db_pool.wait_closed()
            _db_pool = None
            _db_async_obj = None
            utils.logger.info("数据库连接池已关闭")
    except Exception as e:
        utils.logger.error(f"关闭数据库连接池失败: {e}")

from models.content_models import (
    CrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse
)

router = APIRouter()

# 全局任务状态存储
task_status = {}

# 🆕 任务清理配置
TASK_CLEANUP_INTERVAL = 3600  # 1小时清理一次
TASK_MAX_AGE = 86400  # 24小时后清理任务状态

async def cleanup_old_tasks():
    """清理过期的任务状态"""
    try:
        from datetime import datetime, timedelta
        current_time = datetime.now()
        
        tasks_to_remove = []
        for task_id, task_info in task_status.items():
            # 检查任务是否超过24小时
            if 'created_at' in task_info:
                created_time = datetime.fromisoformat(task_info['created_at'])
                if current_time - created_time > timedelta(seconds=TASK_MAX_AGE):
                    tasks_to_remove.append(task_id)
        
        # 移除过期任务
        for task_id in tasks_to_remove:
            del task_status[task_id]
            utils.logger.info(f"清理过期任务状态: {task_id}")
        
        if tasks_to_remove:
            utils.logger.info(f"清理了 {len(tasks_to_remove)} 个过期任务状态")
            
    except Exception as e:
        utils.logger.error(f"清理过期任务失败: {e}")

# 🆕 启动定期清理任务
import asyncio
async def start_task_cleanup():
    """启动定期任务清理"""
    while True:
        try:
            await asyncio.sleep(TASK_CLEANUP_INTERVAL)
            await cleanup_old_tasks()
        except Exception as e:
            utils.logger.error(f"任务清理循环失败: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再重试

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
            "max_notes_count": request.max_notes_count,
            "crawler_type": request.crawler_type,
            "account_id": request.account_id,
            "session_id": request.session_id,
            "login_type": request.login_type,
            "crawler_type": request.crawler_type,
            "get_comments": request.get_comments,
            "save_data_option": request.save_data_option,
            "use_proxy": request.use_proxy,
            "proxy_ip": request.proxy_ip  # 🆕 修复：使用proxy_ip而不是proxy_strategy
        }
        
        # 处理创作者ID列表
        creator_ref_ids = None
        if request.crawler_type == "creator":
            if hasattr(request, 'selected_creators') and request.selected_creators:
                creator_ref_ids = request.selected_creators
            elif hasattr(request, 'creator_ref_ids') and request.creator_ref_ids:
                creator_ref_ids = request.creator_ref_ids
            elif hasattr(request, 'creator_ref_id') and request.creator_ref_id:
                creator_ref_ids = [request.creator_ref_id]
        
        # 使用字典方式构建数据
        task_data = {
            'id': task_id,
            'platform': request.platform,
            'task_type': 'single_platform',
            'crawler_type': request.crawler_type,  # 添加爬取类型
            'creator_ref_ids': json.dumps(creator_ref_ids) if creator_ref_ids else None,  # 添加创作者引用ID列表
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

async def update_task_creator_ref_ids(task_id: str, creator_ref_ids: List[str]):
    """更新任务的creator_ref_ids字段"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[TASK_CREATOR_REF] 无法获取数据库连接")
            return
        
        # 构建更新数据字典
        update_data = {
            'creator_ref_ids': json.dumps(creator_ref_ids),
            'updated_at': datetime.now()
        }
        
        # 使用update_table方法
        await async_db_obj.update_table('crawler_tasks', update_data, 'id', task_id)
        
        utils.logger.info(f"[TASK_CREATOR_REF] 任务creator_ref_ids更新: {task_id}, creator_ref_ids: {creator_ref_ids}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_CREATOR_REF] 更新任务creator_ref_ids失败: {e}")

async def log_task_step(task_id: str, platform: str, step: str, message: str, 
                       log_level: str = "INFO", progress: int = None, account_id: str = None):
    """记录任务步骤日志"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[TASK_LOG] 无法获取数据库连接")
            return
        
        # 构建日志数据字典 - 修复：支持account_id字段
        log_data = {
            'task_id': task_id,
            'platform': platform,
            'account_id': account_id,
            'log_level': log_level,
            'message': message,
            'step': step,
            'progress': progress or 0,
            'add_ts': int(datetime.now().timestamp())
        }
        
        # 使用item_to_table方法
        await async_db_obj.item_to_table('crawler_task_logs', log_data)
        
        utils.logger.info(f"[TASK_LOG] {task_id} - {step}: {message}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_LOG] 记录任务日志失败: {e}")

async def run_crawler_task(task_id: str, request: CrawlerRequest, proxy_info=None):
    """后台运行爬虫任务"""
    # 🆕 设置任务超时时间（30分钟）
    import asyncio
    from concurrent.futures import TimeoutError
    
    try:
        # 🆕 使用asyncio.wait_for添加超时机制
        await asyncio.wait_for(
            _run_crawler_task_internal(task_id, request, proxy_info),
            timeout=1800  # 30分钟超时
        )
    except TimeoutError:
        utils.logger.error(f"[TASK_{task_id}] ❌ 任务执行超时（30分钟）")
        task_status[task_id]["status"] = "timeout"
        task_status[task_id]["error"] = "任务执行超时，请检查网络连接或重试"
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 0.0, "timeout")
        await log_task_step(task_id, request.platform, "task_timeout", "任务执行超时", "ERROR", 0, request.account_id)
    except Exception as e:
        utils.logger.error(f"[TASK_{task_id}] ❌ 任务执行失败: {e}")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 0.0, "failed")
        await log_task_step(task_id, request.platform, "task_failed", f"任务执行失败: {str(e)}", "ERROR", 0, request.account_id)

async def _run_crawler_task_internal(task_id: str, request: CrawlerRequest, proxy_info=None):
    """内部爬虫任务执行函数"""
    # 🆕 导入错误处理模块
    from utils.crawler_error_handler import create_error_handler, RetryConfig, ErrorType
    
    try:
        utils.logger.info("█" * 100)
        utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬虫任务")
        utils.logger.info(f"[TASK_{task_id}] 📝 请求参数详情:")
        utils.logger.info(f"[TASK_{task_id}]   ├─ platform: {request.platform}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ keywords: {request.keywords}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ max_notes_count: {request.max_notes_count}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ account_id: {request.account_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ session_id: {request.session_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ login_type: {request.login_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ crawler_type: {request.crawler_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ get_comments: {request.get_comments}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ save_data_option: {request.save_data_option}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ use_proxy: {request.use_proxy}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ proxy_ip: {request.proxy_ip}")  # 🆕 修复：使用proxy_ip而不是proxy_strategy
        utils.logger.info(f"[TASK_{task_id}]   ├─ video_priority: {getattr(request, 'video_priority', False)}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ video_only: {getattr(request, 'video_only', False)}")
        utils.logger.info(f"[TASK_{task_id}]   └─ start_page: {getattr(request, 'start_page', 1)}")
        
        # 🆕 创建错误处理器 - 减少重试次数避免嵌套重试过多
        retry_config = RetryConfig(
            max_retries=3,  
            base_delay=2.0,
            max_delay=20.0,  # 减少最大延迟
            account_switch_enabled=True,
            max_account_switches=2  # 减少账号切换次数
        )
        error_handler = await create_error_handler(request.platform, task_id, retry_config)
        utils.logger.info(f"[TASK_{task_id}] ✅ 错误处理器初始化完成")
        
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
        await log_task_step(task_id, request.platform, "task_start", "任务开始执行", "INFO", 0, request.account_id)
        
        # 🆕 设置爬虫配置
        utils.logger.info(f"[TASK_{task_id}] ⚙️ 设置爬虫配置...")
        await log_task_step(task_id, request.platform, "config_setup", "设置爬虫配置", "INFO", 35, request.account_id)
        
        # 🆕 设置配置
        import config
        config.PLATFORM = request.platform
        config.KEYWORDS = request.keywords
        config.CRAWLER_MAX_NOTES_COUNT = request.max_notes_count
        config.ENABLE_GET_COMMENTS = request.get_comments
        config.SAVE_DATA_OPTION = request.save_data_option
        config.ENABLE_IP_PROXY = request.use_proxy
        
        # 🆕 创建爬虫实例
        utils.logger.info(f"[TASK_{task_id}] 🔧 创建爬虫实例...")
        await log_task_step(task_id, request.platform, "crawler_init", "创建爬虫实例", "INFO", 40, request.account_id)
        
        try:
            crawler = CrawlerFactory.create_crawler(request.platform, task_id=task_id)
            # 🆕 标记浏览器由外部管理，避免重复关闭
            crawler._externally_managed = True
            
            # 🆕 设置代理信息
            if proxy_info and request.use_proxy:
                crawler.proxy_info = proxy_info
                utils.logger.info(f"[TASK_{task_id}] 设置代理: {proxy_info.ip}:{proxy_info.port}")
                await log_task_step(task_id, request.platform, "proxy_setup", f"设置代理: {proxy_info.ip}:{proxy_info.port}", "INFO", 42, request.account_id)
            
            utils.logger.info(f"[TASK_{task_id}] ✅ 爬虫实例创建成功")
            await log_task_step(task_id, request.platform, "crawler_ready", "爬虫实例就绪", "INFO", 45, request.account_id)
            
        except Exception as e:
            if "coming soon" in str(e).lower():
                utils.logger.warning(f"[TASK_{task_id}] ⚠️ 平台 {request.platform} 功能即将上线: {e}")
                await log_task_step(task_id, request.platform, "platform_coming_soon", str(e), "WARN", 0, request.account_id)
                raise Exception(f"平台 {request.platform} 功能即将上线，敬请期待！")
            else:
                utils.logger.error(f"[TASK_{task_id}] ❌ 创建爬虫实例失败: {e}")
                await log_task_step(task_id, request.platform, "crawler_init_failed", f"创建爬虫实例失败: {str(e)}", "ERROR", 0, request.account_id)
                raise
        
        # 🆕 开始执行爬取
        utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬取...")
        await log_task_step(task_id, request.platform, "crawling_start", "开始执行爬取", "INFO", 50, request.account_id)
        
        try:
            # 🆕 使用错误处理器包装爬取操作
            async def execute_crawling():
                """执行爬取操作"""
                # 执行爬虫任务
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
                        proxy_ip=request.proxy_ip,  # 🆕 修复：使用proxy_ip而不是proxy_strategy
                        start_page=getattr(request, 'start_page', 1)
                    )
                elif request.crawler_type == "creator":
                    # 从数据库获取创作者列表
                    db = await get_db_connection()
                    if not db:
                        raise Exception("数据库连接失败")
                    
                    # 获取指定平台的创作者列表
                    utils.logger.info(f"[TASK_{task_id}] 检查用户选择的创作者...")
                    utils.logger.info(f"[TASK_{task_id}] selected_creators 属性存在: {hasattr(request, 'selected_creators')}")
                    utils.logger.info(f"[TASK_{task_id}] selected_creators 值: {getattr(request, 'selected_creators', None)}")
                    
                    # 🆕 平台代码映射：前端代码 -> 数据库代码
                    platform_mapping = {
                        'dy': 'douyin',
                        'ks': 'kuaishou',
                        'xhs': 'xhs',
                        'bili': 'bilibili',
                        'wb': 'weibo',
                        'tieba': 'tieba',
                        'zhihu': 'zhihu'
                    }
                    
                    # 进行平台代码映射
                    mapped_platform = platform_mapping.get(request.platform, request.platform)
                    utils.logger.info(f"[TASK_{task_id}] 平台代码映射: {request.platform} -> {mapped_platform}")
                    
                    if hasattr(request, 'selected_creators') and request.selected_creators:
                        # 使用用户选择的创作者
                        utils.logger.info(f"[TASK_{task_id}] 使用用户选择的创作者，数量: {len(request.selected_creators)}")
                        creators_query = """
                            SELECT creator_id, platform, name, nickname 
                            FROM unified_creator 
                            WHERE platform = %s AND creator_id IN ({})
                            ORDER BY last_modify_ts DESC
                        """.format(','.join(['%s'] * len(request.selected_creators)))
                        creators = await db.query(creators_query, mapped_platform, *request.selected_creators)
                        utils.logger.info(f"[TASK_{task_id}] 用户选择了 {len(creators)} 个创作者")
                        utils.logger.info(f"[TASK_{task_id}] 创作者列表: {[c.get('name', c.get('nickname', '未知')) for c in creators]}")
                    else:
                        # 获取所有创作者（按最大数量限制）
                        utils.logger.info(f"[TASK_{task_id}] 未选择特定创作者，获取所有创作者")
                        creators_query = """
                            SELECT creator_id, platform, name, nickname 
                            FROM unified_creator 
                            WHERE platform = %s AND is_deleted = 0
                            ORDER BY last_modify_ts DESC
                            LIMIT %s
                        """
                        creators = await db.query(creators_query, mapped_platform, request.max_notes_count)
                        utils.logger.info(f"[TASK_{task_id}] 找到 {len(creators)} 个创作者（自动选择）")
                        utils.logger.info(f"[TASK_{task_id}] 创作者列表: {[c.get('name', c.get('nickname', '未知')) for c in creators]}")
                    
                    if not creators:
                        raise Exception(f"平台 {request.platform} (映射为 {mapped_platform}) 没有找到可用的创作者")
                    
                    # 先初始化爬虫（创建客户端等）
                    await crawler.start()
                    
                    # 🆕 添加调试日志，确保关键字正确传递
                    utils.logger.debug(f"[TASK_{task_id}] 传递给创作者爬取方法的关键字: '{request.keywords}'")
                    utils.logger.debug(f"[TASK_{task_id}] 关键字类型: {type(request.keywords)}")
                    utils.logger.debug(f"[TASK_{task_id}] 关键字是否为空: {not request.keywords or not request.keywords.strip()}")
                    
                    # 调用创作者爬取方法
                    return await crawler.get_creators_and_notes_from_db(
                        creators=creators,
                        max_count=request.max_notes_count,
                        keywords=request.keywords,  # 添加关键词参数
                        account_id=request.account_id,
                        session_id=request.session_id,
                        login_type=request.login_type,
                        get_comments=request.get_comments,
                        save_data_option=request.save_data_option,
                        use_proxy=request.use_proxy,
                        proxy_ip=request.proxy_ip
                    )
                else:
                    raise ValueError(f"不支持的爬虫类型: {request.crawler_type}")
            
            # 🆕 使用错误处理器执行爬取
            from utils.crawler_error_handler import RetryableCrawlerOperation
            retry_op = RetryableCrawlerOperation(error_handler)
            results = await retry_op.execute(execute_crawling)
            
            # 更新任务状态
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["result_count"] = len(results) if results else 0
            task_status[task_id]["results"] = results
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            
            # 🆕 记录错误摘要
            error_summary = error_handler.get_error_summary()
            if error_summary["total_errors"] > 0:
                utils.logger.info(f"[TASK_{task_id}] 📊 错误处理摘要: {error_summary}")
                await log_task_step(task_id, request.platform, "error_summary", f"错误处理摘要: {error_summary}", "INFO", 95, request.account_id)
            
            await update_task_progress(task_id, 100.0, "completed", len(results) if results else 0)
            await log_task_step(task_id, request.platform, "crawling_completed", f"爬取完成，共获取 {len(results) if results else 0} 条数据", "INFO", 100, request.account_id)
            
            utils.logger.info(f"[TASK_{task_id}] ✅ 爬取任务完成，共获取 {len(results) if results else 0} 条数据")
            
        except Exception as e:
            utils.logger.error(f"[TASK_{task_id}] ❌ 爬取过程中发生错误: {e}")
            
            # 🆕 记录错误处理摘要
            error_summary = error_handler.get_error_summary()
            utils.logger.error(f"[TASK_{task_id}] 📊 最终错误处理摘要: {error_summary}")
            
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = f"爬取失败: {str(e)}"
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.0, "failed")
            await log_task_step(task_id, request.platform, "crawling_failed", f"爬取失败: {str(e)}", "ERROR", 0, request.account_id)
            raise
        finally:
            # 🆕 安全关闭爬虫资源
            try:
                if hasattr(crawler, 'close'):
                    await crawler.close()
                    utils.logger.info(f"[TASK_{task_id}] 爬虫资源已关闭")
            except Exception as e:
                utils.logger.warning(f"[TASK_{task_id}] 关闭爬虫资源时出现警告: {e}")
            
            # 🆕 确保浏览器实例被正确关闭
            try:
                if hasattr(crawler, 'browser') and crawler.browser:
                    await crawler.browser.close()
                    utils.logger.info(f"[TASK_{task_id}] 浏览器实例已关闭")
            except Exception as e:
                utils.logger.warning(f"[TASK_{task_id}] 关闭浏览器实例时出现警告: {e}")
            
            # 🆕 清理Playwright上下文
            try:
                if hasattr(crawler, 'context') and crawler.context:
                    await crawler.context.close()
                    utils.logger.info(f"[TASK_{task_id}] Playwright上下文已关闭")
            except Exception as e:
                utils.logger.warning(f"[TASK_{task_id}] 关闭Playwright上下文时出现警告: {e}")
        
    except Exception as e:
        utils.logger.error("█" * 100)
        utils.logger.error(f"[TASK_{task_id}] ❌ 爬虫任务执行失败")
        utils.logger.error(f"[TASK_{task_id}] 🐛 错误详情: {e}")
        utils.logger.error(f"[TASK_{task_id}] 📍 错误类型: {type(e).__name__}")
        utils.logger.error(f"[TASK_{task_id}] 📊 错误堆栈:")
        import traceback
        utils.logger.error(f"[TASK_{task_id}] {traceback.format_exc()}")
        
        # 更新任务状态为失败
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 0.0, "failed")
        await log_task_step(task_id, request.platform, "task_failed", f"任务执行失败: {str(e)}", "ERROR", 0, request.account_id)
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
        
        # 使用登录服务直接调用登录检查逻辑
        from services.login_service import check_platform_login_status
        try:
            login_result = await check_platform_login_status(request.platform)
            utils.logger.info(f"[CRAWLER_START] 登录服务检查结果: {login_result}")
        except Exception as e:
            utils.logger.error(f"[CRAWLER_START] 登录服务检查失败: {e}")
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
        
        # 🆕 获取代理信息
        proxy_info = None
        if request.use_proxy:
            if hasattr(request, 'proxy_ip') and request.proxy_ip:
                # 手动指定代理IP
                try:
                    from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
                    proxy_manager = await get_qingguo_proxy_manager()
                    
                    # 从数据库获取指定IP的代理信息
                    db = await get_db_connection()
                    if db:
                        query = "SELECT * FROM proxy_pool WHERE ip = %s AND status = 'active' AND enabled = 1"
                        proxy_data = await db.get_first(query, request.proxy_ip)
                        
                        if proxy_data:
                            from proxy.qingguo_long_term_proxy import ProxyInfo, ProxyStatus
                            proxy_info = ProxyInfo(
                                id=str(proxy_data['id']),
                                ip=proxy_data['ip'],
                                port=proxy_data['port'],
                                username=proxy_data.get('username', ''),
                                password=proxy_data.get('password', ''),
                                proxy_type=proxy_data['proxy_type'],
                                expire_ts=proxy_data.get('expire_ts', 0),
                                created_at=proxy_data['created_at'],
                                status=ProxyStatus(proxy_data.get('status', 'active')),
                                enabled=proxy_data.get('enabled', True),
                                area=proxy_data.get('area'),
                                description=proxy_data.get('description')
                            )
                            utils.logger.info(f"[CRAWLER_START] 使用指定代理: {proxy_info.ip}:{proxy_info.port}")
                            # 🆕 打印代理详细信息
                            utils.logger.info(f"[CRAWLER_START] 📋 代理详细信息:")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 代理ID: {proxy_info.id}")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 代理类型: {proxy_info.proxy_type}")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 用户名: {proxy_info.username}")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 区域: {proxy_info.area}")
                            utils.logger.info(f"[CRAWLER_START]   ├─ 描述: {proxy_info.description}")
                            utils.logger.info(f"[CRAWLER_START]   └─ 过期时间: {proxy_info.expire_ts}")
                        else:
                            utils.logger.warning(f"[CRAWLER_START] 指定的代理IP {request.proxy_ip} 不可用")
                except Exception as e:
                    utils.logger.warning(f"[CRAWLER_START] 获取指定代理失败: {e}")
            elif request.account_id:
                # 使用登录时的代理
                try:
                    from api.login_proxy_helper import get_proxy_from_login_token
                    proxy_info = await get_proxy_from_login_token(request.account_id, request.platform)
                    if proxy_info:
                        utils.logger.info(f"[CRAWLER_START] 获取到登录代理: {proxy_info.ip}:{proxy_info.port}")
                        # 🆕 打印代理详细信息
                        utils.logger.info(f"[CRAWLER_START] 📋 登录代理详细信息:")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理ID: {proxy_info.id}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理类型: {proxy_info.proxy_type}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 用户名: {proxy_info.username}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 区域: {proxy_info.area}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 描述: {proxy_info.description}")
                        utils.logger.info(f"[CRAWLER_START]   └─ 过期时间: {proxy_info.expire_ts}")
                    else:
                        utils.logger.info(f"[CRAWLER_START] 未找到登录代理，将使用新代理")
                except Exception as e:
                    utils.logger.warning(f"[CRAWLER_START] 获取登录代理失败: {e}")
            
            # 如果没有获取到代理，尝试自动获取
            if not proxy_info:
                try:
                    from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
                    proxy_manager = await get_qingguo_proxy_manager()
                    proxy_info = await proxy_manager.get_available_proxy()
                    if proxy_info:
                        utils.logger.info(f"[CRAWLER_START] 自动获取代理: {proxy_info.ip}:{proxy_info.port}")
                        # 🆕 打印代理详细信息
                        utils.logger.info(f"[CRAWLER_START] 📋 自动代理详细信息:")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理ID: {proxy_info.id}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 代理类型: {proxy_info.proxy_type}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 用户名: {proxy_info.username}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 区域: {proxy_info.area}")
                        utils.logger.info(f"[CRAWLER_START]   ├─ 描述: {proxy_info.description}")
                        utils.logger.info(f"[CRAWLER_START]   └─ 过期时间: {proxy_info.expire_ts}")
                except Exception as e:
                    utils.logger.warning(f"[CRAWLER_START] 自动获取代理失败: {e}")
        else:
            utils.logger.info(f"[CRAWLER_START] 未启用代理功能")
        
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
        background_tasks.add_task(run_crawler_task, task_id, request, proxy_info)
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

@router.get("/crawler/health")
async def get_crawler_health():
    """获取爬虫系统健康状态"""
    try:
        # 检查数据库连接
        db_status = "unknown"
        try:
            async_db_obj = await get_db_connection()
            if async_db_obj:
                db_status = "healthy"
            else:
                db_status = "unhealthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # 统计任务状态
        total_tasks = len(task_status)
        running_tasks = len([t for t in task_status.values() if t.get('status') == 'running'])
        completed_tasks = len([t for t in task_status.values() if t.get('status') == 'completed'])
        failed_tasks = len([t for t in task_status.values() if t.get('status') == 'failed'])
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "tasks": {
                "total": total_tasks,
                "running": running_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks
            },
            "memory_usage": {
                "task_status_size": len(str(task_status)),
                "estimated_memory_mb": len(str(task_status)) / (1024 * 1024)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 