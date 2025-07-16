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


class DouYinLogin(AbstractLogin):
    """
    抖音统一远程登录类
    
    重构说明:
    - 移除了复杂的滑块验证逻辑 (check_page_display_slider, move_slider)
    - 移除了qrcode/phone/cookie三种登录方式选择
    - 统一使用远程桌面登录方式，由管理员手动处理验证码和滑块
    - 大幅简化代码复杂度，提高登录可靠性
    """

    def __init__(self,
                 login_type: str,  # 保留参数兼容性
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: Optional[str] = ""
                 ):
        # 记录原始参数（保持向后兼容）
        self.original_login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.scan_qrcode_time = 60
        self.cookie_str = cookie_str
        
        # 创建统一远程登录实例
        self.remote_login = RemoteLoginFactory.create_remote_login(
            platform="dy", 
            browser_context=browser_context,
            context_page=context_page
        )
        
        utils.logger.info(f"🔄 [DOUYIN] 使用统一远程登录方式 (原登录类型: {login_type})")
        utils.logger.info("💡 [DOUYIN] 抖音滑块验证将由管理员在远程桌面中手动处理")

    async def begin(self):
        """
        开始登录流程 - 统一远程登录入口
        
        之前抖音登录的复杂逻辑:
        - 弹出登录对话框 (popup_login_dialog)
        - 根据类型选择登录方式
        - 复杂的滑块验证处理 (check_page_display_slider)
        - 现在全部交给远程桌面中的管理员手动处理
        """
        utils.logger.info("🚀 [DOUYIN] 开始统一远程登录流程...")
        utils.logger.info("📝 [DOUYIN] 原来的滑块验证现在由管理员在远程桌面中处理")
        
        try:
            # 使用统一远程登录
            result = await self.remote_login.begin()
            
            if result["success"]:
                utils.logger.info(f"✅ [DOUYIN] 统一远程登录成功: {result['method']}")
                utils.logger.info(f"📝 [DOUYIN] 登录信息: {result.get('message', '登录完成')}")
                
                # 兼容原有的等待时间
                wait_redirect_seconds = 5
                utils.logger.info(f"⏳ [DOUYIN] 等待 {wait_redirect_seconds} 秒后继续...")
                await asyncio.sleep(wait_redirect_seconds)
                
            else:
                utils.logger.error(f"❌ [DOUYIN] 统一远程登录失败: {result.get('message', '未知错误')}")
                if result.get("remote_desktop_required"):
                    utils.logger.info("💡 [DOUYIN] 需要通过远程桌面完成登录（包括滑块验证）")
                sys.exit(1)
                
        except Exception as e:
            utils.logger.error(f"❌ [DOUYIN] 登录过程出现异常: {e}")
            sys.exit(1)

    # ============= 以下方法保留以兼容现有代码 =============
    # 但复杂的滑块验证逻辑已移除，统一到远程登录中
    
    async def login_by_qrcode(self):
        """二维码登录 - 已重定向到统一远程登录"""
        utils.logger.info("🔄 [DOUYIN] login_by_qrcode -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_mobile(self):
        """手机验证码登录 - 已重定向到统一远程登录"""
        utils.logger.info("🔄 [DOUYIN] login_by_mobile -> 重定向到统一远程登录")
        await self.begin()

    async def login_by_cookies(self):
        """Cookie登录 - 已集成到统一远程登录的状态检查中"""
        utils.logger.info("🔄 [DOUYIN] login_by_cookies -> 已集成到统一远程登录")
        await self.begin()

    async def popup_login_dialog(self):
        """弹出登录对话框 - 已集成到远程登录中"""
        utils.logger.info("🔄 [DOUYIN] popup_login_dialog -> 由远程登录处理")

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self):
        """检查登录状态 - 兼容方法，使用远程登录的检测逻辑"""
        try:
            return await self.remote_login._detect_login_success()
        except Exception as e:
            utils.logger.warning(f"检查登录状态失败: {e}")
            return False

    # ============= 已移除的复杂验证方法 =============
    # 这些方法之前处理抖音复杂的滑块验证，现在统一在远程桌面中手动处理
    
    async def check_page_display_slider(self, move_step: int = 10, slider_level: str = "easy"):
        """
        滑块验证处理 - 已移除复杂逻辑，由远程桌面管理员处理
        
        原来这个方法包含:
        - 检测滑块验证码出现
        - 自动移动滑块
        - 处理"操作过慢"等错误
        - 现在全部由管理员在远程桌面中手动处理
        """
        utils.logger.info("🔄 [DOUYIN] 滑块验证由远程桌面管理员手动处理")

    async def move_slider(self, back_selector: str, gap_selector: str, move_step: int = 10, slider_level="easy"):
        """
        移动滑块 - 已移除复杂逻辑，由远程桌面管理员处理
        
        原来这个方法包含:
        - 获取滑块背景图片和缺口图片
        - 识别滑块位置
        - 生成移动轨迹
        - 模拟鼠标拖拽
        - 现在全部由管理员在远程桌面中手动处理
        """
        utils.logger.info("🔄 [DOUYIN] 滑块移动由远程桌面管理员手动处理")


# ============= 抖音登录迁移指南 =============

class DouYinLoginMigrationGuide:
    """
    抖音登录迁移指南
    
    特别关注抖音复杂验证机制的简化
    """
    
    @staticmethod
    def show_migration_info():
        """显示抖音登录迁移信息"""
        migration_info = """
🔄 抖音登录方式迁移指南

📋 重大变更:
  ❌ 移除: 复杂的滑块自动化验证逻辑
  ❌ 移除: qrcode/phone/cookie 三种登录方式选择  
  ✅ 新增: 统一远程桌面登录方式
  ✅ 简化: 由管理员手动处理所有验证

🎯 抖音特有优势:
  1. 彻底解决滑块验证准确率问题
  2. 避免"操作过慢"等自动化检测
  3. 管理员可以灵活处理各种验证码
  4. 减少维护复杂滑块算法的成本

⚠️ 原有复杂功能:
  - check_page_display_slider() : 自动滑块检测和处理
  - move_slider(): 滑块轨迹生成和移动
  - 复杂的验证失败重试逻辑
  👆 以上功能现在由管理员在远程桌面中手动操作

💡 使用建议:
  - 抖音验证较为复杂，建议管理员预先登录
  - 登录成功后状态会自动保存，员工可直接使用
  - 如遇到新的验证方式，管理员可以灵活应对
        """
        
        utils.logger.info(migration_info)
    
    @staticmethod
    def show_slider_handling_guide():
        """显示滑块处理指南"""
        slider_guide = """
🎯 抖音滑块验证处理指南 (远程桌面版)

🖱️ 管理员操作流程:
  1. 打开远程桌面登录页面
  2. 输入账号密码或扫描二维码
  3. 遇到滑块验证时:
     - 仔细观察缺口位置
     - 缓慢拖动滑块到正确位置
     - 避免过快操作被识别为机器人
  4. 遇到点击验证码时:
     - 按照提示点击正确的图像
     - 多次尝试直到验证成功
  5. 登录成功后会自动保存状态

⚡ 效率建议:
  - 建议每天固定时间统一处理登录
  - 可以同时处理多个平台的登录
  - 登录状态通常可以保持较长时间
        """
        
        utils.logger.info(slider_guide)


# ============= 使用示例 =============

"""
抖音登录重构使用示例:

# 1. 基本使用 (API完全相同)
login_obj = DouYinLogin(
    login_type="qrcode",  # 任何类型都会使用远程登录
    browser_context=browser_context,
    context_page=context_page
)
await login_obj.begin()

# 2. 查看迁移指南
DouYinLoginMigrationGuide.show_migration_info()

# 3. 查看滑块处理指南  
DouYinLoginMigrationGuide.show_slider_handling_guide()

# 注意: 不再需要手动处理滑块验证！
# 原来的复杂代码:
# await login_obj.check_page_display_slider(move_step=3, slider_level="hard")
# 
# 现在: 完全由管理员在远程桌面中处理
"""
