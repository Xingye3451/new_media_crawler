# 代理集成使用示例

## 概述

本文档展示了如何在MediaCrawler项目中集成青果长效代理，实现Cookie-IP绑定的反爬策略。

## 🎯 核心设计

### 1. 数据库表结构

#### proxy_pool表（代理池）
```sql
CREATE TABLE `proxy_pool` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `proxy_id` varchar(100) NOT NULL COMMENT '代理唯一标识',
  `ip` varchar(45) NOT NULL COMMENT '代理IP地址',
  `port` int(11) NOT NULL COMMENT '代理端口',
  `proxy_type` varchar(10) NOT NULL DEFAULT 'http' COMMENT '代理类型',
  `username` varchar(100) DEFAULT NULL COMMENT '代理用户名',
  `password` varchar(100) DEFAULT NULL COMMENT '代理密码',
  `country` varchar(50) DEFAULT NULL COMMENT '代理所在国家/地区',
  `speed` int(11) DEFAULT '0' COMMENT '代理速度(ms)',
  `anonymity` varchar(20) DEFAULT NULL COMMENT '匿名级别',
  `success_rate` float DEFAULT '0' COMMENT '成功率(0-100)',
  `expire_ts` bigint(20) DEFAULT NULL COMMENT '代理过期时间戳',
  `platform` varchar(20) DEFAULT NULL COMMENT '关联平台(dy,xhs,ks,bili)',
  `account_id` int(11) DEFAULT NULL COMMENT '关联账号ID',
  `provider` varchar(50) DEFAULT 'qingguo' COMMENT '代理提供商',
  `usage_count` int(11) DEFAULT 0 COMMENT '使用次数',
  `success_count` int(11) DEFAULT 0 COMMENT '成功次数',
  `fail_count` int(11) DEFAULT 0 COMMENT '失败次数',
  `status` varchar(20) DEFAULT 'active' COMMENT '代理状态',
  `last_check` timestamp NULL DEFAULT NULL COMMENT '最后检查时间',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_proxy_id` (`proxy_id`),
  KEY `idx_ip_port` (`ip`,`port`),
  KEY `idx_platform` (`platform`),
  KEY `idx_provider` (`provider`),
  KEY `idx_status` (`status`),
  KEY `idx_expire_ts` (`expire_ts`)
);
```

#### login_tokens表（登录令牌）
```sql
CREATE TABLE `login_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account_id` int(11) NOT NULL COMMENT '关联的账号ID',
  `platform` varchar(20) NOT NULL COMMENT '平台名称',
  `token_type` varchar(20) DEFAULT 'cookie' COMMENT '令牌类型',
  `token_data` text COMMENT '令牌数据(JSON格式)',
  `user_agent` text COMMENT '用户代理',
  `proxy_info` text COMMENT '代理信息(JSON格式)',
  `proxy_id` varchar(64) DEFAULT NULL COMMENT '代理ID',
  `is_valid` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `expires_at` timestamp NULL DEFAULT NULL COMMENT '过期时间',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_proxy_id` (`proxy_id`),
  KEY `idx_is_valid` (`is_valid`)
);
```

## 🚀 使用流程

### 1. 配置代理

#### 环境变量配置
```bash
# 青果代理配置
export QG_PROXY_KEY="your_qingguo_key_here"
export QG_PROXY_PWD="your_qingguo_password_here"  # 可选

# 启用代理功能
export ENABLE_IP_PROXY="true"
```

#### 配置文件设置
```yaml
# config/config_local.yaml
proxy:
  provider_name: "qingguo"
  enabled: true
  pool_count: 5
  validate_ip: true
  
  # 青果代理配置
  qingguo_key: "your_qingguo_key_here"
  qingguo_pwd: "your_qingguo_password_here"
```

### 2. 登录时使用代理

```python
from api.login_proxy_helper import get_proxy_for_login, save_login_token_with_proxy

async def login_with_proxy(platform: str, account_id: int):
    """使用代理进行登录"""
    
    # 1. 获取代理
    proxy_info = await get_proxy_for_login(platform, account_id)
    
    if not proxy_info:
        print("获取代理失败，使用直连登录")
        # 执行直连登录逻辑
        return await login_without_proxy(platform, account_id)
    
    print(f"使用代理登录: {proxy_info.ip}:{proxy_info.port}")
    
    # 2. 使用代理进行登录
    try:
        # 创建带代理的浏览器上下文
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            # 配置代理
            proxy_config = {
                "server": f"{proxy_info.proxy_type}://{proxy_info.ip}:{proxy_info.port}"
            }
            
            if proxy_info.username:
                proxy_config["username"] = proxy_info.username
            
            if proxy_info.password:
                proxy_config["password"] = proxy_info.password
            
            # 创建浏览器上下文
            context = await browser.new_context(proxy=proxy_config)
            page = await context.new_page()
            
            # 执行登录逻辑
            cookies = await perform_login(page, platform)
            
            # 3. 保存登录令牌和代理信息
            await save_login_token_with_proxy(
                account_id=account_id,
                platform=platform,
                token_data=json.dumps(cookies),
                user_agent=await page.evaluate("() => navigator.userAgent"),
                proxy_info=proxy_info,
                expires_at=datetime.now() + timedelta(days=7)
            )
            
            print("登录成功，代理信息已保存")
            return True
            
    except Exception as e:
        print(f"代理登录失败: {e}")
        # 标记代理使用失败
        from api.login_proxy_helper import update_login_token_proxy_usage
        await update_login_token_proxy_usage(account_id, platform, success=False, error_message=str(e))
        return False
```

### 3. 爬取时使用相同代理

```python
from api.login_proxy_helper import get_proxy_from_login_token

async def crawl_with_same_proxy(platform: str, account_id: int, keywords: str):
    """使用登录时的相同代理进行爬取"""
    
    # 1. 获取登录时使用的代理
    proxy_info = await get_proxy_from_login_token(account_id, platform)
    
    if not proxy_info:
        print("未找到登录代理，使用新代理")
        # 获取新代理的逻辑
        return await crawl_with_new_proxy(platform, account_id, keywords)
    
    print(f"使用登录代理爬取: {proxy_info.ip}:{proxy_info.port}")
    
    # 2. 使用相同代理进行爬取
    try:
        # 创建爬虫实例
        crawler = create_crawler(platform)
        
        # 设置代理信息
        crawler.proxy_info = proxy_info
        
        # 执行爬取
        results = await crawler.search_by_keywords(
            keywords=keywords,
            max_count=100,
            account_id=account_id,
            use_proxy=True,
            proxy_strategy="same_as_login"
        )
        
        # 3. 标记代理使用成功
        from api.login_proxy_helper import update_login_token_proxy_usage
        await update_login_token_proxy_usage(account_id, platform, success=True)
        
        print("爬取成功")
        return results
        
    except Exception as e:
        print(f"代理爬取失败: {e}")
        # 标记代理使用失败
        from api.login_proxy_helper import update_login_token_proxy_usage
        await update_login_token_proxy_usage(account_id, platform, success=False, error_message=str(e))
        return None
```

### 4. 代理管理界面

访问代理管理界面：`http://localhost:8100/static/proxy_management.html`

功能包括：
- 代理列表查看
- 代理状态筛选
- 代理测试
- 代理统计
- 过期代理清理

## 📊 代理使用统计

### 1. 查看代理统计
```python
from api.proxy_management import get_proxy_stats

async def view_proxy_stats():
    """查看代理统计信息"""
    stats = await get_proxy_stats()
    
    print(f"总代理数: {stats.total_proxies}")
    print(f"活跃代理: {stats.active_proxies}")
    print(f"平均成功率: {stats.avg_success_rate}%")
    print(f"总使用次数: {stats.total_usage_count}")
    
    print("\n按提供商统计:")
    for provider, count in stats.by_provider.items():
        print(f"  {provider}: {count}")
    
    print("\n按平台统计:")
    for platform, count in stats.by_platform.items():
        print(f"  {platform}: {count}")
```

### 2. 测试代理连接
```python
from api.proxy_management import test_proxy

async def test_proxy_connection(proxy_id: str):
    """测试代理连接"""
    result = await test_proxy(proxy_id)
    
    if result.success:
        print(f"代理测试成功，速度: {result.speed}ms")
        print(f"返回IP: {result.response.get('origin')}")
    else:
        print(f"代理测试失败: {result.error}")
```

## 🔧 高级配置

### 1. 代理轮换策略
```python
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager

async def smart_proxy_rotation(platform: str, account_id: int):
    """智能代理轮换"""
    proxy_manager = await get_qingguo_proxy_manager()
    
    # 获取多个候选代理
    candidates = await proxy_manager.get_candidate_proxies(platform, account_id, limit=3)
    
    for proxy in candidates:
        try:
            # 测试代理
            if await test_proxy_connection(proxy.proxy_id):
                return proxy
        except Exception as e:
            print(f"代理 {proxy.ip}:{proxy.port} 测试失败: {e}")
            continue
    
    # 如果所有候选代理都失败，获取新代理
    return await proxy_manager.extract_proxy(platform, account_id)
```

### 2. 代理健康检查
```python
async def health_check_proxies():
    """代理健康检查"""
    from api.proxy_management import cleanup_expired_proxies
    
    # 清理过期代理
    result = await cleanup_expired_proxies()
    print(f"清理了 {result.affected_rows} 个过期代理")
    
    # 测试活跃代理
    # ... 测试逻辑
```

## ⚠️ 注意事项

### 1. 反爬策略
- **Cookie-IP绑定**: 确保登录和爬取使用相同IP
- **请求频率控制**: 合理控制请求间隔
- **User-Agent轮换**: 避免使用固定User-Agent
- **地理位置一致性**: 保持IP地理位置稳定

### 2. 代理管理
- **定期清理**: 自动清理过期代理
- **失败处理**: 失败次数过多时标记为无效
- **负载均衡**: 合理分配代理使用

### 3. 成本控制
- **按需提取**: 只在需要时提取代理
- **复用策略**: 优先使用现有代理
- **监控使用**: 跟踪代理使用情况

## 🛠️ 故障排除

### 1. 代理获取失败
```python
# 检查配置
import os
print(f"代理Key: {os.getenv('QG_PROXY_KEY')}")
print(f"代理启用: {os.getenv('ENABLE_IP_PROXY')}")

# 检查余额
proxy_manager = await get_qingguo_proxy_manager()
balance = await proxy_manager.get_balance()
print(f"账户余额: {balance}")
```

### 2. 代理连接失败
```python
# 检查代理状态
query = "SELECT * FROM proxy_pool WHERE status = 'active'"
proxies = await db.query(query)
print(f"活跃代理数量: {len(proxies)}")
```

### 3. 登录代理不匹配
```python
# 检查登录令牌
query = "SELECT proxy_info FROM login_tokens WHERE account_id = %s AND platform = %s"
result = await db.get_first(query, account_id, platform)
print(f"登录代理信息: {result}")
```

## 📈 性能优化

### 1. 代理池管理
- 预提取代理，减少API调用
- 智能代理选择，优先使用成功率高的代理
- 自动代理轮换，避免单一代理过载

### 2. 数据库优化
- 添加合适的索引
- 定期清理过期数据
- 使用连接池管理数据库连接

### 3. 缓存策略
- 缓存代理信息，减少数据库查询
- 缓存登录状态，提高响应速度
- 使用Redis缓存热点数据

这个集成方案完美解决了您提到的反爬问题，通过Cookie-IP绑定策略，大大降低了被检测的风险。同时，长效代理的成本效益也很高，适合长期使用。
