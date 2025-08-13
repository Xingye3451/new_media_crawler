"""
登录服务
提供登录状态检查的内部函数
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
from tools import utils
from var import media_crawler_db_var


async def check_platform_login_status(platform: str, account_id: Optional[int] = None) -> Dict[str, Any]:
    """
    检查平台登录状态
    直接调用登录检查逻辑，不通过HTTP API
    
    Args:
        platform: 平台名称
        account_id: 账号ID（可选）
    
    Returns:
        Dict: 登录状态信息
    """
    db = await get_db()
    try:
        utils.logger.info(f"[LOGIN_SERVICE] 检查平台登录状态 - 平台: {platform}, 账号ID: {account_id}")
        
        # 如果指定了账号ID，检查特定账号
        if account_id:
            return await _check_specific_account_login(db, platform, account_id)
        else:
            return await _check_platform_login(db, platform)
            
    except Exception as e:
        utils.logger.error(f"[LOGIN_SERVICE] 登录检查失败: {e}")
        return {
            "code": 500,
            "message": f"登录检查失败: {str(e)}",
            "data": None
        }


async def _check_specific_account_login(db, platform: str, account_id: int) -> Dict[str, Any]:
    """检查特定账号的登录状态"""
    account_query = "SELECT id, account_name, platform FROM social_accounts WHERE id = %s AND platform = %s"
    account = await db.get_first(account_query, account_id, platform)
    
    if not account:
        utils.logger.info(f"[LOGIN_SERVICE] 指定账号不存在: {account_id}, {platform}")
        return {
            "code": 404,
            "message": "指定账号不存在",
            "data": None
        }
    
    # 检查该账号的登录状态
    token_query = """
    SELECT is_valid, expires_at, last_used_at, created_at, token_data
    FROM login_tokens 
    WHERE account_id = %s AND platform = %s AND is_valid = 1
    ORDER BY created_at DESC 
    LIMIT 1
    """
    
    token = await db.get_first(token_query, account_id, platform)
    
    if not token:
        utils.logger.info(f"[LOGIN_SERVICE] 账号无有效token: {account['account_name']}")
        return {
            "code": 200,
            "message": f"账号 {account['account_name']} 未登录",
            "data": {
                "platform": platform,
                "status": "not_logged_in",
                "account_info": {"account_id": account['id'], "account_name": account['account_name']}
            }
        }
    
    # 检查token是否过期
    if token['expires_at'] and token['expires_at'] < datetime.now():
        utils.logger.info(f"[LOGIN_SERVICE] token已过期: {account['account_name']}")
        # 更新token为无效
        update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
        await db.execute(update_query, account_id, platform)
        
        return {
            "code": 200,
            "message": f"账号 {account['account_name']} 登录凭证已过期",
            "data": {
                "platform": platform,
                "status": "expired",
                "account_info": {"account_id": account['id'], "account_name": account['account_name']},
                "last_login_time": token['created_at'].isoformat() if token['created_at'] else None,
                "expires_at": token['expires_at'].isoformat() if token['expires_at'] else None
            }
        }
    
    # 实际验证登录状态
    utils.logger.info(f"[LOGIN_SERVICE] 开始实际验证账号 {account['account_name']} 在平台 {platform} 的登录状态")
    
    # 导入验证函数
    from api.login_management import verify_actual_login_status
    verification_result = await verify_actual_login_status(platform, token['token_data'])
    utils.logger.info(f"[LOGIN_SERVICE] verify_actual_login_status返回: {verification_result}")
    
    # 尝试解析用户信息
    account_info = {"account_id": account['id'], "account_name": account['account_name']}
    try:
        token_data = json.loads(token['token_data'])
        if 'user_info' in token_data:
            account_info.update(token_data['user_info'])
    except:
        pass
    
    if verification_result['is_logged_in']:
        utils.logger.info(f"[LOGIN_SERVICE] 验证通过: {account['account_name']} 已登录")
        # 更新最后使用时间
        update_query = "UPDATE login_tokens SET last_used_at = %s WHERE account_id = %s AND platform = %s"
        await db.execute(update_query, datetime.now(), account_id, platform)
        
        return {
            "code": 200,
            "message": f"账号 {account['account_name']} 已登录（已验证）",
            "data": {
                "platform": platform,
                "status": "logged_in",
                "account_info": account_info,
                "last_login_time": token['created_at'].isoformat() if token['created_at'] else None,
                "expires_at": token['expires_at'].isoformat() if token['expires_at'] else None
            }
        }
    else:
        utils.logger.info(f"[LOGIN_SERVICE] 验证失败: {account['account_name']} 未登录，原因: {verification_result.get('message')}")
        
        # 根据验证结果决定是否将token设为无效
        verification_message = verification_result.get('message', '')
        is_logged_in = verification_result.get('is_logged_in', False)
        
        # 如果明确验证失败，将token设为无效
        if not is_logged_in and ('验证失败' in verification_message or '未登录' in verification_message):
            update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
            await db.execute(update_query, account_id, platform)
            utils.logger.info(f"[LOGIN_SERVICE] 已将无效token设为无效: {account['account_name']}")
        
        return {
            "code": 200,
            "message": f"账号 {account['account_name']} 未登录",
            "data": {
                "platform": platform,
                "status": "not_logged_in",
                "account_info": account_info,
                "verification_message": verification_message
            }
        }


async def _check_platform_login(db, platform: str) -> Dict[str, Any]:
    """检查平台的登录状态（不指定具体账号）"""
    # 查找平台下所有有效账号
    account_query = """
    SELECT sa.id, sa.account_name, sa.platform, lt.is_valid, lt.expires_at, lt.last_used_at, lt.created_at, lt.token_data
    FROM social_accounts sa
    LEFT JOIN login_tokens lt ON sa.id = lt.account_id AND lt.is_valid = 1
    WHERE sa.platform = %s AND sa.is_active = 1
    ORDER BY lt.created_at DESC
    """
    
    accounts = await db.query(account_query, platform)
    
    if not accounts:
        return {
            "code": 200,
            "message": f"平台 {platform} 没有可用账号",
            "data": {
                "platform": platform,
                "status": "no_accounts",
                "accounts": []
            }
        }
    
    # 检查每个账号的登录状态
    logged_in_accounts = []
    for account in accounts:
        if account['is_valid'] and account['token_data']:
            # 检查token是否过期
            if account['expires_at'] and account['expires_at'] < datetime.now():
                # 更新token为无效
                update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
                await db.execute(update_query, account['id'], platform)
                continue
            
            # 实际验证登录状态
            from api.login_management import verify_actual_login_status
            verification_result = await verify_actual_login_status(platform, account['token_data'])
            
            if verification_result['is_logged_in']:
                logged_in_accounts.append({
                    "account_id": account['id'],
                    "account_name": account['account_name'],
                    "last_login_time": account['created_at'].isoformat() if account['created_at'] else None,
                    "expires_at": account['expires_at'].isoformat() if account['expires_at'] else None
                })
    
    if logged_in_accounts:
        return {
            "code": 200,
            "message": f"平台 {platform} 有 {len(logged_in_accounts)} 个账号已登录",
            "data": {
                "platform": platform,
                "status": "logged_in",
                "accounts": logged_in_accounts
            }
        }
    else:
        return {
            "code": 200,
            "message": f"平台 {platform} 没有已登录的账号",
            "data": {
                "platform": platform,
                "status": "not_logged_in",
                "accounts": []
            }
        }


async def get_db():
    """获取数据库连接"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        # 如果上下文变量没有设置，尝试初始化数据库连接
        from db import init_mediacrawler_db
        await init_mediacrawler_db()
        return media_crawler_db_var.get()
