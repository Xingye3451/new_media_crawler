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
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import kuaishou as kuaishou_store
from tools import utils
from var import comment_tasks_var, crawler_type_var, source_keyword_var

from .client import KuaiShouClient
from .exception import DataFetchError
from .login import KuaishouLogin
from utils.db_utils import get_cookies_from_database


class KuaishouCrawler(AbstractCrawler):
    context_page: Page
    ks_client: KuaiShouClient
    browser_context: BrowserContext

    def __init__(self, task_id: str = None):
        self.index_url = "https://www.kuaishou.com"
        # 使用存储工厂创建存储对象
        from store.kuaishou import KuaishouStoreFactory
        self.kuaishou_store = KuaishouStoreFactory.create_store()
        self.user_agent = utils.get_user_agent()
        self.task_id = task_id

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

            # 添加方法存在性检查
            if not hasattr(self, 'create_ks_client'):
                raise AttributeError("KuaishouCrawler 缺少 create_ks_client 方法")
            
            self.ks_client = await self.create_ks_client(httpx_proxy_format)
            
            # 🆕 简化：直接使用数据库中的token，无需复杂登录流程
            utils.logger.info("[KuaishouCrawler] 开始使用数据库中的登录凭证...")
            
            # 从传入的参数中获取account_id
            account_id = getattr(self, 'account_id', None)
            if account_id:
                utils.logger.info(f"[KuaishouCrawler] 使用指定账号: {account_id}")
            else:
                utils.logger.info(f"[KuaishouCrawler] 使用默认账号（最新登录）")
            
            # 从数据库获取cookies
            cookie_str = await get_cookies_from_database("ks", account_id)
            
            if cookie_str:
                utils.logger.info("[KuaishouCrawler] 发现数据库中的cookies，直接使用...")
                try:
                    # 设置cookies到浏览器
                    await self.ks_client.set_cookies_from_string(cookie_str)
                    
                    # 验证cookies是否有效
                    # if await self.ks_client.pong():
                    #     utils.logger.info("[KuaishouCrawler] ✅ 数据库中的cookies有效，开始爬取")
                    #     # 更新cookies到客户端
                    #     await self.ks_client.update_cookies(browser_context=self.browser_context)
                    # else:
                    #     utils.logger.error("[KuaishouCrawler] ❌ 数据库中的cookies无效，无法继续")
                    #     raise Exception("数据库中的登录凭证无效，请重新登录")
                except Exception as e:
                    utils.logger.error(f"[KuaishouCrawler] 使用数据库cookies失败: {e}")
                    raise Exception(f"使用数据库登录凭证失败: {str(e)}")
            else:
                utils.logger.error("[KuaishouCrawler] ❌ 数据库中没有找到有效的登录凭证")
                raise Exception("数据库中没有找到有效的登录凭证，请先登录")
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_notes()

            utils.logger.info("[KuaishouCrawler.start] Kuaishou Crawler finished ...")

    async def search(self):
        utils.logger.info("[KuaishouCrawler.search] Begin search kuaishou keywords")
        ks_limit_count = 20  # kuaishou limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < ks_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = ks_limit_count
        start_page = config.START_PAGE
        
        # 添加资源监控
        start_time = time.time()
        processed_count = 0
        
        for keyword in config.KEYWORDS.split(","):
            search_session_id = ""
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[KuaishouCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            while (
                page - start_page + 1
            ) * ks_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[KuaishouCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                
                try:
                    utils.logger.info(
                        f"[KuaishouCrawler.search] search kuaishou keyword: {keyword}, page: {page}"
                    )
                    video_id_list: List[str] = []
                    videos_res = await self.ks_client.search_info_by_keyword(
                        keyword=keyword,
                        pcursor=str(page),
                        search_session_id=search_session_id,
                    )
                    if not videos_res:
                        utils.logger.error(
                            f"[KuaishouCrawler.search] search info by keyword:{keyword} not found data"
                        )
                        continue

                    vision_search_photo: Dict = videos_res.get("visionSearchPhoto")
                    if vision_search_photo.get("result") != 1:
                        utils.logger.error(
                            f"[KuaishouCrawler.search] search info by keyword:{keyword} not found data "
                        )
                        continue
                    search_session_id = vision_search_photo.get("searchSessionId", "")
                    
                    # 分批处理视频详情
                    feeds = vision_search_photo.get("feeds", [])
                    batch_size = 5  # 每批处理5个视频
                    
                    for i in range(0, len(feeds), batch_size):
                        batch_feeds = feeds[i:i + batch_size]
                        utils.logger.info(f"[KuaishouCrawler.search] Processing video batch {i//batch_size + 1}, items: {len(batch_feeds)}")
                        
                        for video_detail in batch_feeds:
                            try:
                                import json
                                utils.logger.info(f"[KuaishouCrawler] 原始视频数据: {json.dumps(video_detail, ensure_ascii=False)}")
                                video_id_list.append(video_detail.get("photo", {}).get("id"))
                                await self.kuaishou_store.update_kuaishou_video(video_item=video_detail, task_id=self.task_id)
                                processed_count += 1
                            except Exception as e:
                                utils.logger.error(f"[KuaishouCrawler.search] Failed to process video: {e}")
                                continue
                        
                        # 添加间隔，避免请求过于频繁
                        await asyncio.sleep(1)
                    
                    # 检查处理时间，避免长时间运行
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 300:  # 5分钟超时
                        utils.logger.warning(f"[KuaishouCrawler.search] Processing time exceeded 5 minutes, stopping")
                        break
                    
                    # 获取评论（如果启用）
                    if config.ENABLE_GET_COMMENTS and video_id_list:
                        try:
                            await self.batch_get_video_comments(video_id_list)
                        except Exception as e:
                            utils.logger.error(f"[KuaishouCrawler.search] Failed to get comments: {e}")
                    
                    page += 1
                    
                except Exception as e:
                    utils.logger.error(
                        f"[KuaishouCrawler.search] Unexpected error during search: {e}"
                    )
                    page += 1
                    continue
            
            utils.logger.info(f"[KuaishouCrawler.search] Search completed. Total processed: {processed_count}")

    async def get_specified_videos(self):
        """Get the information and comments of the specified post"""
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(video_id=video_id, semaphore=semaphore)
            for video_id in config.KS_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await self.kuaishou_store.update_kuaishou_video(video_detail, task_id=self.task_id)
        await self.batch_get_video_comments(config.KS_SPECIFIED_ID_LIST)

    async def get_video_info_task(
        self, video_id: str, semaphore: asyncio.Semaphore
    ) -> Optional[Dict]:
        """Get video detail task"""
        async with semaphore:
            try:
                result = await self.ks_client.get_video_info(video_id)
                utils.logger.info(
                    f"[KuaishouCrawler.get_video_info_task] Get video_id:{video_id} info result: {result} ..."
                )
                return result.get("visionVideoDetail")
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_video_info_task] Get video detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_video_info_task] have not fund video detail video_id:{video_id}, err: {ex}"
                )
                return None

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[KuaishouCrawler.batch_get_video_comments] Crawling comment mode is not enabled"
            )
            return

        utils.logger.info(
            f"[KuaishouCrawler.batch_get_video_comments] video ids:{video_id_list}"
        )
        
        # 限制并发数量
        max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(video_id_list))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 分批处理评论
        batch_size = 3  # 每批处理3个评论任务
        total_processed = 0
        
        for i in range(0, len(video_id_list), batch_size):
            batch_videos = video_id_list[i:i + batch_size]
            
            utils.logger.info(f"[KuaishouCrawler.batch_get_video_comments] Processing comment batch {i//batch_size + 1}, videos: {len(batch_videos)}")
            
            task_list: List[Task] = []
            for video_id in batch_videos:
                task = asyncio.create_task(
                    self.get_comments(video_id, semaphore), name=video_id
                )
                task_list.append(task)

            try:
                # 添加超时控制
                await asyncio.wait_for(
                    asyncio.gather(*task_list, return_exceptions=True),
                    timeout=120  # 2分钟超时
                )
                total_processed += len(batch_videos)
                utils.logger.info(f"[KuaishouCrawler.batch_get_video_comments] Completed batch {i//batch_size + 1}")
            except asyncio.TimeoutError:
                utils.logger.warning(f"[KuaishouCrawler.batch_get_video_comments] Comment batch timeout")
                break
            except Exception as e:
                utils.logger.error(f"[KuaishouCrawler.batch_get_video_comments] Comment batch error: {e}")
                continue
            
            # 添加间隔，避免请求过于频繁
            await asyncio.sleep(2)
        
        utils.logger.info(f"[KuaishouCrawler.batch_get_video_comments] Comment processing completed. Total processed: {total_processed}")

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(
                    f"[KuaishouCrawler.get_comments] begin get video_id: {video_id} comments ..."
                )
                await self.ks_client.get_video_all_comments(
                    photo_id=video_id,
                    crawl_interval=random.random(),
                    callback=self.kuaishou_store.batch_update_ks_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_comments] get video_id: {video_id} comment error: {ex}"
                )
            except Exception as e:
                utils.logger.error(
                    f"[KuaishouCrawler.get_comments] may be been blocked, err:{e}"
                )
                # use time.sleeep block main coroutine instead of asyncio.sleep and cacel running comment task
                # maybe kuaishou block our request, we will take a nap and update the cookie again
                current_running_tasks = comment_tasks_var.get()
                for task in current_running_tasks:
                    task.cancel()
                time.sleep(20)
                await self.context_page.goto(f"{self.index_url}?isHome=1")
                await self.ks_client.update_cookies(
                    browser_context=self.browser_context
                )

    @staticmethod
    def format_proxy_info(
        ip_proxy_info: IpInfoModel,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
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

    async def create_ks_client(self, httpx_proxy: Optional[str]) -> KuaiShouClient:
        """Create ks client"""
        utils.logger.info(
            "[KuaishouCrawler.create_ks_client] Begin create kuaishou API client ..."
        )
        cookie_str, cookie_dict = utils.convert_cookies(
            await self.browser_context.cookies()
        )
        ks_client_obj = KuaiShouClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": self.index_url,
                "Referer": self.index_url,
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return ks_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info(
            "[KuaishouCrawler.launch_browser] Begin create browser context ..."
        )
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM
            )  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}, user_agent=user_agent
            )
            return browser_context

    async def get_creators_and_videos(self) -> None:
        """Get creator's videos and retrieve their comment information."""
        utils.logger.info(
            "[KuaiShouCrawler.get_creators_and_videos] Begin get kuaishou creators"
        )
        for user_id in config.KS_CREATOR_ID_LIST:
            # get creator detail info from web html content
            createor_info: Dict = await self.ks_client.get_creator_info(user_id=user_id)
            if createor_info:
                await self.kuaishou_store.save_creator(user_id, creator=createor_info)

            # Get all video information of the creator
            all_video_list = await self.ks_client.get_all_videos_by_creator(
                user_id=user_id,
                crawl_interval=random.random(),
                callback=self.fetch_creator_video_detail,
            )

            video_ids = [
                video_item.get("photo", {}).get("id") for video_item in all_video_list
            ]
            await self.batch_get_video_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(post_item.get("photo", {}).get("id"), semaphore)
            for post_item in video_list
        ]

        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await self.kuaishou_store.update_kuaishou_video(video_detail, task_id=self.task_id)

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[KuaishouCrawler.close] Browser context closed ...")

    async def search_by_keywords(self, keywords: str, max_count: int = 50, 
                                account_id: str = None, session_id: str = None,
                                login_type: str = "qrcode", get_comments: bool = False,
                                save_data_option: str = "db", use_proxy: bool = False,
                                proxy_strategy: str = "disabled") -> List[Dict]:
        """
        根据关键词搜索快手视频
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
            utils.logger.info(f"[KuaishouCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            
            # 🆕 设置account_id到实例变量，供start方法使用
            self.account_id = account_id
            if account_id:
                utils.logger.info(f"[KuaishouCrawler.search_by_keywords] 使用指定账号ID: {account_id}")
            
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
            if hasattr(self, 'kuaishou_store') and hasattr(self.kuaishou_store, 'get_all_content'):
                results = await self.kuaishou_store.get_all_content()
            
            # 如果Redis中没有数据，尝试从任务结果中获取
            if not results and hasattr(self, 'task_id'):
                from utils.redis_manager import redis_manager
                try:
                    task_videos = await redis_manager.get_task_videos(self.task_id, "ks")
                    results = task_videos
                except Exception as e:
                    utils.logger.warning(f"[KuaishouCrawler.search_by_keywords] 从Redis获取数据失败: {e}")
            
            utils.logger.info(f"[KuaishouCrawler.search_by_keywords] 搜索完成，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[KuaishouCrawler.search_by_keywords] 搜索失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[KuaishouCrawler.search_by_keywords] 关闭浏览器时出现警告: {e}")

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
            utils.logger.info(f"[KuaishouCrawler.get_user_notes] 开始获取用户视频: {user_id}")
            
            # 设置配置
            import config
            config.KS_SPECIFIED_ID_LIST = [user_id]
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'kuaishou_store') and hasattr(self.kuaishou_store, 'get_all_content'):
                results = await self.kuaishou_store.get_all_content()
            
            utils.logger.info(f"[KuaishouCrawler.get_user_notes] 获取完成，共 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[KuaishouCrawler.get_user_notes] 获取失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[KuaishouCrawler.get_user_notes] 关闭浏览器时出现警告: {e}")
