# 青果代理系统使用指南

## 概述

MediaCrawler 项目已集成青果代理系统，支持长效动态IP代理，用于反爬虫策略。系统实现了"Cookie-IP绑定"机制，确保登录和爬取使用相同的IP地址，有效避免因IP切换触发的反爬检测。

## 配置说明

### 1. 环境变量配置

```bash
# 青果代理认证信息
export QG_PROXY_KEY="EEFECFB3"
export QG_PROXY_PWD="E169CFB91ACD"
export ENABLE_IP_PROXY="true"
```

### 2. 配置文件设置

在 `config/config_local.yaml` 中：

```yaml
proxy:
  provider_name: "qingguo"
  enabled: true
  pool_count: 5
  validate_ip: true
  
  # 青果代理配置
  qingguo_key: "EEFECFB3"
  qingguo_pwd: "E169CFB91ACD"
```

## 核心功能

### 1. 代理提取和管理

- **长效动态IP**: 支持数小时到365天的IP有效期
- **自动管理**: 自动清理过期代理，统计使用情况
- **平台绑定**: 支持按平台和账号绑定代理

### 2. Cookie-IP绑定机制

```python
# 登录时获取代理
proxy_info = await get_proxy_for_login(platform, account_id)

# 保存登录token和代理绑定
await save_login_token_with_proxy(
    account_id=account_id,
    platform=platform,
    token_data=token_data,
    proxy_info=proxy_info
)

# 爬取时使用相同代理
proxy_info = await get_proxy_from_login_token(account_id, platform)
```

### 3. 数据库表结构

#### login_tokens 表
- `proxy_id`: 关联的代理ID
- `proxy_info`: 代理详细信息(JSON格式)

#### proxy_pool 表
- `proxy_id`: 代理唯一标识
- `ip`, `port`: 代理地址和端口
- `username`, `password`: 认证信息
- `expire_ts`: 过期时间戳
- `platform`, `account_id`: 关联平台和账号
- `status`: 代理状态(active/expired/failed)
- `usage_count`, `success_count`, `fail_count`: 使用统计

### 4. 代理使用日志

系统会在每次使用代理时自动打印详细的代理信息：

```
[PROXY_USAGE] 🚀 使用Playwright代理: tunpool-tyk37.qg.net:17003
[PROXY_USAGE] 📋 代理类型: http
[PROXY_USAGE] 🔑 认证信息: EEFECFB3:E169CFB91ACD
[PROXY_USAGE] ⏰ 过期时间: 1754887991
[PROXY_USAGE] 📊 使用统计: 成功1次, 失败0次
[PROXY_USAGE] 💡 curl使用示例: curl -x http://EEFECFB3:E169CFB91ACD@tunpool-tyk37.qg.net:17003 https://httpbin.org/ip
[PROXY_USAGE] 📋 Playwright配置: {'server': 'http://tunpool-tyk37.qg.net:17003', 'username': 'EEFECFB3', 'password': 'E169CFB91ACD'}
```

#### 支持的代理格式

1. **HTTP代理** (推荐)
   ```bash
   curl -x http://{username}:{password}@{ip}:{port} {targetUrl}
   ```

2. **Playwright配置**
   ```python
   {
       "server": "http://{ip}:{port}",
       "username": "{username}",
       "password": "{password}"
   }
   ```

3. **httpx配置**
   ```python
   {
       "http://": "http://{username}:{password}@{ip}:{port}",
       "https://": "http://{username}:{password}@{ip}:{port}"
   }
   ```

## API接口

### 代理管理API

```bash
# 查询代理统计
GET /v1/proxies/stats/overview

# 查询代理列表
GET /v1/proxies/

# 测试代理
POST /v1/proxies/{proxy_id}/test

# 清理过期代理
POST /v1/proxies/cleanup/expired
```

### 青果代理专用API

```bash
# 查询账户余额
GET /v1/qingguo/balance

# 查询资源地区
GET /v1/qingguo/resources

# 查询白名单
GET /v1/qingguo/whitelist

# 添加白名单
POST /v1/qingguo/whitelist/add

# 删除白名单
DELETE /v1/qingguo/whitelist/remove

# 提取代理（支持区域和运营商）
POST /v1/qingguo/extract?platform=dy&region=北京&isp=电信

# 批量提取代理
POST /v1/qingguo/batch-extract

# 查询在用代理
GET /v1/qingguo/in-use

# 释放代理
DELETE /v1/qingguo/release/{proxy_id}

# 健康检查
POST /v1/qingguo/health-check
```

### 区域和运营商支持

系统支持按区域和运营商提取代理：

#### 支持的区域
- **一线城市**: 北京(110000)、上海(310000)、广州(440100)、深圳(440300)
- **新一线城市**: 杭州(330100)、南京(320100)、成都(510100)、武汉(420100)等
- **省份**: 支持全国所有省份

#### 支持的运营商
- **电信**: 0
- **联通**: 1  
- **移动**: 2
- **铁通**: 3
- **教育网**: 4
- **广电**: 5
- **长城**: 6
- **其他**: 7

## 使用流程

### 1. 账号登录流程

```python
# 1. 获取登录代理
proxy_info = await get_proxy_for_login(platform, account_id)

# 2. 使用代理进行登录
crawler = create_crawler(platform)
crawler.proxy_info = proxy_info
login_result = await crawler.login()

# 3. 保存登录token和代理绑定
if login_result.success:
    await save_login_token_with_proxy(
        account_id=account_id,
        platform=platform,
        token_data=login_result.cookies,
        proxy_info=proxy_info
    )
```

### 2. 爬取任务流程

```python
# 1. 获取绑定的代理
proxy_info = await get_proxy_from_login_token(account_id, platform)

# 2. 使用相同代理进行爬取
crawler = create_crawler(platform)
if proxy_info:
    crawler.proxy_info = proxy_info

# 3. 执行爬取任务
results = await crawler.crawl(keywords, max_count)
```

## 管理界面

### 1. 代理管理页面

访问 `http://localhost:8000/static/proxy_management.html`

功能包括：
- 代理统计概览
- 代理列表管理
- 代理测试功能
- 过期代理清理

### 2. 青果代理专用功能

- 账户余额查询
- 资源地区查看
- IP白名单管理
- 代理提取和释放
- 健康检查

## 测试验证

运行测试脚本验证系统功能：

```bash
python test_proxy_system.py
```

测试内容包括：
- 基础API功能测试
- 代理提取和保存测试
- 登录代理绑定测试
- 代理管理功能测试

## 故障排除

### 1. 常见错误

#### 资源不足错误
```
{"Code":-103,"Msg":"资源不足"}
```
**解决方案**: 
- 检查青果代理账户余额
- 确认通道数是否足够
- 联系青果代理客服充值

#### API连接错误
```
HTTP 404 Not Found
```
**解决方案**:
- 检查API接口地址是否正确
- 确认认证信息是否有效
- 查看网络连接状态

### 2. 日志查看

```bash
# 查看代理相关日志
tail -f logs/mediacrawler_*.log | grep -i proxy
```

### 3. 数据库检查

```sql
-- 检查代理池状态
SELECT * FROM proxy_pool WHERE status = 'active';

-- 检查登录token绑定
SELECT * FROM login_tokens WHERE proxy_id IS NOT NULL;
```

## 最佳实践

### 1. 代理使用策略

- **平台隔离**: 不同平台使用不同代理，避免交叉污染
- **账号绑定**: 每个账号绑定固定代理，保持IP一致性
- **定期轮换**: 根据代理质量和使用情况定期轮换
- **监控告警**: 设置代理成功率监控和告警

### 2. 性能优化

- **连接池**: 合理设置代理连接池大小
- **超时控制**: 设置合适的请求超时时间
- **重试机制**: 实现代理失败自动重试
- **缓存策略**: 缓存代理信息，减少API调用

### 3. 安全考虑

- **白名单管理**: 及时更新IP白名单
- **认证安全**: 妥善保管代理认证信息
- **访问控制**: 限制代理管理接口访问权限
- **日志审计**: 记录代理使用日志，便于审计

## 技术支持

如遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 运行测试脚本验证系统状态
3. 检查青果代理账户和资源状态
4. 联系技术支持团队

---

**注意**: 本系统仅供学习研究使用，请遵守相关平台的使用条款和法律法规。
