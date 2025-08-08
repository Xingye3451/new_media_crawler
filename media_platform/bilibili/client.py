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
# @Desc    : bilibili 请求客户端
import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractApiClient
from tools import utils

from .exception import DataFetchError, FrequencyLimitError, IPBlockError
from .field import CommentOrderType, SearchOrderType
from .help import BilibiliSign


class BilibiliClient(AbstractApiClient):
    def __init__(
            self,
            timeout=10,
            proxies=None,
            *,
            headers: Dict[str, str],
            playwright_page: Page,
            cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://api.bilibili.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data: Dict = response.json()
        
        # 🆕 检测频率限制错误
        if data.get("code") == -412 and "请求过于频繁" in data.get("message", ""):
            utils.logger.error(f"[BilibiliClient.request] 访问频次异常，需要等待更长时间: {data}")
            raise FrequencyLimitError("访问频次异常，请勿频繁操作或重启试试")
        elif data.get("code") == -403 and "访问被禁止" in data.get("message", ""):
            utils.logger.error(f"[BilibiliClient.request] 访问被禁止: {data}")
            raise IPBlockError("访问被禁止，IP可能被封")
        elif data.get("code") != 0:
            raise DataFetchError(data.get("message", "unkonw error"))
        else:
            return data.get("data", {})

    async def pre_request_data(self, req_data: Dict) -> Dict:
        """
        发送请求进行请求参数签名
        需要从 localStorage 拿 wbi_img_urls 这参数，值如下：
        https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png-https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png
        :param req_data:
        :return:
        """
        if not req_data:
            return {}
        img_key, sub_key = await self.get_wbi_keys()
        return BilibiliSign(img_key, sub_key).sign(req_data)

    async def get_wbi_keys(self) -> Tuple[str, str]:
        """
        获取最新的 img_key 和 sub_key
        :return:
        """
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        wbi_img_urls = local_storage.get("wbi_img_urls", "") or local_storage.get(
            "wbi_img_url") + "-" + local_storage.get("wbi_sub_url")
        if wbi_img_urls and "-" in wbi_img_urls:
            img_url, sub_url = wbi_img_urls.split("-")
        else:
            resp = await self.request(method="GET", url=self._host + "/x/web-interface/nav")
            img_url: str = resp['wbi_img']['img_url']
            sub_url: str = resp['wbi_img']['sub_url']
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        return img_key, sub_key

    async def get(self, uri: str, params=None, enable_params_sign: bool = True) -> Dict:
        final_uri = uri
        if enable_params_sign:
            params = await self.pre_request_data(params)
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        
        # 为播放地址请求添加特殊请求头
        headers = self.headers.copy()
        if "playurl" in uri:
            headers.update({
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site"
            })
        
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers)

    async def post(self, uri: str, data: dict) -> Dict:
        data = await self.pre_request_data(data)
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, headers=self.headers)

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[BilibiliClient.pong] Begin pong bilibili...")
        ping_flag = False
        try:
            check_login_uri = "/x/web-interface/nav"
            response = await self.get(check_login_uri)
            if response.get("isLogin"):
                utils.logger.info(
                    "[BilibiliClient.pong] Use cache login state get web interface successfull!")
                ping_flag = True
        except Exception as e:
            utils.logger.error(
                f"[BilibiliClient.pong] Pong bilibili failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def set_cookies_from_string(self, cookie_str: str):
        """从字符串设置cookies"""
        try:
            from tools import utils as crawler_utils
            cookie_dict = crawler_utils.convert_str_cookie_to_dict(cookie_str)
            
            # 设置cookies到浏览器上下文
            for key, value in cookie_dict.items():
                await self.playwright_page.context.add_cookies([{
                    'name': key,
                    'value': value,
                    'domain': '.bilibili.com',
                    'path': '/'
                }])
            
            # 更新客户端cookies
            self.headers["Cookie"] = cookie_str
            self.cookie_dict = cookie_dict
            
            utils.logger.info(f"[BilibiliClient] 已设置 {len(cookie_dict)} 个cookies")
            
        except Exception as e:
            utils.logger.error(f"[BilibiliClient] 设置cookies失败: {e}")
            raise

    async def clear_cookies(self):
        """清除cookies"""
        try:
            # 清除浏览器上下文中的cookies
            await self.playwright_page.context.clear_cookies()
            
            # 清除客户端cookies
            self.headers["Cookie"] = ""
            self.cookie_dict = {}
            
            utils.logger.info("[BilibiliClient] 已清除所有cookies")
            
        except Exception as e:
            utils.logger.error(f"[BilibiliClient] 清除cookies失败: {e}")
            raise

    async def search_video_by_keyword(self, keyword: str, page: int = 1, page_size: int = 20,
                                      order: SearchOrderType = SearchOrderType.DEFAULT,
                                      pubtime_begin_s: int = 0, pubtime_end_s: int = 0) -> Dict:

        """
        KuaiShou web search api
        :param keyword: 搜索关键词
        :param page: 分页参数具体第几页
        :param page_size: 每一页参数的数量
        :param order: 搜索结果排序，默认位综合排序
        :param pubtime_begin_s: 发布时间开始时间戳
        :param pubtime_end_s: 发布时间结束时间戳
        :return:
        """
        uri = "/x/web-interface/wbi/search/type"
        post_data = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": order.value,
            "pubtime_begin_s": pubtime_begin_s,
            "pubtime_end_s": pubtime_end_s
        }
        return await self.get(uri, post_data)

    async def search_up_videos(self, creator_id: int, keywords: str, page: int = 1, page_size: int = 20) -> Dict:
        """
        搜索指定UP主的视频（使用通用搜索API）
        :param creator_id: UP主ID
        :param keywords: 搜索关键词
        :param page: 分页参数具体第几页
        :param page_size: 每一页参数的数量
        :return: 搜索结果
        """
        uri = "/x/web-interface/wbi/search/type"
        post_data = {
            "search_type": "video",
            "keyword": f"uid:{creator_id} {keywords}",  # 使用uid:前缀限制搜索范围
            "page": page,
            "page_size": page_size,
            "order": SearchOrderType.LAST_PUBLISH.value,  # 按发布时间排序
        }
        return await self.get(uri, post_data)

    async def search_creator_videos(self, creator_id: int, keywords: str, page: int = 1, page_size: int = 20) -> Dict:
        """
        搜索指定UP主的视频（使用创作者主页专用搜索API）
        :param creator_id: UP主ID
        :param keywords: 搜索关键词
        :param page: 分页参数具体第几页
        :param page_size: 每一页参数的数量
        :return: 搜索结果
        """
        # 使用创作者主页的专用搜索API
        uri = "/x/space/wbi/arc/search"
        params = {
            "pn": page,
            "ps": page_size,
            "tid": 0,
            "special_type": "",
            "order": "pubdate",  # 按发布时间排序
            "mid": creator_id,
            "index": 0,
            "keyword": keywords,  # 搜索关键词
            "order_avoided": "true",
            "platform": "web",
            "web_location": "333.1387"
        }
        # 使用WBI签名，因为这是需要认证的API
        return await self.get(uri, params, enable_params_sign=True)

    async def get_video_info(self, aid: Union[int, None] = None, bvid: Union[str, None] = None) -> Dict:
        """
        Bilibli web video detail api, aid 和 bvid任选一个参数
        :param aid: 稿件avid
        :param bvid: 稿件bvid
        :return:
        """
        if not aid and not bvid:
            raise ValueError("请提供 aid 或 bvid 中的至少一个参数")

        uri = "/x/web-interface/view/detail"
        params = dict()
        if aid:
            params.update({"aid": aid})
        else:
            params.update({"bvid": bvid})
        return await self.get(uri, params, enable_params_sign=False)

    async def get_video_play_url(self, aid: int, cid: int) -> Dict:
        """
        Bilibli web video play url api
        :param aid: 稿件avid
        :param cid: cid
        :return:
        """
        if not aid or not cid or aid <= 0 or cid <= 0:
            raise ValueError("aid 和 cid 必须存在")
        
        # 尝试多个API端点
        endpoints = [
            ("/x/player/wbi/playurl", True),   # 带WBI签名
            ("/x/player/playurl", False),      # 不带WBI签名
        ]
        
        for uri, enable_sign in endpoints:
            try:
                params = {
                    "avid": aid,
                    "cid": cid,
                    "qn": 80,
                    "fourk": 1,
                    "fnval": 1,
                    "platform": "pc",
                    "high_quality": 1,  # 请求高质量视频
                }
                
                utils.logger.info(f"[BilibiliClient] 尝试获取播放地址 - aid: {aid}, cid: {cid}, uri: {uri}")
                result = await self.get(uri, params, enable_params_sign=enable_sign)
                
                # 检查返回结果是否包含视频URL
                if result and (result.get("durl") or result.get("data", {}).get("durl")):
                    utils.logger.info(f"[BilibiliClient] 成功获取播放地址 - aid: {aid}, cid: {cid}")
                    return result
                else:
                    utils.logger.warning(f"[BilibiliClient] API返回结果不包含视频URL - aid: {aid}, cid: {cid}, uri: {uri}")
                    
            except Exception as e:
                utils.logger.warning(f"[BilibiliClient] API调用失败 - aid: {aid}, cid: {cid}, uri: {uri}, error: {e}")
                continue
        
        # 如果所有端点都失败，抛出异常
        raise DataFetchError(f"无法获取视频播放地址 - aid: {aid}, cid: {cid}")

    async def get_video_media(self, url: str) -> Union[bytes, None]:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request("GET", url, timeout=self.timeout, headers=self.headers)
            if not response.reason_phrase == "OK":
                utils.logger.error(f"[BilibiliClient.get_video_media] request {url} err, res:{response.text}")
                return None
            else:
                return response.content

    async def get_video_comments(self,
                                 video_id: str,
                                 order_mode: CommentOrderType = CommentOrderType.DEFAULT,
                                 next: int = 0
                                 ) -> Dict:
        """get video comments
        :param video_id: 视频 ID
        :param order_mode: 排序方式
        :param next: 评论页选择
        :return:
        """
        uri = "/x/v2/reply/wbi/main"
        post_data = {
            "oid": video_id,
            "mode": order_mode.value,
            "type": 1,
            "ps": 20,
            "next": next
        }
        return await self.get(uri, post_data)

    async def get_video_all_comments(self, video_id: str, crawl_interval: float = 1.0, is_fetch_sub_comments=False,
                                     callback: Optional[Callable] = None,
                                     max_count: int = 10,):
        """
        get video all comments include sub comments
        :param video_id:
        :param crawl_interval:
        :param is_fetch_sub_comments:
        :param callback:
        max_count: 一次笔记爬取的最大评论数量

        :return:
        """

        result = []
        is_end = False
        next_page = 0
        while not is_end and len(result) < max_count:
            comments_res = await self.get_video_comments(video_id, CommentOrderType.DEFAULT, next_page)
            cursor_info: Dict = comments_res.get("cursor")
            comment_list: List[Dict] = comments_res.get("replies", [])
            is_end = cursor_info.get("is_end")
            next_page = cursor_info.get("next")
            if is_fetch_sub_comments:
                for comment in comment_list:
                    comment_id = comment['rpid']
                    if (comment.get("rcount", 0) > 0):
                        {
                            await self.get_video_all_level_two_comments(
                                video_id, comment_id, CommentOrderType.DEFAULT, 10, crawl_interval,  callback)
                        }
            if len(result) + len(comment_list) > max_count:
                comment_list = comment_list[:max_count - len(result)]
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(video_id, comment_list)
            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                result.extend(comment_list)
                continue
        return result

    async def get_video_all_level_two_comments(self,
                                               video_id: str,
                                               level_one_comment_id: int,
                                               order_mode: CommentOrderType,
                                               ps: int = 10,
                                               crawl_interval: float = 1.0,
                                               callback: Optional[Callable] = None,
                                               ) -> Dict:
        """
        get video all level two comments for a level one comment
        :param video_id: 视频 ID
        :param level_one_comment_id: 一级评论 ID
        :param order_mode:
        :param ps: 一页评论数
        :param crawl_interval:
        :param callback:
        :return:
        """

        pn = 1
        while True:
            result = await self.get_video_level_two_comments(
                video_id, level_one_comment_id, pn, ps, order_mode)
            comment_list: List[Dict] = result.get("replies", [])
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(video_id, comment_list)
            await asyncio.sleep(crawl_interval)
            if (int(result["page"]["count"]) <= pn * ps):
                break

            pn += 1

    async def get_video_level_two_comments(self,
                                           video_id: str,
                                           level_one_comment_id: int,
                                           pn: int,
                                           ps: int,
                                           order_mode: CommentOrderType,
                                           ) -> Dict:
        """get video level two comments
        :param video_id: 视频 ID
        :param level_one_comment_id: 一级评论 ID
        :param order_mode: 排序方式

        :return:
        """
        uri = "/x/v2/reply/reply"
        post_data = {
            "oid": video_id,
            "mode": order_mode.value,
            "type": 1,
            "ps": ps,
            "pn": pn,
            "root": level_one_comment_id,
        }
        result = await self.get(uri, post_data)
        return result

    async def get_creator_videos(self, creator_id: str, pn: int, ps: int = 30, order_mode: SearchOrderType = SearchOrderType.LAST_PUBLISH) -> Dict:
        """get all videos for a creator
        :param creator_id: 创作者 ID
        :param pn: 页数
        :param ps: 一页视频数
        :param order_mode: 排序方式

        :return:
        """
        uri = "/x/space/wbi/arc/search"
        post_data = {
            "mid": creator_id,
            "pn": pn,
            "ps": ps,
            "order": order_mode,
        }
        return await self.get(uri, post_data)

    async def get_creator_info(self, creator_id: int) -> Dict:
        """
        get creator info
        :param creator_id: 作者 ID
        """
        uri = "/x/space/wbi/acc/info"
        post_data = {
            "mid": creator_id,
        }
        return await self.get(uri, post_data)

    async def get_creator_fans(self,
                               creator_id: int,
                               pn: int,
                               ps: int = 24,
                               ) -> Dict:
        """
        get creator fans
        :param creator_id: 创作者 ID
        :param pn: 开始页数
        :param ps: 每页数量
        :return:
        """
        uri = "/x/relation/fans"
        post_data = {
            'vmid': creator_id,
            "pn": pn,
            "ps": ps,
            "gaia_source": "main_web",

        }
        return await self.get(uri, post_data)

    async def get_creator_followings(self,
                                     creator_id: int,
                                     pn: int,
                                     ps: int = 24,
                                     ) -> Dict:
        """
        get creator followings
        :param creator_id: 创作者 ID
        :param pn: 开始页数
        :param ps: 每页数量
        :return:
        """
        uri = "/x/relation/followings"
        post_data = {
            "vmid": creator_id,
            "pn": pn,
            "ps": ps,
            "gaia_source": "main_web",
        }
        return await self.get(uri, post_data)

    async def get_creator_dynamics(self, creator_id: int, offset: str = ""):
        """
        get creator comments
        :param creator_id: 创作者 ID
        :param offset: 发送请求所需参数
        :return:
        """
        uri = "/x/polymer/web-dynamic/v1/feed/space"
        post_data = {
            "offset": offset,
            "host_mid": creator_id,
            "platform": "web",
        }

        return await self.get(uri, post_data)

    async def get_creator_all_fans(self, creator_info: Dict, crawl_interval: float = 1.0,
                                   callback: Optional[Callable] = None,
                                   max_count: int = 100) -> List:
        """
        get creator all fans
        :param creator_info:
        :param crawl_interval:
        :param callback:
        :param max_count: 一个up主爬取的最大粉丝数量

        :return: up主粉丝数列表
        """
        creator_id = creator_info["id"]
        result = []
        pn = config.START_CONTACTS_PAGE
        while len(result) < max_count:
            fans_res: Dict = await self.get_creator_fans(creator_id, pn=pn)
            fans_list: List[Dict] = fans_res.get("list", [])

            pn += 1
            if len(result) + len(fans_list) > max_count:
                fans_list = fans_list[:max_count - len(result)]
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(creator_info, fans_list)
            await asyncio.sleep(crawl_interval)
            if not fans_list:
                break
            result.extend(fans_list)
        return result

    async def get_creator_all_followings(self, creator_info: Dict, crawl_interval: float = 1.0,
                                         callback: Optional[Callable] = None,
                                         max_count: int = 100) -> List:
        """
        get creator all followings
        :param creator_info:
        :param crawl_interval:
        :param callback:
        :param max_count: 一个up主爬取的最大关注者数量

        :return: up主关注者列表
        """
        creator_id = creator_info["id"]
        result = []
        pn = config.START_CONTACTS_PAGE
        while len(result) < max_count:
            followings_res: Dict = await self.get_creator_followings(creator_id, pn=pn)
            followings_list: List[Dict] = followings_res.get("list", [])

            pn += 1
            if len(result) + len(followings_list) > max_count:
                followings_list = followings_list[:max_count - len(result)]
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(creator_info, followings_list)
            await asyncio.sleep(crawl_interval)
            if not followings_list:
                break
            result.extend(followings_list)
        return result

    async def get_creator_all_dynamics(self, creator_info: Dict, crawl_interval: float = 1.0,
                                       callback: Optional[Callable] = None,
                                       max_count: int = 20) -> List:
        """
        get creator all followings
        :param creator_info:
        :param crawl_interval:
        :param callback:
        :param max_count: 一个up主爬取的最大动态数量

        :return: up主关注者列表
        """
        creator_id = creator_info["id"]
        result = []
        offset = ""
        has_more = True
        while has_more and len(result) < max_count:
            dynamics_res = await self.get_creator_dynamics(creator_id, offset)
            dynamics_list: List[Dict] = dynamics_res["items"]
            has_more = dynamics_res["has_more"]
            offset = dynamics_res["offset"]
            if len(result) + len(dynamics_list) > max_count:
                dynamics_list = dynamics_list[:max_count - len(result)]
            if callback:
                await callback(creator_info, dynamics_list)
            await asyncio.sleep(crawl_interval)
            result.extend(dynamics_list)
        return result
