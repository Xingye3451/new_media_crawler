# MediaCrawler 任务管理功能

## 概述

MediaCrawler 任务管理功能提供了完整的任务生命周期管理，包括任务创建、执行、监控、结果查看等功能。系统支持多平台爬取任务，并提供友好的Web界面进行管理。

## 主要功能

### 1. 任务管理
- **任务创建**: 支持创建不同平台的爬取任务
- **任务状态**: 实时监控任务执行状态（等待中、运行中、已完成、失败）
- **任务操作**: 支持收藏、置顶、删除等操作
- **任务筛选**: 按平台、状态、关键词等条件筛选任务

### 2. 视频管理
- **视频预览**: 支持在线预览爬取的视频内容
- **视频下载**: 提供视频下载功能
- **视频收藏**: 将视频保存到MinIO对象存储
- **视频详情**: 查看视频的详细信息

### 3. 日志记录
- **操作日志**: 记录所有任务相关操作
- **执行日志**: 记录任务执行过程中的详细信息
- **错误日志**: 记录任务执行过程中的错误信息

## 数据库表结构

### crawler_tasks 表
```sql
CREATE TABLE `crawler_tasks` (
  `id` varchar(36) NOT NULL,
  `platform` varchar(20) NOT NULL,
  `task_type` varchar(20) NOT NULL,
  `keywords` text,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `progress` float DEFAULT '0',
  `result_count` int(11) DEFAULT '0',
  `error_message` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `started_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `user_id` varchar(36) DEFAULT NULL,
  `params` json DEFAULT NULL,
  `priority` int DEFAULT 0,
  `is_favorite` tinyint(1) DEFAULT 0,
  `deleted` tinyint(1) DEFAULT 0,
  `is_pinned` tinyint(1) DEFAULT 0,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_security_id` varchar(64) DEFAULT NULL,
  `user_signature` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### douyin_aweme 表（扩展字段）
```sql
ALTER TABLE `douyin_aweme`
ADD COLUMN `author_id` varchar(64) DEFAULT NULL COMMENT '作者ID',
ADD COLUMN `author_name` varchar(128) DEFAULT NULL COMMENT '作者昵称',
ADD COLUMN `author_avatar` varchar(255) DEFAULT NULL COMMENT '作者头像',
ADD COLUMN `cover_url` varchar(255) DEFAULT NULL COMMENT '封面图',
ADD COLUMN `play_url` varchar(255) DEFAULT NULL COMMENT '播放页链接',
ADD COLUMN `download_url` varchar(255) DEFAULT NULL COMMENT '无水印下载链接',
ADD COLUMN `share_url` varchar(255) DEFAULT NULL COMMENT '分享链接',
ADD COLUMN `is_collected` tinyint(1) DEFAULT 0 COMMENT '是否已收藏到minio',
ADD COLUMN `minio_url` varchar(255) DEFAULT NULL COMMENT 'minio存储链接',
ADD COLUMN `task_id` varchar(36) DEFAULT NULL COMMENT '关联任务ID';
```

### crawler_task_logs 表
```sql
CREATE TABLE `crawler_task_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) NOT NULL,
  `action_type` varchar(32) NOT NULL,
  `content` text,
  `operator` varchar(64) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## API接口

### 任务管理接口

#### 创建任务
```http
POST /api/v1/task-management/tasks
Content-Type: application/json

{
  "platform": "dy",
  "task_type": "search",
  "keywords": "编程副业",
  "user_id": "user123",
  "priority": 0
}
```

#### 获取任务列表
```http
GET /api/v1/task-management/tasks?page=1&page_size=20&platform=dy&status=completed
```

#### 获取任务详情
```http
GET /api/v1/task-management/tasks/{task_id}
```

#### 更新任务
```http
PUT /api/v1/task-management/tasks/{task_id}
Content-Type: application/json

{
  "status": "completed",
  "progress": 100,
  "result_count": 50
}
```

#### 删除任务
```http
DELETE /api/v1/task-management/tasks/{task_id}
```

### 视频管理接口

#### 获取任务视频列表
```http
GET /api/v1/task-management/tasks/{task_id}/videos?page=1&page_size=20
```

#### 获取视频详情
```http
GET /api/v1/task-management/videos/{video_id}
```

#### 视频操作
```http
POST /api/v1/task-management/videos/{video_id}/action
Content-Type: application/json

{
  "action": "favorite",
  "video_id": 123
}
```

### 任务操作接口

#### 任务操作
```http
POST /api/v1/task-management/tasks/{task_id}/action
Content-Type: application/json

{
  "action": "favorite",
  "task_id": "task-uuid"
}
```

### 统计接口

#### 获取任务统计
```http
GET /api/v1/task-management/tasks/statistics
```

#### 获取任务日志
```http
GET /api/v1/task-management/tasks/{task_id}/logs?page=1&page_size=50
```

## Web界面

### 任务管理页面
访问 `http://localhost:8000/task_results.html` 查看任务管理界面。

### 任务视频页面
访问 `http://localhost:8000/task_videos.html?task_id={task_id}` 查看任务视频列表。

## 使用示例

### 1. 创建爬取任务
```python
import requests

# 创建抖音搜索任务
task_data = {
    "platform": "dy",
    "task_type": "search", 
    "keywords": "编程副业",
    "user_id": "user123",
    "priority": 0
}

response = requests.post(
    "http://localhost:8000/api/v1/task-management/tasks",
    json=task_data
)

if response.status_code == 200:
    task_id = response.json()["data"]["task_id"]
    print(f"任务创建成功: {task_id}")
```

### 2. 监控任务状态
```python
import requests
import time

task_id = "your-task-id"

while True:
    response = requests.get(f"http://localhost:8000/api/v1/task-management/tasks/{task_id}")
    
    if response.status_code == 200:
        task = response.json()["data"]
        print(f"任务状态: {task['status']}, 进度: {task['progress']}%")
        
        if task['status'] in ['completed', 'failed']:
            break
    
    time.sleep(5)
```

### 3. 查看任务视频
```python
import requests

task_id = "your-task-id"

# 获取任务视频列表
response = requests.get(
    f"http://localhost:8000/api/v1/task-management/tasks/{task_id}/videos"
)

if response.status_code == 200:
    videos = response.json()["data"]["items"]
    print(f"找到 {len(videos)} 个视频")
    
    for video in videos:
        print(f"视频: {video['desc']}")
        print(f"作者: {video['author_name']}")
        print(f"点赞: {video['digg_count']}")
        print("---")
```

## 配置说明

### 数据库配置
确保数据库连接配置正确，并执行数据库升级SQL：
```bash
mysql -u username -p database_name < db_upgrade.sql
```

### MinIO配置
如需使用视频收藏功能，请配置MinIO服务：
```yaml
minio:
  endpoint: "192.168.31.231:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  bucket: "mediacrawler-videos"
  secure: false
```

## 注意事项

1. **数据安全**: 所有任务操作都会记录日志，便于审计和追踪
2. **性能优化**: 大量数据查询时建议使用分页
3. **存储管理**: 视频收藏功能会占用存储空间，请定期清理
4. **错误处理**: 系统提供完善的错误处理和日志记录
5. **权限控制**: 可根据需要添加用户权限控制

## 故障排除

### 常见问题

1. **任务创建失败**
   - 检查数据库连接
   - 验证请求参数格式
   - 查看服务器日志

2. **视频无法预览**
   - 检查视频URL是否有效
   - 确认网络连接正常
   - 验证视频格式支持

3. **MinIO上传失败**
   - 检查MinIO服务状态
   - 验证存储空间是否充足
   - 确认网络连接正常

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持任务CRUD操作
- 支持视频预览和下载
- 支持MinIO视频存储
- 提供Web管理界面 