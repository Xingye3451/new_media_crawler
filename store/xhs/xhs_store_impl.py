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
# @Desc    : 小红书存储实现类 - 使用统一存储系统

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


class XhsCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/xhs"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/xhs/search_comments_20240114.csv ...

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
        Xhs content CSV storage implementation
        Args:
            content_item: note item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        Xhs comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")


class XhsDbStoreImplement(AbstractStore):
    """小红书数据库存储实现 - 使用统一存储系统"""
    
    def __init__(self):
        self.unified_store = UnifiedStoreImplement("xhs")
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    def _convert_to_timestamp(self, time_value) -> int:
        """
        将时间值转换为时间戳整数
        Args:
            time_value: 时间值，可能是字符串、整数或其他类型
        Returns:
            int: 时间戳整数
        """
        try:
            if time_value is None:
                return 0
            
            # 如果是字符串，尝试解析
            if isinstance(time_value, str):
                # 如果是"time"字符串，返回0
                if time_value == "time":
                    return 0
                # 如果是数字字符串，直接转换
                if time_value.isdigit():
                    return int(time_value)
                # 如果是空字符串，返回0
                if time_value.strip() == "":
                    return 0
                # 其他字符串情况返回0
                return 0
            
            # 如果是数字，直接转换
            if isinstance(time_value, (int, float)):
                return int(time_value)
            
            # 其他情况返回0
            return 0
        except Exception as e:
            utils.logger.warning(f"[XhsDbStoreImplement._convert_to_timestamp] 时间转换失败: {e}, 原始值: {time_value}")
            return 0

    async def store_content(self, content_item: Dict):
        """
        小红书内容数据库存储实现
        Args:
            content_item: 内容字典

        Returns:

        """
        try:
            # 使用UnifiedStoreImplement的store_content方法
            await self.unified_store.store_content(content_item)
                
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement] 存储内容失败: {content_item.get('note_id', '')}, 错误: {e}")
            raise

    async def store_comment(self, comment_item: Dict):
        """
        小红书评论数据库存储实现
        Args:
            comment_item: 评论字典

        Returns:

        """
        try:
            # 使用UnifiedStoreImplement的store_comment方法
            await self.unified_store.store_comment(comment_item)
                
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement] 存储评论失败: {comment_item.get('id', '')}, 错误: {e}")
            raise

    async def store_creator(self, creator_item: Dict):
        """
        小红书创作者数据库存储实现
        Args:
            creator_item: 创作者字典

        Returns:

        """
        try:
            # 暂时跳过创作者存储，因为统一存储模块没有实现
            utils.logger.info(f"[XhsDbStoreImplement] 跳过创作者存储: {creator_item.get('author_id', '')}")
            # TODO: 实现创作者存储逻辑
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement] 存储创作者失败: {creator_item.get('author_id', '')}, 错误: {e}")
            # 不抛出异常，避免影响主要内容存储

    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        Returns:
            List[Dict]: 内容列表
        """
        try:
            # 使用UnifiedStoreImplement的get_all_content方法
            return await self.unified_store.get_all_content()
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement] 获取内容失败: {e}")
            return []
    
    # 添加兼容性方法，保持与原有代码的兼容性
    async def update_xhs_note(self, note_item: Dict, task_id: str = None):
        """
        更新小红书笔记 - 兼容性方法
        Args:
            note_item: 笔记数据
            task_id: 任务ID
        """
        try:
            # 转换数据格式以适配统一存储的字段映射
            note_id = note_item.get("note_id")
            user_info = note_item.get("user", {})
            interact_info = note_item.get("interact_info", {})
            image_list: List[Dict] = note_item.get("image_list", [])
            tag_list: List[Dict] = note_item.get("tag_list", [])
            
            # 处理图片URL
            for img in image_list:
                if img.get('url_default') != '':
                    img.update({'url': img.get('url_default')})
            
            # 获取视频URL
            video_url = ','.join(self._get_video_url_arr(note_item))
            
            # 构建符合统一存储字段映射的数据结构
            unified_content = {
                "note_id": note_id,  # content_id 映射
                "type": note_item.get("type", "note"),  # content_type 映射
                "title": note_item.get("title") or note_item.get("desc", "")[:255],
                "desc": note_item.get("desc", ""),  # description 和 content 映射
                "user": user_info,  # 嵌套结构，用于 author_id, author_name 等映射
                "interact_info": interact_info,  # 嵌套结构，用于 like_count 等映射
                "image_list": image_list,  # 嵌套结构，用于 cover_url 映射
                "video_url": video_url,  # video_download_url 映射
                "note_url": f"https://www.xiaohongshu.com/explore/{note_id}",  # video_url 映射
                "ip_location": note_item.get("ip_location", ""),
                "time": self._convert_to_timestamp(note_item.get("time", 0)),  # create_time 和 publish_time 映射
                "last_update_time": self._convert_to_timestamp(note_item.get("last_update_time", 0)),  # update_time 映射
                "tag_list": tag_list,  # tags 和 topics 映射
                "source_keyword": note_item.get("source_keyword", ""),
                "raw_data": note_item,  # 原始数据
                "task_id": task_id
            }
            
            await self.store_content(unified_content)
            
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement.update_xhs_note] 更新笔记失败: {note_id}, 错误: {e}")
            raise
    
    def _get_video_url_arr(self, note_item: Dict) -> List[str]:
        """
        获取视频url数组
        Args:
            note_item: 笔记数据

        Returns:
            List[str]: 视频URL列表
        """
        if note_item.get('type') != 'video':
            return []

        videoArr = []
        video_data = note_item.get('video', {})
        consumer = video_data.get('consumer', {})
        originVideoKey = consumer.get('origin_video_key', '')
        if originVideoKey == '':
            originVideoKey = consumer.get('originVideoKey', '')
        
        # 降级有水印
        if originVideoKey == '':
            media = video_data.get('media', {})
            stream = media.get('stream', {})
            videos = stream.get('h264', [])
            if isinstance(videos, list):
                videoArr = [v.get('master_url', '') for v in videos if v.get('master_url')]
        else:
            videoArr = [f"http://sns-video-bd.xhscdn.com/{originVideoKey}"]

        return videoArr
    
    def get_video_url_arr(self, note_item: Dict) -> List[str]:
        """
        获取视频url数组 - 公共接口
        Args:
            note_item: 笔记数据

        Returns:
            List[str]: 视频URL列表
        """
        return self._get_video_url_arr(note_item)
    
    async def batch_update_xhs_note_comments(self, note_id: str, comments: List[Dict]):
        """
        批量更新小红书笔记评论 - 兼容性方法
        Args:
            note_id: 笔记ID
            comments: 评论列表
        """
        if not comments:
            return
        for comment_item in comments:
            await self.update_xhs_note_comment(note_id, comment_item)
    
    async def update_xhs_note_comment(self, note_id: str, comment_item: Dict):
        """
        更新小红书笔记评论 - 兼容性方法
        Args:
            note_id: 笔记ID
            comment_item: 评论数据
        """
        try:
            user_info = comment_item.get("user_info", {})
            comment_id = comment_item.get("id")
            
            # 构建符合统一存储字段映射的评论数据结构
            unified_comment = {
                "id": comment_id,  # comment_id 映射
                "note_id": note_id,  # content_id 映射
                "content": comment_item.get("content", ""),  # content 映射
                "user_info": user_info,  # 嵌套结构，用于 author_id, author_name 等映射
                "like_count": comment_item.get("like_count", 0),
                "sub_comment_count": comment_item.get("sub_comment_count", 0),
                "create_time": self._convert_to_timestamp(comment_item.get("create_time", 0)),
                "raw_data": comment_item  # 原始数据
            }
            
            await self.store_comment(unified_comment)
            
        except Exception as e:
            utils.logger.error(f"[XhsDbStoreImplement.update_xhs_note_comment] 更新评论失败: {comment_id}, 错误: {e}")
            raise
    
    async def update_xhs_note_image(self, note_id: str, pic_content: bytes, extension_file_name: str):
        """
        更新小红书笔记图片 - 兼容性方法
        Args:
            note_id: 笔记ID
            pic_content: 图片内容
            extension_file_name: 文件扩展名
        """
        # 这里可以调用图片存储服务
        from .xhs_store_image import XiaoHongShuImage
        await XiaoHongShuImage().store_image({
            "notice_id": note_id, 
            "pic_content": pic_content, 
            "extension_file_name": extension_file_name
        })
    
    async def save_creator(self, user_id: str, creator: Dict):
        """
        保存小红书创作者 - 兼容性方法
        Args:
            user_id: 用户ID
            creator: 创作者数据
        """
        user_info = creator.get('basicInfo', {})

        follows = 0
        fans = 0
        interaction = 0
        for i in creator.get('interactions', []):
            if i.get('type') == 'follows':
                follows = i.get('count', 0)
            elif i.get('type') == 'fans':
                fans = i.get('count', 0)
            elif i.get('type') == 'interaction':
                interaction = i.get('count', 0)

        def get_gender(gender):
            if gender == 1:
                return '女'
            elif gender == 0:
                return '男'
            else:
                return None

        # 构建统一格式的创作者数据
        unified_creator = {
            "creator_id": user_id,
            "platform": "xhs",
            "author_id": user_id,
            "author_name": user_info.get('nickname', ''),
            "author_nickname": user_info.get('nickname', ''),
            "author_avatar": user_info.get('images', ''),
            "author_signature": user_info.get('desc', ''),
            "gender": get_gender(user_info.get('gender')),
            "ip_location": user_info.get('ipLocation', ''),
            "follows": follows,
            "fans": fans,
            "interaction": interaction,
            "tags": json.dumps({tag.get('tagType'): tag.get('name') for tag in creator.get('tags', [])}, ensure_ascii=False),
            "raw_data": json.dumps(creator, ensure_ascii=False),
            "add_ts": utils.get_current_timestamp(),
            "last_modify_ts": utils.get_current_timestamp()
        }
        
        await self.store_creator(unified_creator)


class XhsJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/xhs/json"
    words_store_path: str = "data/xhs/words"

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
        Xhs creator JSON storage implementation
        Args:
            creator_item: creator item dict

        Returns:

        """
        await self.save_data_to_json(save_item=creator_item, store_type="creator")


class XhsRedisStoreImplement(AbstractStore):
    """小红书Redis存储实现 - 使用统一存储系统"""
    
    def __init__(self, redis_callback=None):
        self.unified_store = UnifiedStoreImplement("xhs", redis_callback)
    
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.unified_store.set_redis_callback(callback)
    
    async def store_content(self, content_item: Dict):
        """
        小红书内容Redis存储实现
        Args:
            content_item: 内容字典
        """
        await self.unified_store.store_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        小红书评论Redis存储实现
        Args:
            comment_item: 评论字典
        """
        await self.unified_store.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict):
        """
        小红书创作者Redis存储实现
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
