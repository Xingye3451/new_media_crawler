#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务管理服务
提供任务CRUD、视频管理、日志记录等功能
"""

import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from models.task_models import (
    TaskStatus, TaskType, ActionType
)
from var import media_crawler_db_var

logger = logging.getLogger(__name__)

async def _get_db_connection():
    """获取数据库连接"""
    try:
        # 直接创建数据库连接，不依赖ContextVar
        from config.env_config_loader import config_loader
        from async_db import AsyncMysqlDB
        import aiomysql
        
        db_config = config_loader.get_database_config()
        
        pool = await aiomysql.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            db=db_config['database'],
            autocommit=True,
        )
        
        async_db_obj = AsyncMysqlDB(pool)
        return async_db_obj
        
    except Exception as e:
        logger.error(f"获取数据库连接失败: {e}")
        raise


class TaskManagementService:
    """任务管理服务"""
    
    def __init__(self):
        self.db = None
    
    async def _get_db(self):
        """获取数据库连接"""
        if not self.db:
            self.db = await _get_db_connection()
        return self.db
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """创建任务"""
        db = await self._get_db()
        try:
            task_id = str(uuid.uuid4())
            
            # 构建插入SQL
            insert_sql = """
            INSERT INTO crawler_tasks (
                id, platform, task_type, keywords, user_id, params, priority,
                ip_address, user_security_id, user_signature, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            import json
            params_json = json.dumps(task_data.get('params', {})) if task_data.get('params') else None
            
            await db.execute(insert_sql, 
                task_id,
                task_data['platform'],
                task_data['task_type'],
                task_data['keywords'],
                task_data.get('user_id'),
                params_json,
                task_data.get('priority', 0),
                task_data.get('ip_address'),
                task_data.get('user_security_id'),
                task_data.get('user_signature'),
                datetime.now(),
                datetime.now()
            )
            
            # 记录日志
            await self._add_task_log(
                task_id=task_id,
                action_type=ActionType.CREATE,
                content=f"创建任务: {task_data['platform']} - {task_data['keywords']}",
                operator=task_data.get('user_id', 'system')
            )
            
            logger.info(f"任务创建成功: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        db = await self._get_db()
        try:
            query = """
            SELECT * FROM crawler_tasks 
            WHERE id = %s AND deleted = 0
            """
            
            result = await db.get_first(query, task_id)
            return result
            
        except Exception as e:
            logger.error(f"获取任务详情失败 {task_id}: {str(e)}")
            raise
    
    async def update_task(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """更新任务"""
        db = await self._get_db()
        try:
            # 构建更新SQL
            set_clauses = []
            params = []
            
            for key, value in update_data.items():
                if key in ['status', 'progress', 'result_count', 'error_message', 
                          'is_favorite', 'is_pinned', 'updated_at']:
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = %s")
            params.append(datetime.now())
            params.append(task_id)
            
            update_sql = f"""
            UPDATE crawler_tasks 
            SET {', '.join(set_clauses)}
            WHERE id = %s AND deleted = 0
            """
            
            result = await db.execute(update_sql, *params)
            
            if result:
                # 记录日志
                await self._add_task_log(
                    task_id=task_id,
                    action_type=ActionType.UPDATE,
                    content=f"更新任务: {update_data}",
                    operator=update_data.get('operator', 'system')
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"更新任务失败 {task_id}: {str(e)}")
            raise
    
    async def delete_task(self, task_id: str, operator: str = 'system') -> bool:
        """删除任务（软删除）"""
        db = await self._get_db()
        try:
            update_sql = """
            UPDATE crawler_tasks 
            SET deleted = 1, updated_at = %s
            WHERE id = %s AND deleted = 0
            """
            
            result = await db.execute(update_sql, datetime.now(), task_id)
            
            if result:
                # 记录日志
                await self._add_task_log(
                    task_id=task_id,
                    action_type=ActionType.DELETE,
                    content="删除任务",
                    operator=operator
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"删除任务失败 {task_id}: {str(e)}")
            raise
    
    async def list_tasks(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取任务列表"""
        db = await self._get_db()
        try:
            # 构建查询条件
            where_clauses = ["deleted = 0"]
            params = []
            
            if filters.get('platform'):
                where_clauses.append("platform = %s")
                params.append(filters['platform'])
            
            if filters.get('status'):
                where_clauses.append("status = %s")
                params.append(filters['status'])
            
            if filters.get('task_type'):
                where_clauses.append("task_type = %s")
                params.append(filters['task_type'])
            
            if filters.get('keyword'):
                where_clauses.append("keywords LIKE %s")
                params.append(f"%{filters['keyword']}%")
            
            if filters.get('is_favorite') is not None:
                where_clauses.append("is_favorite = %s")
                params.append(filters['is_favorite'])
            
            if filters.get('is_pinned') is not None:
                where_clauses.append("is_pinned = %s")
                params.append(filters['is_pinned'])
            
            if filters.get('user_id'):
                where_clauses.append("user_id = %s")
                params.append(filters['user_id'])
            
            where_sql = " AND ".join(where_clauses)
            
            # 构建排序
            sort_field = filters.get('sort_by', 'created_at')
            sort_order = filters.get('sort_order', 'desc')
            
            # 验证排序字段
            valid_sort_fields = ['created_at', 'updated_at', 'priority', 'status', 'result_count']
            if sort_field not in valid_sort_fields:
                sort_field = 'created_at'
            
            order_sql = f"{sort_field} {sort_order.upper()}"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM crawler_tasks WHERE {where_sql}"
            count_result = await db.get_first(count_sql, *params)
            total = count_result['total'] if count_result else 0
            
            # 查询数据
            offset = (page - 1) * page_size
            query_sql = f"""
            SELECT * FROM crawler_tasks 
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """
            
            query_params = params + [page_size, offset]
            results = await db.query(query_sql, *query_params)
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'items': results
            }
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            raise
    
    async def get_task_videos(self, task_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取任务的视频列表"""
        db = await self._get_db()
        try:
            # 查询总数
            count_sql = "SELECT COUNT(*) as total FROM douyin_aweme WHERE task_id = %s"
            count_result = await db.get_first(count_sql, task_id)
            total = count_result['total'] if count_result else 0
            
            # 查询数据
            offset = (page - 1) * page_size
            query_sql = """
            SELECT * FROM douyin_aweme 
            WHERE task_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            
            results = await db.query(query_sql, task_id, page_size, offset)
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'items': results
            }
            
        except Exception as e:
            logger.error(f"获取任务视频列表失败 {task_id}: {str(e)}")
            raise
    
    async def get_video_detail(self, video_id: int) -> Optional[Dict]:
        """获取视频详情"""
        db = await self._get_db()
        try:
            query_sql = "SELECT * FROM douyin_aweme WHERE id = %s"
            result = await db.get_first(query_sql, video_id)
            return result
            
        except Exception as e:
            logger.error(f"获取视频详情失败 {video_id}: {str(e)}")
            raise
    
    async def update_video_collection(self, video_id: int, is_collected: bool, minio_url: str = None) -> bool:
        """更新视频收藏状态"""
        db = await self._get_db()
        try:
            # 暂时注释掉is_collected字段更新，因为该字段可能不存在
            # update_sql = "UPDATE douyin_aweme SET is_collected = %s"
            # params = [is_collected]
            
            # 只更新minio_url字段
            if minio_url:
                update_sql = "UPDATE douyin_aweme SET minio_url = %s WHERE id = %s"
                params = [minio_url, video_id]
            else:
                # 如果没有minio_url，暂时返回成功
                return True
            
            result = await db.execute(update_sql, *params)
            return bool(result)
            
        except Exception as e:
            logger.error(f"更新视频收藏状态失败 {video_id}: {str(e)}")
            raise
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        db = await self._get_db()
        try:
            # 任务统计
            task_stats_sql = """
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_tasks,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
            FROM crawler_tasks 
            WHERE deleted = 0
            """
            
            task_stats = await db.get_first(task_stats_sql)
            
            # 视频统计 - 移除is_collected字段查询
            video_stats_sql = """
            SELECT 
                COUNT(*) as total_videos
            FROM douyin_aweme
            """
            
            video_stats = await db.get_first(video_stats_sql)
            
            # 平台统计
            platform_stats_sql = """
            SELECT platform, COUNT(*) as count
            FROM crawler_tasks 
            WHERE deleted = 0
            GROUP BY platform
            """
            
            platform_results = await db.query(platform_stats_sql)
            platform_stats = {row['platform']: row['count'] for row in platform_results}
            
            # 最近任务
            recent_tasks_sql = """
            SELECT * FROM crawler_tasks 
            WHERE deleted = 0 AND created_at >= %s
            ORDER BY created_at DESC 
            LIMIT 10
            """
            
            week_ago = datetime.now() - timedelta(days=7)
            recent_tasks = await db.query(recent_tasks_sql, week_ago)
            
            return {
                'total_tasks': task_stats['total_tasks'] or 0,
                'completed_tasks': task_stats['completed_tasks'] or 0,
                'running_tasks': task_stats['running_tasks'] or 0,
                'failed_tasks': task_stats['failed_tasks'] or 0,
                'total_videos': video_stats['total_videos'] or 0,
                'collected_videos': 0,  # 暂时设为0，因为is_collected字段不存在
                'platform_stats': platform_stats,
                'recent_tasks': recent_tasks
            }
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {str(e)}")
            raise
    
    async def get_task_logs(self, task_id: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """获取任务日志"""
        db = await self._get_db()
        try:
            # 查询总数
            count_sql = "SELECT COUNT(*) as total FROM crawler_task_logs WHERE task_id = %s"
            count_result = await db.get_first(count_sql, task_id)
            total = count_result['total'] if count_result else 0
            
            # 查询数据
            offset = (page - 1) * page_size
            query_sql = """
            SELECT * FROM crawler_task_logs 
            WHERE task_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            
            results = await db.query(query_sql, task_id, page_size, offset)
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'items': results
            }
            
        except Exception as e:
            logger.error(f"获取任务日志失败 {task_id}: {str(e)}")
            raise
    
    async def _add_task_log(self, task_id: str, action_type: str, content: str, operator: str = 'system'):
        """添加任务日志"""
        db = await self._get_db()
        try:
            insert_sql = """
            INSERT INTO crawler_task_logs (task_id, action_type, content, operator, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            await db.execute(insert_sql, task_id, action_type, content, operator, datetime.now())
            
        except Exception as e:
            logger.error(f"添加任务日志失败: {str(e)}")
    
    async def close(self):
        """关闭数据库连接"""
        self.db = None 