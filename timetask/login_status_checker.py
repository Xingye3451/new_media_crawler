"""
登录状态检查器
定期检查所有账号的登录状态并更新数据库
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import utils
import db
from utils.api_validator import verify_login_by_api
from config.base_config import (
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_INTERVAL_HOURS,
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_MAX_CONCURRENT,
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_TIMEOUT,
    SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLE_LOGGING
)
from var import media_crawler_db_var


class LoginStatusChecker:
    """登录状态检查器"""
    
    def __init__(self):
        self.check_interval_hours = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_INTERVAL_HOURS
        self.max_concurrent_checks = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_MAX_CONCURRENT
        self.timeout_seconds = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_TIMEOUT
        self.enable_logging = SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLE_LOGGING
        
    async def check_all_accounts_login_status(self) -> Dict[str, Any]:
        """检查所有账号的登录状态"""
        try:
            utils.logger.info("🔄 开始执行登录状态检查任务...")
            start_time = datetime.now()
            
            # 获取所有活跃账号
            accounts = await self._get_all_active_accounts()
            if not accounts:
                utils.logger.info("ℹ️ 没有找到活跃账号，跳过登录状态检查")
                return {
                    "success": True,
                    "message": "没有活跃账号",
                    "total_accounts": 0,
                    "checked_accounts": 0,
                    "logged_in_accounts": 0,
                    "expired_accounts": 0,
                    "error_accounts": 0,
                    "duration_seconds": 0
                }
            
            utils.logger.info(f"📊 找到 {len(accounts)} 个活跃账号，开始检查登录状态")
            
            # 按平台分组账号
            accounts_by_platform = self._group_accounts_by_platform(accounts)
            
            # 并发检查各平台的账号
            results = await self._check_accounts_by_platform(accounts_by_platform)
            
            # 统计结果
            stats = self._calculate_statistics(results)
            
            # 更新数据库中的账号状态
            await self._update_account_status_in_db(results)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            utils.logger.info(f"✅ 登录状态检查完成！")
            utils.logger.info(f"   📈 统计结果:")
            utils.logger.info(f"      - 总账号数: {stats['total_accounts']}")
            utils.logger.info(f"      - 已登录: {stats['logged_in_accounts']}")
            utils.logger.info(f"      - 已过期: {stats['expired_accounts']}")
            utils.logger.info(f"      - 检查失败: {stats['error_accounts']}")
            utils.logger.info(f"      - 耗时: {duration:.2f}秒")
            
            return {
                "success": True,
                "message": "登录状态检查完成",
                "total_accounts": stats['total_accounts'],
                "checked_accounts": stats['checked_accounts'],
                "logged_in_accounts": stats['logged_in_accounts'],
                "expired_accounts": stats['expired_accounts'],
                "error_accounts": stats['error_accounts'],
                "duration_seconds": duration,
                "details": results
            }
            
        except Exception as e:
            utils.logger.error(f"❌ 登录状态检查任务执行失败: {e}")
            return {
                "success": False,
                "message": f"检查失败: {str(e)}",
                "error": str(e)
            }
    
    async def _get_all_active_accounts(self) -> List[Dict[str, Any]]:
        """获取所有活跃账号"""
        try:
            # 获取数据库对象
            async_db_obj = media_crawler_db_var.get()
            if async_db_obj is None:
                utils.logger.error("数据库对象未初始化")
                return []
            
            query = """
                SELECT id, platform, username, nickname, token_data, 
                       is_active, is_valid, last_login_time, created_at
                FROM accounts 
                WHERE is_active = 1
                ORDER BY platform, id
            """
            accounts = await async_db_obj.query(query)
            return accounts
        except Exception as e:
            utils.logger.error(f"获取活跃账号失败: {e}")
            return []
    
    def _group_accounts_by_platform(self, accounts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按平台分组账号"""
        grouped = {}
        for account in accounts:
            platform = account['platform']
            if platform not in grouped:
                grouped[platform] = []
            grouped[platform].append(account)
        return grouped
    
    async def _check_accounts_by_platform(self, accounts_by_platform: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """并发检查各平台的账号登录状态"""
        results = {}
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent_checks)
        
        async def check_platform_accounts(platform: str, accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """检查单个平台的所有账号"""
            platform_results = []
            
            for account in accounts:
                async with semaphore:
                    result = await self._check_single_account(platform, account)
                    platform_results.append(result)
                    
                    # 添加小延迟避免请求过于频繁
                    await asyncio.sleep(0.5)
            
            return platform_results
        
        # 并发执行各平台的检查
        tasks = []
        for platform, accounts in accounts_by_platform.items():
            task = check_platform_accounts(platform, accounts)
            tasks.append(task)
        
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        for i, (platform, accounts) in enumerate(accounts_by_platform.items()):
            if isinstance(platform_results[i], Exception):
                utils.logger.error(f"检查平台 {platform} 账号时出错: {platform_results[i]}")
                results[platform] = []
            else:
                results[platform] = platform_results[i]
        
        return results
    
    async def _check_single_account(self, platform: str, account: Dict[str, Any]) -> Dict[str, Any]:
        """检查单个账号的登录状态"""
        account_id = account['id']
        username = account['username']
        token_data_str = account['token_data']
        
        try:
            # 解析token数据
            import json
            token_data = json.loads(token_data_str) if token_data_str else {}
            cookies = token_data.get('cookies', [])
            
            if not cookies:
                return {
                    "account_id": account_id,
                    "platform": platform,
                    "username": username,
                    "status": "no_cookies",
                    "message": "没有找到cookie数据",
                    "is_logged_in": False,
                    "checked_at": datetime.now().isoformat()
                }
            
            # 使用API验证器检查登录状态
            result = await verify_login_by_api(platform, cookies)
            
            return {
                "account_id": account_id,
                "platform": platform,
                "username": username,
                "status": "checked",
                "message": result.get('message', ''),
                "is_logged_in": result.get('is_logged_in', False),
                "user_info": result.get('user_info', {}),
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            utils.logger.error(f"检查账号 {account_id} ({platform}) 登录状态失败: {e}")
            return {
                "account_id": account_id,
                "platform": platform,
                "username": username,
                "status": "error",
                "message": f"检查失败: {str(e)}",
                "is_logged_in": False,
                "checked_at": datetime.now().isoformat()
            }
    
    def _calculate_statistics(self, results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """计算检查结果统计"""
        stats = {
            'total_accounts': 0,
            'checked_accounts': 0,
            'logged_in_accounts': 0,
            'expired_accounts': 0,
            'error_accounts': 0
        }
        
        for platform, platform_results in results.items():
            for result in platform_results:
                stats['total_accounts'] += 1
                
                if result['status'] == 'checked':
                    stats['checked_accounts'] += 1
                    if result['is_logged_in']:
                        stats['logged_in_accounts'] += 1
                    else:
                        stats['expired_accounts'] += 1
                else:
                    stats['error_accounts'] += 1
        
        return stats
    
    async def _update_account_status_in_db(self, results: Dict[str, List[Dict[str, Any]]]):
        """更新数据库中的账号状态"""
        try:
            update_count = 0
            
            for platform, platform_results in results.items():
                for result in platform_results:
                    account_id = result['account_id']
                    is_logged_in = result['is_logged_in']
                    
                    # 更新账号的登录状态
                    if result['status'] == 'checked':
                        # 更新is_valid字段
                        is_valid = 1 if is_logged_in else 0
                        
                        update_query = """
                            UPDATE accounts 
                            SET is_valid = %s, 
                                last_login_check = NOW(),
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        await async_db_obj.execute(update_query, is_valid, account_id)
                        update_count += 1
                        
                        # 记录状态变更日志
                        if self.enable_logging:
                            log_message = f"账号 {result['username']} ({platform}) 登录状态: {'已登录' if is_logged_in else '已过期'}"
                            utils.logger.info(log_message)
            
            utils.logger.info(f"📝 已更新 {update_count} 个账号的状态")
            
        except Exception as e:
            utils.logger.error(f"更新账号状态失败: {e}")
    
    async def run_scheduled_check(self):
        """运行定时检查任务"""
        try:
            utils.logger.info("⏰ 开始执行定时登录状态检查...")
            result = await self.check_all_accounts_login_status()
            
            if result['success']:
                utils.logger.info("✅ 定时登录状态检查完成")
            else:
                utils.logger.error(f"❌ 定时登录状态检查失败: {result['message']}")
                
        except Exception as e:
            utils.logger.error(f"❌ 定时登录状态检查任务异常: {e}")
    
    def get_next_check_time(self) -> datetime:
        """获取下次检查时间"""
        return datetime.now() + timedelta(hours=self.check_interval_hours)
