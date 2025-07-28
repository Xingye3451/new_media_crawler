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
# @Desc    : B站存储实现类 - 使用统一存储系统

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


class BilibiliCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/bilibili"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/bilibili/search_comments_20240114.csv ...

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
        Bilibili content CSV storage implementation
        Args:
            content_item: video item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        Bilibili comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")


class BilibiliDbStoreImplement(AbstractStore):
    """B站数据库存储实现 - 使用统一存储系统"""
    
    def __init__(self):
        self.unified_store = UnifiedStoreImplement("bilibili")
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    async def store_content(self, content_item: Dict):
        """
        B站内容数据库存储实现
        Args:
            content_item: 内容字典

        Returns:

        """
        await self.unified_store.store_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        B站评论数据库存储实现
        Args:
            comment_item: 评论字典

        Returns:

        """
        await self.unified_store.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict):
        """
        B站创作者数据库存储实现
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


class BilibiliJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/bilibili/json"
    words_store_path: str = "data/bilibili/words"

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


    async def store_creator(self, creator_item: Dict):
        """
        Bilibili creator JSON storage implementation
        Args:
            creator_item: creator item dict

        Returns:

        """
        await self.save_data_to_json(save_item=creator_item, store_type="creator")


class BilibiliRedisStoreImplement(AbstractStore):
    """B站Redis存储实现 - 使用统一存储系统"""
    
    def __init__(self, redis_callback=None):
        self.unified_store = UnifiedStoreImplement("bilibili", redis_callback)
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    async def store_content(self, content_item: Dict):
        """
        B站内容Redis存储实现
        Args:
            content_item: 内容字典
        """
        await self.unified_store.store_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        B站评论Redis存储实现
        Args:
            comment_item: 评论字典
        """
        await self.unified_store.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict):
        """
        B站创作者Redis存储实现
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
