# MediaCrawler API 控制指南

## 🎯 概述

MediaCrawler 现在完全支持通过 API 来控制爬虫行为，无需依赖配置文件。所有爬虫参数都可以通过 API 动态设置。

## 📋 API 端点

### 1. 爬虫配置

#### 配置爬虫参数
```http
POST /api/v1/crawler/configure
```

**请求体:**
```json
{
  "platform": "xhs",
  "keywords": "编程副业",
  "max_count": 20,
  "account_id": null,
  "session_id": null,
  "login_type": "qrcode",
  "crawler_type": "search",
  "get_comments": false,
  "get_sub_comments": false,
  "download_media": false,
  "save_data_option": "db",
  "use_proxy": false,
  "proxy_strategy": "disabled",
  "max_concurrency": 2,
  "sleep_interval": 5,
  "timeout_seconds": 300,
  "platform_config": {}
}
```

**响应:**
```json
{
  "task_id": "task_1703123456_xhs",
  "config": {...},
  "estimated_time": "3分30秒",
  "resource_usage": {
    "cpu_usage": "40%",
    "memory_usage": "40MB",
    "network_usage": "100MB",
    "disk_usage": "0MB"
  }
}
```

### 2. 爬虫控制

#### 启动爬虫任务
```http
POST /api/v1/crawler/start
```

**请求体:** 同配置请求

**响应:**
```json
{
  "task_id": "task_1703123456_xhs",
  "status": "started",
  "message": "爬虫任务已启动",
  "data": {
    "task_id": "task_1703123456_xhs"
  }
}
```

#### 批量启动爬虫
```http
POST /api/v1/crawler/batch
```

**请求体:**
```json
{
  "tasks": [
    {
      "platform": "xhs",
      "keywords": "美食",
      "max_count": 20
    },
    {
      "platform": "dy",
      "keywords": "旅游",
      "max_count": 15
    }
  ],
  "batch_name": "美食旅游批量任务",
  "sequential": false
}
```

### 3. 任务管理

#### 获取任务状态
```http
GET /api/v1/crawler/status/{task_id}
```

**响应:**
```json
{
  "task_id": "task_1703123456_xhs",
  "status": "running",
  "progress": 45.5,
  "result": {
    "count": 9,
    "platform": "xhs"
  },
  "error": null,
  "created_at": "2024-01-01T10:30:00",
  "updated_at": "2024-01-01T10:35:00"
}
```

#### 获取任务列表
```http
GET /api/v1/crawler/tasks
```

**响应:**
```json
{
  "tasks": [
    {
      "task_id": "task_1703123456_xhs",
      "status": "running",
      "platform": "xhs",
      "created_at": "2024-01-01T10:30:00",
      "updated_at": "2024-01-01T10:35:00"
    }
  ]
}
```

#### 任务操作
```http
POST /api/v1/crawler/pause/{task_id}    # 暂停任务
POST /api/v1/crawler/resume/{task_id}   # 恢复任务
POST /api/v1/crawler/stop/{task_id}     # 停止任务
DELETE /api/v1/crawler/tasks/{task_id}  # 删除任务
```

### 4. 平台信息

#### 获取支持的平台
```http
GET /api/v1/crawler/platforms
```

**响应:**
```json
{
  "video_platforms": ["xhs", "dy", "ks", "bili"],
  "coming_soon_platforms": ["wb", "tieba", "zhihu"],
  "platform_descriptions": {
    "wb": "微博",
    "tieba": "贴吧",
    "zhihu": "知乎"
  }
}
```

#### 获取平台配置模板
```http
GET /api/v1/crawler/config/template/{platform}
```

**响应:**
```json
{
  "platform": "xhs",
  "template": {
    "max_concurrency": 2,
    "sleep_interval": 5,
    "get_comments": false,
    "download_media": false,
    "video_only": true
  },
  "recommendations": {
    "max_concurrency": "建议2-3，避免资源耗尽",
    "sleep_interval": "建议5秒，避免反爬",
    "get_comments": "建议关闭，减少资源消耗",
    "video_only": "建议开启，专注短视频"
  }
}
```

## 🔧 参数说明

### 基础参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `platform` | string | - | 平台名称 (xhs/dy/ks/bili) |
| `keywords` | string | - | 搜索关键词 |
| `max_count` | int | 20 | 最大爬取数量 (1-100) |
| `crawler_type` | string | "search" | 爬虫类型 (search/user) |
| `login_type` | string | "qrcode" | 登录类型 (qrcode/phone) |

### 功能开关

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `get_comments` | boolean | false | 是否获取评论 |
| `get_sub_comments` | boolean | false | 是否获取子评论 |
| `download_media` | boolean | false | 是否下载媒体文件 |
| `use_proxy` | boolean | false | 是否使用代理 |

### 资源控制

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_concurrency` | int | 2 | 最大并发数 (1-5) |
| `sleep_interval` | int | 5 | 请求间隔(秒) (1-30) |
| `timeout_seconds` | int | 300 | 任务超时时间(秒) (60-1800) |

### 代理设置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `proxy_strategy` | string | "disabled" | 代理策略 |

## 📊 平台特定配置

### 小红书 (XHS)
```json
{
  "max_concurrency": 2,
  "sleep_interval": 5,
  "get_comments": false,
  "download_media": false,
  "video_only": true
}
```

### 抖音 (DY)
```json
{
  "max_concurrency": 1,
  "sleep_interval": 8,
  "get_comments": false,
  "download_media": false,
  "video_only": true
}
```

### 快手 (KS)
```json
{
  "max_concurrency": 2,
  "sleep_interval": 5,
  "get_comments": false,
  "download_media": false,
  "video_only": true
}
```

### B站 (BILI)
```json
{
  "max_concurrency": 2,
  "sleep_interval": 5,
  "get_comments": false,
  "download_media": false,
  "video_only": true
}
```

## 🚀 使用示例

### 1. 基础爬虫任务

```bash
curl -X POST "http://localhost:8000/api/v1/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "keywords": "美食",
    "max_count": 20,
    "get_comments": false,
    "download_media": false,
    "max_concurrency": 2,
    "sleep_interval": 5
  }'
```

### 2. 批量爬虫任务

```bash
curl -X POST "http://localhost:8000/api/v1/crawler/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "platform": "xhs",
        "keywords": "美食",
        "max_count": 20
      },
      {
        "platform": "dy",
        "keywords": "旅游",
        "max_count": 15
      }
    ],
    "sequential": false
  }'
```

### 3. 监控任务状态

```bash
# 获取任务列表
curl "http://localhost:8000/api/v1/crawler/tasks"

# 获取特定任务状态
curl "http://localhost:8000/api/v1/crawler/status/task_1703123456_xhs"
```

### 4. 任务控制

```bash
# 暂停任务
curl -X POST "http://localhost:8000/api/v1/crawler/pause/task_1703123456_xhs"

# 恢复任务
curl -X POST "http://localhost:8000/api/v1/crawler/resume/task_1703123456_xhs"

# 停止任务
curl -X POST "http://localhost:8000/api/v1/crawler/stop/task_1703123456_xhs"

# 删除任务
curl -X DELETE "http://localhost:8000/api/v1/crawler/tasks/task_1703123456_xhs"
```

## 🎛️ 前端控制界面

访问 `http://localhost:8000/static/crawler_control.html` 可以使用图形化界面控制爬虫。

### 功能特性:
- ✅ 平台选择
- ✅ 参数配置
- ✅ 快速预设
- ✅ 任务监控
- ✅ 资源监控
- ✅ 批量操作

## ⚠️ 注意事项

### 1. 资源管理
- **并发数**: 建议 2-3，避免资源耗尽
- **爬取数量**: 建议 20-30，避免长时间运行
- **功能开关**: 建议关闭评论和媒体下载，减少资源消耗

### 2. 反爬虫策略
- **请求间隔**: 建议 5-8 秒，避免被反爬
- **代理使用**: 谨慎使用，避免IP被封
- **登录状态**: 确保账号登录状态正常

### 3. 错误处理
- **网络超时**: 自动重试机制
- **登录失败**: 需要重新登录
- **资源不足**: 自动暂停或降低并发

### 4. 最佳实践
- 先配置再启动
- 监控任务状态
- 及时处理错误
- 合理设置参数

## 🔄 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 任务不存在 |
| 500 | 服务器内部错误 |

## 📈 性能优化

### 1. 保守模式
```json
{
  "max_concurrency": 1,
  "sleep_interval": 8,
  "max_count": 10,
  "get_comments": false,
  "download_media": false
}
```

### 2. 平衡模式
```json
{
  "max_concurrency": 2,
  "sleep_interval": 5,
  "max_count": 20,
  "get_comments": false,
  "download_media": false
}
```

### 3. 激进模式
```json
{
  "max_concurrency": 3,
  "sleep_interval": 3,
  "max_count": 30,
  "get_comments": true,
  "download_media": false
}
```

---

**最后更新**: 2024年1月
**版本**: v1.0
**维护者**: MediaCrawler Team 