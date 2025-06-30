# 青果代理使用指南

## 概述

青果代理是MediaCrawler项目支持的代理提供商之一，提供高质量的HTTP代理服务。本文档详细介绍如何在项目中使用青果代理。

## 快速开始

### 1. 获取青果代理账号

1. 访问 [青果代理官网](https://www.qg.net/)
2. 注册账号并购买代理服务
3. 获取API Key和密码（可选）

### 2. 环境配置

```bash
# 设置环境变量
export qg_key="你的青果代理Key"
export qg_pwd="你的青果代理密码"  # 可选，如果没有密码可以留空
```

### 3. 项目配置

修改 `config/base_config.py` 文件：

```python
# 启用代理
ENABLE_IP_PROXY = True

# 设置代理提供商为青果代理
IP_PROXY_PROVIDER_NAME = "qingguo"

# 设置代理池大小
IP_PROXY_POOL_COUNT = 5
```

## API接口说明

### 1. 获取代理IP

**接口**: `https://proxy.qg.net/allocate`

**参数**:
- `Key`: 你的API Key
- `Pwd`: 密码（可选）
- `num`: 获取的代理数量
- `format`: 返回格式（json/text）
- `sep`: 分隔符

**示例**:
```bash
curl "https://proxy.qg.net/allocate?Key=your_key&num=5&format=json&sep=1"
```

**返回格式**:
```
192.168.1.1:8080,1640995200
192.168.1.2:8080,1640995200
192.168.1.3:8080,1640995200
```

### 2. 释放代理IP

**接口**: `https://proxy.qg.net/release`

**参数**:
- `Key`: 你的API Key
- `Pwd`: 密码（可选）
- `ip`: 代理IP地址
- `port`: 代理端口

**示例**:
```bash
curl "https://proxy.qg.net/release?Key=your_key&ip=192.168.1.1&port=8080"
```

### 3. 查询账户余额

**接口**: `https://proxy.qg.net/query`

**参数**:
- `Key`: 你的API Key
- `Pwd`: 密码（可选）

**示例**:
```bash
curl "https://proxy.qg.net/query?Key=your_key"
```

## 代码使用示例

### 1. 基本使用

```python
import asyncio
from proxy.providers.qingguo_proxy import new_qingguo_proxy

async def test_qingguo_proxy():
    # 创建青果代理实例
    proxy = new_qingguo_proxy()
    
    # 获取账户余额
    balance = await proxy.get_balance()
    print(f"账户余额: {balance}")
    
    # 获取5个代理IP
    proxies = await proxy.get_proxies(5)
    print(f"获取到 {len(proxies)} 个代理")
    
    # 使用第一个代理
    if proxies:
        first_proxy = proxies[0]
        print(f"使用代理: {first_proxy.ip}:{first_proxy.port}")
        
        # 释放代理
        await proxy.release_proxy(first_proxy.ip, first_proxy.port)

# 运行测试
asyncio.run(test_qingguo_proxy())
```

### 2. 在爬虫中使用

```python
from proxy.proxy_ip_pool import create_ip_pool
import config

async def use_proxy_in_crawler():
    # 创建代理池
    proxy_pool = await create_ip_pool(
        ip_pool_count=5,
        enable_validate_ip=True
    )
    
    # 获取代理
    proxy = await proxy_pool.get_proxy()
    print(f"使用代理: {proxy.ip}:{proxy.port}")
    
    # 在爬虫中使用代理
    # ... 爬虫逻辑
```

### 3. 错误处理

```python
async def robust_proxy_usage():
    try:
        proxy = new_qingguo_proxy()
        proxies = await proxy.get_proxies(3)
        
        for proxy_info in proxies:
            try:
                # 使用代理进行请求
                # ... 请求逻辑
                print(f"代理 {proxy_info.ip} 使用成功")
                
            except Exception as e:
                print(f"代理 {proxy_info.ip} 使用失败: {e}")
                # 释放失败的代理
                await proxy.release_proxy(proxy_info.ip, proxy_info.port)
                
    except Exception as e:
        print(f"代理服务异常: {e}")
```

## 代理类型说明

青果代理支持多种代理类型：

### 1. 短效代理
- **特点**: 动态IP，有效期短
- **适用场景**: 高频请求，需要频繁更换IP
- **价格**: 相对便宜

### 2. 长效代理
- **特点**: 固定IP，有效期长
- **适用场景**: 需要稳定IP的场景
- **价格**: 相对较高

### 3. 独享代理
- **特点**: 独享IP资源，速度极快
- **适用场景**: 对速度要求极高的场景
- **价格**: 最高

### 4. 隧道代理
- **特点**: 云端自动切换IP
- **适用场景**: 简化调用，自动管理
- **价格**: 中等

## 最佳实践

### 1. 代理池管理

```python
class QingguoProxyManager:
    def __init__(self, pool_size=10):
        self.pool_size = pool_size
        self.proxy_pool = []
        self.proxy = new_qingguo_proxy()
    
    async def refresh_pool(self):
        """刷新代理池"""
        self.proxy_pool = await self.proxy.get_proxies(self.pool_size)
    
    async def get_proxy(self):
        """获取代理"""
        if not self.proxy_pool:
            await self.refresh_pool()
        
        if self.proxy_pool:
            return self.proxy_pool.pop(0)
        return None
    
    async def release_proxy(self, proxy_info):
        """释放代理"""
        await self.proxy.release_proxy(proxy_info.ip, proxy_info.port)
```

### 2. 代理健康检查

```python
async def check_proxy_health(proxy_info):
    """检查代理健康状态"""
    import httpx
    
    try:
        proxy_url = f"http://{proxy_info.user}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port}"
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=10.0
        ) as client:
            response = await client.get("http://httpbin.org/ip")
            return response.status_code == 200
    except:
        return False
```

### 3. 自动重试机制

```python
async def request_with_retry(url, max_retries=3):
    """带重试的请求"""
    proxy = new_qingguo_proxy()
    
    for attempt in range(max_retries):
        try:
            proxies = await proxy.get_proxies(1)
            if not proxies:
                continue
                
            proxy_info = proxies[0]
            # 使用代理进行请求
            # ... 请求逻辑
            
            # 请求成功，释放代理
            await proxy.release_proxy(proxy_info.ip, proxy_info.port)
            return response
            
        except Exception as e:
            print(f"第 {attempt + 1} 次请求失败: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    
    raise Exception("所有重试都失败了")
```

## 常见问题

### 1. 代理获取失败

**问题**: 调用API获取代理时返回错误

**解决方案**:
- 检查API Key是否正确
- 确认账户余额是否充足
- 检查网络连接是否正常

### 2. 代理连接超时

**问题**: 使用代理时连接超时

**解决方案**:
- 检查代理IP是否有效
- 尝试更换代理
- 增加连接超时时间

### 3. 代理被目标网站封禁

**问题**: 代理IP被目标网站识别并封禁

**解决方案**:
- 使用代理轮换策略
- 降低请求频率
- 使用更高质量的代理

## 联系支持

- **官方网站**: https://www.qg.net/
- **API文档**: https://www.qg.net/doc/2145.html
- **技术支持**: 通过官网联系客服

## 注意事项

1. **合规使用**: 请遵守青果代理的使用条款
2. **合理频率**: 控制请求频率，避免对目标网站造成压力
3. **及时释放**: 使用完代理后及时释放，避免资源浪费
4. **监控余额**: 定期检查账户余额，确保服务正常
5. **备份方案**: 建议准备多个代理提供商作为备份 