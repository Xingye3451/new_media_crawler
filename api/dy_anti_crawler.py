#!/usr/bin/env python3
"""
抖音反爬虫增强模块
专门针对抖音的反爬机制进行反制
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional
from tools import utils

class DYAntiCrawler:
    """抖音反爬虫增强类"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
        ]
        
        self.dy_domains = [
            "www.douyin.com",
            "m.douyin.com",
            "v.douyin.com"
        ]
        
        # 抖音特有的反爬虫特征
        self.dy_specific_features = {
            "webdriver_indicators": [
                "webdriver",
                "selenium",
                "puppeteer",
                "playwright",
                "cypress",
                "testcafe"
            ],
            "automation_indicators": [
                "navigator.webdriver",
                "window.webdriver",
                "window.__webdriver_script_fn",
                "window.__selenium_evaluate",
                "window.__webdriver_evaluate"
            ]
        }
    
    async def setup_enhanced_browser_context(self, browser_context) -> None:
        """设置增强的浏览器上下文"""
        try:
            # 注入增强的反检测脚本
            await browser_context.add_init_script("""
                console.log('🛡️ [DY反爬] 开始注入反检测脚本');
                
                // 1. 隐藏自动化特征
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // 2. 删除webdriver相关变量
                delete window.webdriver;
                delete window.__webdriver_script_fn;
                delete window.__webdriver_evaluate;
                delete window.__selenium_evaluate;
                delete window.__webdriver_unwrapped;
                delete window.__webdriver_script_func;
                delete window.__webdriver_script_fn;
                delete window.__$webdriverAsyncExecutor;
                delete window.__lastWatirAlert;
                delete window.__lastWatirConfirm;
                delete window.__lastWatirPrompt;
                
                // 3. 完善chrome对象
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
                
                // 4. 模拟真实的用户行为特征
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                    configurable: true
                });
                
                // 5. 隐藏自动化相关的CSS类
                const originalQuerySelector = document.querySelector;
                const originalQuerySelectorAll = document.querySelectorAll;
                
                document.querySelector = function(selector) {
                    if (selector.includes('webdriver') || selector.includes('selenium')) {
                        return null;
                    }
                    return originalQuerySelector.call(this, selector);
                };
                
                document.querySelectorAll = function(selector) {
                    if (selector.includes('webdriver') || selector.includes('selenium')) {
                        return [];
                    }
                    return originalQuerySelectorAll.call(this, selector);
                };
                
                // 6. 模拟真实的鼠标事件
                const originalAddEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    if (type === 'mousedown' || type === 'mouseup' || type === 'click') {
                        // 添加随机延迟
                        const originalListener = listener;
                        listener = function(event) {
                            setTimeout(() => {
                                originalListener.call(this, event);
                            }, Math.random() * 50);
                        };
                    }
                    return originalAddEventListener.call(this, type, listener, options);
                };
                
                // 7. 抖音特有的反爬虫处理
                // 隐藏抖音检测到的自动化特征
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
                
                // 8. 模拟真实的屏幕信息
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                    configurable: true
                });
                
                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                    configurable: true
                });
                
                // 9. 隐藏抖音的检测脚本
                const originalEval = window.eval;
                window.eval = function(code) {
                    if (code.includes('webdriver') || code.includes('selenium')) {
                        return undefined;
                    }
                    return originalEval.call(this, code);
                };
                
                console.log('✅ [DY反爬] 反检测脚本注入完成');
            """)
            
            # 设置随机User-Agent
            user_agent = random.choice(self.user_agents)
            await browser_context.set_extra_http_headers({
                "User-Agent": user_agent,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            })
            
            utils.logger.info(f"🛡️ [DY反爬] 浏览器上下文增强完成，User-Agent: {user_agent[:50]}...")
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 设置浏览器上下文失败: {e}")
    
    async def handle_frequency_limit(self, page, session_id: str) -> bool:
        """处理频率限制问题"""
        try:
            # 检查页面是否已关闭
            if not page or page.is_closed():
                utils.logger.warning("⚠️ [DY反爬] 页面已关闭，跳过频率限制检查")
                return False
            
            # 检查是否出现频率限制
            frequency_indicators = [
                "验证过于频繁",
                "请稍后重试",
                "访问过于频繁",
                "安全验证",
                "验证码",
                "请求过于频繁",
                "请稍后再试",
                "系统繁忙"
            ]
            
            try:
                page_content = await page.text_content("body")
                current_title = await page.title()
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 获取页面内容失败: {e}")
                return False
            
            for indicator in frequency_indicators:
                if indicator in page_content or indicator in current_title:
                    utils.logger.warning(f"⚠️ [DY反爬] 检测到频率限制: {indicator}")
                    
                    # 策略1: 等待随机时间
                    wait_time = random.uniform(30, 120)
                    utils.logger.info(f"⏳ [DY反爬] 等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)
                    
                    # 策略2: 刷新页面
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(random.uniform(3, 8))
                    except Exception as e:
                        utils.logger.warning(f"⚠️ [DY反爬] 页面刷新失败: {e}")
                    
                    # 策略3: 清除cookies和localStorage
                    try:
                        await page.evaluate("""
                            localStorage.clear();
                            sessionStorage.clear();
                            document.cookie.split(";").forEach(function(c) { 
                                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
                            });
                        """)
                    except Exception as e:
                        utils.logger.warning(f"⚠️ [DY反爬] 清除存储失败: {e}")
                    
                    return True
            
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 处理频率限制失败: {e}")
            return False
    
    async def simulate_human_behavior(self, page) -> None:
        """模拟人类行为"""
        try:
            # 检查页面是否已关闭
            if not page or page.is_closed():
                utils.logger.warning("⚠️ [DY反爬] 页面已关闭，跳过人类行为模拟")
                return
            
            # 1. 随机鼠标移动
            try:
                viewport = await page.viewport_size()
                if viewport:
                    # 智能获取viewport尺寸，支持多种类型
                    width = 1920
                    height = 1080
                    
                    if isinstance(viewport, dict):
                        # 字典类型
                        width = viewport.get('width', 1920)
                        height = viewport.get('height', 1080)
                    elif hasattr(viewport, 'width') and hasattr(viewport, 'height'):
                        # 对象类型
                        width = viewport.width
                        height = viewport.height
                    elif hasattr(viewport, 'get'):
                        # 有get方法的对象
                        width = viewport.get('width', 1920)
                        height = viewport.get('height', 1080)
                    
                    # 直接使用page.mouse，确保它是正确的对象
                    for _ in range(random.randint(2, 5)):
                        x = random.randint(100, width - 100)
                        y = random.randint(100, height - 100)
                        await page.mouse.move(x, y)
                        await asyncio.sleep(random.uniform(0.1, 0.5))
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 鼠标移动失败: {e}")
            
            # 2. 随机滚动
            try:
                await page.evaluate("""
                    window.scrollTo(0, Math.random() * 100);
                    setTimeout(() => {
                        window.scrollTo(0, 0);
                    }, Math.random() * 1000 + 500);
                """)
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 页面滚动失败: {e}")
            
            # 3. 随机点击空白区域
            try:
                await page.mouse.click(
                    random.randint(50, 200),
                    random.randint(50, 200)
                )
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 鼠标点击失败: {e}")
            
            await asyncio.sleep(random.uniform(1, 3))
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 模拟人类行为失败: {e}")
    
    async def bypass_captcha(self, page, session_id: str) -> bool:
        """绕过验证码"""
        try:
            # 检查页面是否已关闭
            if not page or page.is_closed():
                utils.logger.warning("⚠️ [DY反爬] 页面已关闭，跳过验证码检查")
                return True
            
            # 检查是否有验证码
            captcha_selectors = [
                ".captcha",
                ".verify",
                "[class*='captcha']",
                "[class*='verify']",
                "img[src*='captcha']",
                "img[src*='verify']",
                ".slide-captcha",
                ".geetest",
                ".tcaptcha"
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = await page.query_selector(selector)
                    if captcha_element and await captcha_element.is_visible():
                        utils.logger.warning(f"⚠️ [DY反爬] 检测到验证码: {selector}")
                        
                        # 尝试自动处理验证码
                        return await self.handle_auto_captcha(page, session_id)
                except Exception as e:
                    utils.logger.debug(f"🔍 [DY反爬] 验证码选择器 {selector} 检查失败: {e}")
                    continue
            
            return True
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 绕过验证码失败: {e}")
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
                        utils.logger.info(f"🔄 [DY反爬] 刷新验证码: {selector}")
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # 2. 等待用户手动处理
            utils.logger.info("⏳ [DY反爬] 等待用户手动处理验证码...")
            
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
                    utils.logger.info("✅ [DY反爬] 验证码已处理完成")
                    return True
                
                await asyncio.sleep(1)
            
            utils.logger.error("❌ [DY反爬] 验证码处理超时")
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 自动处理验证码失败: {e}")
            return False
    
    async def enhance_page_loading(self, page, url: str) -> bool:
        """增强页面加载策略"""
        try:
            # 检查页面是否已关闭
            if not page or page.is_closed():
                utils.logger.warning("⚠️ [DY反爬] 页面已关闭，跳过增强页面加载")
                return False
            
            # 1. 设置页面加载超时
            try:
                # 检查set_default_timeout是否为异步方法
                if hasattr(page, 'set_default_timeout'):
                    timeout_method = page.set_default_timeout
                    if asyncio.iscoroutinefunction(timeout_method):
                        await timeout_method(60000)
                    else:
                        # 如果是同步方法，直接调用
                        timeout_method(60000)
                else:
                    # 如果没有set_default_timeout方法，尝试使用set_default_navigation_timeout
                    if hasattr(page, 'set_default_navigation_timeout'):
                        nav_timeout_method = page.set_default_navigation_timeout
                        if asyncio.iscoroutinefunction(nav_timeout_method):
                            await nav_timeout_method(60000)
                        else:
                            nav_timeout_method(60000)
                    else:
                        utils.logger.info("ℹ️ [DY反爬] 页面对象没有超时设置方法，使用默认超时")
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 设置页面超时失败: {e}")
            
            # 2. 禁用图片和CSS以加快加载
            try:
                async def abort_route(route):
                    await route.abort()
                
                await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", abort_route)
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 禁用资源失败: {e}")
            
            # 3. 访问页面
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 页面访问失败: {e}")
                return False
            
            # 4. 等待页面稳定
            await asyncio.sleep(random.uniform(2, 5))
            
            # 5. 检查页面是否正常
            try:
                title = await page.title()
                if "抖音" in title or "douyin" in title.lower():
                    utils.logger.info(f"✅ [DY反爬] 页面加载成功: {title}")
                    return True
                else:
                    utils.logger.warning(f"⚠️ [DY反爬] 页面标题异常: {title}")
                    return False
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 获取页面标题失败: {e}")
                return False
                
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 增强页面加载失败: {e}")
            return False
    
    async def get_optimal_login_url(self) -> str:
        """获取最优登录URL"""
        # 根据时间选择不同的URL
        current_hour = time.localtime().tm_hour
        
        if 9 <= current_hour <= 18:  # 工作时间
            return "https://www.douyin.com"
        elif 19 <= current_hour <= 23:  # 晚上时间
            return "https://m.douyin.com"
        else:  # 凌晨时间
            return "https://www.douyin.com"
    
    async def setup_proxy_rotation(self, browser_context) -> None:
        """设置代理轮换"""
        try:
            # 这里可以集成代理池
            # 暂时使用基础配置
            utils.logger.info("🔄 [DY反爬] 代理轮换功能待实现")
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 设置代理轮换失败: {e}")
    
    async def handle_dy_specific_anti_crawler(self, page, session_id: str) -> bool:
        """处理抖音特有的反爬虫机制"""
        try:
            # 检查页面是否已关闭
            if not page or page.is_closed():
                utils.logger.warning("⚠️ [DY反爬] 页面已关闭，跳过抖音特有反爬虫检查")
                return False
            
            # 1. 检查抖音特有的反爬虫页面
            dy_anti_indicators = [
                "安全验证",
                "验证码",
                "请稍后再试",
                "系统繁忙",
                "访问过于频繁",
                "请求过于频繁"
            ]
            
            try:
                page_content = await page.text_content("body")
                current_title = await page.title()
            except Exception as e:
                utils.logger.warning(f"⚠️ [DY反爬] 获取页面内容失败: {e}")
                return False
            
            for indicator in dy_anti_indicators:
                if indicator in page_content or indicator in current_title:
                    utils.logger.warning(f"⚠️ [DY反爬] 检测到抖音反爬虫机制: {indicator}")
                    
                    # 等待更长时间
                    wait_time = random.uniform(60, 180)
                    utils.logger.info(f"⏳ [DY反爬] 等待 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)
                    
                    # 刷新页面
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(random.uniform(5, 10))
                    except Exception as e:
                        utils.logger.warning(f"⚠️ [DY反爬] 页面刷新失败: {e}")
                    
                    return True
            
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [DY反爬] 处理抖音特有反爬虫机制失败: {e}")
            return False

# 全局实例
dy_anti_crawler = DYAntiCrawler() 