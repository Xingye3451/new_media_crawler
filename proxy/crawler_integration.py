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
代理管理系统与爬虫的集成示例
展示如何在爬取过程中使用代理
"""

import asyncio
import time
from typing import Dict, Optional, Tuple
from contextlib import asynccontextmanager

from playwright.async_api import BrowserContext, BrowserType
import httpx

from .proxy_manager import ProxyManager, ProxyInfo


class ProxyCrawlerMixin:
    """代理爬虫混入类，提供代理管理功能"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.current_proxy: Optional[ProxyInfo] = None
        self.proxy_retry_count = 0
        self.max_proxy_retries = 3
    
    async def get_proxy_for_platform(self, platform: str, strategy: str = "smart") -> Optional[ProxyInfo]:
        """为指定平台获取代理"""
        try:
            proxy = await self.proxy_manager.get_proxy(strategy, platform=platform)
            if proxy:
                self.current_proxy = proxy
                self.proxy_retry_count = 0
                print(f"[代理] 使用代理: {proxy.ip}:{proxy.port} ({proxy.proxy_type})")
            return proxy
        except Exception as e:
            print(f"[代理] 获取代理失败: {e}")
            return None
    
    async def mark_proxy_success(self):
        """标记当前代理使用成功"""
        if self.current_proxy:
            await self.proxy_manager.mark_proxy_success(self.current_proxy.id)
    
    async def mark_proxy_failed(self, error_message: str = None):
        """标记当前代理使用失败"""
        if self.current_proxy:
            await self.proxy_manager.mark_proxy_failed(self.current_proxy.id, error_message)
            self.proxy_retry_count += 1
    
    def format_proxy_for_playwright(self, proxy: ProxyInfo) -> Dict:
        """格式化代理信息为Playwright格式"""
        if not proxy:
            return None
        
        proxy_config = {
            "server": f"{proxy.proxy_type}://{proxy.ip}:{proxy.port}"
        }
        
        if proxy.username and proxy.password:
            proxy_config["username"] = proxy.username
            proxy_config["password"] = proxy.password
        
        return proxy_config
    
    def format_proxy_for_httpx(self, proxy: ProxyInfo) -> str:
        """格式化代理信息为httpx格式"""
        if not proxy:
            return None
        
        return proxy.proxy_url
    
    @asynccontextmanager
    async def proxy_context(self, platform: str, strategy: str = "smart"):
        """代理上下文管理器"""
        proxy = await self.get_proxy_for_platform(platform, strategy)
        try:
            yield proxy
            if proxy:
                await self.mark_proxy_success()
        except Exception as e:
            if proxy:
                await self.mark_proxy_failed(str(e))
            raise


class EnhancedCrawler(ProxyCrawlerMixin):
    """增强版爬虫基类，集成代理管理"""
    
    def __init__(self, platform: str):
        super().__init__()
        self.platform = platform
        self.browser_context: Optional[BrowserContext] = None
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def launch_browser_with_proxy(self, chromium: BrowserType, user_agent: str, headless: bool = True) -> BrowserContext:
        """使用代理启动浏览器"""
        async with self.proxy_context(self.platform, "smart") as proxy:
            playwright_proxy = self.format_proxy_for_playwright(proxy)
            
            # 启动浏览器上下文
            context = await chromium.launch_persistent_context(
                user_data_dir="./browser_data",
                headless=headless,
                proxy=playwright_proxy,
                user_agent=user_agent,
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
            
            self.browser_context = context
            return context
    
    async def create_http_client_with_proxy(self) -> httpx.AsyncClient:
        """创建带代理的HTTP客户端"""
        async with self.proxy_context(self.platform, "smart") as proxy:
            httpx_proxy = self.format_proxy_for_httpx(proxy)
            
            client = httpx.AsyncClient(
                proxies=httpx_proxy,
                timeout=httpx.Timeout(30.0),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            self.http_client = client
            return client
    
    async def make_request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带重试和代理切换的HTTP请求"""
        for attempt in range(self.max_proxy_retries + 1):
            try:
                if not self.http_client:
                    await self.create_http_client_with_proxy()
                
                response = await self.http_client.request(method, url, **kwargs)
                
                # 检查响应状态
                if response.status_code in [200, 201, 202]:
                    return response
                elif response.status_code in [403, 429, 500, 502, 503, 504]:
                    # 可能是代理问题，切换代理
                    print(f"[代理] 请求失败，状态码: {response.status_code}，尝试切换代理")
                    await self.mark_proxy_failed(f"HTTP {response.status_code}")
                    await self.create_http_client_with_proxy()
                    continue
                else:
                    return response
                    
            except Exception as e:
                print(f"[代理] 请求异常: {e}，尝试切换代理")
                await self.mark_proxy_failed(str(e))
                if attempt < self.max_proxy_retries:
                    await self.create_http_client_with_proxy()
                    await asyncio.sleep(1)
                else:
                    raise
        
        raise Exception("所有代理重试失败")
    
    async def crawl_with_proxy_rotation(self, urls: list):
        """使用代理轮换进行爬取"""
        results = []
        
        for i, url in enumerate(urls):
            print(f"[爬取] 处理第 {i+1}/{len(urls)} 个URL: {url}")
            
            try:
                # 为每个请求选择最佳代理
                strategy = "smart" if i % 10 == 0 else "round_robin"  # 每10个请求使用智能策略
                async with self.proxy_context(self.platform, strategy) as proxy:
                    response = await self.make_request_with_retry("GET", url)
                    results.append({
                        "url": url,
                        "status": response.status_code,
                        "proxy": f"{proxy.ip}:{proxy.port}" if proxy else "direct",
                        "content_length": len(response.content)
                    })
                    
                    # 添加延迟避免请求过快
                    await asyncio.sleep(random.uniform(1, 3))
                    
            except Exception as e:
                print(f"[爬取] 处理URL失败: {url}, 错误: {e}")
                results.append({
                    "url": url,
                    "status": "error",
                    "proxy": "failed",
                    "error": str(e)
                })
        
        return results


# 使用示例
async def example_usage():
    """使用示例"""
    # 创建增强版爬虫
    crawler = EnhancedCrawler("xhs")  # 小红书平台
    
    # 示例URL列表
    urls = [
        "https://www.xiaohongshu.com/explore/...",
        "https://www.xiaohongshu.com/explore/...",
        # ... 更多URL
    ]
    
    # 使用代理轮换爬取
    results = await crawler.crawl_with_proxy_rotation(urls)
    
    # 输出结果
    for result in results:
        print(f"URL: {result['url']}")
        print(f"状态: {result['status']}")
        print(f"代理: {result['proxy']}")
        print("---")


if __name__ == "__main__":
    asyncio.run(example_usage()) 