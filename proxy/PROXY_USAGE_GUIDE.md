# 代理管理系统使用指南

## 概述

本文档详细说明代理管理系统在MediaCrawler项目中的运用机制，包括代理的选择、使用、故障处理和优化策略。

## 支持的代理提供商

### 1. 青果代理 (Qingguo Proxy)
- **官方文档**: https://www.qg.net/doc/2145.html
- **配置方式**: 
  ```bash
  # 环境变量配置
  export qg_key="你的青果代理Key"
  export qg_pwd="你的青果代理密码"  # 可选
  ```
- **配置文件设置**:
  ```python
  # config/base_config.py
  IP_PROXY_PROVIDER_NAME = "qingguo"  # 使用青果代理
  ENABLE_IP_PROXY = True              # 启用代理
  IP_PROXY_POOL_COUNT = 5             # 代理池数量
  ```

### 2. 快代理 (KuaiDaili Proxy)
- **配置方式**:
  ```bash
  export kdl_secret_id="你的快代理secret_id"
  export kdl_signature="你的快代理签名"
  export kdl_user_name="你的快代理用户名"
  export kdl_user_pwd="你的快代理密码"
  ```

### 3. 极速HTTP代理 (JiSu HTTP Proxy)
- **配置方式**:
  ```bash
  export jisu_http_key="你的极速HTTP代理Key"
  ```

## 代理在爬取过程中的运用机制

### 1. 代理选择策略

#### A. 智能策略 (Smart Strategy)
```python
# 根据多个因素综合选择最佳代理
- 成功率 (success_rate)
- 响应速度 (speed)
- 地理位置 (country/region)
- 匿名级别 (anonymity)
- 平台适配性 (platform)
```

#### B. 轮询策略 (Round Robin)
```python
# 按顺序轮流使用代理
proxy1 -> proxy2 -> proxy3 -> proxy1 -> ...
```

#### C. 随机策略 (Random)
```python
# 随机选择可用代理
random.choice(available_proxies)
```

#### D. 权重策略 (Weighted)
```python
# 根据权重概率选择代理
weights = [proxy.priority for proxy in proxies]
selected = random.choices(proxies, weights=weights, k=1)[0]
```

#### E. 故障转移策略 (Failover)
```python
# 按优先级顺序尝试代理
priority_order = ["elite", "anonymous", "transparent"]
for anonymity in priority_order:
    proxy = get_proxy_by_anonymity(anonymity)
    if proxy and test_proxy(proxy):
        return proxy
```

#### F. 地理位置策略 (Geo-based)
```python
# 根据目标网站地理位置选择代理
if target_platform == "xhs":
    preferred_countries = ["CN", "HK", "TW"]
elif target_platform == "douyin":
    preferred_countries = ["CN"]
```

### 2. 代理在浏览器自动化中的运用

#### A. Playwright 代理配置
```python
async def launch_browser_with_proxy(self, chromium: BrowserType):
    async with self.proxy_context(self.platform, "smart") as proxy:
        playwright_proxy = self.format_proxy_for_playwright(proxy)
        
        context = await chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            proxy=playwright_proxy,  # 使用代理
            user_agent=self.user_agent,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
```

#### B. 代理格式转换
```python
def format_proxy_for_playwright(self, proxy: ProxyInfo) -> Dict:
    """转换为Playwright代理格式"""
    proxy_config = {
        "server": f"{proxy.proxy_type}://{proxy.ip}:{proxy.port}"
    }
    
    if proxy.username and proxy.password:
        proxy_config["username"] = proxy.username
        proxy_config["password"] = proxy.password
    
    return proxy_config
```

### 3. 代理在HTTP请求中的运用

#### A. httpx 代理配置
```python
async def create_http_client_with_proxy(self):
    async with self.proxy_context(self.platform, "smart") as proxy:
        httpx_proxy = self.format_proxy_for_httpx(proxy)
        
        self.http_client = httpx.AsyncClient(
            proxies=httpx_proxy,  # 使用代理
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/plain, */*"
            }
        )
```

#### B. 带重试的HTTP请求
```python
async def make_request_with_retry(self, method: str, url: str, **kwargs):
    """带重试和代理切换的HTTP请求"""
    for attempt in range(self.max_proxy_retries + 1):
        try:
            response = await self.http_client.request(method, url, **kwargs)
            
            # 检查响应状态
            if response.status_code in [200, 201, 202]:
                return response
            elif response.status_code in [403, 429, 500, 502, 503, 504]:
                # 可能是代理问题，切换代理
                await self.mark_proxy_failed(f"HTTP {response.status_code}")
                await self.create_http_client_with_proxy()
                continue
                
        except Exception as e:
            await self.mark_proxy_failed(str(e))
            if attempt < self.max_proxy_retries:
                await self.create_http_client_with_proxy()
                await asyncio.sleep(1)
            else:
                raise
```

### 4. 代理故障处理机制

#### A. 自动故障检测
```python
async def check_proxy(self, proxy_info: ProxyInfo) -> bool:
    """检测代理可用性"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://httpbin.org/ip',
                proxy=proxy_info.proxy_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
    except:
        return False
```

#### B. 故障标记和统计
```python
async def mark_proxy_failed(self, proxy_id: int, error_message: str = None):
    """标记代理失败"""
    await self.db.execute(
        "UPDATE proxy_pool SET fail_count = fail_count + 1, "
        "total_requests = total_requests + 1, last_check_result = 0, "
        "last_modify_ts = %s WHERE id = %s",
        (int(time.time() * 1000), proxy_id)
    )
    
    # 记录失败日志
    await self.db.execute(
        "INSERT INTO proxy_usage_log (proxy_id, success, error_message, add_ts) "
        "VALUES (%s, 0, %s, %s)",
        (proxy_id, error_message, int(time.time() * 1000))
    )
```

#### C. 自动代理切换
```python
async def rotate_proxy_strategy(self):
    """轮换代理策略"""
    strategies = ["smart", "round_robin", "random", "weighted"]
    current_index = strategies.index(self.proxy_strategy)
    next_index = (current_index + 1) % len(strategies)
    self.proxy_strategy = strategies[next_index]
```

### 5. 代理轮换策略

#### A. 基于请求数量的轮换
```python
# 每50个请求轮换一次代理
self.proxy_rotation_interval = 50

if request_count % self.proxy_rotation_interval == 0:
    await self.rotate_proxy()
```

#### B. 基于时间的轮换
```python
# 每30分钟轮换一次代理
rotation_interval = 30 * 60  # 30分钟

if time.time() - self.last_rotation > rotation_interval:
    await self.rotate_proxy()
    self.last_rotation = time.time()
```

#### C. 基于错误的轮换
```python
# 遇到特定错误时轮换代理
error_codes = [403, 429, 500, 502, 503, 504]

if response.status_code in error_codes:
    await self.mark_proxy_failed(f"HTTP {response.status_code}")
    await self.rotate_proxy()
```

### 6. 代理性能优化

#### A. 代理缓存机制
```python
class RoundRobinStrategy(ProxyStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.proxy_cache: List[ProxyInfo] = []
        self.last_refresh = 0
    
    async def select_proxy(self, platform: str = None, **kwargs):
        # 每5分钟刷新一次代理列表
        if time.time() - self.last_refresh > 300:
            await self._refresh_proxy_list()
        
        if not self.proxy_cache:
            return None
        
        # 轮询选择
        proxy = self.proxy_cache[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_cache)
        
        return proxy
```

#### B. 代理健康检查
```python
async def health_check_proxies(self):
    """定期健康检查代理"""
    while True:
        try:
            # 获取所有代理
            proxies = await self.get_all_proxies()
            
            # 并发检查代理健康状态
            tasks = [self.check_proxy(proxy) for proxy in proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 更新代理状态
            for proxy, is_healthy in zip(proxies, results):
                if isinstance(is_healthy, bool):
                    await self.update_proxy_health(proxy.id, is_healthy)
            
            # 每10分钟检查一次
            await asyncio.sleep(600)
            
        except Exception as e:
            print(f"代理健康检查异常: {e}")
            await asyncio.sleep(60)
```

### 7. 实际应用场景

#### A. 小红书爬虫代理应用
```python
class EnhancedXHSCrawler(ProxyCrawlerMixin):
    async def search_with_proxy(self, keyword: str) -> List[Dict]:
        """使用代理搜索内容"""
        search_url = f"https://www.xiaohongshu.com/api/sns/v1/search/notes?keyword={keyword}"
        
        try:
            response = await self.make_request_with_retry("GET", search_url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("notes", [])
            else:
                print(f"搜索请求失败，状态码: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"搜索异常: {e}")
            await self.mark_proxy_failed(str(e))
            return []
```

#### B. 抖音爬虫代理应用
```python
class EnhancedDouyinCrawler(ProxyCrawlerMixin):
    async def get_video_info_with_proxy(self, video_id: str) -> Dict:
        """使用代理获取视频信息"""
        video_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
        
        try:
            response = await self.make_request_with_retry("GET", video_url)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取视频信息失败，状态码: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"获取视频信息异常: {e}")
            await self.mark_proxy_failed(str(e))
            return {}
```

### 8. 监控和统计

#### A. 代理使用统计
```python
async def get_proxy_stats(self) -> Dict[str, Any]:
    """获取代理统计信息"""
    stats = await self.db.fetch_one("""
        SELECT 
            COUNT(*) as total_proxies,
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as active_proxies,
            SUM(CASE WHEN last_check_result = 1 THEN 1 ELSE 0 END) as healthy_proxies,
            AVG(speed) as avg_speed,
            AVG(success_count * 100.0 / NULLIF(total_requests, 0)) as avg_success_rate
        FROM proxy_pool
    """)
    
    return {
        "total_proxies": stats["total_proxies"],
        "active_proxies": stats["active_proxies"],
        "healthy_proxies": stats["healthy_proxies"],
        "avg_speed": round(stats["avg_speed"], 2) if stats["avg_speed"] else 0,
        "avg_success_rate": round(stats["avg_success_rate"], 2) if stats["avg_success_rate"] else 0
    }
```

#### B. 代理使用日志
```python
async def log_proxy_usage(self, proxy_id: int, success: bool, 
                         platform: str = None, url: str = None, 
                         response_time: float = None):
    """记录代理使用日志"""
    await self.db.execute("""
        INSERT INTO proxy_usage_log 
        (proxy_id, success, platform, url, response_time, add_ts)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (proxy_id, success, platform, url, response_time, int(time.time() * 1000)))
```

## 总结

代理管理系统在MediaCrawler项目中的运用主要体现在以下几个方面：

1. **智能选择**: 根据多种因素选择最佳代理
2. **自动切换**: 在代理故障时自动切换到备用代理
3. **性能优化**: 通过缓存和健康检查提高代理使用效率
4. **故障处理**: 完善的错误处理和重试机制
5. **监控统计**: 详细的代理使用统计和日志记录

这种设计确保了爬虫在各种网络环境下都能稳定运行，提高了爬取的成功率和效率。 