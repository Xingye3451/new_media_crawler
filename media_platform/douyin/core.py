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
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple
import time

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import DOUYINClient
from .exception import DataFetchError
from .field import PublishTimeType
from .login import DouYinLogin
from utils.db_utils import get_cookies_from_database


class DouYinCrawler(AbstractCrawler):
    context_page: Page
    dy_client: DOUYINClient
    browser_context: BrowserContext

    def __init__(self, task_id: str = None) -> None:
        super().__init__()
        self.context_page: Page = None
        self.dy_client: DOUYINClient = None
        self.browser_context: BrowserContext = None
        self.index_url = "https://www.douyin.com"
        # 使用Redis存储实现
        from store.douyin.douyin_store_impl import DouyinRedisStoreImplement
        self.douyin_store = DouyinRedisStoreImplement()
        self.task_id = task_id
        
    def set_storage_callback(self, callback):
        """设置存储回调函数"""
        super().set_storage_callback(callback)
        # 同时设置给Redis存储实现
        if hasattr(self, 'douyin_store') and hasattr(self.douyin_store, 'set_redis_callback'):
            self.douyin_store.set_redis_callback(callback)

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                None,
                user_agent=None,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                # 从数据库读取cookies，支持账号选择
                account_id = getattr(config, 'ACCOUNT_ID', None) or os.environ.get('CRAWLER_ACCOUNT_ID')
                cookie_str = await get_cookies_from_database("dy", account_id)
                
                if account_id:
                    utils.logger.info(f"[DouYinCrawler] 使用指定账号: {account_id}")
                else:
                    utils.logger.info(f"[DouYinCrawler] 使用默认账号（最新登录）")
                
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=cookie_str
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE  # start page number
        
        # 添加资源监控
        start_time = time.time()
        processed_count = 0
        
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            page = 0
            dy_search_id = ""
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    posts_res = await self.dy_client.search_info_by_keyword(keyword=keyword,
                                                                            offset=page * dy_limit_count - dy_limit_count,
                                                                            publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                                                                            search_id=dy_search_id
                                                                            )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(
                        f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                
                # 分批处理视频数据
                data_list = posts_res.get("data", [])
                batch_size = 5  # 每批处理5个视频
                
                for i in range(0, len(data_list), batch_size):
                    batch_data = data_list[i:i + batch_size]
                    utils.logger.info(f"[DouYinCrawler.search] Processing video batch {i//batch_size + 1}, items: {len(batch_data)}")
                    
                    for post_item in batch_data:
                    try:
                        aweme_info: Dict = post_item.get("aweme_info") or \
                                           post_item.get("aweme_mix_info", {}).get("mix_items")[0]
                    except TypeError:
                        continue
                        
                        try:
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    # 添加关键词信息
                    aweme_info["source_keyword"] = keyword
                    # 使用Redis存储
                    await self.douyin_store.store_content({**aweme_info, "task_id": self.task_id} if self.task_id else aweme_info)
                            processed_count += 1
                        except Exception as e:
                            utils.logger.error(f"[DouYinCrawler.search] Failed to process video: {e}")
                            continue
                    
                    # 添加间隔，避免请求过于频繁
                    await asyncio.sleep(1)
                
                # 检查处理时间，避免长时间运行
                elapsed_time = time.time() - start_time
                if elapsed_time > 300:  # 5分钟超时
                    utils.logger.warning(f"[DouYinCrawler.search] Processing time exceeded 5 minutes, stopping")
                    break
            
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")
            
            # 获取评论（如果启用）
            if config.ENABLE_GET_COMMENTS and aweme_list:
                try:
            await self.batch_get_note_comments(aweme_list)
                except Exception as e:
                    utils.logger.error(f"[DouYinCrawler.search] Failed to get comments: {e}")
            
            utils.logger.info(f"[DouYinCrawler.search] Search completed. Total processed: {processed_count}")

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post"""
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in config.DY_SPECIFIED_ID_LIST
        ]
        aweme_details = await asyncio.gather(*task_list)
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                # 使用Redis存储
                await self.douyin_store.store_content({**aweme_detail, "task_id": self.task_id} if self.task_id else aweme_detail)
        await self.batch_get_note_comments(config.DY_SPECIFIED_ID_LIST)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                return await self.dy_client.get_video_by_id(aweme_id)
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Processing {len(aweme_list)} videos for comments")
        
        # 限制并发数量
        max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(aweme_list))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 分批处理评论
        batch_size = 3  # 每批处理3个评论任务
        total_processed = 0
        
        for i in range(0, len(aweme_list), batch_size):
            batch_awemes = aweme_list[i:i + batch_size]
            
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Processing comment batch {i//batch_size + 1}, videos: {len(batch_awemes)}")

        task_list: List[Task] = []
            for aweme_id in batch_awemes:
            task = asyncio.create_task(
                self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
            
        if len(task_list) > 0:
                try:
                    # 添加超时控制
                    await asyncio.wait_for(
                        asyncio.wait(task_list),
                        timeout=120  # 2分钟超时
                    )
                    total_processed += len(batch_awemes)
                    utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Completed batch {i//batch_size + 1}")
                except asyncio.TimeoutError:
                    utils.logger.warning(f"[DouYinCrawler.batch_get_note_comments] Comment batch timeout")
                    break
                except Exception as e:
                    utils.logger.error(f"[DouYinCrawler.batch_get_note_comments] Comment batch error: {e}")
                    continue
            
            # 添加间隔，避免请求过于频繁
            await asyncio.sleep(2)
        
        utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Comment processing completed. Total processed: {total_processed}")

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                # 将关键词列表传递给 get_aweme_all_comments 方法
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=random.random(),
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=douyin_store.batch_update_dy_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
                )
                utils.logger.info(
                    f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        for user_id in config.DY_CREATOR_ID_LIST:
            creator_info: Dict = await self.dy_client.get_user_info(user_id)
            if creator_info:
                await douyin_store.save_creator(user_id, creator=creator_info)

            # Get all video information of the creator
            all_video_list = await self.dy_client.get_all_user_aweme_posts(
                sec_user_id=user_id,
                callback=self.fetch_creator_video_detail
            )

            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list
        ]

        note_details = await asyncio.gather(*task_list)
        for aweme_item in note_details:
            if aweme_item is not None:
                # 使用Redis存储
                await self.douyin_store.store_content({**aweme_item, "task_id": self.task_id} if self.task_id else aweme_item)

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DOUYINClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        douyin_client = DOUYINClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return douyin_client

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def close(self) -> None:
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def search_by_keywords(self, keywords: str, max_count: int = 50, 
                                account_id: str = None, session_id: str = None,
                                login_type: str = "qrcode", get_comments: bool = False,
                                save_data_option: str = "db", use_proxy: bool = False,
                                proxy_strategy: str = "disabled") -> List[Dict]:
        """
        根据关键词搜索抖音视频
        :param keywords: 搜索关键词
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_strategy: 代理策略
        :return: 搜索结果列表
        """
        try:
            utils.logger.info(f"[DouYinCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            
            # 设置配置
            import config
            config.KEYWORDS = keywords
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 由于Redis存储是通过回调函数处理的，我们需要从Redis中获取数据
            # 或者直接返回爬取过程中收集的数据
            results = []
            
            # 如果使用了Redis存储，尝试从Redis获取数据
            if hasattr(self, 'douyin_store') and hasattr(self.douyin_store, 'get_all_content'):
                results = await self.douyin_store.get_all_content()
            
            # 如果Redis中没有数据，尝试从任务结果中获取
            if not results and hasattr(self, 'task_id'):
                from utils.redis_manager import redis_manager
                try:
                    task_videos = await redis_manager.get_task_videos(self.task_id, "dy")
                    results = task_videos
                except Exception as e:
                    utils.logger.warning(f"[DouYinCrawler.search_by_keywords] 从Redis获取数据失败: {e}")
            
            utils.logger.info(f"[DouYinCrawler.search_by_keywords] 搜索完成，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler.search_by_keywords] 搜索失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[DouYinCrawler.search_by_keywords] 关闭浏览器时出现警告: {e}")

    async def get_user_notes(self, user_id: str, max_count: int = 50,
                            account_id: str = None, session_id: str = None,
                            login_type: str = "qrcode", get_comments: bool = False,
                            save_data_option: str = "db", use_proxy: bool = False,
                            proxy_strategy: str = "disabled") -> List[Dict]:
        """
        获取用户发布的视频
        :param user_id: 用户ID
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_strategy: 代理策略
        :return: 视频列表
        """
        try:
            utils.logger.info(f"[DouYinCrawler.get_user_notes] 开始获取用户视频: {user_id}")
            
            # 设置配置
            import config
            config.DY_SPECIFIED_ID_LIST = [user_id]
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'douyin_store') and hasattr(self.douyin_store, 'get_all_content'):
                results = await self.douyin_store.get_all_content()
            
            utils.logger.info(f"[DouYinCrawler.get_user_notes] 获取完成，共 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler.get_user_notes] 获取失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[DouYinCrawler.get_user_notes] 关闭浏览器时出现警告: {e}")
