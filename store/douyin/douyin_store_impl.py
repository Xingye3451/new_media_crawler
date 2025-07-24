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
        aweme_id = content_item.get("aweme_id")
        aweme_detail: Dict = await query_content_by_content_id(content_id=aweme_id)
        task_id = content_item.get("task_id")
        if not aweme_detail:
            content_item["add_ts"] = utils.get_current_timestamp()
            if content_item.get("title"):
                await add_new_content(content_item, task_id=task_id)
        else:
            await update_content_by_content_id(aweme_id, content_item=content_item)

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
        comment_id = comment_item.get("comment_id")
        comment_detail: Dict = await query_comment_by_comment_id(comment_id=comment_id)
        if not comment_detail:
            comment_item["add_ts"] = utils.get_current_timestamp()
            await add_new_comment(comment_item)
        else:
            await update_comment_by_comment_id(comment_id, comment_item=comment_item)

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
        self.collected_data = []  # 收集爬取到的数据
    
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
        video_item = aweme_detail.get("video", {})
        url_h264_list = video_item.get("play_addr_h264", {}).get("url_list", [])
        url_256_list = video_item.get("play_addr_256", {}).get("url_list", [])
        url_list = video_item.get("play_addr", {}).get("url_list", [])
        actual_url_list = url_h264_list or url_256_list or url_list
        if not actual_url_list or len(actual_url_list) < 2:
            return ""
        return actual_url_list[-1]
    
    def _extract_content_cover_url(self, aweme_detail: Dict) -> str:
        """
        提取视频封面地址

        Args:
            aweme_detail (Dict): 抖音内容详情

        Returns:
            str: 视频封面地址
        """
        res_cover_url = ""

        video_item = aweme_detail.get("video", {})
        raw_cover_url_list = (
                video_item.get("raw_cover", {}) or video_item.get("origin_cover", {})
        ).get("url_list", [])
        if raw_cover_url_list and len(raw_cover_url_list) > 1:
            res_cover_url = raw_cover_url_list[1]

        return res_cover_url
    
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
            "aweme_url": f"https://www.douyin.com/video/{aweme_id}",  # 必须
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

        # 收集数据用于返回
        self.collected_data.append(processed_content)

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
                content_item["add_ts"] = utils.get_current_timestamp()
                if content_item.get("title") or content_item.get("desc"):
                    await add_new_content(content_item, task_id=task_id)
                    utils.logger.info(f"✅ [DouyinRedisStore] 数据已存储到数据库: {aweme_id}")
            else:
                await update_content_by_content_id(aweme_id, content_item=content_item)
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

    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        Returns:
            List[Dict]: 内容列表
        """
        utils.logger.info(f"[DouyinRedisStore] 获取存储内容 - 共收集到 {len(self.collected_data)} 条数据")
        return self.collected_data