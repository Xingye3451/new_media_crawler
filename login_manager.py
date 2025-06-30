# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

"""
登录管理器 - 支持AI赋能平台的登录验证流程
提供登录状态检查、手动验证、Cookie保存等功能
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

import aiofiles
from playwright.async_api import BrowserContext, Page, async_playwright
import httpx

from base.base_crawler import AbstractLogin
from media_platform.xhs.login import XiaoHongShuLogin
from media_platform.douyin.login import DouYinLogin
from tools import utils


class LoginStatus(Enum):
    """登录状态枚举"""
    UNKNOWN = "unknown"
    NOT_LOGGED_IN = "not_logged_in"
    NEED_VERIFICATION = "need_verification"
    LOGGED_IN = "logged_in"
    EXPIRED = "expired"
    ERROR = "error"


class VerificationType(Enum):
    """验证类型枚举"""
    QRCODE = "qrcode"
    SMS = "sms"
    CAPTCHA = "captcha"
    SLIDER = "slider"
    MANUAL = "manual"


@dataclass
class LoginSession:
    """登录会话信息"""
    session_id: str
    platform: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    login_time: Optional[datetime] = None
    expire_time: Optional[datetime] = None
    cookies: Optional[Dict] = None
    local_storage: Optional[Dict] = None
    session_storage: Optional[Dict] = None
    status: LoginStatus = LoginStatus.UNKNOWN
    verification_required: bool = False
    verification_type: Optional[VerificationType] = None
    verification_data: Optional[Dict] = None


class LoginManager:
    """登录管理器"""
    
    def __init__(self, data_dir: str = "./login_data"):
        self.data_dir = data_dir
        self.sessions: Dict[str, LoginSession] = {}
        self.browser_contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(f"{data_dir}/cookies", exist_ok=True)
        os.makedirs(f"{data_dir}/sessions", exist_ok=True)
        
        # 加载已保存的会话
        self._load_sessions()
    
    def _load_sessions(self):
        """加载已保存的会话"""
        sessions_file = f"{self.data_dir}/sessions/sessions.json"
        if os.path.exists(sessions_file):
            try:
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    for session_id, data in sessions_data.items():
                        session = LoginSession(
                            session_id=session_id,
                            platform=data.get("platform"),
                            user_id=data.get("user_id"),
                            username=data.get("username"),
                            login_time=datetime.fromisoformat(data["login_time"]) if data.get("login_time") else None,
                            expire_time=datetime.fromisoformat(data["expire_time"]) if data.get("expire_time") else None,
                            status=LoginStatus(data.get("status", "unknown")),
                            verification_required=data.get("verification_required", False)
                        )
                        self.sessions[session_id] = session
            except Exception as e:
                print(f"加载会话失败: {e}")
    
    def _save_sessions(self):
        """保存会话信息"""
        sessions_file = f"{self.data_dir}/sessions/sessions.json"
        sessions_data = {}
        for session_id, session in self.sessions.items():
            sessions_data[session_id] = {
                "platform": session.platform,
                "user_id": session.user_id,
                "username": session.username,
                "login_time": session.login_time.isoformat() if session.login_time else None,
                "expire_time": session.expire_time.isoformat() if session.expire_time else None,
                "status": session.status.value,
                "verification_required": session.verification_required
            }
        
        with open(sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
    
    async def check_login_status(self, platform: str, session_id: Optional[str] = None) -> LoginSession:
        """检查登录状态"""
        if not session_id:
            # 查找该平台的最新会话
            session_id = self._find_latest_session(platform)
        
        if not session_id:
            # 创建新会话
            session_id = str(uuid.uuid4())
            session = LoginSession(session_id=session_id, platform=platform)
            self.sessions[session_id] = session
        else:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")
        
        # 检查会话是否过期
        if session.expire_time and datetime.now() > session.expire_time:
            session.status = LoginStatus.EXPIRED
            session.verification_required = True
            return session
        
        # 如果有浏览器上下文，检查实际登录状态
        if session_id in self.browser_contexts:
            try:
                await self._check_browser_login_status(session)
            except Exception as e:
                print(f"检查浏览器登录状态失败: {e}")
                session.status = LoginStatus.ERROR
                session.verification_required = True
        
        return session
    
    def _find_latest_session(self, platform: str) -> Optional[str]:
        """查找平台的最新会话"""
        latest_session = None
        latest_time = None
        
        for session_id, session in self.sessions.items():
            if session.platform == platform and session.login_time:
                if not latest_time or session.login_time > latest_time:
                    latest_time = session.login_time
                    latest_session = session_id
        
        return latest_session
    
    async def _check_browser_login_status(self, session: LoginSession):
        """检查浏览器登录状态"""
        if session.session_id not in self.browser_contexts:
            return
        
        context = self.browser_contexts[session.session_id]
        page = self.pages.get(session.session_id)
        
        if not page:
            return
        
        try:
            # 获取cookies
            cookies = await context.cookies()
            session.cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
            
            # 获取localStorage
            local_storage = await page.evaluate("() => window.localStorage")
            session.local_storage = local_storage
            
            # 根据平台检查登录状态
            if session.platform == "xhs":
                await self._check_xhs_login_status(session, page)
            elif session.platform == "dy":
                await self._check_douyin_login_status(session, page)
            # 可以添加其他平台的检查逻辑
            
        except Exception as e:
            print(f"检查登录状态异常: {e}")
            session.status = LoginStatus.ERROR
            session.verification_required = True
    
    async def _check_xhs_login_status(self, session: LoginSession, page: Page):
        """检查小红书登录状态"""
        try:
            # 检查是否有登录按钮
            login_button = await page.query_selector("xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button")
            if login_button:
                session.status = LoginStatus.NOT_LOGGED_IN
                session.verification_required = True
                return
            
            # 检查是否有验证码
            if "请通过验证" in await page.content():
                session.status = LoginStatus.NEED_VERIFICATION
                session.verification_required = True
                session.verification_type = VerificationType.CAPTCHA
                return
            
            # 检查web_session cookie
            web_session = session.cookies.get("web_session")
            if web_session:
                session.status = LoginStatus.LOGGED_IN
                session.verification_required = False
            else:
                session.status = LoginStatus.NOT_LOGGED_IN
                session.verification_required = True
                
        except Exception as e:
            print(f"检查小红书登录状态异常: {e}")
            session.status = LoginStatus.ERROR
            session.verification_required = True
    
    async def _check_douyin_login_status(self, session: LoginSession, page: Page):
        """检查抖音登录状态"""
        try:
            # 检查localStorage中的登录状态
            has_user_login = session.local_storage.get("HasUserLogin", "")
            if has_user_login == "1":
                session.status = LoginStatus.LOGGED_IN
                session.verification_required = False
                return
            
            # 检查是否有登录面板
            login_panel = await page.query_selector("xpath=//div[@id='login-panel-new']")
            if login_panel:
                session.status = LoginStatus.NOT_LOGGED_IN
                session.verification_required = True
                return
            
            # 检查是否有滑动验证码
            if "验证码中间页" in await page.title():
                session.status = LoginStatus.NEED_VERIFICATION
                session.verification_required = True
                session.verification_type = VerificationType.SLIDER
                return
            
            session.status = LoginStatus.NOT_LOGGED_IN
            session.verification_required = True
            
        except Exception as e:
            print(f"检查抖音登录状态异常: {e}")
            session.status = LoginStatus.ERROR
            session.verification_required = True
    
    async def start_login_process(self, platform: str, login_type: str = "qrcode", 
                                session_id: Optional[str] = None) -> Dict[str, Any]:
        """启动登录流程"""
        # 检查现有登录状态
        session = await self.check_login_status(platform, session_id)
        
        if session.status == LoginStatus.LOGGED_IN:
            return {
                "session_id": session.session_id,
                "status": "already_logged_in",
                "message": "已经登录",
                "verification_required": False
            }
        
        # 创建或获取会话
        if not session_id:
            session_id = str(uuid.uuid4())
            session = LoginSession(session_id=session_id, platform=platform)
            self.sessions[session_id] = session
        
        # 启动浏览器
        await self._start_browser(session_id, platform)
        
        # 根据平台和登录类型启动登录流程
        if platform == "xhs":
            return await self._start_xhs_login(session, login_type)
        elif platform == "dy":
            return await self._start_douyin_login(session, login_type)
        else:
            raise ValueError(f"不支持的平台: {platform}")
    
    async def _start_browser(self, session_id: str, platform: str):
        """启动浏览器"""
        if session_id in self.browser_contexts:
            return
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=f"{self.data_dir}/browser_{session_id}",
                headless=False,  # 显示浏览器窗口，方便手动验证
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )
            
            self.browser_contexts[session_id] = browser
            page = await browser.new_page()
            self.pages[session_id] = page
            
            # 根据平台导航到相应网站
            if platform == "xhs":
                await page.goto("https://www.xiaohongshu.com")
            elif platform == "dy":
                await page.goto("https://www.douyin.com")
    
    async def _start_xhs_login(self, session: LoginSession, login_type: str) -> Dict[str, Any]:
        """启动小红书登录流程"""
        page = self.pages[session.session_id]
        
        try:
            if login_type == "qrcode":
                # 查找二维码
                qrcode_img = await page.query_selector("xpath=//img[@class='qrcode-img']")
                if qrcode_img:
                    # 获取二维码图片
                    qrcode_src = await qrcode_img.get_attribute("src")
                    
                    session.verification_required = True
                    session.verification_type = VerificationType.QRCODE
                    session.verification_data = {
                        "qrcode_url": qrcode_src,
                        "login_type": "qrcode"
                    }
                    
                    return {
                        "session_id": session.session_id,
                        "status": "need_verification",
                        "message": "需要扫描二维码登录",
                        "verification_required": True,
                        "verification_type": "qrcode",
                        "verification_data": {
                            "qrcode_url": qrcode_src,
                            "browser_url": page.url
                        }
                    }
                else:
                    # 手动点击登录按钮
                    login_button = await page.query_selector("xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button")
                    if login_button:
                        await login_button.click()
                        await asyncio.sleep(1)
                        
                        # 再次查找二维码
                        qrcode_img = await page.query_selector("xpath=//img[@class='qrcode-img']")
                        if qrcode_img:
                            qrcode_src = await qrcode_img.get_attribute("src")
                            
                            session.verification_required = True
                            session.verification_type = VerificationType.QRCODE
                            session.verification_data = {
                                "qrcode_url": qrcode_src,
                                "login_type": "qrcode"
                            }
                            
                            return {
                                "session_id": session.session_id,
                                "status": "need_verification",
                                "message": "需要扫描二维码登录",
                                "verification_required": True,
                                "verification_type": "qrcode",
                                "verification_data": {
                                    "qrcode_url": qrcode_src,
                                    "browser_url": page.url
                                }
                            }
            
            elif login_type == "phone":
                # 手机号登录流程
                session.verification_required = True
                session.verification_type = VerificationType.SMS
                session.verification_data = {
                    "login_type": "phone",
                    "browser_url": page.url
                }
                
                return {
                    "session_id": session.session_id,
                    "status": "need_verification",
                    "message": "需要手机号验证码登录",
                    "verification_required": True,
                    "verification_type": "sms",
                    "verification_data": {
                        "browser_url": page.url
                    }
                }
            
            return {
                "session_id": session.session_id,
                "status": "error",
                "message": "无法启动登录流程",
                "verification_required": False
            }
            
        except Exception as e:
            return {
                "session_id": session.session_id,
                "status": "error",
                "message": f"启动登录流程失败: {e}",
                "verification_required": False
            }
    
    async def _start_douyin_login(self, session: LoginSession, login_type: str) -> Dict[str, Any]:
        """启动抖音登录流程"""
        page = self.pages[session.session_id]
        
        try:
            # 弹出登录对话框
            dialog_selector = "xpath=//div[@id='login-panel-new']"
            try:
                await page.wait_for_selector(dialog_selector, timeout=5000)
            except:
                login_button = page.locator("xpath=//p[text() = '登录']")
                await login_button.click()
                await asyncio.sleep(0.5)
            
            if login_type == "qrcode":
                # 查找二维码
                qrcode_img = await page.query_selector("xpath=//div[@id='animate_qrcode_container']//img")
                if qrcode_img:
                    qrcode_src = await qrcode_img.get_attribute("src")
                    
                    session.verification_required = True
                    session.verification_type = VerificationType.QRCODE
                    session.verification_data = {
                        "qrcode_url": qrcode_src,
                        "login_type": "qrcode"
                    }
                    
                    return {
                        "session_id": session.session_id,
                        "status": "need_verification",
                        "message": "需要扫描二维码登录",
                        "verification_required": True,
                        "verification_type": "qrcode",
                        "verification_data": {
                            "qrcode_url": qrcode_src,
                            "browser_url": page.url
                        }
                    }
            
            elif login_type == "phone":
                # 切换到手机登录
                mobile_tab = page.locator("xpath=//li[text() = '验证码登录']")
                await mobile_tab.click()
                
                session.verification_required = True
                session.verification_type = VerificationType.SMS
                session.verification_data = {
                    "login_type": "phone",
                    "browser_url": page.url
                }
                
                return {
                    "session_id": session.session_id,
                    "status": "need_verification",
                    "message": "需要手机号验证码登录",
                    "verification_required": True,
                    "verification_type": "sms",
                    "verification_data": {
                        "browser_url": page.url
                    }
                }
            
            return {
                "session_id": session.session_id,
                "status": "error",
                "message": "无法启动登录流程",
                "verification_required": False
            }
            
        except Exception as e:
            return {
                "session_id": session.session_id,
                "status": "error",
                "message": f"启动登录流程失败: {e}",
                "verification_required": False
            }
    
    async def wait_for_verification(self, session_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待验证完成"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检查登录状态
            await self._check_browser_login_status(session)
            
            if session.status == LoginStatus.LOGGED_IN:
                # 保存登录信息
                await self._save_login_session(session)
                
                return {
                    "session_id": session_id,
                    "status": "success",
                    "message": "登录成功",
                    "verification_required": False,
                    "cookies": session.cookies,
                    "local_storage": session.local_storage
                }
            
            elif session.status == LoginStatus.NEED_VERIFICATION:
                # 继续等待验证
                await asyncio.sleep(2)
                continue
            
            else:
                # 登录失败或出错
                return {
                    "session_id": session_id,
                    "status": "failed",
                    "message": f"登录失败: {session.status.value}",
                    "verification_required": session.verification_required
                }
        
        # 超时
        return {
            "session_id": session_id,
            "status": "timeout",
            "message": "验证超时",
            "verification_required": True
        }
    
    async def _save_login_session(self, session: LoginSession):
        """保存登录会话"""
        session.login_time = datetime.now()
        session.expire_time = session.login_time + timedelta(days=7)  # 7天过期
        session.status = LoginStatus.LOGGED_IN
        session.verification_required = False
        
        # 保存cookies到文件
        if session.cookies:
            cookies_file = f"{self.data_dir}/cookies/{session.platform}_{session.session_id}.json"
            async with aiofiles.open(cookies_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session.cookies, ensure_ascii=False, indent=2))
        
        # 保存localStorage到文件
        if session.local_storage:
            storage_file = f"{self.data_dir}/sessions/{session.platform}_{session.session_id}_storage.json"
            async with aiofiles.open(storage_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session.local_storage, ensure_ascii=False, indent=2))
        
        # 保存会话信息
        self._save_sessions()
    
    async def get_session_cookies(self, session_id: str) -> Optional[Dict]:
        """获取会话cookies"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # 如果内存中没有cookies，从文件加载
        if not session.cookies:
            cookies_file = f"{self.data_dir}/cookies/{session.platform}_{session_id}.json"
            if os.path.exists(cookies_file):
                async with aiofiles.open(cookies_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    session.cookies = json.loads(content)
        
        return session.cookies
    
    async def close_session(self, session_id: str):
        """关闭会话"""
        if session_id in self.browser_contexts:
            await self.browser_contexts[session_id].close()
            del self.browser_contexts[session_id]
        
        if session_id in self.pages:
            del self.pages[session_id]
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
    
    async def close_all_sessions(self):
        """关闭所有会话"""
        for session_id in list(self.browser_contexts.keys()):
            await self.close_session(session_id)


# 全局登录管理器实例
login_manager = LoginManager() 