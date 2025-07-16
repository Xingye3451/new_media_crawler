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
            # 获取任务基本信息
            task_info = await self.redis_manager.get_task_info(task_id)
            if not task_info:
                return None
            
            # 获取统计信息
            stats = await self.redis_manager.get_task_statistics(task_id)
            
            # 获取视频列表（前10个）
            videos = await self.redis_manager.get_task_videos(task_id, page=1, page_size=10)
            
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
            return await self.redis_manager.get_task_videos(task_id, page=page, page_size=page_size)
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
            # 平台表映射
            table_mapping = {
                'dy': 'douyin_aweme',
                'xhs': 'xhs_note', 
                'ks': 'kuaishou_video',
                'bili': 'bilibili_video',
                'wb': 'weibo_note',
                'zhihu': 'zhihu_video'
            }
            
            table_name = table_mapping.get(platform)
            if not table_name:
                return None
            
            db = await _get_db_connection()
            
            # 查询视频信息
            query = f"""
                SELECT * FROM {table_name} 
                WHERE aweme_id = %s OR note_id = %s OR video_id = %s
                ORDER BY create_time DESC LIMIT 1
            """
            result = await db.get_first(query, video_id, video_id, video_id)
            
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
            # 评论表映射
            comment_table_mapping = {
                'dy': 'douyin_aweme_comment',
                'xhs': 'xhs_note_comment',
                'ks': 'kuaishou_video_comment', 
                'bili': 'bilibili_video_comment',
                'wb': 'weibo_note_comment',
                'zhihu': 'zhihu_video_comment'
            }
            
            table_name = comment_table_mapping.get(platform)
            if not table_name:
                return []
            
            db = await _get_db_connection()
            
            # 查询热门评论（按点赞数排序）
            query = f"""
                SELECT * FROM {table_name} 
                WHERE aweme_id = %s OR note_id = %s OR video_id = %s
                ORDER BY digg_count DESC, create_time DESC 
                LIMIT %s
            """
            results = await db.query(query, video_id, video_id, video_id, limit)
            
            return results
                
        except Exception as e:
            logger.error(f"获取热门评论失败 {platform}/{video_id}: {str(e)}")
            return []
    
    async def get_platform_videos(self, platform: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取平台视频列表"""
        try:
            # 平台表映射
            table_mapping = {
                'dy': 'douyin_aweme',
                'xhs': 'xhs_note',
                'ks': 'kuaishou_video',
                'bili': 'bilibili_video', 
                'wb': 'weibo_note',
                'zhihu': 'zhihu_video'
            }
            
            table_name = table_mapping.get(platform)
            if not table_name:
                return {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            db = await _get_db_connection()
            
            # 查询总数
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count_result = await db.get_first(count_query)
            total = count_result[0] if count_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT * FROM {table_name} 
                ORDER BY create_time DESC 
                LIMIT %s OFFSET %s
            """
            results = await db.query(query, page_size, offset)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'videos': results,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
                
        except Exception as e:
            logger.error(f"获取平台视频列表失败 {platform}: {str(e)}")
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
            
            # 各平台视频数量统计
            platform_tables = {
                'douyin': 'douyin_aweme',
                'xhs': 'xhs_note',
                'kuaishou': 'kuaishou_video',
                'bilibili': 'bilibili_video',
                'weibo': 'weibo_note',
                'zhihu': 'zhihu_video'
            }
            
            db = await _get_db_connection()
            
            for platform, table_name in platform_tables.items():
                try:
                    # 检查表是否存在
                    check_query = f"SHOW TABLES LIKE '{table_name}'"
                    table_exists = await db.get_first(check_query)
                    
                    if table_exists:
                        # 获取视频数量
                        count_query = f"SELECT COUNT(*) FROM {table_name}"
                        count_result = await db.get_first(count_query)
                        stats[f'{platform}_videos'] = count_result[0] if count_result else 0
                        
                        # 获取今日新增
                        today_query = f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE DATE(create_time) = CURDATE()
                        """
                        today_result = await db.get_first(today_query)
                        stats[f'{platform}_today'] = today_result[0] if today_result else 0
                    else:
                        stats[f'{platform}_videos'] = 0
                        stats[f'{platform}_today'] = 0
                except Exception as e:
                    logger.warning(f"统计表 {table_name} 失败: {str(e)}")
                    stats[f'{platform}_videos'] = 0
                    stats[f'{platform}_today'] = 0
            
            # 总计
            stats['total_videos'] = sum(v for k, v in stats.items() if k.endswith('_videos'))
            stats['total_today'] = sum(v for k, v in stats.items() if k.endswith('_today'))
            
            return stats
                
        except Exception as e:
            logger.error(f"获取数据库统计失败: {str(e)}")
            return {}
    
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