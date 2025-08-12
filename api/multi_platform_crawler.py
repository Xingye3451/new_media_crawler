"""
多平台爬取核心模块
支持同时爬取多个平台，统一数据格式存储
"""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from tools import utils
from var import media_crawler_db_var

# 导入数据模型
from models.content_models import (
    MultiPlatformCrawlerRequest, MultiPlatformTaskStatusResponse,
    UnifiedResultResponse
)

router = APIRouter()

# 全局多平台任务状态存储
multi_platform_task_status = {}

# 🆕 多平台任务清理配置
MULTI_TASK_CLEANUP_INTERVAL = 3600  # 1小时清理一次
MULTI_TASK_MAX_AGE = 86400  # 24小时后清理任务状态

async def cleanup_old_multi_platform_tasks():
    """清理过期的多平台任务状态"""
    try:
        from datetime import datetime, timedelta
        current_time = datetime.now()
        
        tasks_to_remove = []
        for task_id, task_info in multi_platform_task_status.items():
            # 检查任务是否超过24小时
            if 'created_at' in task_info:
                created_time = datetime.fromisoformat(task_info['created_at'])
                if current_time - created_time > timedelta(seconds=MULTI_TASK_MAX_AGE):
                    tasks_to_remove.append(task_id)
        
        # 移除过期任务
        for task_id in tasks_to_remove:
            del multi_platform_task_status[task_id]
            utils.logger.info(f"清理过期多平台任务状态: {task_id}")
        
        if tasks_to_remove:
            utils.logger.info(f"清理了 {len(tasks_to_remove)} 个过期多平台任务状态")
            
    except Exception as e:
        utils.logger.error(f"清理过期多平台任务失败: {e}")

# 🆕 启动定期清理任务
import asyncio
async def start_multi_platform_task_cleanup():
    """启动定期多平台任务清理"""
    while True:
        try:
            await asyncio.sleep(MULTI_TASK_CLEANUP_INTERVAL)
            await cleanup_old_multi_platform_tasks()
        except Exception as e:
            utils.logger.error(f"多平台任务清理循环失败: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再重试

class AccountStrategy(str, Enum):
    """账号策略枚举"""
    RANDOM = "random"           # 随机选择
    ROUND_ROBIN = "round_robin" # 轮询选择
    PRIORITY = "priority"        # 优先级选择
    SMART = "smart"             # 智能选择（根据登录状态、成功率等）
    SINGLE = "single"           # 单账号使用

class MultiPlatformCrawlerFactory:
    """多平台爬虫工厂类"""
    
    # 支持的平台
    SUPPORTED_PLATFORMS = ["xhs", "dy", "ks", "bili"]
    
    @staticmethod
    def _get_crawler_class(platform: str):
        """延迟导入爬虫类"""
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
        """创建爬虫实例"""
        crawler_class = MultiPlatformCrawlerFactory._get_crawler_class(platform)
        return crawler_class(task_id=task_id)

# 🆕 复用单平台爬虫的数据库连接管理
from api.crawler_core import get_db_connection, close_db_connection

async def create_multi_platform_task_record(task_id: str, request: MultiPlatformCrawlerRequest) -> None:
    """创建多平台任务记录到数据库"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[MULTI_TASK_RECORD] 无法获取数据库连接")
            return
        
        # 构建任务参数JSON
        task_params = {
            "platforms": request.platforms,
            "keywords": request.keywords,
            "max_count_per_platform": request.max_count_per_platform,
            "enable_comments": request.enable_comments,
            "enable_images": request.enable_images,
            "save_format": request.save_format,
            "use_proxy": request.use_proxy,
            "proxy_ip": request.proxy_ip,  # 🆕 修复：使用proxy_ip而不是proxy_strategy
            "account_strategy": request.account_strategy if hasattr(request, 'account_strategy') else "smart",
            "execution_mode": request.execution_mode if hasattr(request, 'execution_mode') else "parallel"
        }
        
        # 使用字典方式构建数据
        task_data = {
            'id': task_id,
            'platform': ','.join(request.platforms),  # 多平台用逗号分隔
            'task_type': 'multi_platform',
            'crawler_type': 'search',  # 多平台默认为搜索模式
            'creator_ref_ids': None,
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
        
        await async_db_obj.item_to_table('crawler_tasks', task_data)
        utils.logger.info(f"[MULTI_TASK_RECORD] 多平台任务记录创建成功: {task_id}")
        
    except Exception as e:
        utils.logger.error(f"[MULTI_TASK_RECORD] 创建多平台任务记录失败: {e}")
        raise

async def update_multi_platform_task_progress(task_id: str, progress: float, status: str = None, 
                                           platform_results: Dict[str, int] = None):
    """更新多平台任务进度"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[MULTI_TASK_PROGRESS] 无法获取数据库连接")
            return
        
        # 构建更新数据字典
        update_data = {
            'progress': progress,
            'updated_at': datetime.now()
        }
        
        if status:
            update_data['status'] = status
        
        if platform_results:
            total_results = sum(platform_results.values())
            update_data['result_count'] = total_results
        
        await async_db_obj.update_table('crawler_tasks', update_data, 'id', task_id)
        
        utils.logger.info(f"[MULTI_TASK_PROGRESS] 多平台任务进度更新: {task_id}, 进度: {progress}, 状态: {status}")
        
    except Exception as e:
        utils.logger.error(f"[MULTI_TASK_PROGRESS] 更新多平台任务进度失败: {e}")

async def log_multi_platform_task_step(task_id: str, platform: str, step: str, message: str, 
                                     log_level: str = "INFO", progress: int = None):
    """记录多平台任务步骤日志"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            utils.logger.error("[MULTI_TASK_LOG] 无法获取数据库连接")
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
        
        await async_db_obj.item_to_table('crawler_task_logs', log_data)
        utils.logger.info(f"[MULTI_TASK_LOG] {task_id} - {platform} - {step}: {message}")
        
    except Exception as e:
        utils.logger.error(f"[MULTI_TASK_LOG] 记录多平台任务日志失败: {e}")

async def get_platform_accounts(platform: str, account_strategy: str = "smart") -> List[Dict]:
    """根据策略获取平台账号列表"""
    try:
        async_db_obj = await get_db_connection()
        if not async_db_obj:
            return []
        
        # 🆕 修复：使用正确的表结构，参考单平台爬取的账号管理逻辑
        # 获取该平台的所有可用账号（从social_accounts表）
        query = """
            SELECT sa.id, sa.account_name, sa.username, sa.platform, sa.login_method,
                   lt.is_valid, lt.expires_at, lt.last_used_at, lt.created_at as token_created_at
            FROM social_accounts sa
            LEFT JOIN login_tokens lt ON sa.id = lt.account_id AND sa.platform = lt.platform
            WHERE sa.platform = %s
            ORDER BY 
                CASE 
                    WHEN lt.is_valid = 1 AND lt.expires_at > NOW() THEN 1
                    ELSE 2
                END,
                lt.created_at DESC,
                sa.created_at DESC
        """
        
        accounts = await async_db_obj.query(query, platform)
        
        if not accounts:
            utils.logger.warning(f"平台 {platform} 没有找到任何账号")
            return []
        
        # 过滤出有效的账号（有有效token的账号）
        valid_accounts = []
        for account in accounts:
            if account.get('is_valid') == 1 and account.get('expires_at'):
                # 检查token是否过期
                from datetime import datetime
                expires_at = account['expires_at']
                if isinstance(expires_at, str):
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                if expires_at > datetime.now():
                    valid_accounts.append(account)
        
        if not valid_accounts:
            utils.logger.warning(f"平台 {platform} 没有找到有效的登录账号")
            return []
        
        utils.logger.info(f"平台 {platform} 找到 {len(valid_accounts)} 个有效账号")
        
        # 根据策略选择账号
        if account_strategy == "random":
            import random
            selected = random.sample(valid_accounts, min(len(valid_accounts), 3))
            utils.logger.info(f"随机选择 {len(selected)} 个账号")
            return selected
        elif account_strategy == "round_robin":
            # 轮询选择，这里简化处理，选择前几个
            selected = valid_accounts[:min(len(valid_accounts), 2)]
            utils.logger.info(f"轮询选择 {len(selected)} 个账号")
            return selected
        elif account_strategy == "priority":
            # 优先级选择：有效token > 最近使用
            selected = valid_accounts[:min(len(valid_accounts), 2)]
            utils.logger.info(f"优先级选择 {len(selected)} 个账号")
            return selected
        elif account_strategy == "smart":
            # 智能选择：综合考虑token有效性、使用频率
            # 按token创建时间排序，选择最新的
            smart_accounts = sorted(valid_accounts, 
                                 key=lambda x: x.get('token_created_at', datetime.min), 
                                 reverse=True)
            selected = smart_accounts[:min(len(smart_accounts), 2)]
            utils.logger.info(f"智能选择 {len(selected)} 个账号")
            return selected
        elif account_strategy == "single":
            # 单账号使用
            selected = valid_accounts[:1]
            utils.logger.info(f"单账号选择 {len(selected)} 个账号")
            return selected
        else:
            # 默认选择第一个
            selected = valid_accounts[:1]
            utils.logger.info(f"默认选择 {len(selected)} 个账号")
            return selected
            
    except Exception as e:
        utils.logger.error(f"获取平台 {platform} 账号失败: {e}")
        return []

async def run_single_platform_crawler(task_id: str, platform: str, request: MultiPlatformCrawlerRequest, 
                                    account_strategy: str = "smart", execution_mode: str = "parallel", proxy_info=None):
    """运行单个平台的爬虫任务"""
    # 🆕 导入错误处理模块
    from utils.crawler_error_handler import create_error_handler, RetryConfig, ErrorType, RetryableCrawlerOperation
    
    try:
        utils.logger.info(f"[MULTI_TASK_{task_id}] 🚀 开始执行平台 {platform} 爬取任务")
        
        # 🆕 创建错误处理器
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            account_switch_enabled=True,
            max_account_switches=3
        )
        error_handler = await create_error_handler(platform, task_id, retry_config)
        utils.logger.info(f"[MULTI_TASK_{task_id}] ✅ 平台 {platform} 错误处理器初始化完成")
        
        # 获取平台账号
        accounts = await get_platform_accounts(platform, account_strategy)
        if not accounts:
            raise Exception(f"平台 {platform} 没有可用账号")
        
        # 选择第一个账号
        selected_account = accounts[0]
        account_id = selected_account['id']
        
        await log_multi_platform_task_step(task_id, platform, "account_selected", 
                                         f"选择账号: {selected_account.get('account_name', '未知')} (ID: {account_id})")
        
        # 创建爬虫实例
        crawler = MultiPlatformCrawlerFactory.create_crawler(platform, task_id=task_id)
        # 🆕 标记浏览器由外部管理，避免重复关闭
        crawler._externally_managed = True
        
        # 🆕 设置代理信息
        if proxy_info and request.use_proxy:
            crawler.proxy_info = proxy_info
            utils.logger.info(f"[MULTI_TASK_{task_id}] 设置代理: {proxy_info.ip}:{proxy_info.port}")
            # 🆕 打印代理使用信息
            utils.logger.info(f"[MULTI_TASK_{task_id}] 🌐 平台 {platform} 代理使用信息:")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理类型: {proxy_info.proxy_type}")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 认证信息: {proxy_info.username}:{proxy_info.password}")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 区域: {proxy_info.area}")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 描述: {proxy_info.description}")
            utils.logger.info(f"[MULTI_TASK_{task_id}]   └─ 使用方式: curl -x {proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port} https://httpbin.org/ip")
            await log_multi_platform_task_step(task_id, platform, "proxy_setup", f"设置代理: {proxy_info.ip}:{proxy_info.port}", "INFO")
        
        # 🆕 清空之前收集的数据，确保新任务的数据正确
        try:
            if platform == "xhs":
                from store.xhs import _clear_collected_data
                _clear_collected_data()
            elif platform == "dy":
                if hasattr(crawler, 'douyin_store') and hasattr(crawler.douyin_store, 'clear_collected_data'):
                    crawler.douyin_store.clear_collected_data()
            elif platform == "ks":
                from store.kuaishou import _clear_collected_data
                _clear_collected_data()
            elif platform == "bili":
                from store.bilibili import _clear_collected_data
                _clear_collected_data()
            elif platform == "wb":
                from store.weibo import _clear_collected_data
                _clear_collected_data()
            elif platform == "zhihu":
                from store.zhihu import _clear_collected_data
                _clear_collected_data()
            elif platform == "tieba":
                from store.tieba import _clear_collected_data
                _clear_collected_data()
        except Exception as e:
            utils.logger.warning(f"[MULTI_TASK_{task_id}] 清空数据失败: {e}")
        
        # 设置爬虫配置
        import config
        config.PLATFORM = platform
        config.ENABLE_GET_COMMENTS = request.enable_comments
        config.SAVE_DATA_OPTION = "db"  # 多平台固定使用数据库存储
        
        # 开始爬取
        await log_multi_platform_task_step(task_id, platform, "crawling_start", "开始执行爬取")
        
        # 🆕 使用错误处理器包装爬取操作
        async def execute_platform_crawling():
            """执行平台爬取操作"""
            return await crawler.search_by_keywords(
                keywords=request.keywords,
                max_count=request.max_count_per_platform,
                account_id=account_id,
                session_id=None,
                login_type="qrcode",
                get_comments=request.enable_comments,
                save_data_option="db",
                use_proxy=request.use_proxy,
                proxy_ip=request.proxy_ip,  # 🆕 修复：使用proxy_ip而不是proxy_strategy
                start_page=1  # 多平台爬取默认从第1页开始
            )
        
        # 🆕 使用错误处理器执行爬取
        retry_op = RetryableCrawlerOperation(error_handler)
        results = await retry_op.execute(execute_platform_crawling)
        
        result_count = len(results) if results else 0
        await log_multi_platform_task_step(task_id, platform, "crawling_completed", 
                                         f"爬取完成，共获取 {result_count} 条数据")
        
        # 🆕 记录错误摘要
        error_summary = error_handler.get_error_summary()
        if error_summary["total_errors"] > 0:
            utils.logger.info(f"[MULTI_TASK_{task_id}] 📊 平台 {platform} 错误处理摘要: {error_summary}")
            await log_multi_platform_task_step(task_id, platform, "error_summary", f"错误处理摘要: {error_summary}", "INFO")
        
        # 🆕 安全关闭爬虫资源
        try:
            if hasattr(crawler, 'close'):
                await crawler.close()
                utils.logger.info(f"[MULTI_TASK_{task_id}] 爬虫资源已关闭")
        except Exception as e:
            utils.logger.warning(f"[MULTI_TASK_{task_id}] 关闭爬虫资源时出现警告: {e}")
        
        # 🆕 确保浏览器实例被正确关闭
        try:
            if hasattr(crawler, 'browser') and crawler.browser:
                await crawler.browser.close()
                utils.logger.info(f"[MULTI_TASK_{task_id}] 浏览器实例已关闭")
        except Exception as e:
            utils.logger.warning(f"[MULTI_TASK_{task_id}] 关闭浏览器实例时出现警告: {e}")
        
        # 🆕 清理Playwright上下文
        try:
            if hasattr(crawler, 'context') and crawler.context:
                await crawler.context.close()
                utils.logger.info(f"[MULTI_TASK_{task_id}] Playwright上下文已关闭")
        except Exception as e:
            utils.logger.warning(f"[MULTI_TASK_{task_id}] 关闭Playwright上下文时出现警告: {e}")
        
        return result_count
        
    except Exception as e:
        utils.logger.error(f"[MULTI_TASK_{task_id}] ❌ 平台 {platform} 爬取失败: {e}")
        
        # 🆕 记录错误处理摘要
        try:
            error_summary = error_handler.get_error_summary()
            utils.logger.error(f"[MULTI_TASK_{task_id}] 📊 平台 {platform} 最终错误处理摘要: {error_summary}")
        except:
            pass
        
        await log_multi_platform_task_step(task_id, platform, "crawling_failed", f"爬取失败: {str(e)}", "ERROR")
        raise

async def run_multi_platform_crawler_task(task_id: str, request: MultiPlatformCrawlerRequest):
    """后台运行多平台爬虫任务"""
    # 🆕 设置任务超时时间（45分钟，因为多平台需要更多时间）
    import asyncio
    from concurrent.futures import TimeoutError
    
    try:
        # 🆕 使用asyncio.wait_for添加超时机制
        await asyncio.wait_for(
            _run_multi_platform_crawler_task_internal(task_id, request),
            timeout=2700  # 45分钟超时
        )
    except TimeoutError:
        utils.logger.error(f"[MULTI_TASK_{task_id}] ❌ 多平台任务执行超时（45分钟）")
        multi_platform_task_status[task_id]["status"] = "timeout"
        multi_platform_task_status[task_id]["error"] = "多平台任务执行超时，请检查网络连接或重试"
        multi_platform_task_status[task_id]["completed_at"] = datetime.now().isoformat()
        await update_multi_platform_task_progress(task_id, 0.0, "timeout")
        await log_multi_platform_task_step(task_id, "multi", "task_timeout", "多平台任务执行超时", "ERROR", 0)
    except Exception as e:
        utils.logger.error(f"[MULTI_TASK_{task_id}] ❌ 多平台任务执行失败: {e}")
        multi_platform_task_status[task_id]["status"] = "failed"
        multi_platform_task_status[task_id]["error"] = str(e)
        multi_platform_task_status[task_id]["completed_at"] = datetime.now().isoformat()
        await update_multi_platform_task_progress(task_id, 0.0, "failed")
        await log_multi_platform_task_step(task_id, "multi", "task_failed", f"多平台任务执行失败: {str(e)}", "ERROR", 0)

async def _run_multi_platform_crawler_task_internal(task_id: str, request: MultiPlatformCrawlerRequest):
    """内部多平台爬虫任务执行函数"""
    try:
        utils.logger.info("█" * 100)
        utils.logger.info(f"[MULTI_TASK_{task_id}] 🚀 开始执行多平台爬虫任务")
        utils.logger.info(f"[MULTI_TASK_{task_id}] 📝 请求参数详情:")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ platforms: {request.platforms}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ keywords: {request.keywords}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ max_count_per_platform: {request.max_count_per_platform}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ enable_comments: {request.enable_comments}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ enable_images: {request.enable_images}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ save_format: {request.save_format}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ use_proxy: {request.use_proxy}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ proxy_ip: {request.proxy_ip}")  # 🆕 修复：使用proxy_ip而不是proxy_strategy
        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ account_strategy: {getattr(request, 'account_strategy', 'smart')}")
        utils.logger.info(f"[MULTI_TASK_{task_id}]   └─ execution_mode: {getattr(request, 'execution_mode', 'parallel')}")
        
        # 初始化数据库连接
        utils.logger.info(f"[MULTI_TASK_{task_id}] 📊 初始化数据库连接...")
        try:
            from db import init_mediacrawler_db
            await init_mediacrawler_db()
            utils.logger.info(f"[MULTI_TASK_{task_id}] ✅ 数据库连接初始化完成")
        except Exception as e:
            utils.logger.error(f"[MULTI_TASK_{task_id}] ❌ 数据库连接初始化失败: {e}")
        
        # 创建任务记录
        utils.logger.info(f"[MULTI_TASK_{task_id}] 📝 创建多平台任务记录...")
        await create_multi_platform_task_record(task_id, request)
        utils.logger.info(f"[MULTI_TASK_{task_id}] ✅ 多平台任务记录创建成功")
        
        # 更新任务状态
        multi_platform_task_status[task_id]["status"] = "running"
        multi_platform_task_status[task_id]["started_at"] = datetime.now().isoformat()
        await update_multi_platform_task_progress(task_id, 0.0, "running")
        await log_multi_platform_task_step(task_id, "multi", "task_start", "多平台任务开始执行")
        
        # 获取执行模式和账号策略
        execution_mode = getattr(request, 'execution_mode', 'parallel')
        account_strategy = getattr(request, 'account_strategy', 'smart')
        
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
                            utils.logger.info(f"[MULTI_TASK_{task_id}] 使用指定代理: {proxy_info.ip}:{proxy_info.port}")
                            # 🆕 打印代理详细信息
                            utils.logger.info(f"[MULTI_TASK_{task_id}] 📋 代理详细信息:")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理ID: {proxy_info.id}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理类型: {proxy_info.proxy_type}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 用户名: {proxy_info.username}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 区域: {proxy_info.area}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 描述: {proxy_info.description}")
                            utils.logger.info(f"[MULTI_TASK_{task_id}]   └─ 过期时间: {proxy_info.expire_ts}")
                        else:
                            utils.logger.warning(f"[MULTI_TASK_{task_id}] 指定的代理IP {request.proxy_ip} 不可用")
                except Exception as e:
                    utils.logger.warning(f"[MULTI_TASK_{task_id}] 获取指定代理失败: {e}")
            else:
                # 自动获取代理
                try:
                    from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
                    proxy_manager = await get_qingguo_proxy_manager()
                    proxy_info = await proxy_manager.get_available_proxy()
                    if proxy_info:
                        utils.logger.info(f"[MULTI_TASK_{task_id}] 自动获取代理: {proxy_info.ip}:{proxy_info.port}")
                        # 🆕 打印代理详细信息
                        utils.logger.info(f"[MULTI_TASK_{task_id}] 📋 自动代理详细信息:")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理ID: {proxy_info.id}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 代理类型: {proxy_info.proxy_type}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 用户名: {proxy_info.username}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 区域: {proxy_info.area}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ 描述: {proxy_info.description}")
                        utils.logger.info(f"[MULTI_TASK_{task_id}]   └─ 过期时间: {proxy_info.expire_ts}")
                except Exception as e:
                    utils.logger.warning(f"[MULTI_TASK_{task_id}] 自动获取代理失败: {e}")
        else:
            utils.logger.info(f"[MULTI_TASK_{task_id}] 未启用代理功能")
        
        # 执行爬取任务
        platform_results = {}
        platform_errors = {}
        
        if execution_mode == "parallel":
            # 并行执行
            utils.logger.info(f"[MULTI_TASK_{task_id}] 🔄 并行执行模式")
            await log_multi_platform_task_step(task_id, "multi", "execution_mode", "并行执行模式")
            
            # 创建所有平台的爬取任务
            tasks = []
            for platform in request.platforms:
                task = run_single_platform_crawler(task_id, platform, request, account_strategy, execution_mode, proxy_info)
                tasks.append((platform, task))
            
            # 并行执行所有任务
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # 处理结果
            for i, (platform, _) in enumerate(tasks):
                if isinstance(results[i], Exception):
                    platform_errors[platform] = str(results[i])
                    platform_results[platform] = 0
                else:
                    platform_results[platform] = results[i]
                    
        else:
            # 顺序执行
            utils.logger.info(f"[MULTI_TASK_{task_id}] 🔄 顺序执行模式")
            await log_multi_platform_task_step(task_id, "multi", "execution_mode", "顺序执行模式")
            
            for i, platform in enumerate(request.platforms):
                try:
                    progress = (i / len(request.platforms)) * 100
                    await update_multi_platform_task_progress(task_id, progress)
                    await log_multi_platform_task_step(task_id, "multi", "platform_start", f"开始执行平台 {platform}")
                    
                    result_count = await run_single_platform_crawler(task_id, platform, request, account_strategy, execution_mode, proxy_info)
                    platform_results[platform] = result_count
                    
                    await log_multi_platform_task_step(task_id, "multi", "platform_completed", f"平台 {platform} 执行完成，获取 {result_count} 条数据")
                    
                except Exception as e:
                    platform_errors[platform] = str(e)
                    platform_results[platform] = 0
                    await log_multi_platform_task_step(task_id, "multi", "platform_failed", f"平台 {platform} 执行失败: {str(e)}", "ERROR")
        
        # 更新最终状态
        total_results = sum(platform_results.values())
        success_platforms = len([p for p in request.platforms if p not in platform_errors])
        
        if platform_errors:
            # 🆕 修复：缩短状态值以符合数据库字段长度限制
            status = "completed_with_errors" if len("completed_with_errors") <= 20 else "completed_errors"
            message = f"部分平台执行失败，成功: {success_platforms}/{len(request.platforms)} 个平台"
        else:
            status = "completed"
            message = f"所有平台执行成功，共获取 {total_results} 条数据"
        
        multi_platform_task_status[task_id].update({
            "status": status,
            "results": platform_results,
            "errors": platform_errors,
            "completed_at": datetime.now().isoformat()
        })
        
        await update_multi_platform_task_progress(task_id, 100.0, status, platform_results)
        await log_multi_platform_task_step(task_id, "multi", "task_completed", message)
        
        utils.logger.info(f"[MULTI_TASK_{task_id}] ✅ 多平台爬取任务完成")
        utils.logger.info(f"[MULTI_TASK_{task_id}] 📊 结果统计:")
        for platform, count in platform_results.items():
            utils.logger.info(f"[MULTI_TASK_{task_id}]   ├─ {platform}: {count} 条")
        if platform_errors:
            utils.logger.info(f"[MULTI_TASK_{task_id}]   └─ 错误: {platform_errors}")
        utils.logger.info("█" * 100)
        
    except Exception as e:
        utils.logger.error("█" * 100)
        utils.logger.error(f"[MULTI_TASK_{task_id}] ❌ 多平台爬虫任务执行失败")
        utils.logger.error(f"[MULTI_TASK_{task_id}] 🐛 错误详情: {e}")
        utils.logger.error(f"[MULTI_TASK_{task_id}] 📍 错误类型: {type(e).__name__}")
        import traceback
        utils.logger.error(f"[MULTI_TASK_{task_id}] 📊 错误堆栈:")
        utils.logger.error(f"[MULTI_TASK_{task_id}] {traceback.format_exc()}")
        
        # 更新任务状态为失败
        multi_platform_task_status[task_id]["status"] = "failed"
        multi_platform_task_status[task_id]["error"] = str(e)
        multi_platform_task_status[task_id]["completed_at"] = datetime.now().isoformat()
        await update_multi_platform_task_progress(task_id, 0.0, "failed")
        await log_multi_platform_task_step(task_id, "multi", "task_failed", f"多平台任务执行失败: {str(e)}", "ERROR")
        utils.logger.error("█" * 100)

@router.post("/multi-platform/start", response_model=MultiPlatformTaskStatusResponse)
async def start_multi_platform_crawler(request: MultiPlatformCrawlerRequest, background_tasks: BackgroundTasks):
    """启动多平台爬虫任务"""
    try:
        utils.logger.info("=" * 100)
        utils.logger.info("[MULTI_CRAWLER_START] 收到多平台爬虫任务启动请求")
        utils.logger.info(f"[MULTI_CRAWLER_START] 平台: {request.platforms}")
        utils.logger.info(f"[MULTI_CRAWLER_START] 关键词: {request.keywords}")
        utils.logger.info(f"[MULTI_CRAWLER_START] 每平台最大数量: {request.max_count_per_platform}")
        
        # 参数验证
        if not request.platforms:
            raise HTTPException(status_code=400, detail="请至少选择一个平台")
        
        if not request.keywords.strip():
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        # 检查平台支持情况
        unsupported_platforms = [p for p in request.platforms if p not in MultiPlatformCrawlerFactory.SUPPORTED_PLATFORMS]
        if unsupported_platforms:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {', '.join(unsupported_platforms)}")
        
        # 检查各平台登录状态
        utils.logger.info("[MULTI_CRAWLER_START] 检查各平台登录状态...")
        login_issues = []
        
        for platform in request.platforms:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8100/api/v1/login/check",
                        json={"platform": platform},
                        timeout=10.0
                    )
                    login_result = response.json()
                    
                    if login_result["code"] != 200:
                        login_issues.append(f"{platform}: {login_result.get('message', 'unknown')}")
                        
            except Exception as e:
                login_issues.append(f"{platform}: 检查失败 - {str(e)}")
        
        if login_issues:
            utils.logger.warning(f"[MULTI_CRAWLER_START] 部分平台登录状态异常: {login_issues}")
            # 继续执行，但记录警告
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        utils.logger.info(f"[MULTI_CRAWLER_START] 生成任务ID: {task_id}")
        
        # 初始化任务状态
        multi_platform_task_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "platforms": request.platforms,
            "keywords": request.keywords,
            "progress": {
                "total": len(request.platforms),
                "completed": 0,
                "failed": 0,
                "pending": len(request.platforms)
            },
            "results": {},
            "errors": {},
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None
        }
        utils.logger.info("[MULTI_CRAWLER_START] 多平台任务状态已初始化")
        
        # 添加后台任务
        background_tasks.add_task(run_multi_platform_crawler_task, task_id, request)
        utils.logger.info("[MULTI_CRAWLER_START] 后台任务已添加")
        
        # 构建响应数据
        response_data = {
            "task_id": task_id,
            "status": "pending",
            "platforms": request.platforms,
            "keywords": request.keywords,
            "progress": {
                "total": len(request.platforms),
                "completed": 0,
                "failed": 0,
                "pending": len(request.platforms)
            },
            "results": {},
            "errors": {},
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None
        }
        utils.logger.info(f"[MULTI_CRAWLER_START] 响应数据: {response_data}")
        utils.logger.info("=" * 100)
        
        return MultiPlatformTaskStatusResponse(**response_data)
        
    except Exception as e:
        utils.logger.error(f"[MULTI_CRAWLER_START] 启动多平台爬虫任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动多平台爬虫任务失败: {str(e)}")

@router.get("/multi-platform/status/{task_id}", response_model=MultiPlatformTaskStatusResponse)
async def get_multi_platform_task_status(task_id: str):
    """获取多平台任务状态"""
    if task_id not in multi_platform_task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return MultiPlatformTaskStatusResponse(**multi_platform_task_status[task_id])

@router.get("/multi-platform/tasks")
async def list_multi_platform_tasks():
    """获取所有多平台任务列表"""
    return {
        "tasks": list(multi_platform_task_status.values()),
        "total": len(multi_platform_task_status)
    }

@router.delete("/multi-platform/tasks/{task_id}")
async def delete_multi_platform_task(task_id: str):
    """删除多平台任务"""
    if task_id not in multi_platform_task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del multi_platform_task_status[task_id]
    return {"message": "多平台任务已删除"}

@router.get("/multi-platform/health")
async def get_multi_platform_health():
    """获取多平台爬虫系统健康状态"""
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
        total_tasks = len(multi_platform_task_status)
        running_tasks = len([t for t in multi_platform_task_status.values() if t.get('status') == 'running'])
        completed_tasks = len([t for t in multi_platform_task_status.values() if t.get('status') == 'completed'])
        failed_tasks = len([t for t in multi_platform_task_status.values() if t.get('status') == 'failed'])
        
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
                "task_status_size": len(str(multi_platform_task_status)),
                "estimated_memory_mb": len(str(multi_platform_task_status)) / (1024 * 1024)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/multi-platform/info")
async def get_multi_platform_crawler_info():
    """获取多平台功能信息"""
    return {
        "supported_platforms": MultiPlatformCrawlerFactory.SUPPORTED_PLATFORMS,
        "account_strategies": [strategy.value for strategy in AccountStrategy],
        "execution_modes": ["parallel", "sequential"],
        "save_formats": ["db"],  # 多平台固定使用数据库存储
        "features": {
            "concurrent_crawling": True,
            "unified_data_format": True,
            "account_management": True,
            "progress_tracking": True,
            "error_handling": True
        }
    } 