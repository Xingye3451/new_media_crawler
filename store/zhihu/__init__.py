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

import config
from base.base_crawler import AbstractStore
from model.m_zhihu import ZhihuComment, ZhihuContent, ZhihuCreator
from store.zhihu.zhihu_store_impl import (ZhihuCsvStoreImplement,
                                          ZhihuDbStoreImplement,
                                          ZhihuJsonStoreImplement)
from tools import utils
from var import source_keyword_var


class ZhihuStoreFactory:
    STORES = {
        "csv": ZhihuCsvStoreImplement,
        "db": ZhihuDbStoreImplement,
        "json": ZhihuJsonStoreImplement
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = ZhihuStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[ZhihuStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()

async def batch_update_zhihu_contents(contents: List[ZhihuContent]):
    """
    批量更新知乎内容
    Args:
        contents:

    Returns:

    """
    if not contents:
        return

    for content_item in contents:
        await update_zhihu_content(content_item)

async def get_all_content() -> List[Dict]:
    """
    获取所有存储的内容
    Returns:
        List[Dict]: 内容列表
    """
    collected_data = _get_collected_data()
    utils.logger.info(f"[ZhihuStore] 获取存储内容 - 共收集到 {len(collected_data)} 条数据")
    return collected_data


def get_video_url_arr(note_item: Dict) -> List:
    """
    获取视频url数组
    Args:
        note_item:

    Returns:

    """
    # 知乎视频URL处理逻辑
    video_url = note_item.get('video_url', '')
    if video_url:
        return [video_url]
    return []


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


async def update_zhihu_content(content_item: ZhihuContent, task_id: str = None):
    """
    更新知乎内容
    Args:
        content_item:

    Returns:

    """
    save_content_item = {
        "note_id": content_item.id,
        "note_type": content_item.type,
        "title": content_item.title[:500],
        "desc": content_item.excerpt,
        "create_time": content_item.created_time,
        "user_id": content_item.author.id,
        "nickname": content_item.author.name,
        "avatar": content_item.author.avatar_url,
        "liked_count": str(content_item.voteup_count),
        "comment_count": str(content_item.comment_count),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": content_item.url,
        "source_keyword": source_keyword_var.get(),
        "platform": "zhihu",  # 添加平台标识
        "task_id": task_id,
    }
    
    # 收集数据
    _add_collected_data(save_content_item)
    
    utils.logger.info(
        f"[store.zhihu.update_zhihu_content] Zhihu content id:{content_item.id}, title:{save_content_item.get('title')}")
    await ZhihuStoreFactory.create_store().store_content(content_item=save_content_item)



async def batch_update_zhihu_note_comments(comments: List[ZhihuComment]):
    """
    批量更新知乎内容评论
    Args:
        comments:

    Returns:

    """
    if not comments:
        return
    
    for comment_item in comments:
        await update_zhihu_content_comment(comment_item)


async def update_zhihu_content_comment(comment_item: ZhihuComment):
    """
    更新知乎内容评论
    Args:
        comment_item:

    Returns:

    """
    local_db_item = comment_item.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.zhihu.update_zhihu_note_comment] zhihu content comment:{local_db_item}")
    await ZhihuStoreFactory.create_store().store_comment(local_db_item)


async def save_creator(creator: ZhihuCreator):
    """
    保存知乎创作者信息
    Args:
        creator:

    Returns:

    """
    if not creator:
        return
    local_db_item = creator.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})
    await ZhihuStoreFactory.create_store().store_creator(local_db_item)