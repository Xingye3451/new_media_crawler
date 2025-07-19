#!/usr/bin/env python3
"""
Redis数据管理器
管理爬取任务结果数据的存储和检索
"""
import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from tools import utils
from config.config_manager import config_manager


class TaskResultRedisManager:
    """任务结果Redis管理器"""
    
    def __init__(self, redis_host=None, redis_port=None, redis_db=None):
        """初始化Redis连接"""
        # 获取Redis配置
        self.redis_config = config_manager.get_redis_config()
        
        # 使用配置管理器的配置，或者传入的参数
        host = redis_host or self.redis_config.host
        port = redis_port or self.redis_config.port
        db = redis_db or self.redis_config.db
        
        # 创建连接池
        connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=self.redis_config.password if self.redis_config.password else None,
            decode_responses=True,
            socket_timeout=self.redis_config.socket_timeout,
            socket_connect_timeout=self.redis_config.socket_connect_timeout,
            socket_keepalive=self.redis_config.socket_keepalive,
            socket_keepalive_options=self.redis_config.socket_keepalive_options,
            health_check_interval=self.redis_config.health_check_interval,
            retry_on_timeout=self.redis_config.retry_on_timeout,
            max_connections=self.redis_config.max_connections,
        )
        
        self.redis_client = redis.Redis(connection_pool=connection_pool)
        
        # Redis key 前缀 - 使用配置的前缀
        self.TASK_RESULT_PREFIX = self.redis_config.task_result_key_prefix
        self.TASK_VIDEOS_PREFIX = "task:videos:"
        self.VIDEO_DETAIL_PREFIX = "video:"
        self.VIDEO_COMMENTS_PREFIX = "video:comments:"
        self.TASK_STATS_PREFIX = "task:stats:"
        
        # TTL配置
        self.task_result_ttl = self.redis_config.task_result_ttl
        
        utils.logger.info("✅ TaskResultRedisManager 初始化完成")
    
    def _get_task_result_key(self, task_id: str) -> str:
        """获取任务结果key"""
        return f"{self.TASK_RESULT_PREFIX}{task_id}"
    
    def _get_task_videos_key(self, task_id: str) -> str:
        """获取任务视频列表key"""
        return f"{self.TASK_VIDEOS_PREFIX}{task_id}"
    
    def _get_video_detail_key(self, platform: str, video_id: str) -> str:
        """获取视频详情key"""
        return f"{self.VIDEO_DETAIL_PREFIX}{platform}:{video_id}"
    
    def _get_video_comments_key(self, platform: str, video_id: str) -> str:
        """获取视频评论key"""
        return f"{self.VIDEO_COMMENTS_PREFIX}{platform}:{video_id}"
    
    def _get_task_stats_key(self, task_id: str) -> str:
        """获取任务统计key"""
        return f"{self.TASK_STATS_PREFIX}{task_id}"

    async def ping(self) -> bool:
        """测试Redis连接"""
        try:
            result = self.redis_client.ping()
            utils.logger.info("✅ Redis连接测试成功")
            return True
        except Exception as e:
            utils.logger.error(f"❌ Redis连接测试失败: {e}")
            return False

    async def close(self) -> None:
        """关闭Redis连接"""
        try:
            self.redis_client.close()
            utils.logger.info("✅ Redis连接已关闭")
        except Exception as e:
            utils.logger.error(f"❌ 关闭Redis连接失败: {e}")

    async def store_task_result(self, task_id: str, task_info: Dict[str, Any]) -> bool:
        """
        存储任务基本信息
        
        Args:
            task_id: 任务ID
            task_info: 任务信息，包含：
                - account_id: 执行账号ID
                - platform: 平台
                - keywords: 搜索关键词
                - total_videos: 总视频数
                - total_comments: 总评论数
                - start_time: 开始时间
                - end_time: 结束时间
                - status: 任务状态
        """
        try:
            task_key = self._get_task_result_key(task_id)
            
            # 准备存储数据
            task_data = {
                "task_id": task_id,
                "account_id": task_info.get("account_id"),
                "platform": task_info.get("platform"),
                "keywords": task_info.get("keywords", ""),
                "total_videos": task_info.get("total_videos", 0),
                "total_comments": task_info.get("total_comments", 0),
                "start_time": task_info.get("start_time"),
                "end_time": task_info.get("end_time"),
                "status": task_info.get("status", "completed"),
                "created_at": datetime.now().isoformat()
            }
            
            # 存储到Redis，使用配置的TTL
            self.redis_client.hset(task_key, mapping=task_data)
            self.redis_client.expire(task_key, self.task_result_ttl)
            
            utils.logger.info(f"✅ 任务结果已存储到Redis: {task_id}")
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ 存储任务结果失败: {task_id}, 错误: {e}")
            return False

    async def store_video_data(self, task_id: str, platform: str, video_data: Dict[str, Any]) -> bool:
        """
        存储视频数据（标准化字段，全部转为字符串）
        Args:
            task_id: 任务ID
            platform: 平台名称
            video_data: 标准化视频数据
        """
        try:
            video_id = video_data.get("aweme_id") or video_data.get("video_id")
            if not video_id:
                utils.logger.error("❌ 视频ID不能为空")
                return False

            # 1. 将视频ID添加到任务视频列表
            task_videos_key = self._get_task_videos_key(task_id)
            self.redis_client.sadd(task_videos_key, video_id)
            self.redis_client.expire(task_videos_key, self.task_result_ttl)

            # 2. 存储视频详细信息
            video_key = self._get_video_detail_key(platform, video_id)

            # 标准化字段，全部转为字符串
            video_detail = {
                "video_id": str(video_id),
                "aweme_url": str(video_data.get("aweme_url", "")),
                "download_url": str(video_data.get("download_url", "")),
                "cover_url": str(video_data.get("cover_url", "")),
                "title": str(video_data.get("title", "")),
                "author_id": str(video_data.get("author_id", "")),
                "author_name": str(video_data.get("author_name", "")),
                "avatar": str(video_data.get("avatar", "")),
                "create_time": str(video_data.get("create_time", "")),
                "liked_count": str(video_data.get("liked_count", "")),
                "comment_count": str(video_data.get("comment_count", "")),
                "collected_count": str(video_data.get("collected_count", "")),
                "share_count": str(video_data.get("share_count", "")),
                "play_count": str(video_data.get("play_count", "")),
                "video_size": str(video_data.get("video_size", "")),
                "duration": str(video_data.get("duration", "")),
                "platform": str(platform),
                "source_keyword": str(video_data.get("source_keyword", "")),
                "task_id": str(task_id),
                "stored_at": str(video_data.get("stored_at", datetime.now().isoformat())),
            }

            self.redis_client.hset(video_key, mapping=video_detail)
            self.redis_client.expire(video_key, self.task_result_ttl)

            utils.logger.info(f"✅ 视频数据已存储: {platform}:{video_id}")
            return True

        except Exception as e:
            utils.logger.error(f"❌ 存储视频数据失败: {platform}:{video_id}, 错误: {e}")
            return False

    async def store_hot_comments(self, platform: str, video_id: str, comments: List[Dict[str, Any]]) -> bool:
        """
        存储热门评论
        Args:
            platform: 平台名称
            video_id: 视频ID
            comments: 评论列表
        """
        try:
            comments_key = self._get_video_comments_key(platform, video_id)
            
            # 存储评论数据
            for i, comment in enumerate(comments):
                field_name = f"comment_{i}"
                self.redis_client.hset(comments_key, field_name, json.dumps(comment, ensure_ascii=False))
            
            # 设置过期时间
            self.redis_client.expire(comments_key, self.task_result_ttl)
            
            utils.logger.info(f"✅ 热门评论已存储: {platform}:{video_id} ({len(comments)} 条)")
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ 存储热门评论失败: {platform}:{video_id}, 错误: {e}")
            return False

    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务基本信息"""
        try:
            task_key = self._get_task_result_key(task_id)
            task_data = self.redis_client.hgetall(task_key)
            
            if not task_data:
                return None
                
            return task_data
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务信息失败: {task_id}, 错误: {e}")
            return None

    async def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            stats_key = self._get_task_stats_key(task_id)
            stats_data = self.redis_client.hgetall(stats_key)
            
            if not stats_data:
                return {
                    "total_videos": 0,
                    "total_comments": 0,
                    "platforms": "",
                    "completed_at": ""
                }
                
            return stats_data
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务统计失败: {task_id}, 错误: {e}")
            return {
                "total_videos": 0,
                "total_comments": 0,
                "platforms": "",
                "completed_at": ""
            }

    async def get_task_videos(self, task_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取任务的视频列表（带分页）"""
        try:
            # 获取任务关联的视频ID列表
            task_videos_key = self._get_task_videos_key(task_id)
            video_ids = list(self.redis_client.smembers(task_videos_key))
            
            if not video_ids:
                return {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            # 分页处理
            total = len(video_ids)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_video_ids = video_ids[start_idx:end_idx]
            
            videos = []
            for video_id in page_video_ids:
                # 尝试从不同平台获取视频详情
                for platform in ['dy', 'xhs', 'ks', 'bili', 'wb', 'zhihu']:
                    video_key = self._get_video_detail_key(platform, video_id)
                    video_data = self.redis_client.hgetall(video_key)
                    
                    if video_data:
                        # 获取热门评论
                        comments_key = self._get_video_comments_key(platform, video_id)
                        comments_data = self.redis_client.hgetall(comments_key)
                        
                        # 解析评论数据
                        comments = []
                        for field, comment_json in comments_data.items():
                            if field.startswith('comment_'):
                                try:
                                    comment = json.loads(comment_json)
                                    comments.append(comment)
                                except:
                                    pass
                        
                        # 按rank排序
                        comments.sort(key=lambda x: x.get('rank', 0))
                        
                        # 组装视频信息
                        video_info = {
                            **video_data,
                            'hot_comments': comments
                        }
                        videos.append(video_info)
                        break  # 找到后跳出平台循环
            
            # 按存储时间排序
            videos.sort(key=lambda x: x.get('stored_at', ''), reverse=True)
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'videos': videos,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务视频失败: {task_id}, 错误: {e}")
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
            video_key = self._get_video_detail_key(platform, video_id)
            video_data = self.redis_client.hgetall(video_key)
            
            if not video_data:
                return None
            
            # 获取热门评论
            comments_key = self._get_video_comments_key(platform, video_id)
            comments_data = self.redis_client.hgetall(comments_key)
            
            # 解析评论数据
            comments = []
            for field, comment_json in comments_data.items():
                if field.startswith('comment_'):
                    try:
                        comment = json.loads(comment_json)
                        comments.append(comment)
                    except:
                        pass
            
            # 按rank排序
            comments.sort(key=lambda x: x.get('rank', 0))
            
            # 组装视频信息
            video_info = {
                **video_data,
                'hot_comments': comments
            }
            
            return video_info
            
        except Exception as e:
            utils.logger.error(f"❌ 获取视频详情失败: {platform}:{video_id}, 错误: {e}")
            return None

    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 获取任务统计
            task_pattern = f"{self.TASK_RESULT_PREFIX}*"
            task_keys = self.redis_client.keys(task_pattern)
            
            # 获取视频统计
            video_pattern = f"{self.VIDEO_DETAIL_PREFIX}*"
            video_keys = self.redis_client.keys(video_pattern)
            
            # 获取评论统计
            comment_pattern = f"{self.VIDEO_COMMENTS_PREFIX}*"
            comment_keys = self.redis_client.keys(comment_pattern)
            
            # 按平台统计
            platform_stats = {}
            for video_key in video_keys:
                video_data = self.redis_client.hgetall(video_key)
                if video_data and 'platform' in video_data:
                    platform = video_data['platform']
                    platform_stats[platform] = platform_stats.get(platform, 0) + 1
            
            return {
                'total_tasks': len(task_keys),
                'total_videos': len(video_keys),
                'total_comments': len(comment_keys),
                'platform_stats': platform_stats,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            utils.logger.error(f"❌ 获取系统统计失败: {e}")
            return {
                'total_tasks': 0,
                'total_videos': 0,
                'total_comments': 0,
                'platform_stats': {},
                'last_updated': datetime.now().isoformat()
            }

    async def delete_task_result(self, task_id: str) -> bool:
        """删除任务结果"""
        try:
            # 获取任务关联的视频ID列表
            task_videos_key = self._get_task_videos_key(task_id)
            video_ids = self.redis_client.smembers(task_videos_key)
            
            # 删除视频详情
            for video_id in video_ids:
                for platform in ['dy', 'xhs', 'ks', 'bili', 'wb', 'zhihu']:
                    video_key = self._get_video_detail_key(platform, video_id)
                    comments_key = self._get_video_comments_key(platform, video_id)
                    
                    self.redis_client.delete(video_key)
                    self.redis_client.delete(comments_key)
            
            # 删除任务相关数据
            task_key = self._get_task_result_key(task_id)
            stats_key = self._get_task_stats_key(task_id)
            
            self.redis_client.delete(task_key)
            self.redis_client.delete(stats_key)
            self.redis_client.delete(task_videos_key)
            
            utils.logger.info(f"✅ 任务结果已删除: {task_id}")
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ 删除任务结果失败: {task_id}, 错误: {e}")
            return False

    async def cleanup_expired_tasks(self, days: int = 7) -> int:
        """清理过期任务"""
        try:
            # 获取所有任务key
            pattern = f"{self.TASK_RESULT_PREFIX}*"
            keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            cutoff_time = datetime.now() - timedelta(days=days)
            
            for key in keys:
                task_data = self.redis_client.hgetall(key)
                if task_data and 'created_at' in task_data:
                    try:
                        created_at = datetime.fromisoformat(task_data['created_at'])
                        if created_at < cutoff_time:
                            task_id = task_data.get('task_id', key.split(':')[-1])
                            if await self.delete_task_result(task_id):
                                cleaned_count += 1
                    except:
                        pass
            
            utils.logger.info(f"✅ 清理过期任务完成，共清理 {cleaned_count} 个任务")
            return cleaned_count
            
        except Exception as e:
            utils.logger.error(f"❌ 清理过期任务失败: {e}")
            return 0

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        try:
            task_key = self._get_task_result_key(task_id)
            task_data = self.redis_client.hgetall(task_key)
            
            if not task_data:
                return None
                
            return task_data
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务结果失败: {task_id}, 错误: {e}")
            return None

    async def get_task_videos_by_platform(self, task_id: str, platform: str) -> List[Dict[str, Any]]:
        """获取任务的视频列表（按平台）"""
        try:
            # 获取任务关联的视频ID列表
            task_videos_key = self._get_task_videos_key(task_id)
            video_ids = self.redis_client.smembers(task_videos_key)
            
            if not video_ids:
                return []
            
            videos = []
            for video_id in video_ids:
                # 获取视频详情
                video_key = self._get_video_detail_key(platform, video_id)
                video_data = self.redis_client.hgetall(video_key)
                
                if video_data:
                    # 获取热门评论
                    comments_key = self._get_video_comments_key(platform, video_id)
                    comments_data = self.redis_client.hgetall(comments_key)
                    
                    # 解析评论数据
                    comments = []
                    for field, comment_json in comments_data.items():
                        if field.startswith('comment_'):
                            try:
                                comment = json.loads(comment_json)
                                comments.append(comment)
                            except:
                                pass
                    
                    # 按rank排序
                    comments.sort(key=lambda x: x.get('rank', 0))
                    
                    # 组装视频信息
                    video_info = {
                        **video_data,
                        'hot_comments': comments
                    }
                    videos.append(video_info)
            
            # 按存储时间排序
            videos.sort(key=lambda x: x.get('stored_at', ''), reverse=True)
            
            return videos
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务视频失败: {task_id}, 错误: {e}")
            return []

    async def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的任务列表"""
        try:
            pattern = f"{self.TASK_RESULT_PREFIX}*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return []
            
            tasks = []
            for key in keys:
                task_data = self.redis_client.hgetall(key)
                if task_data:
                    tasks.append(task_data)
            
            # 按创建时间排序
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return tasks[:limit]
            
        except Exception as e:
            utils.logger.error(f"❌ 获取最近任务失败: {e}")
            return []

    async def update_task_stats(self, task_id: str, stats: Dict[str, Any]) -> bool:
        """更新任务统计信息"""
        try:
            stats_key = self._get_task_stats_key(task_id)
            
            # 存储统计数据
            stats_data = {
                "task_id": task_id,
                "updated_at": datetime.now().isoformat(),
                **stats
            }
            
            self.redis_client.hset(stats_key, mapping=stats_data)
            self.redis_client.expire(stats_key, self.task_result_ttl)
            
            utils.logger.info(f"✅ 任务统计已更新: {task_id}")
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ 更新任务统计失败: {task_id}, 错误: {e}")
            return False

    async def cleanup_expired_data(self) -> int:
        """清理过期数据"""
        try:
            # 获取所有相关的key
            patterns = [
                f"{self.TASK_RESULT_PREFIX}*",
                f"{self.TASK_VIDEOS_PREFIX}*",
                f"{self.VIDEO_DETAIL_PREFIX}*",
                f"{self.VIDEO_COMMENTS_PREFIX}*",
                f"{self.TASK_STATS_PREFIX}*"
            ]
            
            total_cleaned = 0
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                expired_keys = []
                
                for key in keys:
                    ttl = self.redis_client.ttl(key)
                    if ttl == -1:  # 没有设置过期时间
                        # 重新设置过期时间
                        self.redis_client.expire(key, self.task_result_ttl)
                    elif ttl == -2:  # 已经过期
                        expired_keys.append(key)
                
                if expired_keys:
                    self.redis_client.delete(*expired_keys)
                    total_cleaned += len(expired_keys)
            
            utils.logger.info(f"✅ 清理过期数据完成，共清理 {total_cleaned} 条记录")
            return total_cleaned
            
        except Exception as e:
            utils.logger.error(f"❌ 清理过期数据失败: {e}")
            return 0

    async def get_task_results(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """获取任务结果列表（带分页）"""
        try:
            # 获取所有任务key
            pattern = f"{self.TASK_RESULT_PREFIX}*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return {
                    'results': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            
            # 获取所有任务数据
            all_tasks = []
            for key in keys:
                task_data = self.redis_client.hgetall(key)
                if task_data:
                    all_tasks.append(task_data)
            
            # 按创建时间排序
            all_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 分页处理
            total = len(all_tasks)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_tasks = all_tasks[start_idx:end_idx]
            
            # 为每个任务补充统计信息
            for task in page_tasks:
                task_id = task.get('task_id')
                if task_id:
                    stats = await self.get_task_statistics(task_id)
                    task['statistics'] = stats
            
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'results': page_tasks,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            utils.logger.error(f"❌ 获取任务结果列表失败: {e}")
            return {
                'results': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }


# 全局Redis管理器实例
redis_manager = TaskResultRedisManager()


# 便捷函数
async def store_crawler_result(task_id: str, platform: str, account_id: str, 
                             videos_data: List[Dict], comments_data: Dict = None):
    """
    存储爬虫结果到Redis
    
    Args:
        task_id: 任务ID
        platform: 平台名称
        account_id: 账号ID
        videos_data: 视频数据列表
        comments_data: 评论数据（可选）
    """
    try:
        redis_manager = TaskResultRedisManager()
        
        # 1. 存储任务基本信息
        task_info = {
            "account_id": account_id,
            "platform": platform,
            "keywords": "",  # 从视频数据中提取
            "total_videos": len(videos_data),
            "total_comments": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "status": "completed"
        }
        
        await redis_manager.store_task_result(task_id, task_info)
        
        # 2. 存储视频数据
        for video_data in videos_data:
            await redis_manager.store_video_data(task_id, platform, video_data)
            
            # 存储热门评论
            video_id = video_data.get("video_id")
            if video_id and comments_data and video_id in comments_data:
                video_comments = comments_data[video_id]
                await redis_manager.store_hot_comments(platform, video_id, video_comments)
        
        # 3. 更新任务统计
        stats = {
            "total_videos": len(videos_data),
            "total_comments": sum(len(comments_data.get(v.get("video_id"), [])) for v in videos_data) if comments_data else 0,
            "platforms": platform,  # 改为字符串，避免列表类型错误
            "completed_at": datetime.now().isoformat()
        }
        
        await redis_manager.update_task_stats(task_id, stats)
        
        utils.logger.info(f"✅ 爬虫结果已存储到Redis: {task_id} ({len(videos_data)} 个视频)")
        
    except Exception as e:
        utils.logger.error(f"❌ 存储爬虫结果失败: {task_id}, 错误: {e}")
        raise 