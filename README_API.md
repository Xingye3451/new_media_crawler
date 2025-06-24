# MediaCrawler API 服务

## 概述

MediaCrawler API 是将原有的命令行爬虫工具包装成 HTTP API 服务，方便集成到其他平台中。

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
  "enable_images": false
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

## 参数说明

### 请求参数

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

### 响应格式

#### 启动任务响应
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "爬虫任务已启动",
  "data": {
    "task_id": "uuid-string"
  }
}
```

#### 任务状态响应
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "progress": 100.0,
  "result": {
    "data": [...]
  },
  "error": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:05:00"
}
```

## 使用示例

### Python 客户端示例

```python
import requests
import time

# 启动爬虫任务
def start_crawler_task(platform="xhs", keywords="编程"):
    url = "http://localhost:8000/api/v1/crawler/start"
    payload = {
        "platform": platform,
        "keywords": keywords,
        "max_notes_count": 10,
        "get_comments": False
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# 获取任务状态
def get_task_status(task_id):
    url = f"http://localhost:8000/api/v1/crawler/status/{task_id}"
    response = requests.get(url)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 启动任务
    result = start_crawler_task("xhs", "Python编程")
    task_id = result["data"]["task_id"]
    print(f"任务ID: {task_id}")
    
    # 轮询任务状态
    while True:
        status = get_task_status(task_id)
        print(f"任务状态: {status['status']}")
        
        if status['status'] in ['completed', 'failed']:
            if status['status'] == 'completed':
                print(f"爬取完成，共获取 {len(status['result'])} 条数据")
            else:
                print(f"任务失败: {status['error']}")
            break
        
        time.sleep(5)
```

### JavaScript 客户端示例

```javascript
// 启动爬虫任务
async function startCrawlerTask(platform = 'xhs', keywords = '编程') {
    const response = await fetch('http://localhost:8000/api/v1/crawler/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            platform,
            keywords,
            max_notes_count: 10,
            get_comments: false
        })
    });
    
    return await response.json();
}

// 获取任务状态
async function getTaskStatus(taskId) {
    const response = await fetch(`http://localhost:8000/api/v1/crawler/status/${taskId}`);
    return await response.json();
}

// 使用示例
async function main() {
    try {
        // 启动任务
        const result = await startCrawlerTask('xhs', 'Python编程');
        const taskId = result.data.task_id;
        console.log(`任务ID: ${taskId}`);
        
        // 轮询任务状态
        const checkStatus = async () => {
            const status = await getTaskStatus(taskId);
            console.log(`任务状态: ${status.status}`);
            
            if (status.status === 'completed') {
                console.log(`爬取完成，共获取 ${status.result.length} 条数据`);
            } else if (status.status === 'failed') {
                console.log(`任务失败: ${status.error}`);
            } else {
                setTimeout(checkStatus, 5000);
            }
        };
        
        checkStatus();
    } catch (error) {
        console.error('错误:', error);
    }
}

main();
```

## 集成到AI平台

### 1. 微服务架构集成

```python
# 在你的AI平台中添加MediaCrawler服务调用
class MediaCrawlerService:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
    
    async def crawl_content(self, platform, keywords, max_count=50):
        """爬取内容并返回结构化数据"""
        # 启动爬虫任务
        task = await self._start_task(platform, keywords, max_count)
        
        # 等待任务完成
        result = await self._wait_for_completion(task['task_id'])
        
        return result
    
    async def _start_task(self, platform, keywords, max_count):
        # 实现任务启动逻辑
        pass
    
    async def _wait_for_completion(self, task_id):
        # 实现任务等待逻辑
        pass
```

### 2. 消息队列集成

```python
# 使用Redis或RabbitMQ进行任务队列管理
import redis
import json

class CrawlerTaskQueue:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def enqueue_task(self, task_data):
        """将爬虫任务加入队列"""
        task_id = str(uuid.uuid4())
        task_data['task_id'] = task_id
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

## 开发说明

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动API服务
python api_server.py

# 运行测试
python test_api.py
```

### 自定义配置

可以通过环境变量或配置文件自定义API服务的行为：

```bash
# 环境变量
export CRAWLER_MAX_CONCURRENCY=5
export CRAWLER_TIMEOUT=300
export LOG_LEVEL=INFO

# 启动服务
docker-compose up -d
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和平台使用条款。 