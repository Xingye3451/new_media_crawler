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
增强版小红书爬虫示例
展示如何集成新的代理管理系统到现有爬虫中
"""

import asyncio
import random
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright
import httpx

from .proxy_manager import ProxyManager, ProxyInfo
from .crawler_integration import ProxyCrawlerMixin


class EnhancedXHSCrawler(ProxyCrawlerMixin):
    """增强版小红书爬虫，集成代理管理"""
    
    def __init__(self):
        super().__init__()
        self.platform = "xhs"
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # 代理配置
        self.proxy_strategy = "smart"  # 默认使用智能策略
        self.enable_proxy_rotation = True  # 启用代理轮换
        self.proxy_rotation_interval = 50  # 每50个请求轮换一次代理
        
    async def start(self) -> None:
        """启动爬虫"""
        print("[增强爬虫] 启动小红书爬虫...")
        
        try:
            async with async_playwright() as playwright:
                chromium = playwright.chromium
                
                # 使用代理启动浏览器
                await self.launch_browser_with_proxy(chromium)
                
                # 创建HTTP客户端
                await self.create_http_client_with_proxy()
                
                # 执行爬取任务
                await self.perform_crawling_tasks()
                
        except Exception as e:
            print(f"[增强爬虫] 爬虫运行异常: {e}")
            await self.mark_proxy_failed(str(e))
        finally:
            await self.cleanup()
    
    async def launch_browser_with_proxy(self, chromium: BrowserType) -> None:
        """使用代理启动浏览器"""
        print("[增强爬虫] 正在启动浏览器...")
        
        async with self.proxy_context(self.platform, self.proxy_strategy) as proxy:
            playwright_proxy = self.format_proxy_for_playwright(proxy)
            
            # 启动浏览器上下文
            self.browser_context = await chromium.launch_persistent_context(
                user_data_dir="./browser_data_xhs",
                headless=False,  # 调试时设为False
                proxy=playwright_proxy,
                user_agent=self.user_agent,
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
            
            # 添加反检测脚本
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            
            # 添加cookie避免滑动验证码
            await self.browser_context.add_cookies([
                {
                    "name": "webId",
                    "value": "xxx123",
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                }
            ])
            
            # 创建新页面
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)
            
            print(f"[增强爬虫] 浏览器启动成功，使用代理: {proxy.ip}:{proxy.port}" if proxy else "[增强爬虫] 浏览器启动成功，直连模式")
    
    async def create_http_client_with_proxy(self) -> None:
        """创建带代理的HTTP客户端"""
        print("[增强爬虫] 正在创建HTTP客户端...")
        
        async with self.proxy_context(self.platform, self.proxy_strategy) as proxy:
            httpx_proxy = self.format_proxy_for_httpx(proxy)
            
            self.http_client = httpx.AsyncClient(
                proxies=httpx_proxy,
                timeout=httpx.Timeout(30.0),
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            print(f"[增强爬虫] HTTP客户端创建成功，使用代理: {proxy.ip}:{proxy.port}" if proxy else "[增强爬虫] HTTP客户端创建成功，直连模式")
    
    async def perform_crawling_tasks(self) -> None:
        """执行爬取任务"""
        print("[增强爬虫] 开始执行爬取任务...")
        
        # 示例：搜索关键词
        keywords = ["美食", "旅游", "穿搭"]
        
        for keyword in keywords:
            print(f"[增强爬虫] 搜索关键词: {keyword}")
            
            try:
                # 使用代理进行搜索
                search_results = await self.search_with_proxy(keyword)
                
                # 处理搜索结果
                for result in search_results:
                    await self.process_note_with_proxy(result)
                    
                    # 添加延迟
                    await asyncio.sleep(random.uniform(2, 5))
                    
            except Exception as e:
                print(f"[增强爬虫] 搜索关键词 {keyword} 失败: {e}")
                await self.mark_proxy_failed(str(e))
                
                # 如果失败，尝试切换代理策略
                if self.enable_proxy_rotation:
                    await self.rotate_proxy_strategy()
    
    async def search_with_proxy(self, keyword: str) -> List[Dict]:
        """使用代理搜索内容"""
        print(f"[增强爬虫] 使用代理搜索: {keyword}")
        
        # 模拟搜索API调用
        search_url = f"https://www.xiaohongshu.com/api/sns/v1/search/notes?keyword={keyword}"
        
        try:
            response = await self.make_request_with_retry("GET", search_url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("notes", [])
            else:
                print(f"[增强爬虫] 搜索请求失败，状态码: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[增强爬虫] 搜索异常: {e}")
            await self.mark_proxy_failed(str(e))
            return []
    
    async def process_note_with_proxy(self, note_data: Dict) -> None:
        """使用代理处理笔记详情"""
        note_id = note_data.get("id")
        if not note_id:
            return
            
        print(f"[增强爬虫] 处理笔记: {note_id}")
        
        try:
            # 获取笔记详情
            detail_url = f"https://www.xiaohongshu.com/api/sns/v1/note/{note_id}/detail"
            response = await self.make_request_with_retry("GET", detail_url)
            
            if response.status_code == 200:
                note_detail = response.json()
                
                # 保存笔记数据
                await self.save_note_data(note_detail)
                
                # 获取评论
                await self.get_comments_with_proxy(note_id)
                
            else:
                print(f"[增强爬虫] 获取笔记详情失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"[增强爬虫] 处理笔记异常: {e}")
            await self.mark_proxy_failed(str(e))
    
    async def get_comments_with_proxy(self, note_id: str) -> None:
        """使用代理获取评论"""
        print(f"[增强爬虫] 获取评论: {note_id}")
        
        try:
            comments_url = f"https://www.xiaohongshu.com/api/sns/v1/note/{note_id}/comments"
            response = await self.make_request_with_retry("GET", comments_url)
            
            if response.status_code == 200:
                comments_data = response.json()
                comments = comments_data.get("data", {}).get("comments", [])
                
                # 保存评论数据
                await self.save_comments_data(note_id, comments)
                
            else:
                print(f"[增强爬虫] 获取评论失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"[增强爬虫] 获取评论异常: {e}")
            await self.mark_proxy_failed(str(e))
    
    async def save_note_data(self, note_detail: Dict) -> None:
        """保存笔记数据"""
        # 这里实现数据保存逻辑
        print(f"[增强爬虫] 保存笔记数据: {note_detail.get('id', 'unknown')}")
        # TODO: 实现具体的数据保存逻辑
    
    async def save_comments_data(self, note_id: str, comments: List[Dict]) -> None:
        """保存评论数据"""
        # 这里实现评论保存逻辑
        print(f"[增强爬虫] 保存评论数据: 笔记{note_id}，评论数量{len(comments)}")
        # TODO: 实现具体的评论保存逻辑
    
    async def rotate_proxy_strategy(self) -> None:
        """轮换代理策略"""
        strategies = ["smart", "round_robin", "random", "weighted"]
        current_index = strategies.index(self.proxy_strategy)
        next_index = (current_index + 1) % len(strategies)
        self.proxy_strategy = strategies[next_index]
        
        print(f"[增强爬虫] 切换代理策略: {self.proxy_strategy}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        print("[增强爬虫] 正在清理资源...")
        
        if self.http_client:
            await self.http_client.aclose()
        
        if self.browser_context:
            await self.browser_context.close()
        
        print("[增强爬虫] 资源清理完成")


# 使用示例
async def run_enhanced_xhs_crawler():
    """运行增强版小红书爬虫"""
    crawler = EnhancedXHSCrawler()
    
    # 配置代理策略
    crawler.proxy_strategy = "smart"  # 使用智能策略
    crawler.enable_proxy_rotation = True  # 启用代理轮换
    
    try:
        await crawler.start()
    except Exception as e:
        print(f"[主程序] 爬虫运行失败: {e}")


if __name__ == "__main__":
    asyncio.run(run_enhanced_xhs_crawler()) 