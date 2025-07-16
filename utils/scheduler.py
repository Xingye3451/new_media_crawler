#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时任务调度器
"""

import asyncio
from typing import Dict, List
from datetime import datetime
from tools import utils
from .db_utils import check_token_validity, cleanup_expired_tokens, get_expiring_tokens


class TokenValidityScheduler:
    """凭证有效性检查调度器"""
    
    def __init__(self):
        self.is_running = False
        self.tasks = []
        self.platforms = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
        
    async def start(self):
        """启动定时任务"""
        if self.is_running:
            utils.logger.warning("[Scheduler] 定时任务已在运行中")
            return
            
        self.is_running = True
        utils.logger.info("[Scheduler] 启动凭证有效性检查定时任务")
        
        # 创建定时任务
        tasks = [
            asyncio.create_task(self._cleanup_expired_tokens_loop()),  # 每小时清理过期凭证
            asyncio.create_task(self._check_expiring_tokens_loop()),   # 每6小时检查即将过期的凭证
            asyncio.create_task(self._validate_tokens_loop()),         # 每12小时验证所有凭证
        ]
        self.tasks.extend(tasks)
        
        utils.logger.info("[Scheduler] 所有定时任务已启动")
        
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return
            
        self.is_running = False
        utils.logger.info("[Scheduler] 停止定时任务")
        
        # 取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.tasks.clear()
        utils.logger.info("[Scheduler] 所有定时任务已停止")
        
    async def _cleanup_expired_tokens_loop(self):
        """清理过期凭证循环任务 - 每小时执行一次"""
        # 启动时等待5分钟，确保数据库连接稳定
        await asyncio.sleep(300)
        
        while self.is_running:
            try:
                utils.logger.info("[Scheduler] 开始清理过期凭证")
                count = await cleanup_expired_tokens()
                if count > 0:
                    utils.logger.info(f"[Scheduler] 清理了 {count} 个过期凭证")
                else:
                    utils.logger.debug("[Scheduler] 没有需要清理的过期凭证")
                    
                # 每小时执行一次
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                utils.logger.error(f"[Scheduler] 清理过期凭证任务出错: {e}")
                await asyncio.sleep(3600)  # 出错后也等待1小时再重试
                
    async def _check_expiring_tokens_loop(self):
        """检查即将过期凭证循环任务 - 每6小时执行一次"""
        # 启动时等待10分钟，确保数据库连接稳定
        await asyncio.sleep(600)
        
        while self.is_running:
            try:
                utils.logger.info("[Scheduler] 检查即将过期的凭证")
                expiring_tokens = await get_expiring_tokens(24)  # 24小时内过期
                
                if expiring_tokens:
                    utils.logger.warning(f"[Scheduler] 发现 {len(expiring_tokens)} 个即将过期的凭证:")
                    for token in expiring_tokens:
                        utils.logger.warning(
                            f"  - 平台: {token['platform']}, "
                            f"账号: {token['account_name']} ({token['account_id']}), "
                            f"过期时间: {token['expires_at']}"
                        )
                else:
                    utils.logger.debug("[Scheduler] 没有即将过期的凭证")
                    
                # 每6小时执行一次
                await asyncio.sleep(21600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                utils.logger.error(f"[Scheduler] 检查即将过期凭证任务出错: {e}")
                await asyncio.sleep(21600)
                
    async def _validate_tokens_loop(self):
        """验证所有凭证循环任务 - 每12小时执行一次"""
        # 启动时等待15分钟，确保数据库连接稳定
        await asyncio.sleep(900)
        
        while self.is_running:
            try:
                utils.logger.info("[Scheduler] 开始验证所有平台凭证有效性")
                
                for platform in self.platforms:
                    try:
                        validity = await check_token_validity(platform)
                        
                        if validity["status"] == "not_found":
                            utils.logger.info(f"[Scheduler] {platform}: 无凭证")
                        elif validity["status"] == "valid":
                            utils.logger.info(f"[Scheduler] {platform}: 凭证有效")
                        elif validity["status"] == "expiring_soon":
                            utils.logger.warning(
                                f"[Scheduler] {platform}: 凭证即将过期 - "
                                f"账号: {validity['account_id']}, "
                                f"过期时间: {validity['expires_at']}"
                            )
                        elif validity["status"] == "expired":
                            utils.logger.warning(
                                f"[Scheduler] {platform}: 凭证已过期并已标记无效 - "
                                f"账号: {validity['account_id']}"
                            )
                        else:
                            utils.logger.error(f"[Scheduler] {platform}: 验证失败 - {validity['message']}")
                            
                        # 避免过于频繁的数据库查询
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        utils.logger.error(f"[Scheduler] 验证 {platform} 凭证时出错: {e}")
                
                utils.logger.info("[Scheduler] 所有平台凭证验证完成")
                
                # 每12小时执行一次
                await asyncio.sleep(43200)
            except asyncio.CancelledError:
                break
            except Exception as e:
                utils.logger.error(f"[Scheduler] 验证凭证任务出错: {e}")
                await asyncio.sleep(43200)


# 全局调度器实例
scheduler = TokenValidityScheduler()


async def start_scheduler():
    """启动调度器"""
    await scheduler.start()


async def stop_scheduler():
    """停止调度器"""
    await scheduler.stop()


async def get_scheduler_status() -> Dict:
    """获取调度器状态"""
    return {
        "is_running": scheduler.is_running,
        "task_count": len(scheduler.tasks),
        "platforms": scheduler.platforms,
        "status": "running" if scheduler.is_running else "stopped"
    } 