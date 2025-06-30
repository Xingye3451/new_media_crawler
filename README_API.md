# MediaCrawler API 服务

## 概述

MediaCrawler API 是将原有的命令行爬虫工具包装成 HTTP API 服务，方便集成到其他平台中。现在支持完整的代理管理功能，提供更安全、更稳定的爬取能力。

## 快速开始

### 1. 构建并启动容器

```bash
# 使用 docker-compose（推荐）
docker-compose up -d --build

# 或者使用 Docker 命令
docker build -f Dockerfile.api -t mediacrawler-api .
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data mediacrawler-api
```

### 2. 快速测试

```bash
# 运行快速测试脚本
chmod +x quick_test.sh
./quick_test.sh

# 或者手动测试
curl http://localhost:8000/api/v1/health
```

### 3. 初始化代理数据库（可选）

```bash
# 初始化代理相关表结构
python -c "
import asyncio
import db
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

## API 接口

### 基础接口

#### 健康检查
```bash
GET /api/v1/health
```

#### 获取支持的平台
```bash
GET /api/v1/platforms
```

### 爬虫任务接口

#### 启动爬虫任务
```bash
POST /api/v1/crawler/start
Content-Type: application/json

{
  "platform": "xhs",
  "login_type": "qrcode",
  "crawler_type": "search",
  "keywords": "编程",
  "start_page": 1,
  "get_comments": true,
  "get_sub_comments": false,
  "save_data_option": "json",
  "max_notes_count": 100,
  "enable_images": false,
  "use_proxy": true,
  "proxy_strategy": "smart"
}
```

#### 获取任务状态
```bash
GET /api/v1/crawler/status/{task_id}
```

#### 列出所有任务
```bash
GET /api/v1/crawler/tasks
```

#### 删除任务
```bash
DELETE /api/v1/crawler/tasks/{task_id}
```

### 代理管理接口

#### 获取代理统计
```bash
GET /api/v1/proxy/stats
```

#### 快速获取代理
```bash
GET /api/v1/proxy/quick-get?strategy_type=smart&platform=xhs
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

#### 检测代理
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

## 参数说明

### 爬虫请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| platform | string | 是 | - | 平台：xhs, dy, ks, bili, wb, tieba, zhihu |
| login_type | string | 否 | qrcode | 登录类型：qrcode, phone, cookie |
| crawler_type | string | 否 | search | 爬取类型：search, detail, creator |
| keywords | string | 否 | "" | 搜索关键词 |
| start_page | int | 否 | 1 | 开始页数 |
| get_comments | boolean | 否 | true | 是否爬取评论 |
| get_sub_comments | boolean | 否 | false | 是否爬取二级评论 |
| save_data_option | string | 否 | json | 数据保存方式：csv, db, json |
| cookies | string | 否 | "" | Cookie字符串 |
| specified_ids | array | 否 | null | 指定ID列表 |
| max_notes_count | int | 否 | 200 | 最大爬取数量 |
| enable_images | boolean | 否 | false | 是否爬取图片 |
| **use_proxy** | **boolean** | **否** | **false** | **是否使用代理** |
| **proxy_strategy** | **string** | **否** | **round_robin** | **代理策略：round_robin, random, weighted, failover, geo_based, smart** |

### 代理策略说明

- **round_robin**: 轮询策略 - 按顺序轮询使用代理
- **random**: 随机策略 - 随机选择代理
- **weighted**: 权重策略 - 根据代理权重选择
- **failover**: 故障转移策略 - 优先使用高可用代理，失败时自动切换
- **geo_based**: 地理位置策略 - 根据目标网站地理位置选择代理
- **smart**: 智能策略 - 综合速度、可用性等因素智能选择

## 使用示例

### Python 客户端示例（带代理）

```python
import requests
import time

# 启动带代理的爬虫任务
def start_crawler_with_proxy(platform="xhs", keywords="编程"):
    url = "http://localhost:8000/api/v1/crawler/start"
    payload = {
        "platform": platform,
        "keywords": keywords,
        "max_notes_count": 10,
        "get_comments": False,
        "use_proxy": True,
        "proxy_strategy": "smart"
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 获取代理统计
def get_proxy_stats():
    url = "http://localhost:8000/api/v1/proxy/stats"
    response = requests.get(url)
    return response.json()

# 快速获取代理
def get_proxy(strategy="smart", platform="xhs"):
    url = f"http://localhost:8000/api/v1/proxy/quick-get?strategy_type={strategy}&platform={platform}"
    response = requests.get(url)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 查看代理统计
    stats = get_proxy_stats()
    print(f"代理统计: {stats}")
    
    # 获取代理
    proxy = get_proxy("smart", "xhs")
    print(f"获取代理: {proxy}")
    
    # 启动爬虫任务
    result = start_crawler_with_proxy("xhs", "Python编程")
    task_id = result["data"]["task_id"]
    print(f"任务ID: {task_id}")
```

### JavaScript 客户端示例（带代理）

```javascript
// 启动带代理的爬虫任务
async function startCrawlerWithProxy(platform = 'xhs', keywords = '编程') {
    const response = await fetch('http://localhost:8000/api/v1/crawler/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            platform,
            keywords,
            max_notes_count: 10,
            get_comments: false,
            use_proxy: true,
            proxy_strategy: 'smart'
        })
    });
    
    return await response.json();
}

// 获取代理统计
async function getProxyStats() {
    const response = await fetch('http://localhost:8000/api/v1/proxy/stats');
    return await response.json();
}

// 快速获取代理
async function getProxy(strategy = 'smart', platform = 'xhs') {
    const response = await fetch(`http://localhost:8000/api/v1/proxy/quick-get?strategy_type=${strategy}&platform=${platform}`);
    return await response.json();
}

// 使用示例
async function main() {
    try {
        // 查看代理统计
        const stats = await getProxyStats();
        console.log('代理统计:', stats);
        
        // 获取代理
        const proxy = await getProxy('smart', 'xhs');
        console.log('获取代理:', proxy);
        
        // 启动爬虫任务
        const result = await startCrawlerWithProxy('xhs', 'Python编程');
        const taskId = result.data.task_id;
        console.log('任务ID:', taskId);
        
    } catch (error) {
        console.error('错误:', error);
    }
}

main();
```

## 代理管理工具

### 支持的代理提供商

#### 1. 青果代理 (Qingguo Proxy)
- **官方文档**: https://www.qg.net/doc/2145.html
- **配置方式**:
  ```bash
  # 环境变量配置
  export qg_key="你的青果代理Key"
  export qg_pwd="你的青果代理密码"  # 可选
  
  # 项目配置
  # 修改 config/base_config.py
  IP_PROXY_PROVIDER_NAME = "qingguo"
  ENABLE_IP_PROXY = True
  ```

#### 2. 快代理 (KuaiDaili Proxy)
- **配置方式**:
  ```bash
  export kdl_secret_id="你的快代理secret_id"
  export kdl_signature="你的快代理签名"
  export kdl_user_name="你的快代理用户名"
  export kdl_user_pwd="你的快代理密码"
  ```

#### 3. 极速HTTP代理 (JiSu HTTP Proxy)
- **配置方式**:
  ```bash
  export jisu_http_key="你的极速HTTP代理Key"
  ```

### 命令行工具

```bash
# 导入代理
python proxy/proxy_tools.py import --file proxy/sample_proxies.txt

# 检测代理
python proxy/proxy_tools.py check

# 查看统计
python proxy/proxy_tools.py stats

# 列出代理
python proxy/proxy_tools.py list --limit 20

# 测试策略
python proxy/proxy_tools.py test

# 清理失效代理
python proxy/proxy_tools.py cleanup --max-fail 5
```

### 代理文件格式

#### 文本格式
```
# 注释行
http://127.0.0.1:8080
http://user:pass@127.0.0.1:8081
https://127.0.0.1:8443
socks5://127.0.0.1:1080
```

#### JSON格式
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

## 集成到AI平台

### 1. 微服务架构集成（带代理）

```python
# 在你的AI平台中添加MediaCrawler服务调用
class MediaCrawlerService:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
    
    async def crawl_content_with_proxy(self, platform, keywords, max_count=50, use_proxy=True):
        """爬取内容并返回结构化数据（支持代理）"""
        # 启动爬虫任务
        task = await self._start_task_with_proxy(platform, keywords, max_count, use_proxy)
        
        # 等待任务完成
        result = await self._wait_for_completion(task['task_id'])
        
        return result
    
    async def _start_task_with_proxy(self, platform, keywords, max_count, use_proxy):
        # 实现带代理的任务启动逻辑
        pass
    
    async def _wait_for_completion(self, task_id):
        # 实现任务等待逻辑
        pass
    
    async def get_proxy_info(self, strategy="smart", platform=None):
        """获取代理信息"""
        # 实现代理获取逻辑
        pass
```

### 2. 消息队列集成（带代理）

```python
# 使用Redis或RabbitMQ进行任务队列管理
import redis
import json

class CrawlerTaskQueue:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def enqueue_task_with_proxy(self, task_data, use_proxy=True, proxy_strategy="smart"):
        """将爬虫任务加入队列（支持代理）"""
        task_id = str(uuid.uuid4())
        task_data['task_id'] = task_id
        task_data['use_proxy'] = use_proxy
        task_data['proxy_strategy'] = proxy_strategy
        self.redis_client.lpush('crawler_tasks', json.dumps(task_data))
        return task_id
    
    def dequeue_task(self):
        """从队列中取出任务"""
        task_data = self.redis_client.rpop('crawler_tasks')
        return json.loads(task_data) if task_data else None
```

## 注意事项

1. **登录验证**: 爬虫需要扫码登录，首次使用需要在容器日志中查看二维码
2. **请求频率**: 请合理控制请求频率，避免对目标平台造成压力
3. **数据存储**: 数据默认保存在 `./data` 目录下
4. **容器日志**: 使用 `docker-compose logs -f mediacrawler-api` 查看详细日志
5. **资源限制**: 爬虫任务会消耗较多资源，建议设置合理的并发限制
6. **代理使用**: 使用代理时请确保代理服务器可用，建议定期检测代理质量
7. **法律合规**: 请确保代理使用符合当地法律法规

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 查看容器日志
   docker-compose logs mediacrawler-api
   
   # 检查端口占用
   netstat -tlnp | grep 8000
   ```

2. **API服务无响应**
   ```bash
   # 检查容器状态
   docker-compose ps
   
   # 重启服务
   docker-compose restart mediacrawler-api
   ```

3. **爬虫任务失败**
   ```bash
   # 查看详细错误信息
   docker-compose logs -f mediacrawler-api
   
   # 检查网络连接
   docker exec mediacrawler-api ping www.xiaohongshu.com
   ```

4. **代理相关问题**
   ```bash
   # 检查代理统计
   curl http://localhost:8000/api/v1/proxy/stats
   
   # 检测代理可用性
   python proxy/proxy_tools.py check
   
   # 查看代理日志
   curl "http://localhost:8000/api/v1/proxy/usage/logs?success=false&page_size=10"
   ```

5. **青果代理相关问题**
   ```bash
   # 测试青果代理连接
   python test/test_qingguo_proxy.py
   
   # 检查青果代理配置
   echo $qg_key
   echo $qg_pwd
   
   # 查看青果代理余额
   curl "https://proxy.qg.net/query?Key=your_key"
   ```

## 开发说明

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动API服务
python api_server.py

# 运行测试
python test_api.py

# 测试青果代理
python test/test_qingguo_proxy.py
```

### 自定义配置

可以通过环境变量或配置文件自定义API服务的行为：

```bash
# 环境变量
export CRAWLER_MAX_CONCURRENCY=5
export CRAWLER_TIMEOUT=300
export LOG_LEVEL=INFO
export PROXY_ENABLED=true
export PROXY_STRATEGY=smart

# 青果代理配置
export qg_key="your_qingguo_key"
export qg_pwd="your_qingguo_password"

# 启动服务
docker-compose up -d
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和平台使用条款。