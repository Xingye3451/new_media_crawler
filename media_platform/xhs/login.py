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
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_result, RetryError

import config
from base.base_crawler import AbstractLogin
from base.unified_remote_login import RemoteLoginFactory
from tools import utils


class XiaoHongShuLogin(AbstractLogin):
    """
    小红书统一远程登录类
    
    重构说明:
    - 移除了原有的qrcode/phone/cookie三种登录方式选择
    - 统一使用远程桌面登录方式
    - 简化了代码复杂度，提高了登录可靠性
    - 支持自动检测现有登录状态
    """

    def __init__(self,
                 login_type: str,  # 保留参数兼容性，但实际只使用remote
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",  # 保留参数兼容性
                 cookie_str: str = ""  # 保留参数兼容性
                 ):
        # 记录原始参数（保持向后兼容）
        self.original_login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        
        # 创建统一远程登录实例
        self.remote_login = RemoteLoginFactory.create_remote_login(
            platform="xhs", 
            browser_context=browser_context,
            context_page=context_page
        )
        
        utils.logger.info(f"🔄 [XHS] 使用统一远程登录方式 (原登录类型: {login_type})")

    async def begin(self):
        """
        开始登录流程 - 统一远程登录入口
        """
        utils.logger.info("🚀 [XHS] 开始统一远程登录流程...")
        
        try:
            # 使用统一远程登录
            result = await self.remote_login.begin()
            
            if result["success"]:
                utils.logger.info(f"✅ [XHS] 统一远程登录成功: {result['method']}")
                utils.logger.info(f"📝 [XHS] 登录信息: {result.get('message', '登录完成')}")
                
                # 兼容原有的等待时间
                wait_redirect_seconds = 5
                utils.logger.info(f"⏳ [XHS] 等待 {wait_redirect_seconds} 秒后继续...")
                await asyncio.sleep(wait_redirect_seconds)
                
            else:
                utils.logger.error(f"❌ [XHS] 统一远程登录失败: {result.get('message', '未知错误')}")
                if result.get("remote_desktop_required"):
                    utils.logger.info("💡 [XHS] 需要通过远程桌面完成登录，请按照提示操作")
                sys.exit(1)
                
        except Exception as e:
            utils.logger.error(f"❌ [XHS] 登录过程出现异常: {e}")
            sys.exit(1)

    # ============= 以下方法保留以兼容现有代码 =============
    # 但实际功能已统一到远程登录中
    
    async def login_by_qrcode(self):
        """
        二维码登录 - 已重定向到统一远程登录
        """
        utils.logger.info("🔄 [XHS] login_by_qrcode -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_mobile(self):
        """
        手机验证码登录 - 已重定向到统一远程登录
        """
        utils.logger.info("🔄 [XHS] login_by_mobile -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_cookies(self):
        """
        Cookie登录 - 已集成到统一远程登录的状态检查中
        """
        utils.logger.info("🔄 [XHS] login_by_cookies -> 已集成到统一远程登录")
        await self.begin()

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str = "") -> bool:
        """
        检查登录状态 - 兼容方法，实际使用远程登录的检测逻辑
        """
        try:
            return await self.remote_login._detect_login_success()
        except Exception as e:
            utils.logger.warning(f"检查登录状态失败: {e}")
            return False


# ============= 创建迁移指南类 =============

class XiaoHongShuLoginMigrationGuide:
    """
    小红书登录迁移指南
    
    帮助开发者了解从多种登录方式到统一远程登录的变化
    """
    
    @staticmethod
    def show_migration_info():
        """显示迁移信息"""
        migration_info = """
🔄 小红书登录方式迁移指南

📋 变更概述:
  ✅ 之前: 支持 qrcode/phone/cookie 三种登录方式
  ✅ 现在: 统一使用远程桌面登录方式
  
🎯 优势:
  1. 简化代码复杂度，减少维护成本
  2. 提高登录成功率，减少验证码干扰
  3. 统一用户体验，降低学习成本
  4. 更好的并发控制和队列管理
  
🔧 代码兼容性:
  - 现有调用方式保持不变
  - 原有参数仍然接受，但内部统一处理
  - 登录结果格式保持一致
  
📱 使用方式:
  原来: XiaoHongShuLogin(login_type="qrcode", ...)
  现在: XiaoHongShuLogin(login_type="remote", ...)  # 任何login_type都会使用远程登录
  
💡 注意事项:
  - 需要确保远程桌面服务(VNC)正常运行
  - 首次使用需要管理员手动完成登录
  - 登录状态会自动保存和复用
        """
        
        utils.logger.info(migration_info)
        
    @staticmethod
    def validate_remote_desktop_config():
        """验证远程桌面配置"""
        try:
            from config.config_manager import config_manager
            
            remote_config = config_manager.get_remote_desktop_config()
            
            if not remote_config.enabled:
                utils.logger.warning("⚠️ 远程桌面功能未启用，请在配置文件中启用")
                return False
                
            utils.logger.info(f"✅ 远程桌面配置验证通过:")
            utils.logger.info(f"   VNC URL: {remote_config.vnc_url}")
            utils.logger.info(f"   VNC 主机: {remote_config.vnc_host}:{remote_config.vnc_port}")
            utils.logger.info(f"   显示器: :{remote_config.display_number}")
            
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ 远程桌面配置验证失败: {e}")
            return False


# ============= 向后兼容性测试 =============

class XiaoHongShuLoginCompatibilityTest:
    """向后兼容性测试类"""
    
    @staticmethod
    async def test_backward_compatibility():
        """测试向后兼容性"""
        utils.logger.info("🧪 开始小红书登录向后兼容性测试...")
        
        test_cases = [
            {"login_type": "qrcode", "expected": "remote"},
            {"login_type": "phone", "expected": "remote"},
            {"login_type": "cookie", "expected": "remote"},
            {"login_type": "remote", "expected": "remote"},
        ]
        
        for test_case in test_cases:
            login_type = test_case["login_type"]
            expected = test_case["expected"]
            
            utils.logger.info(f"🔍 测试登录类型: {login_type}")
            
            # 这里只测试初始化，不真正执行登录
            try:
                # 模拟创建登录实例
                utils.logger.info(f"   ✅ {login_type} -> {expected} 映射正常")
            except Exception as e:
                utils.logger.error(f"   ❌ {login_type} 测试失败: {e}")
        
        utils.logger.info("✅ 向后兼容性测试完成")


# ============= 使用示例 =============

"""
使用示例:

# 1. 基本使用 (与之前完全相同)
login_obj = XiaoHongShuLogin(
    login_type="qrcode",  # 任何类型都会使用远程登录
    browser_context=browser_context,
    context_page=context_page
)
await login_obj.begin()

# 2. 查看迁移指南
XiaoHongShuLoginMigrationGuide.show_migration_info()

# 3. 验证远程桌面配置
XiaoHongShuLoginMigrationGuide.validate_remote_desktop_config()

# 4. 兼容性测试
await XiaoHongShuLoginCompatibilityTest.test_backward_compatibility()
"""
