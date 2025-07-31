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
import time
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

    async def update_bilibili_video(self, video_item: Dict, task_id: str = None):
        """
        B站视频内容更新（兼容旧接口）
        Args:
            video_item: 视频详情字典
            task_id: 任务ID，可选
        """
        import json
        from var import source_keyword_var
        
        # 提取视频基本信息 - 根据B站实际数据结构调整
        video_info = video_item.get("View", video_item)  # 兼容两种数据结构
        video_id = video_info.get("bvid") or video_info.get("aid")
        if not video_id:
            return
        
        # 提取UP主信息
        owner_info = video_info.get("owner", {})
        
        # 提取统计信息
        stat_info = video_info.get("stat", {})
        
        # 提取视频播放地址和下载地址
        video_play_url = ""
        video_download_url = ""
        
        # 从原始数据中提取播放地址（如果存在）
        utils.logger.info(f"[BilibiliStore] 开始提取播放地址，原始数据键: {list(video_item.keys())}")
        
        # 检查多种可能的数据结构
        durl_list = []
        
        # 1. 直接从video_item中获取durl
        if "durl" in video_item:
            durl_list = video_item.get("durl", [])
            utils.logger.info(f"[BilibiliStore] 从video_item.durl获取到 {len(durl_list)} 个URL")
        
        # 2. 从data.durl中获取
        elif "data" in video_item and "durl" in video_item["data"]:
            durl_list = video_item["data"].get("durl", [])
            utils.logger.info(f"[BilibiliStore] 从video_item.data.durl获取到 {len(durl_list)} 个URL")
        
        # 3. 从result.durl中获取
        elif "result" in video_item and "durl" in video_item["result"]:
            durl_list = video_item["result"].get("durl", [])
            utils.logger.info(f"[BilibiliStore] 从video_item.result.durl获取到 {len(durl_list)} 个URL")
        
        if durl_list:
            # 选择最大尺寸的视频URL
            max_size = -1
            best_url = ""
            
            for durl in durl_list:
                size = durl.get("size", 0)
                url = durl.get("url", "")
                utils.logger.info(f"[BilibiliStore] 检查URL: size={size}, url={url[:50]}...")
                
                if size > max_size and url:
                    max_size = size
                    best_url = url
            
            if best_url:
                video_download_url = best_url
                video_play_url = best_url
                utils.logger.info(f"[BilibiliStore] 选择最佳URL: size={max_size}, url={best_url[:50]}...")
                
                # 如果获取到了视频URL，尝试处理403问题
                try:
                    from services.bilibili_video_service import bilibili_video_service
                    processed_url = await bilibili_video_service.get_video_url_with_retry(best_url)
                    if processed_url:
                        video_download_url = processed_url
                        video_play_url = processed_url
                        utils.logger.info(f"[BilibiliStore] 成功处理视频URL，避免403错误")
                except Exception as e:
                    utils.logger.warning(f"[BilibiliStore] 处理视频URL失败: {e}")
            else:
                utils.logger.warning(f"[BilibiliStore] 未找到有效的视频URL")
        else:
            utils.logger.warning(f"[BilibiliStore] 未找到durl数据")
        
        # 构建存储数据 - 使用统一存储系统的字段映射
        save_content_item = {
            "content_id": video_id,  # 使用bvid作为content_id
            "platform": "bilibili",
            "content_type": "video",
            "title": video_info.get("title", "")[:500],
            "description": video_info.get("desc", ""),
            "content": video_info.get("desc", ""),
            "source_keyword": source_keyword_var.get(),
            "create_time": video_info.get("ctime"),
            "publish_time": video_info.get("ctime"),
            "update_time": video_info.get("ctime"),
            "author_id": owner_info.get("mid"),
            "author_name": owner_info.get("name"),
            "author_nickname": owner_info.get("name"),
            "author_avatar": owner_info.get("face"),
            "author_signature": owner_info.get("sign"),
            "author_unique_id": owner_info.get("mid"),
            "author_sec_uid": owner_info.get("sec_uid"),
            "author_short_id": owner_info.get("short_id"),
            "like_count": stat_info.get("like", 0),
            "comment_count": stat_info.get("reply", 0),
            "share_count": stat_info.get("share", 0),
            "collect_count": stat_info.get("favorite", 0),
            "view_count": stat_info.get("view", 0),
            "cover_url": video_info.get("pic"),
            "video_url": f"https://www.bilibili.com/video/{video_id}",
            "video_play_url": video_play_url,
            "video_download_url": video_download_url,
            "video_share_url": f"https://www.bilibili.com/video/{video_id}",
            "image_urls": json.dumps([video_info.get("pic")] if video_info.get("pic") else [], ensure_ascii=False),
            "audio_url": video_info.get("audio_url", ""),
            "file_urls": json.dumps([video_download_url] if video_download_url else [], ensure_ascii=False),
            "ip_location": video_info.get("location", ""),
            "location": video_info.get("location", ""),
            "tags": json.dumps(video_info.get("tags", []), ensure_ascii=False),
            "categories": json.dumps([video_info.get("tname")] if video_info.get("tname") else [], ensure_ascii=False),
            "topics": json.dumps(video_info.get("topics", []), ensure_ascii=False),
            "is_favorite": 1 if video_info.get("is_favorite") else 0,
            "is_deleted": 1 if video_info.get("is_deleted") else 0,
            "is_private": 1 if video_info.get("is_private") else 0,
            "is_original": 1 if video_info.get("is_original") else 0,
            "minio_url": video_info.get("minio_url", ""),
            "local_path": video_info.get("local_path", ""),
            "file_size": video_info.get("file_size", 0),
            "storage_type": video_info.get("storage_type", "remote"),
            "metadata": json.dumps({
                "duration": video_info.get("duration", 0),
                "dimension": video_info.get("dimension", {}),
                "rights": video_info.get("rights", {}),
                "staff": video_info.get("staff", []),
                "subtitle": video_info.get("subtitle", {}),
                "redirect_url": video_info.get("redirect_url", ""),
                "dynamic": video_info.get("dynamic", ""),
                "cid": video_info.get("cid", 0),
                "state": video_info.get("state", 0),
                "mission_id": video_info.get("mission_id", 0),
                "is_360": video_info.get("is_360", 0),
                "is_imax": video_info.get("is_imax", 0),
                "is_steins_gate": video_info.get("is_steins_gate", 0),
                "is_360_2": video_info.get("is_360_2", 0),
                "is_imax_2": video_info.get("is_imax_2", 0),
                "is_steins_gate_2": video_info.get("is_steins_gate_2", 0),
                "is_360_3": video_info.get("is_360_3", 0),
                "is_imax_3": video_info.get("is_imax_3", 0),
                "is_steins_gate_3": video_info.get("is_steins_gate_3", 0),
                "is_360_4": video_info.get("is_360_4", 0),
                "is_imax_4": video_info.get("is_imax_4", 0),
                "is_steins_gate_4": video_info.get("is_steins_gate_4", 0),
                "is_360_5": video_info.get("is_360_5", 0),
                "is_imax_5": video_info.get("is_imax_5", 0),
                "is_steins_gate_5": video_info.get("is_steins_gate_5", 0),
                "is_360_6": video_info.get("is_360_6", 0),
                "is_imax_6": video_info.get("is_imax_6", 0),
                "is_steins_gate_6": video_info.get("is_steins_gate_6", 0),
                "is_360_7": video_info.get("is_360_7", 0),
                "is_imax_7": video_info.get("is_imax_7", 0),
                "is_steins_gate_7": video_info.get("is_steins_gate_7", 0),
                "is_360_8": video_info.get("is_360_8", 0),
                "is_imax_8": video_info.get("is_imax_8", 0),
                "is_steins_gate_8": video_info.get("is_steins_gate_8", 0),
                "is_360_9": video_info.get("is_360_9", 0),
                "is_imax_9": video_info.get("is_imax_9", 0),
                "is_steins_gate_9": video_info.get("is_steins_gate_9", 0),
                "is_360_10": video_info.get("is_360_10", 0),
                "is_imax_10": video_info.get("is_imax_10", 0),
                "is_steins_gate_10": video_info.get("is_steins_gate_10", 0),
            }, ensure_ascii=False),
            "raw_data": json.dumps(video_item, ensure_ascii=False),
            "extra_info": json.dumps({
                "owner": owner_info,
                "stat": stat_info,
                "durl": durl_list,
                "task_id": task_id,
                "source_keyword": source_keyword_var.get(),
                "platform": "bilibili",
                "aid": video_info.get("aid"),
                "bvid": video_id,
                "cid": video_info.get("cid"),
            }, ensure_ascii=False),
            "add_ts": int(time.time()),
            "last_modify_ts": int(time.time()),
            "task_id": task_id,
        }
        
        utils.logger.info(f"[BilibiliStore] 处理视频: {video_id}, 标题: {save_content_item['title'][:50]}...")
        
        await self.unified_store.store_content(save_content_item)

    async def update_up_info(self, up_info: Dict, task_id: str = None):
        """
        B站UP主信息更新
        Args:
            up_info: UP主信息字典
            task_id: 任务ID，可选
        """
        import json
        from var import source_keyword_var
        
        # 提取UP主基本信息
        mid = up_info.get("mid")
        if not mid:
            return
        
        # 构建存储数据
        save_content_item = {
            "video_id": f"up_{mid}",  # 使用特殊前缀标识UP主信息
            "video_type": "creator",
            "title": up_info.get("name", "")[:500],
            "desc": up_info.get("sign", ""),
            "user_id": mid,
            "nickname": up_info.get("name"),
            "avatar": up_info.get("face"),
            "liked_count": up_info.get("follower", 0),
            "comment_count": 0,  # UP主信息没有评论数
            "share_count": 0,
            "collect_count": 0,
            "viewd_count": 0,
            "video_cover_url": up_info.get("face"),
            "video_url": f"https://space.bilibili.com/{mid}",
            "video_play_url": "",
            "video_download_url": "",
            "create_time": up_info.get("ctime", 0),
            "last_modify_ts": up_info.get("ctime", 0),
            "raw_data": json.dumps(up_info, ensure_ascii=False),
            # 新增字段
            "author_signature": up_info.get("sign"),
            "author_unique_id": mid,
            "author_sec_uid": up_info.get("sec_uid"),
            "author_short_id": up_info.get("short_id"),
            "video_share_url": f"https://space.bilibili.com/{mid}",
            "image_urls": json.dumps([up_info.get("face")] if up_info.get("face") else [], ensure_ascii=False),
            "audio_url": "",
            "file_urls": json.dumps([], ensure_ascii=False),
            "ip_location": "",
            "location": "",
            "tags": json.dumps([], ensure_ascii=False),
            "categories": json.dumps([], ensure_ascii=False),
            "topics": json.dumps([], ensure_ascii=False),
            "is_favorite": 0,
            "is_deleted": 0,
            "is_private": 0,
            "is_original": 0,
            "minio_url": "",
            "local_path": "",
            # 添加必需字段
            "source_keyword": source_keyword_var.get(),
            "platform": "bilibili",
            "task_id": task_id,
        }
        
        utils.logger.info(f"[BilibiliStore] 处理UP主信息: {mid}, 昵称: {save_content_item['nickname']}")
        
        await self.unified_store.store_content(save_content_item)

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
