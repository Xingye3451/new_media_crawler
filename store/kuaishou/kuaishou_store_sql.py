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
# @Time    : 2024/4/6 15:30
# @Desc    : sql接口集合 - 使用统一存储系统

import json
from typing import Dict, List
from tools import utils
import time

from db import AsyncMysqlDB
from var import media_crawler_db_var
from store.unified_store import (
    query_content_by_content_id as unified_query_content,
    add_new_content as unified_add_content,
    update_content_by_content_id as unified_update_content,
    query_comment_by_comment_id as unified_query_comment,
    add_new_comment as unified_add_comment,
    update_comment_by_comment_id as unified_update_comment
)


async def _get_db_connection() -> AsyncMysqlDB:
    """获取数据库连接，如果未初始化则尝试初始化"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        # 如果上下文变量没有设置，尝试初始化数据库连接
        try:
            from db import init_mediacrawler_db
            await init_mediacrawler_db()
            return media_crawler_db_var.get()
        except Exception as e:
            utils.logger.error(f"数据库连接初始化失败: {e}")
            raise


async def query_content_by_content_id(content_id: str) -> Dict:
    """
    查询一条内容记录（使用统一存储系统）
    Args:
        content_id: 内容ID

    Returns:
        Dict: 内容记录
    """
    try:
        return await unified_query_content("kuaishou", content_id)
    except Exception as e:
        utils.logger.error(f"查询内容失败: {content_id}, 错误: {e}")
        return dict()


async def add_new_content(content_item: Dict, task_id: str = None) -> int:
    """
    新增一条内容记录（使用统一存储系统）
    Args:
        content_item: 内容字典
        task_id: 任务ID

    Returns:
        int: 新增记录的ID
    """
    try:
        return await unified_add_content("kuaishou", content_item, task_id)
    except Exception as e:
        utils.logger.error(f"新增内容失败: {content_item.get('photo_id', 'unknown')}, 错误: {e}")
        raise


async def update_content_by_content_id(content_id: str, content_item: Dict) -> int:
    """
    更新一条内容记录（使用统一存储系统）
    Args:
        content_id: 内容ID
        content_item: 内容字典

    Returns:
        int: 更新的记录数
    """
    try:
        return await unified_update_content("kuaishou", content_id, content_item)
    except Exception as e:
        utils.logger.error(f"更新内容失败: {content_id}, 错误: {e}")
        raise


async def query_comment_by_comment_id(comment_id: str) -> Dict:
    """
    查询一条评论记录（使用统一存储系统）
    Args:
        comment_id: 评论ID

    Returns:
        Dict: 评论记录
    """
    try:
        return await unified_query_comment("kuaishou", comment_id)
    except Exception as e:
        utils.logger.error(f"查询评论失败: {comment_id}, 错误: {e}")
        return dict()


async def add_new_comment(comment_item: Dict) -> int:
    """
    新增一条评论记录（使用统一存储系统）
    Args:
        comment_item: 评论字典

    Returns:
        int: 新增记录的ID
    """
    try:
        return await unified_add_comment("kuaishou", comment_item)
    except Exception as e:
        utils.logger.error(f"新增评论失败: {comment_item.get('comment_id', 'unknown')}, 错误: {e}")
        raise


async def update_comment_by_comment_id(comment_id: str, comment_item: Dict) -> int:
    """
    更新一条评论记录（使用统一存储系统）
    Args:
        comment_id: 评论ID
        comment_item: 评论字典

    Returns:
        int: 更新的记录数
    """
    try:
        return await unified_update_comment("kuaishou", comment_id, comment_item)
    except Exception as e:
        utils.logger.error(f"更新评论失败: {comment_id}, 错误: {e}")
        raise


async def add_new_creator(creator_item: Dict) -> int:
    """
    新增一条创作者记录（使用统一存储系统）
    Args:
        creator_item: 创作者字典

    Returns:
        int: 新增记录的ID
    """
    try:
        # 暂时使用统一存储系统的内容存储，因为创作者表还在开发中
        return await unified_add_content("kuaishou", creator_item)
    except Exception as e:
        utils.logger.error(f"新增创作者失败: {creator_item.get('user_id', 'unknown')}, 错误: {e}")
        raise


async def query_creator_by_user_id(user_id: str) -> Dict:
    """
    查询一条创作者记录（使用统一存储系统）
    Args:
        user_id: 用户ID

    Returns:
        Dict: 创作者记录
    """
    try:
        # 暂时使用统一存储系统的内容查询，因为创作者表还在开发中
        return await unified_query_content("kuaishou", user_id)
    except Exception as e:
        utils.logger.error(f"查询创作者失败: {user_id}, 错误: {e}")
        return dict()


async def update_creator_by_user_id(user_id: str, creator_item: Dict) -> int:
    """
    更新一条创作者记录（使用统一存储系统）
    Args:
        user_id: 用户ID
        creator_item: 创作者字典

    Returns:
        int: 更新的记录数
    """
    try:
        # 暂时使用统一存储系统的内容更新，因为创作者表还在开发中
        return await unified_update_content("kuaishou", user_id, creator_item)
    except Exception as e:
        utils.logger.error(f"更新创作者失败: {user_id}, 错误: {e}")
        raise


def serialize_for_db(data):
    """
    只对最外层 dict 的字段值为 dict/list 的做 json.dumps，最外层 dict 保持原结构
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                new_data[k] = json.dumps(v, ensure_ascii=False)
            else:
                new_data[k] = v
        return new_data
    elif isinstance(data, list):
        return json.dumps(data, ensure_ascii=False)
    else:
        return data
