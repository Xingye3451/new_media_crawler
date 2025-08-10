# 青果长效代理使用指南

## 概述

MediaCrawler项目集成了青果代理的长效代理（动态IP）功能，用于避免反爬机制。通过Cookie-IP绑定的策略，确保登录和爬取使用相同的IP地址，降低被检测的风险。

## 🎯 推荐配置

### 代理类型选择
- **推荐**: 长效代理（动态IP）
- **带宽**: 10Mbps
- **隧道转发**: 启用
- **通道数**: 1-2个
- **购买时长**: 1个月
- **地区**: 国内

### 优势分析
1. **IP存活时间长**: 每天自然更换，符合正常用户行为
2. **地理位置稳定**: 减少地理异常检测
3. **成本效益高**: 相比独享代理更经济实惠
4. **稳定性好**: IP质量较高，成功率更高

## 🔧 配置步骤

### 1. 环境变量配置

```bash
# 青果代理配置
export QG_PROXY_KEY="你的青果代理Key"
export QG_PROXY_PWD="你的青果代理密码"  # 可选

# 启用代理功能
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
  qingguo_key: "your_qingguo_key_here"
  qingguo_pwd: "your_qingguo_pwd_here"  # 可选
```

### 3. 数据库迁移

执行数据库迁移，添加proxy_id字段：

```bash
# 激活conda环境
conda activate mediacrawler

# 执行迁移
python migrate/migrate.py
```

## 🚀 使用流程

### 1. 远程登录时使用代理

```python
from api.login_proxy_helper import get_proxy_for_login, save_login_token_with_proxy

# 获取代理
proxy_info = await get_proxy_for_login(platform="dy", account_id=123)

# 使用代理进行登录
# ... 登录逻辑 ...

# 保存登录令牌和代理信息
await save_login_token_with_proxy(
    account_id=123,
    platform="dy",
    token_data=json.dumps(cookies),
    user_agent=user_agent,
    proxy_info=proxy_info
)
```

### 2. 爬取时使用相同代理

```python
from api.login_proxy_helper import get_proxy_from_login_token

# 获取登录时使用的代理
proxy_info = await get_proxy_from_login_token(account_id=123, platform="dy")

# 在爬虫中使用代理
crawler.proxy_info = proxy_info
```

## 📊 数据库结构

### login_tokens表
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

### proxy_pool表
```sql
CREATE TABLE `proxy_pool` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ip` varchar(15) NOT NULL COMMENT '代理IP',
  `port` int(11) NOT NULL COMMENT '代理端口',
  `username` varchar(100) DEFAULT NULL COMMENT '用户名',
  `password` varchar(100) DEFAULT NULL COMMENT '密码',
  `proxy_type` varchar(10) DEFAULT 'http' COMMENT '代理类型',
  `expire_ts` bigint(20) NOT NULL COMMENT '过期时间戳',
  `platform` varchar(20) DEFAULT NULL COMMENT '平台名称',
  `account_id` int(11) DEFAULT NULL COMMENT '账号ID',
  `status` varchar(20) DEFAULT 'active' COMMENT '状态',
  `usage_count` int(11) DEFAULT 0 COMMENT '使用次数',
  `success_count` int(11) DEFAULT 0 COMMENT '成功次数',
  `fail_count` int(11) DEFAULT 0 COMMENT '失败次数',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_status` (`status`),
  KEY `idx_expire_ts` (`expire_ts`)
);
```

## 🔄 工作流程

### 1. 登录流程
```
用户登录 → 获取青果代理 → 使用代理登录 → 保存Cookie和代理信息
```

### 2. 爬取流程
```
启动爬取 → 获取登录代理 → 使用相同代理爬取 → 更新代理使用统计
```

### 3. 代理管理
```
代理提取 → 数据库存储 → 状态跟踪 → 过期清理
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
print(f"代理Key: {os.getenv('QG_PROXY_KEY')}")
print(f"代理启用: {ENABLE_IP_PROXY}")

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

## 🔐 安全考虑

### 1. 代理安全
- 定期更换代理密码
- 监控代理使用异常
- 限制代理访问权限

### 2. 数据安全
- 加密敏感配置信息
- 定期备份数据库
- 监控数据访问日志

### 3. 合规使用
- 遵守目标平台使用条款
- 合理控制爬取频率
- 不得用于商业用途

## 📞 技术支持

如遇到问题，请检查：
1. 青果代理账户余额
2. 网络连接状态
3. 数据库连接配置
4. 代理API调用日志

更多信息请参考：
- [青果代理官方文档](https://www.qg.net/doc/2145.html)
- [MediaCrawler项目文档](./README.md)
