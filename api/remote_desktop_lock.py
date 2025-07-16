#!/usr/bin/env python3
"""
远程桌面并发控制模块
实现远程桌面登录的互斥访问
"""

import asyncio
import time
from typing import Optional, Dict, Any
from tools import utils
from datetime import datetime, timedelta

class RemoteDesktopLock:
    """远程桌面互斥锁"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._current_session: Optional[str] = None
        self._session_start_time: Optional[datetime] = None
        self._session_info: Dict[str, Any] = {}
        self._max_session_time = 1800  # 30分钟最大会话时间
        self._waiting_queue = []  # 等待队列
    
    async def try_acquire(self, session_id: str, user_info: Dict[str, Any]) -> bool:
        """
        尝试获取远程桌面访问权限
        
        Args:
            session_id: 会话ID
            user_info: 用户信息（包含账号ID、平台等）
            
        Returns:
            bool: 是否成功获取权限
        """
        async with self._lock:
            # 检查当前会话是否已过期
            if self._current_session and self._session_start_time:
                if datetime.now() - self._session_start_time > timedelta(seconds=self._max_session_time):
                    utils.logger.info(f"当前远程桌面会话已过期: {self._current_session}")
                    await self._force_release()
            
            # 如果没有活动会话，直接获取
            if not self._current_session:
                self._current_session = session_id
                self._session_start_time = datetime.now()
                self._session_info = user_info.copy()
                
                utils.logger.info(f"🔒 远程桌面访问权限已授予: {session_id}")
                utils.logger.info(f"   用户信息: {user_info}")
                
                # 从等待队列中移除（如果存在）
                self._remove_from_queue(session_id)
                
                return True
            
            # 如果是当前会话的重复请求，直接允许
            if self._current_session == session_id:
                utils.logger.info(f"🔄 远程桌面会话续期: {session_id}")
                self._session_start_time = datetime.now()  # 更新时间
                return True
            
            # 否则加入等待队列
            if session_id not in [item['session_id'] for item in self._waiting_queue]:
                queue_info = {
                    'session_id': session_id,
                    'user_info': user_info,
                    'request_time': datetime.now()
                }
                self._waiting_queue.append(queue_info)
                
                utils.logger.info(f"⏳ 远程桌面忙碌，已加入等待队列: {session_id}")
                utils.logger.info(f"   当前队列位置: {len(self._waiting_queue)}")
                utils.logger.info(f"   当前使用者: {self._current_session}")
            
            return False
    
    async def release(self, session_id: str) -> bool:
        """
        释放远程桌面访问权限
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功释放
        """
        async with self._lock:
            if self._current_session == session_id:
                utils.logger.info(f"🔓 远程桌面访问权限已释放: {session_id}")
                
                # 记录使用时长
                if self._session_start_time:
                    duration = datetime.now() - self._session_start_time
                    utils.logger.info(f"   会话持续时间: {duration.total_seconds():.1f}秒")
                
                self._current_session = None
                self._session_start_time = None
                self._session_info.clear()
                
                # 从等待队列中移除（如果存在）
                self._remove_from_queue(session_id)
                
                # 通知等待队列中的下一个用户
                await self._notify_next_in_queue()
                
                return True
            else:
                # 如果不是当前会话，只从等待队列中移除
                removed = self._remove_from_queue(session_id)
                if removed:
                    utils.logger.info(f"📤 已从等待队列中移除: {session_id}")
                return removed
    
    async def _force_release(self):
        """强制释放当前会话（超时等情况）"""
        if self._current_session:
            utils.logger.warning(f"⚠️ 强制释放远程桌面会话: {self._current_session}")
            self._current_session = None
            self._session_start_time = None
            self._session_info.clear()
            
            # 通知等待队列
            await self._notify_next_in_queue()
    
    def _remove_from_queue(self, session_id: str) -> bool:
        """从等待队列中移除指定会话"""
        original_length = len(self._waiting_queue)
        self._waiting_queue = [item for item in self._waiting_queue if item['session_id'] != session_id]
        return len(self._waiting_queue) < original_length
    
    async def _notify_next_in_queue(self):
        """通知等待队列中的下一个用户"""
        if self._waiting_queue:
            next_item = self._waiting_queue[0]
            utils.logger.info(f"📢 通知等待队列中的下一个用户: {next_item['session_id']}")
            # 这里可以发送通知给前端，但现在先只记录日志
    
    def get_status(self) -> Dict[str, Any]:
        """获取远程桌面锁状态"""
        return {
            "is_locked": self._current_session is not None,
            "current_session": self._current_session,
            "session_start_time": self._session_start_time.isoformat() if self._session_start_time else None,
            "session_info": self._session_info.copy(),
            "queue_length": len(self._waiting_queue),
            "waiting_sessions": [
                {
                    "session_id": item['session_id'],
                    "user_info": item['user_info'],
                    "wait_time_seconds": (datetime.now() - item['request_time']).total_seconds()
                }
                for item in self._waiting_queue
            ],
            "max_session_time": self._max_session_time
        }
    
    def get_queue_position(self, session_id: str) -> Optional[int]:
        """获取会话在队列中的位置（1-based）"""
        for i, item in enumerate(self._waiting_queue):
            if item['session_id'] == session_id:
                return i + 1
        return None
    
    def estimate_wait_time(self, session_id: str) -> Optional[int]:
        """估算等待时间（秒）"""
        position = self.get_queue_position(session_id)
        if position is None:
            return None
        
        # 简单估算：当前会话剩余时间 + 前面队列的估算时间
        remaining_time = 0
        if self._current_session and self._session_start_time:
            elapsed = (datetime.now() - self._session_start_time).total_seconds()
            remaining_time = max(0, self._max_session_time - elapsed)
        
        # 假设每个会话平均需要15分钟
        average_session_time = 900  # 15分钟
        estimated_wait = remaining_time + (position - 1) * average_session_time
        
        return int(estimated_wait)

# 全局远程桌面锁实例
remote_desktop_lock = RemoteDesktopLock() 