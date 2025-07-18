"""
内容管理路由模块
包含内容查询、详情获取等功能
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import utils
from models.content_models import (
    ContentListRequest, ContentListResponse, UnifiedContent
)
from var import media_crawler_db_var

router = APIRouter()

async def get_unified_content_from_db(request: ContentListRequest) -> ContentListResponse:
    """从数据库获取统一格式的内容列表"""
    try:
        from models.content_models import PLATFORM_MAPPING
        
        all_contents = []
        platforms_summary = {}
        
        # 确定要查询的平台
        platforms_to_query = []
        if request.platform:
            # 指定平台
            if request.platform in PLATFORM_MAPPING:
                platforms_to_query = [request.platform]
            else:
                raise HTTPException(status_code=400, detail=f"不支持的平台: {request.platform}")
        else:
            # 所有平台
            platforms_to_query = list(PLATFORM_MAPPING.keys())
        
        # 过滤平台
        if request.video_platforms_only:
            from models.content_models import VIDEO_PRIORITY_PLATFORMS
            platforms_to_query = [p for p in platforms_to_query if p in VIDEO_PRIORITY_PLATFORMS]
        
        if request.exclude_todo_platforms:
            from models.content_models import TODO_PLATFORMS
            platforms_to_query = [p for p in platforms_to_query if p not in TODO_PLATFORMS]
        
        # 为每个平台查询数据
        for platform_key in platforms_to_query:
            try:
                platform_info = PLATFORM_MAPPING[platform_key]
                table_name = platform_info["table"]
                id_field = platform_info["id_field"]
                platform_name = platform_info["name"]
                
                # 构建查询条件
                where_conditions = []
                params = []
                
                # 关键词搜索
                if request.keyword:
                    keyword_conditions = []
                    if "keyword_fields" in platform_info:
                        for field in platform_info["keyword_fields"]:
                            keyword_conditions.append(f"{field} LIKE %s")
                            params.append(f"%{request.keyword}%")
                    else:
                        # 默认搜索字段
                        keyword_conditions.append("(title LIKE %s OR `desc` LIKE %s)")
                        params.extend([f"%{request.keyword}%", f"%{request.keyword}%"])
                    
                    if keyword_conditions:
                        where_conditions.append(f"({' OR '.join(keyword_conditions)})")
                
                # 视频内容过滤
                if request.video_only and "video_filter" in platform_info:
                    where_conditions.append(platform_info["video_filter"])
                
                # 时间范围过滤
                if request.start_time:
                    where_conditions.append("add_ts >= %s")
                    params.append(int(request.start_time.timestamp()))
                
                if request.end_time:
                    where_conditions.append("add_ts <= %s")
                    params.append(int(request.end_time.timestamp()))
                
                # 构建WHERE子句
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # 排序字段映射
                sort_field_mapping = {
                    "crawl_time": "add_ts",
                    "publish_time": "create_time",
                    "like_count": "liked_count",
                    "comment_count": "comment_count",
                    "share_count": "share_count"
                }
                sort_field = sort_field_mapping.get(request.sort_by, "add_ts")
                sort_order = "DESC" if request.sort_order == "desc" else "ASC"
                
                # 计算偏移量
                offset = (request.page - 1) * request.page_size
                
                # 查询总数
                async_db_obj = media_crawler_db_var.get()
                count_sql = f"SELECT COUNT(*) as total FROM {table_name} {where_clause}"
                count_result = await async_db_obj.query(count_sql, *params)
                total_count = count_result[0]['total'] if count_result else 0
                platforms_summary[platform_key] = total_count
                
                if total_count == 0:
                    continue
                
                # 查询数据
                data_sql = f"""
                SELECT * FROM {table_name} 
                {where_clause}
                ORDER BY {sort_field} {sort_order}
                LIMIT %s OFFSET %s
                """
                params.extend([request.page_size, offset])
                rows = await async_db_obj.query(data_sql, *params)
                
                # 转换为统一格式
                for row in rows:
                    unified_content = convert_to_unified_content(row, platform_key, platform_name, id_field)
                    if unified_content:
                        all_contents.append(unified_content)
                        
            except Exception as e:
                utils.logger.error(f"查询平台 {platform_key} 数据失败: {e}")
                platforms_summary[platform_key] = 0
                continue
        
        # 如果是跨平台查询，需要重新排序和分页
        if not request.platform:
            # 按指定字段排序
            if request.sort_by == "crawl_time":
                all_contents.sort(key=lambda x: x.crawl_time or 0, reverse=(request.sort_order == "desc"))
            elif request.sort_by == "publish_time":
                all_contents.sort(key=lambda x: x.publish_time or 0, reverse=(request.sort_order == "desc"))
            elif request.sort_by == "like_count":
                all_contents.sort(key=lambda x: int(str(x.like_count or 0).replace(',', '')), reverse=(request.sort_order == "desc"))
            
            # 重新分页
            total = len(all_contents)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            all_contents = all_contents[start_idx:end_idx]
        else:
            total = platforms_summary.get(request.platform, 0)
        
        total_pages = (total + request.page_size - 1) // request.page_size
        
        return ContentListResponse(
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            items=all_contents,
            platforms_summary=platforms_summary
        )
        
    except Exception as e:
        utils.logger.error(f"获取统一内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取内容失败: {str(e)}")

def convert_to_unified_content(row: Dict, platform: str, platform_name: str, id_field: str) -> Optional[UnifiedContent]:
    """将数据库行转换为统一格式"""
    try:
        # 基础信息
        content_id = str(row.get(id_field, ''))
        title = row.get('title', '')
        description = row.get('desc', '') or row.get('content', '') or row.get('content_text', '')
        
        # 判断内容类型
        content_type = "text"
        if platform in ["dy", "ks", "bili"]:
            content_type = "video"
        elif platform == "xhs":
            note_type = row.get('type', '')
            if note_type == "video":
                content_type = "video"
            elif row.get('image_list'):
                content_type = "image"
            else:
                content_type = "text"
        elif platform == "wb":
            if row.get('image_list') or row.get('video_url'):
                content_type = "mixed"
        elif platform == "zhihu":
            zhihu_type = row.get('content_type', '')
            if zhihu_type == "zvideo":
                content_type = "video"
            else:
                content_type = "text"
        
        # 作者信息
        author_id = str(row.get('user_id', ''))
        author_name = row.get('nickname', '') or row.get('user_nickname', '')
        author_avatar = row.get('avatar', '') or row.get('user_avatar', '')
        
        # 统计数据
        like_count = row.get('liked_count') or row.get('voteup_count') or row.get('like_count') or 0
        comment_count = row.get('comment_count') or row.get('comments_count') or 0
        share_count = row.get('share_count') or row.get('shared_count') or 0
        view_count = row.get('video_play_count') or row.get('viewd_count') or row.get('view_count') or 0
        collect_count = row.get('collected_count') or row.get('video_favorite_count') or 0
        
        # 时间信息
        publish_time = None
        publish_time_str = None
        crawl_time = row.get('add_ts')
        crawl_time_str = None
        
        # 根据平台获取发布时间
        if platform in ["xhs"]:
            publish_time = row.get('time')
        elif platform in ["dy", "ks", "bili"]:
            publish_time = row.get('create_time')
        elif platform == "wb":
            publish_time = row.get('create_time')
            publish_time_str = row.get('create_date_time')
        elif platform == "zhihu":
            created_time_str = row.get('created_time')
            if created_time_str:
                try:
                    publish_time = int(datetime.fromisoformat(created_time_str).timestamp())
                except:
                    pass
                publish_time_str = created_time_str
        elif platform == "tieba":
            publish_time_str = row.get('publish_time')
        
        # 格式化时间字符串
        if publish_time and not publish_time_str:
            try:
                publish_time_str = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        if crawl_time:
            try:
                crawl_time_str = datetime.fromtimestamp(crawl_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 关联信息
        source_keyword = row.get('source_keyword', '')
        content_url = row.get('note_url') or row.get('aweme_url') or row.get('video_url') or row.get('content_url') or ''
        cover_url = row.get('cover_url') or row.get('video_cover_url') or ''
        video_url = row.get('video_url') or row.get('video_play_url') or row.get('video_download_url') or ''
        
        # 标签处理
        tags = []
        tag_list = row.get('tag_list', '')
        if tag_list:
            try:
                import json
                if isinstance(tag_list, str):
                    if tag_list.startswith('['):
                        tags = json.loads(tag_list)
                    else:
                        tags = [tag.strip() for tag in tag_list.split(',') if tag.strip()]
                elif isinstance(tag_list, list):
                    tags = tag_list
            except:
                pass
        
        # IP地理位置
        ip_location = row.get('ip_location', '')
        
        return UnifiedContent(
            id=row.get('id', 0),
            platform=platform,
            platform_name=platform_name,
            content_id=content_id,
            content_type=content_type,
            title=title,
            description=description[:500] if description else None,  # 限制描述长度
            content=description,
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            view_count=view_count,
            collect_count=collect_count,
            publish_time=publish_time,
            publish_time_str=publish_time_str,
            crawl_time=crawl_time,
            crawl_time_str=crawl_time_str,
            source_keyword=source_keyword,
            content_url=content_url,
            cover_url=cover_url,
            video_url=video_url,
            tags=tags,
            ip_location=ip_location,
            extra_data=None
        )
        
    except Exception as e:
        utils.logger.error(f"转换统一内容失败: {e}")
        return None

@router.post("/content/list", response_model=ContentListResponse)
async def get_content_list(request: ContentListRequest):
    """获取内容列表"""
    try:
        utils.logger.info(f"[CONTENT_LIST] 收到内容查询请求: {request}")
        result = await get_unified_content_from_db(request)
        utils.logger.info(f"[CONTENT_LIST] 查询完成: 总数={result.total}, 返回{len(result.items)}条")
        return result
    except Exception as e:
        utils.logger.error(f"[CONTENT_LIST] 查询内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询内容失败: {str(e)}")

@router.get("/content/{platform}/{content_id}", response_model=UnifiedContent)
async def get_content_detail(platform: str, content_id: str):
    """获取内容详情"""
    try:
        from models.content_models import PLATFORM_MAPPING
        
        if platform not in PLATFORM_MAPPING:
            raise HTTPException(status_code=400, detail="不支持的平台")
        
        platform_info = PLATFORM_MAPPING[platform]
        table_name = platform_info["table"]
        id_field = platform_info["id_field"]
        platform_name = platform_info["name"]
        
        # 查询数据
        async_db_obj = media_crawler_db_var.get()
        sql = f"SELECT * FROM {table_name} WHERE {id_field} = %s LIMIT 1"
        rows = await async_db_obj.query(sql, content_id)
        
        if not rows:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        row = rows[0]
        unified_content = convert_to_unified_content(row, platform, platform_name, id_field)
        
        if not unified_content:
            raise HTTPException(status_code=500, detail="数据转换失败")
        
        utils.logger.info(f"[CONTENT_DETAIL] 获取详情成功: {unified_content.title}")
        return unified_content
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[CONTENT_DETAIL] 获取内容详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取内容详情失败: {str(e)}")

@router.get("/content/platforms")
async def get_platforms_info():
    """获取平台信息和统计"""
    try:
        from models.content_models import (
            PLATFORM_MAPPING, 
            VIDEO_PRIORITY_PLATFORMS, 
            TODO_PLATFORMS,
            get_platform_description,
            is_video_priority_platform
        )
        
        platforms_info = {}
        
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            try:
                async_db_obj = media_crawler_db_var.get()
                sql = f"SELECT COUNT(*) as total FROM {platform_info['table']}"
                result = await async_db_obj.query(sql)
                total_count = result[0]['total'] if result else 0
                
                # 统计视频内容数量
                video_count = 0
                if "video_filter" in platform_info and platform_info["video_filter"]:
                    video_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']} WHERE {platform_info['video_filter']}"
                    video_result = await async_db_obj.query(video_sql)
                    video_count = video_result[0]['total'] if video_result else 0
                
                # 获取最近的关键词
                recent_keywords_sql = f"""
                SELECT source_keyword, COUNT(*) as count 
                FROM {platform_info['table']} 
                WHERE source_keyword IS NOT NULL AND source_keyword != ''
                GROUP BY source_keyword 
                ORDER BY count DESC, MAX(add_ts) DESC
                LIMIT 5
                """
                keywords_result = await async_db_obj.query(recent_keywords_sql)
                recent_keywords = [row['source_keyword'] for row in keywords_result]
                
                platforms_info[platform_key] = {
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": total_count,
                    "video_count": video_count,
                    "video_ratio": round(video_count / total_count * 100, 1) if total_count > 0 else 0,
                    "recent_keywords": recent_keywords,
                    "is_video_priority": is_video_priority_platform(platform_key),
                    "is_todo": platform_key in TODO_PLATFORMS,
                    "primary_content_type": platform_info.get("primary_content_type", "mixed")
                }
                
            except Exception as e:
                utils.logger.error(f"获取平台 {platform_key} 统计失败: {e}")
                platforms_info[platform_key] = {
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": 0,
                    "video_count": 0,
                    "video_ratio": 0,
                    "recent_keywords": [],
                    "is_video_priority": is_video_priority_platform(platform_key),
                    "is_todo": platform_key in TODO_PLATFORMS,
                    "primary_content_type": platform_info.get("primary_content_type", "mixed")
                }
        
        return {
            "platforms": platforms_info,
            "total_platforms": len(platforms_info),
            "video_priority_platforms": VIDEO_PRIORITY_PLATFORMS,
            "todo_platforms": TODO_PLATFORMS,
            "total_content": sum(info["total_count"] for info in platforms_info.values()),
            "total_video_content": sum(info["video_count"] for info in platforms_info.values())
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台信息失败: {str(e)}")

@router.post("/content/videos", response_model=ContentListResponse)
async def get_video_content_list(
    keyword: Optional[str] = None,
    platform: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取短视频内容列表 - 专注短视频优先平台"""
    try:
        utils.logger.info(f"[VIDEO_CONTENT] 收到短视频内容查询请求: keyword={keyword}, platform={platform}")
        
        # 构建专门的短视频查询请求
        request = ContentListRequest(
            platform=platform,
            keyword=keyword,
            page=page,
            page_size=page_size,
            video_only=True,  # 仅视频内容
            video_platforms_only=True,  # 仅视频优先平台
            exclude_todo_platforms=True,  # 排除TODO平台
            sort_by="crawl_time",
            sort_order="desc"
        )
        
        result = await get_unified_content_from_db(request)
        
        utils.logger.info(f"[VIDEO_CONTENT] 短视频查询完成: 总数={result.total}, 返回{len(result.items)}条视频")
        return result
        
    except Exception as e:
        utils.logger.error(f"[VIDEO_CONTENT] 查询短视频内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询短视频内容失败: {str(e)}")

@router.get("/content/video-platforms")
async def get_video_platforms_info():
    """获取短视频优先平台信息"""
    try:
        from models.content_models import (
            VIDEO_PRIORITY_PLATFORMS, 
            PLATFORM_MAPPING,
            get_platform_description
        )
        
        video_platforms = []
        for platform_key in VIDEO_PRIORITY_PLATFORMS:
            if platform_key in PLATFORM_MAPPING:
                platform_info = PLATFORM_MAPPING[platform_key]
                
                # 获取视频数量统计
                video_count = 0
                total_count = 0
                try:
                    async_db_obj = media_crawler_db_var.get()
                    # 总数量
                    total_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']}"
                    total_result = await async_db_obj.query(total_sql)
                    total_count = total_result[0]['total'] if total_result else 0
                    
                    # 视频数量
                    if "video_filter" in platform_info and platform_info["video_filter"]:
                        video_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']} WHERE {platform_info['video_filter']}"
                        video_result = await async_db_obj.query(video_sql)
                        video_count = video_result[0]['total'] if video_result else 0
                    else:
                        video_count = total_count  # 如果没有视频筛选，假设全部是视频
                except:
                    pass
                
                video_platforms.append({
                    "code": platform_key,
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": total_count,
                    "video_count": video_count,
                    "video_ratio": round(video_count / total_count * 100, 1) if total_count > 0 else 100,
                    "primary_content_type": platform_info.get("primary_content_type", "video")
                })
        
        return {
            "video_priority_platforms": video_platforms,
            "total_platforms": len(video_platforms),
            "total_video_content": sum(p["video_count"] for p in video_platforms),
            "message": "本平台专注于短视频内容，以上为主要短视频平台"
        }
        
    except Exception as e:
        utils.logger.error(f"获取短视频平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取短视频平台信息失败: {str(e)}") 