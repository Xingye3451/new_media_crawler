#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库工具函数
"""

import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from tools import utils


async def _get_db_connection():
    """获取数据库连接（兼容不同的异步上下文）"""
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
            minsize=1,
            maxsize=10,
            charset='utf8mb4',
            # 设置时区为UTC+8
            init_command="SET time_zone = '+08:00'"
        )
        
        async_db_obj = AsyncMysqlDB(pool)
        return async_db_obj
        
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 获取数据库连接失败: {e}")
        return None


async def get_cookies_from_database(platform: str, account_id: Optional[str] = None) -> str:
    """从数据库获取指定平台和账号的cookies"""
    try:
        db = await _get_db_connection()
        if not db:
            utils.logger.error("[DB_UTILS] 无法获取数据库连接")
            return ""
        
        # 🆕 根据account_id参数构建查询条件
        if account_id:
            # 查询指定账号的最新有效token
            query = """
            SELECT token_data, created_at, expires_at
            FROM login_tokens 
            WHERE platform = %s AND account_id = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
            """
            result = await db.get_first(query, platform, account_id)
            utils.logger.info(f"[DB_UTILS] 查询指定账号cookies - 平台: {platform}, 账号ID: {account_id}")
        else:
            # 查询平台最新登录的token（兼容旧逻辑）
            query = """
            SELECT token_data, created_at, expires_at
            FROM login_tokens 
            WHERE platform = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
            """
            result = await db.get_first(query, platform)
            utils.logger.info(f"[DB_UTILS] 查询平台最新cookies - 平台: {platform}")
        
        if result and result['token_data']:
            token_data_str = result['token_data']
            
            # 🆕 修复：token_data存储的是JSON格式的cookies字典
            try:
                token_data = json.loads(token_data_str)
                
                # token_data本身就是cookies的字典格式 {"cookie_name": "cookie_value", ...}
                if isinstance(token_data, dict):
                    # 将cookies字典转换为字符串格式
                    cookie_parts = []
                    for key, value in token_data.items():
                        if key and value and isinstance(value, str) and key not in ["user_info"]:
                            cookie_parts.append(f"{key}={value}")
                    cookie_str = "; ".join(cookie_parts)
                    utils.logger.info(f"[DB_UTILS] 从token_data解析cookies，字段数: {len(token_data)}, 转换后长度: {len(cookie_str)}")
                else:
                    # 如果不是字典，直接当作字符串使用
                    cookie_str = str(token_data)
                    utils.logger.info(f"[DB_UTILS] token_data非字典格式，直接使用，长度: {len(cookie_str)}")
                    
            except json.JSONDecodeError:
                # 如果无法解析JSON，直接当作字符串使用
                cookie_str = token_data_str
                utils.logger.info(f"[DB_UTILS] token_data非JSON格式，直接使用，长度: {len(cookie_str)}")
            
            utils.logger.info(f"[DB_UTILS] 成功读取cookies，最终长度: {len(cookie_str)}")
            return cookie_str
        else:
            utils.logger.warning(f"[DB_UTILS] 未找到有效的cookies - 平台: {platform}, 账号ID: {account_id}")
            return ""
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 读取cookies失败 - 平台: {platform}, 账号ID: {account_id}, 错误: {e}")
        return ""


async def get_account_list_by_platform(platform: str) -> List[Dict]:
    """获取指定平台的所有账号列表"""
    try:
        db = await _get_db_connection()
        if not db:
            utils.logger.error("[DB_UTILS] 无法获取数据库连接")
            return []
        
        query = """
        SELECT DISTINCT lt.account_id, 
               COALESCE(sa.account_name, CONCAT('账号_', lt.account_id)) as account_name,
               MAX(lt.created_at) as last_login_time,
               COUNT(*) as login_count
        FROM login_tokens lt
        LEFT JOIN social_accounts sa ON lt.account_id = sa.id
        WHERE lt.platform = %s AND lt.is_valid = 1
        GROUP BY lt.account_id, sa.account_name
        ORDER BY last_login_time DESC
        """
        
        results = await db.query(query, platform)
        utils.logger.info(f"[DB_UTILS] 获取平台账号列表 - 平台: {platform}, 账号数: {len(results)}")
        return results
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 获取账号列表失败 - 平台: {platform}, 错误: {e}")
        return []


async def check_token_validity(platform: str, account_id: Optional[str] = None) -> Dict:
    """检查指定平台和账号的凭证有效性"""
    try:
        db = await _get_db_connection()
        if not db:
            utils.logger.error("[DB_UTILS] 无法获取数据库连接")
            return {
                "status": "error",
                "message": "数据库连接失败"
            }
        
        if account_id:
            query = """
            SELECT id, account_id, expires_at, created_at, updated_at
            FROM login_tokens 
            WHERE platform = %s AND account_id = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
            """
            result = await db.get_first(query, platform, account_id)
        else:
            query = """
            SELECT id, account_id, expires_at, created_at, updated_at
            FROM login_tokens 
            WHERE platform = %s AND is_valid = 1
            ORDER BY created_at DESC 
            LIMIT 1
            """
            result = await db.get_first(query, platform)
        
        if not result:
            return {
                "status": "not_found",
                "message": "未找到有效凭证"
            }
        
        now = datetime.now()
        expires_at = result.get('expires_at')
        
        if expires_at and expires_at <= now:
            # 凭证已过期，标记为无效
            await mark_token_invalid(result['id'])
            return {
                "status": "expired",
                "message": "凭证已过期",
                "expires_at": expires_at,
                "account_id": result['account_id']
            }
        elif expires_at and expires_at <= now + timedelta(hours=24):
            # 凭证将在24小时内过期
            return {
                "status": "expiring_soon",
                "message": "凭证即将过期",
                "expires_at": expires_at,
                "account_id": result['account_id']
            }
        else:
            return {
                "status": "valid",
                "message": "凭证有效",
                "expires_at": expires_at,
                "account_id": result['account_id']
            }
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 检查凭证有效性失败 - 平台: {platform}, 账号ID: {account_id}, 错误: {e}")
        return {
            "status": "error",
            "message": f"检查失败: {e}"
        }


async def mark_token_invalid(token_id: int) -> bool:
    """标记凭证为无效"""
    try:
        db = await _get_db_connection()
        if not db:
            utils.logger.error("[DB_UTILS] 无法获取数据库连接")
            return False
        
        query = """
        UPDATE login_tokens 
        SET is_valid = 0, updated_at = NOW()
        WHERE id = %s
        """
        
        await db.execute(query, token_id)
        utils.logger.info(f"[DB_UTILS] 标记凭证为无效 - ID: {token_id}")
        return True
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 标记凭证无效失败 - ID: {token_id}, 错误: {e}")
        return False


async def get_expiring_tokens(hours: int = 24) -> List[Dict]:
    """获取即将过期的凭证列表"""
    try:
        db = await _get_db_connection()
        
        query = """
        SELECT lt.id, lt.platform, lt.account_id, 
               COALESCE(sa.account_name, CONCAT('账号_', lt.account_id)) as account_name,
               lt.expires_at, lt.created_at
        FROM login_tokens lt
        LEFT JOIN social_accounts sa ON lt.account_id = sa.id
        WHERE lt.is_valid = 1
        AND lt.expires_at IS NOT NULL 
        AND lt.expires_at > NOW() 
        AND lt.expires_at <= DATE_ADD(NOW(), INTERVAL %s HOUR)
        ORDER BY lt.expires_at ASC
        """
        
        results = await db.query(query, hours)
        utils.logger.info(f"[DB_UTILS] 获取即将过期的凭证 - 数量: {len(results)}")
        return results
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 获取即将过期凭证失败 - 错误: {e}")
        return []


async def cleanup_expired_tokens() -> int:
    """清理已过期的凭证"""
    try:
        db = await _get_db_connection()
        
        query = """
        UPDATE login_tokens 
        SET is_valid = 0, updated_at = NOW()
        WHERE is_valid = 1 AND expires_at IS NOT NULL AND expires_at <= NOW()
        """
        
        count = await db.execute(query)
        utils.logger.info(f"[DB_UTILS] 清理过期凭证完成 - 数量: {count}")
        return count
    except Exception as e:
        utils.logger.error(f"[DB_UTILS] 清理过期凭证失败 - 错误: {e}")
        return 0


# 保持向后兼容的函数
async def get_account_cookies(platform: str, account_id: Optional[int] = None) -> str:
    """根据账号ID从数据库读取cookies（向后兼容）"""
    return await get_cookies_from_database(platform, str(account_id) if account_id else None) 