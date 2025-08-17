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
# @Time    : 2024/1/14 18:46
# @Desc    : 抖音存储实现类
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict, List

import aiofiles

import config
from base.base_crawler import AbstractStore
from tools import utils, words
from var import crawler_type_var


def calculate_number_of_files(file_store_path: str) -> int:
    """计算数据保存文件的前部分排序数字，支持每次运行代码不写到同一个文件中
    Args:
        file_store_path;
    Returns:
        file nums
    """
    if not os.path.exists(file_store_path):
        return 1
    try:
        return max([int(file_name.split("_")[0]) for file_name in os.listdir(file_store_path)]) + 1
    except ValueError:
        return 1


class DouyinCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/douyin"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/douyin/search_comments_20240114.csv ...

        """
        return f"{self.csv_store_path}/{self.file_count}_{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.csv"

    async def save_data_to_csv(self, save_item: Dict, store_type: str):
        """
        Below is a simple way to save it in CSV format.
        Args:
            save_item:  save content dict info
            store_type: Save type contains content and comments（contents | comments）

        Returns: no returns

        """
        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(store_type=store_type)
        async with aiofiles.open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if await f.tell() == 0:
                await writer.writerow(save_item.keys())
            await writer.writerow(save_item.values())

    async def store_content(self, content_item: Dict):
        """
        Douyin content CSV storage implementation
        Args:
            content_item: note item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        Douyin comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")

    async def store_creator(self, creator: Dict):
        """
        Douyin creator CSV storage implementation
        Args:
            creator: creator item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=creator, store_type="creator")


class DouyinDbStoreImplement(AbstractStore):
    
    def _extract_video_download_url(self, aweme_detail: Dict) -> str:
        """
        提取视频下载地址

        Args:
            aweme_detail (Dict): 抖音视频

        Returns:
            str: 视频下载地址
        """
        # 优先使用 download_addr
        video_item = aweme_detail.get("video", {})
        download_addr = video_item.get("download_addr", {})
        if download_addr and download_addr.get("url_list"):
            return download_addr["url_list"][0]
        
        # 备用 play_addr
        play_addr = video_item.get("play_addr", {})
        if play_addr and play_addr.get("url_list"):
            return play_addr["url_list"][0]
        
        return ""
    
    def _extract_video_play_url(self, aweme_detail: Dict) -> str:
        """
        提取视频播放页链接

        Args:
            aweme_detail (Dict): 抖音视频

        Returns:
            str: 视频播放页链接
        """
        aweme_id = aweme_detail.get("aweme_id", "")
        if aweme_id:
            return f"https://www.douyin.com/video/{aweme_id}"
        return ""
    
    def _extract_content_cover_url(self, aweme_detail: Dict) -> str:
        """
        提取视频封面地址

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            str: 视频封面地址
        """
        video_item = aweme_detail.get("video", {})
        
        # 优先使用 cover
        cover = video_item.get("cover", {})
        if cover and cover.get("url_list"):
            return cover["url_list"][0]
        
        # 备用 origin_cover
        origin_cover = video_item.get("origin_cover", {})
        if origin_cover and origin_cover.get("url_list"):
            return origin_cover["url_list"][0]
        
        return ""
    
    def _extract_author_info(self, aweme_detail: Dict) -> Dict:
        """
        提取作者信息

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            Dict: 作者信息
        """
        author = aweme_detail.get("author", {})
        return {
            "author_id": author.get("uid", ""),
            "author_name": author.get("nickname", ""),
            "author_nickname": author.get("nickname", ""),
            "author_avatar": author.get("avatar_thumb", {}).get("url_list", [""])[0] if author.get("avatar_thumb") else "",
            "author_signature": author.get("signature", ""),
            "author_unique_id": author.get("unique_id", ""),
            "author_sec_uid": author.get("sec_uid", ""),
            "author_short_id": author.get("short_id", "")
        }
    
    def _extract_video_info(self, aweme_detail: Dict) -> Dict:
        """
        提取视频信息

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            Dict: 视频信息
        """
        video_item = aweme_detail.get("video", {})
        return {
            "video_url": self._extract_video_download_url(aweme_detail),
            "video_download_url": self._extract_video_download_url(aweme_detail),
            "video_play_url": self._extract_video_play_url(aweme_detail),
            "cover_url": self._extract_content_cover_url(aweme_detail),
            "file_size": video_item.get("data_size", 0),
            "duration": video_item.get("duration", 0)
        }
    
    def _flatten_douyin_data(self, content_item: Dict) -> Dict:
        """
        将抖音原始数据扁平化为统一表结构

        Args:
            content_item (Dict): 抖音原始数据

        Returns:
            Dict: 扁平化后的数据
        """
        # 🆕 修复：确保source_keyword正确传递
        source_keyword = content_item.get("source_keyword", "")
        if not source_keyword:
            # 如果没有直接传递，尝试从全局变量获取
            from var import source_keyword_var
            source_keyword = source_keyword_var.get()
        
        # 基础信息
        flattened = {
            "content_id": content_item.get("aweme_id", ""),
            "platform": "douyin",
            "content_type": "video",
            "task_id": content_item.get("task_id", ""),
            "source_keyword": source_keyword,  # 🆕 修复：确保source_keyword正确设置
            
            # 内容信息
            "title": content_item.get("desc", ""),
            "description": content_item.get("desc", ""),
            "content": content_item.get("desc", ""),
            # 🆕 修复：将10位时间戳转换为13位时间戳
            "create_time": content_item.get("create_time", 0) * 1000 if content_item.get("create_time", 0) < 1000000000000 else content_item.get("create_time", 0),
            "publish_time": content_item.get("create_time", 0) * 1000 if content_item.get("create_time", 0) < 1000000000000 else content_item.get("create_time", 0),
            "update_time": content_item.get("create_time", 0) * 1000 if content_item.get("create_time", 0) < 1000000000000 else content_item.get("create_time", 0),
            
            # 统计信息
            "like_count": content_item.get("statistics", {}).get("digg_count", 0),
            "comment_count": content_item.get("statistics", {}).get("comment_count", 0),
            "share_count": content_item.get("statistics", {}).get("share_count", 0),
            "collect_count": content_item.get("statistics", {}).get("collect_count", 0),
            "view_count": content_item.get("statistics", {}).get("play_count", 0),
            
            # 状态信息
            "is_favorite": content_item.get("is_favorite", False),
            "is_deleted": content_item.get("is_deleted", False),
            "is_private": content_item.get("is_private", False),
            "is_original": content_item.get("is_original", False),
            
            # 存储信息
            "storage_type": "url_only",
            "raw_data": json.dumps(content_item, ensure_ascii=False),
            
            # 时间戳
            "add_ts": utils.get_current_timestamp(),
            "last_modify_ts": utils.get_current_timestamp(),
            
            # 作者信息
            "author_id": content_item.get("author", {}).get("uid", ""),
            "author_name": content_item.get("author", {}).get("nickname", ""),
            "author_nickname": content_item.get("author", {}).get("nickname", ""),
            "author_avatar": content_item.get("author", {}).get("avatar_thumb", {}).get("url_list", [""])[0] if content_item.get("author", {}).get("avatar_thumb") else "",
            "author_signature": content_item.get("author", {}).get("signature", ""),
            "author_unique_id": content_item.get("author", {}).get("unique_id", ""),
            "author_sec_uid": content_item.get("author", {}).get("sec_uid", ""),
            "author_short_id": content_item.get("author", {}).get("short_id", ""),
            
            # 媒体信息
            "cover_url": self._extract_content_cover_url(content_item),
            "video_url": self._extract_video_play_url(content_item),
            "video_download_url": self._extract_video_download_url(content_item),
            "video_play_url": self._extract_video_play_url(content_item),
            "video_share_url": self._extract_video_play_url(content_item),
            
            # 位置信息
            "ip_location": content_item.get("ip_location", ""),
            "location": content_item.get("location", ""),
            
            # 标签和分类
            "tags": json.dumps(content_item.get("tag_list", []), ensure_ascii=False),
            "categories": json.dumps([], ensure_ascii=False),
            "topics": json.dumps(content_item.get("cha_list", []), ensure_ascii=False),
            
            # 扩展信息
            "metadata": json.dumps({}, ensure_ascii=False),
            "extra_info": json.dumps({}, ensure_ascii=False)
        }
        
        return flattened

    async def store_content(self, content_item: Dict):
        """
        Douyin content DB storage implementation
        Args:
            content_item: content item dict

        Returns:

        """
        from .douyin_store_sql import (add_new_content,
                                       query_content_by_content_id,
                                       update_content_by_content_id)
        
        # 扁平化数据
        flattened_data = self._flatten_douyin_data(content_item)
        content_id = flattened_data.get("content_id")
        
        if not content_id:
            utils.logger.error("内容ID为空，跳过存储")
            return
        
        # 查询是否已存在
        existing_content: Dict = await query_content_by_content_id(content_id=content_id)
        task_id = content_item.get("task_id")
        
        if not existing_content:
            # 新增内容
            await add_new_content(flattened_data, task_id=task_id)
            utils.logger.info(f"✅ 新增抖音内容: {content_id}")
        else:
            # 更新内容
            await update_content_by_content_id(content_id, content_item=flattened_data)
            utils.logger.info(f"✅ 更新抖音内容: {content_id}")

    async def store_comment(self, comment_item: Dict):
        """
        Douyin content DB storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        from .douyin_store_sql import (add_new_comment,
                                       query_comment_by_comment_id,
                                       update_comment_by_comment_id)
        
        # 扁平化评论数据
        flattened_comment = {
            "comment_id": comment_item.get("cid", ""),
            "content_id": comment_item.get("aweme_id", ""),
            "platform": "douyin",
            "content": comment_item.get("text", ""),
            "text": comment_item.get("text", ""),
            "author_id": comment_item.get("user", {}).get("uid", ""),
            "author_name": comment_item.get("user", {}).get("nickname", ""),
            "author_nickname": comment_item.get("user", {}).get("nickname", ""),
            "author_avatar": comment_item.get("user", {}).get("avatar_thumb", {}).get("url_list", [""])[0] if comment_item.get("user", {}).get("avatar_thumb") else "",
            "like_count": comment_item.get("digg_count", 0),
            "reply_count": comment_item.get("reply_comment_total", 0),
            "create_time": comment_item.get("create_time", 0),
            "is_deleted": comment_item.get("is_deleted", False),
            "is_hidden": comment_item.get("is_hidden", False),
            "is_top": comment_item.get("is_top", False),
            "raw_data": json.dumps(comment_item, ensure_ascii=False),
            "add_ts": utils.get_current_timestamp(),
            "last_modify_ts": utils.get_current_timestamp()
        }
        
        comment_id = flattened_comment.get("comment_id")
        if not comment_id:
            utils.logger.error("评论ID为空，跳过存储")
            return
        
        comment_detail: Dict = await query_comment_by_comment_id(comment_id=comment_id)
        if not comment_detail:
            await add_new_comment(flattened_comment)
            utils.logger.info(f"✅ 新增抖音评论: {comment_id}")
        else:
            await update_comment_by_comment_id(comment_id, comment_item=flattened_comment)
            utils.logger.info(f"✅ 更新抖音评论: {comment_id}")

    async def store_creator(self, creator: Dict):
        """
        Douyin content DB storage implementation
        Args:
            creator: creator dict

        Returns:

        """
        from .douyin_store_sql import (add_new_creator,
                                       query_creator_by_user_id,
                                       update_creator_by_user_id)
        user_id = creator.get("user_id")
        user_detail: Dict = await query_creator_by_user_id(user_id)
        if not user_detail:
            creator["add_ts"] = utils.get_current_timestamp()
            await add_new_creator(creator)
        else:
            await update_creator_by_user_id(user_id, creator)

class DouyinJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/douyin/json"
    words_store_path: str = "data/douyin/words"

    lock = asyncio.Lock()
    file_count: int = calculate_number_of_files(json_store_path)
    WordCloud = words.AsyncWordCloudGenerator()

    def make_save_file_name(self, store_type: str) -> (str,str):
        """
        make save file name by store type
        Args:
            store_type: Save type contains content and comments（contents | comments）

        Returns:

        """

        return (
            f"{self.json_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.json",
            f"{self.words_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}"
        )
    async def save_data_to_json(self, save_item: Dict, store_type: str):
        """
        Below is a simple way to save it in json format.
        Args:
            save_item: save content dict info
            store_type: Save type contains content and comments（contents | comments）

        Returns:

        """
        pathlib.Path(self.json_store_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.words_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name,words_file_name_prefix = self.make_save_file_name(store_type=store_type)
        save_data = []

        async with self.lock:
            if os.path.exists(save_file_name):
                async with aiofiles.open(save_file_name, 'r', encoding='utf-8') as file:
                    save_data = json.loads(await file.read())

            save_data.append(save_item)
            async with aiofiles.open(save_file_name, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(save_data, ensure_ascii=False))

            if config.ENABLE_GET_COMMENTS and config.ENABLE_GET_WORDCLOUD:
                try:
                    await self.WordCloud.generate_word_frequency_and_cloud(save_data, words_file_name_prefix)
                except:
                    pass

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.save_data_to_json(content_item, "contents")

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.save_data_to_json(comment_item, "comments")


    async def store_creator(self, creator: Dict):
        """
        Douyin creator CSV storage implementation
        Args:
            creator: creator item dict

        Returns:

        """
        await self.save_data_to_json(save_item=creator, store_type="creator")


class DouyinRedisStoreImplement(AbstractStore):
    """抖音Redis存储实现"""
    
    def __init__(self, redis_callback=None):
        self.redis_callback = redis_callback
        self.collected_data = []
    
    def clear_collected_data(self):
        """清空收集的数据，用于新的爬取任务"""
        self.collected_data.clear()
        utils.logger.info("[DouyinRedisStore] 已清空收集的数据，准备新的爬取任务")  # 收集爬取到的数据
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.redis_callback = callback
    
    def _extract_video_download_url(self, aweme_detail: Dict) -> str:
        """
        提取视频下载地址

        Args:
            aweme_detail (Dict): 抖音视频

        Returns:
            str: 视频下载地址
        """
        # 优先使用 download_addr
        video_item = aweme_detail.get("video", {})
        download_addr = video_item.get("download_addr", {})
        if download_addr and download_addr.get("url_list"):
            return download_addr["url_list"][0]
        
        # 备用 play_addr
        play_addr = video_item.get("play_addr", {})
        if play_addr and play_addr.get("url_list"):
            return play_addr["url_list"][0]
        
        return ""
    
    def _extract_video_play_url(self, aweme_detail: Dict) -> str:
        """
        提取视频播放页链接

        Args:
            aweme_detail (Dict): 抖音视频

        Returns:
            str: 视频播放页链接
        """
        aweme_id = aweme_detail.get("aweme_id", "")
        if aweme_id:
            return f"https://www.douyin.com/video/{aweme_id}"
            return ""
    
    def _extract_content_cover_url(self, aweme_detail: Dict) -> str:
        """
        提取视频封面地址

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            str: 视频封面地址
        """
        video_item = aweme_detail.get("video", {})
        
        # 优先使用 cover
        cover = video_item.get("cover", {})
        if cover and cover.get("url_list"):
            return cover["url_list"][0]
        
        # 备用 origin_cover
        origin_cover = video_item.get("origin_cover", {})
        if origin_cover and origin_cover.get("url_list"):
            return origin_cover["url_list"][0]

        return ""
    
    async def store_content(self, content_item: Dict):
        """
        抖音内容Redis存储实现（标准化字段）
        Args:
            content_item: 视频内容字典
        """
        # 兼容不同字段来源
        aweme_id = content_item.get("aweme_id") or content_item.get("video_id")
        user_info = content_item.get("author", {})
        interact_info = content_item.get("statistics", {})

        processed_content = {
            "aweme_id": aweme_id,
            "aweme_url": self._extract_video_play_url(content_item),  # 必须
            "download_url": self._extract_video_download_url(content_item),  # 有则存
            "cover_url": self._extract_content_cover_url(content_item),
            "title": content_item.get("desc", "") or content_item.get("title", ""),
            "author_id": user_info.get("uid") or content_item.get("author_id", ""),
            "author_name": user_info.get("nickname") or content_item.get("author_name", ""),
            "avatar": user_info.get("avatar_thumb", {}).get("url_list", [""])[0] if user_info.get("avatar_thumb") else "",
            "create_time": content_item.get("create_time"),
            "liked_count": str(interact_info.get("digg_count") or content_item.get("liked_count", "")),
            "comment_count": str(interact_info.get("comment_count") or content_item.get("comment_count", "")),
            "collected_count": str(interact_info.get("collect_count") or content_item.get("collected_count", "")),
            "share_count": str(interact_info.get("share_count") or content_item.get("share_count", "")),
            "platform": "dy",
            "source_keyword": content_item.get("source_keyword", ""),
            "task_id": content_item.get("task_id", ""),
            "stored_at": content_item.get("stored_at", ""),
        }

        # 🆕 修复：检查是否已存在相同ID的数据，避免重复存储
        existing_ids = [item.get("aweme_id") for item in self.collected_data]
        if aweme_id not in existing_ids:
            # 收集数据用于返回
            self.collected_data.append(processed_content)
            utils.logger.debug(f"🆕 [DouyinRedisStore] 新增数据: {aweme_id}")
        else:
            utils.logger.debug(f"🆕 [DouyinRedisStore] 跳过重复数据: {aweme_id}")

        # 日志输出
        utils.logger.info(f"🎬 [DouyinRedisStore] 视频ID: {aweme_id}, 标题: {processed_content.get('title')}")
        utils.logger.info(f"🔗 [DouyinRedisStore] 播放页链接: {processed_content.get('aweme_url')}")
        utils.logger.info(f"📥 [DouyinRedisStore] 下载链接: {processed_content.get('download_url')}")

        # 同时存储到数据库
        try:
            from .douyin_store_sql import (add_new_content,
                                           query_content_by_content_id,
                                           update_content_by_content_id)
            
            aweme_detail: Dict = await query_content_by_content_id(content_id=aweme_id)
            task_id = content_item.get("task_id")
            if not aweme_detail:
                # 使用处理过的数据存储到数据库，确保URL正确
                db_content_item = content_item.copy()
                db_content_item.update({
                    "aweme_url": processed_content.get("aweme_url"),
                    "download_url": processed_content.get("download_url"),
                    "video_download_url": processed_content.get("download_url"),  # 确保映射到video_download_url字段
                    "video_url": processed_content.get("aweme_url"),  # 确保映射到video_url字段
                    "video_play_url": processed_content.get("aweme_url"),  # 确保映射到video_play_url字段
                    "add_ts": utils.get_current_timestamp()
                })
                if db_content_item.get("title") or db_content_item.get("desc"):
                    await add_new_content(db_content_item, task_id=task_id)
                    utils.logger.info(f"✅ [DouyinRedisStore] 数据已存储到数据库: {aweme_id}")
            else:
                # 更新时也使用处理过的URL
                update_content_item = content_item.copy()
                update_content_item.update({
                    "aweme_url": processed_content.get("aweme_url"),
                    "download_url": processed_content.get("download_url"),
                    "video_download_url": processed_content.get("download_url"),  # 确保映射到video_download_url字段
                    "video_url": processed_content.get("aweme_url"),  # 确保映射到video_url字段
                    "video_play_url": processed_content.get("aweme_url"),  # 确保映射到video_play_url字段
                })
                await update_content_by_content_id(aweme_id, content_item=update_content_item)
                utils.logger.info(f"✅ [DouyinRedisStore] 数据已更新到数据库: {aweme_id}")
        except Exception as e:
            utils.logger.error(f"❌ [DouyinRedisStore] 数据库存储失败: {aweme_id}, 错误: {e}")

        # 存储到Redis
        if self.redis_callback:
            await self.redis_callback("dy", processed_content, "video")

    async def store_comment(self, comment_item: Dict):
        """
        抖音评论Redis存储实现
        Args:
            comment_item: 评论字典
        """
        if self.redis_callback:
            await self.redis_callback("dy", comment_item, "comment")

    async def store_creator(self, creator: Dict):
        """
        抖音创作者Redis存储实现
        Args:
            creator: 创作者字典
        """
        if self.redis_callback:
            await self.redis_callback("dy", creator, "creator")

    async def save_creator(self, user_id: str, creator: Dict):
        """
        保存抖音创作者 - 兼容性方法
        Args:
            user_id: 用户ID
            creator: 创作者数据
        """
        try:
            # 构建统一格式的创作者数据
            unified_creator = {
                "creator_id": user_id,
                "platform": "dy",
                "author_id": user_id,
                "author_name": creator.get('nickname', ''),
                "author_nickname": creator.get('nickname', ''),
                "author_avatar": creator.get('avatar_thumb', {}).get('url_list', [''])[0] if creator.get('avatar_thumb') else '',
                "author_signature": creator.get('signature', ''),
                "gender": creator.get('gender', ''),
                "ip_location": creator.get('location', ''),
                "follows": creator.get('following_count', 0),
                "fans": creator.get('follower_count', 0),
                "interaction": creator.get('total_favorited', 0),
                "tags": json.dumps(creator.get('tags', {}), ensure_ascii=False),
                "raw_data": json.dumps(creator, ensure_ascii=False),
                "add_ts": utils.get_current_timestamp(),
                "last_modify_ts": utils.get_current_timestamp()
            }
            
            # 调用store_creator方法
            await self.store_creator(unified_creator)
            
            utils.logger.info(f"✅ [DouyinRedisStore] 创作者数据已保存: {user_id}")
            
        except Exception as e:
            utils.logger.error(f"❌ [DouyinRedisStore] 保存创作者数据失败: {user_id}, 错误: {e}")

    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        Returns:
            List[Dict]: 内容列表
        """
        utils.logger.info(f"[DouyinRedisStore] 获取存储内容 - 共收集到 {len(self.collected_data)} 条数据")
        return self.collected_data