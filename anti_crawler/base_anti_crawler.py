"""
反爬虫基类
提供通用的反爬虫功能和接口
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from tools import utils


class BaseAntiCrawler(ABC):
    """反爬虫基类"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
        ]
        
        # 通用反爬虫特征
        self.common_anti_features = {
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
    
    @abstractmethod
    async def setup_enhanced_browser_context(self, browser_context) -> None:
        """设置增强的浏览器上下文"""
        pass
    
    @abstractmethod
    async def handle_frequency_limit(self, page, session_id: str) -> bool:
        """处理频率限制问题"""
        pass
    
    @abstractmethod
    async def simulate_human_behavior(self, page) -> None:
        """模拟人类行为"""
        pass
    
    @abstractmethod
    async def bypass_captcha(self, page, session_id: str) -> bool:
        """绕过验证码"""
        pass
    
    @abstractmethod
    async def enhance_page_loading(self, page, url: str) -> bool:
        """增强页面加载策略"""
        pass
    
    @abstractmethod
    async def get_optimal_login_url(self) -> str:
        """获取最优登录URL"""
        pass
    
    async def setup_proxy_rotation(self, browser_context) -> None:
        """设置代理轮换"""
        try:
            # 这里可以集成代理池
            utils.logger.info(f"🔄 [{self.platform.upper()}反爬] 代理轮换功能待实现")
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 设置代理轮换失败: {e}")
    
    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    async def inject_common_anti_detection_script(self, browser_context) -> None:
        """注入通用的反检测脚本"""
        try:
            await browser_context.add_init_script("""
                console.log('🛡️ [通用反爬] 开始注入反检测脚本');
                
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
                
                console.log('✅ [通用反爬] 反检测脚本注入完成');
            """)
            
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 注入通用反检测脚本失败: {e}")
    
    async def set_random_headers(self, browser_context) -> None:
        """设置随机请求头"""
        try:
            user_agent = self.get_random_user_agent()
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
                "Upgrade-Insecure-Requests": "1"
            })
            
            utils.logger.info(f"🛡️ [{self.platform.upper()}反爬] 设置随机请求头完成，User-Agent: {user_agent[:50]}...")
            
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 设置随机请求头失败: {e}")
    
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
                        utils.logger.info(f"🔄 [{self.platform.upper()}反爬] 刷新验证码: {selector}")
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # 2. 等待用户手动处理
            utils.logger.info(f"⏳ [{self.platform.upper()}反爬] 等待用户手动处理验证码...")
            
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
                    utils.logger.info(f"✅ [{self.platform.upper()}反爬] 验证码已处理完成")
                    return True
                
                await asyncio.sleep(1)
            
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 验证码处理超时")
            return False
            
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 自动处理验证码失败: {e}")
            return False
    
    def get_wait_time(self, base_time: float = 30.0, max_time: float = 120.0) -> float:
        """获取随机等待时间"""
        return random.uniform(base_time, max_time)
    
    async def safe_page_operation(self, page, operation: str, *args, **kwargs):
        """安全的页面操作"""
        try:
            if not page or page.is_closed():
                utils.logger.warning(f"⚠️ [{self.platform.upper()}反爬] 页面已关闭，跳过操作: {operation}")
                return None
            
            # 根据操作类型调用相应方法
            if operation == "reload":
                return await page.reload(*args, **kwargs)
            elif operation == "evaluate":
                return await page.evaluate(*args, **kwargs)
            elif operation == "title":
                return await page.title()
            elif operation == "text_content":
                return await page.text_content(*args, **kwargs)
            elif operation == "query_selector":
                return await page.query_selector(*args, **kwargs)
            elif operation == "mouse_move":
                return await page.mouse.move(*args, **kwargs)
            elif operation == "mouse_click":
                return await page.mouse.click(*args, **kwargs)
            else:
                utils.logger.warning(f"⚠️ [{self.platform.upper()}反爬] 未知的页面操作: {operation}")
                return None
                
        except Exception as e:
            utils.logger.error(f"❌ [{self.platform.upper()}反爬] 页面操作失败 {operation}: {e}")
            return None
