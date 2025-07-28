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
from tenacity import RetryError

import config
from base.base_crawler import AbstractCrawler
from config import CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
from model.m_xiaohongshu import NoteUrlInfo
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import xhs as xhs_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import XiaoHongShuClient
from .exception import DataFetchError
from .field import SearchSortType
from .help import parse_note_info_from_note_url, get_search_id
from .login import XiaoHongShuLogin
from utils.db_utils import get_cookies_from_database
from .field import SearchNoteType


class XiaoHongShuCrawler(AbstractCrawler):
    context_page: Page
    xhs_client: XiaoHongShuClient
    browser_context: BrowserContext

    def __init__(self, task_id: str = None) -> None:
        self.index_url = "https://www.xiaohongshu.com"
        # self.user_agent = utils.get_user_agent()
        self.user_agent = config.UA if config.UA else "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        # 使用存储工厂创建存储对象
        from store.xhs import XhsStoreFactory
        self.xhs_store = XhsStoreFactory.create_store()
        self.task_id = task_id

    async def start(self) -> None:
        """Start xhs crawler"""
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info
            )

        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, playwright_proxy_format, self.user_agent, config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(
                path="libs/stealth.min.js"
            )
            # add a cookie attribute webId to avoid the appearance of a sliding captcha on the webpage
            await self.browser_context.add_cookies(
                [
                    {
                        "name": "webId",
                        "value": "xxx123",
                        "domain": ".xiaohongshu.com",
                        "path": "/",
                    }
                ]
            )
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.xhs_client = await self.create_xhs_client(httpx_proxy_format)
            # 检查登录状态
            ping_success = False
            cookie_str = None  # 初始化cookie_str变量
            
            try:
                ping_success = await self.xhs_client.pong()
                utils.logger.info(f"[XiaoHongShuCrawler] Ping result: {ping_success}")
            except Exception as e:
                utils.logger.warning(f"[XiaoHongShuCrawler] Ping failed: {e}")
                ping_success = False
            
            # 如果ping失败，从数据库读取cookies，支持账号选择
            if not ping_success:
                account_id = getattr(config, 'ACCOUNT_ID', None) or os.environ.get('CRAWLER_ACCOUNT_ID')
                cookie_str = await get_cookies_from_database("xhs", account_id)
                
                if account_id:
                    utils.logger.info(f"[XiaoHongShuCrawler] 使用指定账号: {account_id}")
                else:
                    utils.logger.info(f"[XiaoHongShuCrawler] 使用默认账号（最新登录）")
                
            # 如果有cookies且ping失败，尝试直接使用cookies
            if cookie_str and not ping_success:
                utils.logger.info("[XiaoHongShuCrawler] 检测到数据库中有cookies，尝试直接使用")
                try:
                    # 直接设置cookies到浏览器上下文
                    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
                    utils.logger.info(f"[XiaoHongShuCrawler] 转换后的cookies数量: {len(cookie_dict)}")
                    
                    for key, value in cookie_dict.items():
                        await self.browser_context.add_cookies([{
                            'name': key,
                            'value': value,
                            'domain': ".xiaohongshu.com",
                            'path': "/"
                        }])
                    
                    # 更新客户端cookies
                    await self.xhs_client.update_cookies(browser_context=self.browser_context)
                    utils.logger.info("[XiaoHongShuCrawler] 已更新客户端cookies")
                    
                    # 再次测试ping
                    try:
                        ping_success = await self.xhs_client.pong()
                        utils.logger.info(f"[XiaoHongShuCrawler] 使用数据库cookies后的ping结果: {ping_success}")
                    except Exception as ping_e:
                        utils.logger.warning(f"[XiaoHongShuCrawler] 使用数据库cookies后ping仍失败: {ping_e}")
                        ping_success = False
                    
                except Exception as cookie_e:
                    utils.logger.error(f"[XiaoHongShuCrawler] 设置数据库cookies失败: {cookie_e}")
                    ping_success = False
            
            # 如果ping仍然失败，强制重新登录
            if not ping_success:
                utils.logger.info("[XiaoHongShuCrawler] 需要重新登录")
                try:
                    login_obj = XiaoHongShuLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",  # input your phone number
                        browser_context=self.browser_context,
                        context_page=self.context_page,
                        cookie_str=cookie_str,
                    )
                    await login_obj.begin()
                    # 登录成功后更新客户端cookies
                    await self.xhs_client.update_cookies(browser_context=self.browser_context)
                    utils.logger.info("[XiaoHongShuCrawler] 登录成功，已更新cookies")
                    
                    # 登录后再次测试ping
                    try:
                        final_ping_success = await self.xhs_client.pong()
                        utils.logger.info(f"[XiaoHongShuCrawler] 登录后的ping结果: {final_ping_success}")
                        if not final_ping_success:
                            utils.logger.warning("[XiaoHongShuCrawler] 登录后ping仍失败，但继续尝试爬取")
                    except Exception as final_ping_e:
                        utils.logger.warning(f"[XiaoHongShuCrawler] 登录后ping测试失败: {final_ping_e}")
                        
                except Exception as login_e:
                    utils.logger.error(f"[XiaoHongShuCrawler] 登录失败: {login_e}")
                    # 即使登录失败，也尝试继续爬取
                    utils.logger.info("[XiaoHongShuCrawler] 登录失败但继续尝试爬取")
            else:
                utils.logger.info("[XiaoHongShuCrawler] 登录状态正常，无需重新登录")

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                await self.get_creators_and_notes()
            else:
                pass

            utils.logger.info("[XiaoHongShuCrawler.start] Xhs Crawler finished ...")

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info(
            "[XiaoHongShuCrawler.search] Begin search xiaohongshu keywords"
        )
        xhs_limit_count = 20  # xhs limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < xhs_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = xhs_limit_count
        start_page = config.START_PAGE
        
        # 获取搜索类型配置，默认为全部内容
        search_note_type = getattr(config, 'SEARCH_NOTE_TYPE', SearchNoteType.ALL)
        utils.logger.info(f"[XiaoHongShuCrawler.search] 搜索内容类型: {search_note_type.name}")
        
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[XiaoHongShuCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            search_id = get_search_id()
            
            # 添加资源监控
            start_time = time.time()
            processed_count = 0
            
            while (
                page - start_page + 1
            ) * xhs_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(
                        f"[XiaoHongShuCrawler.search] search xhs keyword: {keyword}, page: {page}, note_type: {search_note_type.name}"
                    )
                    note_ids: List[str] = []
                    xsec_tokens: List[str] = []
                    notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=search_id,
                        page=page,
                        sort=(
                            SearchSortType(config.SORT_TYPE)
                            if config.SORT_TYPE != ""
                            else SearchSortType.GENERAL
                        ),
                        note_type=search_note_type,  # 添加笔记类型筛选
                    )
                    utils.logger.info(
                        f"[XiaoHongShuCrawler.search] Search notes res:{notes_res}"
                    )
                    if not notes_res or not notes_res.get("has_more", False):
                        utils.logger.info("No more content!")
                        break
                    
                    # 添加详细的调试日志
                    items = notes_res.get("items", [])
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Found {len(items)} items in search results")
                    
                    # 过滤掉推荐查询和热门查询
                    filtered_items = [item for item in items if item.get("model_type") not in ("rec_query", "hot_query")]
                    utils.logger.info(f"[XiaoHongShuCrawler.search] After filtering, {len(filtered_items)} valid items remain")
                    
                    # 如果指定了视频类型，进一步过滤确保只获取视频内容
                    if search_note_type == SearchNoteType.VIDEO:
                        video_items = []
                        for item in filtered_items:
                            # 检查是否为视频类型
                            if item.get("model_type") == "note" and item.get("note_card", {}).get("type") == "video":
                                video_items.append(item)
                        filtered_items = video_items
                        utils.logger.info(f"[XiaoHongShuCrawler.search] After video filtering, {len(filtered_items)} video items remain")
                    
                    # 限制并发数量，避免资源耗尽
                    max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(filtered_items))
                    semaphore = asyncio.Semaphore(max_concurrent)
                    
                    # 分批处理，避免一次性创建太多任务
                    batch_size = 5  # 每批处理5个任务
                    note_details = []
                    
                    for i in range(0, len(filtered_items), batch_size):
                        batch_items = filtered_items[i:i + batch_size]
                        utils.logger.info(f"[XiaoHongShuCrawler.search] Processing batch {i//batch_size + 1}, items: {len(batch_items)}")
                        
                        task_list = [
                            self.get_note_detail_async_task(
                                note_id=post_item.get("id"),
                                xsec_source=post_item.get("xsec_source"),
                                xsec_token=post_item.get("xsec_token"),
                                semaphore=semaphore,
                            )
                            for post_item in batch_items
                        ]
                        
                        # 添加超时控制
                        try:
                            batch_results = await asyncio.wait_for(
                                asyncio.gather(*task_list, return_exceptions=True),
                                timeout=60  # 60秒超时
                            )
                            note_details.extend([r for r in batch_results if not isinstance(r, Exception)])
                        except asyncio.TimeoutError:
                            utils.logger.warning(f"[XiaoHongShuCrawler.search] Batch timeout, skipping remaining items")
                            break
                        except Exception as e:
                            utils.logger.error(f"[XiaoHongShuCrawler.search] Batch processing error: {e}")
                            continue
                        
                        # 添加间隔，避免请求过于频繁
                        await asyncio.sleep(1)
                    
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Retrieved {len(note_details)} note details")
                    
                    successful_details = 0
                    for note_detail in note_details:
                        if note_detail:
                            try:
                                await self.xhs_store.update_xhs_note(note_detail, task_id=self.task_id)
                                await self.get_notice_media(note_detail)
                                note_ids.append(note_detail.get("note_id"))
                                xsec_tokens.append(note_detail.get("xsec_token"))
                                successful_details += 1
                                processed_count += 1
                            except Exception as e:
                                utils.logger.error(f"[XiaoHongShuCrawler.search] Failed to process note: {e}")
                                continue
                    
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Successfully processed {successful_details} note details")
                    
                    # 检查处理时间，避免长时间运行
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 300:  # 5分钟超时
                        utils.logger.warning(f"[XiaoHongShuCrawler.search] Processing time exceeded 5 minutes, stopping")
                        break
                    
                    # 获取评论（如果启用）
                    if config.ENABLE_GET_COMMENTS and note_ids:
                        try:
                            await self.batch_get_note_comments(note_ids, xsec_tokens)
                        except Exception as e:
                            utils.logger.error(f"[XiaoHongShuCrawler.search] Failed to get comments: {e}")
                    
                    page += 1
                    
                except DataFetchError:
                    utils.logger.error(
                        "[XiaoHongShuCrawler.search] Get note detail error"
                    )
                    break
                except Exception as e:
                    utils.logger.error(
                        f"[XiaoHongShuCrawler.search] Unexpected error during search: {e}"
                    )
                    # 不要立即break，尝试继续
                    page += 1
                    continue
            
            utils.logger.info(f"[XiaoHongShuCrawler.search] Search completed. Total processed: {processed_count}")

    async def get_creators_and_notes(self) -> None:
        """Get creator's notes and retrieve their comment information."""
        utils.logger.info(
            "[XiaoHongShuCrawler.get_creators_and_notes] Begin get xiaohongshu creators"
        )
        for user_id in config.XHS_CREATOR_ID_LIST:
            # get creator detail info from web html content
            createor_info: Dict = await self.xhs_client.get_creator_info(
                user_id=user_id
            )
            if createor_info:
                await self.xhs_store.save_creator(user_id, creator=createor_info)

            # When proxy is not enabled, increase the crawling interval
            if config.ENABLE_IP_PROXY:
                crawl_interval = random.random()
            else:
                crawl_interval = random.uniform(1, config.CRAWLER_MAX_SLEEP_SEC)
            # Get all note information of the creator
            all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                user_id=user_id,
                crawl_interval=crawl_interval,
                callback=self.fetch_creator_notes_detail,
            )

            note_ids = []
            xsec_tokens = []
            for note_item in all_notes_list:
                note_ids.append(note_item.get("note_id"))
                xsec_tokens.append(note_item.get("xsec_token"))
            await self.batch_get_note_comments(note_ids, xsec_tokens)

    async def fetch_creator_notes_detail(self, note_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(
                note_id=post_item.get("note_id"),
                xsec_source=post_item.get("xsec_source"),
                xsec_token=post_item.get("xsec_token"),
                semaphore=semaphore,
            )
            for post_item in note_list
        ]

        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail:
                await self.xhs_store.update_xhs_note(note_detail, task_id=self.task_id)

    async def get_specified_notes(self):
        """
        Get the information and comments of the specified post
        must be specified note_id, xsec_source, xsec_token⚠️⚠️⚠️
        Returns:

        """
        get_note_detail_task_list = []
        for full_note_url in config.XHS_SPECIFIED_NOTE_URL_LIST:
            note_url_info: NoteUrlInfo = parse_note_info_from_note_url(full_note_url)
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_specified_notes] Parse note url info: {note_url_info}"
            )
            crawler_task = self.get_note_detail_async_task(
                note_id=note_url_info.note_id,
                xsec_source=note_url_info.xsec_source,
                xsec_token=note_url_info.xsec_token,
                semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
            )
            get_note_detail_task_list.append(crawler_task)

        need_get_comment_note_ids = []
        xsec_tokens = []
        note_details = await asyncio.gather(*get_note_detail_task_list)
        for note_detail in note_details:
            if note_detail:
                need_get_comment_note_ids.append(note_detail.get("note_id", ""))
                xsec_tokens.append(note_detail.get("xsec_token", ""))
                await self.xhs_store.update_xhs_note(note_detail, task_id=self.task_id)
        await self.batch_get_note_comments(need_get_comment_note_ids, xsec_tokens)

    async def get_note_detail_async_task(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict]:
        """Get note detail

        Args:
            note_id:
            xsec_source:
            xsec_token:
            semaphore:

        Returns:
            Dict: note detail
        """
        note_detail_from_html, note_detail_from_api = None, None
        async with semaphore:
            # When proxy is not enabled, increase the crawling interval
            if config.ENABLE_IP_PROXY:
                crawl_interval = random.random()
            else:
                crawl_interval = random.uniform(1, config.CRAWLER_MAX_SLEEP_SEC)
            try:
                # 尝试直接获取网页版笔记详情，携带cookie
                note_detail_from_html: Optional[Dict] = (
                    await self.xhs_client.get_note_by_id_from_html(
                        note_id, xsec_source, xsec_token, enable_cookie=True
                    )
                )
                time.sleep(crawl_interval)
                if not note_detail_from_html:
                    # 如果网页版笔记详情获取失败，则尝试不使用cookie获取
                    note_detail_from_html = (
                        await self.xhs_client.get_note_by_id_from_html(
                            note_id, xsec_source, xsec_token, enable_cookie=False
                        )
                    )
                    utils.logger.error(
                        f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error, note_id: {note_id}"
                    )
                if not note_detail_from_html:
                    # 如果网页版笔记详情获取失败，则尝试API获取
                    note_detail_from_api: Optional[Dict] = (
                        await self.xhs_client.get_note_by_id(
                            note_id, xsec_source, xsec_token
                        )
                    )
                note_detail = note_detail_from_html or note_detail_from_api
                if note_detail:
                    note_detail.update(
                        {"xsec_token": xsec_token, "xsec_source": xsec_source}
                    )
                    return note_detail
            except DataFetchError as ex:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] have not fund note detail note_id:{note_id}, err: {ex}"
                )
                return None

    async def batch_get_note_comments(
        self, note_list: List[str], xsec_tokens: List[str]
    ):
        """Batch get note comments"""
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[XiaoHongShuCrawler.batch_get_note_comments] Crawling comment mode is not enabled"
            )
            return

        utils.logger.info(
            f"[XiaoHongShuCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}"
        )
        
        # 限制并发数量
        max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(note_list))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 分批处理评论
        batch_size = 3  # 每批处理3个评论任务
        total_processed = 0
        
        for i in range(0, len(note_list), batch_size):
            batch_notes = note_list[i:i + batch_size]
            batch_tokens = xsec_tokens[i:i + batch_size]
            
            utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Processing comment batch {i//batch_size + 1}, notes: {len(batch_notes)}")
            
            task_list: List[Task] = []
            for index, note_id in enumerate(batch_notes):
                task = asyncio.create_task(
                    self.get_comments(
                        note_id=note_id, xsec_token=batch_tokens[index], semaphore=semaphore
                    ),
                    name=note_id,
                )
                task_list.append(task)
            
            try:
                # 添加超时控制
                await asyncio.wait_for(
                    asyncio.gather(*task_list, return_exceptions=True),
                    timeout=120  # 2分钟超时
                )
                total_processed += len(batch_notes)
                utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Completed batch {i//batch_size + 1}")
            except asyncio.TimeoutError:
                utils.logger.warning(f"[XiaoHongShuCrawler.batch_get_note_comments] Comment batch timeout")
                break
            except Exception as e:
                utils.logger.error(f"[XiaoHongShuCrawler.batch_get_note_comments] Comment batch error: {e}")
                continue
            
            # 添加间隔，避免请求过于频繁
            await asyncio.sleep(2)
        
        utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Comment processing completed. Total processed: {total_processed}")

    async def get_comments(
        self, note_id: str, xsec_token: str, semaphore: asyncio.Semaphore
    ):
        """Get note comments with keyword filtering and quantity limitation"""
        async with semaphore:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_comments] Begin get note id comments {note_id}"
            )
            # When proxy is not enabled, increase the crawling interval
            if config.ENABLE_IP_PROXY:
                crawl_interval = random.random()
            else:
                crawl_interval = random.uniform(1, config.CRAWLER_MAX_SLEEP_SEC)
            await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                xsec_token=xsec_token,
                crawl_interval=crawl_interval,
                callback=self.xhs_store.batch_update_xhs_note_comments,
                max_count=CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
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

    async def create_xhs_client(self, httpx_proxy: Optional[str]) -> XiaoHongShuClient:
        """Create xhs client"""
        utils.logger.info(
            "[XiaoHongShuCrawler.create_xhs_client] Begin create xiaohongshu API client ..."
        )
        cookie_str, cookie_dict = utils.convert_cookies(
            await self.browser_context.cookies()
        )
        xhs_client_obj = XiaoHongShuClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info(
            "[XiaoHongShuCrawler.launch_browser] Begin create browser context ..."
        )
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
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

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[XiaoHongShuCrawler.close] Browser context closed ...")

    async def get_notice_media(self, note_detail: Dict):
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_notice_media] Crawling image mode is not enabled"
            )
            return
        await self.get_note_images(note_detail)
        await self.get_notice_video(note_detail)

    async def get_note_images(self, note_item: Dict):
        """
        get note images. please use get_notice_media
        :param note_item:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            return
        note_id = note_item.get("note_id")
        image_list: List[Dict] = note_item.get("image_list", [])

        for img in image_list:
            if img.get("url_default") != "":
                img.update({"url": img.get("url_default")})

        if not image_list:
            return
        picNum = 0
        for pic in image_list:
            url = pic.get("url")
            if not url:
                continue
            content = await self.xhs_client.get_note_media(url)
            if content is None:
                continue
            extension_file_name = f"{picNum}.jpg"
            picNum += 1
            await self.xhs_store.update_xhs_note_image(note_id, content, extension_file_name)

    async def get_notice_video(self, note_item: Dict):
        """
        get note images. please use get_notice_media
        :param note_item:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            return
        note_id = note_item.get("note_id")

        videos = self.xhs_store.get_video_url_arr(note_item)

        if not videos:
            return
        videoNum = 0
        for url in videos:
            content = await self.xhs_client.get_note_media(url)
            if content is None:
                continue
            extension_file_name = f"{videoNum}.mp4"
            videoNum += 1
            await self.xhs_store.update_xhs_note_image(note_id, content, extension_file_name)

    async def search_by_keywords(self, keywords: str, max_count: int = 50, 
                                account_id: str = None, session_id: str = None,
                                login_type: str = "qrcode", get_comments: bool = False,
                                save_data_option: str = "db", use_proxy: bool = False,
                                proxy_strategy: str = "disabled", video_only: bool = False) -> List[Dict]:
        """
        根据关键词搜索小红书笔记
        :param keywords: 搜索关键词
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_strategy: 代理策略
        :param video_only: 是否只搜索视频内容
        :return: 搜索结果列表
        """
        try:
            utils.logger.info(f"[XiaoHongShuCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            if video_only:
                utils.logger.info("[XiaoHongShuCrawler.search_by_keywords] 启用视频筛选模式")
            
            # 设置配置
            import config
            config.KEYWORDS = keywords
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            config.CRAWLER_TYPE = "search"  # 设置爬取类型为搜索
            
            # 设置视频筛选
            if video_only:
                config.SEARCH_NOTE_TYPE = SearchNoteType.VIDEO
            else:
                config.SEARCH_NOTE_TYPE = SearchNoteType.ALL
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'xhs_store') and hasattr(self.xhs_store, 'get_all_content'):
                results = await self.xhs_store.get_all_content()
            
            utils.logger.info(f"[XiaoHongShuCrawler.search_by_keywords] 搜索完成，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuCrawler.search_by_keywords] 搜索失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[XiaoHongShuCrawler.search_by_keywords] 关闭浏览器时出现警告: {e}")

    async def get_user_notes(self, user_id: str, max_count: int = 50,
                            account_id: str = None, session_id: str = None,
                            login_type: str = "qrcode", get_comments: bool = False,
                            save_data_option: str = "db", use_proxy: bool = False,
                            proxy_strategy: str = "disabled", video_only: bool = False) -> List[Dict]:
        """
        获取用户发布的笔记
        :param user_id: 用户ID
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_strategy: 代理策略
        :param video_only: 是否只获取视频内容
        :return: 笔记列表
        """
        try:
            utils.logger.info(f"[XiaoHongShuCrawler.get_user_notes] 开始获取用户笔记: {user_id}")
            if video_only:
                utils.logger.info("[XiaoHongShuCrawler.get_user_notes] 启用视频筛选模式")
            
            # 设置配置
            import config
            config.XHS_SPECIFIED_ID_LIST = [user_id]
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            config.CRAWLER_TYPE = "creator"  # 设置爬取类型为创作者
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'xhs_store') and hasattr(self.xhs_store, 'get_all_content'):
                results = await self.xhs_store.get_all_content()
            
            # 如果指定了视频筛选，在结果中进一步过滤
            if video_only and results:
                video_results = []
                for result in results:
                    # 检查内容类型是否为视频
                    content_type = result.get('content_type', '')
                    if content_type == 'video':
                        video_results.append(result)
                results = video_results
                utils.logger.info(f"[XiaoHongShuCrawler.get_user_notes] 视频筛选后，剩余 {len(results)} 条视频数据")
            
            utils.logger.info(f"[XiaoHongShuCrawler.get_user_notes] 获取完成，共 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuCrawler.get_user_notes] 获取失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[XiaoHongShuCrawler.get_user_notes] 关闭浏览器时出现警告: {e}")
