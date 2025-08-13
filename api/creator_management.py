"""
创作者管理API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import logging
import time
import json

from utils.db_utils import _get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/creators/add", response_model=Dict[str, Any])
async def add_creator(creator_data: Dict[str, Any]):
    """添加创作者"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        original_platform = creator_data.get("platform")
        mapped_platform = platform_mapping.get(original_platform, original_platform)
        if original_platform != mapped_platform:
            logger.info(f"平台代码映射: {original_platform} -> {mapped_platform}")
            creator_data["platform"] = mapped_platform
        
        # 验证必填字段
        required_fields = ["creator_id", "platform", "name"]
        for field in required_fields:
            if not creator_data.get(field):
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")
        
        # 检查是否已存在
        check_query = """
            SELECT id FROM unified_creator 
            WHERE creator_id = %s AND platform = %s
        """
        existing = await db.get_first(check_query, creator_data["creator_id"], creator_data["platform"])
        if existing:
            raise HTTPException(status_code=400, detail="创作者已存在")
        
        # 准备数据
        now_ts = int(time.time() * 1000)
        creator_data.update({
            "add_ts": now_ts,
            "last_modify_ts": now_ts
        })
        
        # 序列化JSON字段
        if "tags" in creator_data and isinstance(creator_data["tags"], dict):
            creator_data["tags"] = json.dumps(creator_data["tags"], ensure_ascii=False)
        if "categories" in creator_data and isinstance(creator_data["categories"], list):
            creator_data["categories"] = json.dumps(creator_data["categories"], ensure_ascii=False)
        if "metadata" in creator_data and isinstance(creator_data["metadata"], dict):
            creator_data["metadata"] = json.dumps(creator_data["metadata"], ensure_ascii=False)
        if "raw_data" in creator_data and isinstance(creator_data["raw_data"], dict):
            creator_data["raw_data"] = json.dumps(creator_data["raw_data"], ensure_ascii=False)
        if "extra_info" in creator_data and isinstance(creator_data["extra_info"], dict):
            creator_data["extra_info"] = json.dumps(creator_data["extra_info"], ensure_ascii=False)
        
        # 插入数据库
        creator_id = await db.item_to_table("unified_creator", creator_data)
        
        return {
            "code": 200,
            "message": "创作者添加成功",
            "data": {"creator_id": creator_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加创作者失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加创作者失败: {str(e)}")

@router.get("/creators", response_model=Dict[str, Any])
async def get_creators(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    platform: Optional[str] = Query(None, description="平台"),
    keyword: Optional[str] = Query(None, description="搜索关键词")
):
    """获取创作者列表"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 如果提供了平台参数，进行映射
        if platform:
            mapped_platform = platform_mapping.get(platform, platform)
            logger.info(f"平台代码映射: {platform} -> {mapped_platform}")
            platform = mapped_platform
        
        # 构建查询条件
        where_conditions = ["is_deleted = 0"]
        params = []
        
        if platform:
            where_conditions.append("platform = %s")
            params.append(platform)
        
        if keyword:
            where_conditions.append("(name LIKE %s OR nickname LIKE %s OR creator_id LIKE %s)")
            keyword_param = f"%{keyword}%"
            params.extend([keyword_param, keyword_param, keyword_param])
        
        where_clause = " AND ".join(where_conditions)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM unified_creator WHERE {where_clause}"
        count_result = await db.get_first(count_query, *params)
        total = count_result.get('total', 0) if count_result else 0
        
        if total == 0:
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "creators": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }
            }
        
        # 分页查询
        offset = (page - 1) * page_size
        query = f"""
            SELECT * FROM unified_creator 
            WHERE {where_clause}
            ORDER BY add_ts DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        
        results = await db.query(query, *params)
        
        # 处理JSON字段
        creators = []
        for row in results:
            creator = dict(row)
            # 解析JSON字段
            for field in ["tags", "categories", "metadata", "raw_data", "extra_info"]:
                if creator.get(field):
                    try:
                        creator[field] = json.loads(creator[field])
                    except:
                        pass
            creators.append(creator)
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "creators": creators,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        logger.error(f"获取创作者列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取创作者列表失败: {str(e)}")

@router.get("/creators/{creator_id}", response_model=Dict[str, Any])
async def get_creator_detail(creator_id: str, platform: str = Query(..., description="平台")):
    """获取创作者详情"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        mapped_platform = platform_mapping.get(platform, platform)
        logger.info(f"平台代码映射: {platform} -> {mapped_platform}")
        
        query = """
            SELECT * FROM unified_creator 
            WHERE creator_id = %s AND platform = %s AND is_deleted = 0
        """
        result = await db.get_first(query, creator_id, mapped_platform)
        
        if not result:
            raise HTTPException(status_code=404, detail="创作者不存在")
        
        # 处理JSON字段
        creator = dict(result)
        for field in ["tags", "categories", "metadata", "raw_data", "extra_info"]:
            if creator.get(field):
                try:
                    creator[field] = json.loads(creator[field])
                except:
                    pass
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": creator
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取创作者详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取创作者详情失败: {str(e)}")

@router.get("/creators/{creator_id}/detail", response_model=Dict[str, Any])
async def get_creator_detail_info(creator_id: str, platform: str = Query(..., description="平台")):
    """获取创作者详细信息"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        mapped_platform = platform_mapping.get(platform, platform)
        logger.info(f"平台代码映射: {platform} -> {mapped_platform}")
        
        # 获取创作者基本信息
        creator_query = """
            SELECT * FROM unified_creator 
            WHERE creator_id = %s AND platform = %s AND is_deleted = 0
        """
        creator = await db.get_first(creator_query, creator_id, mapped_platform)
        
        if not creator:
            raise HTTPException(status_code=404, detail="创作者不存在")
        
        # 获取创作者的内容统计
        content_stats_query = """
            SELECT 
                COUNT(*) as total_content,
                SUM(view_count) as total_views,
                SUM(like_count) as total_likes,
                SUM(comment_count) as total_comments,
                SUM(collect_count) as total_collects,
                SUM(share_count) as total_shares,
                AVG(view_count) as avg_views,
                AVG(like_count) as avg_likes,
                AVG(comment_count) as avg_comments,
                MAX(create_time) as latest_content_time,
                MIN(create_time) as earliest_content_time
            FROM unified_content 
            WHERE author_id = %s AND platform = %s AND is_deleted = 0
        """
        content_stats = await db.get_first(content_stats_query, creator_id, mapped_platform)
        
        # 获取创作者的最新内容（最近10条）
        recent_content_query = """
            SELECT 
                content_id, title, description, create_time,
                view_count, like_count, comment_count, collect_count, share_count,
                video_url, cover_url, tags, categories
            FROM unified_content 
            WHERE author_id = %s AND platform = %s AND is_deleted = 0
            ORDER BY create_time DESC 
            LIMIT 10
        """
        recent_content = await db.query(recent_content_query, creator_id, mapped_platform)
        
        # 获取创作者的内容趋势（按月份统计）
        trend_query = """
            SELECT 
                DATE_FORMAT(FROM_UNIXTIME(create_time), '%%Y-%%m') as month,
                COUNT(*) as content_count,
                SUM(view_count) as total_views,
                SUM(like_count) as total_likes,
                SUM(comment_count) as total_comments
            FROM unified_content 
            WHERE author_id = %s AND platform = %s AND is_deleted = 0
            GROUP BY DATE_FORMAT(FROM_UNIXTIME(create_time), '%%Y-%%m')
            ORDER BY month DESC
            LIMIT 12
        """
        content_trends = await db.query(trend_query, creator_id, mapped_platform)
        
        # 获取热门标签
        tags_query = """
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(tags, '$[*]')) as tag_list
            FROM unified_content 
            WHERE author_id = %s AND platform = %s AND is_deleted = 0
            AND tags IS NOT NULL AND tags != ''
        """
        tags_result = await db.query(tags_query, creator_id, mapped_platform)
        
        # 统计标签使用频率
        tag_frequency = {}
        for row in tags_result:
            if row.get('tag_list'):
                try:
                    tags = json.loads(row['tag_list'])
                    if isinstance(tags, list):
                        for tag in tags:
                            tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
                except:
                    pass
        
        # 按频率排序标签
        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 构建详情数据
        detail_data = {
            "creator_info": creator,
            "content_stats": content_stats or {},
            "recent_content": recent_content or [],
            "content_trends": content_trends or [],
            "popular_tags": [{"tag": tag, "count": count} for tag, count in sorted_tags],
            "platform_info": {
                "platform": mapped_platform,
                "platform_name": get_platform_name(mapped_platform),
                "creator_url": generate_creator_url(creator_id, mapped_platform, creator)
            }
        }
        
        return {
            "code": 200,
            "message": "获取创作者详情成功",
            "data": detail_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取创作者详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取创作者详情失败: {str(e)}")


def get_platform_name(platform: str) -> str:
    """获取平台中文名称"""
    platform_names = {
        'dy': '抖音',
        'xhs': '小红书', 
        'ks': '快手',
        'bili': '哔哩哔哩',
        'wb': '微博',
        'zhihu': '知乎',
        'tieba': '贴吧'
    }
    return platform_names.get(platform, platform)


def generate_creator_url(creator_id: str, platform: str, creator_info: Dict[str, Any]) -> str:
    """生成创作者主页URL"""
    if platform == 'dy':
        # 抖音：优先使用sec_uid，如果没有则使用creator_id
        sec_uid = creator_info.get('sec_uid')
        if sec_uid:
            return f'https://www.douyin.com/user/{sec_uid}'
        else:
            return f'https://www.douyin.com/user/{creator_id}'
    elif platform == 'xhs':
        # 小红书：使用unique_id或creator_id
        unique_id = creator_info.get('unique_id')
        if unique_id:
            return f'https://www.xiaohongshu.com/user/profile/{unique_id}'
        else:
            return f'https://www.xiaohongshu.com/user/profile/{creator_id}'
    elif platform == 'ks':
        # 快手：使用short_id或creator_id
        short_id = creator_info.get('short_id')
        if short_id:
            return f'https://www.kuaishou.com/short-video/{short_id}'
        else:
            return f'https://www.kuaishou.com/short-video/{creator_id}'
    elif platform == 'bili':
        # B站：使用uid或creator_id
        uid = creator_info.get('uid')
        if uid:
            return f'https://space.bilibili.com/{uid}'
        else:
            return f'https://space.bilibili.com/{creator_id}'
    elif platform == 'wb':
        # 微博：使用uid或creator_id
        uid = creator_info.get('uid')
        if uid:
            return f'https://weibo.com/u/{uid}'
        else:
            return f'https://weibo.com/u/{creator_id}'
    elif platform == 'zhihu':
        # 知乎：使用url_token或creator_id
        url_token = creator_info.get('url_token')
        if url_token:
            return f'https://www.zhihu.com/people/{url_token}'
        else:
            return f'https://www.zhihu.com/people/{creator_id}'
    elif platform == 'tieba':
        # 贴吧：使用username或creator_id
        username = creator_info.get('username')
        if username:
            return f'https://tieba.baidu.com/home/main?un={username}'
        else:
            return f'https://tieba.baidu.com/home/main?un={creator_id}'
    else:
        return '#'

@router.put("/creators/{creator_id}", response_model=Dict[str, Any])
async def update_creator(creator_id: str, creator_data: Dict[str, Any]):
    """更新创作者信息"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        original_platform = creator_data.get("platform")
        mapped_platform = platform_mapping.get(original_platform, original_platform)
        if original_platform != mapped_platform:
            logger.info(f"平台代码映射: {original_platform} -> {mapped_platform}")
            creator_data["platform"] = mapped_platform
        
        # 检查是否存在
        check_query = """
            SELECT id FROM unified_creator 
            WHERE creator_id = %s AND platform = %s AND is_deleted = 0
        """
        existing = await db.get_first(check_query, creator_id, creator_data.get("platform"))
        if not existing:
            raise HTTPException(status_code=404, detail="创作者不存在")
        
        # 准备更新数据
        now_ts = int(time.time() * 1000)
        creator_data["last_modify_ts"] = now_ts
        
        # 序列化JSON字段
        for field in ["tags", "categories", "metadata", "raw_data", "extra_info"]:
            if field in creator_data and isinstance(creator_data[field], (dict, list)):
                creator_data[field] = json.dumps(creator_data[field], ensure_ascii=False)
        
        # 构建更新SQL
        set_clauses = []
        values = []
        for key, value in creator_data.items():
            if key != "creator_id" and key != "platform":  # 不允许更新主键
                set_clauses.append(f"`{key}` = %s")
                values.append(value)
        
        set_clause = ", ".join(set_clauses)
        values.extend([creator_id, creator_data.get("platform")])
        
        update_query = f"""
            UPDATE unified_creator 
            SET {set_clause}
            WHERE creator_id = %s AND platform = %s
        """
        
        await db.execute(update_query, *values)
        
        return {
            "code": 200,
            "message": "创作者更新成功",
            "data": {"creator_id": creator_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新创作者失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新创作者失败: {str(e)}")

@router.delete("/creators/{creator_id}", response_model=Dict[str, Any])
async def delete_creator(creator_id: str, platform: str = Query(..., description="平台")):
    """删除创作者（软删除）"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        mapped_platform = platform_mapping.get(platform, platform)
        logger.info(f"平台代码映射: {platform} -> {mapped_platform}")
        
        # 软删除
        now_ts = int(time.time() * 1000)
        update_query = """
            UPDATE unified_creator 
            SET is_deleted = 1, last_modify_ts = %s
            WHERE creator_id = %s AND platform = %s
        """
        
        result = await db.execute(update_query, now_ts, creator_id, mapped_platform)
        
        if result == 0:
            raise HTTPException(status_code=404, detail="创作者不存在")
        
        return {
            "code": 200,
            "message": "创作者删除成功",
            "data": {"creator_id": creator_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除创作者失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除创作者失败: {str(e)}")

@router.post("/creators/from-content", response_model=Dict[str, Any])
async def add_creator_from_content(content_data: Dict[str, Any]):
    """从内容数据中提取并添加创作者"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 从内容数据中提取创作者信息
        original_platform = content_data.get("platform")
        mapped_platform = platform_mapping.get(original_platform, original_platform)
        
        creator_data = {
            "creator_id": content_data.get("author_id"),
            "platform": mapped_platform,
            "name": content_data.get("author_name"),
            "nickname": content_data.get("author_nickname"),
            "avatar": content_data.get("author_avatar"),
            "signature": content_data.get("author_signature"),
            "unique_id": content_data.get("author_unique_id"),
            "sec_uid": content_data.get("author_sec_uid"),
            "short_id": content_data.get("author_short_id"),
            "ip_location": content_data.get("ip_location"),
            "add_ts": int(time.time() * 1000),
            "last_modify_ts": int(time.time() * 1000)
        }
        
        if original_platform != mapped_platform:
            logger.info(f"平台代码映射: {original_platform} -> {mapped_platform}")
        
        # 验证必填字段
        if not creator_data["creator_id"] or not creator_data["platform"]:
            raise HTTPException(status_code=400, detail="缺少创作者ID或平台信息")
        
        # 检查是否已存在
        check_query = """
            SELECT id FROM unified_creator 
            WHERE creator_id = %s AND platform = %s
        """
        existing = await db.get_first(check_query, creator_data["creator_id"], creator_data["platform"])
        if existing:
            return {
                "code": 200,
                "message": "创作者已存在",
                "data": {"creator_id": creator_data["creator_id"]}
            }
        
        # 插入数据库
        creator_id = await db.item_to_table("unified_creator", creator_data)
        
        return {
            "code": 200,
            "message": "创作者添加成功",
            "data": {"creator_id": creator_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从内容添加创作者失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"从内容添加创作者失败: {str(e)}") 

@router.post("/creators/refresh", response_model=Dict[str, Any])
async def refresh_creator_data(creator_data: Dict[str, Any]):
    """刷新创作者数据（获取最新的粉丝、关注、获赞等数据）"""
    try:
        creator_id = creator_data.get("creator_id")
        platform = creator_data.get("platform")
        
        if not creator_id or not platform:
            raise HTTPException(status_code=400, detail="缺少创作者ID或平台信息")
        
        # 🆕 平台代码映射：前端代码 -> 数据库代码
        platform_mapping = {
            'dy': 'douyin',
            'ks': 'kuaishou',
            'xhs': 'xhs',
            'bili': 'bilibili',
            'wb': 'weibo',
            'tieba': 'tieba',
            'zhihu': 'zhihu'
        }
        
        # 进行平台代码映射
        mapped_platform = platform_mapping.get(platform, platform)
        if platform != mapped_platform:
            logger.info(f"平台代码映射: {platform} -> {mapped_platform}")
        
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 获取创作者信息
        query = """
            SELECT * FROM unified_creator 
            WHERE creator_id = %s AND platform = %s AND is_deleted = 0
        """
        creator = await db.get_first(query, creator_id, mapped_platform)
        
        if not creator:
            raise HTTPException(status_code=404, detail="创作者不存在")
        
        # 根据平台获取最新数据
        updated_data = {}
        
        if mapped_platform == "douyin":  # 抖音
            try:
                # TODO: 实现抖音创作者数据刷新
                # 这里需要调用抖音的API获取最新数据
                # 暂时返回模拟数据
                updated_data = {
                    "fans_count": 1000 + (hash(creator_id) % 1000),  # 模拟数据
                    "follow_count": 100 + (hash(creator_id) % 100),
                    "like_count": 5000 + (hash(creator_id) % 5000),
                    "content_count": 50 + (hash(creator_id) % 50),
                    "last_refresh_ts": int(time.time() * 1000)
                }
            except Exception as e:
                logger.error(f"刷新抖音创作者数据失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"刷新抖音创作者数据失败: {str(e)}")
        
        elif mapped_platform == "xhs":  # 小红书
            try:
                # TODO: 实现小红书创作者数据刷新
                updated_data = {
                    "fans_count": 800 + (hash(creator_id) % 800),
                    "follow_count": 80 + (hash(creator_id) % 80),
                    "like_count": 4000 + (hash(creator_id) % 4000),
                    "content_count": 40 + (hash(creator_id) % 40),
                    "last_refresh_ts": int(time.time() * 1000)
                }
            except Exception as e:
                logger.error(f"刷新小红书创作者数据失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"刷新小红书创作者数据失败: {str(e)}")
        
        elif mapped_platform == "kuaishou":  # 快手
            try:
                # TODO: 实现快手创作者数据刷新
                updated_data = {
                    "fans_count": 1200 + (hash(creator_id) % 1200),
                    "follow_count": 120 + (hash(creator_id) % 120),
                    "like_count": 6000 + (hash(creator_id) % 6000),
                    "content_count": 60 + (hash(creator_id) % 60),
                    "last_refresh_ts": int(time.time() * 1000)
                }
            except Exception as e:
                logger.error(f"刷新快手创作者数据失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"刷新快手创作者数据失败: {str(e)}")
        
        elif mapped_platform == "bilibili":  # B站
            try:
                # TODO: 实现B站创作者数据刷新
                updated_data = {
                    "fans_count": 2000 + (hash(creator_id) % 2000),
                    "follow_count": 200 + (hash(creator_id) % 200),
                    "like_count": 10000 + (hash(creator_id) % 10000),
                    "content_count": 100 + (hash(creator_id) % 100),
                    "last_refresh_ts": int(time.time() * 1000)
                }
            except Exception as e:
                logger.error(f"刷新B站创作者数据失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"刷新B站创作者数据失败: {str(e)}")
        
        else:
            # 其他平台暂时返回模拟数据
            updated_data = {
                "fans_count": 500 + (hash(creator_id) % 500),
                "follow_count": 50 + (hash(creator_id) % 50),
                "like_count": 2500 + (hash(creator_id) % 2500),
                "content_count": 25 + (hash(creator_id) % 25),
                "last_refresh_ts": int(time.time() * 1000)
            }
        
        # 更新数据库
        now_ts = int(time.time() * 1000)
        updated_data["last_modify_ts"] = now_ts
        
        # 构建更新SQL
        set_clauses = []
        values = []
        for key, value in updated_data.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        
        set_clause = ", ".join(set_clauses)
        values.extend([creator_id, platform])
        
        update_query = f"""
            UPDATE unified_creator 
            SET {set_clause}
            WHERE creator_id = %s AND platform = %s
        """
        
        await db.execute(update_query, *values)
        
        return {
            "code": 200,
            "message": "创作者数据刷新成功",
            "data": {
                "creator_id": creator_id,
                "platform": mapped_platform,
                "updated_data": updated_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新创作者数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新创作者数据失败: {str(e)}")

@router.post("/creators/refresh-all", response_model=Dict[str, Any])
async def refresh_all_creators_data():
    """刷新所有创作者数据"""
    try:
        db = await _get_db_connection()
        if not db:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        # 获取所有创作者
        query = """
            SELECT creator_id, platform FROM unified_creator 
            WHERE is_deleted = 0
            ORDER BY last_modify_ts DESC
            LIMIT 50
        """
        creators = await db.query(query)
        
        if not creators:
            return {
                "code": 200,
                "message": "没有找到需要刷新的创作者",
                "data": {"refreshed_count": 0}
            }
        
        refreshed_count = 0
        failed_count = 0
        
        for creator in creators:
            try:
                # 调用单个刷新接口
                refresh_response = await refresh_creator_data({"creator_id": creator["creator_id"], "platform": creator["platform"]})
                if refresh_response["code"] == 200:
                    refreshed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"刷新创作者 {creator['creator_id']} 失败: {str(e)}")
                failed_count += 1
        
        return {
            "code": 200,
            "message": f"批量刷新完成，成功: {refreshed_count}，失败: {failed_count}",
            "data": {
                "refreshed_count": refreshed_count,
                "failed_count": failed_count,
                "total_count": len(creators)
            }
        }
        
    except Exception as e:
        logger.error(f"批量刷新创作者数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量刷新创作者数据失败: {str(e)}") 