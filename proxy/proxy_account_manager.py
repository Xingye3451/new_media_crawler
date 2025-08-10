#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理账号管理器
从数据库获取代理账号配置，替代原有的配置文件方式
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import json

from tools import utils
from var import media_crawler_db_var

@dataclass
class ProxyAccountInfo:
    """代理账号信息"""
    account_id: str
    provider: str
    provider_name: str
    api_key: str
    api_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    signature: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    max_pool_size: int = 10
    validate_ip: bool = True
    description: Optional[str] = None
    config_json: Optional[Dict] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0

class ProxyAccountManager:
    """代理账号管理器"""
    
    def __init__(self):
        self._accounts_cache: Dict[str, ProxyAccountInfo] = {}
        self._default_accounts: Dict[str, ProxyAccountInfo] = {}
        self._cache_updated_at: Optional[datetime] = None
        self._cache_ttl = 300  # 5分钟缓存
    
    async def get_db(self):
        """获取数据库连接"""
        try:
            return media_crawler_db_var.get()
        except LookupError:
            from db import init_mediacrawler_db
            await init_mediacrawler_db()
            return media_crawler_db_var.get()
    
    async def _load_accounts_from_db(self) -> List[ProxyAccountInfo]:
        """从数据库加载代理账号"""
        try:
            db = await self.get_db()
            
            query = """
                SELECT * FROM proxy_accounts 
                WHERE is_active = 1 
                ORDER BY is_default DESC, created_at DESC
            """
            
            results = await db.query(query)
            
            accounts = []
            for row in results:
                account = ProxyAccountInfo(
                    account_id=row['account_id'],
                    provider=row['provider'],
                    provider_name=row['provider_name'],
                    api_key=row['api_key'],
                    api_secret=row.get('api_secret'),
                    username=row.get('username'),
                    password=row.get('password'),
                    signature=row.get('signature'),
                    endpoint_url=row.get('endpoint_url'),
                    is_active=bool(row['is_active']),
                    is_default=bool(row['is_default']),
                    max_pool_size=row['max_pool_size'],
                    validate_ip=bool(row['validate_ip']),
                    description=row.get('description'),
                    config_json=json.loads(row['config_json']) if row.get('config_json') else None,
                    last_used_at=row.get('last_used_at'),
                    usage_count=row.get('usage_count', 0),
                    success_count=row.get('success_count', 0),
                    fail_count=row.get('fail_count', 0)
                )
                accounts.append(account)
            
            return accounts
            
        except Exception as e:
            utils.logger.error(f"从数据库加载代理账号失败: {e}")
            return []
    
    async def _update_cache(self):
        """更新缓存"""
        try:
            accounts = await self._load_accounts_from_db()
            
            # 清空缓存
            self._accounts_cache.clear()
            self._default_accounts.clear()
            
            # 填充缓存
            for account in accounts:
                self._accounts_cache[account.account_id] = account
                
                # 记录默认账号
                if account.is_default:
                    self._default_accounts[account.provider] = account
            
            self._cache_updated_at = datetime.now()
            utils.logger.debug(f"代理账号缓存已更新，共 {len(accounts)} 个账号")
            
        except Exception as e:
            utils.logger.error(f"更新代理账号缓存失败: {e}")
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_updated_at:
            return False
        
        elapsed = (datetime.now() - self._cache_updated_at).total_seconds()
        return elapsed < self._cache_ttl
    
    async def get_account(self, account_id: str) -> Optional[ProxyAccountInfo]:
        """获取指定账号"""
        if not self._is_cache_valid():
            await self._update_cache()
        
        return self._accounts_cache.get(account_id)
    
    async def get_default_account(self, provider: str) -> Optional[ProxyAccountInfo]:
        """获取指定提供商的默认账号"""
        if not self._is_cache_valid():
            await self._update_cache()
        
        return self._default_accounts.get(provider)
    
    async def get_accounts_by_provider(self, provider: str) -> List[ProxyAccountInfo]:
        """获取指定提供商的所有账号"""
        if not self._is_cache_valid():
            await self._update_cache()
        
        return [
            account for account in self._accounts_cache.values()
            if account.provider == provider and account.is_active
        ]
    
    async def get_all_active_accounts(self) -> List[ProxyAccountInfo]:
        """获取所有活跃账号"""
        if not self._is_cache_valid():
            await self._update_cache()
        
        return list(self._accounts_cache.values())
    
    async def get_qingguo_account(self) -> Optional[ProxyAccountInfo]:
        """获取青果代理账号（兼容性方法）"""
        return await self.get_default_account('qingguo')
    
    async def get_kuaidaili_account(self) -> Optional[ProxyAccountInfo]:
        """获取快代理账号（兼容性方法）"""
        return await self.get_default_account('kuaidaili')
    
    async def get_jisuhttp_account(self) -> Optional[ProxyAccountInfo]:
        """获取极速HTTP代理账号（兼容性方法）"""
        return await self.get_default_account('jisuhttp')
    
    async def log_account_usage(self, account_id: str, operation: str, success: bool, 
                               response_time: Optional[int] = None, error_message: Optional[str] = None,
                               proxy_id: Optional[str] = None, ip: Optional[str] = None, 
                               port: Optional[int] = None):
        """记录账号使用日志"""
        try:
            db = await self.get_db()
            
            # 记录日志
            log_query = """
                INSERT INTO proxy_account_logs (
                    account_id, provider, operation, proxy_id, ip, port,
                    success, response_time, error_message, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            account = await self.get_account(account_id)
            provider = account.provider if account else 'unknown'
            
            await db.execute(log_query, account_id, provider, operation, proxy_id, ip, port,
                          1 if success else 0, response_time, error_message, datetime.now())
            
            # 更新账号统计
            if account:
                update_query = """
                    UPDATE proxy_accounts SET 
                        usage_count = usage_count + 1,
                        success_count = success_count + %s,
                        fail_count = fail_count + %s,
                        last_used_at = %s,
                        updated_at = %s
                    WHERE account_id = %s
                """
                
                success_count = 1 if success else 0
                fail_count = 1 if not success else 0
                
                await db.execute(update_query, success_count, fail_count, 
                               datetime.now(), datetime.now(), account_id)
                
                # 更新缓存
                if account_id in self._accounts_cache:
                    self._accounts_cache[account_id].usage_count += 1
                    if success:
                        self._accounts_cache[account_id].success_count += 1
                    else:
                        self._accounts_cache[account_id].fail_count += 1
                    self._accounts_cache[account_id].last_used_at = datetime.now()
            
        except Exception as e:
            utils.logger.error(f"记录代理账号使用日志失败: {e}")
    
    async def refresh_cache(self):
        """手动刷新缓存"""
        await self._update_cache()

# 全局代理账号管理器实例
_proxy_account_manager: Optional[ProxyAccountManager] = None

async def get_proxy_account_manager() -> ProxyAccountManager:
    """获取代理账号管理器实例"""
    global _proxy_account_manager
    
    if _proxy_account_manager is None:
        _proxy_account_manager = ProxyAccountManager()
        await _proxy_account_manager._update_cache()
    
    return _proxy_account_manager

# 兼容性函数
async def get_qingguo_proxy_config() -> Optional[Dict[str, Any]]:
    """获取青果代理配置（兼容性函数）"""
    try:
        account_manager = await get_proxy_account_manager()
        account = await account_manager.get_qingguo_account()
        
        if not account:
            utils.logger.warning("未找到青果代理账号配置")
            return None
        
        return {
            "key": account.api_key,
            "pwd": account.api_secret,
            "username": account.username,
            "password": account.password,
            "endpoint_url": account.endpoint_url,
            "max_pool_size": account.max_pool_size,
            "validate_ip": account.validate_ip,
            "description": account.description,
            "config_json": account.config_json
        }
        
    except Exception as e:
        utils.logger.error(f"获取青果代理配置失败: {e}")
        return None

async def get_proxy_config_by_provider(provider: str) -> Optional[Dict[str, Any]]:
    """根据提供商获取代理配置"""
    try:
        account_manager = await get_proxy_account_manager()
        account = await account_manager.get_default_account(provider)
        
        if not account:
            utils.logger.warning(f"未找到 {provider} 代理账号配置")
            return None
        
        return {
            "account_id": account.account_id,
            "provider": account.provider,
            "provider_name": account.provider_name,
            "api_key": account.api_key,
            "api_secret": account.api_secret,
            "username": account.username,
            "password": account.password,
            "signature": account.signature,
            "endpoint_url": account.endpoint_url,
            "max_pool_size": account.max_pool_size,
            "validate_ip": account.validate_ip,
            "description": account.description,
            "config_json": account.config_json
        }
        
    except Exception as e:
        utils.logger.error(f"获取 {provider} 代理配置失败: {e}")
        return None
