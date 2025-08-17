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
import copy
import json
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

import requests
from playwright.async_api import BrowserContext

from base.base_crawler import AbstractApiClient
from tools import utils
from var import request_keyword_var

from .exception import *
from .field import *
from .help import *
from constant.douyin import (
    DOUYIN_AID, DOUYIN_DEVICE_PLATFORM, DOUYIN_CHANNEL, 
    DOUYIN_VERSION_CODE, DOUYIN_VERSION_NAME, DOUYIN_UPDATE_VERSION_CODE,
    DOUYIN_PC_CLIENT_TYPE, DOUYIN_COOKIE_ENABLED, DOUYIN_BROWSER_LANGUAGE,
    DOUYIN_BROWSER_PLATFORM, DOUYIN_BROWSER_NAME, DOUYIN_BROWSER_VERSION,
    DOUYIN_BROWSER_ONLINE, DOUYIN_ENGINE_NAME, DOUYIN_OS_NAME, DOUYIN_OS_VERSION,
    DOUYIN_CPU_CORE_NUM, DOUYIN_DEVICE_MEMORY, DOUYIN_ENGINE_VERSION,
    DOUYIN_PLATFORM, DOUYIN_SCREEN_WIDTH, DOUYIN_SCREEN_HEIGHT,
    DOUYIN_EFFECTIVE_TYPE, DOUYIN_ROUND_TRIP_TIME
)


class DOUYINClient(AbstractApiClient):
    def __init__(
            self,
            timeout=30,
            proxies=None,
            *,
            headers: Dict,
            playwright_page: Optional[Page],
            cookie_dict: Dict
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.douyin.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def __process_req_params(
            self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None,
            request_method="GET"
    ):

        if not params:
            return
        headers = headers or self.headers
        
        # 🆕 检查页面是否已关闭
        if not self.playwright_page or self.playwright_page.is_closed():
            utils.logger.warning("⚠️ [DOUYINClient] 页面已关闭，跳过localStorage获取")
            local_storage: Dict = {}
        else:
            try:
                local_storage: Dict = await self.playwright_page.evaluate("() => window.localStorage")  # type: ignore
            except Exception as e:
                utils.logger.warning(f"⚠️ [DOUYINClient] 获取localStorage失败: {e}")
                local_storage: Dict = {}
        common_params = {
            "device_platform": DOUYIN_DEVICE_PLATFORM,
            "aid": str(DOUYIN_AID),
            "channel": DOUYIN_CHANNEL,
            "version_code": DOUYIN_VERSION_CODE,
            "version_name": DOUYIN_VERSION_NAME,
            "update_version_code": DOUYIN_UPDATE_VERSION_CODE,
            "pc_client_type": DOUYIN_PC_CLIENT_TYPE,
            "cookie_enabled": DOUYIN_COOKIE_ENABLED,
            "browser_language": DOUYIN_BROWSER_LANGUAGE,
            "browser_platform": DOUYIN_BROWSER_PLATFORM,
            "browser_name": DOUYIN_BROWSER_NAME,
            "browser_version": DOUYIN_BROWSER_VERSION,
            "browser_online": DOUYIN_BROWSER_ONLINE,
            "engine_name": DOUYIN_ENGINE_NAME,
            "os_name": DOUYIN_OS_NAME,
            "os_version": DOUYIN_OS_VERSION,
            "cpu_core_num": DOUYIN_CPU_CORE_NUM,
            "device_memory": DOUYIN_DEVICE_MEMORY,
            "engine_version": DOUYIN_ENGINE_VERSION,
            "platform": DOUYIN_PLATFORM,
            "screen_width": DOUYIN_SCREEN_WIDTH,
            "screen_height": DOUYIN_SCREEN_HEIGHT,
            'effective_type': DOUYIN_EFFECTIVE_TYPE,
            "round_trip_time": DOUYIN_ROUND_TRIP_TIME,
            "webid": get_web_id(),
            "msToken": local_storage.get("xmst"),
        }
        params.update(common_params)
        query_string = urllib.parse.urlencode(params)

        # 20240927 a-bogus更新（JS版本）
        post_data = {}
        if request_method == "POST":
            post_data = params
        a_bogus = await get_a_bogus(uri, query_string, post_data, headers["User-Agent"], self.playwright_page)
        params["a_bogus"] = a_bogus

    async def request(self, method, url, **kwargs):
        response = None
        if method == "GET":
            response = requests.request(method, url, **kwargs)
        elif method == "POST":
            response = requests.request(method, url, **kwargs)
        try:
            if response.text == "" or response.text == "blocked":
                utils.logger.error(f"request params incrr, response.text: {response.text}")
                raise Exception("account blocked")
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        """
        GET请求
        """
        await self.__process_req_params(uri, params, headers)
        headers = headers or self.headers
        return await self.request(method="GET", url=f"{self._host}{uri}", params=params, headers=headers)

    async def post(self, uri: str, data: dict, headers: Optional[Dict] = None):
        await self.__process_req_params(uri, data, headers)
        headers = headers or self.headers
        return await self.request(method="POST", url=f"{self._host}{uri}", data=data, headers=headers)

    async def pong(self, browser_context: BrowserContext) -> bool:
        """验证cookies是否有效 - 临时放宽验证条件"""
        try:
            # 🆕 临时放宽验证：检查是否有基本的登录相关cookies
            _, cookie_dict = utils.convert_cookies(await browser_context.cookies())
            
            # 检查是否有基本的登录相关cookies
            login_indicators = [
                'sessionid', 'uid_tt', 'sid_tt', 'passport_csrf_token',
                'ttwid', 'bd_ticket_guard_client_data'
            ]
            
            found_indicators = 0
            for indicator in login_indicators:
                if indicator in cookie_dict and cookie_dict[indicator]:
                    found_indicators += 1
            
            utils.logger.info(f"[DOUYINClient] 登录指示器检查: 找到 {found_indicators}/{len(login_indicators)} 个")
            
            # 如果有至少2个登录指示器，就认为cookies有效
            if found_indicators >= 2:
                utils.logger.info(f"[DOUYINClient] ✅ Cookies验证通过，找到 {found_indicators} 个登录指示器")
                return True
            
            # 原有的严格验证（作为备选）
            if not self.playwright_page or self.playwright_page.is_closed():
                utils.logger.warning("[DOUYINClient] ⚠️ 页面已关闭，跳过localStorage验证")
            else:
                try:
                    local_storage = await self.playwright_page.evaluate("() => window.localStorage")
                    if local_storage.get("HasUserLogin", "") == "1":
                        utils.logger.info("[DOUYINClient] ✅ localStorage验证通过")
                        return True
                except Exception as e:
                    utils.logger.warning(f"[DOUYINClient] ⚠️ localStorage验证失败: {e}")

            if cookie_dict.get("LOGIN_STATUS") == "1":
                utils.logger.info("[DOUYINClient] ✅ LOGIN_STATUS验证通过")
                return True
            
            utils.logger.warning(f"[DOUYINClient] ⚠️ Cookies验证失败，但继续执行（临时放宽）")
            return True  # 🆕 临时放宽：即使验证失败也返回True
            
        except Exception as e:
            utils.logger.error(f"[DOUYINClient] Cookies验证异常: {e}")
            utils.logger.warning(f"[DOUYINClient] ⚠️ 验证异常，但继续执行（临时放宽）")
            return True  # 🆕 临时放宽：即使异常也返回True

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def set_cookies_from_string(self, cookie_str: str):
        """从字符串设置cookies"""
        try:
            from tools import utils as crawler_utils
            cookie_dict = crawler_utils.convert_str_cookie_to_dict(cookie_str)
            
            # 🆕 检查页面是否已关闭
            if not self.playwright_page or self.playwright_page.is_closed():
                utils.logger.warning("[DOUYINClient] ⚠️ 页面已关闭，跳过cookies设置")
            else:
                # 设置cookies到浏览器上下文
                for key, value in cookie_dict.items():
                    await self.playwright_page.context.add_cookies([{
                        'name': key,
                        'value': value,
                        'domain': '.douyin.com',
                        'path': '/'
                    }])
            
            # 更新客户端cookies
            self.headers["Cookie"] = cookie_str
            self.cookie_dict = cookie_dict
            
            utils.logger.info(f"[DOUYINClient] 已设置 {len(cookie_dict)} 个cookies")
            
        except Exception as e:
            utils.logger.error(f"[DOUYINClient] 设置cookies失败: {e}")
            raise

    async def clear_cookies(self):
        """清除cookies"""
        try:
            # 🆕 检查页面是否已关闭
            if not self.playwright_page or self.playwright_page.is_closed():
                utils.logger.warning("[DOUYINClient] ⚠️ 页面已关闭，跳过cookies清除")
            else:
                # 清除浏览器上下文中的cookies
                await self.playwright_page.context.clear_cookies()
            
            # 清除客户端cookies
            self.headers["Cookie"] = ""
            self.cookie_dict = {}
            
            utils.logger.info("[DOUYINClient] 已清除所有cookies")
            
        except Exception as e:
            utils.logger.error(f"[DOUYINClient] 清除cookies失败: {e}")
            raise

    async def search_info_by_keyword(
            self,
            keyword: str,
            offset: int = 0,
            search_channel: SearchChannelType = SearchChannelType.GENERAL,
            sort_type: SearchSortType = SearchSortType.GENERAL,
            publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
            search_id: str = ""
    ):
        """
        DouYin Web Search API
        :param keyword:
        :param offset:
        :param search_channel:
        :param sort_type:
        :param publish_time: ·
        :param search_id: ·
        :return:
        """
        query_params = {
            'search_channel': search_channel.value,
            'enable_history': '1',
            'keyword': keyword,
            'search_source': 'tab_search',
            'query_correct_type': '1',
            'is_filter_search': '0',
            'from_group_id': '7378810571505847586',
            'offset': offset,
            'count': '15',
            'need_filter_settings': '1',
            'list_type': 'multi',
            'search_id': search_id,
        }
        if sort_type.value != SearchSortType.GENERAL.value or publish_time.value != PublishTimeType.UNLIMITED.value:
            query_params["filter_selected"] = json.dumps({
                "sort_type": str(sort_type.value),
                "publish_time": str(publish_time.value)
            })
            query_params["is_filter_search"] = 1
            query_params["search_source"] = "tab_search"
        referer_url = f"https://www.douyin.com/search/{keyword}?aid=f594bbd9-a0e2-4651-9319-ebe3cb6298c1&type=general"
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=':/')
        return await self.get("/aweme/v1/web/general/search/single/", query_params, headers=headers)

    async def get_video_by_id(self, aweme_id: str) -> Any:
        """
        DouYin Video Detail API
        :param aweme_id:
        :return:
        """
        params = {
            "aweme_id": aweme_id
        }
        headers = copy.copy(self.headers)
        del headers["Origin"]
        res = await self.get("/aweme/v1/web/aweme/detail/", params, headers)
        return res.get("aweme_detail", {})

    async def get_aweme_comments(self, aweme_id: str, cursor: int = 0):
        """get note comments

        """
        uri = "/aweme/v1/web/comment/list/"
        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": 20,
            "item_type": 0
        }
        keywords = request_keyword_var.get()
        referer_url = "https://www.douyin.com/search/" + keywords + '?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general'
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=':/')
        return await self.get(uri, params)

    async def get_sub_comments(self, comment_id: str, cursor: int = 0):
        """
            获取子评论
        """
        uri = "/aweme/v1/web/comment/list/reply/"
        params = {
            'comment_id': comment_id,
            "cursor": cursor,
            "count": 20,
            "item_type": 0,
        }
        keywords = request_keyword_var.get()
        referer_url = "https://www.douyin.com/search/" + keywords + '?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general'
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=':/')
        return await self.get(uri, params)

    async def search_user_videos(self, user_id: str, keywords: str, max_count: int = 50) -> List[Dict]:
        """
        搜索指定用户的视频（使用主页内搜索接口）
        Args:
            user_id: 用户ID
            keywords: 搜索关键词
            max_count: 最大获取数量
        Returns:
            List[Dict]: 视频列表
        """
        try:
            utils.logger.info(f"[DOUYINClient.search_user_videos] 开始搜索用户 {user_id} 的关键词 '{keywords}' 视频")
            
            # 使用抖音主页内搜索接口
            offset = 0
            all_matching_videos = []
            
            # 限制搜索页数，避免过度请求
            max_search_pages = 10
            current_page = 0
            
            while current_page < max_search_pages and len(all_matching_videos) < max_count:
                current_page += 1
                utils.logger.info(f"[DOUYINClient.search_user_videos] 搜索第 {current_page} 页")
                
                try:
                    # 构建主页内搜索请求参数
                    search_params = {
                        "device_platform": "webapp",
                        "aid": "6383",
                        "channel": "channel_pc_web",
                        "search_channel": "aweme_personal_home_video",  # 主页内搜索
                        "search_source": "normal_search",
                        "search_scene": "douyin_search",
                        "sort_type": "0",
                        "publish_time": "0",
                        "is_filter_search": "0",
                        "query_correct_type": "1",
                        "keyword": keywords,
                        "enable_history": "1",
                        "search_id": f"{int(time.time() * 1000)}CD94424B022C85DE74",  # 生成搜索ID
                        "offset": str(offset),
                        "count": "10",
                        "from_user": user_id,  # 指定用户ID
                        "pc_client_type": "1",
                        "pc_libra_divert": "Windows",
                        "support_h265": "1",
                        "support_dash": "1",
                        "version_code": "170400",
                        "version_name": "17.4.0",
                        "cookie_enabled": "true",
                        "screen_width": "2560",
                        "screen_height": "1440",
                        "browser_language": "zh-CN",
                        "browser_platform": "Win32",
                        "browser_name": "Chrome",
                        "browser_version": "139.0.0.0",
                        "browser_online": "true",
                        "engine_name": "Blink",
                        "engine_version": "139.0.0.0",
                        "os_name": "Windows",
                        "os_version": "10",
                        "cpu_core_num": "16",
                        "device_memory": "8",
                        "platform": "PC",
                        "downlink": "10",
                        "effective_type": "4g",
                        "round_trip_time": "150",
                        "webid": "7519425222413321738"
                    }
                    
                    # 设置请求头
                    headers = copy.copy(self.headers)
                    headers["Referer"] = f"https://www.douyin.com/user/{user_id}"
                    
                    # 调用主页内搜索接口
                    search_result = await self.get("/aweme/v1/web/home/search/item/", search_params, headers=headers)
                    
                    utils.logger.debug(f"[DOUYINClient.search_user_videos] 第 {current_page} 页搜索API响应: {search_result}")
                    
                    if not search_result:
                        utils.logger.warning(f"[DOUYINClient.search_user_videos] 第 {current_page} 页搜索无结果")
                        break
                    
                    # 检查搜索结果
                    aweme_list = search_result.get("aweme_list", [])
                    if not aweme_list:
                        utils.logger.info(f"[DOUYINClient.search_user_videos] 第 {current_page} 页没有更多结果")
                        break
                    
                    # 处理搜索结果
                    for aweme_item in aweme_list:
                        try:
                            video_data = aweme_item.get("item", {})
                            if video_data:
                                all_matching_videos.append(video_data)
                                utils.logger.info(f"[DOUYINClient.search_user_videos] 找到匹配用户 {user_id} 的视频: {video_data.get('desc', '')[:50]}")
                                
                                if len(all_matching_videos) >= max_count:
                                    utils.logger.info(f"[DOUYINClient.search_user_videos] 已达到最大数量限制 {max_count}")
                                    break
                        except Exception as e:
                            utils.logger.warning(f"[DOUYINClient.search_user_videos] 处理视频时出错: {e}")
                            continue
                    
                    # 检查是否还有更多结果
                    has_more = search_result.get("has_more", 0)
                    if not has_more:
                        utils.logger.info(f"[DOUYINClient.search_user_videos] 没有更多结果")
                        break
                    
                    # 更新offset用于下一页
                    offset += 10  # 每页10个结果
                    
                    # 添加延迟，避免请求过于频繁
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    utils.logger.error(f"[DOUYINClient.search_user_videos] 第 {current_page} 页搜索失败: {e}")
                    break
            
            utils.logger.info(f"[DOUYINClient.search_user_videos] 主页内搜索完成，找到 {len(all_matching_videos)} 个匹配用户 {user_id} 的视频")
            
            return all_matching_videos
            
        except Exception as e:
            utils.logger.error(f"[DOUYINClient.search_user_videos] 搜索用户视频失败: {e}")
            return []

    async def get_aweme_all_comments(
            self,
            aweme_id: str,
            crawl_interval: float = 1.0,
            is_fetch_sub_comments=False,
            callback: Optional[Callable] = None,
            max_count: int = 10,
    ):
        """
        获取帖子的所有评论，包括子评论
        :param aweme_id: 帖子ID
        :param crawl_interval: 抓取间隔
        :param is_fetch_sub_comments: 是否抓取子评论
        :param callback: 回调函数，用于处理抓取到的评论
        :param max_count: 一次帖子爬取的最大评论数量
        :return: 评论列表
        """
        result = []
        comments_has_more = 1
        comments_cursor = 0
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_aweme_comments(aweme_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", 0)
            comments_cursor = comments_res.get("cursor", 0)
            comments = comments_res.get("comments", [])
            if not comments:
                continue
            if len(result) + len(comments) > max_count:
                comments = comments[:max_count - len(result)]
            result.extend(comments)
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(aweme_id, comments)

            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                continue
            # 获取二级评论
            for comment in comments:
                reply_comment_total = comment.get("reply_comment_total")

                if reply_comment_total > 0:
                    comment_id = comment.get("cid")
                    sub_comments_has_more = 1
                    sub_comments_cursor = 0

                    while sub_comments_has_more:
                        sub_comments_res = await self.get_sub_comments(comment_id, sub_comments_cursor)
                        sub_comments_has_more = sub_comments_res.get("has_more", 0)
                        sub_comments_cursor = sub_comments_res.get("cursor", 0)
                        sub_comments = sub_comments_res.get("comments", [])

                        if not sub_comments:
                            continue
                        result.extend(sub_comments)
                        if callback:  # 如果有回调函数，就执行回调函数
                            await callback(aweme_id, sub_comments)
                        await asyncio.sleep(crawl_interval)
        return result

    async def get_user_info(self, sec_user_id: str):
        uri = "/aweme/v1/web/user/profile/other/"
        params = {
            "sec_user_id": sec_user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
        }
        
        # 设置请求头
        headers = copy.copy(self.headers)
        headers["Referer"] = f"https://www.douyin.com/user/{sec_user_id}"
        
        utils.logger.debug(f"[DOUYINClient.get_user_info] 请求参数: {params}")
        
        result = await self.get(uri, params, headers=headers)
        
        utils.logger.debug(f"[DOUYINClient.get_user_info] API响应: {result}")
        
        return result

    async def get_user_aweme_posts(self, sec_user_id: str, max_cursor: str = "") -> Dict:
        uri = "/aweme/v1/web/aweme/post/"
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "sec_user_id": sec_user_id,
            "max_cursor": max_cursor,
            "locate_query": "false",
            "show_live_replay_strategy": "1",
            "need_time_list": "1",
            "time_list_query": "0",
            "whale_cut_token": "",
            "cut_version": "1",
            "count": "18",
            "publish_video_strategy_type": "2",
            "from_user_page": "1",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "pc_libra_divert": "Windows",
            "support_h265": "1",
            "support_dash": "1",
            "cpu_core_num": "16",
            "version_code": "290100",
            "version_name": "29.1.0",
            "cookie_enabled": "true",
            "screen_width": "2560",
            "screen_height": "1440",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "139.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "139.0.0.0",
            "os_name": "Windows",
            "os_version": "10",
            "device_memory": "8",
            "platform": "PC",
            "downlink": "10",
            "effective_type": "4g",
            "round_trip_time": "150",
            "webid": "7519425222413321738"
        }
        
        # 设置请求头
        headers = copy.copy(self.headers)
        headers["Referer"] = f"https://www.douyin.com/user/{sec_user_id}"
        
        utils.logger.debug(f"[DOUYINClient.get_user_aweme_posts] 请求参数: {params}")
        
        result = await self.get(uri, params, headers=headers)
        
        utils.logger.info(f"[DOUYINClient.get_user_aweme_posts] API响应状态: {result.get('status_code', 'unknown')}")
        utils.logger.info(f"[DOUYINClient.get_user_aweme_posts] API响应has_more: {result.get('has_more', 'unknown')}")
        utils.logger.info(f"[DOUYINClient.get_user_aweme_posts] API响应aweme_list长度: {len(result.get('aweme_list', []))}")
        utils.logger.debug(f"[DOUYINClient.get_user_aweme_posts] API响应详情: {result}")
        
        return result

    async def get_all_user_aweme_posts(self, sec_user_id: str, callback: Optional[Callable] = None, max_count: int = None):
        posts_has_more = 1
        max_cursor = ""
        result = []
        page_count = 0
        
        utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 开始获取用户 {sec_user_id} 的视频，最大数量限制: {max_count}")
        
        while posts_has_more == 1:
            page_count += 1
            utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 获取第 {page_count} 页视频")
            
            try:
                aweme_post_res = await self.get_user_aweme_posts(sec_user_id, max_cursor)
                
                if not aweme_post_res:
                    utils.logger.error(f"[DOUYINClient.get_all_user_aweme_posts] 第 {page_count} 页API响应为空")
                    break
                
                posts_has_more = aweme_post_res.get("has_more", 0)
                max_cursor = aweme_post_res.get("max_cursor")
                aweme_list = aweme_post_res.get("aweme_list") if aweme_post_res.get("aweme_list") else []
                
                utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 第 {page_count} 页获取到 {len(aweme_list)} 个视频")
                utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] has_more: {posts_has_more}, max_cursor: {max_cursor}")
                
                # 🆕 应用数量限制
                if max_count is not None:
                    remaining_count = max_count - len(result)
                    if remaining_count <= 0:
                        utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 已达到最大数量限制 {max_count}，停止获取")
                        break
                    
                    # 只取需要的数量
                    if len(aweme_list) > remaining_count:
                        aweme_list = aweme_list[:remaining_count]
                        utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 限制数量，只取前 {remaining_count} 个视频")
                
                if callback:
                    await callback(aweme_list)
                result.extend(aweme_list)
                
                # 🆕 增加延迟，避免触发反爬虫
                await asyncio.sleep(2.0)
                
            except Exception as e:
                utils.logger.error(f"[DOUYINClient.get_all_user_aweme_posts] 第 {page_count} 页获取失败: {e}")
                break
        
        utils.logger.info(f"[DOUYINClient.get_all_user_aweme_posts] 用户 {sec_user_id} 视频获取完成，共 {len(result)} 个视频")
        return result
