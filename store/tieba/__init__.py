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
from typing import List, Dict

from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from var import source_keyword_var

from . import tieba_store_impl
from .tieba_store_impl import *


# 全局数据收集器
_collected_data = []

def _add_collected_data(data: Dict):
    """添加收集到的数据"""
    global _collected_data
    _collected_data.append(data)

def _get_collected_data() -> List[Dict]:
    """获取收集到的数据"""
    global _collected_data
    return _collected_data

def _clear_collected_data():
    """清空收集到的数据"""
    global _collected_data
    _collected_data = []


class TieBaStoreFactory:
    STORES = {
        "csv": TieBaCsvStoreImplement,
        "db": TieBaDbStoreImplement,
        "json": TieBaJsonStoreImplement
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TieBaStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[TieBaStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


async def batch_update_tieba_notes(note_list: List[TiebaNote]):
    """
    Batch update tieba notes
    Args:
        note_list:

    Returns:

    """
    if not note_list:
        return
    for note_item in note_list:
        await update_tieba_note(note_item)


async def get_all_content() -> List[Dict]:
    """
    获取所有存储的内容
    Returns:
        List[Dict]: 内容列表
    """
    collected_data = _get_collected_data()
    utils.logger.info(f"[TiebaStore] 获取存储内容 - 共收集到 {len(collected_data)} 条数据")
    return collected_data


def get_video_url_arr(note_item: Dict) -> List:
    """
    获取视频url数组
    Args:
        note_item:

    Returns:

    """
    # 贴吧视频URL处理逻辑
    video_url = note_item.get('video_url', '')
    if video_url:
        return [video_url]
    return []


async def update_tieba_note(note_item: TiebaNote, task_id: str = None):
    """
    Add or Update tieba note
    Args:
        note_item:

    Returns:

    """
    save_content_item = {
        "note_id": note_item.id,
        "note_type": "tieba",
        "title": note_item.title[:500],
        "desc": note_item.content,
        "create_time": note_item.create_time,
        "user_id": note_item.author.id,
        "nickname": note_item.author.name,
        "avatar": note_item.author.avatar_url,
        "liked_count": str(note_item.like_count),
        "comment_count": str(note_item.reply_count),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": note_item.url,
        "source_keyword": source_keyword_var.get(),
        "platform": "tieba",  # 添加平台标识
        "task_id": task_id,
    }
    
    # 收集数据
    _add_collected_data(save_content_item)
    
    utils.logger.info(
        f"[store.tieba.update_tieba_note] Tieba note id:{note_item.id}, title:{save_content_item.get('title')}")
    await TieBaStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_tieba_note_comments(note_id: str, comments: List[TiebaComment]):
    """
    Batch update tieba note comments
    Args:
        note_id:
        comments:

    Returns:

    """
    if not comments:
        return
    for comment_item in comments:
        await update_tieba_note_comment(note_id, comment_item)


async def update_tieba_note_comment(note_id: str, comment_item: TiebaComment):
    """
    Update tieba note comment
    Args:
        note_id:
        comment_item:

    Returns:

    """
    save_comment_item = comment_item.model_dump()
    save_comment_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.tieba.update_tieba_note_comment] tieba note id: {note_id} comment:{save_comment_item}")
    await TieBaStoreFactory.create_store().store_comment(save_comment_item)


async def save_creator(user_info: TiebaCreator):
    """
    Save creator information to local
    Args:
        user_info:

    Returns:

    """
    local_db_item = user_info.model_dump()
    local_db_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.tieba.save_creator] creator:{local_db_item}")
    await TieBaStoreFactory.create_store().store_creator(local_db_item)
