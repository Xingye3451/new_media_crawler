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
import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractApiClient
from tools import utils

from .exception import DataFetchError, FrequencyLimitError, IPBlockError
from .graphql import KuaiShouGraphQL


class KuaiShouClient(AbstractApiClient):
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
        self._host = "https://www.kuaishou.com/graphql"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.graphql = KuaiShouGraphQL()

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        
        # 🆕 添加响应内容调试
        response_text = response.text
        utils.logger.info(f"[KuaiShouClient.request] 响应状态码: {response.status_code}")
        utils.logger.info(f"[KuaiShouClient.request] 响应内容长度: {len(response_text)}")
        utils.logger.info(f"[KuaiShouClient.request] 响应内容前500字符: {response_text[:500]}")
        
        # 检查响应是否为空
        if not response_text.strip():
            utils.logger.error(f"[KuaiShouClient.request] 响应为空")
            return {}
        
        try:
            data: Dict = response.json()
            utils.logger.info(f"[KuaiShouClient.request] JSON解析成功，数据结构: {list(data.keys()) if isinstance(data, dict) else '非字典类型'}")
            
            # 🆕 检测反爬虫机制
            if data.get("errors"):
                error_msg = str(data.get("errors"))
                utils.logger.error(f"[KuaiShouClient.request] API返回错误: {error_msg}")
                
                # 检测常见的反爬虫错误
                if "400002" in error_msg or "captcha" in error_msg.lower() or "验证码" in error_msg:
                    utils.logger.error("🚨 检测到反爬虫机制：需要验证码")
                    raise DataFetchError("反爬虫机制触发：需要验证码验证")
                elif "429" in error_msg or "too many requests" in error_msg.lower() or "请求过于频繁" in error_msg:
                    utils.logger.error("🚨 检测到反爬虫机制：请求过于频繁")
                    raise FrequencyLimitError("访问频次异常，请勿频繁操作或重启试试")
                elif "403" in error_msg or "forbidden" in error_msg.lower() or "访问被禁止" in error_msg:
                    utils.logger.error("🚨 检测到反爬虫机制：访问被禁止")
                    raise IPBlockError("访问被禁止，IP可能被封")
                else:
                    raise DataFetchError(data.get("errors", "unkonw error"))
            else:
                result = data.get("data", {})
                utils.logger.info(f"[KuaiShouClient.request] 返回数据键: {list(result.keys()) if isinstance(result, dict) else '非字典类型'}")
                return result
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient.request] JSON解析失败: {e}")
            utils.logger.error(f"[KuaiShouClient.request] 完整响应内容: {response_text}")
            # 🆕 修复：不要返回空字典，而是抛出异常，让调用方知道请求失败
            raise DataFetchError(f"JSON解析失败: {e}")

    async def get(self, uri: str, params=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"
        return await self.request(
            method="GET", url=f"{self._host}{final_uri}", headers=self.headers
        )

    async def post(self, uri: str, data: dict) -> Dict:
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        
        # 🆕 修复POST请求头
        post_headers = self.headers.copy()
        post_headers["Content-Type"] = "application/json;charset=UTF-8"
        
        utils.logger.debug(f"[KuaiShouClient.post] POST请求URL: {self._host}{uri}")
        utils.logger.debug(f"[KuaiShouClient.post] POST请求数据: {json_str}")
        utils.logger.debug(f"[KuaiShouClient.post] POST请求头: {post_headers}")
        
        return await self.request(
            method="POST", url=f"{self._host}{uri}", data=json_str, headers=post_headers
        )

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[KuaiShouClient.pong] Begin pong kuaishou...")
        ping_flag = False
        try:
            post_data = {
                "operationName": "visionProfileUserList",
                "variables": {
                    "ftype": 1,
                },
                "query": self.graphql.get("vision_profile_user_list"),
            }
            res = await self.post("", post_data)
            if res.get("visionProfileUserList", {}).get("result") == 1:
                ping_flag = True
        except Exception as e:
            utils.logger.error(
                f"[KuaiShouClient.pong] Pong kuaishou failed: {e}, and try to login again..."
            )
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
                    'domain': '.kuaishou.com',
                    'path': '/'
                }])
            
            # 更新客户端cookies
            self.headers["Cookie"] = cookie_str
            self.cookie_dict = cookie_dict
            
            utils.logger.info(f"[KuaiShouClient] 已设置 {len(cookie_dict)} 个cookies")
            
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient] 设置cookies失败: {e}")
            raise

    async def clear_cookies(self):
        """清除cookies"""
        try:
            # 清除浏览器上下文中的cookies
            await self.playwright_page.context.clear_cookies()
            
            # 清除客户端cookies
            self.headers["Cookie"] = ""
            self.cookie_dict = {}
            
            utils.logger.info("[KuaiShouClient] 已清除所有cookies")
            
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient] 清除cookies失败: {e}")
            raise

    async def search_info_by_keyword(
        self, keyword: str, pcursor: str, search_session_id: str = ""
    ):
        """
        KuaiShou web search api
        :param keyword: search keyword
        :param pcursor: limite page curson
        :param search_session_id: search session id
        :return:
        """
        post_data = {
            "operationName": "visionSearchPhoto",
            "variables": {
                "keyword": keyword,
                "pcursor": pcursor,
                "page": "search",
                "searchSessionId": search_session_id,
            },
            "query": self.graphql.get("search_query"),
        }
        
        utils.logger.info(f"[KuaiShouClient.search_info_by_keyword] 搜索关键词: '{keyword}', pcursor: '{pcursor}', search_session_id: '{search_session_id}'")
        utils.logger.info(f"[KuaiShouClient.search_info_by_keyword] POST数据: {post_data}")
        
        result = await self.post("", post_data)
        
        utils.logger.info(f"[KuaiShouClient.search_info_by_keyword] 搜索API返回结果: {result}")
        
        return result

    async def get_video_info(self, photo_id: str) -> Dict:
        """
        Kuaishou web video detail api
        :param photo_id:
        :return:
        """
        post_data = {
            "operationName": "visionVideoDetail",
            "variables": {"photoId": photo_id, "page": "search"},
            "query": self.graphql.get("video_detail"),
        }
        return await self.post("", post_data)

    async def get_video_comments(self, photo_id: str, pcursor: str = "") -> Dict:
        """get video comments
        :param photo_id: photo id you want to fetch
        :param pcursor: last you get pcursor, defaults to ""
        :return:
        """
        post_data = {
            "operationName": "commentListQuery",
            "variables": {"photoId": photo_id, "pcursor": pcursor},
            "query": self.graphql.get("comment_list"),
        }
        return await self.post("", post_data)

    async def get_video_sub_comments(
        self, photo_id: str, rootCommentId: str, pcursor: str = ""
    ) -> Dict:
        """get video sub comments
        :param photo_id: photo id you want to fetch
        :param pcursor: last you get pcursor, defaults to ""
        :return:
        """
        post_data = {
            "operationName": "visionSubCommentList",
            "variables": {
                "photoId": photo_id,
                "pcursor": pcursor,
                "rootCommentId": rootCommentId,
            },
            "query": self.graphql.get("vision_sub_comment_list"),
        }
        return await self.post("", post_data)

    async def get_creator_profile(self, userId: str) -> Dict:
        post_data = {
            "operationName": "visionProfile",
            "variables": {"userId": userId},
            "query": self.graphql.get("vision_profile"),
        }
        return await self.post("", post_data)

    async def get_video_by_creater(self, userId: str, pcursor: str = "") -> Dict:
        post_data = {
            "operationName": "visionProfilePhotoList",
            "variables": {"page": "profile", "pcursor": pcursor, "userId": userId},
            "query": self.graphql.get("vision_profile_photo_list"),
        }
        return await self.post("", post_data)

    async def get_video_all_comments(
        self,
        photo_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ):
        """
        get video all comments include sub comments
        :param photo_id:
        :param crawl_interval:
        :param callback:
        :param max_count:
        :return:
        """

        result = []
        pcursor = ""

        while pcursor != "no_more" and len(result) < max_count:
            comments_res = await self.get_video_comments(photo_id, pcursor)
            vision_commen_list = comments_res.get("visionCommentList", {})
            pcursor = vision_commen_list.get("pcursor", "")
            comments = vision_commen_list.get("rootComments", [])
            if len(result) + len(comments) > max_count:
                comments = comments[: max_count - len(result)]
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(photo_id, comments)
            result.extend(comments)
            await asyncio.sleep(crawl_interval)
            sub_comments = await self.get_comments_all_sub_comments(
                comments, photo_id, crawl_interval, callback
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[Dict],
        photo_id,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            comments: 评论列表
            photo_id: 视频id
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后
        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[KuaiShouClient.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled"
            )
            return []

        result = []
        for comment in comments:
            sub_comments = comment.get("subComments")
            if sub_comments and callback:
                await callback(photo_id, sub_comments)

            sub_comment_pcursor = comment.get("subCommentsPcursor")
            if sub_comment_pcursor == "no_more":
                continue

            root_comment_id = comment.get("commentId")
            sub_comment_pcursor = ""

            while sub_comment_pcursor != "no_more":
                comments_res = await self.get_video_sub_comments(
                    photo_id, root_comment_id, sub_comment_pcursor
                )
                vision_sub_comment_list = comments_res.get("visionSubCommentList", {})
                sub_comment_pcursor = vision_sub_comment_list.get("pcursor", "no_more")

                comments = vision_sub_comment_list.get("subComments", {})
                if callback:
                    await callback(photo_id, comments)
                await asyncio.sleep(crawl_interval)
                result.extend(comments)
        return result

    async def get_creator_info(self, user_id: str) -> Dict:
        """
        eg: https://www.kuaishou.com/profile/3x4jtnbfter525a
        快手用户主页
        """
        # 🆕 添加用户状态检查
        try:
            post_data = {
                "operationName": "visionProfilePhotoList",
                "variables": {"page": "profile", "pcursor": "", "userId": user_id},
                "query": self.graphql.get("vision_profile_photo_list"),
            }
            result = await self.post("", post_data)
            utils.logger.debug(f"[KuaiShouClient.get_creator_info] 用户 {user_id} 状态检查响应: {result}")
            return result
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient.get_creator_info] 检查用户 {user_id} 状态失败: {e}")
            return {}

        visionProfile = await self.get_creator_profile(user_id)
        return visionProfile.get("userProfile")

    async def get_all_videos_by_creator(
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
        # 🆕 先检查用户状态
        try:
            user_status = await self.get_creator_info(user_id)
            utils.logger.debug(f"[KuaiShouClient.get_all_videos_by_creator] 用户 {user_id} 状态检查: {user_status}")
            
            # 检查是否有错误信息
            if user_status.get("error"):
                utils.logger.warning(f"[KuaiShouClient.get_all_videos_by_creator] 用户 {user_id} 状态异常: {user_status.get('error')}")
                return []
                
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient.get_all_videos_by_creator] 检查用户 {user_id} 状态失败: {e}")
        
        result = []
        pcursor = ""
        max_iterations = 50  # 最大迭代次数，防止无限循环
        iteration_count = 0

        while pcursor != "no_more" and iteration_count < max_iterations:
            iteration_count += 1
            utils.logger.info(f"[KuaiShouClient.get_all_videos_by_creator] 第 {iteration_count} 次查询，pcursor: {pcursor}")
            
            videos_res = await self.get_video_by_creater(user_id, pcursor)
            if not videos_res:
                utils.logger.warning(
                    f"[KuaiShouClient.get_all_videos_by_creator] 用户 {user_id} 可能没有视频或已被封禁，停止查询"
                )
                break

            # 🆕 检测反爬虫机制
            if "visionProfilePhotoList" in videos_res:
                vision_profile_photo_list = videos_res.get("visionProfilePhotoList", {})
                result_code = vision_profile_photo_list.get("result")
                if result_code and result_code != 1:
                    utils.logger.error(f"[KuaiShouClient.get_all_videos_by_creator] API返回错误码: {result_code}")
                    
                    if result_code == 400002:
                        utils.logger.error("🚨 检测到反爬虫机制：需要验证码验证")
                        raise Exception("反爬虫机制触发：需要验证码验证，请重新登录或稍后重试")
                    elif result_code == 429:
                        utils.logger.error("🚨 检测到反爬虫机制：请求过于频繁")
                        raise Exception("反爬虫机制触发：请求过于频繁，请稍后重试")
                    elif result_code == 403:
                        utils.logger.error("🚨 检测到反爬虫机制：访问被禁止")
                        raise Exception("反爬虫机制触发：访问被禁止")
                    else:
                        utils.logger.error(f"🚨 未知错误码: {result_code}")
                        raise Exception(f"API返回错误码: {result_code}")

            # 🆕 添加详细调试日志
            utils.logger.debug(f"[KuaiShouClient.get_all_videos_by_creator] API响应: {videos_res}")
            
            # 🆕 修复：API响应结构可能直接返回数据，而不是嵌套在visionProfilePhotoList中
            if "visionProfilePhotoList" in videos_res:
                vision_profile_photo_list = videos_res.get("visionProfilePhotoList", {})
                pcursor = vision_profile_photo_list.get("pcursor", "no_more")
                videos = vision_profile_photo_list.get("feeds", [])
            else:
                # 直接使用响应数据
                pcursor = videos_res.get("pcursor", "no_more")
                videos = videos_res.get("feeds", [])
            utils.logger.info(
                f"[KuaiShouClient.get_all_videos_by_creator] got user_id:{user_id} videos len : {len(videos)}"
            )

            if callback:
                await callback(videos)
            await asyncio.sleep(crawl_interval)
            result.extend(videos)
            
            # 如果连续多次没有获取到视频，提前结束
            if len(videos) == 0 and iteration_count > 3:
                utils.logger.warning(f"[KuaiShouClient.get_all_videos_by_creator] 连续 {iteration_count} 次没有获取到视频，提前结束查询")
                break
        
        if iteration_count >= max_iterations:
            utils.logger.warning(f"[KuaiShouClient.get_all_videos_by_creator] 达到最大迭代次数 {max_iterations}，停止查询")
        
        utils.logger.info(f"[KuaiShouClient.get_all_videos_by_creator] 查询完成，共获取 {len(result)} 个视频，迭代次数: {iteration_count}")
        return result

    async def search_user_videos(self, user_id: str, keywords: str, max_count: int = 50) -> List[Dict]:
        """
        搜索指定用户的视频
        Args:
            user_id: 用户ID
            keywords: 搜索关键词
            max_count: 最大获取数量
        Returns:
            List[Dict]: 视频列表
        """
        try:
            utils.logger.info(f"[KuaiShouClient.search_user_videos] 开始搜索用户 {user_id} 的关键词 '{keywords}' 视频")
            
            # 🆕 优化：使用快手的原生搜索API，而不是获取所有视频后过滤
            # 这样可以更准确地匹配关键词，避免获取无关内容
            utils.logger.info(f"[KuaiShouClient.search_user_videos] 使用原生搜索API搜索关键词: {keywords}")
            
            # 使用全局搜索API，然后过滤出指定用户的视频
            search_session_id = ""
            pcursor = "1"
            all_matching_videos = []
            
            # 限制搜索页数，避免过度请求
            max_search_pages = 10
            current_page = 0
            
            while current_page < max_search_pages and len(all_matching_videos) < max_count:
                current_page += 1
                utils.logger.info(f"[KuaiShouClient.search_user_videos] 搜索第 {current_page} 页")
                
                try:
                    # 使用全局搜索API
                    search_result = await self.search_info_by_keyword(
                        keyword=keywords,
                        pcursor=pcursor,
                        search_session_id=search_session_id
                    )
                    
                    # 🆕 添加详细调试日志
                    utils.logger.debug(f"[KuaiShouClient.search_user_videos] 第 {current_page} 页搜索API响应: {search_result}")
                    
                    if not search_result:
                        utils.logger.warning(f"[KuaiShouClient.search_user_videos] 第 {current_page} 页搜索无结果")
                        break
                    
                    vision_search_photo = search_result.get("visionSearchPhoto", {})
                    if vision_search_photo.get("result") != 1:
                        result_code = vision_search_photo.get("result")
                        utils.logger.error(f"[KuaiShouClient.search_user_videos] 第 {current_page} 页搜索失败，错误码: {result_code}")
                        
                        # 🆕 检测反爬虫机制
                        if result_code == 400002:
                            utils.logger.error("🚨 检测到反爬虫机制：需要验证码验证")
                            raise Exception("反爬虫机制触发：需要验证码验证，请重新登录或稍后重试")
                        elif result_code == 429:
                            utils.logger.error("🚨 检测到反爬虫机制：请求过于频繁")
                            raise Exception("反爬虫机制触发：请求过于频繁，请稍后重试")
                        elif result_code == 403:
                            utils.logger.error("🚨 检测到反爬虫机制：访问被禁止")
                            raise Exception("反爬虫机制触发：访问被禁止")
                        else:
                            utils.logger.error(f"🚨 未知错误码: {result_code}")
                            raise Exception(f"搜索API返回错误码: {result_code}")
                        
                        break
                    
                    search_session_id = vision_search_photo.get("searchSessionId", "")
                    feeds = vision_search_photo.get("feeds", [])
                    
                    if not feeds:
                        utils.logger.info(f"[KuaiShouClient.search_user_videos] 第 {current_page} 页没有更多结果")
                        break
                    
                    # 过滤出指定用户的视频
                    for video in feeds:
                        try:
                            video_user_id = video.get("photo", {}).get("author", {}).get("id")
                            if video_user_id == user_id:
                                all_matching_videos.append(video)
                                utils.logger.info(f"[KuaiShouClient.search_user_videos] 找到匹配用户 {user_id} 的视频")
                                
                                if len(all_matching_videos) >= max_count:
                                    utils.logger.info(f"[KuaiShouClient.search_user_videos] 已达到最大数量限制 {max_count}")
                                    break
                        except Exception as e:
                            utils.logger.warning(f"[KuaiShouClient.search_user_videos] 处理视频时出错: {e}")
                            continue
                    
                    # 获取下一页的pcursor
                    pcursor = vision_search_photo.get("pcursor", "no_more")
                    if pcursor == "no_more":
                        utils.logger.info(f"[KuaiShouClient.search_user_videos] 搜索完成，没有更多页面")
                        break
                    
                    # 添加延迟，避免请求过于频繁
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    utils.logger.error(f"[KuaiShouClient.search_user_videos] 第 {current_page} 页搜索失败: {e}")
                    break
            
            utils.logger.info(f"[KuaiShouClient.search_user_videos] 原生搜索完成，找到 {len(all_matching_videos)} 个匹配用户 {user_id} 的视频")
            
            # 如果原生搜索没有找到足够的结果，回退到本地过滤方式
            if len(all_matching_videos) < max_count // 2:  # 如果找到的结果少于一半，使用回退方案
                utils.logger.info(f"[KuaiShouClient.search_user_videos] 原生搜索结果较少，使用本地过滤回退方案")
                
                # 获取用户的所有视频
                all_videos = await self.get_all_videos_by_creator(
                    user_id=user_id,
                    crawl_interval=0.5,
                    callback=None,
                )
                
                if all_videos:
                    # 本地关键词过滤
                    for video in all_videos:
                        try:
                            video_desc = video.get("photo", {}).get("caption", "").lower()
                            if keywords.lower() in video_desc:
                                all_matching_videos.append(video)
                                if len(all_matching_videos) >= max_count:
                                    break
                        except Exception as e:
                            utils.logger.warning(f"[KuaiShouClient.search_user_videos] 本地过滤处理视频时出错: {e}")
                            continue
                    
                    utils.logger.info(f"[KuaiShouClient.search_user_videos] 本地过滤完成，总共找到 {len(all_matching_videos)} 个匹配视频")
            
            return all_matching_videos[:max_count]  # 确保不超过最大数量限制
            
        except Exception as e:
            utils.logger.error(f"[KuaiShouClient.search_user_videos] 搜索用户视频失败: {e}")
            return []
