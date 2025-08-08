#!/usr/bin/env python3
"""
小红书反爬虫增强模块
专门针对小红书的反爬机制进行反制
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional
from tools import utils
from .base_anti_crawler import BaseAntiCrawler

class XHSAntiCrawler(BaseAntiCrawler):
    """小红书反爬虫增强类"""
    
    def __init__(self):
        super().__init__("xhs")
        
        self.xhs_domains = [
            "www.xiaohongshu.com",
            "creator.xiaohongshu.com",
            "m.xiaohongshu.com"
        ]
    
    async def setup_enhanced_browser_context(self, browser_context) -> None:
        """设置增强的浏览器上下文"""
        try:
            # 注入通用的反检测脚本
            await self.inject_common_anti_detection_script(browser_context)
            
            # 注入小红书特有的反检测脚本
            await browser_context.add_init_script("""
                console.log('🛡️ [XHS反爬] 开始注入小红书特有反检测脚本');
                
                // 小红书特有的反爬虫处理
                // 隐藏小红书检测到的自动化特征
                if (window.navigator) {
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8,
                        configurable: true
                    });
                    
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8,
                        configurable: true
                    });
                }
                
                // 模拟真实的屏幕信息
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                    configurable: true
                });
                
                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                    configurable: true
                });
                
                console.log('✅ [XHS反爬] 小红书特有反检测脚本注入完成');
            """)
            
            # 设置随机请求头
            await self.set_random_headers(browser_context)
            
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 设置浏览器上下文失败: {e}")
    
    async def handle_frequency_limit(self, page, session_id: str) -> bool:
        """处理频率限制问题"""
        try:
            # 检查是否出现频率限制
            frequency_indicators = [
                "验证过于频繁",
                "请稍后重试",
                "访问过于频繁",
                "安全验证",
                "验证码"
            ]
            
            page_content = await self.safe_page_operation(page, "text_content", "body")
            current_title = await self.safe_page_operation(page, "title")
            
            if not page_content or not current_title:
                return False
            
            for indicator in frequency_indicators:
                if indicator in page_content or indicator in current_title:
                    utils.logger.warning(f"⚠️ [XHS反爬] 检测到频率限制: {indicator}")
                    
                    # 策略1: 等待随机时间
                    wait_time = self.get_wait_time(30, 120)
                    utils.logger.info(f"⏳ [XHS反爬] 等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)
                    
                    # 策略2: 刷新页面
                    await self.safe_page_operation(page, "reload", wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(random.uniform(3, 8))
                    
                    # 策略3: 清除cookies和localStorage
                    await self.safe_page_operation(page, "evaluate", """
                        localStorage.clear();
                        sessionStorage.clear();
                        document.cookie.split(";").forEach(function(c) { 
                            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
                        });
                    """)
                    
                    return True
            
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 处理频率限制失败: {e}")
            return False
    
    async def simulate_human_behavior(self, page) -> None:
        """模拟人类行为"""
        try:
            # 1. 随机鼠标移动
            viewport = await page.viewport_size()
            if viewport:
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await self.safe_page_operation(page, "mouse_move", x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # 2. 随机滚动
            await self.safe_page_operation(page, "evaluate", """
                window.scrollTo(0, Math.random() * 100);
                setTimeout(() => {
                    window.scrollTo(0, 0);
                }, Math.random() * 1000 + 500);
            """)
            
            # 3. 随机点击空白区域
            await self.safe_page_operation(page, "mouse_click",
                random.randint(50, 200),
                random.randint(50, 200)
            )
            
            await asyncio.sleep(random.uniform(1, 3))
            
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 模拟人类行为失败: {e}")
    
    async def bypass_captcha(self, page, session_id: str) -> bool:
        """绕过验证码"""
        try:
            # 检查是否有验证码
            captcha_selectors = [
                ".captcha",
                ".verify",
                "[class*='captcha']",
                "[class*='verify']",
                "img[src*='captcha']",
                "img[src*='verify']"
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = await self.safe_page_operation(page, "query_selector", selector)
                    if captcha_element and await captcha_element.is_visible():
                        utils.logger.warning(f"⚠️ [XHS反爬] 检测到验证码: {selector}")
                        
                        # 尝试自动处理验证码
                        return await self.handle_auto_captcha(page, session_id)
                except:
                    continue
            
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 绕过验证码失败: {e}")
            return False
    
    async def handle_auto_captcha(self, page, session_id: str) -> bool:
        """自动处理验证码"""
        try:
            # 1. 尝试刷新验证码
            refresh_selectors = [
                "button[class*='refresh']",
                "button[class*='reload']",
                ".refresh",
                ".reload",
                "[class*='refresh']",
                "[class*='reload']"
            ]
            
            for selector in refresh_selectors:
                try:
                    refresh_btn = await page.query_selector(selector)
                    if refresh_btn and await refresh_btn.is_visible():
                        await refresh_btn.click()
                        utils.logger.info(f"🔄 [XHS反爬] 刷新验证码: {selector}")
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # 2. 等待用户手动处理
            utils.logger.info("⏳ [XHS反爬] 等待用户手动处理验证码...")
            
            # 等待最多5分钟
            for i in range(300):
                # 检查验证码是否还存在
                captcha_exists = False
                for selector in [".captcha", ".verify", "[class*='captcha']", "[class*='verify']"]:
                    try:
                        captcha_element = await page.query_selector(selector)
                        if captcha_element and await captcha_element.is_visible():
                            captcha_exists = True
                            break
                    except:
                        continue
                
                if not captcha_exists:
                    utils.logger.info("✅ [XHS反爬] 验证码已处理完成")
                    return True
                
                await asyncio.sleep(1)
            
            utils.logger.error("❌ [XHS反爬] 验证码处理超时")
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 自动处理验证码失败: {e}")
            return False
    
    async def enhance_page_loading(self, page, url: str) -> bool:
        """增强页面加载策略"""
        try:
            # 1. 设置页面加载超时
            try:
                await page.set_default_timeout(60000)
            except Exception as e:
                utils.logger.warning(f"⚠️ [XHS反爬] 设置页面超时失败: {e}")
            
            # 2. 禁用图片和CSS以加快加载
            try:
                async def abort_route(route):
                    await route.abort()
                
                await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", abort_route)
            except Exception as e:
                utils.logger.warning(f"⚠️ [XHS反爬] 禁用资源失败: {e}")
            
            # 3. 访问页面
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                utils.logger.warning(f"⚠️ [XHS反爬] 页面访问失败: {e}")
                return False
            
            # 4. 等待页面稳定
            await asyncio.sleep(random.uniform(2, 5))
            
            # 5. 检查页面是否正常
            title = await self.safe_page_operation(page, "title")
            if title and ("小红书" in title or "xiaohongshu" in title.lower()):
                utils.logger.info(f"✅ [XHS反爬] 页面加载成功: {title}")
                return True
            else:
                utils.logger.warning(f"⚠️ [XHS反爬] 页面标题异常: {title}")
                return False
                
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 增强页面加载失败: {e}")
            return False
    
    async def get_optimal_login_url(self) -> str:
        """获取最优登录URL"""
        # 根据时间选择不同的URL
        current_hour = time.localtime().tm_hour
        
        if 9 <= current_hour <= 18:  # 工作时间
            return "https://creator.xiaohongshu.com/login"
        elif 19 <= current_hour <= 23:  # 晚上时间
            return "https://www.xiaohongshu.com/explore"
        else:  # 凌晨时间
            return "https://m.xiaohongshu.com"
    
    async def setup_proxy_rotation(self, browser_context) -> None:
        """设置代理轮换"""
        try:
            # 这里可以集成代理池
            # 暂时使用基础配置
            utils.logger.info("🔄 [XHS反爬] 代理轮换功能待实现")
        except Exception as e:
            utils.logger.error(f"❌ [XHS反爬] 设置代理轮换失败: {e}")

# 全局实例
xhs_anti_crawler = XHSAntiCrawler() 