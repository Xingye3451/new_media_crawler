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
# @Desc    : sql接口集合

from typing import Dict, List
from tools import utils

from db import AsyncMysqlDB
from var import media_crawler_db_var


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
    查询一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_id:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    sql: str = f"select * from kuaishou_video where video_id = '{content_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()
    except Exception as e:
        utils.logger.error(f"查询内容失败: {content_id}, 错误: {e}")
        return dict()


async def add_new_content(content_item: Dict) -> int:
    """
    新增一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    last_row_id: int = await async_db_conn.item_to_table("kuaishou_video", content_item)
    return last_row_id
    except Exception as e:
        utils.logger.error(f"新增内容失败: {content_item.get('video_id', 'unknown')}, 错误: {e}")
        raise


async def update_content_by_content_id(content_id: str, content_item: Dict) -> int:
    """
    更新一条记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_id:
        content_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    effect_row: int = await async_db_conn.update_table("kuaishou_video", content_item, "video_id", content_id)
    return effect_row
    except Exception as e:
        utils.logger.error(f"更新内容失败: {content_id}, 错误: {e}")
        raise


async def query_comment_by_comment_id(comment_id: str) -> Dict:
    """
    查询一条评论内容
    Args:
        comment_id:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    sql: str = f"select * from kuaishou_video_comment where comment_id = '{comment_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()
    except Exception as e:
        utils.logger.error(f"查询评论失败: {comment_id}, 错误: {e}")
        return dict()


async def add_new_comment(comment_item: Dict) -> int:
    """
    新增一条评论记录
    Args:
        comment_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    last_row_id: int = await async_db_conn.item_to_table("kuaishou_video_comment", comment_item)
    return last_row_id
    except Exception as e:
        utils.logger.error(f"新增评论失败: {comment_item.get('comment_id', 'unknown')}, 错误: {e}")
        raise


async def update_comment_by_comment_id(comment_id: str, comment_item: Dict) -> int:
    """
    更新增一条评论记录
    Args:
        comment_id:
        comment_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
    effect_row: int = await async_db_conn.update_table("kuaishou_video_comment", comment_item, "comment_id", comment_id)
    return effect_row
    except Exception as e:
        utils.logger.error(f"更新评论失败: {comment_id}, 错误: {e}")
        raise


async def query_creator_by_user_id(user_id: str) -> Dict:
    """
    查询一条创作者记录
    Args:
        user_id:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        sql: str = f"select * from ks_creator where user_id = '{user_id}'"
        rows: List[Dict] = await async_db_conn.query(sql)
        if len(rows) > 0:
            return rows[0]
        return dict()
    except Exception as e:
        utils.logger.error(f"查询创作者失败: {user_id}, 错误: {e}")
        return dict()


async def add_new_creator(creator_item: Dict) -> int:
    """
    新增一条创作者信息
    Args:
        creator_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        last_row_id: int = await async_db_conn.item_to_table("ks_creator", creator_item)
        return last_row_id
    except Exception as e:
        utils.logger.error(f"新增创作者失败: {creator_item.get('user_id', 'unknown')}, 错误: {e}")
        raise


async def update_creator_by_user_id(user_id: str, creator_item: Dict) -> int:
    """
    更新一条创作者信息
    Args:
        user_id:
        creator_item:

    Returns:

    """
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        effect_row: int = await async_db_conn.update_table("ks_creator", creator_item, "user_id", user_id)
        return effect_row
    except Exception as e:
        utils.logger.error(f"更新创作者失败: {user_id}, 错误: {e}")
        raise
