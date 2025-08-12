# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:41
# @Desc    : 微博爬虫主流程代码


import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import weibo as weibo_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import WeiboClient
from .exception import DataFetchError
from .field import SearchType
from .help import filter_search_result_card
from .login import WeiboLogin
from utils.db_utils import get_cookies_from_database


class WeiboCrawler(AbstractCrawler):
    context_page: Page
    wb_client: WeiboClient
    browser_context: BrowserContext

    def __init__(self, task_id: str = None):
        self.index_url = "https://weibo.com"
        self.mobile_index_url = "https://m.weibo.cn"
        self.user_agent = utils.get_user_agent()
        self.mobile_user_agent = utils.get_mobile_user_agent()
        # 使用存储工厂创建存储对象
        from store.weibo import WeiboStoreFactory
        self.weibo_store = WeiboStoreFactory.create_store()
        self.task_id = task_id

    async def start(self):
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
                self.mobile_user_agent,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.mobile_index_url)

            # Create a client to interact with the xiaohongshu website.
            self.wb_client = await self.create_weibo_client(httpx_proxy_format)
            # if not await self.wb_client.pong():
            #     # 从数据库读取cookies，支持账号选择
            #     account_id = getattr(config, 'ACCOUNT_ID', None) or os.environ.get('CRAWLER_ACCOUNT_ID')
            #     cookie_str = await get_cookies_from_database("wb", account_id)
            #     
            #     if account_id:
            #         utils.logger.info(f"[WeiboCrawler] 使用指定账号: {account_id}")
            #     else:
            #         utils.logger.info(f"[WeiboCrawler] 使用默认账号（最新登录）")
            #     
            #     login_obj = WeiboLogin(
            #         login_type=config.LOGIN_TYPE,
            #         login_phone="",  # your phone number
            #         browser_context=self.browser_context,
            #         context_page=self.context_page,
            #         cookie_str=cookie_str
            #     )
            #     await login_obj.begin()
            #     await self.wb_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                await self.get_creators_and_notes()
            else:
                pass
            utils.logger.info("[WeiboCrawler.start] Weibo Crawler finished ...")

    async def search(self):
        """
        search weibo note with keywords
        :return:
        """
        utils.logger.info("[WeiboCrawler.search] Begin search weibo keywords")
        weibo_limit_count = 10  # weibo limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < weibo_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = weibo_limit_count
        start_page = config.START_PAGE
        # 🆕 修复：完全忽略配置文件中的关键字，使用动态传入的关键字
        # 从实例变量获取关键字，如果没有则使用配置文件中的（向后兼容）
        keywords_to_search = getattr(self, 'dynamic_keywords', None)
        if not keywords_to_search:
            utils.logger.warning("[WBCrawler.search] 未找到动态关键字，使用配置文件中的关键字（向后兼容）")
            keywords_to_search = config.KEYWORDS
        
        # 确保关键字不为空
        if not keywords_to_search or not keywords_to_search.strip():
            utils.logger.error("[WBCrawler.search] 没有有效的关键字，无法进行搜索")
            return
        
        # 处理多个关键字（用逗号分隔）
        keyword_list = [kw.strip() for kw in keywords_to_search.split(",") if kw.strip()]
        
        for keyword in keyword_list:
            source_keyword_var.set(keyword)
            utils.logger.info(f"[WeiboCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * weibo_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[WeiboCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                utils.logger.info(f"[WeiboCrawler.search] search weibo keyword: {keyword}, page: {page}")
                search_res = await self.wb_client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                    search_type=SearchType.DEFAULT
                )
                note_id_list: List[str] = []
                note_list = filter_search_result_card(search_res.get("cards"))
                for note_item in note_list:
                    if note_item:
                        mblog: Dict = note_item.get("mblog")
                        if mblog:
                            note_id_list.append(mblog.get("id"))
                            await self.weibo_store.update_weibo_note(note_item, task_id=self.task_id)
                            await self.get_note_images(mblog)

                page += 1
                await self.batch_get_notes_comments(note_id_list)

    async def get_specified_notes(self):
        """
        get specified notes info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_info_task(note_id=note_id, semaphore=semaphore) for note_id in
            config.WEIBO_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        for note_item in video_details:
            if note_item:
                await self.weibo_store.update_weibo_note(note_item, task_id=self.task_id)
        await self.batch_get_notes_comments(config.WEIBO_SPECIFIED_ID_LIST)

    async def get_note_info_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get note detail task
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.wb_client.get_note_info_by_id(note_id)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_info_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[WeiboCrawler.get_note_info_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_notes_comments(self, note_id_list: List[str]):
        """
        batch get notes comments
        :param note_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[WeiboCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[WeiboCrawler.batch_get_notes_comments] note ids:{note_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_id_list:
            task = asyncio.create_task(self.get_note_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_note_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for note id
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[WeiboCrawler.get_note_comments] begin get note_id: {note_id} comments ...")
                await self.wb_client.get_note_all_comments(
                    note_id=note_id,
                    crawl_interval=random.randint(1,3), # 微博对API的限流比较严重，所以延时提高一些
                    callback=self.weibo_store.batch_update_weibo_note_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
                )
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] get note_id: {note_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] may be been blocked, err:{e}")

    async def get_note_images(self, mblog: Dict):
        """
        get note images
        :param mblog:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[WeiboCrawler.get_note_images] Crawling image mode is not enabled")
            return
        
        pics: Dict = mblog.get("pics")
        if not pics:
            return
        for pic in pics:
            url = pic.get("url")
            if not url:
                continue
            content = await self.wb_client.get_note_image(url)
            if content != None:
                extension_file_name = url.split(".")[-1]
                await self.weibo_store.update_weibo_note_image(pic["pid"], content, extension_file_name)


    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info("[WeiboCrawler.get_creators_and_notes] Begin get weibo creators")
        for user_id in config.WEIBO_CREATOR_ID_LIST:
            createor_info_res: Dict = await self.wb_client.get_creator_info_by_id(creator_id=user_id)
            if createor_info_res:
                createor_info: Dict = createor_info_res.get("userInfo", {})
                utils.logger.info(f"[WeiboCrawler.get_creators_and_notes] creator info: {createor_info}")
                if not createor_info:
                    raise DataFetchError("Get creator info error")
                await self.weibo_store.save_creator(user_id, user_info=createor_info)

                # Get all note information of the creator
                all_notes_list = await self.wb_client.get_all_notes_by_creator_id(
                    creator_id=user_id,
                    container_id=createor_info_res.get("lfid_container_id"),
                    crawl_interval=0,
                    callback=self.weibo_store.batch_update_weibo_notes
                )

                note_ids = [note_item.get("mblog", {}).get("id") for note_item in all_notes_list if
                            note_item.get("mblog", {}).get("id")]
                await self.batch_get_notes_comments(note_ids)

            else:
                utils.logger.error(
                    f"[WeiboCrawler.get_creators_and_notes] get creator info error, creator_id:{user_id}")

    async def get_creators_and_notes_from_db(self, creators: List[Dict], max_count: int = 50,
                                           keywords: str = None, account_id: str = None, session_id: str = None,
                                           login_type: str = "qrcode", get_comments: bool = False,
                                           save_data_option: str = "db", use_proxy: bool = False,
                                           proxy_strategy: str = "disabled") -> List[Dict]:
        """
        从数据库获取创作者列表进行爬取
        Args:
            creators: 创作者列表，包含creator_id, platform, name, nickname
            max_count: 最大爬取数量
            account_id: 账号ID
            session_id: 会话ID
            login_type: 登录类型
            get_comments: 是否获取评论
            save_data_option: 数据保存方式
            use_proxy: 是否使用代理
            proxy_strategy: 代理策略
        Returns:
            List[Dict]: 爬取结果列表
        """
        try:
            utils.logger.info(f"[WeiboCrawler.get_creators_and_notes_from_db] 开始爬取 {len(creators)} 个创作者，最大数量限制: {max_count}")
            
            all_results = []
            total_processed = 0
            
            for creator in creators:
                user_id = creator.get("creator_id")
                creator_name = creator.get("name") or creator.get("nickname") or "未知创作者"
                
                utils.logger.info(f"[WeiboCrawler.get_creators_and_notes_from_db] 开始爬取创作者: {creator_name} (ID: {user_id})")
                
                try:
                    # 获取创作者详细信息
                    creator_info_res: Dict = await self.wb_client.get_creator_info_by_id(creator_id=user_id)
                    if creator_info_res:
                        creator_info: Dict = creator_info_res.get("userInfo", {})
                        if creator_info:
                            # 更新创作者信息到数据库
                            await self.weibo_store.save_creator(user_id, user_info=creator_info)
                            utils.logger.info(f"[WeiboCrawler.get_creators_and_notes_from_db] 创作者信息已更新: {creator_name}")
                        
                        # 获取创作者的所有微博
                        all_notes_list = await self.wb_client.get_all_notes_by_creator_id(
                            creator_id=user_id,
                            container_id=creator_info_res.get("lfid_container_id"),
                            crawl_interval=0,
                            callback=self.weibo_store.batch_update_weibo_notes
                        )
                        
                        if all_notes_list:
                            utils.logger.info(f"[WeiboCrawler.get_creators_and_notes_from_db] 获取到 {len(all_notes_list)} 条微博")
                        # 使用原生搜索API

                            
                            # 获取评论
                            if get_comments:
                                note_ids = [note_item.get("mblog", {}).get("id") for note_item in all_notes_list if
                                            note_item.get("mblog", {}).get("id")]
                                await self.batch_get_notes_comments(note_ids)
                            
                            # 收集结果
                            all_results.extend(all_notes_list)
                        else:
                            utils.logger.warning(f"[WeiboCrawler.get_creators_and_notes_from_db] 创作者 {creator_name} 没有获取到微博")
                    else:
                        utils.logger.error(f"[WeiboCrawler.get_creators_and_notes_from_db] 获取创作者信息失败: {user_id}")
                
                except Exception as e:
                    utils.logger.error(f"[WeiboCrawler.get_creators_and_notes_from_db] 爬取创作者 {creator_name} 失败: {e}")
                    continue
            
            utils.logger.info(f"[WeiboCrawler.get_creators_and_notes_from_db] 爬取完成，共获取 {len(all_results)} 条数据 (限制: {max_count})")
            return all_results
            
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler.get_creators_and_notes_from_db] 爬取失败: {e}")
            raise

    async def create_weibo_client(self, httpx_proxy: Optional[str]) -> WeiboClient:
        """Create xhs client"""
        utils.logger.info("[WeiboCrawler.create_weibo_client] Begin create weibo API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        weibo_client_obj = WeiboClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": utils.get_mobile_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return weibo_client_obj

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

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[WeiboCrawler.launch_browser] Begin create browser context ...")
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
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def search_by_keywords(self, keywords: str, max_count: int = 50, 
                                account_id: str = None, session_id: str = None,
                                login_type: str = "qrcode", get_comments: bool = False,
                                save_data_option: str = "db", use_proxy: bool = False,
                                proxy_ip: str = None) -> List[Dict]:
        """
        根据关键词搜索微博内容
        :param keywords: 搜索关键词
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_ip: 指定代理IP地址
        :return: 搜索结果列表
        """
        try:
            utils.logger.info(f"[WeiboCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            
            # 设置配置
            import config
            # 🆕 修复：使用动态关键字，完全忽略配置文件中的关键字
            if keywords and keywords.strip():
                # 将动态关键字设置到实例变量，而不是全局配置
                self.dynamic_keywords = keywords
                utils.logger.info(f"[WBCrawler.search_by_keywords] 设置动态关键字: '{keywords}'")
            else:
                utils.logger.warning("[WBCrawler.search_by_keywords] 关键字为空，将使用默认搜索")
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 🆕 清空之前收集的数据，确保新任务的数据正确
            try:
                from store.weibo import _clear_collected_data
                _clear_collected_data()
            except Exception as e:
                utils.logger.warning(f"[WeiboCrawler] 清空数据失败: {e}")
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'weibo_store') and hasattr(self.weibo_store, 'get_all_content'):
                results = await self.weibo_store.get_all_content()
            
            utils.logger.info(f"[WeiboCrawler.search_by_keywords] 搜索完成，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler.search_by_keywords] 搜索失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[WeiboCrawler.search_by_keywords] 关闭浏览器时出现警告: {e}")

    async def get_user_notes(self, user_id: str, max_count: int = 50,
                            account_id: str = None, session_id: str = None,
                            login_type: str = "qrcode", get_comments: bool = False,
                            save_data_option: str = "db", use_proxy: bool = False,
                            proxy_strategy: str = "disabled") -> List[Dict]:
        """
        获取用户发布的微博
        :param user_id: 用户ID
        :param max_count: 最大获取数量
        :param account_id: 账号ID
        :param session_id: 会话ID
        :param login_type: 登录类型
        :param get_comments: 是否获取评论
        :param save_data_option: 数据保存方式
        :param use_proxy: 是否使用代理
        :param proxy_strategy: 代理策略
        :return: 微博列表
        """
        try:
            utils.logger.info(f"[WeiboCrawler.get_user_notes] 开始获取用户微博: {user_id}")
            
            # 设置配置
            import config
            config.WEIBO_SPECIFIED_ID_LIST = [user_id]
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'weibo_store') and hasattr(self.weibo_store, 'get_all_content'):
                results = await self.weibo_store.get_all_content()
            
            utils.logger.info(f"[WeiboCrawler.get_user_notes] 获取完成，共 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler.get_user_notes] 获取失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[WeiboCrawler.get_user_notes] 关闭浏览器时出现警告: {e}")
