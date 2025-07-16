# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import asyncio
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_result, RetryError

import config
from base.base_crawler import AbstractLogin
from base.unified_remote_login import RemoteLoginFactory
from tools import utils


class BilibiliLogin(AbstractLogin):
    """
    B站统一远程登录类
    
    重构说明:
    - 移除了qrcode/phone/cookie三种登录方式选择
    - 统一使用远程桌面登录方式
    - 简化代码逻辑，提高登录成功率
    - 支持自动检测和复用登录状态
    """

    def __init__(self,
                 login_type: str,  # 保留参数兼容性
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        # 记录原始参数（保持向后兼容）
        self.original_login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        
        # 创建统一远程登录实例
        self.remote_login = RemoteLoginFactory.create_remote_login(
            platform="bili", 
            browser_context=browser_context,
            context_page=context_page
        )
        
        utils.logger.info(f"🔄 [BILI] 使用统一远程登录方式 (原登录类型: {login_type})")

    async def begin(self):
        """
        开始登录流程 - 统一远程登录入口
        """
        utils.logger.info("🚀 [BILI] 开始统一远程登录流程...")
        
        try:
            # 使用统一远程登录
            result = await self.remote_login.begin()
            
            if result["success"]:
                utils.logger.info(f"✅ [BILI] 统一远程登录成功: {result['method']}")
                utils.logger.info(f"📝 [BILI] 登录信息: {result.get('message', '登录完成')}")
                
                # 兼容原有的等待时间
                wait_redirect_seconds = 5
                utils.logger.info(f"⏳ [BILI] 等待 {wait_redirect_seconds} 秒后继续...")
                await asyncio.sleep(wait_redirect_seconds)
                
            else:
                utils.logger.error(f"❌ [BILI] 统一远程登录失败: {result.get('message', '未知错误')}")
                if result.get("remote_desktop_required"):
                    utils.logger.info("💡 [BILI] 需要通过远程桌面完成登录，请按照提示操作")
                sys.exit(1)
                
        except Exception as e:
            utils.logger.error(f"❌ [BILI] 登录过程出现异常: {e}")
            sys.exit(1)

    # ============= 以下方法保留以兼容现有代码 =============
    
    async def login_by_qrcode(self):
        """二维码登录 - 已重定向到统一远程登录"""
        utils.logger.info("🔄 [BILI] login_by_qrcode -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_mobile(self):
        """手机验证码登录 - 已重定向到统一远程登录"""
        utils.logger.info("🔄 [BILI] login_by_mobile -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_cookies(self):
        """Cookie登录 - 已集成到统一远程登录的状态检查中"""
        utils.logger.info("🔄 [BILI] login_by_cookies -> 已集成到统一远程登录")
        await self.begin()

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """检查登录状态 - 兼容方法，使用远程登录的检测逻辑"""
        try:
            return await self.remote_login._detect_login_success()
        except Exception as e:
            utils.logger.warning(f"检查登录状态失败: {e}")
            return False


# ============= B站登录迁移指南 =============

class BilibiliLoginMigrationGuide:
    """
    B站登录迁移指南
    """
    
    @staticmethod
    def show_migration_info():
        """显示B站登录迁移信息"""
        migration_info = """
🔄 B站登录方式迁移指南

📋 变更概述:
  ✅ 之前: 支持 qrcode/phone/cookie 三种登录方式
  ✅ 现在: 统一使用远程桌面登录方式
  
🎯 B站特有优势:
  1. B站登录相对简单，远程登录更稳定
  2. 避免复杂的验证码处理
  3. 支持多种B站登录方式（密码、短信、扫码等）
  4. 登录状态持久化，支持长期使用

🔧 代码兼容性:
  - 现有调用方式保持完全不变
  - 所有登录类型都会重定向到远程登录
  - 登录成功率显著提升

💡 B站登录特点:
  - 通常需要在passport.bilibili.com进行认证
  - 登录成功后会自动跳转到主站
  - SESSDATA和bili_jct是关键认证cookies
  - 支持各种B站功能访问
        """
        
        utils.logger.info(migration_info)


# ============= 使用示例 =============

"""
B站登录重构使用示例:

# 1. 基本使用 (完全兼容原有代码)
login_obj = BilibiliLogin(
    login_type="qrcode",  # 任何类型都会使用远程登录
    browser_context=browser_context,
    context_page=context_page
)
await login_obj.begin()

# 2. 查看迁移指南
BilibiliLoginMigrationGuide.show_migration_info()

# 3. B站登录通常比较稳定，适合作为统一远程登录的示例平台
"""
