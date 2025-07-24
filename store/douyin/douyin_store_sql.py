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

import json
from typing import Dict, List
from tools import utils
import time

from db import AsyncMysqlDB
from var import media_crawler_db_var


DOUYIN_AWEME_FIELDS = {
    "aweme_id", "aweme_type", "title", "desc", "create_time", "user_id", "sec_uid", "short_user_id",
    "user_unique_id", "nickname", "avatar", "user_signature", "ip_location", "liked_count", "comment_count",
    "share_count", "collected_count", "aweme_url", "cover_url", "video_download_url", "video_play_url",
    "video_share_url", "is_favorite", "minio_url", "task_id", "source_keyword", "add_ts", "last_modify_ts",
    "tags", "meta", "author"
}

def filter_fields_for_table(item: dict, allowed_fields: set) -> dict:
    return {k: v for k, v in item.items() if k in allowed_fields}


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
        sql: str = f"select * from douyin_aweme where aweme_id = '{content_id}'"
        rows: List[Dict] = await async_db_conn.query(sql)
        if len(rows) > 0:
            return rows[0]
        return dict()
    except Exception as e:
        utils.logger.error(f"查询内容失败: {content_id}, 错误: {e}")
        return dict()


def fill_fields_from_all_sources(safe_item, content_item):
    # 1. 顶层字段优先赋值
    for k in [
        "aweme_id", "aweme_type", "title", "desc", "create_time", "user_id", "sec_uid", "short_user_id",
        "user_unique_id", "nickname", "avatar", "user_signature", "ip_location", "is_favorite", "minio_url",
        "task_id", "source_keyword", "add_ts", "last_modify_ts", "tags"
    ]:
        if not safe_item.get(k) and content_item.get(k) is not None:
            safe_item[k] = content_item[k]

    # 2. author 字段拍平
    if "author" in safe_item and safe_item["author"]:
        try:
            author_data = safe_item["author"]
            if isinstance(author_data, str):
                import json
                author_data = json.loads(author_data)
            safe_item.setdefault("user_id", author_data.get("uid", ""))
            safe_item.setdefault("sec_uid", author_data.get("sec_uid", ""))
            safe_item.setdefault("nickname", author_data.get("nickname", ""))
            avatar_thumb = author_data.get("avatar_thumb")
            if avatar_thumb:
                if isinstance(avatar_thumb, dict):
                    url_list = avatar_thumb.get("url_list")
                    if url_list and isinstance(url_list, list):
                        safe_item.setdefault("avatar", url_list[0])
                    else:
                        safe_item.setdefault("avatar", avatar_thumb.get("uri", ""))
                elif isinstance(avatar_thumb, str):
                    safe_item.setdefault("avatar", avatar_thumb)
            safe_item.setdefault("user_signature", author_data.get("signature", ""))
            # user_unique_id/short_user_id
            safe_item.setdefault("user_unique_id", author_data.get("unique_id", ""))
            safe_item.setdefault("short_user_id", author_data.get("short_id", ""))
        except Exception as e:
            utils.logger.warning(f"[拍平author] 解析失败: {e}")

    # 3. video 字段拍平
    video = content_item.get("video")
    if video:
        play_addr = video.get("play_addr")
        if play_addr and play_addr.get("url_list"):
            safe_item.setdefault("video_play_url", play_addr["url_list"][0])
        download_addr = video.get("download_addr")
        if download_addr and download_addr.get("url_list"):
            safe_item.setdefault("video_download_url", download_addr["url_list"][0])
        cover = video.get("cover")
        if cover and cover.get("url_list"):
            safe_item.setdefault("cover_url", cover["url_list"][0])

    # 4. statistics 字段拍平
    statistics = content_item.get("statistics")
    if statistics:
        safe_item.setdefault("liked_count", str(statistics.get("digg_count", "")))
        safe_item.setdefault("comment_count", str(statistics.get("comment_count", "")))
        safe_item.setdefault("share_count", str(statistics.get("share_count", "")))
        safe_item.setdefault("collected_count", str(statistics.get("collect_count", "")))

    # 5. share_info 字段拍平
    share_info = content_item.get("share_info")
    if share_info:
        safe_item.setdefault("aweme_url", share_info.get("share_url", ""))
        safe_item.setdefault("title", share_info.get("share_title", content_item.get("desc", "")))
        safe_item.setdefault("video_share_url", share_info.get("share_url", ""))
    elif safe_item.get("aweme_url"):
        safe_item.setdefault("video_share_url", safe_item["aweme_url"])

    # 6. tags from text_extra
    text_extra = content_item.get("text_extra")
    if text_extra and isinstance(text_extra, list):
        tags_list = [x.get("hashtag_name") for x in text_extra if x.get("hashtag_name")]
        if tags_list:
            import json
            safe_item["tags"] = json.dumps(tags_list, ensure_ascii=False)

    # 7. meta as a union of several subfields
    meta_dict = {}
    for k in ["video", "statistics", "status", "video_control", "music", "share_info"]:
        if content_item.get(k) is not None:
            meta_dict[k] = content_item[k]
    if meta_dict:
        import json
        safe_item["meta"] = json.dumps(meta_dict, ensure_ascii=False)

    return safe_item


async def add_new_content(content_item: Dict, task_id: str = None) -> int:
    """
    新增一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_item: 原始内容数据
        task_id: 任务ID（可选，强制关联）
    Returns:
        新增行ID
    """
    try:
        utils.logger.info(f"[DEBUG] content_item原始内容: {content_item}")
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        safe_item = serialize_for_db(content_item)
        safe_item = fill_fields_from_all_sources(safe_item, content_item)
        safe_item = filter_fields_for_table(safe_item, DOUYIN_AWEME_FIELDS)
        # 强制覆盖 task_id
        if task_id:
            safe_item["task_id"] = task_id
        # 自动补全所有 NOT NULL 且无默认值的字段
        now_ts = int(time.time() * 1000)
        if "last_modify_ts" not in safe_item or not safe_item["last_modify_ts"]:
            safe_item["last_modify_ts"] = now_ts
        if "add_ts" not in safe_item or not safe_item["add_ts"]:
            safe_item["add_ts"] = now_ts
        if "create_time" not in safe_item or not safe_item["create_time"]:
            safe_item["create_time"] = int(time.time())
        if "aweme_type" not in safe_item or not safe_item["aweme_type"]:
            safe_item["aweme_type"] = "video"
        if "aweme_id" not in safe_item or not safe_item["aweme_id"]:
            safe_item["aweme_id"] = f"auto_{now_ts}"
        utils.logger.info(f"[DEBUG] 实际插入字段: {list(safe_item.keys())}")
        utils.logger.info(f"[DEBUG] 字段对应的值: {list(safe_item.values())}")
        last_row_id: int = await async_db_conn.item_to_table("douyin_aweme", safe_item)
        return last_row_id
    except Exception as e:
        utils.logger.error(f"新增内容失败: {content_item.get('aweme_id', 'unknown')}, 错误: {e}")
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
        effect_row: int = await async_db_conn.update_table("douyin_aweme", content_item, "aweme_id", content_id)
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
        sql: str = f"select * from douyin_aweme_comment where comment_id = '{comment_id}'"
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
        last_row_id: int = await async_db_conn.item_to_table("douyin_aweme_comment", comment_item)
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
        effect_row: int = await async_db_conn.update_table("douyin_aweme_comment", comment_item, "comment_id", comment_id)
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
        sql: str = f"select * from dy_creator where user_id = '{user_id}'"
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
        last_row_id: int = await async_db_conn.item_to_table("dy_creator", creator_item)
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
        effect_row: int = await async_db_conn.update_table("dy_creator", creator_item, "user_id", user_id)
        return effect_row
    except Exception as e:
        utils.logger.error(f"更新创作者失败: {user_id}, 错误: {e}")
        raise