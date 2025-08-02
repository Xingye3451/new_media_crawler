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
import json
import re
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_result, wait_exponential

import config
from base.base_crawler import AbstractApiClient
from tools import utils
from html import unescape

from .exception import DataFetchError, IPBlockError
from .field import SearchNoteType, SearchSortType
from .help import get_search_id, sign


class XiaoHongShuClient(AbstractApiClient):
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
        self._host = "https://edith.xiaohongshu.com"
        self._domain = "https://www.xiaohongshu.com"
        self.IP_ERROR_STR = "网络连接异常，请检查网络设置或重启试试"
        self.IP_ERROR_CODE = 300012
        self.NOTE_ABNORMAL_STR = "笔记状态异常，请稍后查看"
        self.NOTE_ABNORMAL_CODE = -510001
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def _pre_headers(self, url: str, data=None) -> Dict:
        """
        请求头参数签名
        Args:
            url:
            data:

        Returns:

        """
        encrypt_params = await self.playwright_page.evaluate(
            "([url, data]) => window._webmsxyw(url,data)", [url, data]
        )
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        signs = sign(
            a1=self.cookie_dict.get("a1", ""),
            b1=local_storage.get("b1", ""),
            x_s=encrypt_params.get("X-s", ""),
            x_t=str(encrypt_params.get("X-t", "")),
        )

        headers = {
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "x-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"],
        }
        self.headers.update(headers)
        return self.headers

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def request(self, method, url, **kwargs) -> Union[str, Any]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        # return response.text
        return_response = kwargs.pop("return_response", False)

        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code == 471 or response.status_code == 461:
            # someday someone maybe will bypass captcha
            verify_type = response.headers.get("Verifytype", "unknown")
            verify_uuid = response.headers.get("Verifyuuid", "unknown")
            utils.logger.error(f"[XiaoHongShuClient.request] 出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}")
            raise Exception(
                f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}, Response: {response}"
            )

        if return_response:
            return response.text
        
        try:
            data: Dict = response.json()
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuClient.request] JSON解析失败: {e}, Response: {response.text}")
            raise DataFetchError(f"响应数据格式错误: {e}")
        
        if data.get("success"):
            return data.get("data", data.get("success", {}))
        elif data.get("code") == self.IP_ERROR_CODE:
            utils.logger.error(f"[XiaoHongShuClient.request] IP被限制: {data}")
            raise IPBlockError(self.IP_ERROR_STR)
        elif data.get("code") == -510000 and data.get("msg") == "笔记不存在":
            # 🆕 修复：笔记不存在是正常现象，不是错误
            utils.logger.debug(f"[XiaoHongShuClient.request] 笔记不存在，这是正常现象: {data}")
            return {}  # 返回空字典，让调用方处理
        elif data.get("code") == -510001 and data.get("msg") == "笔记状态异常，请稍后查看":
            # 🆕 修复：笔记状态异常也是正常现象
            utils.logger.debug(f"[XiaoHongShuClient.request] 笔记状态异常，这是正常现象: {data}")
            return {}  # 返回空字典，让调用方处理
        else:
            error_msg = data.get("msg", f"未知错误，状态码: {response.status_code}")
            utils.logger.error(f"[XiaoHongShuClient.request] 请求失败: {error_msg}, 完整响应: {data}")
            raise DataFetchError(error_msg)

    async def get(self, uri: str, params=None) -> Dict:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"
        headers = await self._pre_headers(final_uri)
        return await self.request(
            method="GET", url=f"{self._host}{final_uri}", headers=headers
        )

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        headers = await self._pre_headers(uri, data)
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST",
            url=f"{self._host}{uri}",
            data=json_str,
            headers=headers,
            **kwargs,
        )

    async def get_note_media(self, url: str) -> Union[bytes, None]:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request("GET", url, timeout=self.timeout)
            if not response.reason_phrase == "OK":
                utils.logger.error(
                    f"[XiaoHongShuClient.get_note_media] request {url} err, res:{response.text}"
                )
                return None
            else:
                return response.content

    async def pong(self) -> bool:
        """
        用于检查登录态是否失效了
        Returns:

        """
        """get a note to check if login state is ok"""
        utils.logger.info("[XiaoHongShuClient.pong] Begin to pong xhs...")
        ping_flag = False
        
        # 检查cookies状态
        cookie_count = len(self.cookie_dict) if self.cookie_dict else 0
        utils.logger.info(f"[XiaoHongShuClient.pong] Current cookies count: {cookie_count}")
        if cookie_count > 0:
            utils.logger.info(f"[XiaoHongShuClient.pong] Cookie keys: {list(self.cookie_dict.keys())}")
        
        try:
            note_card: Dict = await self.get_note_by_keyword(keyword="小红书")
            if note_card.get("items"):
                ping_flag = True
                utils.logger.info("[XiaoHongShuClient.pong] Ping xhs success")
            else:
                utils.logger.warning("[XiaoHongShuClient.pong] Ping xhs failed: no items returned")
                utils.logger.debug(f"[XiaoHongShuClient.pong] Response: {note_card}")
        except DataFetchError as e:
            utils.logger.error(
                f"[XiaoHongShuClient.pong] Ping xhs failed with DataFetchError: {e}, and try to login again..."
            )
            ping_flag = False
        except IPBlockError as e:
            utils.logger.error(
                f"[XiaoHongShuClient.pong] Ping xhs failed with IPBlockError: {e}, IP may be blocked..."
            )
            ping_flag = False
        except Exception as e:
            utils.logger.error(
                f"[XiaoHongShuClient.pong] Ping xhs failed with unexpected error: {e}, and try to login again..."
            )
            ping_flag = False
        
        # 如果ping失败，尝试使用不同的关键词
        if not ping_flag:
            utils.logger.info("[XiaoHongShuClient.pong] 尝试使用备用关键词进行ping测试...")
            try:
                note_card: Dict = await self.get_note_by_keyword(keyword="美食")
                if note_card.get("items"):
                    ping_flag = True
                    utils.logger.info("[XiaoHongShuClient.pong] 备用关键词ping成功")
                else:
                    utils.logger.warning("[XiaoHongShuClient.pong] 备用关键词ping也失败")
            except Exception as e:
                utils.logger.error(f"[XiaoHongShuClient.pong] 备用关键词ping失败: {e}")
        
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        """
        API客户端提供的更新cookies方法，一般情况下登录成功后会调用此方法
        Args:
            browser_context: 浏览器上下文对象

        Returns:

        """
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
                    'domain': '.xiaohongshu.com',
                    'path': '/'
                }])
            
            # 更新客户端cookies
            self.headers["Cookie"] = cookie_str
            self.cookie_dict = cookie_dict
            
            utils.logger.info(f"[XiaoHongShuClient] 已设置 {len(cookie_dict)} 个cookies")
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuClient] 设置cookies失败: {e}")
            raise

    async def clear_cookies(self):
        """清除cookies"""
        try:
            # 清除浏览器上下文中的cookies
            await self.playwright_page.context.clear_cookies()
            
            # 清除客户端cookies
            self.headers["Cookie"] = ""
            self.cookie_dict = {}
            
            utils.logger.info("[XiaoHongShuClient] 已清除所有cookies")
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuClient] 清除cookies失败: {e}")
            raise

    async def get_note_by_keyword(
        self,
        keyword: str,
        search_id: str = get_search_id(),
        page: int = 1,
        page_size: int = 20,
        sort: SearchSortType = SearchSortType.GENERAL,
        note_type: SearchNoteType = SearchNoteType.ALL,
    ) -> Dict:
        """
        根据关键词搜索笔记
        Args:
            keyword: 关键词参数
            page: 分页第几页
            page_size: 分页数据长度
            sort: 搜索结果排序指定
            note_type: 搜索的笔记类型

        Returns:

        """
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": search_id,
            "sort": sort.value,
            "note_type": note_type.value,
        }
        return await self.post(uri, data)

    async def get_note_by_id(
        self, note_id: str, xsec_source: str, xsec_token: str
    ) -> Dict:
        """
        获取笔记详情API
        Args:
            note_id:笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        if xsec_source == "":
            xsec_source = "pc_search"

        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        # 🆕 修复：将错误日志改为警告级别，因为这是正常现象
        # 爬取频繁了可能会出现有的笔记能有结果有的没有，这是正常现象
        utils.logger.warning(
            f"[XiaoHongShuClient.get_note_by_id] 笔记详情获取失败，使用基本信息: note_id={note_id}"
        )
        return dict()

    async def get_note_comments(
        self, note_id: str, xsec_token: str, cursor: str = ""
    ) -> Dict:
        """
        获取一级评论的API
        Args:
            note_id: 笔记ID
            xsec_token: 验证token
            cursor: 分页游标

        Returns:

        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
        }
        return await self.get(uri, params)

    async def get_note_sub_comments(
        self,
        note_id: str,
        root_comment_id: str,
        xsec_token: str,
        num: int = 10,
        cursor: str = "",
    ):
        """
        获取指定父评论下的子评论的API
        Args:
            note_id: 子评论的帖子ID
            root_comment_id: 根评论ID
            xsec_token: 验证token
            num: 分页数量
            cursor: 分页游标

        Returns:

        """
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": num,
            "cursor": cursor,
            "image_formats": "jpg,webp,avif",
            "top_comment_id": "",
            "xsec_token": xsec_token,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        note_id: str,
        xsec_token: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List[Dict]:
        """
        获取指定笔记下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            note_id: 笔记ID
            xsec_token: 验证token
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后
            max_count: 一次笔记爬取的最大评论数量
        Returns:

        """
        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_note_comments(
                note_id=note_id, xsec_token=xsec_token, cursor=comments_cursor
            )
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            if "comments" not in comments_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_note_all_comments] No 'comments' key found in response: {comments_res}"
                )
                break
            comments = comments_res["comments"]
            if len(result) + len(comments) > max_count:
                comments = comments[: max_count - len(result)]
            if callback:
                await callback(note_id, comments)
            await asyncio.sleep(crawl_interval)
            result.extend(comments)
            sub_comments = await self.get_comments_all_sub_comments(
                comments=comments,
                xsec_token=xsec_token,
                crawl_interval=crawl_interval,
                callback=callback,
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[Dict],
        xsec_token: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            comments: 评论列表
            xsec_token: 验证token
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled"
            )
            return []

        result = []
        for comment in comments:
            note_id = comment.get("note_id")
            sub_comments = comment.get("sub_comments")
            if sub_comments and callback:
                await callback(note_id, sub_comments)

            sub_comment_has_more = comment.get("sub_comment_has_more")
            if not sub_comment_has_more:
                continue

            root_comment_id = comment.get("id")
            sub_comment_cursor = comment.get("sub_comment_cursor")

            while sub_comment_has_more:
                comments_res = await self.get_note_sub_comments(
                    note_id=note_id,
                    root_comment_id=root_comment_id,
                    xsec_token=xsec_token,
                    num=10,
                    cursor=sub_comment_cursor,
                )
                
                if comments_res is None:
                    utils.logger.info(
                        f"[XiaoHongShuClient.get_comments_all_sub_comments] No response found for note_id: {note_id}"
                    )
                    continue
                sub_comment_has_more = comments_res.get("has_more", False)
                sub_comment_cursor = comments_res.get("cursor", "")
                if "comments" not in comments_res:
                    utils.logger.info(
                        f"[XiaoHongShuClient.get_comments_all_sub_comments] No 'comments' key found in response: {comments_res}"
                    )
                    break
                comments = comments_res["comments"]
                if callback:
                    await callback(note_id, comments)
                await asyncio.sleep(crawl_interval)
                result.extend(comments)
        return result

    async def get_creator_info(self, user_id: str) -> Dict:
        """
        通过解析网页版的用户主页HTML，获取用户个人简要信息
        PC端用户主页的网页存在window.__INITIAL_STATE__这个变量上的，解析它即可
        eg: https://www.xiaohongshu.com/user/profile/59d8cb33de5fb4696bf17217
        """
        uri = f"/user/profile/{user_id}"
        html_content = await self.request(
            "GET", self._domain + uri, return_response=True, headers=self.headers
        )
        match = re.search(
            r"<script>window.__INITIAL_STATE__=(.+)<\/script>", html_content, re.M
        )

        if match is None:
            return {}

        info = json.loads(match.group(1).replace(":undefined", ":null"), strict=False)
        if info is None:
            return {}
        return info.get("user").get("userPageData")

    async def get_notes_by_creator(
        self, creator: str, cursor: str, page_size: int = 30
    ) -> Dict:
        """
        获取博主的笔记
        Args:
            creator: 博主ID
            cursor: 上一页最后一条笔记的ID
            page_size: 分页数据长度

        Returns:

        """
        uri = "/api/sns/web/v1/user_posted"
        data = {
            "user_id": creator,
            "cursor": cursor,
            "num": page_size,
            "image_formats": "jpg,webp,avif",
        }
        return await self.get(uri, data)

    async def get_all_notes_by_creator(
        self,
        user_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        获取指定用户下的所有发过的帖子，该方法会一直查找一个用户下的所有帖子信息
        Args:
            user_id: 用户ID
            crawl_interval: 爬取一次的延迟单位（秒）
            callback: 一次分页爬取结束后的更新回调函数

        Returns:

        """
        result = []
        notes_has_more = True
        notes_cursor = ""
        while notes_has_more and len(result) < config.CRAWLER_MAX_NOTES_COUNT:
            notes_res = await self.get_notes_by_creator(user_id, notes_cursor)
            if not notes_res:
                utils.logger.error(
                    f"[XiaoHongShuClient.get_notes_by_creator] The current creator may have been banned by xhs, so they cannot access the data."
                )
                break

            notes_has_more = notes_res.get("has_more", False)
            notes_cursor = notes_res.get("cursor", "")
            if "notes" not in notes_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_all_notes_by_creator] No 'notes' key found in response: {notes_res}"
                )
                break

            notes = notes_res["notes"]
            utils.logger.info(
                f"[XiaoHongShuClient.get_all_notes_by_creator] got user_id:{user_id} notes len : {len(notes)}"
            )

            remaining = config.CRAWLER_MAX_NOTES_COUNT - len(result)
            if remaining <= 0:
                break

            notes_to_add = notes[:remaining]
            if callback:
                await callback(notes_to_add)

            result.extend(notes_to_add)
            await asyncio.sleep(crawl_interval)

        utils.logger.info(
            f"[XiaoHongShuClient.get_all_notes_by_creator] Finished getting notes for user {user_id}, total: {len(result)}"
        )
        return result

    async def get_note_short_url(self, note_id: str) -> Dict:
        """
        获取笔记的短链接
        Args:
            note_id: 笔记ID

        Returns:

        """
        uri = f"/api/sns/web/short_url"
        data = {"original_url": f"{self._domain}/discovery/item/{note_id}"}
        return await self.post(uri, data=data, return_response=True)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        """
        通过解析网页版的笔记详情页HTML，获取笔记详情, 该接口可能会出现失败的情况，这里尝试重试3次
        copy from https://github.com/ReaJason/xhs/blob/eb1c5a0213f6fbb592f0a2897ee552847c69ea2d/xhs/core.py#L217-L259
        thanks for ReaJason
        Args:
            note_id:
            xsec_source:
            xsec_token:
            enable_cookie:

        Returns:

        """

        def camel_to_underscore(key):
            return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()

        def transform_json_keys(json_data):
            data_dict = json.loads(json_data)
            dict_new = {}
            for key, value in data_dict.items():
                new_key = camel_to_underscore(key)
                if not value:
                    dict_new[new_key] = value
                elif isinstance(value, dict):
                    dict_new[new_key] = transform_json_keys(json.dumps(value))
                elif isinstance(value, list):
                    dict_new[new_key] = [
                        (
                            transform_json_keys(json.dumps(item))
                            if (item and isinstance(item, dict))
                            else item
                        )
                        for item in value
                    ]
                else:
                    dict_new[new_key] = value
            return dict_new

        url = (
            "https://www.xiaohongshu.com/explore/"
            + note_id
            + f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
        )
        copy_headers = self.headers.copy()
        if not enable_cookie:
            del copy_headers["Cookie"]

        html = await self.request(
            method="GET", url=url, return_response=True, headers=copy_headers
        )

        def get_note_dict(html):
            state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[
                0
            ].replace("undefined", '""')

            if state != "{}":
                note_dict = transform_json_keys(state)
                return note_dict["note"]["note_detail_map"][note_id]["note"]
            return {}

        try:
            return get_note_dict(html)
        except:
            return None

    async def search_user_notes(self, user_id: str, keywords: str, max_count: int = 50) -> List[Dict]:
        """
        搜索指定用户的笔记
        Args:
            user_id: 用户ID
            keywords: 搜索关键词
            max_count: 最大获取数量
        Returns:
            List[Dict]: 笔记列表
        """
        try:
            utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 开始搜索用户 {user_id} 的关键词 '{keywords}' 笔记")
            
            # 🆕 使用小红书的原生搜索API，然后过滤出指定用户的笔记
            utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 使用原生搜索API搜索关键词: {keywords}")
            
            all_matching_notes = []
            page = 1
            max_search_pages = 10  # 限制搜索页数，避免过度请求
            
            while page <= max_search_pages and len(all_matching_notes) < max_count:
                utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 搜索第 {page} 页")
                
                try:
                    # 使用全局搜索API
                    search_result = await self.get_note_by_keyword(
                        keyword=keywords,
                        page=page,
                        page_size=20,
                        note_type=SearchNoteType.VIDEO  # 默认搜索视频内容
                    )
                    
                    utils.logger.debug(f"[XiaoHongShuClient.search_user_notes] 第 {page} 页搜索API响应: {search_result}")
                    
                    if not search_result or not search_result.get("items"):
                        utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 第 {page} 页没有更多结果")
                        break
                    
                    items = search_result.get("items", [])
                    
                    # 过滤出指定用户的笔记
                    for note in items:
                        try:
                            note_user_id = note.get("user", {}).get("user_id")
                            if note_user_id == user_id:
                                all_matching_notes.append(note)
                                utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 找到匹配用户 {user_id} 的笔记")
                                
                                if len(all_matching_notes) >= max_count:
                                    utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 已达到最大数量限制 {max_count}")
                                    break
                        except Exception as e:
                            utils.logger.warning(f"[XiaoHongShuClient.search_user_notes] 处理笔记时出错: {e}")
                            continue
                    
                    # 如果当前页没有找到匹配的笔记，继续搜索下一页
                    page += 1
                    
                    # 添加延迟，避免请求过于频繁
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    utils.logger.error(f"[XiaoHongShuClient.search_user_notes] 第 {page} 页搜索失败: {e}")
                    break
            
            utils.logger.info(f"[XiaoHongShuClient.search_user_notes] 搜索完成，找到 {len(all_matching_notes)} 个匹配用户 {user_id} 的笔记")
            return all_matching_notes
            
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuClient.search_user_notes] 搜索用户笔记失败: {e}")
            return []
