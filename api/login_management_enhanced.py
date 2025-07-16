#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版登录管理器 - 专门优化反检测
解决快手、抖音、B站等平台的检测问题
"""

import asyncio
import os
import sys
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from config.browser_config_2024 import get_platform_config, BrowserConfig2024
from tools import utils

class EnhancedLoginManager:
    """增强版登录管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        
    async def create_enhanced_browser_context(self, session_id: str, platform: str) -> BrowserContext:
        """创建增强版浏览器上下文"""
        
        # 获取平台特定配置
        config = get_platform_config(platform)
        browser_args = BrowserConfig2024.get_browser_args(platform, remote_desktop=True)
        
        self.logger.info(f"🚀 [Enhanced] 创建 {platform} 平台浏览器上下文")
        self.logger.info(f"   User-Agent: {config['user_agent'][:80]}...")
        self.logger.info(f"   Viewport: {config['viewport']}")
        
        # 检测环境
        is_headless_env = not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY')
        
        async with async_playwright() as playwright:
            # 启动浏览器
            browser = await playwright.chromium.launch(
                headless=is_headless_env,
                args=browser_args
            )
            
            # 创建上下文
            context = await browser.new_context(
                user_agent=config['user_agent'],
                viewport=config['viewport'],
                locale=config['locale'],
                timezone_id=config['timezone_id'],
                geolocation=config['geolocation'],
                permissions=config['permissions'],
                color_scheme=config['color_scheme'],
                reduced_motion=config['reduced_motion'],
                forced_colors=config['forced_colors'],
                extra_http_headers=config['extra_http_headers']
            )
            
            # 添加增强反检测脚本
            await self._inject_enhanced_stealth(context, platform)
            
            # 保存上下文
            self.contexts[session_id] = context
            self.browser = browser
            
            return context
    
    async def _inject_enhanced_stealth(self, context: BrowserContext, platform: str):
        """注入增强反检测脚本"""
        
        # 读取增强反检测脚本
        stealth_script_path = os.path.join(project_root, "libs", "enhanced_stealth.js")
        
        if os.path.exists(stealth_script_path):
            self.logger.info(f"📄 [Enhanced] 注入增强反检测脚本")
            await context.add_init_script(path=stealth_script_path)
        else:
            self.logger.warning(f"⚠️ [Enhanced] 反检测脚本未找到: {stealth_script_path}")
        
        # 添加平台特定的初始化脚本
        platform_script = self._get_platform_specific_script(platform)
        if platform_script:
            await context.add_init_script(platform_script)
    
    def _get_platform_specific_script(self, platform: str) -> Optional[str]:
        """获取平台特定的JavaScript脚本"""
        
        scripts = {
            "kuaishou": """
                // 快手特定初始化
                console.log('🎬 [快手] 平台特定脚本加载');
                
                // 模拟快手环境
                window.ks = window.ks || {};
                window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
                
                // 删除可能暴露的自动化属性
                delete window.webdriver;
                delete window.__webdriver_script_fn;
                
                // 模拟真实的快手客户端环境
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // 快手可能检测的特殊函数
                window.btoa = window.btoa || function(str) {
                    return Buffer.from(str, 'binary').toString('base64');
                };
            """,
            
            "douyin": """
                // 抖音特定初始化
                console.log('🎵 [抖音] 平台特定脚本加载');
                
                // 抖音环境变量
                window.byted_acrawler = window.byted_acrawler || {};
                window.SLARDAR_WEB_ID = '3715';
                
                // 模拟抖音的TT对象
                window.TT = window.TT || {
                    ENV: 'production',
                    VERSION: '1.0.0'
                };
                
                // 抖音可能检测的媒体API
                if (navigator.mediaDevices) {
                    const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
                    navigator.mediaDevices.getUserMedia = function(constraints) {
                        console.log('🎥 模拟媒体设备访问');
                        return Promise.resolve({
                            getTracks: () => [],
                            getVideoTracks: () => [],
                            getAudioTracks: () => []
                        });
                    };
                }
            """,
            
            "bilibili": """
                // B站特定初始化
                console.log('📺 [B站] 平台特定脚本加载');
                
                // B站环境变量
                window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
                window.reportObserver = window.reportObserver || {};
                
                // 模拟B站的buvid
                if (!localStorage.getItem('_uuid')) {
                    const uuid = 'B' + Date.now().toString(36) + Math.random().toString(36).substr(2);
                    localStorage.setItem('_uuid', uuid);
                    console.log('💾 生成B站UUID:', uuid);
                }
                
                // B站可能检测的WebRTC
                if (window.RTCPeerConnection) {
                    const originalRTC = window.RTCPeerConnection;
                    window.RTCPeerConnection = function(...args) {
                        console.log('🔗 模拟WebRTC连接');
                        return new originalRTC(...args);
                    };
                }
            """,
            
            "xhs": """
                // 小红书特定初始化
                console.log('📍 [小红书] 平台特定脚本加载');
                
                // 小红书Cookie设置
                document.cookie = 'webId=xxx123; domain=.xiaohongshu.com; path=/';
                
                // 模拟小红书环境
                window.xhs = window.xhs || {};
                
                // 小红书可能检测的canvas
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(...args) {
                    // 轻微扰动canvas指纹
                    const result = originalToDataURL.apply(this, args);
                    return result;
                };
            """
        }
        
        return scripts.get(platform)
    
    async def create_page_for_platform(self, session_id: str, platform: str) -> Page:
        """为特定平台创建页面"""
        
        if session_id not in self.contexts:
            await self.create_enhanced_browser_context(session_id, platform)
        
        context = self.contexts[session_id]
        page = await context.new_page()
        
        # 添加页面级别的优化
        await self._optimize_page_for_platform(page, platform)
        
        self.pages[session_id] = page
        return page
    
    async def _optimize_page_for_platform(self, page: Page, platform: str):
        """为页面添加平台特定优化"""
        
        # 设置额外的请求头
        platform_headers = {
            "kuaishou": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "douyin": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            },
            "bilibili": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com/",
            }
        }
        
        headers = platform_headers.get(platform, {})
        if headers:
            await page.set_extra_http_headers(headers)
            self.logger.info(f"📨 [Enhanced] 设置 {platform} 特定请求头")
        
        # 监听网络请求，过滤可疑请求
        await page.route("**/*", self._handle_request)
    
    async def _handle_request(self, route):
        """处理网络请求"""
        request = route.request
        
        # 过滤可能暴露自动化的请求
        suspicious_patterns = [
            'webdriver',
            'automation', 
            'playwright',
            'puppeteer',
            'selenium'
        ]
        
        url_lower = request.url.lower()
        if any(pattern in url_lower for pattern in suspicious_patterns):
            self.logger.warning(f"🚫 [Enhanced] 阻止可疑请求: {request.url}")
            await route.abort()
            return
        
        # 继续正常请求
        await route.continue_()
    
    async def navigate_to_platform(self, session_id: str, platform: str) -> bool:
        """导航到指定平台"""
        
        platform_urls = {
            "kuaishou": "https://www.kuaishou.com",
            "douyin": "https://www.douyin.com", 
            "bilibili": "https://www.bilibili.com",
            "xhs": "https://www.xiaohongshu.com"
        }
        
        url = platform_urls.get(platform)
        if not url:
            self.logger.error(f"❌ [Enhanced] 不支持的平台: {platform}")
            return False
        
        try:
            page = await self.create_page_for_platform(session_id, platform)
            
            self.logger.info(f"🌐 [Enhanced] 导航到 {platform}: {url}")
            
            # 设置较长的超时时间
            response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            if response and response.status == 200:
                self.logger.info(f"✅ [Enhanced] {platform} 页面加载成功")
                
                # 等待页面稳定
                await page.wait_for_timeout(3000)
                
                # 检查是否被检测
                is_detected = await self._check_detection(page, platform)
                if is_detected:
                    self.logger.warning(f"⚠️ [Enhanced] {platform} 可能检测到自动化")
                    return False
                
                return True
            else:
                status = response.status if response else "No Response"
                self.logger.error(f"❌ [Enhanced] {platform} 页面加载失败: {status}")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 [Enhanced] 导航失败: {e}")
            return False
    
    async def _check_detection(self, page: Page, platform: str) -> bool:
        """检查是否被平台检测"""
        
        try:
            # 检查页面标题和内容
            title = await page.title()
            content = await page.content()
            
            # 常见的检测标识
            detection_signs = [
                "访问被拒绝",
                "access denied", 
                "blocked",
                "robot",
                "automation",
                "验证码",
                "captcha",
                "人机验证"
            ]
            
            title_lower = title.lower()
            content_lower = content.lower()
            
            for sign in detection_signs:
                if sign in title_lower or sign in content_lower:
                    self.logger.warning(f"🚨 [Enhanced] 检测到风险标识: {sign}")
                    return True
            
            # 平台特定检测
            if platform == "kuaishou":
                # 检查快手特有的错误
                if '"result":2' in content or 'result: 2' in content:
                    self.logger.warning(f"🚨 [Enhanced] 快手返回 result:2 错误")
                    return True
            
            elif platform in ["douyin", "bilibili"]:
                # 检查版本过低提示
                if "浏览器版本过低" in content or "browser version" in content_lower:
                    self.logger.warning(f"🚨 [Enhanced] {platform} 提示浏览器版本过低")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"💥 [Enhanced] 检测判断失败: {e}")
            return False
    
    async def cleanup(self, session_id: str = None):
        """清理资源"""
        
        if session_id:
            # 清理特定会话
            if session_id in self.pages:
                try:
                    await self.pages[session_id].close()
                    del self.pages[session_id]
                except:
                    pass
            
            if session_id in self.contexts:
                try:
                    await self.contexts[session_id].close()
                    del self.contexts[session_id]
                except:
                    pass
        else:
            # 清理所有
            for page in self.pages.values():
                try:
                    await page.close()
                except:
                    pass
            self.pages.clear()
            
            for context in self.contexts.values():
                try:
                    await context.close()
                except:
                    pass
            self.contexts.clear()
            
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass

# =============================================
# 快速测试功能
# =============================================

async def test_platform_detection(platform: str):
    """测试平台检测"""
    
    manager = EnhancedLoginManager()
    session_id = f"test_{platform}_{int(asyncio.get_event_loop().time())}"
    
    try:
        print(f"\n🧪 测试 {platform} 平台反检测...")
        
        success = await manager.navigate_to_platform(session_id, platform)
        
        if success:
            print(f"✅ {platform} 测试成功 - 未被检测")
        else:
            print(f"❌ {platform} 测试失败 - 可能被检测")
        
        # 等待一段时间观察
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"💥 {platform} 测试异常: {e}")
    finally:
        await manager.cleanup(session_id)

async def test_all_platforms():
    """测试所有平台"""
    
    platforms = ["kuaishou", "douyin", "bilibili", "xhs"]
    
    for platform in platforms:
        await test_platform_detection(platform)
        await asyncio.sleep(2)  # 间隔等待

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="增强版登录管理器测试")
    parser.add_argument("--platform", choices=["kuaishou", "douyin", "bilibili", "xhs", "all"], 
                       default="all", help="测试的平台")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if args.platform == "all":
        asyncio.run(test_all_platforms())
    else:
        asyncio.run(test_platform_detection(args.platform)) 