"""
任务调度器
管理定时任务的执行和调度
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import utils
from config.base_config import (
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLED,
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_INTERVAL_HOURS,
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_START_TIME,
    SCHEDULED_TASKS_SCHEDULER_MAX_CONCURRENT_TASKS,
    SCHEDULED_TASKS_SCHEDULER_TASK_TIMEOUT_SECONDS,
    SCHEDULED_TASKS_SCHEDULER_ENABLE_LOGGING
)
from .login_status_checker import LoginStatusChecker


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        
        # 初始化登录状态检查器
        self.login_checker = LoginStatusChecker()
        
        # 从配置文件读取调度配置
        self._load_scheduler_config()
    
    def _load_scheduler_config(self):
        """从配置文件加载调度器配置"""
        try:
            # 使用base_config中的配置
            self.login_check_interval = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_INTERVAL_HOURS
            self.login_check_enabled = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLED
            self.login_check_start_time = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_START_TIME
            
            self.max_concurrent_tasks = SCHEDULED_TASKS_SCHEDULER_MAX_CONCURRENT_TASKS
            self.task_timeout = SCHEDULED_TASKS_SCHEDULER_TASK_TIMEOUT_SECONDS
            self.enable_logging = SCHEDULED_TASKS_SCHEDULER_ENABLE_LOGGING
            
            utils.logger.info("📋 定时任务调度器配置加载完成")
            utils.logger.debug(f"   - 登录状态检查间隔: {self.login_check_interval}小时")
            utils.logger.debug(f"   - 登录状态检查启用: {self.login_check_enabled}")
            utils.logger.debug(f"   - 最大并发任务数: {self.max_concurrent_tasks}")
            
        except Exception as e:
            utils.logger.error(f"加载调度器配置失败: {e}")
            # 使用默认配置
            self.login_check_interval = 6
            self.login_check_enabled = True
            self.login_check_start_time = "02:00"
            self.max_concurrent_tasks = 3
            self.task_timeout = 3600
            self.enable_logging = True
    
    async def start(self):
        """启动任务调度器"""
        if self.is_running:
            utils.logger.warning("⚠️ 任务调度器已在运行中")
            return
        
        try:
            utils.logger.info("🚀 启动定时任务调度器...")
            self.is_running = True
            
            # 启动登录状态检查任务
            if self.login_check_enabled:
                await self._start_login_status_check_task()
            
            utils.logger.info("✅ 定时任务调度器启动完成")
            
        except Exception as e:
            utils.logger.error(f"❌ 启动任务调度器失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """停止任务调度器"""
        try:
            utils.logger.info("🛑 停止定时任务调度器...")
            self.is_running = False
            
            # 取消所有正在运行的任务
            for task_name, task in self.tasks.items():
                if not task.done():
                    utils.logger.debug(f"取消任务: {task_name}")
                    task.cancel()
            
            # 等待所有任务完成
            if self.tasks:
                await asyncio.gather(*self.tasks.values(), return_exceptions=True)
            
            self.tasks.clear()
            self.scheduled_tasks.clear()
            
            utils.logger.info("✅ 定时任务调度器已停止")
            
        except Exception as e:
            utils.logger.error(f"❌ 停止任务调度器失败: {e}")
    
    async def _start_login_status_check_task(self):
        """启动登录状态检查任务"""
        try:
            task_name = "login_status_check"
            
            # 创建任务
            task = asyncio.create_task(
                self._run_login_status_check_scheduler(),
                name=task_name
            )
            
            self.tasks[task_name] = task
            self.scheduled_tasks[task_name] = {
                "type": "login_status_check",
                "interval_hours": self.login_check_interval,
                "start_time": datetime.now(),
                "next_run": self._calculate_next_run_time(),
                "enabled": True
            }
            
            utils.logger.info(f"✅ 登录状态检查任务已启动，下次执行时间: {self.scheduled_tasks[task_name]['next_run']}")
            
        except Exception as e:
            utils.logger.error(f"❌ 启动登录状态检查任务失败: {e}")
    
    async def _run_login_status_check_scheduler(self):
        """运行登录状态检查调度器"""
        try:
            while self.is_running:
                try:
                    # 计算下次执行时间
                    next_run = self._calculate_next_run_time()
                    self.scheduled_tasks["login_status_check"]["next_run"] = next_run
                    
                    # 等待到下次执行时间
                    wait_seconds = (next_run - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        utils.logger.debug(f"⏰ 登录状态检查任务将在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 执行")
                        await asyncio.sleep(wait_seconds)
                    
                    # 检查调度器是否仍在运行
                    if not self.is_running:
                        break
                    
                    # 执行登录状态检查
                    await self._execute_login_status_check()
                    
                except asyncio.CancelledError:
                    utils.logger.info("🛑 登录状态检查任务被取消")
                    break
                except Exception as e:
                    utils.logger.error(f"❌ 登录状态检查调度器异常: {e}")
                    # 出错后等待1小时再重试
                    await asyncio.sleep(3600)
            
        except Exception as e:
            utils.logger.error(f"❌ 登录状态检查调度器失败: {e}")
    
    def _calculate_next_run_time(self) -> datetime:
        """计算下次执行时间"""
        now = datetime.now()
        
        # 解析开始时间
        try:
            start_hour, start_minute = map(int, self.login_check_start_time.split(':'))
            next_run = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            
            # 如果今天的时间已过，设置为明天
            if next_run <= now:
                next_run += timedelta(days=1)
            
            # 如果距离下次执行时间超过间隔时间，调整为间隔时间后
            time_diff = (next_run - now).total_seconds() / 3600
            if time_diff > self.login_check_interval:
                next_run = now + timedelta(hours=self.login_check_interval)
            
            return next_run
            
        except Exception as e:
            utils.logger.error(f"计算下次执行时间失败: {e}")
            # 默认1小时后执行
            return now + timedelta(hours=1)
    
    async def _execute_login_status_check(self):
        """执行登录状态检查任务"""
        try:
            utils.logger.info("🔄 开始执行定时登录状态检查...")
            start_time = datetime.now()
            
            # 执行登录状态检查
            result = await self.login_checker.check_all_accounts_login_status()
            
            # 记录执行结果
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                utils.logger.info(f"✅ 定时登录状态检查完成，耗时: {duration:.2f}秒")
                utils.logger.info(f"   📊 检查结果: 总账号 {result['total_accounts']}, "
                                f"已登录 {result['logged_in_accounts']}, "
                                f"已过期 {result['expired_accounts']}, "
                                f"检查失败 {result['error_accounts']}")
            else:
                utils.logger.error(f"❌ 定时登录状态检查失败: {result['message']}")
            
            # 更新任务状态
            self.scheduled_tasks["login_status_check"]["last_run"] = start_time
            self.scheduled_tasks["login_status_check"]["last_duration"] = duration
            self.scheduled_tasks["login_status_check"]["last_result"] = result
            
        except Exception as e:
            utils.logger.error(f"❌ 执行登录状态检查任务失败: {e}")
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        try:
            status = {
                "is_running": self.is_running,
                "total_tasks": len(self.tasks),
                "scheduled_tasks": {}
            }
            
            for task_name, task_info in self.scheduled_tasks.items():
                task_status = {
                    "enabled": task_info.get("enabled", False),
                    "type": task_info.get("type", "unknown"),
                    "next_run": task_info.get("next_run", ""),
                    "last_run": task_info.get("last_run", ""),
                    "last_duration": task_info.get("last_duration", 0),
                    "last_result": task_info.get("last_result", {})
                }
                
                # 检查任务是否正在运行
                if task_name in self.tasks:
                    task = self.tasks[task_name]
                    task_status["is_running"] = not task.done()
                    task_status["is_cancelled"] = task.cancelled()
                    if task.done():
                        try:
                            task_status["exception"] = str(task.exception())
                        except:
                            task_status["exception"] = None
                else:
                    task_status["is_running"] = False
                    task_status["is_cancelled"] = False
                    task_status["exception"] = None
                
                status["scheduled_tasks"][task_name] = task_status
            
            return status
            
        except Exception as e:
            utils.logger.error(f"获取调度器状态失败: {e}")
            return {
                "is_running": self.is_running,
                "error": str(e)
            }
    
    async def manually_trigger_login_check(self) -> Dict[str, Any]:
        """手动触发登录状态检查"""
        try:
            utils.logger.info("🔧 手动触发登录状态检查...")
            result = await self.login_checker.check_all_accounts_login_status()
            
            # 更新任务状态
            self.scheduled_tasks["login_status_check"]["last_run"] = datetime.now()
            self.scheduled_tasks["login_status_check"]["last_result"] = result
            
            return result
            
        except Exception as e:
            utils.logger.error(f"手动触发登录状态检查失败: {e}")
            return {
                "success": False,
                "message": f"手动触发失败: {str(e)}",
                "error": str(e)
            }


# 全局调度器实例
scheduler = TaskScheduler()
