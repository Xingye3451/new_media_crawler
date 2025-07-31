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
# @Desc    : 统一存储系统 - 多平台内容统一存储

import json
import time
from typing import Dict, List, Optional
from tools import utils

from db import AsyncMysqlDB
from var import media_crawler_db_var


# 统一内容表字段定义
UNIFIED_CONTENT_FIELDS = {
    # 基础标识字段
    "content_id", "platform", "content_type", "task_id", "source_keyword",
    
    # 内容信息字段
    "title", "description", "content", "create_time", "publish_time", "update_time",
    
    # 作者信息字段
    "author_id", "author_name", "author_nickname", "author_avatar", "author_signature",
    "author_unique_id", "author_sec_uid", "author_short_id",
    
    # 统计字段
    "like_count", "comment_count", "share_count", "collect_count", "view_count",
    
    # 媒体字段
    "cover_url", "video_url", "video_download_url", "video_play_url", "video_share_url",
    "image_urls", "audio_url", "file_urls",
    
    # 位置信息
    "ip_location", "location",
    
    # 标签和分类
    "tags", "categories", "topics",
    
    # 状态字段
    "is_favorite", "is_deleted", "is_private", "is_original",
    
    # 存储字段
    "minio_url", "local_path", "file_size", "storage_type",
    
    # 扩展字段
    "metadata", "raw_data", "extra_info",
    
    # 时间戳
    "add_ts", "last_modify_ts"
}

# 统一评论表字段定义
UNIFIED_COMMENT_FIELDS = {
    # 基础标识字段
    "comment_id", "content_id", "platform", "parent_id", "reply_to_id",
    
    # 评论内容
    "content", "text", "html_content",
    
    # 作者信息
    "author_id", "author_name", "author_nickname", "author_avatar",
    
    # 统计字段
    "like_count", "reply_count", "share_count",
    
    # 时间字段
    "create_time", "publish_time",
    
    # 状态字段
    "is_deleted", "is_hidden", "is_top",
    
    # 扩展字段
    "metadata", "raw_data",
    
    # 时间戳
    "add_ts", "last_modify_ts"
}

# 平台字段映射配置
PLATFORM_FIELD_MAPPINGS = {
    "douyin": {
        "content_id": "aweme_id",
        "content_type": "video",  # 固定值
        "title": "desc",
        "description": "desc",
        "content": "desc",
        "author_id": "author.uid",
        "author_name": "author.nickname",
        "author_nickname": "author.nickname",
        "author_avatar": "author.avatar_thumb.url_list.0",
        "author_signature": "author.signature",
        "author_unique_id": "author.unique_id",
        "author_sec_uid": "author.sec_uid",
        "author_short_id": "author.short_id",
        "like_count": "statistics.digg_count",
        "comment_count": "statistics.comment_count",
        "share_count": "statistics.share_count",
        "collect_count": "statistics.collect_count",
        "view_count": "statistics.play_count",
        "cover_url": "video.cover.url_list.0",
        "video_url": "aweme_url",  # 播放页链接
        "video_download_url": "download_url",  # 下载链接
        "video_play_url": "aweme_url",  # 播放页链接
        "video_share_url": "aweme_url",  # 分享链接（使用播放页链接）
        "audio_url": "music.play_url.uri",
        "ip_location": "ip_location",
        "create_time": "create_time",
        "publish_time": "create_time",
        "update_time": "create_time",
        "topics": "cha_list",
        "raw_data": "raw_data"
    },
    "xhs": {
        "content_id": "note_id",
        "content_type": "type",
        "title": "title",
        "description": "desc",
        "content": "desc",
        "author_id": "user.user_id",
        "author_name": "user.nickname",
        "author_nickname": "user.nickname",
        "author_avatar": "user.avatar",
        "like_count": "interact_info.liked_count",
        "comment_count": "interact_info.comment_count",
        "share_count": "interact_info.share_count",
        "collect_count": "interact_info.collected_count",
        "cover_url": "image_list.0.url",
        "image_urls": "image_list",
        "video_url": "note_url",
        "video_download_url": "video_url",
        "video_play_url": "note_url",
        "video_share_url": "note_url",
        "ip_location": "ip_location",
        "create_time": "time",
        "publish_time": "time",
        "update_time": "last_update_time",
        "tags": "tag_list",
        "topics": "tag_list",
        "raw_data": "raw_data"
    },
    "kuaishou": {
        "content_id": "video_id",
        "content_type": "video_type",
        "title": "title",
        "description": "desc",
        "content": "desc",
        "author_id": "user_id",
        "author_name": "nickname",
        "author_nickname": "nickname",
        "author_avatar": "avatar",
        "like_count": "liked_count",
        "comment_count": "comment_count",
        "share_count": "share_count",
        "collect_count": "collect_count",
        "view_count": "viewd_count",
        "cover_url": "video_cover_url",
        "video_url": "video_url",
        "video_play_url": "video_play_url",
        "video_download_url": "video_download_url",
        "create_time": "create_time",
        "publish_time": "create_time",
        "update_time": "last_modify_ts",
        "raw_data": "raw_data",
        # 新增字段映射
        "author_signature": "author_signature",
        "author_unique_id": "author_unique_id",
        "author_sec_uid": "author_sec_uid",
        "author_short_id": "author_short_id",
        "video_share_url": "video_share_url",
        "image_urls": "image_urls",
        "audio_url": "audio_url",
        "file_urls": "file_urls",
        "ip_location": "ip_location",
        "location": "location",
        "tags": "tags",
        "categories": "categories",
        "topics": "topics",
        "is_favorite": "is_favorite",
        "is_deleted": "is_deleted",
        "is_private": "is_private",
        "is_original": "is_original",
        "minio_url": "minio_url",
        "local_path": "local_path"
    },
    "bilibili": {
        "content_id": "content_id",  # 直接使用content_id字段
        "content_type": "content_type",
        "title": "title",
        "description": "description",
        "content": "content",
        "source_keyword": "source_keyword",
        "create_time": "create_time",
        "publish_time": "publish_time",
        "update_time": "update_time",
        "author_id": "author_id",
        "author_name": "author_name",
        "author_nickname": "author_nickname",
        "author_avatar": "author_avatar",
        "author_signature": "author_signature",
        "author_unique_id": "author_unique_id",
        "author_sec_uid": "author_sec_uid",
        "author_short_id": "author_short_id",
        "like_count": "like_count",
        "comment_count": "comment_count",
        "share_count": "share_count",
        "collect_count": "collect_count",
        "view_count": "view_count",
        "cover_url": "cover_url",
        "video_url": "video_url",
        "video_play_url": "video_play_url",
        "video_download_url": "video_download_url",
        "video_share_url": "video_share_url",
        "image_urls": "image_urls",
        "audio_url": "audio_url",
        "file_urls": "file_urls",
        "ip_location": "ip_location",
        "location": "location",
        "tags": "tags",
        "categories": "categories",
        "topics": "topics",
        "is_favorite": "is_favorite",
        "is_deleted": "is_deleted",
        "is_private": "is_private",
        "is_original": "is_original",
        "minio_url": "minio_url",
        "local_path": "local_path",
        "file_size": "file_size",
        "storage_type": "storage_type",
        "metadata": "metadata",
        "raw_data": "raw_data",
        "extra_info": "extra_info",
        "add_ts": "add_ts",
        "last_modify_ts": "last_modify_ts"
    },
    "weibo": {
        "content_id": "id",
        "content_type": "weibo_type",
        "title": "title",
        "content": "text",
        "author_id": "user_id",
        "author_name": "screen_name",
        "author_nickname": "screen_name",
        "author_avatar": "avatar_hd",
        "author_signature": "description",
        "like_count": "attitudes_count",
        "comment_count": "comments_count",
        "share_count": "reposts_count",
        "cover_url": "thumbnail_pic",
        "image_urls": "pics",
        "create_time": "created_at"
    },
    "zhihu": {
        "content_id": "id",
        "content_type": "content_type",
        "title": "title",
        "content": "content",
        "author_id": "author_id",
        "author_name": "author_name",
        "author_nickname": "author_name",
        "author_avatar": "author_avatar",
        "like_count": "voteup_count",
        "comment_count": "comment_count",
        "share_count": "share_count",
        "create_time": "created_time",
        "publish_time": "updated_time"
    },
    "tieba": {
        "content_id": "tid",
        "content_type": "post_type",
        "title": "title",
        "content": "content",
        "author_id": "author_id",
        "author_name": "author_name",
        "author_nickname": "author_name",
        "like_count": "like_count",
        "comment_count": "reply_count",
        "create_time": "create_time"
    }
}


def filter_fields_for_table(item: dict, allowed_fields: set) -> dict:
    """过滤字段，只保留允许的字段"""
    return {k: v for k, v in item.items() if k in allowed_fields}


def serialize_for_db(data):
    """序列化数据，将dict/list转换为JSON字符串"""
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


def get_nested_value(data: Dict, path: str):
    """
    根据路径获取嵌套字典中的值
    
    Args:
        data (Dict): 数据字典
        path (str): 路径，如 "author.nickname" 或 "video.cover.url_list.0"
    
    Returns:
        任意类型: 找到的值，如果路径不存在则返回None
    """
    if not path or not data:
        return None
    
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict):
            if key.isdigit() and isinstance(current, list):
                # 处理数组索引
                try:
                    current = current[int(key)]
                except (IndexError, ValueError):
                    return None
            else:
                current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            # 处理数组索引
            try:
                current = current[int(key)]
            except (IndexError, ValueError):
                return None
        else:
            return None
        
        if current is None:
            return None
    
    return current


def map_platform_fields(platform: str, data: Dict) -> Dict:
    """将平台特定字段映射到统一字段"""
    if platform not in PLATFORM_FIELD_MAPPINGS:
        return data
    
    mapping = PLATFORM_FIELD_MAPPINGS[platform]
    mapped_data = {}
    
    # 添加平台标识
    mapped_data["platform"] = platform
    
    # 数值字段列表，需要转换为整数
    numeric_fields = {
        "like_count", "comment_count", "share_count", "collect_count", 
        "view_count", "create_time", "publish_time", "update_time",
        "add_ts", "last_modify_ts"
    }
    
    # 映射字段
    for unified_field, platform_field in mapping.items():
        if platform_field == "raw_data":
            # 特殊处理原始数据字段
            mapped_data[unified_field] = json.dumps(data, ensure_ascii=False)
        elif platform_field == "topics" and platform_field in data:
            # 特殊处理话题字段
            topics_data = data.get(platform_field, [])
            if isinstance(topics_data, list):
                topic_names = []
                for topic in topics_data:
                    if isinstance(topic, dict):
                        topic_names.append(topic.get("cha_name", ""))
                    else:
                        topic_names.append(str(topic))
                mapped_data[unified_field] = json.dumps(topic_names, ensure_ascii=False)
        elif platform_field in ["video", "image", "note", "post"]:
            # 固定值映射
            mapped_data[unified_field] = platform_field
        elif "." not in platform_field and platform_field not in data:
            # 其他固定值映射（如果字段不在数据中）
            # 修复：不应该将字段名作为值传递
            # mapped_data[unified_field] = platform_field
            pass  # 跳过不存在的字段
        else:
            # 处理嵌套字段路径或直接字段
            value = None
            if "." in platform_field:
                # 嵌套字段路径
                value = get_nested_value(data, platform_field)
            else:
                # 直接字段
                if platform_field in data:
                    value = data[platform_field]
            
            if value is not None:
                # 对数值字段进行类型转换
                if unified_field in numeric_fields:
                    try:
                        if isinstance(value, str):
                            # 如果是字符串，尝试转换为整数
                            if value.isdigit():
                                mapped_data[unified_field] = int(value)
                            else:
                                mapped_data[unified_field] = 0
                        elif isinstance(value, (int, float)):
                            mapped_data[unified_field] = int(value)
                        else:
                            mapped_data[unified_field] = 0
                    except (ValueError, TypeError):
                        mapped_data[unified_field] = 0
                else:
                    mapped_data[unified_field] = value
    
    return mapped_data


async def _get_db_connection() -> AsyncMysqlDB:
    """获取数据库连接"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        try:
            from db import init_mediacrawler_db
            await init_mediacrawler_db()
            return media_crawler_db_var.get()
        except Exception as e:
            utils.logger.error(f"数据库连接初始化失败: {e}")
            raise


async def query_content_by_content_id(platform: str, content_id: str) -> Dict:
    """查询内容记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        sql = f"SELECT * FROM unified_content WHERE platform = '{platform}' AND content_id = '{content_id}'"
        rows: List[Dict] = await async_db_conn.query(sql)
        if len(rows) > 0:
            return rows[0]
        return dict()
    except Exception as e:
        utils.logger.error(f"查询内容失败: {platform}/{content_id}, 错误: {e}")
        return dict()


async def add_new_content(platform: str, content_item: Dict, task_id: str = None) -> int:
    """新增内容记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 映射字段
        mapped_data = map_platform_fields(platform, content_item)
        
        # 添加任务ID
        if task_id:
            mapped_data["task_id"] = task_id
        
        # 添加时间戳
        now_ts = int(time.time() * 1000)
        if "add_ts" not in mapped_data:
            mapped_data["add_ts"] = now_ts
        if "last_modify_ts" not in mapped_data:
            mapped_data["last_modify_ts"] = now_ts
        
        # 序列化数据
        safe_item = serialize_for_db(mapped_data)
        
        # 过滤字段
        safe_item = filter_fields_for_table(safe_item, UNIFIED_CONTENT_FIELDS)
        
        # 插入数据库
        last_row_id: int = await async_db_conn.item_to_table("unified_content", safe_item)
        return last_row_id
        
    except Exception as e:
        utils.logger.error(f"新增内容失败: {platform}/{content_item.get('content_id', 'unknown')}, 错误: {e}")
        raise


async def update_content_by_content_id(platform: str, content_id: str, content_item: Dict) -> int:
    """更新内容记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 映射字段
        mapped_data = map_platform_fields(platform, content_item)
        
        # 更新时间戳
        mapped_data["last_modify_ts"] = int(time.time() * 1000)
        
        # 序列化数据
        safe_item = serialize_for_db(mapped_data)
        
        # 过滤字段
        safe_item = filter_fields_for_table(safe_item, UNIFIED_CONTENT_FIELDS)
        
        # 更新数据库 - 使用复合条件
        where_condition = f"platform = '{platform}' AND content_id = '{content_id}'"
        
        # 构建SET子句
        set_clauses = []
        values = []
        for key, value in safe_item.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        
        set_clause = ", ".join(set_clauses)
        sql = f"UPDATE unified_content SET {set_clause} WHERE {where_condition}"
        
        result = await async_db_conn.execute(sql, *values)
        return result
        
    except Exception as e:
        utils.logger.error(f"更新内容失败: {platform}/{content_id}, 错误: {e}")
        raise


async def query_comment_by_comment_id(platform: str, comment_id: str) -> Dict:
    """查询评论记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        sql = f"SELECT * FROM unified_comment WHERE platform = '{platform}' AND comment_id = '{comment_id}'"
        rows: List[Dict] = await async_db_conn.query(sql)
        if len(rows) > 0:
            return rows[0]
        return dict()
    except Exception as e:
        utils.logger.error(f"查询评论失败: {platform}/{comment_id}, 错误: {e}")
        return dict()


async def add_new_comment(platform: str, comment_item: Dict) -> int:
    """新增评论记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 映射字段
        mapped_data = map_platform_fields(platform, comment_item)
        
        # 添加时间戳
        now_ts = int(time.time() * 1000)
        if "add_ts" not in mapped_data:
            mapped_data["add_ts"] = now_ts
        if "last_modify_ts" not in mapped_data:
            mapped_data["last_modify_ts"] = now_ts
        
        # 序列化数据
        safe_item = serialize_for_db(mapped_data)
        
        # 过滤字段
        safe_item = filter_fields_for_table(safe_item, UNIFIED_COMMENT_FIELDS)
        
        # 插入数据库
        last_row_id: int = await async_db_conn.item_to_table("unified_comment", safe_item)
        return last_row_id
        
    except Exception as e:
        utils.logger.error(f"新增评论失败: {platform}/{comment_item.get('comment_id', 'unknown')}, 错误: {e}")
        raise


async def update_comment_by_comment_id(platform: str, comment_id: str, comment_item: Dict) -> int:
    """更新评论记录"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 映射字段
        mapped_data = map_platform_fields(platform, comment_item)
        
        # 更新时间戳
        mapped_data["last_modify_ts"] = int(time.time() * 1000)
        
        # 序列化数据
        safe_item = serialize_for_db(mapped_data)
        
        # 过滤字段
        safe_item = filter_fields_for_table(safe_item, UNIFIED_COMMENT_FIELDS)
        
        # 更新数据库 - 使用复合条件
        where_condition = f"platform = '{platform}' AND comment_id = '{comment_id}'"
        
        # 构建SET子句
        set_clauses = []
        values = []
        for key, value in safe_item.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        
        set_clause = ", ".join(set_clauses)
        sql = f"UPDATE unified_comment SET {set_clause} WHERE {where_condition}"
        
        result = await async_db_conn.execute(sql, *values)
        return result
        
    except Exception as e:
        utils.logger.error(f"更新评论失败: {platform}/{comment_id}, 错误: {e}")
        raise


async def get_content_list(platform: str = None, task_id: str = None, page: int = 1, page_size: int = 20) -> Dict:
    """获取内容列表"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 构建查询条件
        where_conditions = {}
        if platform:
            where_conditions["platform"] = platform
        if task_id:
            where_conditions["task_id"] = task_id
        
        # 查询总数
        count_sql = "SELECT COUNT(*) as total FROM unified_content"
        if where_conditions:
            conditions = " AND ".join([f"{k} = '{v}'" for k, v in where_conditions.items()])
            count_sql += f" WHERE {conditions}"
        
        count_result = await async_db_conn.get_first(count_sql)
        total = count_result['total'] if count_result else 0
        
        # 查询数据
        offset = (page - 1) * page_size
        query_sql = "SELECT * FROM unified_content"
        if where_conditions:
            conditions = " AND ".join([f"{k} = '{v}'" for k, v in where_conditions.items()])
            query_sql += f" WHERE {conditions}"
        query_sql += f" ORDER BY add_ts DESC LIMIT {page_size} OFFSET {offset}"
        
        results = await async_db_conn.query(query_sql)
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "items": results
        }
        
    except Exception as e:
        utils.logger.error(f"获取内容列表失败: {e}")
        raise


async def get_comment_list(content_id: str = None, platform: str = None, page: int = 1, page_size: int = 20) -> Dict:
    """获取评论列表"""
    try:
        async_db_conn: AsyncMysqlDB = await _get_db_connection()
        
        # 构建查询条件
        where_conditions = {}
        if content_id:
            where_conditions["content_id"] = content_id
        if platform:
            where_conditions["platform"] = platform
        
        # 查询总数
        count_sql = "SELECT COUNT(*) as total FROM unified_comment"
        if where_conditions:
            conditions = " AND ".join([f"{k} = '{v}'" for k, v in where_conditions.items()])
            count_sql += f" WHERE {conditions}"
        
        count_result = await async_db_conn.get_first(count_sql)
        total = count_result['total'] if count_result else 0
        
        # 查询数据
        offset = (page - 1) * page_size
        query_sql = "SELECT * FROM unified_comment"
        if where_conditions:
            conditions = " AND ".join([f"{k} = '{v}'" for k, v in where_conditions.items()])
            query_sql += f" WHERE {conditions}"
        query_sql += f" ORDER BY add_ts DESC LIMIT {page_size} OFFSET {offset}"
        
        results = await async_db_conn.query(query_sql)
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "items": results
        }
        
    except Exception as e:
        utils.logger.error(f"获取评论列表失败: {e}")
        raise 