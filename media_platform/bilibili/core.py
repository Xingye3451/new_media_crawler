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
# @Time    : 2023/12/2 18:44
# @Desc    : B站爬虫

import asyncio
import os
import random
import json
from asyncio import Task
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import time

from playwright.async_api import (BrowserContext, BrowserType, Page, async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .login import BilibiliLogin
from utils.db_utils import get_cookies_from_database


class BilibiliCrawler(AbstractCrawler):
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext

    def __init__(self, task_id: str = None):
        self.index_url = "https://www.bilibili.com"
        self.user_agent = utils.get_user_agent()
        # 使用存储工厂创建存储对象
        from store.bilibili import BilibiliStoreFactory
        self.bilibili_store = BilibiliStoreFactory.create_store()
        self.task_id = task_id

    async def start(self) -> None:
        """初始化爬虫，创建浏览器上下文和客户端"""
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
            chromium,
            None,
            self.user_agent,
            headless=config.HEADLESS
        )
        # stealth.min.js is a js script to prevent the website from detecting the crawler.
        await self.browser_context.add_init_script(path="libs/stealth.min.js")
        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(self.index_url)

        # Create a client to interact with the bilibili website.
        self.bili_client = await self.create_bilibili_client(httpx_proxy_format)
        
        # 🆕 简化：直接使用数据库中的token，无需复杂登录流程
        utils.logger.info("[BilibiliCrawler] 开始使用数据库中的登录凭证...")
        
        # 从传入的参数中获取account_id
        account_id = getattr(self, 'account_id', None)
        if account_id:
            utils.logger.info(f"[BilibiliCrawler] 使用指定账号: {account_id}")
        else:
            utils.logger.info(f"[BilibiliCrawler] 使用默认账号（最新登录）")
        
        # 从数据库获取cookies
        cookie_str = await get_cookies_from_database("bili", account_id)
        
        if cookie_str:
            utils.logger.info("[BilibiliCrawler] 发现数据库中的cookies，直接使用...")
            try:
                # 设置cookies到浏览器
                await self.bili_client.set_cookies_from_string(cookie_str)
                
                # 验证cookies是否有效
                if await self.bili_client.pong():
                    utils.logger.info("[BilibiliCrawler] ✅ 数据库中的cookies有效，开始爬取")
                    # 更新cookies到客户端
                    await self.bili_client.update_cookies(browser_context=self.browser_context)
                else:
                    utils.logger.error("[BilibiliCrawler] ❌ 数据库中的cookies无效，无法继续")
                    raise Exception("数据库中的登录凭证无效，请重新登录")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler] 使用数据库cookies失败: {e}")
                raise Exception(f"使用数据库登录凭证失败: {str(e)}")
        else:
            utils.logger.error("[BilibiliCrawler] ❌ 数据库中没有找到有效的登录凭证")
            raise Exception("数据库中没有找到有效的登录凭证，请先登录")
        
        utils.logger.info("[BilibiliCrawler.start] 爬虫初始化完成，浏览器上下文已创建")

    async def get_creators_and_notes(self) -> None:
        """Get creator's videos and retrieve their comment information."""
        utils.logger.info(
            "[BilibiliCrawler.get_creators_and_notes] Begin get bilibili creators"
        )
        for creator_id in config.BILI_CREATOR_ID_LIST:
            # get creator detail info
            creator_info: Dict = await self.bili_client.get_creator_info(creator_id=int(creator_id))
            if creator_info:
                await self.bilibili_store.store_creator(creator_info)
                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes] creator info: {creator_info}")

            # Get all video information of the creator
            all_video_list = await self.get_creator_videos(creator_id=int(creator_id))
            if all_video_list:
                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes] got creator_id:{creator_id} videos len : {len(all_video_list)}")
                
                # 处理每个视频，获取详细信息和播放地址
                for video_item in all_video_list:
                    try:
                        # 获取视频详细信息
                        video_detail = await self.get_video_info_task(
                            aid=video_item.get("aid", 0), 
                            bvid=video_item.get("bvid", ""), 
                            semaphore=asyncio.Semaphore(5)
                        )
                        
                        if video_detail:
                            # 获取播放地址
                            video_aid = video_detail.get("View", {}).get("aid")
                            video_cid = video_detail.get("View", {}).get("cid")
                            
                            if video_aid and video_cid:
                                play_url_result = await self.get_video_play_url_task(
                                    video_aid, video_cid, asyncio.Semaphore(5)
                                )
                                if play_url_result:
                                    video_detail.update(play_url_result)
                            
                            # 保存到数据库
                            await self.bilibili_store.update_bilibili_video(video_detail, task_id=self.task_id)
                            await self.bilibili_store.update_up_info(video_detail)
                            await self.get_bilibili_video(video_detail, asyncio.Semaphore(5))
                        
                    except Exception as e:
                        utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes] 处理视频失败: {e}")
                        continue
                
                # Get comments for all videos
                video_ids = [video_item.get("bvid") for video_item in all_video_list if video_item.get("bvid")]
                await self.batch_get_video_comments(video_ids)
            else:
                utils.logger.warning(f"[BilibiliCrawler.get_creators_and_notes] creator_id:{creator_id} not found")

    async def search(self):
        """
        search bilibili video with keywords
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search] Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < bili_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = bili_limit_count
        start_page = config.START_PAGE  # start page number
        
        # 添加资源监控
        start_time = time.time()
        processed_count = 0
        
        # 🆕 修复：完全忽略配置文件中的关键字，使用动态传入的关键字
        # 从实例变量获取关键字，如果没有则使用配置文件中的（向后兼容）
        keywords_to_search = getattr(self, 'dynamic_keywords', None)
        if not keywords_to_search:
            utils.logger.warning("[BilibiliCrawler.search] 未找到动态关键字，使用配置文件中的关键字（向后兼容）")
            keywords_to_search = config.KEYWORDS
        
        # 确保关键字不为空
        if not keywords_to_search or not keywords_to_search.strip():
            utils.logger.error("[BilibiliCrawler.search] 没有有效的关键字，无法进行搜索")
            return
        
        # 处理多个关键字（用逗号分隔）
        keyword_list = [kw.strip() for kw in keywords_to_search.split(",") if kw.strip()]
        
        for keyword in keyword_list:
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search] Current search keyword: {keyword}")
            # 每个关键词最多返回 1000 条数据
            if not config.ALL_DAY:
                page = 1
                while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                    if page < start_page:
                        utils.logger.info(f"[BilibiliCrawler.search] Skip page: {page}")
                        page += 1
                        continue

                    try:
                        utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, page: {page}")
                        video_id_list: List[str] = []
                        videos_res = await self.bili_client.search_video_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=bili_limit_count,
                            order=SearchOrderType.DEFAULT,
                            pubtime_begin_s=0,  # 作品发布日期起始时间戳
                            pubtime_end_s=0  # 作品发布日期结束日期时间戳
                        )
                        video_list: List[Dict] = videos_res.get("result")

                        # 限制并发数量，避免资源耗尽
                        max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(video_list))
                        semaphore = asyncio.Semaphore(max_concurrent)
                        
                        # 分批处理视频详情
                        batch_size = 5  # 每批处理5个视频
                        video_items = []
                        
                        for i in range(0, len(video_list), batch_size):
                            batch_videos = video_list[i:i + batch_size]
                            utils.logger.info(f"[BilibiliCrawler.search] Processing video batch {i//batch_size + 1}, items: {len(batch_videos)}")
                            
                            task_list = []
                            try:
                                task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in batch_videos]
                            except Exception as e:
                                utils.logger.warning(f"[BilibiliCrawler.search] error in the task list. The video for this page will not be included. {e}")
                                continue
                            
                            try:
                                # 添加超时控制
                                batch_results = await asyncio.wait_for(
                                    asyncio.gather(*task_list, return_exceptions=True),
                                    timeout=60  # 60秒超时
                                )
                                video_items.extend([r for r in batch_results if not isinstance(r, Exception)])
                            except asyncio.TimeoutError:
                                utils.logger.warning(f"[BilibiliCrawler.search] Video batch timeout, skipping remaining items")
                                break
                            except Exception as e:
                                utils.logger.error(f"[BilibiliCrawler.search] Video batch processing error: {e}")
                                continue
                            
                            # 添加间隔，避免请求过于频繁
                            await asyncio.sleep(1)
                        
                        # 处理视频详情
                        for video_item in video_items:
                            if video_item:
                                try:
                                    import json
                                    utils.logger.info(f"[BilibiliCrawler] 原始视频数据: {json.dumps(video_item, ensure_ascii=False)}")
                                    
                                    # 获取视频播放地址
                                    video_info = video_item.get("View", {})
                                    aid = video_info.get("aid")
                                    cid = video_info.get("cid")
                                    
                                    if aid and cid:
                                        # 获取播放地址
                                        utils.logger.info(f"[BilibiliCrawler] 开始获取播放地址 - aid: {aid}, cid: {cid}")
                                        play_url_result = await self.get_video_play_url_task(aid, cid, semaphore)
                                        if play_url_result:
                                            # 将播放地址数据合并到视频信息中
                                            video_item.update(play_url_result)
                                            utils.logger.info(f"[BilibiliCrawler] 获取到播放地址数据: {json.dumps(play_url_result, ensure_ascii=False)}")
                                        else:
                                            utils.logger.warning(f"[BilibiliCrawler] 获取播放地址失败 - aid: {aid}, cid: {cid}")
                                    else:
                                        utils.logger.warning(f"[BilibiliCrawler] 缺少aid或cid - aid: {aid}, cid: {cid}")
                                    
                                    video_id_list.append(aid)
                                    await self.bilibili_store.update_bilibili_video(video_item, task_id=self.task_id)
                                    await self.bilibili_store.update_up_info(video_item)
                                    await self.get_bilibili_video(video_item, semaphore)
                                    processed_count += 1
                                except Exception as e:
                                    utils.logger.error(f"[BilibiliCrawler.search] Failed to process video: {e}")
                                    continue
                        
                        # 检查处理时间，避免长时间运行
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 300:  # 5分钟超时
                            utils.logger.warning(f"[BilibiliCrawler.search] Processing time exceeded 5 minutes, stopping")
                            break
                        
                        # 获取评论（如果启用）
                        if config.ENABLE_GET_COMMENTS and video_id_list:
                            try:
                                await self.batch_get_video_comments(video_id_list)
                            except Exception as e:
                                utils.logger.error(f"[BilibiliCrawler.search] Failed to get comments: {e}")
                        
                        page += 1
                        
                    except Exception as e:
                        utils.logger.error(f"[BilibiliCrawler.search] Unexpected error during search: {e}")
                        page += 1
                        continue
                        
            # 按照 START_DAY 至 END_DAY 按照每一天进行筛选，这样能够突破 1000 条视频的限制，最大程度爬取该关键词下每一天的所有视频
            else:
                for day in pd.date_range(start=config.START_DAY, end=config.END_DAY, freq='D'):
                    # 按照每一天进行爬取的时间戳参数
                    pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(start=day.strftime('%Y-%m-%d'), end=day.strftime('%Y-%m-%d'))
                    page = 1
                    #!该段 while 语句在发生异常时（通常情况下为当天数据为空时）会自动跳转到下一天，以实现最大程度爬取该关键词下当天的所有视频
                    #!除了仅保留现在原有的 try, except Exception 语句外，不要再添加其他的异常处理！！！否则将使该段代码失效，使其仅能爬取当天一天数据而无法跳转到下一天
                    #!除非将该段代码的逻辑进行重构以实现相同的功能，否则不要进行修改！！！
                    while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                        #! Catch any error if response return nothing, go to next day
                        try:
                            #! Don't skip any page, to make sure gather all video in one day
                            # if page < start_page:
                            #     utils.logger.info(f"[BilibiliCrawler.search] Skip page: {page}")
                            #     page += 1
                            #     continue

                            utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, date: {day.ctime()}, page: {page}")
                            video_id_list: List[str] = []
                            videos_res = await self.bili_client.search_video_by_keyword(
                                keyword=keyword,
                                page=page,
                                page_size=bili_limit_count,
                                order=SearchOrderType.DEFAULT,
                                pubtime_begin_s=pubtime_begin_s,  # 作品发布日期起始时间戳
                                pubtime_end_s=pubtime_end_s  # 作品发布日期结束日期时间戳
                            )
                            video_list: List[Dict] = videos_res.get("result")

                            # 限制并发数量
                            max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(video_list))
                            semaphore = asyncio.Semaphore(max_concurrent)
                            
                            # 分批处理视频详情
                            batch_size = 5
                            video_items = []
                            
                            for i in range(0, len(video_list), batch_size):
                                batch_videos = video_list[i:i + batch_size]
                                task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in batch_videos]
                                
                                try:
                                    batch_results = await asyncio.wait_for(
                                        asyncio.gather(*task_list, return_exceptions=True),
                                        timeout=60
                                    )
                                    video_items.extend([r for r in batch_results if not isinstance(r, Exception)])
                                except asyncio.TimeoutError:
                                    utils.logger.warning(f"[BilibiliCrawler.search] Video batch timeout")
                                    break
                                except Exception as e:
                                    utils.logger.error(f"[BilibiliCrawler.search] Video batch error: {e}")
                                    continue
                                
                                await asyncio.sleep(1)
                            
                            for video_item in video_items:
                                if video_item:
                                    try:
                                        import json
                                        utils.logger.info(f"[BilibiliCrawler] 原始视频数据: {json.dumps(video_item, ensure_ascii=False)}")
                                        
                                        # 获取视频播放地址
                                        video_info = video_item.get("View", {})
                                        aid = video_info.get("aid")
                                        cid = video_info.get("cid")
                                        
                                        if aid and cid:
                                            # 获取播放地址
                                            utils.logger.info(f"[BilibiliCrawler] 开始获取播放地址 - aid: {aid}, cid: {cid}")
                                            play_url_result = await self.get_video_play_url_task(aid, cid, semaphore)
                                            if play_url_result:
                                                # 将播放地址数据合并到视频信息中
                                                video_item.update(play_url_result)
                                                utils.logger.info(f"[BilibiliCrawler] 获取到播放地址数据: {json.dumps(play_url_result, ensure_ascii=False)}")
                                        else:
                                            utils.logger.warning(f"[BilibiliCrawler] 缺少aid或cid - aid: {aid}, cid: {cid}")
                                        
                                        video_id_list.append(aid)
                                        await self.bilibili_store.update_bilibili_video(video_item, task_id=self.task_id)
                                        await self.bilibili_store.update_up_info(video_item)
                                        await self.get_bilibili_video(video_item, semaphore)
                                        processed_count += 1
                                    except Exception as e:
                                        utils.logger.error(f"[BilibiliCrawler.search] Failed to process video: {e}")
                                        continue
                            
                            page += 1
                            await self.batch_get_video_comments(video_id_list)
                        # go to next day
                        except Exception as e:
                            print(e)
                            break
            
            utils.logger.info(f"[BilibiliCrawler.search] Search completed. Total processed: {processed_count}")

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[BilibiliCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(
            f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        
        # 限制并发数量
        max_concurrent = min(config.MAX_CONCURRENCY_NUM, len(video_id_list))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 分批处理评论
        batch_size = 3  # 每批处理3个评论任务
        total_processed = 0
        
        for i in range(0, len(video_id_list), batch_size):
            batch_videos = video_id_list[i:i + batch_size]
            
            utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] Processing comment batch {i//batch_size + 1}, videos: {len(batch_videos)}")
            
            task_list: List[Task] = []
            for video_id in batch_videos:
                task = asyncio.create_task(self.get_comments(
                    video_id, semaphore), name=video_id)
                task_list.append(task)
            
            try:
                # 添加超时控制
                await asyncio.wait_for(
                    asyncio.gather(*task_list, return_exceptions=True),
                    timeout=120  # 2分钟超时
                )
                total_processed += len(batch_videos)
                utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] Completed batch {i//batch_size + 1}")
            except asyncio.TimeoutError:
                utils.logger.warning(f"[BilibiliCrawler.batch_get_video_comments] Comment batch timeout")
                break
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.batch_get_video_comments] Comment batch error: {e}")
                continue
            
            # 添加间隔，避免请求过于频繁
            await asyncio.sleep(2)
        
        utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] Comment processing completed. Total processed: {total_processed}")

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
                    f"[BilibiliCrawler.get_comments] begin get video_id: {video_id} comments ...")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=random.random(),
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=self.bilibili_store.batch_update_bilibili_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_comments] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_comments] may be been blocked, err:{e}")

    async def get_creator_videos(self, creator_id: int, max_count: int = None):
        """
        get videos for a creator
        :param creator_id: 创作者ID
        :param max_count: 最大获取数量，None表示获取所有
        :return: List[Dict] 创作者视频列表
        """
        ps = 30
        pn = 1
        max_pages = 10  # 最大获取10页，避免无限循环
        video_bvids_list = []
        all_video_list = []
        
        try:
            while True:
                result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 获取创作者 {creator_id} 第 {pn} 页视频列表")
                
                # 添加调试日志，查看API返回的数据结构
                import json
                utils.logger.debug(f"[BilibiliCrawler.get_creator_videos] API返回数据结构: {json.dumps(result, ensure_ascii=False)[:500]}...")
                
                if not result:
                    utils.logger.warning(f"[BilibiliCrawler.get_creator_videos] 获取创作者视频列表失败: 结果为空")
                    break
                
                if "list" not in result:
                    utils.logger.warning(f"[BilibiliCrawler.get_creator_videos] 获取创作者视频列表失败: 缺少list字段, {result}")
                    break
                
                if "vlist" not in result["list"]:
                    utils.logger.warning(f"[BilibiliCrawler.get_creator_videos] 获取创作者视频列表失败: 缺少vlist字段, {result['list']}")
                    break
                
                video_list = result["list"]["vlist"]
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 第 {pn} 页获取到 {len(video_list)} 个视频")
                
                for video in video_list:
                    # 检查是否达到最大数量限制
                    if max_count is not None and len(all_video_list) >= max_count:
                        utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 已达到最大数量限制 {max_count}，停止获取")
                        break
                    
                    bvid = video.get("bvid", "")
                    if bvid:
                        video_bvids_list.append(bvid)
                    # 构建基础视频信息 - 使用安全的字段访问
                    video_info = {
                        "bvid": video.get("bvid", ""),
                        "aid": video.get("aid", 0),
                        "title": video.get("title", ""),
                        "desc": video.get("description", ""),
                        "duration": video.get("duration", 0),
                        "pic": video.get("pic", ""),
                        "owner": {
                            "mid": video.get("owner", {}).get("mid", 0),
                            "name": video.get("owner", {}).get("name", ""),
                            "face": video.get("owner", {}).get("face", "")
                        },
                        "stat": {
                            "view": video.get("stat", {}).get("view", 0),
                            "danmaku": video.get("stat", {}).get("danmaku", 0),
                            "reply": video.get("stat", {}).get("reply", 0),
                            "favorite": video.get("stat", {}).get("favorite", 0),
                            "coin": video.get("stat", {}).get("coin", 0),
                            "share": video.get("stat", {}).get("share", 0),
                            "like": video.get("stat", {}).get("like", 0)
                        },
                        "pubdate": video.get("pubdate", 0),
                        "ctime": video.get("ctime", 0)
                    }
                    all_video_list.append(video_info)
                
                # 如果已达到最大数量限制，跳出分页循环
                if max_count is not None and len(all_video_list) >= max_count:
                    break
                
                # 检查是否还有更多页
                page_info = result.get("page", {})
                total_count = page_info.get("count", 0)
                current_count = pn * ps
                
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 总视频数: {total_count}, 当前已获取: {current_count}")
                
                if total_count <= current_count:
                    utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 已获取所有视频，停止分页")
                    break
                
                if pn >= max_pages:
                    utils.logger.warning(f"[BilibiliCrawler.get_creator_videos] 已达到最大页数限制 {max_pages}，停止获取")
                    break
                
                await asyncio.sleep(random.random())
                pn += 1
            
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos] 获取到 {len(all_video_list)} 个视频")
            return all_video_list
            
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.get_creator_videos] 获取创作者视频失败: {e}")
            import traceback
            utils.logger.error(f"[BilibiliCrawler.get_creator_videos] 错误堆栈: {traceback.format_exc()}")
            return []

    async def get_creator_videos_by_keywords(self, creator_id: int, keywords: str, max_count: int = None):
        """
        使用关键词搜索获取创作者的视频
        :param creator_id: 创作者ID
        :param keywords: 搜索关键词
        :param max_count: 最大获取数量，None表示获取所有
        :return: List[Dict] 匹配关键词的视频列表
        """
        try:
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 开始关键词搜索")
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 创作者ID: {creator_id}")
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 搜索关键词: '{keywords}'")
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 最大数量限制: {max_count}")
            
            # 使用B站创作者主页专用搜索API
            search_result = await self.bili_client.search_creator_videos(creator_id, keywords)
            
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 搜索API返回结果: {search_result}")
            
            # 检查返回的数据结构 - 根据真实API返回的数据结构
            if not search_result or "list" not in search_result:
                utils.logger.warning(f"[BilibiliCrawler.get_creator_videos_by_keywords] 搜索失败或无结果")
                return []
            
            # 检查返回的数据结构
            if "vlist" not in search_result["list"]:
                utils.logger.warning(f"[BilibiliCrawler.get_creator_videos_by_keywords] 搜索返回数据结构异常: {search_result}")
                return []
            
            video_list = search_result["list"]["vlist"]
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 搜索到 {len(video_list)} 个匹配的视频")
            
            # 构建标准化的视频信息
            all_video_list = []
            for video in video_list:
                # 构建基础视频信息 - 使用安全的字段访问
                # 保留原始字段，确保后续处理能正常工作
                video_info = {
                    # 核心字段 - 用于后续获取详细信息
                    "bvid": video.get("bvid", ""),
                    "aid": video.get("aid", 0),
                    "title": video.get("title", ""),
                    "description": video.get("description", ""),  # 真实API中是"description"
                    "content": video.get("description", ""),  # 内容使用描述
                    "content_type": "video",  # 固定值
                    "content_id": video.get("bvid", ""),  # 使用bvid作为content_id
                    "author_id": video.get("mid", 0),  # 真实API中是"mid"
                    "author_name": video.get("author", ""),  # 真实API中是"author"
                    "author_nickname": video.get("author", ""),  # 真实API中是"author"
                    "author_avatar": "",  # 真实API中没有直接的avatar字段
                    "author_signature": "",  # 真实API中没有signature字段
                    "author_unique_id": "",  # 真实API中没有unique_id字段
                    "author_sec_uid": "",  # 真实API中没有sec_uid字段
                    "author_short_id": "",  # 真实API中没有short_id字段
                    "like_count": 0,  # 真实API中没有like字段
                    "comment_count": video.get("comment", 0),  # 真实API中是"comment"
                    "share_count": 0,  # 真实API中没有share字段
                    "collect_count": 0,  # 真实API中没有collect字段
                    "view_count": video.get("play", 0),  # 真实API中是"play"
                    "cover_url": video.get("pic", ""),  # 真实API中是"pic"
                    "video_url": f"https://www.bilibili.com/video/{video.get('bvid', '')}",  # 构建播放页链接
                    "video_play_url": f"https://www.bilibili.com/video/{video.get('bvid', '')}",  # 播放页链接
                    "video_download_url": "",  # 需要单独获取
                    "video_share_url": f"https://www.bilibili.com/video/{video.get('bvid', '')}",  # 分享链接
                    "image_urls": [],  # 真实API中没有image_urls字段
                    "audio_url": "",  # 真实API中没有audio_url字段
                    "file_urls": [],  # 真实API中没有file_urls字段
                    "ip_location": "",  # 真实API中没有ip_location字段
                    "location": "",  # 真实API中没有location字段
                    "tags": "",  # 真实API中没有tags字段
                    "categories": "",  # 真实API中没有categories字段
                    "topics": "",  # 真实API中没有topics字段
                    "is_favorite": False,  # 真实API中没有is_favorite字段
                    "is_deleted": False,  # 真实API中没有is_deleted字段
                    "is_private": False,  # 真实API中没有is_private字段
                    "is_original": True,  # 假设为原创
                    "minio_url": "",  # 需要后续处理
                    "local_path": "",  # 需要后续处理
                    "file_size": 0,  # 真实API中没有file_size字段
                    "storage_type": "",  # 真实API中没有storage_type字段
                    "metadata": json.dumps(video.get("meta", {}), ensure_ascii=False),  # 序列化meta数据
                    "raw_data": json.dumps(video, ensure_ascii=False),  # 原始数据
                    "extra_info": json.dumps({
                        "typeid": video.get("typeid", 0),
                        "copyright": video.get("copyright", "1"),
                        "review": video.get("review", 0),
                        "hide_click": video.get("hide_click", False),
                        "is_pay": video.get("is_pay", 0),
                        "is_union_video": video.get("is_union_video", 0),
                        "is_steins_gate": video.get("is_steins_gate", 0),
                        "is_live_playback": video.get("is_live_playback", 0),
                        "is_lesson_video": video.get("is_lesson_video", 0),
                        "is_lesson_finished": video.get("is_lesson_finished", 0),
                        "is_charging_arc": video.get("is_charging_arc", False),
                        "elec_arc_type": video.get("elec_arc_type", 0),
                        "elec_arc_badge": video.get("elec_arc_badge", ""),
                        "season_id": video.get("season_id", 0),
                        "attribute": video.get("attribute", 0),
                        "subtitle": video.get("subtitle", ""),
                        "jump_url": video.get("jump_url", ""),
                        "length": video.get("length", ""),
                        "video_review": video.get("video_review", 0)
                    }, ensure_ascii=False),
                    "create_time": video.get("created", 0),  # 真实API中是"created"
                    "publish_time": video.get("created", 0),  # 真实API中是"created"
                    "update_time": video.get("created", 0),  # 真实API中是"created"
                    "add_ts": int(time.time()),  # 当前时间戳
                    "last_modify_ts": int(time.time()),  # 当前时间戳
                    "source_keyword": keywords if keywords else "",  # 搜索关键词
                    # 保留原始字段用于兼容性
                    "stat": {
                        "view": video.get("play", 0),
                        "danmaku": video.get("video_review", 0),
                        "reply": video.get("comment", 0),
                        "favorite": 0,
                        "coin": 0,
                        "share": 0,
                        "like": 0
                    },
                    "pubdate": video.get("created", 0),
                    "ctime": video.get("created", 0),
                    # 添加原始数据，确保后续处理能获取到完整信息
                    "original_data": video
                }
                all_video_list.append(video_info)
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 匹配视频: {video_info.get('title', '无标题')}")
            
            # 应用数量限制
            if max_count is not None and len(all_video_list) > max_count:
                all_video_list = all_video_list[:max_count]
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 应用数量限制，保留前 {len(all_video_list)} 个视频")
            
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos_by_keywords] 最终返回 {len(all_video_list)} 个视频")
            return all_video_list
            
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.get_creator_videos_by_keywords] 关键词搜索失败: {e}")
            import traceback
            utils.logger.error(f"[BilibiliCrawler.get_creator_videos_by_keywords] 错误堆栈: {traceback.format_exc()}")
            return []

    async def get_specified_videos(self, bvids_list: List[str]):
        """
        get specified videos info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore) for video_id in
            bvids_list
        ]
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail is not None:
                import json
                utils.logger.info(f"[BilibiliCrawler] 原始视频数据: {json.dumps(video_detail, ensure_ascii=False)}")
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = video_item_view.get("aid")
                video_cid: str = video_item_view.get("cid")
                
                if video_aid and video_cid:
                    # 获取播放地址
                    play_url_result = await self.get_video_play_url_task(video_aid, video_cid, semaphore)
                    if play_url_result:
                        # 将播放地址数据合并到视频信息中
                        video_detail.update(play_url_result)
                        utils.logger.info(f"[BilibiliCrawler] 获取到播放地址数据: {json.dumps(play_url_result, ensure_ascii=False)}")
                
                if video_aid:
                    video_aids_list.append(video_aid)
                await self.bilibili_store.update_bilibili_video(video_detail, task_id=self.task_id)
                await self.bilibili_store.update_up_info(video_detail)
                await self.get_bilibili_video(video_detail, semaphore)
        await self.batch_get_video_comments(video_aids_list)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)
                return result
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None

    async def get_video_play_url_task(self, aid: int, cid: int, semaphore: asyncio.Semaphore) -> Union[Dict, None]:
        """
                Get video play url
                :param aid:
                :param cid:
                :param semaphore:
                :return:
                """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_play_url(aid=aid, cid=cid)
                return result
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_play_url_task] Get video play url error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_play_url_task] have not fund play url from :{aid}|{cid}, err: {ex}")
                return None

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """
        create bilibili client
        :param httpx_proxy: httpx proxy
        :return: bilibili client
        """
        utils.logger.info(
            "[BilibiliCrawler.create_bilibili_client] Begin create bilibili API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        bilibili_client_obj = BilibiliClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return bilibili_client_obj

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        format proxy info for playwright and httpx
        :param ip_proxy_info: ip proxy info
        :return: playwright proxy, httpx proxy
        """
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
        """ 
        launch browser and create browser context
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        utils.logger.info(
            "[BilibiliCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
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
            # type: ignore
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def get_bilibili_video(self, video_item: Dict, semaphore: asyncio.Semaphore):
        """
        download bilibili video
        :param video_item:
        :param semaphore:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Crawling image mode is not enabled")
            return
        video_item_view: Dict = video_item.get("View")
        aid = video_item_view.get("aid")
        cid = video_item_view.get("cid")
        result = await self.get_video_play_url_task(aid, cid, semaphore)
        if result is None:
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video play url failed")
            return
        durl_list = result.get("durl")
        max_size = -1
        video_url = ""
        for durl in durl_list:
            size = durl.get("size")
            if size > max_size:
                max_size = size
                video_url = durl.get("url")
        if video_url == "":
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video url failed")
            return

        content = await self.bili_client.get_video_media(video_url)
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await self.bilibili_store.store_video(aid, content, extension_file_name)

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
            keywords: 关键词（可选，用于筛选创作者内容）
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
            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 开始爬取 {len(creators)} 个创作者")
            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 最大数量限制: {max_count}")
            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 关键词: '{keywords}'")
            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 创作者列表: {[c.get('name', c.get('nickname', '未知')) for c in creators]}")
            
            # 确保客户端已初始化
            if not hasattr(self, 'bili_client') or self.bili_client is None:
                utils.logger.error("[BilibiliCrawler.get_creators_and_notes_from_db] bili_client 未初始化")
                raise Exception("B站客户端未初始化，请先调用start()方法")
            
            all_results = []
            
            for creator in creators:
                user_id = creator.get("creator_id")
                creator_name = creator.get("name") or creator.get("nickname") or "未知创作者"
                
                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 开始爬取创作者: {creator_name} (ID: {user_id})")
                
                try:
                    # 获取创作者详细信息
                    creator_info: Dict = await self.bili_client.get_creator_info(int(user_id))
                    if creator_info:
                        # 更新创作者信息到数据库
                        await self.bilibili_store.store_creator(creator_info)
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 创作者信息已更新: {creator_name}")
                        
                        # 更新任务的creator_ref_ids字段
                        try:
                            from api.crawler_core import update_task_creator_ref_ids
                            await update_task_creator_ref_ids(self.task_id, [str(user_id)])
                            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 任务creator_ref_ids已更新: {user_id}")
                        except Exception as e:
                            utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 更新任务creator_ref_ids失败: {e}")
                    
                    # 根据是否有关键词选择不同的获取方式
                    if keywords and keywords.strip():
                        # 使用关键词搜索获取视频
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 使用关键词 '{keywords}' 搜索创作者 {creator_name} 的视频")
                        all_video_list = await self.get_creator_videos_by_keywords(int(user_id), keywords, max_count)
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 关键词搜索完成，获取到 {len(all_video_list) if all_video_list else 0} 个视频")
                    else:
                        # 获取创作者的所有视频（应用数量限制）
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取创作者 {creator_name} 的所有视频（无关键词筛选）")
                        all_video_list = await self.get_creator_videos(int(user_id), max_count)
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取所有视频完成，获取到 {len(all_video_list) if all_video_list else 0} 个视频")
                    
                    if all_video_list:
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取到 {len(all_video_list)} 个视频")
                        
                        # 处理每个视频，获取详细信息
                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 开始处理 {len(all_video_list)} 个视频")
                        
                        for i, video_item in enumerate(all_video_list):
                            try:
                                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 处理第 {i+1} 个视频: {video_item.get('title', '无标题')}")
                                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频信息: aid={video_item.get('aid')}, bvid={video_item.get('bvid')}")
                                
                                # 获取视频详细信息
                                video_detail = await self.get_video_info_task(
                                    aid=video_item.get("aid", 0), 
                                    bvid=video_item.get("bvid", ""), 
                                    semaphore=asyncio.Semaphore(5)
                                )
                                
                                if video_detail:
                                    utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 成功获取视频详细信息")
                                    
                                    # 获取播放地址
                                    video_aid = video_detail.get("View", {}).get("aid")
                                    video_cid = video_detail.get("View", {}).get("cid")
                                    
                                    if video_aid and video_cid:
                                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取播放地址: aid={video_aid}, cid={video_cid}")
                                        play_url_result = await self.get_video_play_url_task(
                                            video_aid, video_cid, asyncio.Semaphore(5)
                                        )
                                        if play_url_result:
                                            video_detail.update(play_url_result)
                                            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 成功获取播放地址")
                                        else:
                                            utils.logger.warning(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取播放地址失败")
                                    else:
                                        utils.logger.warning(f"[BilibiliCrawler.get_creators_and_notes_from_db] 缺少aid或cid: aid={video_aid}, cid={video_cid}")
                                    
                                    # 保存到数据库
                                    utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 开始保存到数据库")
                                    try:
                                        await self.bilibili_store.update_bilibili_video(video_detail, task_id=self.task_id)
                                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频数据保存成功")
                                    except Exception as e:
                                        utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频数据保存失败: {e}")
                                    
                                    try:
                                        await self.bilibili_store.update_up_info(video_detail)
                                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] UP主信息更新成功")
                                    except Exception as e:
                                        utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] UP主信息更新失败: {e}")
                                    
                                    try:
                                        await self.get_bilibili_video(video_detail, asyncio.Semaphore(5))
                                        utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频下载处理成功")
                                    except Exception as e:
                                        utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频下载处理失败: {e}")
                                    
                                    # 添加到结果列表
                                    all_results.append(video_detail)
                                    utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 视频处理完成，已添加到结果列表")
                                else:
                                    utils.logger.warning(f"[BilibiliCrawler.get_creators_and_notes_from_db] 获取视频详细信息失败")
                                
                            except Exception as e:
                                utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 处理视频失败: {e}")
                                import traceback
                                utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 错误堆栈: {traceback.format_exc()}")
                                continue
                        
                        # 获取评论
                        if get_comments:
                            video_ids = [video_item.get("bvid") for video_item in all_results if video_item.get("bvid")]
                            if video_ids:
                                utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 为 {len(video_ids)} 个视频获取评论")
                                await self.batch_get_video_comments(video_ids)
                    else:
                        utils.logger.warning(f"[BilibiliCrawler.get_creators_and_notes_from_db] 创作者 {creator_name} 没有获取到视频")
                
                except Exception as e:
                    utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 爬取创作者 {creator_name} 失败: {e}")
                    continue
            
            utils.logger.info(f"[BilibiliCrawler.get_creators_and_notes_from_db] 爬取完成，共获取 {len(all_results)} 条数据 (限制: {max_count})")
            return all_results
            
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.get_creators_and_notes_from_db] 爬取失败: {e}")
            raise

    async def get_all_creator_details(self, creator_id_list: List[int]):
        """
        creator_id_list: get details for creator from creator_id_list
        """
        utils.logger.info(
            f"[BilibiliCrawler.get_creator_details] Crawling the detalis of creator")
        utils.logger.info(
            f"[BilibiliCrawler.get_creator_details] creator ids:{creator_id_list}")

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        try:
            for creator_id in creator_id_list:
                task = asyncio.create_task(self.get_creator_details(
                    creator_id, semaphore), name=creator_id)
                task_list.append(task)
        except Exception as e:
            utils.logger.warning(
                f"[BilibiliCrawler.get_all_creator_details] error in the task list. The creator will not be included. {e}")

        await asyncio.gather(*task_list)

    async def get_creator_details(self, creator_id: int, semaphore: asyncio.Semaphore):
        """
        get details for creator id
        :param creator_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
            creator_info: Dict = {
                "id": creator_id,
                "name": creator_unhandled_info.get("name"),
                "sign": creator_unhandled_info.get("sign"),
                "avatar": creator_unhandled_info.get("face"),
            }
        await self.get_fans(creator_info, semaphore)
        await self.get_followings(creator_info, semaphore)
        await self.get_dynamics(creator_info, semaphore)

    async def get_fans(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get fans for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_fans] begin get creator_id: {creator_id} fans ...")
                await self.bili_client.get_creator_all_fans(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=self.bilibili_store.batch_update_bilibili_creator_fans,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_fans] get creator_id: {creator_id} fans error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_fans] may be been blocked, err:{e}")

    async def get_followings(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get followings for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_followings] begin get creator_id: {creator_id} followings ...")
                await self.bili_client.get_creator_all_followings(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=self.bilibili_store.batch_update_bilibili_creator_followings,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_followings] get creator_id: {creator_id} followings error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_followings] may be been blocked, err:{e}")

    async def get_dynamics(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get dynamics for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_dynamics] begin get creator_id: {creator_id} dynamics ...")
                await self.bili_client.get_creator_all_dynamics(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=self.bilibili_store.batch_update_bilibili_creator_dynamics,
                    max_count=config.CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_dynamics] get creator_id: {creator_id} dynamics error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_dynamics] may be been blocked, err:{e}")

    async def search_by_keywords(self, keywords: str, max_count: int = 50, 
                                account_id: str = None, session_id: str = None,
                                login_type: str = "qrcode", get_comments: bool = False,
                                save_data_option: str = "db", use_proxy: bool = False,
                                proxy_strategy: str = "disabled") -> List[Dict]:
        """
        根据关键词搜索B站视频
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
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords] 开始搜索关键词: {keywords}")
            
            # 🆕 设置account_id到实例变量，供start方法使用
            self.account_id = account_id
            if account_id:
                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] 使用指定账号ID: {account_id}")
            
            # 设置配置
            import config
            # 🆕 修复：使用动态关键字，完全忽略配置文件中的关键字
            if keywords and keywords.strip():
                # 将动态关键字设置到实例变量，而不是全局配置
                self.dynamic_keywords = keywords
                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] 设置动态关键字: '{keywords}'")
            else:
                utils.logger.warning("[BilibiliCrawler.search_by_keywords] 关键字为空，将使用默认搜索")
            
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 执行实际的搜索
            await self.search()
            
            # 从统一存储中获取结果
            results = []
            if hasattr(self, 'bilibili_store') and hasattr(self.bilibili_store, 'unified_store'):
                results = await self.bilibili_store.unified_store.get_all_content()
            
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords] 搜索完成，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.search_by_keywords] 搜索失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[BilibiliCrawler.search_by_keywords] 关闭浏览器时出现警告: {e}")

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
            utils.logger.info(f"[BilibiliCrawler.get_user_notes] 开始获取用户视频: {user_id}")
            
            # 设置配置
            import config
            # 🆕 修复：使用动态用户ID，而不是修改全局配置
            self.dynamic_video_ids = [user_id]
            utils.logger.info(f"[BilibiliCrawler.get_user_notes] 设置动态用户ID: {user_id}")
            
            config.CRAWLER_MAX_NOTES_COUNT = max_count
            config.ENABLE_GET_COMMENTS = get_comments
            config.SAVE_DATA_OPTION = save_data_option
            config.ENABLE_IP_PROXY = use_proxy
            
            # 启动爬虫
            await self.start()
            
            # 获取存储的数据
            results = []
            if hasattr(self, 'bilibili_store') and hasattr(self.bilibili_store, 'get_all_content'):
                results = await self.bilibili_store.get_all_content()
            
            utils.logger.info(f"[BilibiliCrawler.get_user_notes] 获取完成，共 {len(results)} 条数据")
            return results
            
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.get_user_notes] 获取失败: {e}")
            raise
        finally:
            # 安全关闭浏览器，避免重复关闭
            try:
                if hasattr(self, 'browser_context') and self.browser_context:
                    await self.close()
            except Exception as e:
                utils.logger.warning(f"[BilibiliCrawler.get_user_notes] 关闭浏览器时出现警告: {e}")

    async def close(self):
        """
        安全关闭浏览器和相关资源
        """
        try:
            if hasattr(self, 'browser_context') and self.browser_context:
                await self.browser_context.close()
                utils.logger.info("[BilibiliCrawler] 浏览器上下文已关闭")
            
            if hasattr(self, 'context_page') and self.context_page:
                await self.context_page.close()
                utils.logger.info("[BilibiliCrawler] 页面已关闭")
            
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                utils.logger.info("[BilibiliCrawler] Playwright实例已关闭")
                
        except Exception as e:
            utils.logger.warning(f"[BilibiliCrawler.close] 关闭资源时出现警告: {e}")
