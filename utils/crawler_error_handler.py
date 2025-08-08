"""
爬虫错误处理和重试机制
包含权限丢失检测、验证码处理、重试逻辑和账号切换功能
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from tools import utils


class ErrorType(Enum):
    """错误类型枚举"""
    PERMISSION_DENIED = "permission_denied"      # 权限丢失
    CAPTCHA_REQUIRED = "captcha_required"        # 验证码要求
    RATE_LIMITED = "rate_limited"                # 频率限制
    NETWORK_ERROR = "network_error"              # 网络错误
    LOGIN_REQUIRED = "login_required"            # 需要登录
    ACCOUNT_BLOCKED = "account_blocked"          # 账号被封
    UNKNOWN_ERROR = "unknown_error"              # 未知错误


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3                    # 最大重试次数
    base_delay: float = 2.0                 # 基础延迟时间（秒）
    max_delay: float = 30.0                 # 最大延迟时间（秒）
    exponential_base: float = 2.0            # 指数退避基数
    jitter: bool = True                      # 是否添加随机抖动
    account_switch_enabled: bool = True      # 是否启用账号切换
    max_account_switches: int = 3            # 最大账号切换次数


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: ErrorType
    message: str
    platform: str
    account_id: Optional[str] = None
    timestamp: datetime = None
    retry_count: int = 0
    account_switch_count: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CrawlerErrorHandler:
    """爬虫错误处理器"""
    
    def __init__(self, platform: str, task_id: str = None, retry_config: RetryConfig = None):
        self.platform = platform
        self.task_id = task_id
        self.retry_config = retry_config or RetryConfig()
        self.error_history: List[ErrorInfo] = []
        self.current_account_id: Optional[str] = None
        self.available_accounts: List[Dict] = []
        self.account_index = 0
        
    def log_error(self, error_type: ErrorType, message: str, account_id: Optional[str] = None):
        """记录错误信息"""
        error_info = ErrorInfo(
            error_type=error_type,
            message=message,
            platform=self.platform,
            account_id=account_id or self.current_account_id,
            retry_count=len([e for e in self.error_history if e.error_type == error_type]),
            account_switch_count=self.account_index
        )
        self.error_history.append(error_info)
        
        utils.logger.error(f"[ERROR_HANDLER_{self.platform}] {error_type.value}: {message}")
        if self.task_id:
            utils.logger.error(f"[ERROR_HANDLER_{self.platform}] Task: {self.task_id}, Account: {account_id}")
    
    def should_retry(self, error_type: ErrorType) -> bool:
        """判断是否应该重试"""
        retry_count = len([e for e in self.error_history if e.error_type == error_type])
        
        # 某些错误类型不应该重试
        if error_type in [ErrorType.ACCOUNT_BLOCKED, ErrorType.LOGIN_REQUIRED]:
            return False
        
        return retry_count < self.retry_config.max_retries
    
    def should_switch_account(self, error_type: ErrorType) -> bool:
        """判断是否应该切换账号"""
        if not self.retry_config.account_switch_enabled:
            return False
        
        if error_type in [ErrorType.ACCOUNT_BLOCKED, ErrorType.PERMISSION_DENIED, ErrorType.LOGIN_REQUIRED]:
            return True
        
        # 验证码错误也考虑切换账号
        if error_type == ErrorType.CAPTCHA_REQUIRED:
            return True
        
        return False
    
    def can_switch_account(self) -> bool:
        """检查是否还能切换账号"""
        return (self.available_accounts and 
                self.account_index < len(self.available_accounts) - 1 and
                self.account_index < self.retry_config.max_account_switches)
    
    async def switch_account(self) -> Optional[Dict]:
        """切换账号"""
        if not self.can_switch_account():
            return None
        
        self.account_index += 1
        new_account = self.available_accounts[self.account_index]
        self.current_account_id = new_account.get('id')
        
        utils.logger.info(f"[ERROR_HANDLER_{self.platform}] 切换到账号: {new_account.get('account_name', '未知')} (ID: {self.current_account_id})")
        return new_account
    
    def get_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟时间"""
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** retry_count)
        delay = min(delay, self.retry_config.max_delay)
        
        if self.retry_config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)
        
        return delay
    
    async def wait_before_retry(self, retry_count: int):
        """重试前等待"""
        delay = self.get_retry_delay(retry_count)
        utils.logger.info(f"[ERROR_HANDLER_{self.platform}] 等待 {delay:.2f} 秒后重试 (第 {retry_count + 1} 次)")
        await asyncio.sleep(delay)
    
    def detect_error_type(self, exception: Exception, response: Optional[httpx.Response] = None) -> ErrorType:
        """检测错误类型"""
        error_message = str(exception).lower()
        
        # 检测权限丢失
        if any(keyword in error_message for keyword in ['permission', 'unauthorized', 'forbidden', '403']):
            return ErrorType.PERMISSION_DENIED
        
        # 检测验证码
        if any(keyword in error_message for keyword in ['captcha', 'verify', '验证码', '471', '461']):
            return ErrorType.CAPTCHA_REQUIRED
        
        # 检测频率限制
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorType.RATE_LIMITED
        
        # 检测需要登录
        if any(keyword in error_message for keyword in ['login required', 'not logged in', '未登录']):
            return ErrorType.LOGIN_REQUIRED
        
        # 检测账号被封
        if any(keyword in error_message for keyword in ['blocked', 'banned', 'account suspended']):
            return ErrorType.ACCOUNT_BLOCKED
        
        # 检测网络错误
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network']):
            return ErrorType.NETWORK_ERROR
        
        # 根据HTTP状态码判断
        if response:
            if response.status_code == 403:
                return ErrorType.PERMISSION_DENIED
            elif response.status_code == 429:
                return ErrorType.RATE_LIMITED
            elif response.status_code in [471, 461]:
                return ErrorType.CAPTCHA_REQUIRED
        
        return ErrorType.UNKNOWN_ERROR
    
    async def handle_error(self, exception: Exception, response: Optional[httpx.Response] = None) -> Dict[str, Any]:
        """处理错误并决定下一步行动"""
        error_type = self.detect_error_type(exception, response)
        error_message = str(exception)
        
        self.log_error(error_type, error_message)
        
        # 检查是否需要切换账号
        if self.should_switch_account(error_type) and self.can_switch_account():
            new_account = await self.switch_account()
            if new_account:
                return {
                    "action": "switch_account",
                    "account": new_account,
                    "should_retry": True,
                    "error_type": error_type
                }
        
        # 检查是否应该重试
        if self.should_retry(error_type):
            retry_count = len([e for e in self.error_history if e.error_type == error_type])
            await self.wait_before_retry(retry_count)
            return {
                "action": "retry",
                "retry_count": retry_count + 1,
                "should_retry": True,
                "error_type": error_type
            }
        
        # 终止操作
        return {
            "action": "terminate",
            "should_retry": False,
            "error_type": error_type,
            "reason": f"达到最大重试次数或遇到不可恢复错误: {error_type.value}"
        }
    
    async def load_available_accounts(self) -> List[Dict]:
        """加载可用账号列表"""
        try:
            from api.crawler_core import get_db_connection
            
            async_db_obj = await get_db_connection()
            if not async_db_obj:
                return []
            
            # 获取该平台的所有可用账号
            query = """
                SELECT sa.id, sa.account_name, sa.username, sa.platform, sa.login_method,
                       lt.is_valid, lt.expires_at, lt.last_used_at, lt.created_at as token_created_at
                FROM social_accounts sa
                LEFT JOIN login_tokens lt ON sa.id = lt.account_id AND sa.platform = lt.platform
                WHERE sa.platform = %s AND lt.is_valid = 1 AND lt.expires_at > NOW()
                ORDER BY lt.created_at DESC
            """
            
            accounts = await async_db_obj.query(query, self.platform)
            self.available_accounts = accounts
            utils.logger.info(f"[ERROR_HANDLER_{self.platform}] 加载了 {len(accounts)} 个可用账号")
            return accounts
            
        except Exception as e:
            utils.logger.error(f"[ERROR_HANDLER_{self.platform}] 加载账号失败: {e}")
            return []
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        error_counts = {}
        for error_type in ErrorType:
            error_counts[error_type.value] = len([e for e in self.error_history if e.error_type == error_type])
        
        return {
            "total_errors": len(self.error_history),
            "error_counts": error_counts,
            "account_switches": self.account_index,
            "current_account_id": self.current_account_id,
            "available_accounts_count": len(self.available_accounts)
        }


class RetryableCrawlerOperation:
    """可重试的爬虫操作包装器"""
    
    def __init__(self, error_handler: CrawlerErrorHandler):
        self.error_handler = error_handler
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """执行可重试的操作"""
        max_attempts = self.error_handler.retry_config.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                utils.logger.info(f"[RETRY_OP_{self.error_handler.platform}] 执行操作 (第 {attempt + 1} 次尝试)")
                return await operation(*args, **kwargs)
                
            except Exception as e:
                utils.logger.error(f"[RETRY_OP_{self.error_handler.platform}] 操作失败: {e}")
                
                # 处理错误
                result = await self.error_handler.handle_error(e)
                
                if not result["should_retry"]:
                    utils.logger.error(f"[RETRY_OP_{self.error_handler.platform}] 终止操作: {result.get('reason', '未知原因')}")
                    raise e
                
                if result["action"] == "switch_account":
                    utils.logger.info(f"[RETRY_OP_{self.error_handler.platform}] 已切换账号，继续重试")
                elif result["action"] == "retry":
                    utils.logger.info(f"[RETRY_OP_{self.error_handler.platform}] 准备重试 (第 {result['retry_count']} 次)")
        
        # 所有重试都失败了
        raise Exception(f"操作失败，已重试 {max_attempts} 次")


# 便捷函数
async def create_error_handler(platform: str, task_id: str = None, 
                             retry_config: RetryConfig = None) -> CrawlerErrorHandler:
    """创建错误处理器"""
    handler = CrawlerErrorHandler(platform, task_id, retry_config)
    await handler.load_available_accounts()
    return handler


async def execute_with_retry(platform: str, operation: Callable, task_id: str = None,
                            retry_config: RetryConfig = None, *args, **kwargs) -> Any:
    """执行带重试的操作"""
    error_handler = await create_error_handler(platform, task_id, retry_config)
    retry_op = RetryableCrawlerOperation(error_handler)
    return await retry_op.execute(operation, *args, **kwargs)
