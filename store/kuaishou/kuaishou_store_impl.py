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
# @Desc    : 快手存储实现类 - 使用统一存储系统

import asyncio
import csv
import json
import os
import pathlib
from typing import Dict, List, Tuple

import aiofiles

import config
from base.base_crawler import AbstractStore
from tools import utils, words
from var import crawler_type_var, source_keyword_var
from store.unified_store_impl import UnifiedStoreImplement


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


class KuaishouCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/kuaishou"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/kuaishou/search_comments_20240114.csv ...

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
        Kuaishou content CSV storage implementation
        Args:
            content_item: video item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        Kuaishou comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")


class KuaishouDbStoreImplement(AbstractStore):
    """快手数据库存储实现 - 使用统一存储系统"""
    
    def __init__(self):
        self.unified_store = UnifiedStoreImplement("kuaishou")
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    async def store_content(self, content_item: Dict):
        """
        快手内容数据库存储实现
        Args:
            content_item: 内容字典

        Returns:

        """
        await self.unified_store.store_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        快手评论数据库存储实现
        Args:
            comment_item: 评论字典

        Returns:

        """
        await self.unified_store.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict):
        """
        快手创作者数据库存储实现
        Args:
            creator_item: 创作者字典

        Returns:

        """
        await self.unified_store.store_creator(creator_item)

    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        Returns:
            List[Dict]: 内容列表
        """
        return await self.unified_store.get_all_content()

    async def update_kuaishou_video(self, video_item: Dict, task_id: str = None):
        """
        快手视频内容更新（兼容旧接口）
        Args:
            video_item: 视频详情字典
            task_id: 任务ID，可选
        """
        photo_info: Dict = video_item.get("photo", {})
        video_id = photo_info.get("id")
        if not video_id:
            return
        user_info = video_item.get("author", {})
        save_content_item = {
            "video_id": video_id,
            "video_type": str(video_item.get("type")),
            "title": photo_info.get("caption", "")[:500],
            "desc": photo_info.get("caption", ""),
            "user_id": user_info.get("id"),
            "nickname": user_info.get("name"),
            "avatar": user_info.get("headerUrl"),
            "liked_count": photo_info.get("likeCount", 0),
            "comment_count": photo_info.get("commentCount", 0),
            "share_count": photo_info.get("shareCount", 0),
            "collect_count": photo_info.get("collectCount", 0),
            "viewd_count": photo_info.get("viewCount", 0),
            "video_cover_url": photo_info.get("coverUrl"),  # 封面图片
            "video_url": photo_info.get("photoUrl"),  # 视频播放链接
            "video_play_url": photo_info.get("photoUrl"),  # 视频播放链接
            "video_download_url": photo_info.get("photoUrl"),  # 视频下载链接（初始值）
            "create_time": photo_info.get("timestamp"),
            "last_modify_ts": photo_info.get("timestamp"),
            "raw_data": json.dumps(video_item, ensure_ascii=False),
            # 🆕 新增字段
            "author_signature": user_info.get("signature"),
            "author_unique_id": user_info.get("id"),
            "author_sec_uid": user_info.get("secUid"),
            "author_short_id": user_info.get("shortId"),
            "video_share_url": photo_info.get("shareUrl"),
            "image_urls": json.dumps(photo_info.get("coverUrls", []), ensure_ascii=False),
            "audio_url": photo_info.get("audioUrl"),
            "file_urls": json.dumps(photo_info.get("fileUrls", []), ensure_ascii=False),
            "ip_location": photo_info.get("ipLocation"),
            "location": photo_info.get("location"),
            "tags": json.dumps(photo_info.get("tags", []), ensure_ascii=False),
            "categories": json.dumps(photo_info.get("categories", []), ensure_ascii=False),
            "topics": json.dumps(photo_info.get("topics", []), ensure_ascii=False),
            "is_favorite": 1 if photo_info.get("isFavorite") else 0,
            "is_deleted": 1 if photo_info.get("isDeleted") else 0,
            "is_private": 1 if photo_info.get("isPrivate") else 0,
            "is_original": 1 if photo_info.get("isOriginal") else 0,
            "minio_url": photo_info.get("minioUrl"),
            "local_path": photo_info.get("localPath"),
            # 添加必需字段
            "source_keyword": source_keyword_var.get(),
            "platform": "kuaishou",
            "task_id": task_id,
        }
        
        # 🆕 优先使用高清视频下载链接
        if "manifest" in photo_info:
            manifest = photo_info.get("manifest", {})
            if "adaptationSet" in manifest and manifest["adaptationSet"]:
                adaptation_set = manifest["adaptationSet"][0]
                if "representation" in adaptation_set and adaptation_set["representation"]:
                    representation = adaptation_set["representation"][0]
                    hd_video_url = representation.get("url")
                    if hd_video_url:
                        save_content_item["video_download_url"] = hd_video_url
                        utils.logger.info(f"[KuaishouStore] 使用高清视频下载链接: {hd_video_url[:100]}...")
        
        # 备用：使用videoResource中的H264链接
        if "videoResource" in photo_info:
            video_resource = photo_info.get("videoResource", {})
            if "h264" in video_resource:
                h264 = video_resource.get("h264", {})
                if "adaptationSet" in h264 and h264["adaptationSet"]:
                    adaptation_set = h264["adaptationSet"][0]
                    if "representation" in adaptation_set and adaptation_set["representation"]:
                        representation = adaptation_set["representation"][0]
                        h264_video_url = representation.get("url")
                        if h264_video_url and save_content_item["video_download_url"] == photo_info.get("photoUrl"):
                            save_content_item["video_download_url"] = h264_video_url
                            utils.logger.info(f"[KuaishouStore] 使用H264视频下载链接: {h264_video_url[:100]}...")
        
        utils.logger.info(f"[KuaishouStore] 最终视频下载链接: {save_content_item['video_download_url'][:100]}...")
        
        await self.unified_store.store_content(save_content_item)


class KuaishouJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/kuaishou/json"
    words_store_path: str = "data/kuaishou/words"

    lock = asyncio.Lock()
    file_count: int = calculate_number_of_files(json_store_path)
    WordCloud = words.AsyncWordCloudGenerator()

    def make_save_file_name(self, store_type: str) -> Tuple[str, str]:
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


    async def store_creator(self, creator_item: Dict):
        """
        Kuaishou creator JSON storage implementation
        Args:
            creator_item: creator item dict

        Returns:

        """
        await self.save_data_to_json(save_item=creator_item, store_type="creator")


class KuaishouRedisStoreImplement(AbstractStore):
    """快手Redis存储实现 - 使用统一存储系统"""
    
    def __init__(self, redis_callback=None):
        self.unified_store = UnifiedStoreImplement("kuaishou", redis_callback)
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    async def store_content(self, content_item: Dict):
        """
        快手内容Redis存储实现
        Args:
            content_item: 内容字典
        """
        await self.unified_store.store_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        快手评论Redis存储实现
        Args:
            comment_item: 评论字典
        """
        await self.unified_store.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict):
        """
        快手创作者Redis存储实现
        Args:
            creator_item: 创作者字典
        """
        await self.unified_store.store_creator(creator_item)

    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        Returns:
            List[Dict]: 内容列表
        """
        return await self.unified_store.get_all_content()
        await self.save_data_to_json(creator, "creator")