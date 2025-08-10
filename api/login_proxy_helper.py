"""
登录代理辅助模块
在远程登录时使用青果长效代理，并记录代理信息到login_tokens表
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime

from tools import utils
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager, ProxyInfo


async def get_proxy_for_login(platform: str, account_id: int) -> Optional[ProxyInfo]:
    """为登录获取代理"""
    try:
        # 检查是否启用代理
        from config.base_config import ENABLE_IP_PROXY
        if not ENABLE_IP_PROXY:
            utils.logger.info(f"[LOGIN_PROXY] 代理功能未启用，使用直连登录")
            return None
        
        # 获取青果代理管理器
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 获取代理
        proxy_info = await proxy_manager.get_proxy_for_login(platform, account_id)
        
        if proxy_info:
            utils.logger.info(f"[LOGIN_PROXY] 为平台 {platform} 账号 {account_id} 获取代理: {proxy_info.ip}:{proxy_info.port}")
        else:
            utils.logger.warning(f"[LOGIN_PROXY] 为平台 {platform} 账号 {account_id} 获取代理失败")
        
        return proxy_info
        
    except Exception as e:
        utils.logger.error(f"[LOGIN_PROXY] 获取登录代理失败: {e}")
        return None


def format_proxy_info_for_token(proxy_info: ProxyInfo) -> Dict[str, Any]:
    """格式化代理信息用于存储到login_tokens表"""
    if not proxy_info:
        return None
    
    return {
        "proxy_id": proxy_info.id,
        "ip": proxy_info.ip,
        "port": proxy_info.port,
        "username": proxy_info.username,
        "password": proxy_info.password,
        "proxy_type": proxy_info.proxy_type,
        "expire_ts": proxy_info.expire_ts,
        "created_at": proxy_info.created_at.isoformat() if proxy_info.created_at else None,
        "status": proxy_info.status.value,
        "platform": proxy_info.platform,
        "account_id": proxy_info.account_id
    }


async def save_login_token_with_proxy(
    account_id: int,
    platform: str,
    token_data: str,
    user_agent: str = None,
    proxy_info: ProxyInfo = None,
    expires_at: datetime = None
) -> bool:
    """保存登录令牌和代理信息"""
    try:
        from var import media_crawler_db_var
        from db import init_mediacrawler_db
        
        # 初始化数据库
        await init_mediacrawler_db()
        db = media_crawler_db_var.get()
        
        # 格式化代理信息
        proxy_info_json = None
        proxy_id = None
        
        if proxy_info:
            proxy_info_dict = format_proxy_info_for_token(proxy_info)
            proxy_info_json = json.dumps(proxy_info_dict, ensure_ascii=False)
            proxy_id = proxy_info.id
        
        # 插入登录令牌
        insert_query = """
            INSERT INTO login_tokens (
                account_id, platform, token_type, token_data, 
                user_agent, proxy_info, proxy_id, expires_at, 
                is_valid, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query,
            account_id, platform, "cookie", token_data,
            user_agent, proxy_info_json, proxy_id, expires_at,
            1, datetime.now(), datetime.now()
        )
        
        utils.logger.info(f"[LOGIN_PROXY] 登录令牌保存成功，账号ID: {account_id}, 平台: {platform}")
        
        # 标记代理使用成功
        if proxy_info and proxy_info.id:
            proxy_manager = await get_qingguo_proxy_manager()
            await proxy_manager.mark_proxy_success(proxy_info.id)
        
        return True
        
    except Exception as e:
        utils.logger.error(f"[LOGIN_PROXY] 保存登录令牌失败: {e}")
        return False


async def get_proxy_from_login_token(account_id: int, platform: str) -> Optional[ProxyInfo]:
    """从登录令牌中获取代理信息"""
    try:
        from var import media_crawler_db_var
        from db import init_mediacrawler_db
        
        # 初始化数据库
        await init_mediacrawler_db()
        db = media_crawler_db_var.get()
        
        # 查询最新的有效登录令牌
        query = """
            SELECT proxy_info, proxy_id, expires_at
            FROM login_tokens 
            WHERE account_id = %s AND platform = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        result = await db.get_first(query, account_id, platform)
        
        if not result or not result['proxy_info']:
            utils.logger.info(f"[LOGIN_PROXY] 账号 {account_id} 平台 {platform} 没有找到代理信息")
            return None
        
        # 解析代理信息
        proxy_info_dict = json.loads(result['proxy_info'])
        
        # 检查是否过期
        if result['expires_at'] and result['expires_at'] < datetime.now():
            utils.logger.warning(f"[LOGIN_PROXY] 账号 {account_id} 平台 {platform} 的代理已过期")
            return None
        
        # 创建代理信息对象
        from proxy.qingguo_long_term_proxy import ProxyInfo, ProxyStatus
        
        proxy_info = ProxyInfo(
            id=proxy_info_dict.get('proxy_id'),
            ip=proxy_info_dict['ip'],
            port=proxy_info_dict['port'],
            username=proxy_info_dict['username'],
            password=proxy_info_dict.get('password', ''),
            proxy_type=proxy_info_dict.get('proxy_type', 'http'),
            expire_ts=proxy_info_dict['expire_ts'],
            created_at=datetime.fromisoformat(proxy_info_dict['created_at']) if proxy_info_dict.get('created_at') else datetime.now(),
            status=ProxyStatus(proxy_info_dict.get('status', 'active')),
            platform=proxy_info_dict.get('platform'),
            account_id=proxy_info_dict.get('account_id')
        )
        
        utils.logger.info(f"[LOGIN_PROXY] 从登录令牌获取代理: {proxy_info.ip}:{proxy_info.port}")
        return proxy_info
        
    except Exception as e:
        utils.logger.error(f"[LOGIN_PROXY] 从登录令牌获取代理失败: {e}")
        return None


async def update_login_token_proxy_usage(account_id: int, platform: str, success: bool = True, error_message: str = None):
    """更新登录令牌的代理使用情况"""
    try:
        from var import media_crawler_db_var
        from db import init_mediacrawler_db
        
        # 初始化数据库
        await init_mediacrawler_db()
        db = media_crawler_db_var.get()
        
        # 获取最新的登录令牌
        query = """
            SELECT proxy_id FROM login_tokens 
            WHERE account_id = %s AND platform = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        result = await db.get_first(query, account_id, platform)
        
        if not result or not result['proxy_id']:
            return
        
        proxy_id = result['proxy_id']
        
        # 更新代理使用情况
        proxy_manager = await get_qingguo_proxy_manager()
        
        if success:
            await proxy_manager.mark_proxy_success(proxy_id)
            utils.logger.info(f"[LOGIN_PROXY] 代理 {proxy_id} 使用成功")
        else:
            await proxy_manager.mark_proxy_failed(proxy_id, error_message)
            utils.logger.warning(f"[LOGIN_PROXY] 代理 {proxy_id} 使用失败: {error_message}")
        
    except Exception as e:
        utils.logger.error(f"[LOGIN_PROXY] 更新代理使用情况失败: {e}")


async def cleanup_expired_proxies():
    """清理过期的代理"""
    try:
        proxy_manager = await get_qingguo_proxy_manager()
        await proxy_manager.cleanup_expired_proxies()
    except Exception as e:
        utils.logger.error(f"[LOGIN_PROXY] 清理过期代理失败: {e}")
