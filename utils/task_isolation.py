"""
任务隔离工具
确保多个爬虫任务互不影响，支持资源隔离和会话管理
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from tools import utils

class TaskIsolationManager:
    """任务隔离管理器"""
    
    def __init__(self):
        self.running_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_sessions: Dict[str, Dict[str, Any]] = {}
        self.resource_locks: Dict[str, asyncio.Lock] = {}
        self.max_concurrent_tasks = 10
        self.max_tasks_per_session = 50
        
    async def create_task_session(self, task_id: str, user_id: Optional[str] = None) -> str:
        """创建任务会话"""
        session_id = f"task_session_{task_id}_{int(time.time())}"
        
        self.task_sessions[session_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "resources": {},
            "status": "active"
        }
        
        utils.logger.info(f"创建任务会话: {session_id} (任务ID: {task_id})")
        return session_id
    
    async def register_task(self, task_id: str, platform: str, session_id: Optional[str] = None) -> bool:
        """注册任务"""
        try:
            # 检查并发任务数量限制
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                utils.logger.warning(f"达到最大并发任务数量限制: {self.max_concurrent_tasks}")
                return False
            
            # 检查任务是否已存在
            if task_id in self.running_tasks:
                utils.logger.warning(f"任务已存在: {task_id}")
                return False
            
            # 创建任务记录
            self.running_tasks[task_id] = {
                "task_id": task_id,
                "platform": platform,
                "session_id": session_id,
                "status": "running",
                "started_at": datetime.now(),
                "resources": {},
                "progress": 0.0
            }
            
            # 创建资源锁
            self.resource_locks[task_id] = asyncio.Lock()
            
            utils.logger.info(f"注册任务成功: {task_id} (平台: {platform})")
            return True
            
        except Exception as e:
            utils.logger.error(f"注册任务失败: {task_id}, 错误: {e}")
            return False
    
    async def unregister_task(self, task_id: str):
        """注销任务"""
        try:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                utils.logger.info(f"注销任务: {task_id}")
            
            if task_id in self.resource_locks:
                del self.resource_locks[task_id]
                
        except Exception as e:
            utils.logger.error(f"注销任务失败: {task_id}, 错误: {e}")
    
    async def update_task_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id]["progress"] = progress
            self.running_tasks[task_id]["updated_at"] = datetime.now()
    
    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.running_tasks.get(task_id)
    
    async def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有运行中的任务"""
        return self.running_tasks.copy()
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session in self.task_sessions.items():
                # 检查会话是否超过24小时
                if current_time - session["created_at"] > timedelta(hours=24):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.task_sessions[session_id]
                utils.logger.info(f"清理过期会话: {session_id}")
                
        except Exception as e:
            utils.logger.error(f"清理过期会话失败: {e}")
    
    async def get_task_resources(self, task_id: str) -> Dict[str, Any]:
        """获取任务资源"""
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].get("resources", {})
        return {}
    
    async def set_task_resource(self, task_id: str, resource_key: str, resource_value: Any):
        """设置任务资源"""
        if task_id in self.running_tasks:
            if "resources" not in self.running_tasks[task_id]:
                self.running_tasks[task_id]["resources"] = {}
            self.running_tasks[task_id]["resources"][resource_key] = resource_value
    
    async def acquire_resource_lock(self, task_id: str, resource_name: str) -> bool:
        """获取资源锁"""
        try:
            if task_id in self.resource_locks:
                await self.resource_locks[task_id].acquire()
                utils.logger.debug(f"获取资源锁: {task_id} - {resource_name}")
                return True
            return False
        except Exception as e:
            utils.logger.error(f"获取资源锁失败: {task_id} - {resource_name}, 错误: {e}")
            return False
    
    async def release_resource_lock(self, task_id: str, resource_name: str):
        """释放资源锁"""
        try:
            if task_id in self.resource_locks:
                self.resource_locks[task_id].release()
                utils.logger.debug(f"释放资源锁: {task_id} - {resource_name}")
        except Exception as e:
            utils.logger.error(f"释放资源锁失败: {task_id} - {resource_name}, 错误: {e}")
    
    async def check_task_isolation(self, task_id: str) -> bool:
        """检查任务隔离状态"""
        if task_id not in self.running_tasks:
            return False
        
        task = self.running_tasks[task_id]
        return task.get("status") == "running"
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        total_tasks = len(self.running_tasks)
        running_tasks = len([t for t in self.running_tasks.values() if t.get("status") == "running"])
        completed_tasks = len([t for t in self.running_tasks.values() if t.get("status") == "completed"])
        failed_tasks = len([t for t in self.running_tasks.values() if t.get("status") == "failed"])
        
        # 按平台统计
        platform_stats = {}
        for task in self.running_tasks.values():
            platform = task.get("platform", "unknown")
            if platform not in platform_stats:
                platform_stats[platform] = 0
            platform_stats[platform] += 1
        
        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "platform_stats": platform_stats,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "active_sessions": len(self.task_sessions)
        }

# 全局任务隔离管理器实例
task_isolation_manager = TaskIsolationManager()

# 定期清理任务
async def start_task_cleanup():
    """启动任务清理任务"""
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟清理一次
            await task_isolation_manager.cleanup_expired_sessions()
        except Exception as e:
            utils.logger.error(f"任务清理任务失败: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再重试

# 任务隔离装饰器
def task_isolation_required(func):
    """任务隔离装饰器"""
    async def wrapper(*args, **kwargs):
        task_id = kwargs.get('task_id') or (args[0] if args else None)
        
        if not task_id:
            raise ValueError("任务ID不能为空")
        
        # 检查任务隔离状态
        if not await task_isolation_manager.check_task_isolation(task_id):
            raise RuntimeError(f"任务隔离检查失败: {task_id}")
        
        return await func(*args, **kwargs)
    
    return wrapper
