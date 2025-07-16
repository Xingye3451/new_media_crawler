# MediaCrawler API 服务

## 概述

MediaCrawler API 是将原有的命令行爬虫工具包装成 HTTP API 服务，方便集成到其他平台中。现在支持完整的代理管理功能和多平台同时抓取功能，提供更安全、更稳定、更高效的爬取能力。

## 🚀 新增功能：多平台同时抓取

**支持多平台相同关键字同时抓取！** 现在您可以：

- ✅ **并发抓取**：同时抓取多个平台，提高效率
- ✅ **统一结果**：所有平台数据转换为统一格式
- ✅ **灵活选择**：支持任意平台组合（1-7个平台）
- ✅ **任务管理**：完整的任务状态跟踪和进度监控
- ✅ **结果分析**：包含下载链接、关键信息字段、来源平台

### 快速开始多平台抓取

```bash
# 启动多平台抓取任务
curl -X POST "http://localhost:8000/api/v1/multi-platform/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["xhs", "dy", "ks"],
    "keywords": "美食探店",
    "max_count_per_platform": 30,
    "enable_images": true,
    "save_format": "json"
  }'

# 获取任务状态
curl "http://localhost:8000/api/v1/multi-platform/status/{task_id}"

# 获取任务结果
curl "http://localhost:8000/api/v1/multi-platform/results/{task_id}?format_type=json"
```

详细使用说明请查看：[API多平台抓取使用指南](docs/API多平台抓取使用指南.md)

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

# 测试多平台功能
python test_api_multi_platform.py
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

#### 获取多平台功能信息
```bash
GET /api/v1/multi-platform/info
```

### 多平台抓取接口

#### 启动多平台抓取任务
```bash
POST /api/v1/multi-platform/start
Content-Type: application/json

{
  "platforms": ["xhs", "dy", "ks"],
  "keywords": "美食探店",
  "max_count_per_platform": 50,
  "enable_comments": false,
  "enable_images": true,
  "save_format": "json",
  "session_ids": {
    "xhs": "session_id_1",
    "dy": "session_id_2"
  }
}
```

#### 获取多平台任务状态
```bash
GET /api/v1/multi-platform/status/{task_id}
```

#### 获取多平台任务结果
```bash
GET /api/v1/multi-platform/results/{task_id}?format_type=json
```

#### 获取多平台任务列表
```bash
GET /api/v1/multi-platform/tasks
```

#### 取消多平台任务
```bash
POST /api/v1/multi-platform/cancel/{task_id}
```

### 单平台爬虫任务接口

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

### 多平台抓取请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| **platforms** | **array** | **是** | **-** | **平台列表：xhs, dy, ks, bili, wb, tieba, zhihu** |
| **keywords** | **string** | **是** | **-** | **搜索关键词** |
| **max_count_per_platform** | **int** | **否** | **50** | **每个平台最大抓取数量** |
| **enable_comments** | **boolean** | **否** | **false** | **是否抓取评论** |
| **enable_images** | **boolean** | **否** | **false** | **是否抓取图片** |
| **save_format** | **string** | **否** | **json** | **保存格式：json, csv** |
| **session_ids** | **object** | **否** | **null** | **各平台的登录会话ID** |

### 单平台爬虫请求参数

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
| enable_images | boolean | 否 | false | 是否抓取图片 |
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

### Python 多平台抓取示例

```python
import requests
import time

def start_multi_platform_crawl():
    """启动多平台抓取任务"""
    url = "http://localhost:8000/api/v1/multi-platform/start"
    payload = {
        "platforms": ["xhs", "dy", "ks"],
        "keywords": "美食探店",
        "max_count_per_platform": 30,
        "enable_comments": False,
        "enable_images": True,
        "save_format": "json"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()
        task_id = result["task_id"]
        print(f"任务创建成功: {task_id}")
        return task_id
    else:
        print(f"创建任务失败: {response.text}")
        return None

def monitor_multi_platform_task(task_id):
    """监控多平台任务状态"""
    while True:
        response = requests.get(f"http://localhost:8000/api/v1/multi-platform/status/{task_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"任务状态: {status['status']}")
            print(f"进度: {status['progress']['completed']}/{status['progress']['total']}")
            
            if status['status'] in ['completed', 'failed']:
                return status
        
        time.sleep(5)

def get_multi_platform_results(task_id):
    """获取多平台任务结果"""
    response = requests.get(f"http://localhost:8000/api/v1/multi-platform/results/{task_id}?format_type=json")
    if response.status_code == 200:
        results = response.json()
        print(f"总共获取 {results['total_count']} 条数据")
        
        # 按平台统计
        platform_stats = {}
        for item in results['results']:
            platform = item['platform_name']
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        print("按平台统计:")
        for platform, count in platform_stats.items():
            print(f"  {platform}: {count} 条")
        
        return results
    else:
        print(f"获取结果失败: {response.text}")
        return None

# 使用示例
task_id = start_multi_platform_crawl()
if task_id:
    status = monitor_multi_platform_task(task_id)
    if status['status'] == 'completed':
        results = get_multi_platform_results(task_id)
```

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

### JavaScript 多平台抓取示例

```javascript
// 启动多平台抓取任务
async function startMultiPlatformCrawl() {
    const data = {
        platforms: ["xhs", "dy", "ks"],
        keywords: "美食探店",
        max_count_per_platform: 30,
        enable_comments: false,
        enable_images: true,
        save_format: "json"
    };
    
    try {
        const response = await fetch('http://localhost:8000/api/v1/multi-platform/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log(`任务创建成功: ${result.task_id}`);
            return result.task_id;
        } else {
            console.error(`创建任务失败: ${result.detail}`);
            return null;
        }
    } catch (error) {
        console.error('请求失败:', error);
        return null;
    }
}

// 监控任务状态
async function monitorTaskStatus(taskId) {
    while (true) {
        try {
            const response = await fetch(`http://localhost:8000/api/v1/multi-platform/status/${taskId}`);
            const status = await response.json();
            
            if (response.ok) {
                console.log(`任务状态: ${status.status}`);
                console.log(`进度: ${status.progress.completed}/${status.progress.total}`);
                
                if (status.status === 'completed' || status.status === 'failed') {
                    return status;
                }
            } else {
                console.error(`获取状态失败: ${status.detail}`);
                return null;
            }
        } catch (error) {
            console.error('请求失败:', error);
            return null;
        }
        
        // 等待5秒
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

// 获取任务结果
async function getTaskResults(taskId) {
    try {
        const response = await fetch(`http://localhost:8000/api/v1/multi-platform/results/${taskId}?format_type=json`);
        const results = await response.json();
        
        if (response.ok) {
            console.log(`总共获取 ${results.total_count} 条数据`);
            
            // 按平台统计
            const platformStats = {};
            results.results.forEach(item => {
                const platform = item.platform_name;
                platformStats[platform] = (platformStats[platform] || 0) + 1;
            });
            
            console.log('按平台统计:');
            Object.entries(platformStats).forEach(([platform, count]) => {
                console.log(`  ${platform}: ${count} 条`);
            });
            
            return results;
        } else {
            console.error(`获取结果失败: ${results.detail}`);
            return null;
        }
    } catch (error) {
        console.error('请求失败:', error);
        return null;
    }
}

// 主函数
async function main() {
    const taskId = await startMultiPlatformCrawl();
    if (!taskId) return;
    
    const status = await monitorTaskStatus(taskId);
    if (!status || status.status === 'failed') {
        console.log('任务执行失败');
        return;
    }
    
    const results = await getTaskResults(taskId);
    if (results) {
        console.log('任务完成！');
    }
}

// 运行
main();
```

### cURL 示例

```bash
# 多平台抓取
curl -X POST "http://localhost:8000/api/v1/multi-platform/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["xhs", "dy", "ks"],
    "keywords": "美食探店",
    "max_count_per_platform": 30,
    "enable_images": true,
    "save_format": "json"
  }'

# 获取任务状态
curl "http://localhost:8000/api/v1/multi-platform/status/{task_id}"

# 获取任务结果
curl "http://localhost:8000/api/v1/multi-platform/results/{task_id}?format_type=json"

# 单平台抓取（带代理）
curl -X POST "http://localhost:8000/api/v1/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "keywords": "编程",
    "max_notes_count": 10,
    "use_proxy": true,
    "proxy_strategy": "smart"
  }'
```

## 错误处理

### 常见错误码

| 状态码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式和必填字段 |
| 404 | 任务不存在 | 确认任务ID是否正确 |
| 500 | 服务器内部错误 | 检查服务器日志，联系管理员 |

### 错误响应示例

```json
{
  "detail": "不支持的平台: ['invalid_platform']"
}
```

## 最佳实践

### 1. 多平台抓取
- 合理选择平台组合，避免过多平台同时抓取
- 设置合适的抓取数量，避免对平台造成压力
- 使用任务状态监控，及时处理异常

### 2. 代理使用
- 根据目标平台选择合适的代理策略
- 定期检测代理可用性
- 合理配置代理池大小

### 3. 错误处理
- 实现重试机制
- 记录错误日志
- 提供用户友好的错误信息

### 4. 性能优化
- 使用异步请求
- 实现请求缓存
- 控制并发数量

## 注意事项

1. **合规使用**：请遵守各平台的使用条款
2. **频率控制**：避免过于频繁的请求
3. **数据用途**：仅供学习和研究使用
4. **存储管理**：注意管理抓取数据的存储空间
5. **网络环境**：确保网络连接稳定

## 技术支持

如遇到问题，请：
1. 查看API响应中的错误信息
2. 检查服务器日志
3. 确认请求参数格式
4. 参考示例代码
5. 运行测试脚本验证功能