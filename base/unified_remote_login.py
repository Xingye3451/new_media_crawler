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
统一远程登录抽象基类
将所有平台的登录方式统一为远程桌面登录，简化登录流程
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from playwright.async_api import BrowserContext, Page
from datetime import datetime
import asyncio
import uuid
from tools import utils


class UnifiedRemoteLogin(ABC):
    """统一远程登录抽象基类"""
    
    def __init__(self, platform: str, browser_context: BrowserContext, context_page: Page):
        """
        初始化统一远程登录
        
        Args:
            platform: 平台标识 (xhs, dy, ks, bili, wb, tieba, zhihu)
            browser_context: 浏览器上下文
            context_page: 页面对象
        """
        self.platform = platform
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_url = self._get_platform_login_url()
        self.session_id = str(uuid.uuid4())
        self._login_success_indicators = self._get_login_success_indicators()
    
    @abstractmethod
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        """
        获取登录成功的标识信息
        
        Returns:
            包含cookies和URL模式的字典
        """
        pass
    
    def _get_platform_login_url(self) -> str:
        """获取平台登录页面URL"""
        url_map = {
            "xhs": "https://www.xiaohongshu.com/login",
            "dy": "https://www.douyin.com/",
            "ks": "https://www.kuaishou.com/",
            "bili": "https://account.bilibili.com/account/home",
            "wb": "https://weibo.com/login.php",
            "tieba": "https://tieba.baidu.com/",
            "zhihu": "https://www.zhihu.com/signin"
        }
        return url_map.get(self.platform, "https://www.google.com")
    
    async def begin(self) -> Dict[str, Any]:
        """
        开始统一远程登录流程
        
        Returns:
            登录结果信息
        """
        utils.logger.info(f"🚀 [{self.platform.upper()}] 开始统一远程登录流程...")
        
        try:
            # 步骤1: 检查现有登录状态
            current_status = await self._check_existing_login_status()
            if current_status["is_logged_in"]:
                utils.logger.info(f"✅ [{self.platform.upper()}] 检测到已有有效登录状态")
                return {
                    "success": True,
                    "method": "existing_login",
                    "message": "使用现有登录状态",
                    "session_id": self.session_id,
                    "cookies": current_status["cookies"]
                }
            
            # 步骤2: 启动远程桌面登录
            remote_result = await self._start_remote_desktop_login()
            return remote_result
            
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}] 统一远程登录失败: {e}")
            return {
                "success": False,
                "method": "remote_desktop",
                "message": f"登录失败: {str(e)}",
                "session_id": self.session_id,
                "error": str(e)
            }
    
    async def _check_existing_login_status(self) -> Dict[str, Any]:
        """检查现有登录状态"""
        try:
            # 从数据库读取cookies
            from utils.db_utils import get_cookies_from_database
            
            cookie_str = await get_cookies_from_database(self.platform, None)
            if not cookie_str:
                return {"is_logged_in": False, "cookies": []}
            
            # 设置cookies到浏览器
            await self._set_cookies_from_string(cookie_str)
            
            # 验证cookies有效性
            is_valid = await self._validate_cookies_with_platform()
            
            if is_valid:
                current_cookies = await self.browser_context.cookies()
                return {"is_logged_in": True, "cookies": current_cookies}
            else:
                return {"is_logged_in": False, "cookies": []}
                
        except Exception as e:
            utils.logger.warning(f"检查现有登录状态失败: {e}")
            return {"is_logged_in": False, "cookies": []}
    
    async def _set_cookies_from_string(self, cookie_str: str):
        """从字符串设置cookies到浏览器"""
        try:
            from tools import utils as crawler_utils
            cookie_dict = crawler_utils.convert_str_cookie_to_dict(cookie_str)
            domain = self._get_platform_domain()
            
            for key, value in cookie_dict.items():
                await self.browser_context.add_cookies([{
                    'name': key,
                    'value': value,
                    'domain': domain,
                    'path': "/"
                }])
        except Exception as e:
            utils.logger.error(f"设置cookies失败: {e}")
    
    def _get_platform_domain(self) -> str:
        """获取平台域名"""
        domain_map = {
            "xhs": ".xiaohongshu.com",
            "dy": ".douyin.com", 
            "ks": ".kuaishou.com",
            "bili": ".bilibili.com",
            "wb": ".weibo.com",
            "tieba": ".baidu.com",
            "zhihu": ".zhihu.com"
        }
        return domain_map.get(self.platform, ".example.com")
    
    async def _validate_cookies_with_platform(self) -> bool:
        """通过访问平台验证cookies有效性"""
        try:
            # 访问平台主页或用户中心
            validation_url = self._get_validation_url()
            await self.context_page.goto(validation_url, timeout=15000)
            await asyncio.sleep(2)
            
            # 检查登录状态
            return await self._detect_login_success()
            
        except Exception as e:
            utils.logger.warning(f"验证cookies时出错: {e}")
            return False
    
    def _get_validation_url(self) -> str:
        """获取验证URL"""
        validation_map = {
            "xhs": "https://www.xiaohongshu.com/explore",
            "dy": "https://www.douyin.com/",
            "ks": "https://www.kuaishou.com/",
            "bili": "https://www.bilibili.com/",
            "wb": "https://weibo.com/",
            "tieba": "https://tieba.baidu.com/",
            "zhihu": "https://www.zhihu.com/"
        }
        return validation_map.get(self.platform, self.login_url)
    
    async def _start_remote_desktop_login(self) -> Dict[str, Any]:
        """启动远程桌面登录流程"""
        utils.logger.info(f"🖥️ [{self.platform.upper()}] 启动远程桌面登录...")
        
        # 由于复杂的远程桌面登录系统需要额外的服务支持，
        # 这里直接使用简化版的远程登录流程
        try:
            utils.logger.error(f"启动远程桌面登录失败: ")
            return await self._fallback_simple_remote_login()
            
        except Exception as e:
            utils.logger.error(f"启动远程桌面登录失败: {e}")
            return await self._fallback_simple_remote_login()
    
    async def _fallback_simple_remote_login(self) -> Dict[str, Any]:
        """简化版远程登录方案"""
        utils.logger.info(f"🔄 [{self.platform.upper()}] 使用简化版远程登录...")
        
        try:
            # 直接打开登录页面
            await self.context_page.goto(self.login_url, timeout=30000)
            await asyncio.sleep(3)
            
            utils.logger.info(f"📖 [{self.platform.upper()}] 登录页面已打开: {self.login_url}")
            utils.logger.info(f"💡 请在浏览器中手动完成登录操作")
            
            # 等待用户手动登录
            login_success = await self._wait_for_manual_login()
            
            if login_success:
                # 保存登录状态
                cookies = await self.browser_context.cookies()
                await self._save_login_cookies(cookies)
                
                return {
                    "success": True,
                    "method": "manual_remote_login",
                    "message": "手动登录完成",
                    "session_id": self.session_id,
                    "cookies": cookies
                }
            else:
                return {
                    "success": False,
                    "method": "manual_remote_login", 
                    "message": "手动登录超时或失败",
                    "session_id": self.session_id
                }
                
        except Exception as e:
            utils.logger.error(f"简化版远程登录失败: {e}")
            return {
                "success": False,
                "method": "manual_remote_login",
                "message": f"登录失败: {str(e)}",
                "session_id": self.session_id,
                "error": str(e)
            }
    
    async def _wait_for_manual_login(self, timeout: int = 1800) -> bool:
        """等待用户手动完成登录"""
        utils.logger.info(f"⏳ [{self.platform.upper()}] 等待手动登录完成，超时时间: {timeout}秒")
        
        initial_cookies = await self.browser_context.cookies()
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                # 检查登录状态
                if await self._detect_login_success():
                    utils.logger.info(f"✅ [{self.platform.upper()}] 检测到登录成功！")
                    return True
                
                await asyncio.sleep(3)  # 每3秒检查一次
                
            except Exception as e:
                utils.logger.warning(f"检查登录状态时出错: {e}")
                await asyncio.sleep(5)
        
        utils.logger.warning(f"⏰ [{self.platform.upper()}] 等待登录超时")
        return False
    
    async def _detect_login_success(self) -> bool:
        """检测登录是否成功"""
        try:
            current_cookies = await self.browser_context.cookies()
            current_url = self.context_page.url
            
            # 方法1: 检查关键cookies
            indicators = self._login_success_indicators
            required_cookies = indicators.get("cookies", [])
            
            cookie_names = [cookie['name'] for cookie in current_cookies]
            
            for required_cookie in required_cookies:
                if required_cookie in cookie_names:
                    # 验证cookie值不为空
                    for cookie in current_cookies:
                        if cookie['name'] == required_cookie and len(cookie['value']) > 10:
                            utils.logger.info(f"🍪 检测到关键cookie: {required_cookie}")
                            return True
            
            # 方法2: 检查URL模式
            success_patterns = indicators.get("url_patterns", [])
            for pattern in success_patterns:
                if pattern in current_url:
                    utils.logger.info(f"🔗 检测到成功URL模式: {pattern}")
                    return True
            
            # 方法3: 检查页面内容
            page_content = await self.context_page.content()
            if self._check_page_content_for_login(page_content):
                return True
            
            return False
            
        except Exception as e:
            utils.logger.warning(f"检测登录状态时出错: {e}")
            return False
    
    @abstractmethod
    def _check_page_content_for_login(self, content: str) -> bool:
        """检查页面内容判断是否登录成功"""
        pass
    
    async def _save_login_cookies(self, cookies: List[Dict]):
        """保存登录cookies到数据库"""
        try:
            from api.login_management import save_login_cookies
            
            utils.logger.info(f"💾 [{self.platform.upper()}] 保存登录cookies...")
            result = await save_login_cookies(
                self.session_id, 
                cookies, 
                self.platform
            )
            
            if result:
                utils.logger.info(f"✅ [{self.platform.upper()}] Cookies保存成功")
            else:
                utils.logger.error(f"❌ [{self.platform.upper()}] Cookies保存失败")
                
        except Exception as e:
            utils.logger.error(f"保存cookies时出错: {e}")


class RemoteLoginFactory:
    """远程登录工厂类"""
    
    @staticmethod
    def create_remote_login(platform: str, browser_context: BrowserContext, 
                          context_page: Page) -> UnifiedRemoteLogin:
        """
        创建对应平台的远程登录实例
        
        Args:
            platform: 平台标识
            browser_context: 浏览器上下文
            context_page: 页面对象
            
        Returns:
            对应平台的远程登录实例
        """
        platform_classes = {
            "xhs": XHSRemoteLogin,
            "dy": DouyinRemoteLogin, 
            "ks": KuaishouRemoteLogin,
            "bili": BilibiliRemoteLogin,
            "wb": WeiboRemoteLogin,
            "tieba": TiebaRemoteLogin,
            "zhihu": ZhihuRemoteLogin
        }
        
        login_class = platform_classes.get(platform)
        if not login_class:
            raise ValueError(f"不支持的平台: {platform}")
        
        return login_class(platform, browser_context, context_page)


# 各平台具体实现类
class XHSRemoteLogin(UnifiedRemoteLogin):
    """小红书远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["web_session", "xsecappid"],
            "url_patterns": ["xiaohongshu.com/explore", "xiaohongshu.com/user"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        # 检查页面是否包含登录成功的标识
        success_indicators = ["个人主页", "我的", "发布笔记"]
        return any(indicator in content for indicator in success_indicators)


class DouyinRemoteLogin(UnifiedRemoteLogin):
    """抖音远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["LOGIN_STATUS", "sessionid"],
            "url_patterns": ["douyin.com/recommend", "douyin.com/user"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["个人中心", "我的", "关注"]
        return any(indicator in content for indicator in success_indicators)


class KuaishouRemoteLogin(UnifiedRemoteLogin):
    """快手远程登录（严格模式）"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["passToken", "userId", "kuaishou.server.webday7_st", "kuaishou.server.webday7_ph"],
            "url_patterns": ["kuaishou.com/profile", "kuaishou.com/u/"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["个人主页", "我的作品", "用户中心"]
        return any(indicator in content for indicator in success_indicators)
    
    async def _detect_login_success(self) -> bool:
        """快手专用的严格登录检测"""
        try:
            current_cookies = await self.browser_context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in current_cookies}
            
            # 检查核心认证cookies（必须全部存在）
            core_cookies = ['passToken', 'userId']
            core_found = 0
            
            for cookie_name in core_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    if len(cookie_value) > 10:
                        core_found += 1
                        utils.logger.info(f"✅ [快手统一] 核心cookie {cookie_name}: {cookie_value[:20]}...")
            
            # 检查会话cookies（至少一个）
            session_cookies = ['kuaishou.server.webday7_st', 'kuaishou.server.webday7_ph']
            session_found = 0
            
            for cookie_name in session_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    if len(cookie_value) > 20:
                        session_found += 1
                        utils.logger.info(f"✅ [快手统一] 会话cookie {cookie_name}: {cookie_value[:30]}...")
            
            # 严格验证：核心cookies全部存在 + 至少一个会话cookie
            if core_found == len(core_cookies) and session_found >= 1:
                utils.logger.info(f"🎉 [快手统一] 登录检测成功！核心认证({core_found}/{len(core_cookies)}) + 会话({session_found})")
                return True
            else:
                utils.logger.debug(f"🎬 [快手统一] 登录检测中... 核心认证({core_found}/{len(core_cookies)}), 会话({session_found})")
                return False
                
        except Exception as e:
            utils.logger.warning(f"🎬 [快手统一] 检测登录状态时出错: {e}")
            return False


class BilibiliRemoteLogin(UnifiedRemoteLogin):
    """B站远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["SESSDATA", "bili_jct"],
            "url_patterns": ["bilibili.com/", "space.bilibili.com"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["个人中心", "我的信息", "动态"]
        return any(indicator in content for indicator in success_indicators)


class WeiboRemoteLogin(UnifiedRemoteLogin):
    """微博远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["SUB", "login_sid_t"],
            "url_patterns": ["weibo.com/u/", "weibo.com/home"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["个人主页", "我的微博"]
        return any(indicator in content for indicator in success_indicators)


class TiebaRemoteLogin(UnifiedRemoteLogin):
    """贴吧远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["BDUSS", "STOKEN"],
            "url_patterns": ["tieba.baidu.com/home", "tieba.baidu.com/i/"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["我的贴吧", "个人中心"]
        return any(indicator in content for indicator in success_indicators)


class ZhihuRemoteLogin(UnifiedRemoteLogin):
    """知乎远程登录"""
    
    def _get_login_success_indicators(self) -> Dict[str, List[str]]:
        return {
            "cookies": ["z_c0", "q_c1"],
            "url_patterns": ["zhihu.com/", "zhihu.com/people"]
        }
    
    def _check_page_content_for_login(self, content: str) -> bool:
        success_indicators = ["个人主页", "我的主页", "消息"]
        return any(indicator in content for indicator in success_indicators) 