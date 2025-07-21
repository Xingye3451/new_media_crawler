from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from var import media_crawler_db_var
from tools import utils
import base64
import io
from playwright.async_api import async_playwright
import aiohttp
import random
from config.config_manager import config_manager
from api.remote_desktop_lock import remote_desktop_lock

# ===== 新增：增强反检测配置 =====
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    from config.browser_config_2024 import get_platform_config, BrowserConfig2024
    ENHANCED_CONFIG_AVAILABLE = True
    utils.logger.info("✅ [Enhanced] 增强反检测配置加载成功")
except ImportError as e:
    ENHANCED_CONFIG_AVAILABLE = False
    utils.logger.warning(f"⚠️ [Enhanced] 增强反检测配置加载失败: {e}, 将使用默认配置")

# 增强配置获取函数
def get_enhanced_browser_config(platform: str) -> Dict[str, Any]:
    """获取增强的浏览器配置"""
    if ENHANCED_CONFIG_AVAILABLE:
        try:
            config = get_platform_config(platform)
            browser_args = BrowserConfig2024.get_browser_args(platform, remote_desktop=True)
            
            return {
                "user_agent": config['user_agent'],
                "viewport": config['viewport'],
                "locale": config['locale'],
                "timezone_id": config['timezone_id'],
                "geolocation": config['geolocation'],
                "permissions": config['permissions'],
                "extra_http_headers": config['extra_http_headers'],
                "browser_args": browser_args
            }
        except Exception as e:
            utils.logger.error(f"❌ [Enhanced] 获取增强配置失败: {e}")
    
    # 回退到默认配置（适配VNC远程桌面）
    return {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1260, "height": 680},  # 适配1280x720 VNC分辨率，留出窗口边框空间
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "geolocation": {"longitude": 116.3975, "latitude": 39.9085},
        "permissions": ["geolocation", "notifications"],
        "extra_http_headers": {
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
        },
        "browser_args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=VizDisplayCompositor",
            "--disable-automation",
            # 添加适合远程桌面的参数
            "--force-device-scale-factor=0.8",  # 强制缩放到80%
            "--window-size=1260,680",           # 设置窗口大小
            "--start-maximized"                 # 最大化窗口以便操作
        ]
    }

async def inject_enhanced_stealth_script(browser_context, platform: str):
    """注入增强反检测脚本"""
    try:
        # 尝试加载增强反检测脚本
        stealth_script_path = os.path.join(project_root, "libs", "enhanced_stealth.js")
        
        if os.path.exists(stealth_script_path):
            utils.logger.info(f"📄 [Enhanced] 注入增强反检测脚本")
            await browser_context.add_init_script(path=stealth_script_path)
        else:
            # 回退到基础反检测脚本
            utils.logger.info(f"📄 [Enhanced] 使用基础反检测脚本")
            await browser_context.add_init_script("""
                console.log('🛡️ [基础反检测] 脚本加载');
                
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // 删除webdriver相关变量
                delete window.webdriver;
                delete window.__webdriver_script_fn;
                delete window.__webdriver_evaluate;
                delete window.__selenium_evaluate;
                delete window.__webdriver_unwrapped;
                
                // 完善chrome对象
                if (!window.chrome) {
                    window.chrome = {};
                }
                
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {
                        onConnect: {
                            addListener: function() {},
                            removeListener: function() {},
                            hasListener: function() { return false; }
                        },
                        connect: function() {
                            throw new Error('Extension context invalidated.');
                        },
                        sendMessage: function() {
                            throw new Error('Extension context invalidated.');
                        }
                    };
                }
                
                console.log('✅ [基础反检测] 脚本加载完成');
            """)
            
        # 添加平台特定脚本
        await inject_platform_specific_script(browser_context, platform)
        
    except Exception as e:
        utils.logger.error(f"💥 [Enhanced] 注入反检测脚本失败: {e}")

async def inject_platform_specific_script(browser_context, platform: str):
    """注入平台特定脚本"""
    
    platform_scripts = {
        "ks": """
            // 快手特定优化
            console.log('🎬 [快手] 平台特定脚本加载');
            window.ks = window.ks || {};
            window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
        """,
        "dy": """
            // 抖音特定优化  
            console.log('🎵 [抖音] 平台特定脚本加载');
            window.byted_acrawler = window.byted_acrawler || {};
            window.SLARDAR_WEB_ID = '3715';
        """,
        "bili": """
            // B站特定优化
            console.log('📺 [B站] 平台特定脚本加载');
            window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
            if (!localStorage.getItem('_uuid')) {
                const uuid = 'B' + Date.now().toString(36) + Math.random().toString(36).substr(2);
                localStorage.setItem('_uuid', uuid);
            }
        """,
        "xhs": """
            // 小红书特定优化
            console.log('📍 [小红书] 平台特定脚本加载');
            document.cookie = 'webId=xxx123; domain=.xiaohongshu.com; path=/';
        """
    }
    
    script = platform_scripts.get(platform)
    if script:
        try:
            await browser_context.add_init_script(script)
            utils.logger.info(f"✅ [Enhanced] {platform} 平台脚本注入成功")
        except Exception as e:
            utils.logger.error(f"❌ [Enhanced] {platform} 平台脚本注入失败: {e}")

# ===== 原有代码继续 =====

login_router = APIRouter(tags=["登录管理"])

class LoginRequest(BaseModel):
    account_id: int = Field(..., description="账号ID")
    login_method: str = Field(default="qrcode", description="登录方式")
    phone: Optional[str] = Field(None, description="手机号（手机登录时使用）")
    email: Optional[str] = Field(None, description="邮箱（邮箱登录时使用）")

class LoginResponse(BaseModel):
    session_id: str
    status: str
    message: str
    qr_code_url: Optional[str] = None
    expires_at: Optional[str] = None

class LoginStatusResponse(BaseModel):
    session_id: str
    status: str
    message: str
    account_info: Optional[Dict[str, Any]] = None
    progress: int = 0
    qr_code_data: Optional[str] = None
    expires_at: Optional[str] = None
    captcha_screenshot: Optional[str] = None
    captcha_area: Optional[Dict[str, Any]] = None
    element_analysis: Optional[List[Dict[str, Any]]] = None
    analysis_summary: Optional[str] = None
    saved_html_file: Optional[str] = None
    analysis_instruction: Optional[str] = None
    html_save_error: Optional[str] = None
    backup_html_file: Optional[str] = None
    # 远程桌面相关字段
    remote_desktop_url: Optional[str] = None
    remote_desktop_available: bool = False
    remote_desktop_message: Optional[str] = None
    # 队列相关字段
    queue_position: Optional[int] = None
    estimated_wait_seconds: Optional[int] = None
    has_desktop_lock: Optional[bool] = None
    # 自动关闭状态
    auto_closed: Optional[bool] = None

class LoginCheckRequest(BaseModel):
    platform: str = Field(..., description="平台名称", example="xhs")
    account_id: Optional[int] = Field(None, description="指定账号ID（可选）", example=8)

class LoginCheckResponse(BaseModel):
    platform: str
    status: str  # logged_in, not_logged_in, expired, unknown
    message: str
    account_info: Optional[Dict[str, Any]] = None
    last_login_time: Optional[str] = None
    expires_at: Optional[str] = None

class TokenSaveRequest(BaseModel):
    session_id: str = Field(..., description="登录会话ID")
    token_data: str = Field(..., description="令牌数据(JSON格式)")
    user_agent: Optional[str] = Field(None, description="用户代理")
    proxy_info: Optional[str] = Field(None, description="代理信息")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

class TaskLogRequest(BaseModel):
    task_id: str = Field(..., description="任务ID")
    platform: str = Field(..., description="平台名称")
    account_id: Optional[int] = Field(None, description="账号ID")
    log_level: str = Field(default="INFO", description="日志级别")
    message: str = Field(..., description="日志消息")
    step: Optional[str] = Field(None, description="当前步骤")
    progress: int = Field(default=0, description="进度百分比")
    extra_data: Optional[str] = Field(None, description="额外数据")

# 存储登录会话
login_sessions: Dict[str, Dict[str, Any]] = {}


async def verify_actual_login_status(platform: str, token_data_str: str) -> Dict[str, Any]:
    """实际验证登录状态"""
    try:
        utils.logger.info(f"开始验证平台 {platform} 的实际登录状态")
        
        # 解析token数据
        token_data = json.loads(token_data_str)
        cookies_str = token_data.get('cookies', '')
        
        if not cookies_str:
            return {"is_logged_in": False, "message": "没有有效的cookies数据"}
        
        # 解析cookies
        cookies = []
        for cookie_pair in cookies_str.split('; '):
            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": get_platform_domain(platform),
                    "path": "/"
                })
        
        if not cookies:
            return {"is_logged_in": False, "message": "cookies格式无效"}
        
        # 根据平台验证登录状态
        coming_soon_platforms = {"wb": "微博", "tieba": "贴吧", "zhihu": "知乎"}
        if platform in coming_soon_platforms:
            platform_name = coming_soon_platforms[platform]
            return {"is_logged_in": False, "message": f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。"}
        
        if platform == "xhs":
            return await verify_xhs_login_status(cookies)
        elif platform == "dy":
            return await verify_douyin_login_status(cookies)
        elif platform == "ks":
            return await verify_kuaishou_login_status(cookies)
        elif platform == "bili":
            return await verify_bilibili_login_status(cookies)
        else:
            return {"is_logged_in": False, "message": f"不支持的平台: {platform}"}
            
    except json.JSONDecodeError:
        return {"is_logged_in": False, "message": "token数据格式错误"}
    except Exception as e:
        utils.logger.error(f"验证登录状态时出错: {e}")
        return {"is_logged_in": False, "message": f"验证过程出错: {str(e)}"}


def get_platform_domain(platform: str) -> str:
    """获取平台的域名"""
    domain_map = {
        "xhs": ".xiaohongshu.com",
        "dy": ".douyin.com",
        "ks": ".kuaishou.com", 
        "bili": ".bilibili.com",
        "wb": ".weibo.com",
        "tieba": ".baidu.com",
        "zhihu": ".zhihu.com"
    }
    return domain_map.get(platform, ".example.com")


async def verify_xhs_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证小红书登录状态（严格模式：Cookie检查 + 页面验证）"""
    try:
        utils.logger.info("🟠 [小红书] 开始验证登录状态（严格模式）")
        
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # 打印所有cookies用于调试
        utils.logger.info(f"🔍 [小红书调试] 所有cookies ({len(cookie_dict)}个):")
        for name, value in cookie_dict.items():
            utils.logger.info(f"   - {name}: {value[:30]}..." if len(value) > 30 else f"   - {name}: {value}")
        
        # 第一阶段：Cookie预检查（必要条件）
        utils.logger.info("📋 [小红书] 第一阶段：Cookie预检查...")
        
        # 检查关键认证cookies
        required_cookies = {
            'a1': {'min_length': 40, 'desc': '主要认证token'},
            'web_session': {'min_length': 30, 'desc': '会话token'}
        }
        
        missing_cookies = []
        valid_cookies = []
        
        for cookie_name, requirements in required_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) >= requirements['min_length']:
                    valid_cookies.append(cookie_name)
                    utils.logger.info(f"✓ [小红书] Cookie {cookie_name}: {cookie_value[:20]}... (长度: {len(cookie_value)})")
                else:
                    missing_cookies.append(f"{cookie_name}(长度不足: {len(cookie_value)})")
                    utils.logger.warning(f"⚠️ [小红书] Cookie {cookie_name} 长度不足: {len(cookie_value)}")
            else:
                missing_cookies.append(f"{cookie_name}(不存在)")
                utils.logger.warning(f"⚠️ [小红书] 缺少Cookie: {cookie_name}")
        
        # 如果关键cookie不足，直接返回失败
        if len(valid_cookies) < 2:
            return {
                "is_logged_in": False,
                "message": f"Cookie预检查失败 - 缺少关键认证cookies: {', '.join(missing_cookies)}"
            }
        
        utils.logger.info(f"✅ [小红书] Cookie预检查通过 ({len(valid_cookies)}/2)")
        
        # 第二阶段：页面验证（充分条件）
        utils.logger.info("🌐 [小红书] 第二阶段：页面验证...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 添加cookies
            await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            try:
                # 访问小红书主页，检查真实登录状态
                utils.logger.info("🔗 [小红书] 访问首页验证登录状态...")
                await page.goto("https://www.xiaohongshu.com/explore", timeout=30000)
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
                
                # 等待页面完全加载
                await asyncio.sleep(3)
                
                # 检查1: 是否存在登录按钮（强烈的未登录信号）
                login_selectors = [
                    "button:has-text('登录')",
                    "a:has-text('登录')", 
                    "[data-testid='login-button']",
                    ".login-btn",
                    "xpath=//button[contains(text(), '登录')]",
                    "xpath=//a[contains(text(), '登录')]"
                ]
                
                for selector in login_selectors:
                    try:
                        login_element = await page.query_selector(selector)
                        if login_element and await login_element.is_visible():
                            utils.logger.warning(f"❌ [小红书] 发现登录按钮: {selector}")
                            return {
                                "is_logged_in": False,
                                "message": "页面显示需要登录 - 检测到登录按钮"
                            }
                    except:
                        continue
                
                # 检查2: 查找用户相关元素（已登录的积极信号）
                user_selectors = [
                    "[data-testid='user-avatar']",
                    ".user-avatar",
                    ".avatar",
                    ".user-info", 
                    "[data-testid='user-menu']",
                    "xpath=//img[contains(@class, 'avatar')]",
                    "xpath=//div[contains(@class, 'user')]"
                ]
                
                user_element_found = False
                for selector in user_selectors:
                    try:
                        user_element = await page.query_selector(selector)
                        if user_element and await user_element.is_visible():
                            utils.logger.info(f"✓ [小红书] 发现用户元素: {selector}")
                            user_element_found = True
                            break
                    except:
                        continue
                
                # 检查3: 页面内容分析
                page_content = await page.content()
                page_text = await page.inner_text('body')
                
                # 未登录的负面信号
                negative_signals = [
                    "请先登录",
                    "立即登录",
                    "登录后查看",
                    "sign in",
                    "log in"
                ]
                
                negative_found = any(signal in page_text.lower() for signal in negative_signals)
                
                # 已登录的积极信号
                positive_signals = [
                    "首页",
                    "推荐",
                    "关注",
                    "发现",
                    "我的收藏"
                ]
                
                positive_found = any(signal in page_text for signal in positive_signals)
                
                # 检查4: 检查当前cookies是否发生变化（session刷新）
                current_cookies = await context.cookies()
                current_cookie_dict = {cookie['name']: cookie['value'] for cookie in current_cookies}
                
                # 验证关键cookie是否仍然有效
                original_web_session = cookie_dict.get('web_session', '')
                current_web_session = current_cookie_dict.get('web_session', '')
                
                session_valid = (current_web_session and 
                               len(current_web_session) > 20 and 
                               current_web_session == original_web_session)
                
                utils.logger.info(f"🔍 [小红书] 页面验证结果:")
                utils.logger.info(f"   用户元素: {user_element_found}")
                utils.logger.info(f"   负面信号: {negative_found}")
                utils.logger.info(f"   积极信号: {positive_found}")
                utils.logger.info(f"   Session有效: {session_valid}")
                
                # 综合判断
                if negative_found:
                    return {
                        "is_logged_in": False,
                        "message": "页面验证失败 - 检测到需要登录的提示"
                    }
                elif user_element_found and positive_found and session_valid:
                    return {
                        "is_logged_in": True,
                        "message": "登录状态有效 - 页面验证通过（用户元素 + 积极信号 + Session有效）"
                    }
                elif positive_found and session_valid:
                    return {
                        "is_logged_in": True,
                        "message": "登录状态有效 - 页面验证通过（积极信号 + Session有效）"
                    }
                else:
                    return {
                        "is_logged_in": False,
                        "message": f"页面验证失败 - 登录状态不明确（用户元素:{user_element_found}, 积极信号:{positive_found}, Session:{session_valid}）"
                    }
                
            finally:
                await browser.close()
                
    except Exception as e:
        utils.logger.error(f"❌ [小红书] 验证登录状态失败: {e}")
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_douyin_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证抖音登录状态"""
    try:
        utils.logger.info("开始验证抖音登录状态")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            try:
                await page.goto("https://www.douyin.com", timeout=30000)
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                # 检查localStorage中的登录状态
                has_user_login = await page.evaluate("() => window.localStorage.getItem('HasUserLogin')")
                if has_user_login == "1":
                    return {"is_logged_in": True, "message": "localStorage显示已登录"}
                
                # 检查是否有登录面板
                login_panel = await page.query_selector("xpath=//div[@id='login-panel-new']")
                if login_panel:
                    return {"is_logged_in": False, "message": "显示登录面板"}
                
                # 检查LOGIN_STATUS cookie
                current_cookies = await context.cookies()
                login_status = None
                for cookie in current_cookies:
                    if cookie['name'] == 'LOGIN_STATUS':
                        login_status = cookie['value']
                        break
                
                if login_status == "1":
                    return {"is_logged_in": True, "message": "LOGIN_STATUS显示已登录"}
                
                return {"is_logged_in": False, "message": "未检测到登录状态"}
                
            finally:
                await browser.close()
                
    except Exception as e:
        utils.logger.error(f"验证抖音登录状态失败: {e}")
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_kuaishou_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证快手登录状态（严格模式）"""
    try:
        utils.logger.info("🎬 [快手] 开始验证登录状态（严格模式）")
        
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # 检查核心认证cookies（必须全部存在且有效）
        core_auth_cookies = {
            'passToken': '认证token',
            'userId': '用户ID'
        }
        
        missing_core = []
        found_core = []
        
        for cookie_name, description in core_auth_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) > 10:  # 确保值不为空且有实际内容
                    found_core.append(f"{cookie_name}({description})")
                    utils.logger.info(f"✓ [快手] 核心cookie {cookie_name}: {cookie_value[:20]}...")
                else:
                    missing_core.append(f"{cookie_name}({description}) - 值太短")
                    utils.logger.warning(f"⚠️ [快手] 核心cookie {cookie_name} 值无效: {cookie_value}")
            else:
                missing_core.append(f"{cookie_name}({description}) - 不存在")
                utils.logger.warning(f"⚠️ [快手] 缺少核心cookie: {cookie_name}")
        
        # 检查会话相关cookies（至少需要一个）
        session_cookies = {
            'kuaishou.server.webday7_st': '服务器状态token',
            'kuaishou.server.webday7_ph': '会话hash'
        }
        
        found_session = []
        for cookie_name, description in session_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) > 20:  # 会话token通常比较长
                    found_session.append(f"{cookie_name}({description})")
                    utils.logger.info(f"✓ [快手] 会话cookie {cookie_name}: {cookie_value[:30]}...")
        
        # 严格验证：核心cookies必须全部存在，会话cookies至少一个
        if len(found_core) == len(core_auth_cookies) and len(found_session) >= 1:
            utils.logger.info(f"✅ [快手] 登录状态验证通过！")
            utils.logger.info(f"   核心cookies({len(found_core)}): {', '.join(found_core)}")
            utils.logger.info(f"   会话cookies({len(found_session)}): {', '.join(found_session)}")
            return {
                "is_logged_in": True, 
                "message": f"登录状态有效 - 核心cookies: {len(found_core)}/{len(core_auth_cookies)}, 会话cookies: {len(found_session)}"
            }
        else:
            # 详细报告缺失的cookies
            missing_report = []
            if missing_core:
                missing_report.append(f"缺少核心cookies: {', '.join(missing_core)}")
            if len(found_session) == 0:
                missing_report.append(f"缺少会话cookies: {', '.join(session_cookies.keys())}")
            
            utils.logger.warning(f"❌ [快手] 登录状态验证失败:")
            for report in missing_report:
                utils.logger.warning(f"   {report}")
                
            return {
                "is_logged_in": False, 
                "message": f"登录验证失败 - {'; '.join(missing_report)}"
            }
            
    except Exception as e:
        utils.logger.error(f"❌ [快手] 验证登录状态失败: {e}")
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_bilibili_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证B站登录状态（严格模式）"""
    try:
        utils.logger.info("📺 [B站] 开始验证登录状态（严格模式）")
        
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # 打印所有cookies用于调试
        utils.logger.info(f"🔍 [B站调试] 所有cookies ({len(cookie_dict)}个):")
        for name, value in cookie_dict.items():
            utils.logger.info(f"   - {name}: {value[:30]}..." if len(value) > 30 else f"   - {name}: {value}")
        
        # 检查核心认证cookies（必须全部存在且有效）
        core_auth_cookies = {
            'SESSDATA': '主要会话token',
            'DedeUserID': '用户ID',
            'bili_jct': 'CSRF保护token'
        }
        
        missing_core = []
        found_core = []
        
        for cookie_name, description in core_auth_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                # SESSDATA通常很长，DedeUserID是数字，bili_jct是32位hex
                min_length = 32 if cookie_name == 'bili_jct' else 8 if cookie_name == 'DedeUserID' else 50
                
                if len(cookie_value) >= min_length:
                    found_core.append(f"{cookie_name}({description})")
                    utils.logger.info(f"✓ [B站] 核心cookie {cookie_name}: {cookie_value[:20]}...")
                else:
                    missing_core.append(f"{cookie_name}({description}) - 值太短({len(cookie_value)})")
                    utils.logger.warning(f"⚠️ [B站] 核心cookie {cookie_name} 值无效: {cookie_value}")
            else:
                missing_core.append(f"{cookie_name}({description}) - 不存在")
                utils.logger.warning(f"⚠️ [B站] 缺少核心cookie: {cookie_name}")
        
        # 检查辅助认证信息（可选，但有助于确认）
        auxiliary_cookies = {
            'bili_ticket': 'JWT票据',
            'bili_ticket_expires': '票据过期时间',
            'DedeUserID__ckMd5': '用户ID校验'
        }
        
        found_auxiliary = []
        for cookie_name, description in auxiliary_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) > 5:  # 基本长度检查
                    found_auxiliary.append(f"{cookie_name}({description})")
                    utils.logger.info(f"✓ [B站] 辅助cookie {cookie_name}: {cookie_value[:20]}...")
        
        # 严格验证：核心cookies必须全部存在
        if len(found_core) == len(core_auth_cookies):
            utils.logger.info(f"✅ [B站] 登录状态验证通过！")
            utils.logger.info(f"   核心cookies({len(found_core)}): {', '.join(found_core)}")
            if found_auxiliary:
                utils.logger.info(f"   辅助cookies({len(found_auxiliary)}): {', '.join(found_auxiliary)}")
            
            return {
                "is_logged_in": True,
                "message": f"登录状态有效 - 核心cookies: {len(found_core)}/{len(core_auth_cookies)}, 辅助cookies: {len(found_auxiliary)}"
            }
        else:
            # 详细报告缺失的cookies
            utils.logger.warning(f"❌ [B站] 登录状态验证失败:")
            for missing in missing_core:
                utils.logger.warning(f"   {missing}")
            
            return {
                "is_logged_in": False,
                "message": f"登录验证失败 - 缺少核心cookies: {', '.join(missing_core)}"
            }
            
    except Exception as e:
        utils.logger.error(f"❌ [B站] 验证登录状态失败: {e}")
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_weibo_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证微博登录状态"""
    try:
        for cookie in cookies:
            if cookie['name'] in ['SUB', 'SUBP'] and cookie['value']:
                return {"is_logged_in": True, "message": "微博登录cookie存在"}
        return {"is_logged_in": False, "message": "缺少微博登录cookie"}
    except Exception as e:
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_tieba_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证贴吧登录状态"""
    try:
        for cookie in cookies:
            if cookie['name'] in ['BDUSS', 'STOKEN'] and cookie['value']:
                return {"is_logged_in": True, "message": "贴吧登录cookie存在"}
        return {"is_logged_in": False, "message": "缺少贴吧登录cookie"}
    except Exception as e:
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def verify_zhihu_login_status(cookies: List[Dict]) -> Dict[str, Any]:
    """验证知乎登录状态"""
    try:
        for cookie in cookies:
            if cookie['name'] in ['z_c0', 'd_c0'] and cookie['value']:
                return {"is_logged_in": True, "message": "知乎登录cookie存在"}
        return {"is_logged_in": False, "message": "缺少知乎登录cookie"}
    except Exception as e:
        return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


async def get_db():
    """获取数据库连接"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        # 如果上下文变量没有设置，尝试初始化数据库连接
        from db import init_mediacrawler_db
        await init_mediacrawler_db()
        return media_crawler_db_var.get()

@login_router.post("/login/start", response_model=LoginResponse)
async def start_login(request: LoginRequest, background_tasks: BackgroundTasks, http_request: Request):
    """开始登录流程"""
    # 记录详细的请求信息
    request_url = str(http_request.url)
    request_method = http_request.method
    request_headers = dict(http_request.headers)
    request_body = request.dict()
    
    utils.logger.info(f"=== 登录请求开始 ===")
    utils.logger.info(f"请求URL: {request_url}")
    utils.logger.info(f"请求方法: {request_method}")
    utils.logger.info(f"请求头: {request_headers}")
    utils.logger.info(f"请求体: {request_body}")
    
    db = await get_db()
    
    try:
        # 检查账号是否存在
        account_query = "SELECT id, platform, account_name, login_method FROM social_accounts WHERE id = %s"
        utils.logger.info(f"查询账号SQL: {account_query}, 参数: {request.account_id}")
        
        account = await db.get_first(account_query, request.account_id)
        
        if not account:
            error_msg = f"账号不存在，账号ID: {request.account_id}"
            utils.logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        account_id, platform, account_name, login_method = account['id'], account['platform'], account['account_name'], account['login_method']
        
        utils.logger.info(f"找到账号: ID={account_id}, 平台={platform}, 名称={account_name}, 登录方式={login_method}")
        
        # 创建登录会话
        session_id = str(uuid.uuid4())
        session_data = {
            "account_id": account_id,
            "platform": platform,
            "account_name": account_name,
            "login_method": request.login_method or login_method,
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=10),
            "progress": 0
        }
        
        login_sessions[session_id] = session_data
        
        utils.logger.info(f"创建登录会话: {session_id}, 会话数据: {session_data}")
        
        # 根据登录方式处理
        if request.login_method == "qrcode":
            # 二维码登录
            utils.logger.info(f"开始二维码登录流程，平台: {platform}")
            
            # 设置初始状态
            session_data["status"] = "initializing"
            session_data["message"] = "正在初始化登录流程..."
            session_data["progress"] = 10
            
            # 启动后台任务处理真实的登录流程
            background_tasks.add_task(handle_qrcode_login, session_id, platform)
            
            response_data = LoginResponse(
                session_id=session_id,
                status="initializing",
                message="正在初始化登录流程，请稍候...",
                qr_code_url=f"/api/v1/login/qrcode/{session_id}",
                expires_at=session_data["expires_at"].isoformat()
            )
            
            utils.logger.info(f"二维码登录响应: {response_data.dict()}")
            return response_data
        
        elif request.login_method == "phone":
            # 手机号登录
            if not request.phone:
                error_msg = "手机号登录需要提供手机号"
                utils.logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            
            utils.logger.info(f"开始手机号登录流程，平台: {platform}, 手机号: {request.phone}")
            session_data["phone"] = request.phone
            background_tasks.add_task(handle_phone_login, session_id, platform, request.phone)
            
            response_data = LoginResponse(
                session_id=session_id,
                status="verification_code_sent",
                message="验证码已发送，请输入验证码",
                expires_at=session_data["expires_at"].isoformat()
            )
            
            utils.logger.info(f"手机号登录响应: {response_data.dict()}")
            return response_data
        
        elif request.login_method == "email":
            # 邮箱登录
            if not request.email:
                error_msg = "邮箱登录需要提供邮箱"
                utils.logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            
            utils.logger.info(f"开始邮箱登录流程，平台: {platform}, 邮箱: {request.email}")
            session_data["email"] = request.email
            background_tasks.add_task(handle_email_login, session_id, platform, request.email)
            
            response_data = LoginResponse(
                session_id=session_id,
                status="verification_code_sent",
                message="验证码已发送，请输入验证码",
                expires_at=session_data["expires_at"].isoformat()
            )
            
            utils.logger.info(f"邮箱登录响应: {response_data.dict()}")
            return response_data
        
        else:
            error_msg = f"不支持的登录方式: {request.login_method}"
            utils.logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
    
    except HTTPException as e:
        utils.logger.error(f"HTTP异常: 状态码={e.status_code}, 详情={e.detail}")
        raise
    except Exception as e:
        error_msg = f"开始登录失败: {str(e)}"
        utils.logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        utils.logger.info(f"=== 登录请求结束 ===")

@login_router.post("/login/check")
async def check_platform_login_status(request: LoginCheckRequest):
    """检查平台登录状态"""
    db = await get_db()
    
    try:
        utils.logger.info(f"检查平台登录状态 - 平台: {request.platform}, 账号ID: {request.account_id}")
        
        # 如果指定了账号ID，检查特定账号
        if request.account_id:
            account_query = "SELECT id, account_name, platform FROM social_accounts WHERE id = %s AND platform = %s"
            account = await db.get_first(account_query, request.account_id, request.platform)
            
            if not account:
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
            
            token = await db.get_first(token_query, request.account_id, request.platform)
            
            if not token:
                return {
                    "code": 200,
                    "message": f"账号 {account['account_name']} 未登录",
                    "data": {
                        "platform": request.platform,
                        "status": "not_logged_in",
                        "account_info": {"account_id": account['id'], "account_name": account['account_name']}
                    }
                }
            
            # 检查token是否过期
            if token['expires_at'] and token['expires_at'] < datetime.now():
                # 更新token为无效
                update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
                await db.execute(update_query, request.account_id, request.platform)
                
                return {
                    "code": 200,
                    "message": f"账号 {account['account_name']} 登录凭证已过期",
                    "data": {
                        "platform": request.platform,
                        "status": "expired",
                        "account_info": {"account_id": account['id'], "account_name": account['account_name']},
                        "last_login_time": token['created_at'].isoformat() if token['created_at'] else None,
                        "expires_at": token['expires_at'].isoformat() if token['expires_at'] else None
                    }
                }
            
            # 实际验证登录状态
            utils.logger.info(f"开始实际验证账号 {account['account_name']} 在平台 {request.platform} 的登录状态")
            verification_result = await verify_actual_login_status(request.platform, token['token_data'])
            
            # 尝试解析用户信息
            account_info = {"account_id": account['id'], "account_name": account['account_name']}
            try:
                token_data = json.loads(token['token_data'])
                if 'user_info' in token_data:
                    account_info.update(token_data['user_info'])
            except:
                pass
            
            if verification_result['is_logged_in']:
                # 更新最后使用时间
                update_query = "UPDATE login_tokens SET last_used_at = %s WHERE account_id = %s AND platform = %s"
                await db.execute(update_query, datetime.now(), request.account_id, request.platform)
                
                return {
                    "code": 200,
                    "message": f"账号 {account['account_name']} 已登录（已验证）",
                    "data": {
                        "platform": request.platform,
                        "status": "logged_in",
                        "account_info": account_info,
                        "last_login_time": token['created_at'].isoformat() if token['created_at'] else None,
                        "expires_at": token['expires_at'].isoformat() if token['expires_at'] else None
                    }
                }
            else:
                # 实际验证失败，将token设为无效
                update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
                await db.execute(update_query, request.account_id, request.platform)
                
                return {
                    "code": 200,
                    "message": f"账号 {account['account_name']} 登录状态验证失败：{verification_result.get('message', '未知错误')}",
                    "data": {
                        "platform": request.platform,
                        "status": "not_logged_in",
                        "account_info": account_info,
                        "last_login_time": token['created_at'].isoformat() if token['created_at'] else None,
                        "expires_at": token['expires_at'].isoformat() if token['expires_at'] else None
                    }
                }
        
        else:
            # 检查该平台所有账号的登录状态
            accounts_query = "SELECT id, account_name FROM social_accounts WHERE platform = %s AND is_active = 1"
            accounts = await db.query(accounts_query, request.platform)
            
            if not accounts:
                return {
                    "code": 200,
                    "message": f"平台 {request.platform} 没有可用账号",
                    "data": {
                        "platform": request.platform,
                        "status": "not_logged_in"
                    }
                }
            
            logged_in_accounts = []
            expired_accounts = []
            
            for account in accounts:
                token_query = """
                SELECT is_valid, expires_at, last_used_at, created_at
                FROM login_tokens 
                WHERE account_id = %s AND platform = %s AND is_valid = 1
                ORDER BY created_at DESC 
                LIMIT 1
                """
                
                token = await db.get_first(token_query, account['id'], request.platform)
                
                if token:
                    if not token['expires_at'] or token['expires_at'] >= datetime.now():
                        logged_in_accounts.append(account['account_name'])
                    else:
                        expired_accounts.append(account['account_name'])
            
            if logged_in_accounts:
                return {
                    "code": 200,
                    "message": f"平台 {request.platform} 有 {len(logged_in_accounts)} 个账号已登录: {', '.join(logged_in_accounts)}",
                    "data": {
                        "platform": request.platform,
                        "status": "logged_in",
                        "account_info": {"logged_in_count": len(logged_in_accounts), "logged_in_accounts": logged_in_accounts}
                    }
                }
            elif expired_accounts:
                return {
                    "code": 200,
                    "message": f"平台 {request.platform} 有 {len(expired_accounts)} 个账号登录已过期: {', '.join(expired_accounts)}",
                    "data": {
                        "platform": request.platform,
                        "status": "expired",
                        "account_info": {"expired_count": len(expired_accounts), "expired_accounts": expired_accounts}
                    }
                }
            else:
                return {
                    "code": 200,
                    "message": f"平台 {request.platform} 所有账号均未登录",
                    "data": {
                        "platform": request.platform,
                        "status": "not_logged_in"
                    }
                }
    
    except Exception as e:
        utils.logger.error(f"检查平台登录状态失败: {e}")
        return {
            "code": 500,
            "message": f"检查登录状态失败: {str(e)}",
            "data": {
                "platform": request.platform,
                "status": "unknown"
            }
        }

@login_router.get("/login/status/{session_id}", response_model=LoginStatusResponse)
async def get_login_status(session_id: str):
    """获取登录状态"""
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="登录会话不存在")
    
    session_data = login_sessions[session_id]
    
    # 检查会话是否过期
    if datetime.now() > session_data["expires_at"]:
        session_data["status"] = "expired"
        session_data["message"] = "登录会话已过期"
    
    # 检查是否需要显示远程桌面信息
    remote_desktop_info = await get_remote_desktop_info(session_data)
    
    return LoginStatusResponse(
        session_id=session_id,
        status=session_data["status"],
        message=session_data.get("message", ""),
        account_info=session_data.get("account_info"),
        progress=session_data.get("progress", 0),
        qr_code_data=session_data.get("qr_code_data"),
        captcha_screenshot=session_data.get("captcha_screenshot"),
        captcha_area=session_data.get("captcha_area"),
        element_analysis=session_data.get("element_analysis"),
        analysis_summary=session_data.get("analysis_summary"),
        saved_html_file=session_data.get("saved_html_file"),
        analysis_instruction=session_data.get("analysis_instruction"),
        html_save_error=session_data.get("html_save_error"),
        backup_html_file=session_data.get("backup_html_file"),
        # 远程桌面信息
        remote_desktop_url=remote_desktop_info.get("url"),
        remote_desktop_available=remote_desktop_info.get("available", False),
        remote_desktop_message=remote_desktop_info.get("message"),
        # 队列信息
        queue_position=session_data.get("queue_position"),
        estimated_wait_seconds=session_data.get("estimated_wait_seconds"),
        has_desktop_lock=session_data.get("has_desktop_lock"),
        # 自动关闭状态
        auto_closed=session_data.get("auto_closed")
    )

@login_router.get("/login/qrcode/{session_id}")
async def get_qrcode(session_id: str):
    """获取二维码图片"""
    if session_id not in login_sessions:
        utils.logger.error(f"二维码请求失败: 登录会话不存在 {session_id}")
        raise HTTPException(status_code=404, detail="登录会话不存在")
    
    session_data = login_sessions[session_id]
    utils.logger.info(f"二维码请求: session_id={session_id}, 会话状态={session_data.get('status')}, qr_code_data存在={('qr_code_data' in session_data)}")
    
    # 检查二维码是否已生成
    if "qr_code_data" not in session_data:
        # 如果二维码还未生成，返回相应的状态
        status = session_data.get("status", "unknown")
        utils.logger.warning(f"二维码数据不存在: session_id={session_id}, 状态={status}, 会话数据keys={list(session_data.keys())}")
        
        # 🔧 修复：优先检查验证码截图
        if "captcha_screenshot" in session_data and status == "captcha_required":
            # 如果有验证码截图且状态为需要验证码，返回验证码截图
            captcha_data = session_data["captcha_screenshot"]
            utils.logger.info(f"返回验证码截图: session_id={session_id}")
            
            if "," in captcha_data:
                captcha_data = captcha_data.split(",")[1]
            
            try:
                image_data = base64.b64decode(captcha_data)
                return StreamingResponse(
                    io.BytesIO(image_data),
                    media_type="image/png",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Debug-Info": "captcha-screenshot"
                    }
                )
            except Exception as e:
                utils.logger.error(f"Captcha screenshot return failed: {e}")
                # 返回英文错误信息，避免编码问题
                return StreamingResponse(
                    io.BytesIO(b"Captcha screenshot encoding error"),
                    media_type="text/plain",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Debug-Info": "captcha-screenshot-encoding-error"
                    }
                )
        
        # 检查是否有调试截图（错误情况）
        if "debug_screenshot" in session_data and status == "error":
            # 如果有调试截图且状态为错误，返回调试截图
            debug_data = session_data["debug_screenshot"]
            if "," in debug_data:
                debug_data = debug_data.split(",")[1]
            
            try:
                image_data = base64.b64decode(debug_data)
                return StreamingResponse(
                    io.BytesIO(image_data),
                    media_type="image/png",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Debug-Info": "login-debug-screenshot"
                    }
                )
            except Exception as e:
                utils.logger.error(f"Debug screenshot return failed: {e}")
                # 返回英文错误信息，避免编码问题
                return StreamingResponse(
                    io.BytesIO(b"Debug screenshot encoding error"),
                    media_type="text/plain",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Debug-Info": "debug-screenshot-encoding-error"
                    }
                )
        
        if status in ["initializing", "generating_qrcode", "waiting_for_qrcode", "clicking_login", "waiting_for_modal"]:
            raise HTTPException(status_code=202, detail="QR code is generating, please wait...")
        else:
            raise HTTPException(status_code=404, detail="QR code not generated")
    
    # 返回二维码图片
    qr_code_data = session_data["qr_code_data"]
    
    # 如果是base64编码的图片数据
    if isinstance(qr_code_data, str):
        try:
            # 如果包含data:image前缀，去掉它
            if "," in qr_code_data:
                qr_code_data = qr_code_data.split(",")[1]
            
            image_data = base64.b64decode(qr_code_data)
            return StreamingResponse(
                io.BytesIO(image_data),
                media_type="image/png",
                headers={"Cache-Control": "no-cache"}
            )
        except Exception as e:
            utils.logger.error(f"QR code data decode failed: {e}")
            raise HTTPException(status_code=500, detail="QR code data decode failed")
    
    raise HTTPException(status_code=500, detail="QR code data format error")

@login_router.post("/login/save_token")
async def save_login_token(request: TokenSaveRequest):
    """保存登录凭证"""
    db = await get_db()
    
    try:
        if request.session_id not in login_sessions:
            raise HTTPException(status_code=404, detail="登录会话不存在")
        
        session_data = login_sessions[request.session_id]
        account_id = session_data["account_id"]
        platform = session_data["platform"]
        
        # 将旧的token设为无效
        update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s AND platform = %s"
        await db.execute(update_query, account_id, platform)
        
        # 插入新的token
        insert_query = """
        INSERT INTO login_tokens (account_id, platform, token_type, token_data, user_agent, proxy_info, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query, 
            account_id, platform, "cookie", request.token_data,
            request.user_agent, request.proxy_info, request.expires_at
        )
        
        # 更新会话状态
        session_data["status"] = "logged_in"
        session_data["message"] = "登录成功"
        session_data["progress"] = 100
        
        # 解析用户信息
        try:
            token_json = json.loads(request.token_data)
            user_info = token_json.get("user_info", {})
            session_data["account_info"] = user_info
        except:
            pass
        
        return {"message": "登录凭证保存成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"保存登录凭证失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存登录凭证失败: {str(e)}")

@login_router.post("/login/logout/{account_id}")
async def logout_account(account_id: int):
    """账号登出"""
    db = await get_db()
    
    try:
        # 将该账号的所有token设为无效
        update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s"
        await db.execute(update_query, account_id)
        
        # 清理相关的登录会话
        sessions_to_remove = []
        for session_id, session_data in login_sessions.items():
            if session_data.get("account_id") == account_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del login_sessions[session_id]
        
        return {"message": "账号登出成功"}
    
    except Exception as e:
        utils.logger.error(f"账号登出失败: {e}")
        raise HTTPException(status_code=500, detail=f"账号登出失败: {str(e)}")

@login_router.get("/login/tokens/{account_id}")
async def get_account_tokens(account_id: int):
    """获取账号的登录凭证"""
    db = await get_db()
    
    try:
        query = """
        SELECT id, platform, token_type, is_valid, expires_at, last_used_at, created_at, updated_at
        FROM login_tokens 
        WHERE account_id = %s
        ORDER BY created_at DESC
        """
        
        results = await db.query(query, account_id)
        
        tokens = []
        for row in results:
            token = {
                "id": row['id'],
                "platform": row['platform'],
                "token_type": row['token_type'],
                "is_valid": bool(row['is_valid']),
                "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None,
                "last_used_at": row['last_used_at'].isoformat() if row['last_used_at'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
            tokens.append(token)
        
        return {
            "code": 200,
            "message": "获取账号凭证成功",
            "data": tokens
        }
    
    except Exception as e:
        utils.logger.error(f"获取账号凭证失败: {e}")
        return {
            "code": 500,
            "message": f"获取账号凭证失败: {str(e)}",
            "data": []
        }

@login_router.post("/login/log")
async def add_task_log(request: TaskLogRequest):
    """添加任务日志"""
    db = await get_db()
    
    try:
        insert_query = """
        INSERT INTO crawler_task_logs (task_id, platform, account_id, log_level, message, step, progress, extra_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query, 
            request.task_id, request.platform, request.account_id,
            request.log_level, request.message, request.step,
            request.progress, request.extra_data
        )
        
        return {"message": "日志添加成功"}
    
    except Exception as e:
        utils.logger.error(f"添加任务日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加任务日志失败: {str(e)}")

@login_router.get("/login/logs/{task_id}", response_model=List[dict])
async def get_task_logs(task_id: str, limit: int = 100):
    """获取任务日志"""
    db = await get_db()
    
    try:
        query = """
        SELECT id, platform, account_id, log_level, message, step, progress, extra_data, created_at
        FROM crawler_task_logs 
        WHERE task_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        results = await db.query(query, task_id, limit)
        
        logs = []
        for row in results:
            log = {
                "id": row['id'],
                "platform": row['platform'],
                "account_id": row['account_id'],
                "log_level": row['log_level'],
                "message": row['message'],
                "step": row['step'],
                "progress": row['progress'],
                "extra_data": row['extra_data'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            }
            logs.append(log)
        
        return logs
    
    except Exception as e:
        utils.logger.error(f"获取任务日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务日志失败: {str(e)}")

async def handle_qrcode_login(session_id: str, platform: str):
    """处理真实的平台二维码登录"""
    try:
        session_data = login_sessions[session_id]
        
        # 检查是否为即将支持的平台
        coming_soon_platforms = {"wb": "微博", "tieba": "贴吧", "zhihu": "知乎"}
        if platform in coming_soon_platforms:
            platform_name = coming_soon_platforms[platform]
            session_data["status"] = "coming_soon"
            session_data["message"] = f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。"
            session_data["progress"] = 100
            utils.logger.info(f"{platform_name}平台登录请求 - 即将支持")
            return
        
        utils.logger.info(f"开始真实平台登录，会话ID: {session_id}, 平台: {platform}")
        
        # 导入相关模块
        from playwright.async_api import async_playwright
        import config
        from tools import utils as crawler_utils
        
        # 根据平台创建对应的登录对象
        async with async_playwright() as playwright:
            # 启动浏览器
            chromium = playwright.chromium
            
            # 检查是否有显示环境，如果没有则使用headless模式
            import os
            has_display = os.environ.get('DISPLAY') is not None
            
            # ===== 使用增强配置 =====
            utils.logger.info(f"🚀 [Enhanced] 为平台 {platform} 获取增强配置")
            enhanced_config = get_enhanced_browser_config(platform)
            
            # 启动浏览器（使用增强参数）
            browser = await chromium.launch(
                headless=not has_display,
                args=enhanced_config['browser_args']
            )
            
            # 创建浏览器上下文（使用增强配置）
            browser_context = await browser.new_context(
                user_agent=enhanced_config['user_agent'],
                viewport=enhanced_config['viewport'],
                locale=enhanced_config['locale'],
                timezone_id=enhanced_config['timezone_id'],
                geolocation=enhanced_config['geolocation'],
                permissions=enhanced_config['permissions'],
                extra_http_headers=enhanced_config['extra_http_headers']
            )
            
            utils.logger.info(f"📱 [Enhanced] 使用User-Agent: {enhanced_config['user_agent'][:60]}...")
            utils.logger.info(f"🖥️ [Enhanced] 视窗大小: {enhanced_config['viewport']}")
            
            # 注入增强反检测脚本
            await inject_enhanced_stealth_script(browser_context, platform)
            
            # 创建页面
            page = await browser_context.new_page()
            
            try:
                if platform == "xhs":
                    await handle_xhs_login(session_id, browser_context, page)
                elif platform == "dy":
                    await handle_douyin_login(session_id, browser_context, page)
                elif platform == "bili":
                    await handle_bilibili_login(session_id, browser_context, page)
                elif platform == "wb":
                    await handle_weibo_login(session_id, browser_context, page)
                elif platform == "ks":
                    await handle_kuaishou_login(session_id, browser_context, page)
                elif platform == "tieba":
                    await handle_tieba_login(session_id, browser_context, page)
                elif platform == "zhihu":
                    await handle_zhihu_login(session_id, browser_context, page)
                else:
                    raise ValueError(f"不支持的平台: {platform}")
                    
            finally:
                await browser_context.close()
                await browser.close()
        
    except Exception as e:
        utils.logger.error(f"二维码登录处理失败: {e}", exc_info=True)
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "error"
            login_sessions[session_id]["message"] = f"登录失败: {str(e)}"

async def handle_phone_login(session_id: str, platform: str, phone: str):
    """处理手机号登录"""
    try:
        session_data = login_sessions[session_id]
        
        # 更新状态
        session_data["status"] = "sending_sms"
        session_data["message"] = "正在发送验证码..."
        session_data["progress"] = 20
        
        # 这里应该调用实际的平台接口发送验证码
        await asyncio.sleep(2)
        
        session_data["status"] = "verification_code_sent"
        session_data["message"] = "验证码已发送，请输入验证码"
        session_data["progress"] = 50
        
    except Exception as e:
        utils.logger.error(f"手机号登录处理失败: {e}")
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "error"
            login_sessions[session_id]["message"] = f"登录失败: {str(e)}"

async def handle_email_login(session_id: str, platform: str, email: str):
    """处理邮箱登录"""
    try:
        session_data = login_sessions[session_id]
        
        # 更新状态
        session_data["status"] = "sending_email"
        session_data["message"] = "正在发送验证码..."
        session_data["progress"] = 20
        
        # 这里应该调用实际的平台接口发送验证码
        await asyncio.sleep(2)
        
        session_data["status"] = "verification_code_sent"
        session_data["message"] = "验证码已发送，请输入验证码"
        session_data["progress"] = 50
        
    except Exception as e:
        utils.logger.error(f"邮箱登录处理失败: {e}")
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "error"
            login_sessions[session_id]["message"] = f"登录失败: {str(e)}"

async def is_qrcode_image(img_element):
    """检查图片元素是否是二维码"""
    try:
        # 获取图片的src属性
        src = await img_element.get_attribute("src")
        if not src:
            return False
        
        # 获取class属性
        class_name = await img_element.get_attribute("class") or ""
        
        # 特殊处理：如果class包含qrcode-img等明显的二维码标识，直接判定为二维码
        obvious_qrcode_classes = ['qrcode-img', 'qr-code', 'qrcode', 'login-qrcode']
        if any(cls in class_name.lower() for cls in obvious_qrcode_classes):
            utils.logger.info(f"  -> 检测到明显的二维码类名 '{class_name}'，直接判定为二维码")
            return True
        
        # 获取alt属性
        alt = await img_element.get_attribute("alt") or ""
        # 特殊处理：如果alt包含二维码相关信息，也直接判定
        if any(keyword in alt.lower() for keyword in ['qr', 'qrcode', '二维码', 'scan']):
            utils.logger.info(f"  -> 检测到二维码相关alt属性 '{alt}'，直接判定为二维码")
            return True
        
        # 获取图片的尺寸
        box = await img_element.bounding_box()
        if not box:
            # 如果无法获取尺寸，但src是base64且包含二维码特征，也认为是二维码
            if src.startswith('data:image/') and len(src) > 1000:  # base64二维码通常较大
                utils.logger.info("  -> 无法获取尺寸，但检测到base64图片，可能是隐藏的二维码")
                return True
            
            utils.logger.info("  -> 无法获取元素尺寸，且不是base64图片，跳过")
            return False
        
        width = box['width']
        height = box['height']
        
        # 二维码通常是正方形或接近正方形
        aspect_ratio = width / height if height > 0 else 0
        is_square_ish = 0.8 <= aspect_ratio <= 1.25
        
        # 二维码通常有一定的最小尺寸 - 放宽限制
        is_reasonable_size = width >= 50 and height >= 50
        
        # 检查src是否包含二维码相关信息
        src_indicates_qr = any(keyword in src.lower() for keyword in ['qr', 'qrcode', '二维码'])
        
        # 检查是否是base64图片且尺寸合理
        is_base64_and_reasonable = src.startswith('data:image/') and is_reasonable_size and is_square_ish
        
        # 获取alt和class属性的二维码相关信息
        alt_indicates_qr = any(keyword in alt.lower() for keyword in ['qr', 'qrcode', '二维码', 'scan'])
        class_indicates_qr = any(keyword in class_name.lower() for keyword in ['qr', 'qrcode'])
        
        utils.logger.info(f"图片验证详情:")
        utils.logger.info(f"  - src: {src[:50]}...")
        utils.logger.info(f"  - 尺寸: {width}x{height}")
        utils.logger.info(f"  - 正方形: {is_square_ish} (比例: {aspect_ratio:.2f})")
        utils.logger.info(f"  - 尺寸合理: {is_reasonable_size}")
        utils.logger.info(f"  - alt: '{alt}'")
        utils.logger.info(f"  - class: '{class_name}'")
        utils.logger.info(f"  - src包含qr: {src_indicates_qr}")
        utils.logger.info(f"  - alt包含qr: {alt_indicates_qr}")
        utils.logger.info(f"  - class包含qr: {class_indicates_qr}")
        utils.logger.info(f"  - base64且合理: {is_base64_and_reasonable}")
        
        # 综合判断 - 放宽条件，优先识别base64二维码
        is_qr = (is_reasonable_size and is_square_ish and 
                (src_indicates_qr or alt_indicates_qr or class_indicates_qr or is_base64_and_reasonable))
        
        # 特殊处理：如果是base64图片且是正方形，很可能是二维码
        if src.startswith('data:image/') and is_square_ish and width >= 50:
            utils.logger.info("  -> 检测到base64正方形图片，判定为二维码")
            is_qr = True
        
        utils.logger.info(f"  -> 最终判定: {'是二维码' if is_qr else '不是二维码'}")
        return is_qr
        
    except Exception as e:
        utils.logger.debug(f"验证二维码图片失败: {e}")
        return False

async def handle_xhs_login(session_id: str, browser_context, page):
    """处理小红书登录"""
    session_data = login_sessions[session_id]
    
    try:
        # 先测试网络连接
        import requests
        try:
            utils.logger.info("测试网络连接...")
            response = requests.get("https://www.xiaohongshu.com", timeout=10)
            utils.logger.info(f"HTTP请求状态码: {response.status_code}")
        except Exception as e:
            utils.logger.error(f"网络连接测试失败: {e}")
        
        # 尝试直接访问登录页面 - 优先使用主站
        login_urls = [
            "https://www.xiaohongshu.com/explore",
            "https://www.xiaohongshu.com",
            "https://creator.xiaohongshu.com/login",
            "https://creator.xiaohongshu.com"
        ]
        
        page_loaded = False
        for url in login_urls:
            try:
                utils.logger.info(f"尝试访问: {url}")
                utils.logger.info(f"浏览器User-Agent: {await page.evaluate('navigator.userAgent')}")
                
                # 使用与测试脚本相同的配置
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                utils.logger.info(f"页面DOM加载完成: {url}")
                
                # 等待页面稳定
                await asyncio.sleep(2)
                
                # 检查页面是否正常加载
                page_title = await page.title()
                utils.logger.info(f"页面标题: {page_title}")
                
                # 如果页面标题包含"安全限制"，获取详细信息
                if "安全限制" in page_title or "安全" in page_title:
                    utils.logger.warning(f"检测到安全限制页面，标题: {page_title}")
                    
                    # 获取页面的完整文本内容
                    page_content = await page.text_content("body")
                    utils.logger.info(f"页面内容: {page_content[:500]}...")  # 只显示前500字符
                    
                    # 查找具体的安全限制信息
                    security_elements = await page.query_selector_all("h1, h2, h3, .title, .message, .error-message, .security-info")
                    for i, elem in enumerate(security_elements):
                        if elem:
                            text = await elem.text_content()
                            if text and text.strip():
                                utils.logger.info(f"安全限制信息 {i+1}: {text.strip()}")
                    
                    # 检查是否有验证码或其他安全验证
                    captcha_elements = await page.query_selector_all("input[type='text'], input[placeholder*='验证'], .captcha, .verify")
                    if captcha_elements:
                        utils.logger.info(f"检测到验证元素，数量: {len(captcha_elements)}")
                    
                    continue
                
                # 检查是否有错误页面
                error_elements = await page.query_selector_all(".error-img, .error-page, [class*='error']")
                if error_elements:
                    utils.logger.warning(f"检测到错误页面元素，数量: {len(error_elements)}")
                    continue
                else:
                    utils.logger.info(f"页面正常加载: {url}")
                    page_loaded = True
                    break
            except Exception as e:
                utils.logger.warning(f"访问 {url} 失败: {e}")
                continue
        
        if not page_loaded:
            utils.logger.warning("所有URL都无法正常加载，尝试其他策略...")
            
            # 尝试策略1: 访问手机版页面
            try:
                utils.logger.info("尝试策略1: 访问手机版页面")
                await page.goto("https://m.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                page_title = await page.title()
                utils.logger.info(f"手机版页面标题: {page_title}")
                if "小红书" in page_title:
                    page_loaded = True
                    utils.logger.info("成功访问手机版页面")
            except Exception as e:
                utils.logger.warning(f"策略1失败: {e}")
            
            # 尝试策略2: 访问创作者中心登录页面
            if not page_loaded:
                try:
                    utils.logger.info("尝试策略2: 访问创作者中心登录页面")
                    await page.goto("https://creator.xiaohongshu.com/login", wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                    page_title = await page.title()
                    utils.logger.info(f"创作者中心页面标题: {page_title}")
                    if "登录" in page_title or "小红书" in page_title:
                        page_loaded = True
                        utils.logger.info("成功访问创作者中心登录页面")
                except Exception as e:
                    utils.logger.warning(f"策略2失败: {e}")
            
            # 尝试策略3: 刷新当前页面
            if not page_loaded:
                try:
                    utils.logger.info("尝试策略3: 刷新当前页面")
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                except Exception as e:
                    utils.logger.warning(f"策略3失败: {e}")
            
            # 获取当前页面的详细信息
            current_title = await page.title()
            current_url = page.url
            utils.logger.info(f"刷新后页面标题: {current_title}")
            utils.logger.info(f"当前页面URL: {current_url}")
            
            # 如果仍然是安全限制页面，获取详细信息
            if "安全限制" in current_title or "安全" in current_title:
                page_content = await page.text_content("body")
                utils.logger.error(f"安全限制页面完整内容: {page_content}")
                
                # 保存页面截图用于调试
                screenshot_path = f"/tmp/xhs_security_restriction_{session_id}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                utils.logger.info(f"安全限制页面截图已保存: {screenshot_path}")
                
                # 更新会话状态
                login_sessions[session_id]["status"] = "failed"
                login_sessions[session_id]["message"] = f"访问被安全限制阻止: {current_title}"
                login_sessions[session_id]["progress"] = 0
                
                raise Exception(f"小红书访问被安全限制阻止: {current_title}")
            else:
                utils.logger.info("页面刷新后恢复正常")
        
        # 更新状态
        session_data["status"] = "generating_qrcode"
        session_data["message"] = "正在生成二维码..."
        session_data["progress"] = 20
        
        # 点击登录按钮（如果需要）
        try:
            # 尝试多种可能的登录按钮选择器
            login_selectors = [
                "button.submit",  # 从截图中看到的实际选择器
                ".submit",        # CSS类选择器
                "text=登录",      # Playwright的文本选择器
                "xpath=//button[contains(@class, 'submit')]",
                "xpath=//button[contains(text(), '登录')]",
                "xpath=//div[contains(text(), '登录')]",
                "xpath=//*[contains(text(), '登录') and (self::button or self::div or self::span)]",
                "xpath=//*[@id='app']//button[contains(text(), '登录')]",
                "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button",
                "button:has-text('登录')",
                "[data-testid='login-button']",
                ".login-button"
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    utils.logger.info(f"尝试查找登录按钮，选择器: {selector}")
                    login_button = await page.wait_for_selector(selector, timeout=3000)
                    if login_button:
                        is_visible = await login_button.is_visible()
                        if is_visible:
                            await login_button.click()
                            await asyncio.sleep(3)
                            login_clicked = True
                            utils.logger.info(f"成功点击登录按钮，使用选择器: {selector}")
                            break
                        else:
                            utils.logger.info(f"找到登录按钮但不可见，选择器: {selector}")
                except Exception as e:
                    utils.logger.debug(f"选择器 {selector} 未找到登录按钮: {e}")
                    continue
            
            if not login_clicked:
                utils.logger.info("未找到可点击的登录按钮，可能登录弹窗已自动显示")
        except Exception as e:
            utils.logger.info(f"点击登录按钮过程出错: {e}")
        
        # 等待登录弹窗出现 - 增加等待时间
        utils.logger.info("等待登录弹窗完全加载...")
        await asyncio.sleep(5)
        
        # 检查是否有弹窗或模态框
        modal_selectors = [
            ".modal",
            ".dialog",
            ".popup",
            ".login-modal",
            ".login-dialog",
            "[role='dialog']",
            "[class*='modal']",
            "[class*='dialog']",
            "[class*='popup']"
        ]
        
        modal_found = False
        for selector in modal_selectors:
            try:
                modal_element = await page.wait_for_selector(selector, timeout=2000)
                if modal_element and await modal_element.is_visible():
                    utils.logger.info(f"找到登录弹窗: {selector}")
                    modal_found = True
                    break
            except:
                continue
        
        if not modal_found:
            utils.logger.warning("未找到明显的登录弹窗，可能弹窗结构不同")
        
        # 尝试查找"小红书如何扫码"链接或二维码切换按钮
        qrcode_trigger_selectors = [
            "text=小红书如何扫码",
            "text=扫码登录",
            "xpath=//span[contains(text(), '小红书如何扫码')]",
            "xpath=//span[contains(text(), '扫码')]",
            "xpath=//*[contains(text(), '扫码')]",
            "[class*='qrcode'] span",
            ".qrcode-trigger",
            ".qrcode-tab",
            "[data-testid='qrcode-tab']"
        ]
        
        for selector in qrcode_trigger_selectors:
            try:
                trigger_element = await page.wait_for_selector(selector, timeout=3000)
                if trigger_element and await trigger_element.is_visible():
                    await trigger_element.click()
                    utils.logger.info(f"点击了二维码触发元素: {selector}")
                    await asyncio.sleep(3)  # 等待二维码加载
                    break
            except:
                continue
        
        # 查找二维码 - 根据实际页面结构优化选择器
        qrcode_selectors = [
            "img.qrcode-img",  # 从截图看到的实际选择器
            ".qrcode-img",     # CSS类选择器
            "xpath=//img[@class='qrcode-img']",  # 原始xpath
            "xpath=//img[contains(@class, 'qrcode-img')]",
            "xpath=//img[contains(@class, 'qrcode') or contains(@class, 'qr-code')]",
            "xpath=//div[contains(@class, 'login')]//img[contains(@class, 'qrcode')]",
            "xpath=//img[contains(@src, 'qr') and not(contains(@src, 'logo'))]",
            "xpath=//img[starts-with(@src, 'data:image/')]",  # 所有base64图片
            "xpath=//canvas",  # 有些网站使用canvas显示二维码
            "[class*='qrcode'] img",
            "img[src*='qr']",
            "img[src^='data:image/']",  # CSS选择器版本的base64图片
            "xpath=//img[contains(@alt, '二维码') or contains(@alt, 'qrcode') or contains(@alt, 'QR')]"
        ]
        
        qrcode_element = None
        qrcode_selector = None
        
        # 等待登录弹窗完全加载
        await asyncio.sleep(3)
        
        # 先打印整个页面的详细结构用于分析
        utils.logger.info("=" * 80)
        utils.logger.info("开始分析页面结构...")
        utils.logger.info("=" * 80)
        
        # 获取页面中所有可能的弹窗元素
        all_possible_modals = await page.query_selector_all("div")
        utils.logger.info(f"页面中共找到 {len(all_possible_modals)} 个div元素")
        
        # 查找包含登录相关内容的元素
        login_related_elements = []
        for i, div in enumerate(all_possible_modals):
            try:
                div_class = await div.get_attribute("class") or ""
                div_id = await div.get_attribute("id") or ""
                is_visible = await div.is_visible()
                
                # 检查是否包含登录相关的类名或ID
                if any(keyword in (div_class + div_id).lower() for keyword in ['login', 'modal', 'dialog', 'popup', 'qr', 'scan']):
                    login_related_elements.append((i, div, div_class, div_id, is_visible))
            except:
                continue
        
        utils.logger.info(f"找到 {len(login_related_elements)} 个登录相关元素:")
        for i, (idx, div, div_class, div_id, is_visible) in enumerate(login_related_elements):
            utils.logger.info(f"  登录元素 {i}: index={idx}, class='{div_class}', id='{div_id}', 可见={is_visible}")
        
        # 对每个可见的登录相关元素，打印其内部结构
        for i, (idx, div, div_class, div_id, is_visible) in enumerate(login_related_elements):
            if is_visible:
                utils.logger.info(f"\n--- 分析登录元素 {i} 的内部结构 ---")
                try:
                    # 获取元素的HTML内容
                    inner_html = await div.inner_html()
                    utils.logger.info(f"元素 {i} 的HTML内容: {inner_html[:500]}...")
                    
                    # 查找其中的所有图片
                    imgs_in_element = await div.query_selector_all("img")
                    utils.logger.info(f"元素 {i} 内找到 {len(imgs_in_element)} 个图片:")
                    
                    for j, img in enumerate(imgs_in_element):
                        try:
                            img_class = await img.get_attribute("class") or ""
                            img_src = await img.get_attribute("src") or ""
                            img_alt = await img.get_attribute("alt") or ""
                            img_visible = await img.is_visible()
                            box = await img.bounding_box()
                            size_info = f"{box['width']}x{box['height']}" if box else "unknown"
                            
                            utils.logger.info(f"    图片 {j}: class='{img_class}', alt='{img_alt}', 尺寸={size_info}, 可见={img_visible}")
                            utils.logger.info(f"           src='{img_src[:200]}...' " if len(img_src) > 200 else f"           src='{img_src}'")
                            
                            # 检查是否是二维码 - 无论是否可见都要检查
                            if await is_qrcode_image(img):
                                utils.logger.info(f"    *** 找到二维码！在元素 {i} 的图片 {j} ***")
                                qrcode_element = img
                                qrcode_selector = f"login_element_{i}_img_{j}"
                                
                                # 如果二维码不可见，尝试让它变为可见
                                if not img_visible:
                                    utils.logger.info("    二维码不可见，尝试让它变为可见...")
                                    
                                    # 尝试1：等待一段时间，可能是懒加载
                                    await asyncio.sleep(2)
                                    img_visible_after_wait = await img.is_visible()
                                    if img_visible_after_wait:
                                        utils.logger.info("    等待后二维码变为可见")
                                    else:
                                        utils.logger.info("    等待后二维码仍然不可见")
                                        
                                        # 尝试2：查找并点击可能的二维码选项卡或按钮
                                        qrcode_tabs = await page.query_selector_all("xpath=//div[contains(text(), '二维码') or contains(text(), '扫码') or contains(@class, 'qrcode')]")
                                        if qrcode_tabs:
                                            utils.logger.info(f"    找到 {len(qrcode_tabs)} 个可能的二维码选项卡")
                                            for tab in qrcode_tabs:
                                                try:
                                                    if await tab.is_visible():
                                                        await tab.click()
                                                        utils.logger.info("    点击了二维码选项卡")
                                                        await asyncio.sleep(1)
                                                        break
                                                except:
                                                    pass
                                        
                                        # 尝试3：滚动到元素位置
                                        try:
                                            await img.scroll_into_view_if_needed()
                                            utils.logger.info("    滚动到二维码元素位置")
                                            await asyncio.sleep(1)
                                        except:
                                            pass
                                        
                                        # 再次检查是否变为可见
                                        img_visible_final = await img.is_visible()
                                        if img_visible_final:
                                            utils.logger.info("    二维码现在可见了")
                                        else:
                                            utils.logger.info("    二维码仍然不可见，但仍然使用它")
                                
                                break
                        except Exception as e:
                            utils.logger.debug(f"    检查图片 {j} 失败: {e}")
                    
                    if qrcode_element:
                        break
                        
                except Exception as e:
                    utils.logger.warning(f"分析元素 {i} 失败: {e}")
        
        utils.logger.info("=" * 80)
        utils.logger.info("页面结构分析完成")
        utils.logger.info("=" * 80)
        
        # 如果在弹窗内没有找到二维码，继续在整个页面搜索
        if not qrcode_element:
            utils.logger.info("弹窗内未找到二维码，继续在整个页面搜索...")
            for selector in qrcode_selectors:
                try:
                    utils.logger.info(f"尝试查找二维码，选择器: {selector}")
                    qrcode_element = await page.wait_for_selector(selector, timeout=5000)
                    if qrcode_element:
                        # 检查元素是否可见
                        is_visible = await qrcode_element.is_visible()
                        # 验证是否是真正的二维码
                        if await is_qrcode_image(qrcode_element):
                            qrcode_selector = selector
                            utils.logger.info(f"找到二维码元素，使用选择器: {selector}")
                            
                            # 如果二维码不可见，尝试让它变为可见
                            if not is_visible:
                                utils.logger.info(f"二维码不可见，尝试让它变为可见...")
                                
                                # 尝试等待加载
                                await asyncio.sleep(2)
                                is_visible_after_wait = await qrcode_element.is_visible()
                                if is_visible_after_wait:
                                    utils.logger.info(f"等待后二维码变为可见")
                                else:
                                    utils.logger.info(f"等待后二维码仍然不可见")
                                    
                                    # 尝试滚动到元素位置
                                    try:
                                        await qrcode_element.scroll_into_view_if_needed()
                                        utils.logger.info(f"滚动到二维码元素位置")
                                        await asyncio.sleep(1)
                                    except:
                                        pass
                            
                            break
                        else:
                            utils.logger.info(f"找到图片但不是二维码，选择器: {selector}")
                except Exception as e:
                    utils.logger.debug(f"选择器 {selector} 未找到二维码: {e}")
                    continue
        
        if not qrcode_element or not qrcode_selector:
            # 如果找不到二维码，尝试遍历所有图片
            utils.logger.warning("常规选择器未找到二维码，尝试遍历所有图片...")
            
            all_imgs = await page.query_selector_all("img")
            utils.logger.info(f"页面中共找到 {len(all_imgs)} 个img元素")
            
            for i, img in enumerate(all_imgs):
                try:
                    is_visible = await img.is_visible()
                    # 检查是否是二维码 - 无论是否可见都要检查
                    if await is_qrcode_image(img):
                        qrcode_element = img
                        qrcode_selector = f"img_index_{i}"
                        utils.logger.info(f"通过遍历找到二维码，图片索引: {i}")
                        
                        # 如果二维码不可见，尝试让它变为可见
                        if not is_visible:
                            utils.logger.info(f"二维码 {i} 不可见，尝试让它变为可见...")
                            
                            # 尝试等待加载
                            await asyncio.sleep(2)
                            is_visible_after_wait = await img.is_visible()
                            if is_visible_after_wait:
                                utils.logger.info(f"等待后二维码 {i} 变为可见")
                            else:
                                utils.logger.info(f"等待后二维码 {i} 仍然不可见")
                                
                                # 尝试滚动到元素位置
                                try:
                                    await img.scroll_into_view_if_needed()
                                    utils.logger.info(f"滚动到二维码 {i} 元素位置")
                                    await asyncio.sleep(1)
                                except:
                                    pass
                        
                        break
                except Exception as e:
                    utils.logger.debug(f"检查图片 {i} 失败: {e}")
                    continue
            
            # 如果仍然找不到，进行调试
            if not qrcode_element:
                utils.logger.error("未找到可见的二维码元素，正在进行详细调试...")
                
                # 确保目录存在
                import os
                os.makedirs("/tmp", exist_ok=True)
                
                screenshot_path = f"/tmp/xhs_login_debug_{session_id}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                utils.logger.info(f"登录页面截图已保存: {screenshot_path}")
                
                # 获取页面HTML结构用于调试
                try:
                    page_html = await page.content()
                    html_path = f"/tmp/xhs_login_html_{session_id}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    utils.logger.info(f"页面HTML已保存: {html_path}")
                except:
                    pass
                
                # 检查是否有弹窗
                utils.logger.info("检查页面中的弹窗元素...")
                modal_elements = await page.query_selector_all(".modal, .dialog, .popup, [role='dialog'], [class*='modal'], [class*='dialog'], [class*='popup']")
                utils.logger.info(f"找到 {len(modal_elements)} 个可能的弹窗元素")
                
                for i, modal in enumerate(modal_elements):
                    try:
                        modal_class = await modal.get_attribute("class")
                        is_visible = await modal.is_visible()
                        utils.logger.info(f"弹窗 {i}: class='{modal_class}', 可见={is_visible}")
                        
                        if is_visible:
                            # 在这个弹窗内查找图片
                            modal_imgs = await modal.query_selector_all("img")
                            utils.logger.info(f"弹窗 {i} 内找到 {len(modal_imgs)} 个图片")
                            
                            for j, img in enumerate(modal_imgs):
                                try:
                                    img_class = await img.get_attribute("class")
                                    img_src = await img.get_attribute("src")
                                    img_alt = await img.get_attribute("alt")
                                    box = await img.bounding_box()
                                    size_info = f"{box['width']}x{box['height']}" if box else "unknown"
                                    utils.logger.info(f"  弹窗图片 {j}: class='{img_class}', alt='{img_alt}', 尺寸={size_info}, src='{img_src[:100] if img_src else None}'")
                                except:
                                    pass
                    except:
                        pass
                
                # 输出所有图片的详细信息
                utils.logger.info("所有页面图片信息:")
                for i, img in enumerate(all_imgs[:10]):  # 检查前10个
                    try:
                        img_class = await img.get_attribute("class")
                        img_src = await img.get_attribute("src")
                        img_alt = await img.get_attribute("alt")
                        box = await img.bounding_box()
                        size_info = f"{box['width']}x{box['height']}" if box else "unknown"
                        is_visible = await img.is_visible()
                        utils.logger.info(f"图片 {i}: class='{img_class}', alt='{img_alt}', 尺寸={size_info}, 可见={is_visible}, src='{img_src[:100] if img_src else None}'")
                    except:
                        pass
                
                raise Exception("未找到可见的二维码元素，请检查页面结构或网络连接")
        
        # 获取二维码图片
        qrcode_src = await qrcode_element.get_attribute("src")
        utils.logger.info(f"获取到小红书二维码: {qrcode_src}")
        
        # 直接使用获取到的二维码数据
        if qrcode_src and qrcode_src.startswith("data:image/"):
            session_data["qr_code_data"] = qrcode_src
            session_data["status"] = "qr_code_ready"
            session_data["message"] = "二维码已生成，请使用小红书APP扫码"
            session_data["progress"] = 50
            utils.logger.info("小红书二维码生成成功")
        else:
            raise Exception(f"获取二维码失败，src: {qrcode_src}")
        
        # 获取登录前的session
        current_cookies = await browser_context.cookies()
        cookie_dict = {}
        for cookie in current_cookies:
            cookie_dict[cookie['name']] = cookie['value']
        no_logged_in_session = cookie_dict.get("web_session", "")
        
        # 等待扫码登录
        session_data["status"] = "waiting_for_scan"
        session_data["message"] = "等待扫码..."
        session_data["progress"] = 60
        
        # 检查登录状态
        max_wait_time = 120  # 最多等待2分钟
        check_interval = 2   # 每2秒检查一次
        
        for i in range(max_wait_time // check_interval):
            await asyncio.sleep(check_interval)
            
            # 获取当前cookies
            current_cookies = await browser_context.cookies()
            cookie_dict = {}
            for cookie in current_cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            current_session = cookie_dict.get("web_session", "")
            
            # 检查是否登录成功
            if current_session and current_session != no_logged_in_session:
                session_data["status"] = "logged_in"
                session_data["message"] = "登录成功！"
                session_data["progress"] = 100
                
                # 保存登录凭证
                await save_login_cookies(session_id, current_cookies, "xhs")
                utils.logger.info("小红书登录成功，已保存登录凭证")
                return
        
        # 超时未登录
        session_data["status"] = "timeout"
        session_data["message"] = "登录超时，请重新尝试"
        session_data["progress"] = 0
        
    except Exception as e:
        utils.logger.error(f"小红书登录失败: {e}")
        session_data["status"] = "error"
        session_data["message"] = f"登录失败: {str(e)}"
        session_data["progress"] = 0
        # 新增：超时后立即释放远程桌面锁
        if session_data.get("has_desktop_lock"):
            await remote_desktop_lock.release(session_id)
            session_data["has_desktop_lock"] = False

# 重复的save_login_cookies函数已移除，使用后面的版本

async def handle_douyin_login(session_id: str, browser_context, page):
    """处理抖音登录"""
    session_data = login_sessions[session_id]
    
    try:
        utils.logger.info(f"🎵 [抖音] 开始增强登录流程")
        
        # 测试网络连接
        try:
            utils.logger.info("测试抖音网络连接...")
            import requests
            response = requests.get("https://www.douyin.com", timeout=10)
            utils.logger.info(f"抖音HTTP请求状态码: {response.status_code}")
        except Exception as e:
            utils.logger.error(f"抖音网络连接测试失败: {e}")
        
        # 根据用户提供的准确流程：进入指定的抖音URL
        target_url = "https://www.douyin.com/?recommend=1"
        utils.logger.info(f"🎵 [抖音] 步骤1: 加载抖音页面 {target_url}")
        
        try:
            session_data["status"] = "loading_page"
            session_data["message"] = "正在加载抖音页面..."
            session_data["progress"] = 20
            
            await page.goto(target_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(3)  # 等待页面完全加载
            
            current_url = page.url
            title = await page.title()
            utils.logger.info(f"✅ [抖音] 页面加载成功: {current_url}, 标题: {title}")
            
            # 检查是否有浏览器版本过低的提示
            page_content = await page.content()
            version_warnings = [
                "浏览器版本过低",
                "browser version", 
                "不支持您的浏览器",
                "Please upgrade",
                "您的浏览器版本过低",
                "版本过旧"
            ]
            
            has_version_issue = any(warning in page_content for warning in version_warnings)
            
            if has_version_issue:
                utils.logger.warning(f"🎵 [抖音] 检测到浏览器版本问题，已使用最新User-Agent(Chrome 131)")
                session_data["message"] = "抖音检测到浏览器版本，已自动优化..."
                
                # 尝试刷新页面
                await page.reload(wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                
                page_content = await page.content()
                has_version_issue = any(warning in page_content for warning in version_warnings)
                
                if has_version_issue:
                    utils.logger.error(f"❌ [抖音] 刷新后仍有版本问题")
                else:
                    utils.logger.info(f"✅ [抖音] 版本问题已解决")
            
            # 保存当前页面URL供前端使用
            session_data["current_url"] = current_url
            
        except Exception as e:
            raise Exception(f"无法加载抖音页面 {target_url}: {e}")
        
        # 步骤2：查找并点击右上角登录按钮
        utils.logger.info("步骤2: 查找右上角登录按钮...")
        session_data["status"] = "clicking_login"
        session_data["message"] = "正在点击登录按钮..."
        session_data["progress"] = 40
        
        # 精确的右上角登录按钮选择器（基于真实HTML结构）
        login_selectors = [
            # 🎯 基于用户提供的真实HTML元素的精确选择器
            ".semi-button.semi-button-primary",  # 基于类名组合
            ".QPtP8FSi",  # 基于特定类名
            "button:has(.KetGEJla)",  # 基于内部文字的类名
            ".semi-button:has(.KetGEJla)",  # 基于按钮类和文字类
            "button:has(svg#svg_icon_avatar)",  # 基于SVG图标ID
            ".semi-button-content:has(.KetGEJla)",  # 基于内容结构
            "button.semi-button-primary:has-text('登录')",  # 组合选择器
            "button.semi-button.semi-button-primary.QPtP8FSi",  # 完整类名匹配
            ".semi-button:has(p.KetGEJla)",  # 基于p标签和类名
            
            # 传统选择器（保持兼容性）
            ".header-login",
            ".right-entry .login",
            ".top-right .login",
            ".user-info .login",
            ".header-right .login-btn",
            "[data-e2e='top-login-button']",
            # 更通用的右上角定位
            "xpath=//div[contains(@class,'header') or contains(@class,'top')]//button[contains(text(),'登录')]",
            "xpath=//div[contains(@class,'header') or contains(@class,'top')]//a[contains(text(),'登录')]",
            "xpath=//div[contains(@class,'right')]//button[contains(text(),'登录')]",
            "xpath=//div[contains(@class,'right')]//a[contains(text(),'登录')]",
            "xpath=//div[contains(@class,'nav')]//button[contains(text(),'登录')]",
            # 通用文字匹配
            "text=登录",
            "button:has-text('登录')",
            ".login-button"
        ]
        
        login_clicked = False
        for i, selector in enumerate(login_selectors):
            try:
                utils.logger.info(f"尝试选择器 {i+1}/{len(login_selectors)}: {selector}")
                login_element = await page.wait_for_selector(selector, timeout=3000)
                if login_element:
                    # 检查元素是否可见和可点击
                    is_visible = await login_element.is_visible()
                    if is_visible:
                        # 获取元素位置信息
                        box = await login_element.bounding_box()
                        utils.logger.info(f"找到登录按钮位置: {box}")
                        
                        # 尝试点击登录按钮 - 三种方式
                        click_methods = [
                            ("普通点击", lambda: login_element.click()),
                            ("强制点击", lambda: login_element.click(force=True)),
                            ("JavaScript点击", lambda: login_element.evaluate("element => element.click()"))
                        ]
                        
                        for method_name, click_method in click_methods:
                            try:
                                utils.logger.info(f"尝试{method_name}...")
                                await click_method()
                                utils.logger.info(f"✅ {method_name}成功: {selector}")
                                login_clicked = True
                                await asyncio.sleep(3)  # 等待弹窗出现
                                break
                            except Exception as click_error:
                                utils.logger.error(f"❌ {method_name}失败: {click_error}")
                                continue
                        
                        # 如果点击成功，退出选择器循环
                        if login_clicked:
                            # 检查页面是否有变化
                            try:
                                utils.logger.info("检查点击后页面变化...")
                                # 等待页面可能的DOM变化
                                await asyncio.sleep(2)
                                
                                # 检查是否有新的元素出现
                                new_elements = await page.query_selector_all(".modal, .popup, .dialog, .login-modal, .overlay")
                                if new_elements:
                                    utils.logger.info(f"✅ 检测到 {len(new_elements)} 个可能的弹窗元素")
                                    for i, elem in enumerate(new_elements):
                                        is_visible = await elem.is_visible()
                                        utils.logger.info(f"   弹窗元素[{i}]: visible={is_visible}")
                                else:
                                    utils.logger.info("未检测到明显的弹窗元素，但点击可能仍然成功")
                                    
                                # 检查页面URL是否变化
                                current_url = page.url
                                utils.logger.info(f"当前页面URL: {current_url}")
                                
                            except Exception as debug_error:
                                utils.logger.error(f"页面变化检查失败: {debug_error}")
                            
                            break
                    else:
                        utils.logger.debug(f"登录按钮不可见: {selector}")
            except Exception as e:
                utils.logger.debug(f"选择器失败 {selector}: {e}")
                continue
        
        if not login_clicked:
            utils.logger.error("❌ 未找到右上角登录按钮，无法继续登录流程")
            try:
                debug_screenshot = await page.screenshot()
                utils.logger.info(f"调试截图已生成，大小: {len(debug_screenshot)} bytes")
                # 可以将截图保存到session_data供前端查看
                debug_base64 = base64.b64encode(debug_screenshot).decode()
                session_data["debug_screenshot"] = f"data:image/png;base64,{debug_base64}"
            except:
                pass
            
            session_data["status"] = "error"
            session_data["message"] = "未找到登录按钮，请检查页面是否正常加载"
            return
        
        # 步骤3：等待登录弹窗出现
        utils.logger.info("步骤3: 等待登录弹窗出现...")
        session_data["status"] = "waiting_for_modal"
        session_data["message"] = "正在等待登录弹窗..."
        session_data["progress"] = 50
        
        # 查找登录弹窗的选择器（优先使用用户提供的精确信息）
        modal_selectors = [
            # 🎯 用户提供的真实登录弹窗信息
            "#login-panel-new",  # 精确的ID选择器
            ".BGmBK6_i",  # 精确的class选择器
            "[data-bytereplay-mask='strict']",  # 精确的data属性选择器
            "div#login-panel-new",  # 完整标签+ID
            "div.BGmBK6_i",  # 完整标签+class
            "#login-panel-new.BGmBK6_i",  # ID+class组合
            "div#login-panel-new.BGmBK6_i",  # 完整选择器
            "[id='login-panel-new']",  # 属性选择器
            
            # 传统弹窗选择器（保持兼容性）
            ".modal",
            ".popup", 
            ".dialog",
            ".login-modal",
            ".login-popup",
            "[role='dialog']",
            ".ant-modal",
            ".el-dialog",
            ".layer",
            ".overlay"
        ]
        
        modal_appeared = False
        for selector in modal_selectors:
            try:
                utils.logger.info(f"检查弹窗选择器: {selector}")
                modal_element = await page.wait_for_selector(selector, timeout=3000)
                if modal_element and await modal_element.is_visible():
                    utils.logger.info(f"✅ 检测到登录弹窗: {selector}")
                    modal_appeared = True
                    break
            except:
                continue
        
        if modal_appeared:
            utils.logger.info("登录弹窗已出现，等待二维码加载...")
            # 🎯 增加更长的等待时间，让二维码有足够时间加载和显示
            for wait_time in [2, 3, 5]:  # 逐步增加等待时间
                await asyncio.sleep(wait_time)
                utils.logger.info(f"等待二维码加载中... ({wait_time}s)")
                
                # 检查是否有二维码元素开始显示
                temp_qr_check = await page.query_selector(".Z2TvRaOX, img[aria-label='二维码']")
                if temp_qr_check:
                    is_visible = await temp_qr_check.is_visible()
                    utils.logger.info(f"检测到二维码元素，可见性: {is_visible}")
                    if is_visible:
                        break
        else:
            utils.logger.info("未明确检测到弹窗，继续查找二维码（可能页面结构不同）...")
        
        # 步骤3.5：详细检测页面验证码元素
        utils.logger.info("步骤3.5: 详细检测页面验证码元素...")
        
        # 🔍 详细分析页面上的所有可能元素
        utils.logger.info("🔍 开始详细分析页面上所有可能的验证码元素...")
        
        element_analysis = []
        captcha_detected = False
        captcha_element = None
        
        try:
            # 1. 获取所有包含验证码关键词的元素
            verification_keywords = ['验证', 'captcha', 'verify', '滑动', '拖拽', 'slide', 'slider', '点击完成验证', '身份验证', '安全验证', '请完成', 'security']
            
            utils.logger.info("🔍 第1步：搜索包含验证码关键词的元素...")
            for keyword in verification_keywords:
                try:
                    # 搜索包含关键词的元素
                    elements = await page.query_selector_all(f"*:has-text('{keyword}')")
                    if elements:
                        utils.logger.info(f"找到包含'{keyword}'的元素数量: {len(elements)}")
                        for i, elem in enumerate(elements[:3]):  # 只取前3个
                            try:
                                tag_name = await elem.evaluate("el => el.tagName")
                                class_name = await elem.get_attribute("class") or ""
                                elem_id = await elem.get_attribute("id") or ""
                                text_content = await elem.text_content()
                                is_visible = await elem.is_visible()
                                
                                element_info = {
                                    "keyword": keyword,
                                    "index": i,
                                    "tag": tag_name,
                                    "class": class_name,
                                    "id": elem_id,
                                    "text": text_content[:200] if text_content else "",
                                    "visible": is_visible
                                }
                                element_analysis.append(element_info)
                                
                                if is_visible and not captcha_detected:
                                    captcha_detected = True
                                    captcha_element = elem
                                    utils.logger.info(f"✅ 首次检测到可见验证码元素: {keyword}")
                                    
                            except Exception as e:
                                utils.logger.warning(f"分析元素失败: {e}")
                except Exception as e:
                    utils.logger.warning(f"搜索关键词'{keyword}'失败: {e}")
            
            # 2. 检查常见的验证码选择器
            utils.logger.info("🔍 第2步：检查常见验证码选择器...")
            common_selectors = [
                ".captcha", ".verify", ".verification", ".slide", ".slider",
                "[id*='captcha']", "[class*='captcha']", "[id*='verify']", "[class*='verify']",
                "[id*='slide']", "[class*='slide']", "[id*='slider']", "[class*='slider']",
                ".secsdk_captcha", ".sc-verification", ".verification-container",
                "div[class*='verify']", "div[class*='captcha']", "div[class*='slide']"
            ]
            
            for selector in common_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        utils.logger.info(f"选择器'{selector}'找到{len(elements)}个元素")
                        for i, elem in enumerate(elements[:2]):  # 只取前2个
                            try:
                                tag_name = await elem.evaluate("el => el.tagName")
                                class_name = await elem.get_attribute("class") or ""
                                elem_id = await elem.get_attribute("id") or ""
                                text_content = await elem.text_content()
                                is_visible = await elem.is_visible()
                                outer_html = await elem.evaluate("el => el.outerHTML.substring(0, 300)")
                                
                                element_info = {
                                    "selector": selector,
                                    "index": i,
                                    "tag": tag_name,
                                    "class": class_name,
                                    "id": elem_id,
                                    "text": text_content[:200] if text_content else "",
                                    "visible": is_visible,
                                    "html": outer_html
                                }
                                element_analysis.append(element_info)
                                
                                if is_visible and not captcha_detected:
                                    captcha_detected = True
                                    captcha_element = elem
                                    utils.logger.info(f"✅ 通过选择器检测到验证码元素: {selector}")
                                    
                            except Exception as e:
                                utils.logger.warning(f"分析选择器元素失败: {e}")
                except Exception as e:
                    utils.logger.warning(f"查询选择器'{selector}'失败: {e}")
            
            # 3. 检查所有iframe（验证码可能在iframe中）
            utils.logger.info("🔍 第3步：检查页面中的iframe...")
            try:
                iframes = await page.query_selector_all("iframe")
                if iframes:
                    utils.logger.info(f"发现{len(iframes)}个iframe")
                    for i, iframe in enumerate(iframes):
                        try:
                            src = await iframe.get_attribute("src") or ""
                            iframe_id = await iframe.get_attribute("id") or ""
                            iframe_class = await iframe.get_attribute("class") or ""
                            
                            element_info = {
                                "type": "iframe",
                                "index": i,
                                "id": iframe_id,
                                "class": iframe_class,
                                "src": src[:200],
                                "visible": await iframe.is_visible()
                            }
                            element_analysis.append(element_info)
                            
                        except Exception as e:
                            utils.logger.warning(f"分析iframe失败: {e}")
            except Exception as e:
                utils.logger.warning(f"查询iframe失败: {e}")
            
            # 4. 记录分析结果
            utils.logger.info(f"🔍 元素分析完成，共分析了{len(element_analysis)}个元素")
            
            # 将详细分析结果传递给前端
            session_data["element_analysis"] = element_analysis
            session_data["analysis_summary"] = f"共分析{len(element_analysis)}个可能的验证码元素"
            
        except Exception as e:
            utils.logger.error(f"详细元素分析失败: {e}")
            session_data["element_analysis"] = [{"error": f"分析失败: {str(e)}"}]
        
        if captcha_detected:
            utils.logger.info("🔍 发现验证码，准备返回给用户手动处理...")
            session_data["status"] = "captcha_required"
            session_data["message"] = "检测到验证码，请手动完成验证"
            session_data["progress"] = 45
            
            # 保存当前页面URL供原始页面嵌入使用
            current_url = page.url
            session_data["current_url"] = current_url
            utils.logger.info(f"✅ 验证码检测时保存当前页面URL: {current_url}")
            
            try:
                # 截取整个页面，包含验证码
                captcha_screenshot = await page.screenshot()
                captcha_base64 = base64.b64encode(captcha_screenshot).decode()
                session_data["captcha_screenshot"] = f"data:image/png;base64,{captcha_base64}"
                
                # 🎯 保存完整的HTML页面到文件，供离线分析
                utils.logger.info("💾 保存页面HTML到文件供离线分析...")
                try:
                    # 获取完整的页面HTML
                    page_html = await page.content()
                    
                    # 添加分析提示和样式到HTML顶部
                    page_url = page.url
                    analysis_header = f"""
                    <div style="position: fixed; top: 0; left: 0; width: 100%; background: #ff6b6b; color: white; padding: 10px; z-index: 9999; font-family: Arial; font-size: 14px; text-align: center;">
                        🔍 <strong>抖音验证码页面分析</strong> - 原始URL: {page_url}<br>
                        请使用浏览器开发者工具（F12）查找验证码/滑块元素，重点寻找：包含"slide"、"slider"、"captcha"、"verify"、"拖拽"、"滑动"等关键词的元素
                    </div>
                    <style>
                        body {{ margin-top: 80px !important; }}
                        .captcha-highlight {{ border: 3px solid red !important; background: yellow !important; }}
                        /* 高亮可能的验证码元素 */
                        [class*="slide"], [class*="slider"], [class*="captcha"], [class*="verify"] {{
                            outline: 2px dashed orange !important;
                            background-color: rgba(255, 165, 0, 0.1) !important;
                        }}
                        [id*="slide"], [id*="slider"], [id*="captcha"], [id*="verify"] {{
                            outline: 2px dashed red !important;
                            background-color: rgba(255, 0, 0, 0.1) !important;
                        }}
                    </style>
                    <script>
                        // 自动高亮可能的验证码元素
                        window.onload = function() {{
                            console.log('🔍 开始自动高亮可能的验证码元素...');
                            const keywords = ['slide', 'slider', 'captcha', 'verify', 'verification', '滑动', '拖拽', '验证'];
                            let foundElements = [];
                            
                            keywords.forEach(keyword => {{
                                // 查找文本包含关键词的元素
                                const walker = document.createTreeWalker(
                                    document.body,
                                    NodeFilter.SHOW_TEXT,
                                    null,
                                    false
                                );
                                
                                let node;
                                while (node = walker.nextNode()) {{
                                    if (node.textContent.toLowerCase().includes(keyword.toLowerCase())) {{
                                        const element = node.parentElement;
                                        if (element && !foundElements.includes(element)) {{
                                            element.style.border = '3px solid lime';
                                            element.style.backgroundColor = 'rgba(0, 255, 0, 0.2)';
                                            foundElements.push(element);
                                            console.log(`找到包含"${{keyword}}"的元素:`, element);
                                        }}
                                    }}
                                }}
                            }});
                            
                            console.log(`总共高亮了 ${{foundElements.length}} 个可能的验证码元素`);
                        }};
                    </script>
                    """
                    
                    # 在HTML的head或body标签后插入分析头部
                    if '<body' in page_html:
                        page_html = page_html.replace('<body', analysis_header + '<body')
                    elif '<html' in page_html:
                        page_html = page_html.replace('<html', analysis_header + '<html')
                    else:
                        page_html = analysis_header + page_html
                    
                    # 生成文件名（包含时间戳）
                    import os
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"douyin_captcha_page_{timestamp}.html"
                    
                    # 保存到项目根目录下的debug文件夹
                    debug_dir = "debug"
                    if not os.path.exists(debug_dir):
                        os.makedirs(debug_dir)
                    
                    file_path = os.path.join(debug_dir, filename)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    
                    utils.logger.info(f"✅ 页面HTML已保存到: {file_path}")
                    session_data["saved_html_file"] = file_path
                    session_data["analysis_instruction"] = f"页面HTML已保存到 {file_path}，请用浏览器打开此文件，使用F12开发者工具查找验证码元素"
                    
                except Exception as e:
                    utils.logger.error(f"保存HTML文件失败: {e}")
                    session_data["html_save_error"] = f"保存失败: {str(e)}"
                
                # 获取验证码区域的位置信息
                if captcha_element:
                    captcha_box = await captcha_element.bounding_box()
                    if captcha_box:
                        session_data["captcha_area"] = {
                            "x": captcha_box["x"],
                            "y": captcha_box["y"], 
                            "width": captcha_box["width"],
                            "height": captcha_box["height"]
                        }
                        utils.logger.info(f"验证码区域位置: {captcha_box}")
                
                utils.logger.info("✅ 验证码截图已生成，等待用户手动处理")
                
                # 等待用户完成验证码（最多等待5分钟）
                utils.logger.info("等待用户完成验证码验证...")
                max_wait_captcha = 300  # 5分钟
                check_interval = 2
                
                # 🔧 修复：定义验证码选择器列表
                captcha_selectors = [
                    ".captcha", ".verify", ".verification", ".slide", ".slider",
                    "[id*='captcha']", "[class*='captcha']", "[id*='verify']", "[class*='verify']",
                    "[id*='slide']", "[class*='slide']", "#captcha_container"
                ]
                
                # 🎯 新方案：提取验证码数据供前端复刻
                try:
                    utils.logger.info("🎨 提取验证码数据，准备在前端复刻...")
                    captcha_data = await extract_captcha_data(page)
                    
                    if captcha_data.get("success"):
                        utils.logger.info("✅ 验证码数据提取成功")
                        session_data["captcha_data"] = captcha_data
                        session_data["status"] = "captcha_required_with_data"
                        session_data["message"] = "验证码已检测，请在下方完成滑动验证"
                        session_data["progress"] = 52
                        
                        # 等待用户在前端完成滑动并回传轨迹
                        utils.logger.info("等待用户在前端完成滑动验证...")
                        max_wait_captcha = 300  # 5分钟
                        check_interval = 2
                        
                        for i in range(max_wait_captcha // check_interval):
                            await asyncio.sleep(check_interval)
                            
                            # 检查是否收到用户滑动轨迹
                            if "slide_path" in session_data and session_data.get("replay_status") == "ready":
                                utils.logger.info("🎮 收到用户滑动轨迹，开始回放...")
                                slide_path = session_data["slide_path"]
                                
                                # 回放用户滑动轨迹
                                replay_success = await replay_slide_path(page, slide_path, session_data)
                                
                                if replay_success:
                                    utils.logger.info("🎉 验证码验证成功，继续登录流程")
                                    session_data["status"] = "captcha_completed"
                                    session_data["message"] = "验证码验证成功，继续登录流程"
                                    session_data["progress"] = 55
                                    break
                                else:
                                    utils.logger.warning("⚠️ 轨迹回放失败，请重试")
                                    session_data["status"] = "captcha_required_with_data"
                                    session_data["message"] = "验证失败，请重新滑动验证码"
                                    # 清除失败的轨迹，允许重试
                                    session_data.pop("slide_path", None)
                                    session_data.pop("replay_status", None)
                            
                            # 检查验证码是否自然消失（用户可能直接在原页面操作了）
                            still_has_captcha = False
                            for selector in captcha_selectors:
                                try:
                                    element = await page.query_selector(selector)
                                    if element and await element.is_visible():
                                        element_text = await element.text_content() if element else ""
                                        element_html = await element.inner_html() if element else ""
                                        captcha_keywords = ["验证", "captcha", "verify", "滑动", "点击", "拖拽"]
                                        if any(keyword in (element_text + element_html).lower() for keyword in captcha_keywords):
                                            still_has_captcha = True
                                            break
                                except:
                                    continue
                            
                            if not still_has_captcha:
                                utils.logger.info("✅ 验证码已自然消失，验证完成！")
                                session_data["status"] = "captcha_completed"
                                session_data["message"] = "验证码验证完成，继续登录流程"
                                session_data["progress"] = 55
                                break
                            
                            if i % 15 == 0:  # 每30秒更新一次状态
                                utils.logger.info(f"等待用户完成验证码... ({i*check_interval}/{max_wait_captcha}s)")
                                session_data["message"] = f"等待验证码验证... ({i*check_interval}s)"
                        
                        # 检查是否超时
                        if "slide_path" not in session_data and still_has_captcha:
                            utils.logger.warning("验证码处理超时")
                            session_data["status"] = "captcha_timeout"
                            session_data["message"] = "验证码处理超时，请重新尝试"
                            return
                    else:
                        utils.logger.warning("❌ 验证码数据提取失败，使用传统截图方式")
                        session_data["status"] = "captcha_required"
                        session_data["message"] = "检测到验证码，请查看截图"
                        
                except Exception as e:
                    utils.logger.error(f"❌ 验证码数据提取失败: {e}")
                    session_data["status"] = "captcha_required"
                    session_data["message"] = "检测到验证码，请查看截图"
                
                # 如果验证码处理失败，继续原有的等待流程
                max_wait_captcha = 300  # 5分钟
                check_interval = 2
                
                for i in range(max_wait_captcha // check_interval):
                    await asyncio.sleep(check_interval)
                    
                    # 检查验证码是否消失（验证完成）
                    still_has_captcha = False
                    for selector in captcha_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                element_text = await element.text_content() if element else ""
                                element_html = await element.inner_html() if element else ""
                                captcha_keywords = ["验证", "captcha", "verify", "滑动", "点击", "拖拽", "安全验证", "身份验证", "请使用", "扫码验证"]
                                if any(keyword in (element_text + element_html).lower() for keyword in captcha_keywords):
                                    still_has_captcha = True
                                    break
                        except:
                            continue
                    
                    if not still_has_captcha:
                        utils.logger.info("✅ 验证码已消失，用户验证完成！")
                        session_data["status"] = "captcha_completed"
                        session_data["message"] = "验证码验证完成，继续登录流程"
                        session_data["progress"] = 55
                        break
                    
                    if i % 15 == 0:  # 每30秒打印一次状态
                        utils.logger.info(f"等待验证码完成中... ({i*check_interval}/{max_wait_captcha}s)")
                        # 更新截图，显示当前状态
                        try:
                            current_screenshot = await page.screenshot()
                            current_base64 = base64.b64encode(current_screenshot).decode()
                            session_data["captcha_screenshot"] = f"data:image/png;base64,{current_base64}"
                        except:
                            pass
                
                # 如果超时还有验证码
                if still_has_captcha:
                    utils.logger.warning("验证码处理超时")
                    session_data["status"] = "captcha_timeout"
                    session_data["message"] = "验证码处理超时，请重新尝试"
                    return
                    
            except Exception as e:
                utils.logger.error(f"处理验证码时出错: {e}")
                session_data["status"] = "error"
                session_data["message"] = f"验证码处理失败: {str(e)}"
                return
        else:
            utils.logger.info("✅ 未检测到验证码，继续正常流程")
            
        # 🎯 无论是否检测到验证码，都保存HTML页面供分析（因为我们可能漏检）
        utils.logger.info("💾 保存当前页面HTML供离线分析...")
        try:
            page_html = await page.content()
            
            # 添加分析提示
            page_url = page.url
            analysis_header = f"""
            <div style="position: fixed; top: 0; left: 0; width: 100%; background: #17a2b8; color: white; padding: 10px; z-index: 9999; font-family: Arial; font-size: 14px; text-align: center;">
                🔍 <strong>抖音登录页面完整快照</strong> - 原始URL: {page_url}<br>
                如果存在验证码但未被自动检测到，请手动查找验证码元素
            </div>
            <style>
                body {{ margin-top: 80px !important; }}
                [class*="slide"], [class*="slider"], [class*="captcha"], [class*="verify"] {{
                    outline: 2px dashed orange !important;
                    background-color: rgba(255, 165, 0, 0.1) !important;
                }}
            </style>
            """
            
            if '<body' in page_html:
                page_html = page_html.replace('<body', analysis_header + '<body')
            else:
                page_html = analysis_header + page_html
            
            # 生成文件名
            import os
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"douyin_login_page_{timestamp}.html"
            
            debug_dir = "debug"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            file_path = os.path.join(debug_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            utils.logger.info(f"✅ 页面HTML快照已保存到: {file_path}")
            session_data["backup_html_file"] = file_path
            
        except Exception as e:
            utils.logger.error(f"保存页面HTML快照失败: {e}")
        
        # 步骤4：拦截二维码API请求
        utils.logger.info("步骤4: 拦截二维码API请求...")
        session_data["status"] = "waiting_for_qrcode" 
        session_data["message"] = "正在拦截二维码请求..."
        session_data["progress"] = 60
        
        qr_element = None
        qr_code_from_api = None
        
        # 🎯 新方法：拦截网络请求获取二维码API响应
        utils.logger.info("监听二维码API请求...")
        
        # 设置网络请求拦截
        intercepted_data = {}
        
        def handle_response(response):
            url = response.url
            if "get_qrcode" in url and "login.douyin.com" in url:
                utils.logger.info(f"✅ 拦截到二维码API请求: {url}")
                # 记录响应数据
                intercepted_data['qrcode_response'] = response
        
        # 开始监听网络响应
        page.on("response", handle_response)
        
        # 等待API请求被触发（最多等待20秒）
        utils.logger.info("等待二维码API请求...")
        max_wait = 20
        for i in range(max_wait):
            await asyncio.sleep(1)
            if 'qrcode_response' in intercepted_data:
                utils.logger.info("✅ 成功拦截到二维码API响应")
                
                try:
                    # 获取响应JSON数据
                    response_data = await intercepted_data['qrcode_response'].json()
                    utils.logger.info("✅ 成功解析API响应JSON")
                    
                    # 提取二维码数据
                    if 'data' in response_data and 'qrcode' in response_data['data']:
                        qr_base64 = response_data['data']['qrcode']
                        if qr_base64:
                            utils.logger.info("✅ 从API响应中获取到二维码数据")
                            session_data["qr_code_data"] = f"data:image/png;base64,{qr_base64}"
                            qr_code_from_api = True
                            
                            # 记录token等信息
                            if 'token' in response_data['data']:
                                utils.logger.info(f"获取到登录token: {response_data['data']['token'][:20]}...")
                            if 'expire_time' in response_data['data']:
                                utils.logger.info(f"二维码过期时间: {response_data['data']['expire_time']}")
                            
                            break
                        else:
                            utils.logger.warning("API响应中qrcode字段为空")
                    else:
                        utils.logger.warning("API响应中没有找到qrcode字段")
                        utils.logger.info(f"响应数据结构: {response_data.keys() if isinstance(response_data, dict) else 'not dict'}")
                        
                except Exception as e:
                    utils.logger.error(f"解析API响应失败: {e}")
                    break
            
            if i % 5 == 0:
                utils.logger.info(f"等待API请求中... ({i+1}/{max_wait}s)")
        
        # 停止监听
        page.remove_listener("response", handle_response)
        
        # 如果API方法成功，跳过页面元素查找
        if qr_code_from_api:
            utils.logger.info("✅ API方法成功获取二维码，跳过页面元素查找")
        else:
            utils.logger.info("⚠️ API方法失败，回退到页面元素查找...")
            
            # 🎯 备选方法：基于日志发现的真实情况查找页面元素
            utils.logger.info("查找 class='pzLxv91N' 二维码元素...")
            
            # 第一次尝试：查找真实的二维码class
            try:
                qr_element = await page.wait_for_selector(".pzLxv91N", timeout=10000)
                if qr_element and await qr_element.is_visible():
                    utils.logger.info("✅ 找到可见的 .pzLxv91N 二维码元素")
                else:
                    utils.logger.info("⚠️ 找到 .pzLxv91N 元素但不可见，等待其显示...")
                    qr_element = None
            except Exception as e:
                utils.logger.error(f"未找到 .pzLxv91N 元素: {e}")
                qr_element = None
            
            # 第二次尝试：等待隐藏的二维码变为可见
            if not qr_element:
                utils.logger.info("等待隐藏的二维码元素变为可见...")
                for retry in range(5):  # 重试5次，每次等待3秒
                    await asyncio.sleep(3)
                    utils.logger.info(f"重试 {retry + 1}/5: 检查二维码是否可见...")
                    
                    try:
                        hidden_qr = await page.query_selector(".pzLxv91N")
                        if hidden_qr and await hidden_qr.is_visible():
                            utils.logger.info("✅ 隐藏的二维码元素现在可见了!")
                            qr_element = hidden_qr
                            break
                        else:
                            utils.logger.info(f"   二维码仍然隐藏，继续等待...")
                    except:
                        continue
            
            # 第三次尝试：作为备选，查找aria-label="二维码"
            if not qr_element:
                utils.logger.info("备选方案：查找 aria-label='二维码' 元素...")
                try:
                    qr_element = await page.query_selector("img[aria-label='二维码']")
                    if qr_element and await qr_element.is_visible():
                        utils.logger.info("✅ 备选方案成功：找到 aria-label='二维码' 元素")
                    else:
                        qr_element = None
                except:
                    qr_element = None
        
        # 如果所有方法都失败了，报错
        if not qr_code_from_api and not qr_element:
            utils.logger.error("❌ API拦截和页面元素查找都失败了")
            
            # 生成调试截图
            try:
                debug_screenshot = await page.screenshot()
                debug_base64 = base64.b64encode(debug_screenshot).decode()
                session_data["debug_screenshot"] = f"data:image/png;base64,{debug_base64}"
                utils.logger.info(f"已生成调试截图，大小: {len(debug_screenshot)} bytes")
            except Exception as e:
                utils.logger.error(f"生成调试截图失败: {e}")
            
            session_data["status"] = "error"
            session_data["message"] = "无法获取二维码（API拦截和页面元素都失败）"
            session_data["progress"] = 0
            return
        
        # 步骤5：生成二维码图片
        utils.logger.info("步骤5: 生成二维码图片...")
        
        # 如果从API获取到了二维码数据，跳过页面截图
        if qr_code_from_api:
            utils.logger.info("✅ 已从API获取二维码数据，无需页面截图")
        elif qr_element:
            # 从页面元素截图生成二维码
            try:
                utils.logger.info("截取二维码元素...")
                qr_screenshot = await qr_element.screenshot()
                qr_base64 = base64.b64encode(qr_screenshot).decode()
                session_data["qr_code_data"] = f"data:image/png;base64,{qr_base64}"
                utils.logger.info("✅ 页面元素截图生成二维码成功")
                
            except Exception as e:
                utils.logger.error(f"❌ 生成二维码图片失败: {e}")
                session_data["status"] = "error"
                session_data["message"] = f"生成二维码失败: {str(e)}"
                return
        else:
            utils.logger.error("❌ 既没有API二维码数据，也没有页面元素")
            session_data["status"] = "error"
            session_data["message"] = "无法获取二维码数据"
            return
        
        # 更新状态
        session_data["status"] = "qr_code_ready"
        session_data["message"] = "二维码已生成，请使用抖音APP扫码登录"
        session_data["progress"] = 80
        
        # 等待登录成功
        max_wait_time = 120  # 最多等待2分钟
        check_interval = 2   # 每2秒检查一次
        
        utils.logger.info("开始监控抖音登录状态...")
        
        for i in range(max_wait_time // check_interval):
            await asyncio.sleep(check_interval)
            
            try:
                # 检查当前页面URL
                current_url = page.url
                
                # 检查localStorage中的登录状态
                has_user_login = await page.evaluate("() => window.localStorage.getItem('HasUserLogin')")
                
                # 检查cookies
                current_cookies = await browser_context.cookies()
                cookie_dict = {}
                for cookie in current_cookies:
                    cookie_dict[cookie['name']] = cookie['value']
                
                login_status = cookie_dict.get('LOGIN_STATUS', '')
                ttwid = cookie_dict.get('ttwid', '')
                passport_csrf_token = cookie_dict.get('passport_csrf_token', '')
                
                # 更严格的登录状态判断
                is_logged_in = False
                login_indicators = []
                
                # 检查多个条件，需要满足多个才认为真正登录
                if has_user_login == "1":
                    login_indicators.append("localStorage_HasUserLogin")
                    utils.logger.info("✓ localStorage中HasUserLogin=1")
                
                if login_status == "1":
                    login_indicators.append("cookie_LOGIN_STATUS")
                    utils.logger.info("✓ Cookie中LOGIN_STATUS=1")
                
                if ttwid and len(ttwid) > 10:
                    login_indicators.append("cookie_ttwid")
                    utils.logger.info(f"✓ 检测到ttwid cookie: {ttwid[:10]}...")
                
                if passport_csrf_token:
                    login_indicators.append("cookie_csrf_token")
                    utils.logger.info("✓ 检测到passport_csrf_token")
                
                # 检查URL是否跳转到登录后的页面
                if any(keyword in current_url.lower() for keyword in ["user", "profile", "creator", "home"]):
                    if "login" not in current_url.lower():  # 确保不是登录页面
                        login_indicators.append("url_redirect")
                        utils.logger.info(f"✓ URL跳转到登录后页面: {current_url}")
                
                # 需要至少2个指标才认为登录成功，避免误判
                if len(login_indicators) >= 2:
                    utils.logger.info(f"✅ 登录成功！满足{len(login_indicators)}个条件: {', '.join(login_indicators)}")
                    is_logged_in = True
                else:
                    utils.logger.debug(f"登录检测中... 当前满足条件: {login_indicators}")
                    is_logged_in = False
                
                if is_logged_in:
                    session_data["status"] = "logged_in"
                    session_data["message"] = "抖音登录成功！"
                    session_data["progress"] = 100
                    
                    # 保存登录凭证
                    await save_login_cookies(session_id, current_cookies, "dy")
                    utils.logger.info("抖音登录成功，已保存登录凭证")
                    return
                
                # 检查二维码是否过期
                try:
                    expired_element = await page.query_selector("text=二维码已过期")
                    if expired_element:
                        utils.logger.info("检测到二维码过期")
                        session_data["status"] = "qr_expired"
                        session_data["message"] = "二维码已过期，请刷新重试"
                        return
                except:
                    pass
                
            except Exception as e:
                utils.logger.error(f"检查登录状态时出错: {e}")
        
        # 超时未登录
        session_data["status"] = "timeout"
        session_data["message"] = "登录超时，请重新尝试"
        session_data["progress"] = 0
        
    except Exception as e:
        utils.logger.error(f"抖音登录失败: {e}")
        session_data["status"] = "error"
        session_data["message"] = f"登录失败: {str(e)}"
        session_data["progress"] = 0
        # 新增：异常后立即释放远程桌面锁
        if session_data.get("has_desktop_lock"):
            await remote_desktop_lock.release(session_id)
            session_data["has_desktop_lock"] = False

async def handle_bilibili_login(session_id: str, browser_context, page):
    """处理B站登录"""
    session_data = login_sessions[session_id]
    
    try:
        utils.logger.info(f"📺 [B站] 开始增强登录流程")
        
        # 尝试访问B站登录页面
        await page.goto("https://passport.bilibili.com/login", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        page_title = await page.title()
        utils.logger.info(f"📺 [B站] 页面标题: {page_title}")
        
        # 检查是否有浏览器版本过低的提示
        page_content = await page.content()
        version_warnings = [
            "浏览器版本过低",
            "browser version",
            "不支持您的浏览器",
            "Please upgrade"
        ]
        
        has_version_issue = any(warning in page_content for warning in version_warnings)
        
        if has_version_issue:
            utils.logger.warning(f"📺 [B站] 检测到浏览器版本问题，已使用最新User-Agent")
            session_data["message"] = "B站检测到浏览器版本，已优化配置..."
            
            # 尝试刷新页面
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            page_content = await page.content()
        
        # 检查登录页面是否正常加载
        if "登录" in page_content or "login" in page_content.lower():
            utils.logger.info(f"✅ [B站] 登录页面加载成功")
            session_data["status"] = "qrcode_ready"
            session_data["message"] = "B站登录页面已加载，请完成登录"
            session_data["progress"] = 50
        else:
            utils.logger.error(f"❌ [B站] 页面加载异常")
            session_data["status"] = "error"
            session_data["message"] = "B站页面加载异常，请重试"
            
    except Exception as e:
        utils.logger.error(f"📺 [B站] 登录处理失败: {e}")
        session_data["status"] = "error"
        session_data["message"] = f"B站登录失败: {str(e)}"

async def handle_weibo_login(session_id: str, browser_context, page):
    """处理微博登录"""
    session_data = login_sessions[session_id]
    session_data["status"] = "error"
    session_data["message"] = "微博登录功能暂未实现"
    utils.logger.warning("微博登录功能暂未实现")

async def handle_kuaishou_login(session_id: str, browser_context, page):
    """处理快手登录"""
    session_data = login_sessions[session_id]
    
    try:
        utils.logger.info(f"🎬 [快手] 开始增强登录流程")
        
        # 尝试直接访问快手主页
        await page.goto("https://www.kuaishou.com/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        page_title = await page.title()
        utils.logger.info(f"🎬 [快手] 页面标题: {page_title}")
        
        # 检查是否有 result:2 错误
        page_content = await page.content()
        if '"result":2' in page_content or 'result":2' in page_content:
            utils.logger.warning(f"🎬 [快手] 检测到result:2错误，使用增强配置重试")
            session_data["message"] = "快手检测到自动化，正在尝试解决..."
            
            # 刷新页面重试
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            page_content = await page.content()
        
        if '"result":2' in page_content:
            utils.logger.error(f"❌ [快手] 仍然检测到result:2错误")
            session_data["status"] = "error"
            session_data["message"] = "快手检测到自动化，请稍后重试"
            return
            
        utils.logger.info(f"✅ [快手] 页面加载成功，开始优化显示")
        
        # 优化页面显示比例
        try:
            await page.evaluate("""
                // 设置页面缩放，优化远程桌面显示
                document.body.style.zoom = '0.8';
                document.body.style.transform = 'scale(0.8)';
                document.body.style.transformOrigin = 'top left';
                
                // 确保页面内容可见
                document.body.style.maxWidth = '1260px';
                document.body.style.overflow = 'auto';
                
                // 添加快手专用提示
                const notice = document.createElement('div');
                notice.innerHTML = '🎬 快手页面已优化显示，比例调整为80%';
                notice.style.cssText = `
                    position: fixed; top: 10px; right: 10px; 
                    background: #FF6B35; color: white; 
                    padding: 8px 12px; border-radius: 5px; 
                    font-size: 12px; z-index: 10000;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                `;
                document.body.appendChild(notice);
                
                // 3秒后隐藏提示
                setTimeout(() => {
                    if (notice) notice.style.display = 'none';
                }, 3000);
            """)
            utils.logger.info("✅ [快手] 页面显示优化完成")
        except Exception as e:
            utils.logger.warning(f"⚠️ [快手] 页面缩放设置失败: {e}")
        
        # 查找登录按钮
        session_data["status"] = "finding_login_button"
        session_data["message"] = "正在查找登录按钮..."
        session_data["progress"] = 30
        
        login_selectors = [
            ".header-login",
            ".user-login", 
            ".login-btn",
            "text=登录",
            "button:has-text('登录')",
            "[data-test='login-button']",
            ".right-content .login",
            "xpath=//button[contains(text(),'登录')]",
            "xpath=//a[contains(text(),'登录')]",
            ".nav-login"
        ]
        
        login_clicked = False
        for selector in login_selectors:
            try:
                utils.logger.info(f"🎬 [快手] 尝试选择器: {selector}")
                login_element = await page.wait_for_selector(selector, timeout=2000)
                if login_element and await login_element.is_visible():
                    await login_element.click()
                    utils.logger.info(f"✅ [快手] 登录按钮点击成功: {selector}")
                    login_clicked = True
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                utils.logger.debug(f"选择器失败 {selector}: {e}")
                continue
        
        if not login_clicked:
            utils.logger.warning(f"⚠️ [快手] 未找到登录按钮，尝试继续流程")
        
        # 获取登录前的cookies
        initial_cookies = await browser_context.cookies()
        initial_cookie_count = len(initial_cookies)
        utils.logger.info(f"🎬 [快手] 初始cookies数量: {initial_cookie_count}")
        
        # 等待登录完成
        session_data["status"] = "waiting_for_login"
        session_data["message"] = "请在页面中完成快手登录"
        session_data["progress"] = 50
        
        max_wait_time = 300  # 5分钟
        check_interval = 3   # 3秒检查一次
        
        for i in range(max_wait_time // check_interval):
            await asyncio.sleep(check_interval)
            
            try:
                # 获取当前cookies
                current_cookies = await browser_context.cookies()
                current_url = page.url
                
                # 更新状态
                elapsed_time = i * check_interval
                session_data["message"] = f"等待快手登录... ({elapsed_time}s)"
                
                # 检查登录成功的标志
                login_detected = await detect_kuaishou_login_success(current_cookies, current_url, page)
                
                if login_detected:
                    utils.logger.info(f"🎉 [快手] 检测到登录成功！cookies数量: {len(current_cookies)}")
                    
                    session_data["status"] = "logged_in"
                    session_data["message"] = "快手登录成功！"
                    session_data["progress"] = 100
                    
                    # 保存登录凭证
                    await save_login_cookies(session_id, current_cookies, "ks")
                    utils.logger.info("🎬 [快手] 登录成功，已保存登录凭证")
                    return
                
                # 每30秒记录一次状态
                if i % 10 == 0:
                    utils.logger.info(f"🎬 [快手] 等待登录中... {elapsed_time}s, URL: {current_url}")
                    
            except Exception as e:
                utils.logger.warning(f"🎬 [快手] 检查登录状态时出错: {e}")
                continue
        
        # 超时
        session_data["status"] = "timeout"
        session_data["message"] = "快手登录超时，请重新尝试"
        session_data["progress"] = 0
        
    except Exception as e:
        utils.logger.error(f"🎬 [快手] 登录处理失败: {e}")
        session_data["status"] = "error"
        session_data["message"] = f"快手登录失败: {str(e)}"

async def detect_kuaishou_login_success(cookies: list, current_url: str, page) -> bool:
    """检测快手登录是否成功（宽松模式 - 临时调整）"""
    try:
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        login_indicators = []
        
        # 打印所有cookies用于调试
        utils.logger.info(f"🔍 [快手专用调试] 所有cookies ({len(cookie_dict)}个):")
        for name, value in cookie_dict.items():
            utils.logger.info(f"   - {name}: {value[:30]}..." if len(value) > 30 else f"   - {name}: {value}")
        
        # 1. 检查核心认证cookies（降低要求：主要检查passToken）
        core_auth_cookies = {
            'passToken': '认证token',
            'userId': '用户ID'
        }
        
        core_found = 0
        missing_core = []
        for cookie_name, description in core_auth_cookies.items():
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) > 10:  # 确保有实际内容
                    login_indicators.append(f"核心_{cookie_name}")
                    core_found += 1
                    utils.logger.info(f"✅ [快手] 核心认证cookie {cookie_name}: {cookie_value[:20]}...")
                else:
                    utils.logger.warning(f"⚠️ [快手] 核心cookie {cookie_name} 值太短: {cookie_value}")
                    missing_core.append(f"{cookie_name}(值太短)")
            else:
                utils.logger.warning(f"⚠️ [快手] 核心cookie {cookie_name} 不存在")
                missing_core.append(f"{cookie_name}(不存在)")
        
        # 2. 检查会话cookies
        session_cookies = [
            'kuaishou.server.webday7_st',
            'kuaishou.server.webday7_ph'
        ]
        
        session_found = 0
        for cookie_name in session_cookies:
            if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                cookie_value = cookie_dict[cookie_name]
                if len(cookie_value) > 20:  # 会话token通常较长
                    login_indicators.append(f"会话_{cookie_name}")
                    session_found += 1
                    utils.logger.info(f"✅ [快手] 会话cookie {cookie_name}: {cookie_value[:30]}...")
        
        # 3. 临时降低要求：只要有passToken和至少一个会话cookie就认为登录成功
        passToken_exists = 'passToken' in cookie_dict and len(cookie_dict['passToken']) > 10
        
        if passToken_exists and session_found >= 1:
            utils.logger.info(f"🎉 [快手] 登录检测成功！passToken存在 + 会话({session_found}) + 其他({len(login_indicators) - 1 - session_found})")
            if missing_core:
                utils.logger.warning(f"⚠️ [快手] 注意: 缺少以下核心cookies: {missing_core}")
            utils.logger.info(f"   所有指标: {', '.join(login_indicators)}")
            return True
        else:
            utils.logger.debug(f"🎬 [快手] 登录检测中... passToken: {passToken_exists}, 会话({session_found})")
            if missing_core:
                utils.logger.debug(f"   缺少核心cookies: {missing_core}")
            return False
            
    except Exception as e:
        utils.logger.error(f"🎬 [快手] 登录检测失败: {e}")
        return False

async def handle_tieba_login(session_id: str, browser_context, page):
    """处理贴吧登录"""
    session_data = login_sessions[session_id]
    session_data["status"] = "error"
    session_data["message"] = "贴吧登录功能暂未实现"
    utils.logger.warning("贴吧登录功能暂未实现")

async def handle_zhihu_login(session_id: str, browser_context, page):
    """处理知乎登录"""
    session_data = login_sessions[session_id]
    session_data["status"] = "error"
    session_data["message"] = "知乎登录功能暂未实现"
    utils.logger.warning("知乎登录功能暂未实现")

def generate_mock_qrcode() -> str:
    """生成模拟二维码数据"""
    # 这里应该生成真实的二维码图片并转换为base64
    # 暂时返回一个包含登录信息的模拟二维码
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        # 生成二维码内容
        qr_content = f"https://example.com/login?session_id={uuid.uuid4()}&platform=xhs&timestamp={datetime.now().timestamp()}"
        
        # 创建二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        # 生成图片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        utils.logger.info(f"生成二维码成功，内容: {qr_content}")
        return img_str
        
    except ImportError:
        utils.logger.warning("qrcode库未安装，使用简单占位符")
        # 返回一个简单的占位符图片
        mock_qr_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        return mock_qr_data
    except Exception as e:
        utils.logger.error(f"生成二维码失败: {e}")
        # 返回一个简单的占位符图片
        mock_qr_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        return mock_qr_data 

async def handle_slide_captcha(page):
    """
    自动处理滑块验证码
    """
    utils.logger.info("🎯 开始自动处理滑块验证码...")
    
    try:
        # 1. 等待验证码容器出现
        await page.wait_for_selector("#captcha_container", timeout=10000)
        utils.logger.info("✅ 检测到验证码容器")
        
        # 2. 检查是否有iframe
        iframe_selector = "#captcha_container iframe"
        iframe_count = await page.locator(iframe_selector).count()
        
        if iframe_count > 0:
            utils.logger.info("🔍 发现iframe验证码，切换到iframe内部")
            iframe = page.frame_locator(iframe_selector)
            
            # 在iframe中查找滑块元素
            slide_selectors = [
                ".slide-verify-slider",
                ".slider-btn", 
                ".slide-btn",
                ".slider",
                "[class*='slider']",
                "[class*='slide']",
                ".captcha-slider",
                ".verify-slider"
            ]
            
            slider_element = None
            track_element = None
            
            for selector in slide_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        slider_element = iframe.locator(selector).first
                        if await slider_element.is_visible():
                            utils.logger.info(f"✅ 找到滑块元素: {selector}")
                            break
                except:
                    continue
            
            if not slider_element:
                utils.logger.warning("❌ 未找到滑块元素")
                return False
            
            # 查找滑动轨道
            track_selectors = [
                ".slide-verify-track",
                ".slider-track",
                ".slide-track", 
                ".captcha-track",
                "[class*='track']"
            ]
            
            for selector in track_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        track_element = iframe.locator(selector).first
                        if await track_element.is_visible():
                            utils.logger.info(f"✅ 找到滑动轨道: {selector}")
                            break
                except:
                    continue
            
            # 3. 执行滑动操作
            await perform_slide_action(iframe, slider_element, track_element)
            
        else:
            utils.logger.info("🔍 在主页面中查找滑块验证码")
            # 在主页面中查找滑块
            slide_selectors = [
                ".slide-verify-slider",
                ".slider-btn", 
                ".slide-btn",
                ".slider",
                "[class*='slider']",
                "[class*='slide']"
            ]
            
            slider_element = None
            for selector in slide_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        slider_element = page.locator(selector).first
                        if await slider_element.is_visible():
                            utils.logger.info(f"✅ 找到滑块元素: {selector}")
                            break
                except:
                    continue
            
            if slider_element:
                await perform_slide_action(page, slider_element, None)
            else:
                utils.logger.warning("❌ 未找到滑块元素")
                return False
        
        utils.logger.info("✅ 滑块操作完成")
        return True
        
    except Exception as e:
        utils.logger.error(f"❌ 滑块验证码处理失败: {e}")
        return False

async def perform_slide_action(page_or_iframe, slider_element, track_element=None):
    """
    执行滑动操作
    """
    try:
        utils.logger.info("🎯 开始执行滑动操作...")
        
        # 获取滑块的位置和大小
        slider_box = await slider_element.bounding_box()
        if not slider_box:
            utils.logger.error("❌ 无法获取滑块位置")
            return False
        
        start_x = slider_box['x'] + slider_box['width'] / 2
        start_y = slider_box['y'] + slider_box['height'] / 2
        
        # 计算滑动距离
        if track_element:
            # 如果有轨道元素，滑动到轨道末端
            track_box = await track_element.bounding_box()
            if track_box:
                slide_distance = track_box['width'] - slider_box['width']
            else:
                slide_distance = 300  # 默认滑动距离
        else:
            # 尝试通过父元素计算滑动距离
            try:
                parent = slider_element.locator('..')
                parent_box = await parent.bounding_box()
                if parent_box:
                    slide_distance = parent_box['width'] - slider_box['width'] - 10
                else:
                    slide_distance = 280
            except:
                slide_distance = 280
        
        end_x = start_x + slide_distance
        end_y = start_y
        
        utils.logger.info(f"🎯 滑动参数: 起点({start_x:.1f}, {start_y:.1f}) -> 终点({end_x:.1f}, {end_y:.1f}), 距离: {slide_distance:.1f}px")
        
        # 移动到滑块并按下
        await page_or_iframe.mouse.move(start_x, start_y)
        await asyncio.sleep(0.1)
        await page_or_iframe.mouse.down()
        await asyncio.sleep(0.2)
        
        # 模拟人类滑动轨迹（分段滑动，添加随机抖动）
        steps = 15
        for i in range(steps + 1):
            progress = i / steps
            current_x = start_x + (end_x - start_x) * progress
            
            # 添加轻微的垂直抖动，模拟人类操作
            jitter_y = start_y + random.uniform(-2, 2)
            
            await page_or_iframe.mouse.move(current_x, jitter_y)
            await asyncio.sleep(random.uniform(0.02, 0.08))
        
        # 释放鼠标
        await asyncio.sleep(0.2)
        await page_or_iframe.mouse.up()
        await asyncio.sleep(1)
        
        utils.logger.info("✅ 滑动操作执行完成")
        return True
        
    except Exception as e:
        utils.logger.error(f"❌ 滑动操作失败: {e}")
        return False

async def extract_captcha_data(page):
    """
    提取验证码的完整数据，用于前端复刻
    """
    utils.logger.info("🎯 开始提取验证码数据...")
    
    try:
        # 等待验证码容器
        await page.wait_for_selector("#captcha_container", timeout=10000)
        
        # 检查iframe
        iframe_selector = "#captcha_container iframe"
        iframe_count = await page.locator(iframe_selector).count()
        
        captcha_data = {
            "type": "slide_captcha",
            "background_image": None,
            "slider_image": None,
            "slider_position": None,
            "track_width": None,
            "success": False
        }
        
        if iframe_count > 0:
            utils.logger.info("🔍 在iframe中提取验证码数据")
            iframe = page.frame_locator(iframe_selector)
            
            # 提取背景图片
            bg_selectors = [
                ".captcha-bg", ".verify-bg", ".slide-bg", 
                "img[class*='bg']", "img[class*='background']",
                ".captcha-image", "[class*='captcha'] img"
            ]
            
            for selector in bg_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        bg_element = iframe.locator(selector).first
                        if await bg_element.is_visible():
                            bg_src = await bg_element.get_attribute("src")
                            if bg_src and bg_src.startswith("data:image"):
                                captcha_data["background_image"] = bg_src
                                utils.logger.info(f"✅ 提取背景图: {selector}")
                                break
                except:
                    continue
            
            # 提取滑块图片
            slider_selectors = [
                ".slider-img", ".slide-img", ".captcha-slider img",
                ".slider img", "[class*='slider'] img"
            ]
            
            for selector in slider_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        slider_element = iframe.locator(selector).first
                        if await slider_element.is_visible():
                            slider_src = await slider_element.get_attribute("src")
                            if slider_src and slider_src.startswith("data:image"):
                                captcha_data["slider_image"] = slider_src
                                utils.logger.info(f"✅ 提取滑块图: {selector}")
                                break
                except:
                    continue
            
            # 获取滑动轨道宽度
            track_selectors = [
                ".slide-track", ".slider-track", ".captcha-track",
                "[class*='track']", ".verify-track"
            ]
            
            for selector in track_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        track_element = iframe.locator(selector).first
                        if await track_element.is_visible():
                            track_box = await track_element.bounding_box()
                            if track_box:
                                captcha_data["track_width"] = track_box["width"]
                                utils.logger.info(f"✅ 获取轨道宽度: {track_box['width']}px")
                                break
                except:
                    continue
            
            # 获取滑块初始位置
            slide_selectors = [
                ".slide-verify-slider", ".slider-btn", ".slide-btn",
                ".slider", "[class*='slider']"
            ]
            
            for selector in slide_selectors:
                try:
                    if await iframe.locator(selector).count() > 0:
                        slider_element = iframe.locator(selector).first
                        if await slider_element.is_visible():
                            slider_box = await slider_element.bounding_box()
                            if slider_box:
                                captcha_data["slider_position"] = {
                                    "x": slider_box["x"],
                                    "y": slider_box["y"],
                                    "width": slider_box["width"],
                                    "height": slider_box["height"]
                                }
                                utils.logger.info(f"✅ 获取滑块位置: {slider_box}")
                                break
                except:
                    continue
        
        # 如果没有提取到图片，尝试截取整个验证码区域
        if not captcha_data["background_image"]:
            utils.logger.info("🔄 截取整个验证码区域作为背景图")
            captcha_container = page.locator("#captcha_container")
            if await captcha_container.is_visible():
                screenshot_bytes = await captcha_container.screenshot()
                import base64
                captcha_data["background_image"] = f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode()}"
                captcha_data["track_width"] = 300  # 默认宽度
        
        if captcha_data["background_image"]:
            captcha_data["success"] = True
            utils.logger.info("✅ 验证码数据提取成功")
        else:
            utils.logger.warning("❌ 验证码数据提取失败")
        
        return captcha_data
        
    except Exception as e:
        utils.logger.error(f"❌ 提取验证码数据失败: {e}")
        return {"success": False, "error": str(e)}

@login_router.get("/login/captcha_data/{session_id}")
async def get_captcha_data(session_id: str):
    """
    获取验证码完整数据，用于前端复刻
    """
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    session_data = login_sessions[session_id]
    
    # 检查是否有验证码数据
    if "captcha_data" not in session_data:
        raise HTTPException(status_code=404, detail="验证码数据不存在")
    
    captcha_data = session_data["captcha_data"]
    
    return {
        "session_id": session_id,
        "success": captcha_data.get("success", False),
        "type": captcha_data.get("type", "slide_captcha"),
        "background_image": captcha_data.get("background_image"),
        "slider_image": captcha_data.get("slider_image"),
        "track_width": captcha_data.get("track_width", 300),
        "slider_position": captcha_data.get("slider_position"),
        "message": "验证码数据获取成功"
    }

@login_router.post("/login/replay_slide")
async def replay_slide_captcha(request: dict):
    """
    接收用户滑动轨迹并在原页面回放
    """
    session_id = request.get("session_id")
    slide_path = request.get("slide_path")  # 包含轨迹点的数组
    
    if not session_id or not slide_path:
        raise HTTPException(status_code=400, detail="缺少必要参数")
    
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    session_data = login_sessions[session_id]
    
    try:
        utils.logger.info(f"🎯 开始回放用户滑动轨迹，轨迹点数量: {len(slide_path)}")
        
        # 将轨迹存储到session_data，供后台处理
        session_data["slide_path"] = slide_path
        session_data["replay_status"] = "ready"
        session_data["message"] = "轨迹已接收，正在回放..."
        
        return {
            "success": True,
            "message": "滑动轨迹已接收，正在原页面回放验证码",
            "session_id": session_id,
            "path_points": len(slide_path)
        }
        
    except Exception as e:
        utils.logger.error(f"❌ 接收滑动轨迹失败: {e}")
        return {
            "success": False,
            "message": f"轨迹接收失败: {str(e)}",
            "session_id": session_id
        }

async def replay_slide_path(page, slide_path, session_data):
    """
    在原页面回放用户的滑动轨迹
    """
    try:
        utils.logger.info(f"🎯 开始在原页面回放滑动轨迹，共{len(slide_path)}个点")
        
        # 等待验证码容器
        await page.wait_for_selector("#captcha_container", timeout=10000)
        
        # 检查iframe
        iframe_selector = "#captcha_container iframe"
        iframe_count = await page.locator(iframe_selector).count()
        
        target_page = page
        if iframe_count > 0:
            utils.logger.info("🔍 在iframe中回放轨迹")
            target_page = page.frame_locator(iframe_selector)
        
        # 开始回放轨迹
        utils.logger.info("🎮 开始回放用户滑动轨迹...")
        
        # 移动到起始点
        start_point = slide_path[0]
        await target_page.mouse.move(start_point["x"], start_point["y"])
        await asyncio.sleep(0.1)
        
        # 按下鼠标
        await target_page.mouse.down()
        await asyncio.sleep(0.1)
        utils.logger.info(f"🖱️ 鼠标按下，起始点: ({start_point['x']}, {start_point['y']})")
        
        # 回放轨迹路径
        for i, point in enumerate(slide_path[1:], 1):
            try:
                await target_page.mouse.move(point["x"], point["y"])
                # 使用用户原始的时间间隔，或默认间隔
                delay = point.get("delay", 0.05)
                await asyncio.sleep(delay)
                
                if i % 5 == 0:  # 每5个点记录一次日志
                    utils.logger.info(f"🎯 回放进度: {i}/{len(slide_path)-1}, 当前点: ({point['x']}, {point['y']})")
                    
            except Exception as e:
                utils.logger.warning(f"⚠️ 回放点{i}失败: {e}")
                continue
        
        # 释放鼠标
        await target_page.mouse.up()
        await asyncio.sleep(0.5)
        utils.logger.info("🎉 滑动轨迹回放完成")
        
        # 更新状态
        session_data["replay_status"] = "completed"
        session_data["message"] = "轨迹回放完成，等待验证结果..."
        
        # 等待验证结果
        await asyncio.sleep(2)
        
        # 检查验证码是否消失（验证成功）
        captcha_still_exists = False
        try:
            if iframe_count > 0:
                iframe = page.frame_locator(iframe_selector)
                captcha_elements = await iframe.locator("#captcha_container, .captcha, .verify").count()
            else:
                captcha_elements = await page.locator("#captcha_container, .captcha, .verify").count()
            
            captcha_still_exists = captcha_elements > 0
        except:
            pass
        
        if not captcha_still_exists:
            utils.logger.info("✅ 验证码验证成功！")
            session_data["replay_status"] = "success"
            session_data["message"] = "验证码验证成功，继续登录流程"
            return True
        else:
            utils.logger.warning("⚠️ 验证码仍然存在，可能验证失败")
            session_data["replay_status"] = "failed"
            session_data["message"] = "验证可能失败，请重试"
            return False
            
    except Exception as e:
        utils.logger.error(f"❌ 轨迹回放失败: {e}")
        session_data["replay_status"] = "error"
        session_data["message"] = f"轨迹回放失败: {str(e)}"
        return False

@login_router.get("/login/current_page/{session_id}")
async def get_current_page_url(session_id: str):
    """
    获取当前登录页面的URL，用于前端嵌入
    """
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    session_data = login_sessions[session_id]
    
    return {
        "session_id": session_id,
        "current_url": session_data.get("current_url", "https://www.douyin.com"),
        "status": session_data.get("status", "unknown"),
        "message": "页面URL获取成功"
    }

@login_router.get("/login/wait_verification/{session_id}")
async def wait_for_verification(session_id: str):
    """等待浏览器验证完成"""
    try:
        if session_id not in login_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session_data = login_sessions[session_id]
        
        # 使用 login_manager 中的 wait_for_captcha_completion 方法
        from login_manager import login_manager
        
        result = await login_manager.wait_for_captcha_completion(session_id, timeout=10)
        
        return {
            "success": True,
            "session_id": session_id,
            "verification_completed": result.get("verification_completed", False),
            "login_status": result.get("login_status", "unknown"),
            "current_url": result.get("current_url", ""),
            "page_title": result.get("page_title", ""),
            "has_slider": result.get("has_slider", False),
            "message": result.get("message", ""),
            "timeout": result.get("timeout", False),
            "elapsed_time": result.get("elapsed_time", 0)
        }
    except Exception as e:
        utils.logger.error(f"等待验证失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "verification_completed": False,
            "timeout": False
        }

async def get_remote_desktop_info(session_data: dict) -> dict:
    """获取远程桌面服务信息"""
    try:
        # 从配置文件中获取远程桌面配置
        remote_desktop_config = config_manager.get_remote_desktop_config()
        
        if not remote_desktop_config.enabled:
            return {"available": False, "message": "远程桌面功能已禁用"}
        
        # 检查是否为需要远程桌面的状态
        status = session_data.get("status", "")
        # 扩展支持远程桌面的状态列表
        remote_desktop_statuses = [
            "captcha_required", 
            "captcha_required_with_data", 
            "need_verification",
            "remote_desktop_ready",    # 远程桌面准备就绪
            "waiting_user_login",      # 等待用户登录
            "opening_login_page",      # 正在打开登录页面
            "starting_browser",        # 正在启动浏览器
            "checking_remote_desktop", # 正在检查远程桌面
            "error"                    # 错误状态也应该提供远程桌面选项
        ]
        
        if status not in remote_desktop_statuses:
            return {"available": False, "message": "当前状态不需要远程桌面"}
        
        # 检查远程桌面服务是否可用
        import aiohttp
        import asyncio
        
        async def check_remote_desktop_service():
            try:
                timeout = aiohttp.ClientTimeout(total=remote_desktop_config.connection_timeout)
                check_url = f"http://{remote_desktop_config.vnc_host}:{remote_desktop_config.vnc_port}/vnc.html"
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(check_url) as response:
                        if response.status == 200:
                            return True
                        return False
            except:
                return False
        
        is_available = await check_remote_desktop_service()
        
        # 获取远程桌面锁状态
        lock_status = remote_desktop_lock.get_status()
        
        if is_available:
            if lock_status["is_locked"]:
                # 远程桌面被占用
                queue_length = lock_status["queue_length"]
                current_user = lock_status["session_info"].get("account_name", "其他用户")
                
                if queue_length > 0:
                    message = f"远程桌面正被 {current_user} 使用，队列中有 {queue_length} 人等待"
                else:
                    message = f"远程桌面正被 {current_user} 使用"
                
                return {
                    "available": True,
                    "url": remote_desktop_config.vnc_url,
                    "message": message,
                    "is_locked": True,
                    "current_user": current_user,
                    "queue_length": queue_length,
                    "can_join_queue": True
                }
            else:
                # 远程桌面空闲
                return {
                    "available": True,
                    "url": remote_desktop_config.vnc_url,
                    "message": "远程桌面服务可用，点击按钮打开",
                    "is_locked": False,
                    "current_user": None,
                    "queue_length": 0,
                    "can_join_queue": False
                }
        else:
            return {
                "available": False,
                "url": remote_desktop_config.vnc_url,
                "message": "远程桌面服务暂时不可用，请检查服务状态",
                "is_locked": lock_status["is_locked"],
                "current_user": lock_status["session_info"].get("account_name"),
                "queue_length": lock_status["queue_length"],
                "can_join_queue": False
            }
            
    except Exception as e:
        utils.logger.error(f"检查远程桌面服务失败: {e}")
        return {
            "available": False,
            "message": f"检查远程桌面服务失败: {str(e)}"
        }

@login_router.get("/login/remote_desktop/status")
async def get_remote_desktop_status():
    """获取远程桌面状态和队列信息"""
    try:
        lock_status = remote_desktop_lock.get_status()
        
        return {
            "success": True,
            "data": {
                "is_locked": lock_status["is_locked"],
                "current_session": lock_status["current_session"],
                "session_start_time": lock_status["session_start_time"],
                "current_user_info": lock_status["session_info"],
                "queue_length": lock_status["queue_length"],
                "waiting_sessions": lock_status["waiting_sessions"],
                "max_session_time_seconds": lock_status["max_session_time"]
            }
        }
    except Exception as e:
        utils.logger.error(f"获取远程桌面状态失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@login_router.post("/login/remote_desktop/force_release")
async def force_release_remote_desktop(session_id: str = None):
    """强制释放远程桌面锁（管理员功能）"""
    try:
        if session_id:
            # 释放指定会话
            success = await remote_desktop_lock.release(session_id)
            utils.logger.info(f"管理员强制释放远程桌面锁: {session_id}, 成功: {success}")
            
            # 更新会话状态
            if session_id in login_sessions:
                login_sessions[session_id]["status"] = "force_released"
                login_sessions[session_id]["message"] = "管理员强制释放了远程桌面访问权限"
                login_sessions[session_id]["has_desktop_lock"] = False
            
            return {
                "success": success,
                "message": f"{'成功' if success else '失败'}释放会话 {session_id}"
            }
        else:
            # 强制释放当前锁
            lock_status = remote_desktop_lock.get_status()
            current_session = lock_status.get("current_session")
            
            if current_session:
                await remote_desktop_lock._force_release()
                utils.logger.warning(f"管理员强制释放当前远程桌面会话: {current_session}")
                
                # 更新会话状态
                if current_session in login_sessions:
                    login_sessions[current_session]["status"] = "force_released"
                    login_sessions[current_session]["message"] = "管理员强制释放了远程桌面访问权限"
                    login_sessions[current_session]["has_desktop_lock"] = False
                
                return {
                    "success": True,
                    "message": f"成功强制释放当前会话 {current_session}"
                }
            else:
                return {
                    "success": True,
                    "message": "当前没有活动的远程桌面会话"
                }
                
    except Exception as e:
        utils.logger.error(f"强制释放远程桌面锁失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@login_router.post("/login/cancel/{session_id}")
async def cancel_login_session(session_id: str):
    """取消/终止登录会话"""
    try:
        utils.logger.info(f"🛑 用户请求取消登录会话: {session_id}")
        
        # 检查会话是否存在
        if session_id not in login_sessions:
            return {
                "success": False,
                "message": "登录会话不存在"
            }
        
        session_data = login_sessions[session_id]
        original_status = session_data.get("status", "unknown")
        
        utils.logger.info(f"   会话信息: 平台={session_data.get('platform')}, 状态={original_status}")
        
        # 1. 更新会话状态为已取消
        session_data["status"] = "cancelled"
        session_data["message"] = "用户主动取消登录"
        session_data["progress"] = 0
        session_data["cancelled_at"] = datetime.now().isoformat()
        session_data["cancelled_from_status"] = original_status
        
        cleanup_actions = []
        
        # 2. 释放远程桌面锁（如果有的话）
        has_desktop_lock = session_data.get("has_desktop_lock", False)
        if has_desktop_lock:
            try:
                lock_released = await remote_desktop_lock.release(session_id)
                if lock_released:
                    session_data["has_desktop_lock"] = False
                    cleanup_actions.append("远程桌面锁已释放")
                    utils.logger.info(f"✅ 远程桌面锁已释放: {session_id}")
                else:
                    cleanup_actions.append("远程桌面锁释放失败")
                    utils.logger.warning(f"⚠️ 远程桌面锁释放失败: {session_id}")
            except Exception as e:
                cleanup_actions.append(f"远程桌面锁释放异常: {str(e)}")
                utils.logger.error(f"❌ 远程桌面锁释放异常: {session_id}, {e}")
        
        # 3. 从等待队列中移除（如果在队列中）
        queue_position = session_data.get("queue_position")
        if queue_position:
            try:
                await remote_desktop_lock.release(session_id)  # 这也会从队列中移除
                cleanup_actions.append(f"已从等待队列移除（原位置: {queue_position}）")
                utils.logger.info(f"✅ 已从等待队列移除: {session_id}")
            except Exception as e:
                cleanup_actions.append(f"队列移除异常: {str(e)}")
                utils.logger.error(f"❌ 队列移除异常: {session_id}, {e}")
        
        # 4. 清理其他状态
        cleanup_fields = [
            "qr_code_data", "captcha_screenshot", "captcha_area", 
            "element_analysis", "saved_html_file", "current_url",
            "remote_desktop_url", "queue_position", "estimated_wait_seconds"
        ]
        
        cleaned_fields = []
        for field in cleanup_fields:
            if field in session_data:
                del session_data[field]
                cleaned_fields.append(field)
        
        if cleaned_fields:
            cleanup_actions.append(f"清理临时数据: {', '.join(cleaned_fields)}")
        
        # 5. 设置会话短期过期（1分钟后自动清理）
        session_data["expires_at"] = datetime.now() + timedelta(minutes=1)
        
        utils.logger.info(f"✅ 登录会话已取消: {session_id}")
        utils.logger.info(f"   清理操作: {'; '.join(cleanup_actions) if cleanup_actions else '无需清理'}")
        
        return {
            "success": True,
            "message": "登录会话已成功取消",
            "session_id": session_id,
            "original_status": original_status,
            "cleanup_actions": cleanup_actions,
            "cancelled_at": session_data["cancelled_at"]
        }
        
    except Exception as e:
        utils.logger.error(f"❌ 取消登录会话失败: {session_id}, 错误: {e}")
        return {
            "success": False,
            "message": f"取消登录失败: {str(e)}",
            "session_id": session_id
        }

@login_router.get("/login/sessions")
async def list_active_sessions():
    """列出所有活跃的登录会话（调试用）"""
    try:
        active_sessions = []
        current_time = datetime.now()
        
        for session_id, session_data in login_sessions.items():
            # 检查是否过期
            expires_at = session_data.get("expires_at")
            if expires_at and isinstance(expires_at, datetime):
                is_expired = current_time > expires_at
            else:
                is_expired = False
            
            session_info = {
                "session_id": session_id,
                "platform": session_data.get("platform"),
                "status": session_data.get("status"),
                "message": session_data.get("message", ""),
                "progress": session_data.get("progress", 0),
                "account_id": session_data.get("account_id"),
                "has_desktop_lock": session_data.get("has_desktop_lock", False),
                "queue_position": session_data.get("queue_position"),
                "created_at": session_data.get("created_at").isoformat() if session_data.get("created_at") else None,
                "expires_at": expires_at.isoformat() if isinstance(expires_at, datetime) else str(expires_at),
                "is_expired": is_expired
            }
            
            active_sessions.append(session_info)
        
        # 获取远程桌面锁状态
        lock_status = remote_desktop_lock.get_status()
        
        return {
            "success": True,
            "total_sessions": len(active_sessions),
            "sessions": active_sessions,
            "remote_desktop_lock": lock_status
        }
        
    except Exception as e:
        utils.logger.error(f"获取活跃会话列表失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }

@login_router.get("/login/captcha_info/{session_id}")
async def get_captcha_info(session_id: str):
    """获取验证码信息和页面截图"""
    try:
        if session_id not in login_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session_data = login_sessions[session_id]
        
        # 使用 login_manager 中的 get_captcha_info 方法
        from login_manager import login_manager
        
        result = await login_manager.get_captcha_info(session_id)
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "session_id": session_id
            }
        
        import base64
        screenshot_base64 = ""
        if result.get("screenshot"):
            screenshot_base64 = base64.b64encode(result["screenshot"]).decode()
        
        return {
            "success": True,
            "session_id": session_id,
            "current_url": result.get("current_url", ""),
            "screenshot": f"data:image/png;base64,{screenshot_base64}" if screenshot_base64 else "",
            "has_slider": result.get("has_slider", False),
            "slider_info": result.get("slider_info", {}),
            "timestamp": result.get("timestamp", "")
        }
    except Exception as e:
        utils.logger.error(f"获取验证码信息失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

# 新增：远程桌面完整登录流程
@login_router.post("/login/remote_start")
async def start_remote_login(request: LoginRequest, background_tasks: BackgroundTasks):
    """启动远程桌面完整登录流程"""
    try:
        # 获取账号信息
        db = await get_db()
        account_query = "SELECT * FROM social_accounts WHERE id = %s"
        account = await db.get_first(account_query, request.account_id)
        
        if not account:
            return {
                "code": 404,
                "message": "账号不存在",
                "data": None
            }
        
        platform = account['platform']
        session_id = str(uuid.uuid4())
        
        # 准备用户信息用于并发控制
        user_info = {
            "account_id": request.account_id,
            "platform": platform,
            "account_name": account.get('account_name', f'账号{request.account_id}'),
            "request_time": datetime.now().isoformat()
        }
        
        # 尝试获取远程桌面访问权限
        access_granted = await remote_desktop_lock.try_acquire(session_id, user_info)
        
        if access_granted:
            # 获取到权限，创建活跃会话
            session_data = {
                "session_id": session_id,
                "account_id": request.account_id,
                "platform": platform,
                "account_info": dict(account),
                "status": "remote_desktop_ready",
                "message": "远程桌面登录已准备就绪",
                "progress": 0,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(hours=1),
                "login_method": "remote_desktop",
                "login_url": get_platform_login_url(platform),
                "has_desktop_lock": True  # 标记拥有桌面锁
            }
            
            login_sessions[session_id] = session_data
            utils.logger.info(f"✅ 创建远程桌面登录会话: {session_id}, 平台: {platform}")
            
            # 启动远程桌面登录流程
            background_tasks.add_task(handle_remote_desktop_login, session_id, platform)
            
            return {
                "code": 200,
                "message": "远程桌面访问权限已获取，正在准备登录环境...",
                "data": {
                    "session_id": session_id,
                    "status": "remote_desktop_ready",
                    "expires_at": session_data["expires_at"].isoformat()
                }
            }
        else:
            # 未获取到权限，加入等待队列
            queue_position = remote_desktop_lock.get_queue_position(session_id)
            estimated_wait = remote_desktop_lock.estimate_wait_time(session_id)
            
            session_data = {
                "session_id": session_id,
                "account_id": request.account_id,
                "platform": platform,
                "account_info": dict(account),
                "status": "waiting_in_queue",
                "message": f"远程桌面正在使用中，您在队列第 {queue_position} 位",
                "progress": 0,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(hours=2),  # 等待时间更长
                "login_method": "remote_desktop",
                "login_url": get_platform_login_url(platform),
                "has_desktop_lock": False,  # 标记未拥有桌面锁
                "queue_position": queue_position,
                "estimated_wait_seconds": estimated_wait
            }
            
            login_sessions[session_id] = session_data
            utils.logger.info(f"⏳ 远程桌面登录请求已排队: {session_id}, 队列位置: {queue_position}")
            
            # 启动队列监控任务
            background_tasks.add_task(monitor_queue_position, session_id)
            
            wait_message = f"远程桌面正在使用中，您在队列第 {queue_position} 位"
            if estimated_wait:
                wait_message += f"，预计等待 {estimated_wait // 60} 分钟"
            
            return {
                "code": 200,
                "message": wait_message,
                "data": {
                    "session_id": session_id,
                    "status": "waiting_in_queue",
                    "expires_at": session_data["expires_at"].isoformat()
                }
            }
        
    except Exception as e:
        utils.logger.error(f"启动远程桌面登录失败: {e}")
        return {
            "code": 500,
            "message": f"启动登录失败: {str(e)}",
            "data": None
        }

async def monitor_queue_position(session_id: str):
    """监控队列位置并在轮到时启动登录流程"""
    try:
        utils.logger.info(f"🔍 开始监控队列位置: {session_id}")
        
        # 最多监控2小时
        max_monitor_time = 7200
        check_interval = 10  # 每10秒检查一次
        
        for i in range(max_monitor_time // check_interval):
            await asyncio.sleep(check_interval)
            
            # 检查会话是否还存在
            if session_id not in login_sessions:
                utils.logger.info(f"会话已不存在，停止队列监控: {session_id}")
                await remote_desktop_lock.release(session_id)
                return
            
            session_data = login_sessions[session_id]
            
            # 检查是否已经获得了权限
            if session_data.get("has_desktop_lock", False):
                utils.logger.info(f"会话已获得桌面权限，停止队列监控: {session_id}")
                return
            
            # 尝试获取权限
            user_info = {
                "account_id": session_data["account_id"],
                "platform": session_data["platform"],
                "account_name": session_data["account_info"].get("account_name", ""),
                "queue_check_time": datetime.now().isoformat()
            }
            
            access_granted = await remote_desktop_lock.try_acquire(session_id, user_info)
            
            if access_granted:
                utils.logger.info(f"🎉 队列轮到，开始远程桌面登录: {session_id}")
                
                # 更新会话状态
                session_data["status"] = "remote_desktop_ready"
                session_data["message"] = "轮到您了！正在准备远程桌面登录环境..."
                session_data["progress"] = 0
                session_data["has_desktop_lock"] = True
                
                # 启动实际的登录流程
                task = asyncio.create_task(handle_remote_desktop_login(session_id, session_data["platform"]))
                utils.logger.info(f"🚀 [队列] 远程桌面登录任务已启动: {session_id}")
                return
            else:
                # 更新队列位置信息
                queue_position = remote_desktop_lock.get_queue_position(session_id)
                estimated_wait = remote_desktop_lock.estimate_wait_time(session_id)
                
                if queue_position:
                    session_data["queue_position"] = queue_position
                    session_data["estimated_wait_seconds"] = estimated_wait
                    
                    wait_message = f"远程桌面正在使用中，您在队列第 {queue_position} 位"
                    if estimated_wait:
                        wait_message += f"，预计等待 {estimated_wait // 60} 分钟"
                    
                    session_data["message"] = wait_message
                    
                    # 每分钟记录一次状态
                    if i % 6 == 0:  # 每60秒
                        utils.logger.info(f"⏳ 队列等待中: {session_id}, 位置: {queue_position}")
                else:
                    # 不在队列中了，可能出错了
                    utils.logger.warning(f"会话不在队列中: {session_id}")
                    session_data["status"] = "error"
                    session_data["message"] = "队列状态异常，请重新尝试"
                    return
        
        # 超时了
        utils.logger.warning(f"⏰ 队列监控超时: {session_id}")
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "timeout"
            login_sessions[session_id]["message"] = "队列等待超时，请重新尝试"
        
        await remote_desktop_lock.release(session_id)
        
    except Exception as e:
        utils.logger.error(f"队列监控失败: {session_id}, 错误: {e}")
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "error"
            login_sessions[session_id]["message"] = f"队列监控失败: {str(e)}"
        await remote_desktop_lock.release(session_id)

async def auto_close_remote_desktop(page, session_data: dict, session_id: str):
    """自动关闭远程桌面，提供用户友好的倒计时体验"""
    try:
        utils.logger.info(f"🎉 开始自动关闭远程桌面流程: {session_id}")
        
        # 在页面上显示成功提示和倒计时
        success_script = """
        // 创建成功提示覆盖层
        const overlay = document.createElement('div');
        overlay.id = 'login-success-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 24px;
            text-align: center;
        `;
        
        overlay.innerHTML = `
            <div style="background: #4CAF50; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                <div style="font-size: 48px; margin-bottom: 20px;">🎉</div>
                <div style="font-size: 28px; font-weight: bold; margin-bottom: 15px;">登录成功！</div>
                <div style="font-size: 18px; margin-bottom: 20px;">登录凭证已保存，可以开始数据抓取了</div>
                <div style="font-size: 16px; color: #E8F5E8;">
                    远程桌面将在 <span id="countdown" style="font-weight: bold; font-size: 20px;">3</span> 秒后自动关闭
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 倒计时功能
        let countdown = 3;
        const countdownElement = document.getElementById('countdown');
        const timer = setInterval(() => {
            countdown--;
            if (countdownElement) {
                countdownElement.textContent = countdown;
            }
            if (countdown <= 0) {
                clearInterval(timer);
                // 倒计时结束，准备关闭
                overlay.innerHTML = `
                    <div style="background: #2196F3; padding: 40px; border-radius: 20px;">
                        <div style="font-size: 48px; margin-bottom: 20px;">👋</div>
                        <div style="font-size: 24px; font-weight: bold;">正在关闭远程桌面...</div>
                        <div style="font-size: 16px; color: #E3F2FD; margin-top: 15px;">感谢使用！</div>
                    </div>
                `;
            }
        }, 1000);
        """
        
        # 执行成功提示脚本
        await page.evaluate(success_script)
        utils.logger.info("✅ 成功提示页面已显示")
        
        # 更新会话状态，让前端知道即将关闭
        for i in range(3, 0, -1):
            session_data["message"] = f"登录完成！远程桌面将在{i}秒后自动关闭"
            await asyncio.sleep(1)
        
        # 最终提示
        session_data["message"] = "登录完成！远程桌面正在关闭..."
        utils.logger.info("⏰ 倒计时结束，准备关闭浏览器")
        
        # 给用户最后1秒看到关闭提示
        await asyncio.sleep(1)
        
        # 优雅关闭页面
        try:
            # 先尝试关闭当前标签页
            await page.evaluate("window.close();")
            await asyncio.sleep(0.5)
        except Exception as e:
            utils.logger.debug(f"关闭页面时的预期错误: {e}")
        
        session_data["message"] = "✅ 登录完成！远程桌面已关闭"
        session_data["auto_closed"] = True
        utils.logger.info(f"🎯 远程桌面自动关闭完成: {session_id}")
        
    except Exception as e:
        utils.logger.error(f"自动关闭远程桌面失败: {e}")
        session_data["message"] = "登录完成！请手动关闭远程桌面"
        # 失败了也不影响主流程，只是不能自动关闭而已

def get_platform_login_url(platform: str) -> str:
    """获取平台登录页面URL"""
    url_map = {
        "xhs": "https://www.xiaohongshu.com/login",
        "dy": "https://www.douyin.com/",
        "ks": "https://www.kuaishou.com/",
        "bili": "https://passport.bilibili.com/login",
        "wb": "https://weibo.com/login.php",
        "tieba": "https://tieba.baidu.com/",
        "zhihu": "https://www.zhihu.com/signin"
    }
    return url_map.get(platform, "https://www.google.com")

async def handle_remote_desktop_login(session_id: str, platform: str):
    """处理远程桌面登录流程"""
    try:
        session_data = login_sessions[session_id]
        
        # 检查是否为即将支持的平台
        coming_soon_platforms = {"wb": "微博", "tieba": "贴吧", "zhihu": "知乎"}
        if platform in coming_soon_platforms:
            platform_name = coming_soon_platforms[platform]
            session_data["status"] = "coming_soon"
            session_data["message"] = f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。"
            session_data["progress"] = 100
            utils.logger.info(f"{platform_name}平台远程桌面登录请求 - 即将支持")
            # 释放远程桌面锁
            if session_data.get("has_desktop_lock"):
                await remote_desktop_lock.release(session_id)
            return
        
        utils.logger.info(f"开始远程桌面登录流程: {session_id}, 平台: {platform}")
        
        # 步骤1: 检查远程桌面服务
        session_data["status"] = "checking_remote_desktop"
        session_data["message"] = "正在检查远程桌面服务..."
        session_data["progress"] = 10
        
        remote_desktop_info = await get_remote_desktop_info({"status": "captcha_required"})
        if not remote_desktop_info.get("available"):
            session_data["status"] = "error"
            session_data["message"] = "远程桌面服务不可用，请启动VNC服务"
            return
        
        # 步骤2: 启动浏览器并在远程桌面中打开
        session_data["status"] = "starting_browser"
        session_data["message"] = "正在启动远程桌面浏览器..."
        session_data["progress"] = 20
        
        # 设置远程桌面的DISPLAY环境变量
        import os
        remote_desktop_config = config_manager.get_remote_desktop_config()
        original_display = os.environ.get('DISPLAY')
        target_display = f':{remote_desktop_config.display_number}'
        
        utils.logger.info(f"🔧 远程桌面配置:")
        utils.logger.info(f"   原始DISPLAY: {original_display}")
        utils.logger.info(f"   目标DISPLAY: {target_display}")
        utils.logger.info(f"   VNC URL: {remote_desktop_config.vnc_url}")
        utils.logger.info(f"   VNC 主机: {remote_desktop_config.vnc_host}")
        utils.logger.info(f"   VNC 端口: {remote_desktop_config.vnc_port}")
        utils.logger.info(f"   显示器编号: {remote_desktop_config.display_number}")
        
        os.environ['DISPLAY'] = target_display  # 远程桌面的显示器
        
        # 测试显示器是否可用
        import subprocess
        try:
            result = subprocess.run(f"xdpyinfo", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                utils.logger.info(f"✅ 显示器 {target_display} 可用")
            else:
                utils.logger.error(f"❌ 显示器 {target_display} 不可用: {result.stderr}")
        except Exception as e:
            utils.logger.error(f"❌ 显示器测试失败: {e}")
        
        browser = None
        try:
            async with async_playwright() as p:
                # 启动浏览器到远程桌面（DISPLAY=:1）
                utils.logger.info("🚀 启动浏览器到远程桌面...")
                utils.logger.info(f"   DISPLAY环境变量: {os.environ.get('DISPLAY')}")
                
                # ===== 使用增强配置 =====
                utils.logger.info(f"🚀 [Enhanced] 为远程桌面平台 {platform} 获取增强配置")
                enhanced_config = get_enhanced_browser_config(platform)
                
                utils.logger.info(f"📱 [Enhanced] 使用User-Agent: {enhanced_config['user_agent'][:60]}...")
                utils.logger.info(f"🖥️ [Enhanced] 视窗大小: {enhanced_config['viewport']}")
                utils.logger.info(f"🛠️ [Enhanced] 浏览器参数: {len(enhanced_config['browser_args'])} 个")
                
                browser = await p.chromium.launch(
                    headless=False,  # 必须是可见的，因为要在远程桌面中显示
                    args=enhanced_config['browser_args']
                )
                
                utils.logger.info("✅ 浏览器启动成功")
                
                # 检查浏览器进程
                try:
                    result = subprocess.run("ps aux | grep chrome", shell=True, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and 'chrome' in result.stdout:
                        utils.logger.info("✅ Chrome进程已启动")
                        # 查找带有DISPLAY的进程
                        for line in result.stdout.split('\n'):
                            if 'chrome' in line and target_display in line:
                                utils.logger.info(f"   找到目标显示器进程: {line.strip()}")
                    else:
                        utils.logger.warning("❌ 未找到Chrome进程")
                except Exception as e:
                    utils.logger.warning(f"进程检查失败: {e}")
                
                # 检查窗口
                try:
                    result = subprocess.run("xwininfo -root -tree", shell=True, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        output = result.stdout
                        if 'Chrome' in output or 'Chromium' in output:
                            utils.logger.info("✅ 在远程桌面中找到浏览器窗口")
                        else:
                            utils.logger.warning("❌ 未在远程桌面中找到浏览器窗口")
                            utils.logger.info("可用窗口列表:")
                            for line in output.split('\n')[:10]:
                                if line.strip():
                                    utils.logger.info(f"   {line.strip()}")
                    else:
                        utils.logger.warning(f"窗口检查失败: {result.stderr}")
                except Exception as e:
                    utils.logger.warning(f"窗口检查失败: {e}")
                
                # ===== 使用增强配置创建上下文 =====
                context = await browser.new_context(
                    user_agent=enhanced_config['user_agent'],
                    viewport=enhanced_config['viewport'],
                    locale=enhanced_config['locale'],
                    timezone_id=enhanced_config['timezone_id'],
                    geolocation=enhanced_config['geolocation'],
                    permissions=enhanced_config['permissions'],
                    extra_http_headers=enhanced_config['extra_http_headers']
                )
                
                # 注入增强反检测脚本
                await inject_enhanced_stealth_script(context, platform)
                utils.logger.info(f"✅ [Enhanced] 远程桌面浏览器上下文创建完成")
                
                page = await context.new_page()
                
                # 设置页面缩放比例，优化远程桌面显示
                await page.evaluate("document.body.style.zoom = '0.8'")  # 80%缩放
                utils.logger.info("🔍 [Remote] 设置页面缩放为80%，优化远程桌面显示")
                
                # 步骤3: 打开登录页面
                session_data["status"] = "opening_login_page"
                session_data["message"] = "正在打开登录页面..."
                session_data["progress"] = 30
                
                login_url = session_data["login_url"]
                await page.goto(login_url, timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                
                # 页面加载后再次确保缩放设置
                try:
                    await page.evaluate("""
                        // 设置页面缩放
                        document.body.style.zoom = '0.8';
                        document.body.style.transform = 'scale(0.8)';
                        document.body.style.transformOrigin = 'top left';
                        
                        // 调整页面最大宽度，确保内容可见
                        document.body.style.maxWidth = '1260px';
                        document.body.style.overflow = 'auto';
                        
                        // 添加提示信息
                        const notice = document.createElement('div');
                        notice.innerHTML = '🖥️ 远程桌面已优化显示比例，如需调整请按Ctrl+滚轮';
                        notice.style.cssText = `
                            position: fixed; top: 10px; right: 10px; 
                            background: #4CAF50; color: white; 
                            padding: 8px 12px; border-radius: 5px; 
                            font-size: 12px; z-index: 10000;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                        `;
                        document.body.appendChild(notice);
                        
                        // 3秒后隐藏提示
                        setTimeout(() => {
                            if (notice) notice.style.display = 'none';
                        }, 3000);
                    """)
                    utils.logger.info("✅ [Remote] 页面显示优化设置完成")
                except Exception as e:
                    utils.logger.warning(f"⚠️ [Remote] 页面缩放设置失败: {e}")
                
                # 步骤4: 等待用户完成登录
                session_data["status"] = "waiting_user_login"
                session_data["message"] = "请在远程桌面中完成登录操作"
                session_data["progress"] = 40
                session_data["current_url"] = page.url
                session_data["remote_desktop_url"] = remote_desktop_config.vnc_url
                session_data["remote_desktop_available"] = True
                
                utils.logger.info(f"登录页面已打开，等待用户在远程桌面中操作: {login_url}")
                
                # 步骤5: 监控cookies变化，检测登录完成
                initial_cookies = await context.cookies()
                initial_cookie_count = len(initial_cookies)
                
                utils.logger.info(f"初始cookies数量: {initial_cookie_count}")
                
                max_wait_time = 1800  # 30分钟
                check_interval = 3    # 3秒检查一次
                
                for i in range(max_wait_time // check_interval):
                    await asyncio.sleep(check_interval)
                    if session_data.get('status') == 'cancelled':
                        utils.logger.info(f"检测到会话被取消，主动终止登录流程: {session_id}")
                        break                   
                    try:
                        # 检查cookies变化 - 获取所有域名的cookies
                        current_cookies = await context.cookies()
                        
                        # 为快手平台获取id.kuaishou.com域名的额外cookies
                        if platform == "ks":
                            try:
                                # 快手的userId等重要cookie可能在id.kuaishou.com域名下
                                additional_cookies = await context.cookies("https://id.kuaishou.com")
                                utils.logger.debug(f"🔍 [快手] 获取id.kuaishou.com域名cookies: {len(additional_cookies)}个")
                                
                                # 合并cookies，避免重复
                                cookie_names = {cookie['name'] + cookie['domain'] for cookie in current_cookies}
                                for cookie in additional_cookies:
                                    cookie_key = cookie['name'] + cookie['domain']
                                    if cookie_key not in cookie_names:
                                        current_cookies.append(cookie)
                                        utils.logger.debug(f"🔍 [快手] 添加额外cookie: {cookie['name']} from {cookie['domain']}")
                                
                                utils.logger.info(f"🔍 [快手] 总cookies数量: {len(current_cookies)} (包括所有域名)")
                            except Exception as e:
                                utils.logger.warning(f"⚠️ [快手] 获取额外域名cookies失败: {e}")
                        
                        current_url = page.url
                        
                        # 更新会话信息
                        session_data["current_url"] = current_url
                        elapsed_time = i * check_interval
                        session_data["message"] = f"等待用户登录... ({elapsed_time}s) - 当前: {current_url[:50]}..."
                        
                        # 检测登录成功的标志
                        login_detected = await detect_login_success(platform, current_cookies, current_url)
                        
                        if login_detected:
                            utils.logger.info(f"检测到登录成功！cookies数量: {len(current_cookies)}")
                            
                            # 保存登录信息
                            session_data["status"] = "login_successful"
                            session_data["message"] = "登录成功，正在保存登录信息..."
                            session_data["progress"] = 80
                            
                            # 保存cookies
                            cookies_result = await save_login_cookies(session_id, current_cookies, platform)
                            
                            if cookies_result:
                                session_data["status"] = "completed"
                                session_data["message"] = "登录完成！远程桌面将在3秒后自动关闭"
                                session_data["progress"] = 100
                                session_data["cookies_saved"] = True
                                utils.logger.info(f"远程桌面登录完成: {session_id}")
                                
                                # 🎉 新增：自动关闭远程桌面
                                await auto_close_remote_desktop(page, session_data, session_id)
                            else:
                                session_data["status"] = "error"
                                session_data["message"] = "登录成功但保存cookies失败"
                            
                            break
                        
                        # 每30秒记录一次状态
                        if i % 10 == 0:
                            utils.logger.info(f"等待用户登录中... {elapsed_time}s, URL: {current_url}")
                    
                    except Exception as e:
                        utils.logger.warning(f"检查登录状态时出错: {e}")
                        continue
                
                # 检查是否超时
                if session_data["status"] == "waiting_user_login":
                    session_data["status"] = "timeout"
                    session_data["message"] = "登录超时，请重新尝试"
                    utils.logger.warning(f"远程桌面登录超时: {session_id}")
            
        except Exception as e:
            utils.logger.error(f"浏览器操作失败: {e}")
            if session_id in login_sessions:
                login_sessions[session_id]["status"] = "error"
                login_sessions[session_id]["message"] = f"浏览器操作失败: {str(e)}"
        finally:
            # 恢复原始的DISPLAY环境变量
            if original_display:
                os.environ['DISPLAY'] = original_display
            elif 'DISPLAY' in os.environ:
                del os.environ['DISPLAY']
            
            # 释放远程桌面锁
            utils.logger.info(f"🔓 释放远程桌面锁: {session_id}")
            await remote_desktop_lock.release(session_id)
            
            # 更新会话状态
            if session_id in login_sessions:
                login_sessions[session_id]["has_desktop_lock"] = False
            
    except Exception as e:
        utils.logger.error(f"远程桌面登录处理失败: {e}")
        if session_id in login_sessions:
            login_sessions[session_id]["status"] = "error"
            login_sessions[session_id]["message"] = f"登录处理失败: {str(e)}"
            login_sessions[session_id]["has_desktop_lock"] = False
        
        # 确保释放锁
        try:
            await remote_desktop_lock.release(session_id)
        except Exception as lock_error:
            utils.logger.error(f"释放远程桌面锁失败: {lock_error}")

async def detect_login_success(platform: str, cookies: list, current_url: str) -> bool:
    """检测登录是否成功"""
    try:
        # 基于cookies检测
        cookie_names = [cookie['name'] for cookie in cookies]
        
        # 抖音平台的特殊严格检测逻辑
        if platform == "dy":
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            login_indicators = []
            
            # 1. sessionid 必须存在且有实际值
            sessionid = cookie_dict.get('sessionid', '')
            if sessionid and len(sessionid) > 20:
                login_indicators.append("sessionid")
                utils.logger.info(f"✓ 抖音sessionid有效: {sessionid[:10]}...")
            
            # 2. 检查其他用户登录相关cookies
            ttwid = cookie_dict.get('ttwid', '')
            if ttwid and len(ttwid) > 10:
                login_indicators.append("ttwid")
                utils.logger.info(f"✓ 抖音ttwid有效: {ttwid[:10]}...")
                
            odin_tt = cookie_dict.get('odin_tt', '')
            if odin_tt and len(odin_tt) > 10:
                login_indicators.append("odin_tt")
                utils.logger.info(f"✓ 抖音odin_tt有效: {odin_tt[:10]}...")
                
            login_status_cookie = cookie_dict.get('LOGIN_STATUS', '')
            if login_status_cookie == "1":
                login_indicators.append("login_status")
                utils.logger.info("✓ 抖音LOGIN_STATUS=1")
                
            passport_auth_status = cookie_dict.get('passport_auth_status', '')
            if passport_auth_status and passport_auth_status != "":
                login_indicators.append("auth_status")
                utils.logger.info(f"✓ 抖音passport_auth_status有值: {passport_auth_status}")
            
            # 3. URL检查（作为辅助）
            success_keywords = ["user", "creator", "profile"]
            if any(keyword in current_url.lower() for keyword in success_keywords) and "login" not in current_url.lower():
                login_indicators.append("url_redirect")
                utils.logger.info(f"✓ 抖音URL跳转到登录后页面: {current_url}")
            
            # 抖音需要至少3个指标才认为登录成功，避免误判
            if len(login_indicators) >= 3:
                utils.logger.info(f"✅ 抖音登录检测成功！满足{len(login_indicators)}个条件: {', '.join(login_indicators)}")
                return True
            else:
                utils.logger.debug(f"抖音登录检测中... 当前满足条件({len(login_indicators)}): {login_indicators}")
                return False
        
        # 快手平台的特殊严格检测
        elif platform == "ks":
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # 打印所有cookies用于调试
            utils.logger.info(f"🔍 [快手调试] 所有cookies ({len(cookie_dict)}个):")
            for name, value in cookie_dict.items():
                utils.logger.info(f"   - {name}: {value[:30]}..." if len(value) > 30 else f"   - {name}: {value}")
            
            # 核心认证cookies（降低要求：主要检查passToken）
            core_cookies = ['passToken', 'userId']
            core_found = 0
            missing_core = []
            
            for cookie_name in core_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    if len(cookie_value) > 10:
                        core_found += 1
                        utils.logger.info(f"✅ 快手核心cookie {cookie_name}: {cookie_value[:20]}...")
                    else:
                        utils.logger.warning(f"⚠️ 快手核心cookie {cookie_name} 值太短: {cookie_value}")
                        missing_core.append(f"{cookie_name}(值太短)")
                else:
                    utils.logger.warning(f"⚠️ 快手核心cookie {cookie_name} 不存在")
                    missing_core.append(f"{cookie_name}(不存在)")
            
            # 会话cookies（至少一个）
            session_cookies = ['kuaishou.server.webday7_st', 'kuaishou.server.webday7_ph']
            session_found = 0
            
            for cookie_name in session_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    if len(cookie_value) > 20:
                        session_found += 1
                        utils.logger.info(f"✅ 快手会话cookie {cookie_name}: {cookie_value[:30]}...")
            
            # 临时降低要求：只要有passToken和至少一个会话cookie就认为登录成功
            passToken_exists = 'passToken' in cookie_dict and len(cookie_dict['passToken']) > 10
            
            if passToken_exists and session_found >= 1:
                utils.logger.info(f"✅ 快手登录检测成功！passToken存在 + 会话({session_found})")
                if missing_core:
                    utils.logger.warning(f"⚠️ 注意: 缺少以下核心cookies: {missing_core}")
                return True
            else:
                utils.logger.debug(f"快手登录检测中... passToken: {passToken_exists}, 会话({session_found})")
                if missing_core:
                    utils.logger.debug(f"缺少核心cookies: {missing_core}")
                return False
        
        # B站平台的特殊严格检测
        elif platform == "bili":
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # 打印所有cookies用于调试
            utils.logger.info(f"🔍 [B站调试] 所有cookies ({len(cookie_dict)}个):")
            for name, value in cookie_dict.items():
                utils.logger.info(f"   - {name}: {value[:30]}..." if len(value) > 30 else f"   - {name}: {value}")
            
            # 核心认证cookies（必须全部存在）
            core_cookies = ['SESSDATA', 'DedeUserID', 'bili_jct']
            core_found = 0
            missing_core = []
            
            for cookie_name in core_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    # 不同cookie的最小长度要求
                    min_length = 32 if cookie_name == 'bili_jct' else 8 if cookie_name == 'DedeUserID' else 50
                    
                    if len(cookie_value) >= min_length:
                        core_found += 1
                        utils.logger.info(f"✅ B站核心cookie {cookie_name}: {cookie_value[:20]}...")
                    else:
                        utils.logger.warning(f"⚠️ B站核心cookie {cookie_name} 值太短: {cookie_value}")
                        missing_core.append(f"{cookie_name}(值太短)")
                else:
                    utils.logger.warning(f"⚠️ B站核心cookie {cookie_name} 不存在")
                    missing_core.append(f"{cookie_name}(不存在)")
            
            # 严格验证：核心cookies必须全部存在
            if core_found == len(core_cookies):
                utils.logger.info(f"✅ B站登录检测成功！核心认证({core_found}/{len(core_cookies)})")
                return True
            else:
                utils.logger.debug(f"B站登录检测中... 核心认证({core_found}/{len(core_cookies)})")
                if missing_core:
                    utils.logger.debug(f"缺少核心cookies: {missing_core}")
                return False
        
        # 小红书的严格检测（仅核心cookies + 强指标）
        elif platform == "xhs":
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # 检查核心认证cookies（更严格的要求）
            core_cookies = ['a1', 'web_session']
            core_found = 0
            for cookie_name in core_cookies:
                if cookie_name in cookie_dict and cookie_dict[cookie_name]:
                    cookie_value = cookie_dict[cookie_name]
                    min_length = 40 if cookie_name == 'a1' else 30
                    if len(cookie_value) >= min_length:
                        core_found += 1
                        utils.logger.info(f"✅ 小红书核心cookie {cookie_name}: {cookie_value[:20]}...")
            
            # 检查强登录指标（必须存在）
            unread_cookie = cookie_dict.get('unread', '')
            has_strong_indicator = unread_cookie and ('ub' in unread_cookie or 'ue' in unread_cookie)
            
            # 严格判断：必须同时满足核心cookies AND 强指标
            if core_found >= 2 and has_strong_indicator:
                utils.logger.info(f"✅ 小红书登录检测成功（严格模式）！核心({core_found}/2) + 强指标")
                return True
            else:
                utils.logger.debug(f"小红书登录检测失败 - 核心({core_found}/2), 强指标({has_strong_indicator}) [需要两者都满足]")
                return False
        
        # 其他平台的关键cookie检测
        else:
            key_cookies = {
                "wb": ["SUB", "login_sid_t"],
                "tieba": ["BDUSS", "STOKEN"],
                "zhihu": ["z_c0", "q_c1"]
            }
            
            platform_key_cookies = key_cookies.get(platform, [])
            
            # 检查是否有关键cookies
            for key_cookie in platform_key_cookies:
                if key_cookie in cookie_names:
                    # 验证cookie值不为空
                    cookie_value = None
                    for cookie in cookies:
                        if cookie['name'] == key_cookie:
                            cookie_value = cookie['value']
                            break
                    
                    if cookie_value and len(cookie_value) > 10:  # 确保cookie有实际的值
                        utils.logger.info(f"检测到平台 {platform} 的关键cookie: {key_cookie} (有效值)")
                        return True
                    else:
                        utils.logger.info(f"发现关键cookie {key_cookie} 但值无效: {cookie_value}")
        
        # 基于URL检测（登录后通常会跳转到主页或个人页面）
        success_url_patterns = {
            "xhs": ["xiaohongshu.com/explore", "xiaohongshu.com/user"],
            "dy": ["douyin.com/recommend", "douyin.com/user", "douyin.com/foryou"],
            "ks": ["kuaishou.com/profile", "kuaishou.com/u/"],
            "bili": ["bilibili.com/", "space.bilibili.com"],
            "wb": ["weibo.com/u/", "weibo.com/home"],
            "tieba": ["tieba.baidu.com/home", "tieba.baidu.com/i/"],
            "zhihu": ["zhihu.com/", "zhihu.com/people"]
        }
        
        platform_patterns = success_url_patterns.get(platform, [])
        for pattern in platform_patterns:
            if pattern in current_url:
                utils.logger.info(f"检测到平台 {platform} 的成功URL模式: {pattern}")
                return True
        
        # 只在初始检测时才检查cookies数量（防止误判）
        # 移除了简单的cookies数量检测，因为它不够准确
        
        return False
        
    except Exception as e:
        utils.logger.error(f"检测登录状态失败: {e}")
        return False

async def save_login_cookies(session_id: str, cookies: list, platform: str) -> bool:
    """保存登录cookies"""
    try:
        utils.logger.info(f"🔄 开始保存cookies - 会话ID: {session_id}, 平台: {platform}, cookies数量: {len(cookies)}")
        
        # 检查会话是否存在
        session_data = login_sessions.get(session_id)
        if not session_data:
            utils.logger.error(f"❌ 会话不存在: {session_id}")
            return False
        
        account_id = session_data["account_id"]
        utils.logger.info(f"📋 会话信息 - 账号ID: {account_id}, 平台: {platform}")
        
        # 获取数据库连接
        try:
            db = await get_db()
            utils.logger.info("✅ 数据库连接成功")
        except Exception as e:
            utils.logger.error(f"❌ 数据库连接失败: {e}")
            return False
        
        # 转换cookies格式
        try:
            cookies_dict = {}
            for cookie in cookies:
                cookies_dict[cookie['name']] = cookie['value']
            
            utils.logger.info(f"📝 Cookies转换成功，包含字段: {list(cookies_dict.keys())}")
            
            # 记录关键cookies信息
            key_cookies = {
                "xhs": ["web_session", "xsecappid"],
                "dy": ["sessionid", "passport_csrf_token", "odin_tt", "LOGIN_STATUS"],
                "ks": ["kuaishou.server.web_st", "token", "kpf", "kpn", "clientid", "did", "client_key"],
                "bili": ["SESSDATA", "DedeUserID", "bili_jct"],
                "wb": ["SUB", "login_sid_t"],
                "tieba": ["BDUSS", "STOKEN"],
                "zhihu": ["z_c0", "q_c1"]
            }
            
            platform_key_cookies = key_cookies.get(platform, [])
            found_keys = [key for key in platform_key_cookies if key in cookies_dict]
            missing_keys = [key for key in platform_key_cookies if key not in cookies_dict]
            
            if found_keys:
                utils.logger.info(f"✅ 检测到关键cookies: {found_keys}")
            if missing_keys:
                utils.logger.warning(f"⚠️ 缺少关键cookies: {missing_keys}")
            
            # 保存到数据库
            cookies_str = json.dumps(cookies_dict)
            utils.logger.info(f"📊 Cookies JSON字符串长度: {len(cookies_str)}")
            
        except Exception as e:
            utils.logger.error(f"❌ Cookies转换失败: {e}")
            return False
        
        # 数据库更新操作
        try:
            # 保存到正确的 login_tokens 表
            # 首先将旧的token设为无效
            update_old_query = """
                UPDATE login_tokens SET is_valid = 0 
                WHERE account_id = %s AND platform = %s
            """
            await db.execute(update_old_query, account_id, platform)
            utils.logger.info(f"📝 已将账号 {account_id} 在平台 {platform} 的旧token设为无效")
            
            # 插入新的token记录
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(days=30)  # 30天后过期
            
            insert_query = """
                INSERT INTO login_tokens (account_id, platform, token_type, token_data, user_agent, proxy_info, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
            proxy_info = None  # 暂时不记录代理信息
            
            utils.logger.info(f"📤 执行数据库插入 - 账号ID: {account_id}, 平台: {platform}")
            utils.logger.info(f"📝 SQL查询: {insert_query}")
            
            result = await db.execute(insert_query, 
                account_id, platform, "cookie", cookies_str,
                user_agent, proxy_info, expires_at
            )
            utils.logger.info(f"✅ 数据库插入成功 - 新token ID: {result if result else '未知'}")
            
        except Exception as e:
            utils.logger.error(f"❌ 数据库操作失败: {e}")
            utils.logger.error(f"   错误类型: {type(e).__name__}")
            utils.logger.error(f"   错误详情: {str(e)}")
            return False
        
        # 验证保存结果 - 查询 login_tokens 表
        try:
            verify_query = """
                SELECT token_data, is_valid, expires_at, created_at 
                FROM login_tokens 
                WHERE account_id = %s AND platform = %s AND is_valid = 1
                ORDER BY created_at DESC 
                LIMIT 1
            """
            verify_result = await db.get_first(verify_query, account_id, platform)
            
            if verify_result:
                saved_token_data = verify_result.get('token_data', '')
                is_valid = verify_result.get('is_valid', 0)
                expires_at = verify_result.get('expires_at', '')
                created_at = verify_result.get('created_at', '')
                
                utils.logger.info(f"✅ 保存验证成功:")
                utils.logger.info(f"   token有效性: {is_valid}")
                utils.logger.info(f"   创建时间: {created_at}")
                utils.logger.info(f"   过期时间: {expires_at}")
                utils.logger.info(f"   Token数据长度: {len(saved_token_data) if saved_token_data else 0}")
                
                if saved_token_data and len(saved_token_data) > 50 and is_valid:  # 确保有实际内容且有效
                    utils.logger.info(f"🎉 Cookies保存成功 - 账号ID: {account_id}, 平台: {platform}")
                    return True
                else:
                    utils.logger.error("❌ 保存的token数据无效或过短")
                    return False
            else:
                utils.logger.error(f"❌ 验证查询失败 - 未找到账号ID {account_id} 在平台 {platform} 的有效token")
                return False
                
        except Exception as e:
            utils.logger.error(f"❌ 保存验证失败: {e}")
            return False
        
    except Exception as e:
        utils.logger.error(f"❌ 保存cookies总体失败: {e}")
        utils.logger.error(f"   错误类型: {type(e).__name__}")
        import traceback
        utils.logger.error(f"   堆栈跟踪: {traceback.format_exc()}")
        return False

