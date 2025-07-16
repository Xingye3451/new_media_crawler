# API多平台抓取使用指南

## 概述

MediaCrawler API 现在支持多平台同时抓取功能，通过 RESTful API 接口可以轻松实现多平台内容的并发抓取。

## API 端点

### 1. 启动多平台抓取任务

**POST** `/api/v1/multi-platform/start`

启动多平台同时抓取任务。

#### 请求参数

```json
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

#### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platforms` | List[str] | ✅ | 平台列表，支持：xhs, dy, ks, bili, wb, tieba, zhihu |
| `keywords` | str | ✅ | 搜索关键词 |
| `max_count_per_platform` | int | ❌ | 每个平台最大抓取数量，默认50 |
| `enable_comments` | bool | ❌ | 是否抓取评论，默认false |
| `enable_images` | bool | ❌ | 是否抓取图片，默认false |
| `save_format` | str | ❌ | 保存格式，支持：json, csv，默认json |
| `session_ids` | Dict[str, str] | ❌ | 各平台的登录会话ID |

#### 响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "多平台抓取任务已启动，平台: xhs, dy, ks，关键词: 美食探店"
}
```

### 2. 获取任务状态

**GET** `/api/v1/multi-platform/status/{task_id}`

获取多平台抓取任务的状态信息。

#### 响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "platforms": ["xhs", "dy", "ks"],
  "keywords": "美食探店",
  "progress": {
    "total": 3,
    "completed": 3,
    "failed": 0,
    "pending": 0
  },
  "results": {
    "xhs": 45,
    "dy": 38,
    "ks": 42
  },
  "errors": null,
  "created_at": "2024-01-01T12:00:00",
  "started_at": "2024-01-01T12:00:05",
  "completed_at": "2024-01-01T12:15:30"
}
```

### 3. 获取任务结果

**GET** `/api/v1/multi-platform/results/{task_id}?format_type=json`

获取多平台抓取任务的结果数据。

#### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `format_type` | str | 返回格式，支持：table, json，默认table |

#### JSON格式响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_count": 125,
  "format": "json",
  "results": [
    {
      "platform": "xhs",
      "platform_name": "小红书",
      "content_id": "note_123",
      "title": "超好吃的火锅店推荐",
      "author": "美食达人",
      "publish_time": "2024-01-01 12:00:00",
      "content": "今天发现了一家超级好吃的火锅店...",
      "likes": 1234,
      "comments": 56,
      "shares": 78,
      "views": 9999,
      "download_links": ["http://example.com/image1.jpg"],
      "tags": ["美食", "火锅"],
      "url": "https://www.xiaohongshu.com/note/123"
    }
  ]
}
```

#### 表格格式响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_count": 125,
  "format": "table",
  "results": [
    {
      "platform": "小红书",
      "title": "超好吃的火锅店推荐",
      "author": "美食达人",
      "likes": 1234,
      "comments": 56,
      "download_links_count": 1,
      "url": "https://www.xiaohongshu.com/note/123"
    }
  ]
}
```

### 4. 获取任务列表

**GET** `/api/v1/multi-platform/tasks`

获取所有多平台抓取任务列表。

#### 响应示例

```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "platforms": ["xhs", "dy", "ks"],
      "keywords": "美食探店",
      "progress": {
        "total": 3,
        "completed": 3,
        "failed": 0,
        "pending": 0
      },
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total": 1
}
```

### 5. 取消任务

**POST** `/api/v1/multi-platform/cancel/{task_id}`

取消正在运行的多平台抓取任务。

#### 响应示例

```json
{
  "message": "任务已取消",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 6. 获取功能信息

**GET** `/api/v1/multi-platform/info`

获取多平台抓取功能的详细信息。

#### 响应示例

```json
{
  "feature": "多平台同时抓取",
  "description": "支持多个平台同时抓取相同关键词，统一结果格式",
  "supported_platforms": {
    "xhs": "小红书",
    "dy": "抖音",
    "ks": "快手",
    "bili": "B站",
    "wb": "微博",
    "tieba": "贴吧",
    "zhihu": "知乎"
  },
  "capabilities": [
    "并发抓取多个平台",
    "统一结果格式输出",
    "任务状态跟踪",
    "进度监控",
    "错误处理"
  ],
  "output_formats": ["json", "csv"],
  "max_platforms": 7
}
```

## 使用示例

### Python 示例

```python
import requests
import time

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"

def start_multi_platform_crawl():
    """启动多平台抓取任务"""
    
    # 请求数据
    data = {
        "platforms": ["xhs", "dy", "ks"],
        "keywords": "美食探店",
        "max_count_per_platform": 30,
        "enable_comments": False,
        "enable_images": True,
        "save_format": "json"
    }
    
    # 发送请求
    response = requests.post(f"{BASE_URL}/multi-platform/start", json=data)
    
    if response.status_code == 200:
        result = response.json()
        task_id = result["task_id"]
        print(f"任务创建成功: {task_id}")
        return task_id
    else:
        print(f"创建任务失败: {response.text}")
        return None

def monitor_task_status(task_id):
    """监控任务状态"""
    
    while True:
        response = requests.get(f"{BASE_URL}/multi-platform/status/{task_id}")
        
        if response.status_code == 200:
            status = response.json()
            print(f"任务状态: {status['status']}")
            print(f"进度: {status['progress']['completed']}/{status['progress']['total']}")
            
            if status['status'] in ['completed', 'failed']:
                return status
        else:
            print(f"获取状态失败: {response.text}")
            return None
        
        time.sleep(5)  # 每5秒检查一次

def get_task_results(task_id):
    """获取任务结果"""
    
    # 获取JSON格式结果
    response = requests.get(f"{BASE_URL}/multi-platform/results/{task_id}?format_type=json")
    
    if response.status_code == 200:
        results = response.json()
        print(f"总共获取 {results['total_count']} 条数据")
        
        # 按平台统计
        platform_stats = {}
        for item in results['results']:
            platform = item['platform_name']
            if platform not in platform_stats:
                platform_stats[platform] = 0
            platform_stats[platform] += 1
        
        print("按平台统计:")
        for platform, count in platform_stats.items():
            print(f"  {platform}: {count} 条")
        
        return results
    else:
        print(f"获取结果失败: {response.text}")
        return None

def main():
    """主函数"""
    # 1. 启动任务
    task_id = start_multi_platform_crawl()
    if not task_id:
        return
    
    # 2. 监控状态
    status = monitor_task_status(task_id)
    if not status or status['status'] == 'failed':
        print("任务执行失败")
        return
    
    # 3. 获取结果
    results = get_task_results(task_id)
    if results:
        print("任务完成！")

if __name__ == "__main__":
    main()
```

### cURL 示例

```bash
# 1. 启动多平台抓取任务
curl -X POST "http://localhost:8000/api/v1/multi-platform/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["xhs", "dy", "ks"],
    "keywords": "美食探店",
    "max_count_per_platform": 30,
    "enable_images": true,
    "save_format": "json"
  }'

# 2. 获取任务状态
curl "http://localhost:8000/api/v1/multi-platform/status/{task_id}"

# 3. 获取任务结果（JSON格式）
curl "http://localhost:8000/api/v1/multi-platform/results/{task_id}?format_type=json"

# 4. 获取任务结果（表格格式）
curl "http://localhost:8000/api/v1/multi-platform/results/{task_id}?format_type=table"

# 5. 获取所有任务列表
curl "http://localhost:8000/api/v1/multi-platform/tasks"

# 6. 取消任务
curl -X POST "http://localhost:8000/api/v1/multi-platform/cancel/{task_id}"

# 7. 获取功能信息
curl "http://localhost:8000/api/v1/multi-platform/info"
```

### JavaScript 示例

```javascript
// API基础URL
const BASE_URL = "http://localhost:8000/api/v1";

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
        const response = await fetch(`${BASE_URL}/multi-platform/start`, {
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
            const response = await fetch(`${BASE_URL}/multi-platform/status/${taskId}`);
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
        const response = await fetch(`${BASE_URL}/multi-platform/results/${taskId}?format_type=json`);
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
    // 1. 启动任务
    const taskId = await startMultiPlatformCrawl();
    if (!taskId) return;
    
    // 2. 监控状态
    const status = await monitorTaskStatus(taskId);
    if (!status || status.status === 'failed') {
        console.log('任务执行失败');
        return;
    }
    
    // 3. 获取结果
    const results = await getTaskResults(taskId);
    if (results) {
        console.log('任务完成！');
    }
}

// 运行
main();
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

### 1. 任务管理
- 使用任务ID跟踪任务状态
- 定期检查任务进度
- 及时处理失败的任务

### 2. 参数优化
- 合理设置抓取数量，避免过多请求
- 根据需要选择是否抓取评论和图片
- 选择合适的保存格式

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