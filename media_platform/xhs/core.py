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
from typing import Any, Dict, List, Optional, Tuple

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
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        # 创建playwright实例，但不使用async with，让它在整个爬取过程中保持打开
        self.playwright = await async_playwright().start()
        
        # Launch a browser context.
        chromium = self.playwright.chromium
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
        
                # 🆕 简化：直接使用数据库中的token，无需复杂登录流程
        utils.logger.info("[XiaoHongShuCrawler] 开始使用数据库中的登录凭证...")
        
        # 从传入的参数中获取account_id
        account_id = getattr(self, 'account_id', None)
        if account_id:
            utils.logger.info(f"[XiaoHongShuCrawler] 使用指定账号: {account_id}")
        else:
            utils.logger.info(f"[XiaoHongShuCrawler] 使用默认账号（最新登录）")
        
        # 从数据库获取cookies
        cookie_str = await get_cookies_from_database("xhs", account_id)
        
        if cookie_str:
            utils.logger.info("[XiaoHongShuCrawler] 发现数据库中的cookies，直接使用...")
            try:
                # 设置cookies到浏览器
                await self.xhs_client.set_cookies_from_string(cookie_str)
                
                # 验证cookies是否有效
                # if await self.xhs_client.pong():
                #     utils.logger.info("[XiaoHongShuCrawler] ✅ 数据库中的cookies有效，开始爬取")
                #     # 更新cookies到客户端
                #     await self.xhs_client.update_cookies(browser_context=self.browser_context)
                # else:
                #     utils.logger.error("[XiaoHongShuCrawler] ❌ 数据库中的cookies无效，无法继续")
                #     raise Exception("数据库中的登录凭证无效，请重新登录")
            except Exception as e:
                utils.logger.error(f"[XiaoHongShuCrawler] 使用数据库cookies失败: {e}")
                raise Exception(f"使用数据库登录凭证失败: {str(e)}")
        else:
            utils.logger.error("[XiaoHongShuCrawler] ❌ 数据库中没有找到有效的登录凭证")
            raise Exception("数据库中没有找到有效的登录凭证，请先登录")
        
        utils.logger.info("[XiaoHongShuCrawler.start] 爬虫初始化完成，浏览器上下文已创建")
        
        # 🆕 修复：根据动态参数决定执行逻辑，而不是依赖配置文件
        crawler_type_var.set(config.CRAWLER_TYPE)
        
        # 检查是否有动态关键字，如果有则执行搜索
        if hasattr(self, 'dynamic_keywords') and self.dynamic_keywords:
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 检测到动态关键字: {self.dynamic_keywords}")
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 执行关键词搜索模式")
            await self.search()
        elif hasattr(self, 'dynamic_note_ids') and self.dynamic_note_ids:
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 检测到动态笔记ID: {self.dynamic_note_ids}")
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 执行指定笔记模式")
            await self.get_specified_notes()
        elif hasattr(self, 'dynamic_creators') and self.dynamic_creators:
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 检测到动态创作者: {self.dynamic_creators}")
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 执行创作者模式")
            await self.get_creators_and_notes()
        else:
            # 如果没有动态参数，则使用配置文件中的设置
            utils.logger.debug(f"[XiaoHongShuCrawler.start] 使用配置文件中的爬取类型: {config.CRAWLER_TYPE}")
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_notes()

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info(
            "[XiaoHongShuCrawler.search] Begin search xiaohongshu keywords"
        )
        xhs_limit_count = 20  # xhs limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < xhs_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = xhs_limit_count
        start_page = config.START_PAGE
        
        # 🆕 修复：默认使用视频筛选，专门爬取视频内容
        search_note_type = getattr(config, 'SEARCH_NOTE_TYPE', SearchNoteType.VIDEO)
        utils.logger.info(f"[XiaoHongShuCrawler.search] 搜索内容类型: {search_note_type.name} (1=视频, 0=全部, 2=图片)")
        
        # 🆕 修复：完全忽略配置文件中的关键字，使用动态传入的关键字
        # 从实例变量获取关键字，如果没有则使用配置文件中的（向后兼容）
        keywords_to_search = getattr(self, 'dynamic_keywords', None)
        if not keywords_to_search:
            utils.logger.warning("[XHSCrawler.search] 未找到动态关键字，使用配置文件中的关键字（向后兼容）")
            keywords_to_search = config.KEYWORDS
        
        # 确保关键字不为空
        if not keywords_to_search or not keywords_to_search.strip():
            utils.logger.error("[XHSCrawler.search] 没有有效的关键字，无法进行搜索")
            return
        
        # 处理多个关键字（用逗号分隔）
        keyword_list = [kw.strip() for kw in keywords_to_search.split(",") if kw.strip()]
        
        for keyword in keyword_list:
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[XiaoHongShuCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            search_id = get_search_id()
            
            # 添加资源监控
            start_time = time.time()
            processed_count = 0
            
            # 修复循环条件，添加更清晰的退出逻辑
            while True:
                # 检查是否超过最大数量限制
                current_total = (page - start_page + 1) * xhs_limit_count
                if current_total > config.CRAWLER_MAX_NOTES_COUNT:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] 已达到最大数量限制: {config.CRAWLER_MAX_NOTES_COUNT}, 当前预估总数: {current_total}")
                    break
                
                if page < start_page:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] search xhs keyword: {keyword}, page: {page}, note_type: {search_note_type.name}")
                    
                    # 添加随机延迟，避免请求过于频繁
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    search_result = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=xhs_limit_count,
                        note_type=search_note_type
                    )
                    
                    if not search_result or not search_result.get("items"):
                        utils.logger.info(f"[XiaoHongShuCrawler.search] 第{page}页没有数据，停止爬取")
                        break
                    
                    # 处理搜索结果
                    items = search_result.get("items", [])
                    utils.logger.info(f"[XiaoHongShuCrawler.search] 第{page}页获取到 {len(items)} 条数据")
                    
                    for item in items:
                        if processed_count >= config.CRAWLER_MAX_NOTES_COUNT:
                            utils.logger.info(f"[XiaoHongShuCrawler.search] 已达到最大数量限制: {config.CRAWLER_MAX_NOTES_COUNT}")
                            break
                        
                        try:
                            # 🆕 修复：恢复原有逻辑，但优化错误处理
                            note_id = item.get("id")
                            xsec_source = item.get("xsec_source", "pc_search")
                            xsec_token = item.get("xsec_token", "")
                            
                            if note_id and xsec_token:
                                utils.logger.debug(f"[XiaoHongShuCrawler.search] 获取笔记详细信息: {note_id}")
                                try:
                                    # 获取详细信息
                                    detail_item = await self.xhs_client.get_note_by_id(
                                        note_id=note_id,
                                        xsec_source=xsec_source,
                                        xsec_token=xsec_token
                                    )
                                    
                                    if detail_item:
                                        # 合并基本信息到详细信息中
                                        detail_item.update({
                                            "source_keyword": keyword,
                                            "id": note_id,  # 确保ID字段存在
                                            "xsec_source": xsec_source,
                                            "xsec_token": xsec_token
                                        })
                                        
                                        # 使用详细信息存储
                                        await self.xhs_store.store_content({**detail_item, "task_id": self.task_id} if self.task_id else detail_item)
                                        processed_count += 1
                                        utils.logger.debug(f"[XiaoHongShuCrawler.search] 成功获取并存储笔记详细信息: {note_id}")
                                    else:
                                        utils.logger.debug(f"[XiaoHongShuCrawler.search] 详细信息获取失败，使用基本信息: {note_id}")
                                        # 如果获取详细信息失败，使用基本信息
                                        item["source_keyword"] = keyword
                                        await self.xhs_store.store_content({**item, "task_id": self.task_id} if self.task_id else item)
                                        processed_count += 1
                                        
                                except Exception as detail_e:
                                    utils.logger.debug(f"[XiaoHongShuCrawler.search] 获取详细信息异常，使用基本信息: {detail_e}")
                                    # 如果获取详细信息失败，使用基本信息
                                    item["source_keyword"] = keyword
                                    await self.xhs_store.store_content({**item, "task_id": self.task_id} if self.task_id else item)
                                    processed_count += 1
                            else:
                                utils.logger.debug(f"[XiaoHongShuCrawler.search] 笔记缺少必要信息，跳过: note_id={note_id}, xsec_token={xsec_token}")
                                continue
                                
                        except Exception as e:
                            utils.logger.error(f"[XiaoHongShuCrawler.search] 处理数据项失败: {e}")
                            continue
                    
                    page += 1
                    
                except DataFetchError as e:
                    utils.logger.error(f"[XiaoHongShuCrawler.search] 搜索失败 (DataFetchError): {e}")
                    # 如果是网络错误，等待更长时间后重试
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    utils.logger.error(f"[XiaoHongShuCrawler.search] 搜索过程中发生未知错误: {e}")
                    # 等待一段时间后重试
                    await asyncio.sleep(3)
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
            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 开始爬取 {len(creators)} 个创作者")
            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 最大数量限制: {max_count}")
            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 关键词: '{keywords}'")
            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 创作者列表: {[c.get('name', c.get('nickname', '未知')) for c in creators]}")
            
            # 确保客户端已初始化
            if not hasattr(self, 'xhs_client') or self.xhs_client is None:
                utils.logger.error("[XiaoHongShuCrawler.get_creators_and_notes_from_db] xhs_client 未初始化")
                raise Exception("小红书客户端未初始化，请先调用start()方法")
            
            all_results = []
            
            for creator in creators:
                user_id = creator.get("creator_id")
                creator_name = creator.get("name") or creator.get("nickname") or "未知创作者"
                
                utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 开始爬取创作者: {creator_name} (ID: {user_id})")
                
                try:
                    # 获取创作者详细信息
                    creator_info: Dict = await self.xhs_client.get_creator_info(user_id=user_id)
                    if creator_info:
                        # 更新创作者信息到数据库
                        await self.xhs_store.save_creator(user_id, creator=creator_info)
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 创作者信息已更新: {creator_name}")
                        
                        # 🆕 更新任务的creator_ref_ids字段（参考B站和快手实现）
                        try:
                            from api.crawler_core import update_task_creator_ref_ids
                            await update_task_creator_ref_ids(self.task_id, [str(user_id)])
                            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 任务creator_ref_ids已更新: {user_id}")
                        except Exception as e:
                            utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 更新任务creator_ref_ids失败: {e}")
                    
                    # 🆕 优化：根据是否有关键词选择不同的获取方式（参考B站和快手实现）
                    if keywords and keywords.strip():
                        # 使用关键词搜索获取笔记
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 使用关键词 '{keywords}' 搜索创作者 {creator_name} 的笔记")
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 关键词类型: {type(keywords)}, 长度: {len(keywords)}")
                        
                        # 确保关键词不为空且有效
                        clean_keywords = keywords.strip()
                        if clean_keywords:
                            all_notes_list = await self.xhs_client.search_user_notes(user_id, clean_keywords, max_count)
                            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 关键词搜索完成，获取到 {len(all_notes_list) if all_notes_list else 0} 条笔记")
                        else:
                            utils.logger.warning(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 关键词为空，使用默认获取方式")
                            # 设置爬取间隔
                            if config.ENABLE_IP_PROXY:
                                crawl_interval = random.random()
                            else:
                                crawl_interval = random.uniform(1, config.CRAWLER_MAX_SLEEP_SEC)
                            
                            all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                                user_id=user_id,
                                crawl_interval=crawl_interval,
                                callback=self.fetch_creator_notes_detail,
                            )
                    else:
                        # 获取创作者的所有笔记
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 获取创作者 {creator_name} 的所有笔记（无关键词筛选）")
                        
                        # 设置爬取间隔
                        if config.ENABLE_IP_PROXY:
                            crawl_interval = random.random()
                        else:
                            crawl_interval = random.uniform(1, config.CRAWLER_MAX_SLEEP_SEC)
                        
                        all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                            user_id=user_id,
                            crawl_interval=crawl_interval,
                            callback=self.fetch_creator_notes_detail,
                        )
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 获取所有笔记完成，获取到 {len(all_notes_list) if all_notes_list else 0} 条笔记")
                    
                    if all_notes_list:
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 获取到 {len(all_notes_list)} 条笔记")
                        
                        # 🆕 处理每个笔记，获取详细信息（参考B站和快手实现）
                        utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 开始处理 {len(all_notes_list)} 条笔记")
                        
                        for i, note_item in enumerate(all_notes_list):
                            try:
                                utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 处理第 {i+1} 条笔记")
                                
                                # 保存到数据库
                                utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 开始保存到数据库")
                                try:
                                    await self.xhs_store.update_xhs_note(note_item, task_id=self.task_id)
                                    utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 笔记数据保存成功")
                                except Exception as e:
                                    utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 保存笔记数据失败: {e}")
                                    continue
                                
                                all_results.append(note_item)
                                
                                # 检查是否达到数量限制
                                if len(all_results) >= max_count:
                                    utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 已达到最大数量限制 {max_count}")
                                    break
                                
                            except Exception as e:
                                utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 处理笔记时出错: {e}")
                                continue
                        
                        # 如果已达到数量限制，跳出创作者循环
                        if len(all_results) >= max_count:
                            break
                        
                        # 🆕 获取评论（参考B站和快手实现）
                        if get_comments and len(all_results) < max_count:
                            note_ids = []
                            xsec_tokens = []
                            for note_item in all_notes_list:
                                note_ids.append(note_item.get("note_id"))
                                xsec_tokens.append(note_item.get("xsec_token"))
                            
                            if note_ids:
                                utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 为 {len(note_ids)} 条笔记获取评论")
                                await self.batch_get_note_comments(note_ids, xsec_tokens)
                    else:
                        utils.logger.warning(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 创作者 {creator_name} 没有获取到笔记")
                
                except Exception as e:
                    utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 爬取创作者 {creator_name} 失败: {e}")
                    continue
            
            utils.logger.info(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 爬取完成，共获取 {len(all_results)} 条数据 (限制: {max_count})")
            return all_results
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuCrawler.get_creators_and_notes_from_db] 爬取失败: {e}")
            raise

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
        """安全关闭浏览器和相关资源"""
        try:
            if hasattr(self, 'browser_context') and self.browser_context:
                await self.browser_context.close()
                utils.logger.info("[XiaoHongShuCrawler] 浏览器上下文已关闭")
            
            if hasattr(self, 'context_page') and self.context_page:
                await self.context_page.close()
                utils.logger.info("[XiaoHongShuCrawler] 页面已关闭")
            
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                utils.logger.info("[XiaoHongShuCrawler] Playwright实例已关闭")
                
        except Exception as e:
            utils.logger.warning(f"[XiaoHongShuCrawler.close] 关闭资源时出现警告: {e}")

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
                                proxy_strategy: str = "disabled") -> List[Dict]:
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
        :return: 搜索结果列表
        """
        try:
            utils.logger.info(f"[XiaoHongShuCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            
            # 🆕 设置account_id到实例变量，供start方法使用
            self.account_id = account_id
            if account_id:
                utils.logger.info(f"[XiaoHongShuCrawler.search_by_keywords] 使用指定账号ID: {account_id}")
            
            # 设置配置
            import config
            # 🆕 修复：使用动态关键字，完全忽略配置文件中的关键字
            if keywords and keywords.strip():
                # 将动态关键字设置到实例变量，而不是全局配置
                self.dynamic_keywords = keywords
                utils.logger.info(f"[XHSCrawler.search_by_keywords] 设置动态关键字: '{keywords}'")
            else:
                utils.logger.warning("[XHSCrawler.search_by_keywords] 关键字为空，将使用默认搜索")
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
            if hasattr(self, 'xhs_store') and hasattr(self.xhs_store, 'get_all_content'):
                results = await self.xhs_store.get_all_content()
            
            # 如果Redis中没有数据，尝试从任务结果中获取
            if not results and hasattr(self, 'task_id'):
                from utils.redis_manager import redis_manager
                try:
                    task_videos = await redis_manager.get_task_videos(self.task_id, "xhs")
                    results = task_videos
                except Exception as e:
                    utils.logger.warning(f"[XiaoHongShuCrawler.search_by_keywords] 从Redis获取数据失败: {e}")
            
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
