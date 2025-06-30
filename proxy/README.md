# 代理管理功能

## 概述

MediaCrawler 现在支持完整的代理管理功能，包括代理池管理、多种选择策略、自动检测和故障转移等特性。

## 功能特性

### 1. 代理池管理
- 支持 HTTP、HTTPS、SOCKS5 代理
- 代理信息完整记录（IP、端口、认证信息、地理位置等）
- 代理状态监控（可用性、速度、在线率等）
- 代理使用统计（成功率、失败次数等）

### 2. 多种选择策略
- **轮询策略 (round_robin)**: 按顺序轮询使用代理
- **随机策略 (random)**: 随机选择代理
- **权重策略 (weighted)**: 根据代理权重选择
- **故障转移策略 (failover)**: 优先使用高可用代理，失败时自动切换
- **地理位置策略 (geo_based)**: 根据目标网站地理位置选择代理
- **智能策略 (smart)**: 综合速度、可用性等因素智能选择

### 3. 自动检测
- 定期检测代理可用性
- 记录代理响应时间和成功率
- 自动标记失效代理
- 支持批量检测

### 4. 故障处理
- 自动记录代理失败次数
- 支持清理失效代理
- 故障转移机制
- 详细的错误日志

## 数据库表结构

### proxy_pool (代理池)
```sql
CREATE TABLE proxy_pool (
    id INT PRIMARY KEY AUTO_INCREMENT,
    proxy_type VARCHAR(16) NOT NULL,      -- 代理类型
    ip VARCHAR(64) NOT NULL,              -- 代理IP
    port INT NOT NULL,                    -- 代理端口
    username VARCHAR(64),                 -- 用户名
    password VARCHAR(128),                -- 密码
    country VARCHAR(32),                  -- 国家
    region VARCHAR(64),                   -- 地区
    city VARCHAR(64),                     -- 城市
    isp VARCHAR(64),                      -- 网络服务商
    speed INT,                            -- 速度(ms)
    anonymity VARCHAR(16),                -- 匿名度
    uptime DECIMAL(5,2),                  -- 在线率(%)
    last_check_time BIGINT,               -- 最后检测时间
    last_check_result TINYINT(1),         -- 最后检测结果
    fail_count INT DEFAULT 0,             -- 连续失败次数
    success_count INT DEFAULT 0,          -- 连续成功次数
    total_requests INT DEFAULT 0,         -- 总请求次数
    total_success INT DEFAULT 0,          -- 总成功次数
    status TINYINT(1) DEFAULT 1,          -- 状态
    priority INT DEFAULT 0,               -- 优先级
    tags VARCHAR(255),                    -- 标签
    description VARCHAR(500),             -- 描述
    add_ts BIGINT NOT NULL,               -- 添加时间
    last_modify_ts BIGINT NOT NULL        -- 最后修改时间
);
```

### proxy_strategy (代理策略)
```sql
CREATE TABLE proxy_strategy (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_name VARCHAR(64) NOT NULL,   -- 策略名称
    strategy_type VARCHAR(32) NOT NULL,   -- 策略类型
    description VARCHAR(500),             -- 策略描述
    config JSON,                          -- 策略配置
    is_default TINYINT(1) DEFAULT 0,      -- 是否默认
    status TINYINT(1) DEFAULT 1,          -- 状态
    add_ts BIGINT NOT NULL,               -- 添加时间
    last_modify_ts BIGINT NOT NULL        -- 最后修改时间
);
```

## API 接口

### 基础接口

#### 获取代理统计
```bash
GET /api/v1/proxy/stats
```

#### 获取代理列表
```bash
GET /api/v1/proxy/list?page=1&page_size=20&status=true&proxy_type=http&country=CN
```

#### 添加代理
```bash
POST /api/v1/proxy/add
Content-Type: application/json

{
  "proxy_type": "http",
  "ip": "127.0.0.1",
  "port": 8080,
  "username": "user",
  "password": "pass",
  "country": "CN",
  "speed": 100,
  "anonymity": "elite",
  "priority": 10
}
```

#### 更新代理
```bash
PUT /api/v1/proxy/update/{proxy_id}
Content-Type: application/json

{
  "speed": 150,
  "priority": 5
}
```

#### 删除代理
```bash
DELETE /api/v1/proxy/delete/{proxy_id}
```

### 检测接口

#### 检测单个代理
```bash
POST /api/v1/proxy/check/{proxy_id}
```

#### 批量检测代理
```bash
POST /api/v1/proxy/check/batch
Content-Type: application/json

{
  "proxy_ids": [1, 2, 3, 4, 5]
}
```

### 获取代理接口

#### 获取代理
```bash
GET /api/v1/proxy/get?strategy_type=round_robin&platform=xhs&check_availability=true
```

#### 快速获取代理（简化接口）
```bash
GET /api/v1/proxy/quick-get?strategy_type=smart&platform=dy
```

### 日志接口

#### 获取使用日志
```bash
GET /api/v1/proxy/usage/logs?proxy_id=1&platform=xhs&success=true&page=1&page_size=20
```

#### 获取检测日志
```bash
GET /api/v1/proxy/check/logs?proxy_id=1&check_type=health&success=true&page=1&page_size=20
```

## 命令行工具

### 安装数据库表
```bash
# 初始化代理相关表结构
python -c "
import asyncio
import db
from schema.proxy_tables import *
async def init():
    await db.init_db()
    async_db = db.media_crawler_db_var.get()
    with open('schema/proxy_tables.sql', 'r') as f:
        sql = f.read()
    await async_db.execute(sql)
    await db.close()
asyncio.run(init())
"
```

### 使用代理管理工具

#### 导入代理
```bash
# 从文本文件导入
python proxy/proxy_tools.py import --file proxy/sample_proxies.txt

# 从JSON文件导入
python proxy/proxy_tools.py import --file proxies.json
```

#### 检测代理
```bash
# 检测所有代理
python proxy/proxy_tools.py check
```

#### 查看统计
```bash
# 查看代理统计信息
python proxy/proxy_tools.py stats
```

#### 列出代理
```bash
# 列出前20个代理
python proxy/proxy_tools.py list --limit 20
```

#### 测试策略
```bash
# 测试所有代理策略
python proxy/proxy_tools.py test
```

#### 清理失效代理
```bash
# 清理失败次数超过5次的代理
python proxy/proxy_tools.py cleanup --max-fail 5
```

## 在爬虫中使用代理

### 通过API启动带代理的爬虫任务
```bash
curl -X POST http://localhost:8000/api/v1/crawler/start \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "keywords": "编程",
    "use_proxy": true,
    "proxy_strategy": "smart",
    "max_notes_count": 50
  }'
```

### 在代码中使用代理管理器
```python
from proxy import ProxyManager

async def use_proxy():
    proxy_manager = ProxyManager()
    
    # 获取代理
    proxy_info = await proxy_manager.get_proxy("smart", platform="xhs")
    
    if proxy_info:
        print(f"使用代理: {proxy_info.proxy_url}")
        
        # 在请求中使用代理
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.xiaohongshu.com",
                proxy=proxy_info.proxy_url
            ) as response:
                print(f"响应状态: {response.status}")
        
        # 标记代理成功
        await proxy_manager.strategies["smart"].mark_proxy_success(proxy_info.id)
    else:
        print("没有可用的代理")
```

## 代理文件格式

### 文本格式
```
# 注释行
http://127.0.0.1:8080
http://user:pass@127.0.0.1:8081
https://127.0.0.1:8443
socks5://127.0.0.1:1080
```

### JSON格式
```json
[
  {
    "proxy_type": "http",
    "ip": "127.0.0.1",
    "port": 8080,
    "username": "user",
    "password": "pass",
    "country": "CN",
    "speed": 100,
    "anonymity": "elite",
    "priority": 10
  }
]
```

## 最佳实践

### 1. 代理选择策略
- **开发测试**: 使用 `round_robin` 或 `random` 策略
- **生产环境**: 使用 `smart` 或 `failover` 策略
- **特定地区**: 使用 `geo_based` 策略

### 2. 代理质量维护
- 定期运行 `check` 命令检测代理可用性
- 使用 `cleanup` 命令清理失效代理
- 监控代理成功率，及时调整优先级

### 3. 性能优化
- 合理设置代理检测间隔
- 避免同时使用过多代理
- 根据目标网站特点选择合适的代理类型

### 4. 安全考虑
- 使用高匿名度代理
- 定期更换代理
- 避免在代理中存储敏感信息

## 故障排除

### 常见问题

1. **代理连接失败**
   - 检查代理服务器是否可用
   - 验证代理认证信息
   - 确认网络连接正常

2. **代理速度慢**
   - 检测代理服务器负载
   - 考虑更换地理位置更近的代理
   - 调整代理优先级

3. **代理被检测**
   - 使用高匿名度代理
   - 减少请求频率
   - 更换代理IP

### 日志查看
```bash
# 查看代理使用日志
curl "http://localhost:8000/api/v1/proxy/usage/logs?success=false&page_size=10"

# 查看代理检测日志
curl "http://localhost:8000/api/v1/proxy/check/logs?success=false&page_size=10"
```

## 注意事项

1. **法律合规**: 请确保代理使用符合当地法律法规
2. **服务条款**: 遵守代理服务商的使用条款
3. **资源限制**: 合理控制代理使用频率，避免对代理服务器造成压力
4. **数据安全**: 不要在代理中传输敏感信息
5. **成本控制**: 注意代理使用成本，合理规划使用量 