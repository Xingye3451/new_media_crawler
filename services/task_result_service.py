"""
任务结果服务层
处理爬虫任务结果相关的业务逻辑
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging

from utils.redis_manager import TaskResultRedisManager
from utils.db_utils import _get_db_connection
from config.base_config import *

logger = logging.getLogger(__name__)

class TaskResultService:
    """任务结果服务层"""
    
    def __init__(self):
        self.redis_manager = TaskResultRedisManager()
        
    async def get_task_results(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """获取任务结果列表"""
        try:
            # 从Redis获取任务结果
            results = await self.redis_manager.get_task_results(page=page, page_size=page_size)
            
            # 补充统计信息
            for result in results.get('results', []):
                if 'task_id' in result:
                    stats = await self.redis_manager.get_task_statistics(result['task_id'])
                    result['statistics'] = stats
            
            return results
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {str(e)}")
            return {
                'results': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        try:
            # 先从Redis获取任务基本信息
            task_info = await self.redis_manager.get_task_info(task_id)
            
            # 如果Redis没有，从数据库获取
            if not task_info:
                task_info = await self._get_task_from_database(task_id)
                if not task_info:
                    return None
            
            # 获取统计信息
            stats = await self._get_task_statistics_from_database(task_id)
            
            # 获取视频列表（前10个）
            videos = await self._get_task_videos_from_database(task_id, page=1, page_size=10)
            
            return {
                'task_info': task_info,
                'statistics': stats,
                'recent_videos': videos.get('videos', []),
                'total_videos': videos.get('total', 0)
            }
            
        except Exception as e:
            logger.error(f"获取任务详情失败 {task_id}: {str(e)}")
            return None
    
    async def get_task_videos(self, task_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取任务的视频列表"""
        try:
            # 先从Redis获取
            videos = await self.redis_manager.get_task_videos(task_id, page=page, page_size=page_size)
            
            # 如果Redis没有数据，从数据库获取
            if not videos.get('videos'):
                videos = await self._get_task_videos_from_database(task_id, page=page, page_size=page_size)
            
            return videos
        except Exception as e:
            logger.error(f"获取任务视频列表失败 {task_id}: {str(e)}")
            return {
                'videos': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def get_video_detail(self, platform: str, video_id: str) -> Optional[Dict[str, Any]]:
        """获取视频详情"""
        try:
            # 先从Redis查找
            video_data = await self.redis_manager.get_video_detail(platform, video_id)
            if video_data:
                return video_data
            
            # Redis没有，从数据库查找
            return await self._get_video_from_database(platform, video_id)
            
        except Exception as e:
            logger.error(f"获取视频详情失败 {platform}/{video_id}: {str(e)}")
            return None
    
    async def _get_video_from_database(self, platform: str, video_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取视频信息"""
        try:
            db = await _get_db_connection()
            
            # 使用统一内容表查询
            query = """
                SELECT * FROM unified_content 
                WHERE platform = %s AND content_id = %s
                ORDER BY add_ts DESC LIMIT 1
            """
            result = await db.get_first(query, platform, video_id)
            
            if result:
                # 获取热门评论
                comments = await self._get_hot_comments(platform, video_id)
                result['hot_comments'] = comments
                
                return result
            
            return None
                
        except Exception as e:
            logger.error(f"从数据库获取视频失败 {platform}/{video_id}: {str(e)}")
            return None
    
    async def _get_hot_comments(self, platform: str, video_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取热门评论"""
        try:
            db = await _get_db_connection()
            
            # 使用统一评论表查询
            query = """
                SELECT * FROM unified_comment 
                WHERE platform = %s AND content_id = %s
                ORDER BY like_count DESC, add_ts DESC 
                LIMIT %s
            """
            results = await db.query(query, platform, video_id, limit)
            
            return results
                
        except Exception as e:
            logger.error(f"获取热门评论失败 {platform}/{video_id}: {str(e)}")
            return []
    
    async def get_platform_videos(self, platform: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取平台视频列表"""
        try:
            db = await _get_db_connection()
            
            # 使用统一内容表查询
            # 查询总数
            count_query = """
                SELECT COUNT(*) as total FROM unified_content 
                WHERE platform = %s
            """
            count_result = await db.get_first(count_query, platform)
            total = count_result.get('total', 0) if count_result else 0
            
            if total == 0:
                return {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            # 查询数据
            offset = (page - 1) * page_size
            query = """
                SELECT * FROM unified_content 
                WHERE platform = %s
                ORDER BY add_ts DESC 
                LIMIT %s OFFSET %s
            """
            results = await db.query(query, platform, page_size, offset)
            
            # 转换数据格式
            videos = []
            for row in results:
                video_data = {
                    'aweme_id': row.get('content_id'),
                    'title': row.get('title') or row.get('description', ''),
                    'desc': row.get('description') or row.get('title', ''),
                    'nickname': row.get('author_nickname') or row.get('author_name', ''),
                    'user_name': row.get('author_nickname') or row.get('author_name', ''),
                    'create_time': row.get('create_time'),
                    'digg_count': row.get('like_count', 0),
                    'comment_count': row.get('comment_count', 0),
                    'collect_count': row.get('collect_count', 0),
                    'view_count': row.get('view_count', 0),
                    'video_url': row.get('video_download_url') or row.get('video_url') or row.get('video_play_url'),
                    'cover_url': row.get('cover_url'),
                    'aweme_url': row.get('content_id'),
                    'platform': platform
                }
                videos.append(video_data)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'videos': videos,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"获取平台视频失败 {platform}: {str(e)}")
            return {
                'videos': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 从Redis获取任务统计
            redis_stats = await self.redis_manager.get_system_statistics()
            
            # 从数据库获取额外统计
            db_stats = await self._get_database_statistics()
            
            # 合并统计信息
            return {
                'redis_stats': redis_stats,
                'database_stats': db_stats,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return {
                'redis_stats': {},
                'database_stats': {},
                'last_updated': datetime.now().isoformat()
            }
    
    async def _get_database_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = {}
            
            # 使用统一表进行统计
            db = await _get_db_connection()
            if not db:
                logger.error("无法获取数据库连接")
                return {
                    'total_videos': 0,
                    'platform_stats': {}
                }
            
            # 从统一内容表获取统计
            total_query = "SELECT COUNT(*) as total FROM unified_content"
            total_result = await db.get_first(total_query)
            total_videos = total_result['total'] if total_result else 0
            
            # 各平台统计
            platform_query = """
            SELECT platform, COUNT(*) as count 
            FROM unified_content 
            GROUP BY platform
            """
            platform_results = await db.query(platform_query)
            platform_stats = {}
            for row in platform_results:
                platform_stats[row['platform']] = row['count']
            
            # 评论统计
            comment_query = "SELECT COUNT(*) as total FROM unified_comment"
            comment_result = await db.get_first(comment_query)
            total_comments = comment_result['total'] if comment_result else 0
            
            # 创作者统计
            creator_query = "SELECT COUNT(*) as total FROM unified_creator"
            creator_result = await db.get_first(creator_query)
            total_creators = creator_result['total'] if creator_result else 0
            
            return {
                'total_videos': total_videos,
                'total_comments': total_comments,
                'total_creators': total_creators,
                'platform_stats': platform_stats
            }
            
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {
                'total_videos': 0,
                'total_comments': 0,
                'total_creators': 0,
                'platform_stats': {}
            }
    
    async def delete_task_result(self, task_id: str) -> bool:
        """删除任务结果"""
        try:
            return await self.redis_manager.delete_task_result(task_id)
        except Exception as e:
            logger.error(f"删除任务结果失败 {task_id}: {str(e)}")
            return False
    
    async def cleanup_expired_tasks(self, days: int = 7) -> int:
        """清理过期任务"""
        try:
            return await self.redis_manager.cleanup_expired_tasks(days)
        except Exception as e:
            logger.error(f"清理过期任务失败: {str(e)}")
            return 0

    async def _get_task_from_database(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取任务信息"""
        try:
            db = await _get_db_connection()
            
            # 查询crawler_tasks表
            query = """
                SELECT * FROM crawler_tasks 
                WHERE id = %s AND deleted = 0
            """
            result = await db.get_first(query, task_id)
            
            if result:
                return {
                    'task_id': result.get('id'),
                    'platform': result.get('platform'),
                    'keywords': result.get('keywords', ''),
                    'status': result.get('status'),
                    'created_at': result.get('created_at').isoformat() if result.get('created_at') else None,
                    'updated_at': result.get('updated_at').isoformat() if result.get('updated_at') else None,
                    'progress': result.get('progress'),
                    'result_count': result.get('result_count'),
                    'error_message': result.get('error_message'),
                    'user_id': result.get('user_id'),
                    'task_type': result.get('task_type')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"从数据库获取任务失败 {task_id}: {str(e)}")
            return None

    async def _get_task_statistics_from_database(self, task_id: str) -> Dict[str, Any]:
        """从数据库获取任务统计信息"""
        try:
            db = await _get_db_connection()
            
            # 获取任务信息
            task_query = """
                SELECT platform FROM crawler_tasks 
                WHERE id = %s AND deleted = 0
            """
            task_result = await db.get_first(task_query, task_id)
            
            if not task_result:
                return {
                    "total_videos": 0,
                    "total_comments": 0,
                    "avg_likes": 0.0,
                    "total_size": 0,
                    "platforms": "",
                    "completed_at": ""
                }
            
            platform = task_result.get('platform')
            
            # 使用统一表进行统计
            # 统计内容数量和平均点赞数
            content_stats_query = """
                SELECT 
                    COUNT(*) as total_videos,
                    AVG(like_count) as avg_likes,
                    SUM(like_count) as total_likes,
                    AVG(comment_count) as avg_comments,
                    SUM(comment_count) as total_comments,
                    SUM(view_count) as total_views
                FROM unified_content 
                WHERE task_id = %s
            """
            content_result = await db.get_first(content_stats_query, task_id)
            
            total_videos = content_result.get('total_videos', 0) if content_result else 0
            avg_likes = round(content_result.get('avg_likes', 0) or 0, 1) if content_result else 0
            avg_comments = round(content_result.get('avg_comments', 0) or 0, 1) if content_result else 0
            total_comments = content_result.get('total_comments', 0) if content_result else 0
            
            # 估算数据大小（每个视频假设平均10MB）
            estimated_size = total_videos * 10 * 1024 * 1024  # 10MB per video
            
            return {
                "total_videos": total_videos,
                "total_comments": int(total_comments) if total_comments else 0,
                "avg_comments": float(avg_comments) if avg_comments else 0.0,
                "avg_likes": float(avg_likes) if avg_likes else 0.0,
                "total_size": estimated_size,
                "platforms": platform,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"从数据库获取任务统计失败 {task_id}: {str(e)}")
            return {
                "total_videos": 0,
                "total_comments": 0,
                "avg_comments": 0.0,
                "avg_likes": 0.0,
                "total_size": 0,
                "platforms": "",
                "completed_at": ""
            }

    async def _get_task_videos_from_database(self, task_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """从数据库获取任务视频列表"""
        try:
            db = await _get_db_connection()
            
            # 获取任务信息
            task_query = """
                SELECT platform FROM crawler_tasks 
                WHERE id = %s AND deleted = 0
            """
            task_result = await db.get_first(task_query, task_id)
            
            if not task_result:
                return {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            platform = task_result.get('platform')
            
            # 使用统一内容表
            # 获取总数
            count_query = """
                SELECT COUNT(*) as total FROM unified_content 
                WHERE task_id = %s
            """
            count_result = await db.get_first(count_query, task_id)
            total = count_result.get('total', 0) if count_result else 0
            
            if total == 0:
                return {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            # 查询内容列表
            offset = (page - 1) * page_size
            content_query = """
                SELECT * FROM unified_content 
                WHERE task_id = %s
                ORDER BY add_ts DESC
                LIMIT %s OFFSET %s
            """
            content_result = await db.query(content_query, task_id, page_size, offset)
            
            # 转换内容数据格式
            videos = []
            for row in content_result:
                video_data = {
                    'aweme_id': row.get('content_id'),
                    'title': row.get('title') or row.get('description', ''),
                    'desc': row.get('description') or row.get('title', ''),
                    'nickname': row.get('author_nickname') or row.get('author_name', ''),
                    'user_name': row.get('author_nickname') or row.get('author_name', ''),
                    'author_name': row.get('author_name', ''),
                    'author_id': row.get('author_id', ''),
                    'author_nickname': row.get('author_nickname', ''),
                    'author_avatar': row.get('author_avatar', ''),
                    'author_signature': row.get('author_signature', ''),
                    'author_unique_id': row.get('author_unique_id', ''),
                    'author_sec_uid': row.get('author_sec_uid', ''),
                    'author_short_id': row.get('author_short_id', ''),
                    'user_id': row.get('user_id', ''),
                    'uid': row.get('uid', ''),
                    'avatar': row.get('avatar', ''),
                    'signature': row.get('signature', ''),
                    'unique_id': row.get('unique_id', ''),
                    'sec_uid': row.get('sec_uid', ''),
                    'short_id': row.get('short_id', ''),
                    'ip_location': row.get('ip_location', ''),
                    'create_time': row.get('create_time'),
                    'digg_count': row.get('like_count', 0),
                    'comment_count': row.get('comment_count', 0),
                    'collect_count': row.get('collect_count', 0),
                    'view_count': row.get('view_count', 0),
                    'video_url': row.get('video_download_url') or row.get('video_url') or row.get('video_play_url'),
                    'cover_url': row.get('cover_url'),
                    'aweme_url': row.get('content_id'),  # 使用content_id作为URL标识
                    'platform': platform,
                    'task_id': task_id
                }
                videos.append(video_data)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'videos': videos,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"从数据库获取任务视频失败 {task_id}: {str(e)}")
            return {
                'videos': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }

    async def _get_platform_content_count(self, platform: str) -> int:
        """获取指定平台的内容数量"""
        try:
            db = await _get_db_connection()
            if not db:
                return 0
            
            # 使用统一内容表
            query = "SELECT COUNT(*) as count FROM unified_content WHERE platform = %s"
            result = await db.get_first(query, (platform,))
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"获取平台内容数量失败: {platform}, 错误: {e}")
            return 0

    async def _get_platform_comment_count(self, platform: str) -> int:
        """获取指定平台的评论数量"""
        try:
            db = await _get_db_connection()
            if not db:
                return 0
            
            # 使用统一评论表
            query = "SELECT COUNT(*) as count FROM unified_comment WHERE platform = %s"
            result = await db.get_first(query, (platform,))
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"获取平台评论数量失败: {platform}, 错误: {e}")
            return 0

    async def _get_platform_creator_count(self, platform: str) -> int:
        """获取指定平台的创作者数量"""
        try:
            db = await _get_db_connection()
            if not db:
                return 0
            
            # 使用统一创作者表
            query = "SELECT COUNT(*) as count FROM unified_creator WHERE platform = %s"
            result = await db.get_first(query, (platform,))
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"获取平台创作者数量失败: {platform}, 错误: {e}")
            return 0 