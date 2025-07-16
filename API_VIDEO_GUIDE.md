# 短视频内容API使用指南

本平台专注于短视频内容爬取和管理，以下是相关API的使用说明。

## 🎯 短视频优先平台

### 主要短视频平台
- **小红书 (xhs)**: 专注短视频内容，可单独搜索视频类型
- **抖音 (dy)**: 纯短视频平台
- **快手 (ks)**: 纯短视频平台  
- **B站 (bili)**: 视频平台，包含短视频内容

### TODO/暂时忽略的平台
- **微博 (wb)**: 视频支持较少，暂时TODO
- **贴吧 (tieba)**: 主要文本内容，视频支持待开发

## 📡 主要API接口

### 1. 获取短视频内容列表
```http
POST /api/v1/content/videos
```

**参数:**
```json
{
  "keyword": "编程副业",     // 可选，关键词筛选
  "platform": "xhs",       // 可选，指定平台
  "page": 1,               // 页码
  "page_size": 20          // 每页数量
}
```

**特点:**
- 自动筛选仅视频内容
- 仅查询视频优先平台（抖音、快手、小红书、B站）
- 排除TODO平台
- 按爬取时间降序排列

### 2. 获取短视频平台信息
```http
GET /api/v1/content/video-platforms
```

**返回:**
```json
{
  "video_priority_platforms": [
    {
      "code": "xhs",
      "name": "小红书",
      "description": "小红书短视频内容",
      "total_count": 1000,
      "video_count": 800,
      "video_ratio": 80.0,
      "primary_content_type": "video"
    }
  ],
  "total_platforms": 4,
  "total_video_content": 5000,
  "message": "本平台专注于短视频内容，以上为主要短视频平台"
}
```

### 3. 通用内容查询（支持短视频优先筛选）
```http
POST /api/v1/content/list
```

**短视频优先参数:**
```json
{
  "platform": "xhs",
  "keyword": "编程",
  "video_only": true,                    // 仅显示视频内容
  "video_platforms_only": true,          // 仅查询视频优先平台
  "exclude_todo_platforms": true,        // 排除TODO平台
  "page": 1,
  "page_size": 20
}
```

### 4. 启动短视频爬虫任务
```http
POST /api/v1/crawler/start
```

**短视频优先参数:**
```json
{
  "platform": "xhs",
  "keywords": "编程副业",
  "max_notes_count": 50,
  "video_priority": true,               // 短视频优先模式
  "video_only": false,                  // 是否仅爬取视频
  "save_data_option": "db",
  "login_type": "qrcode",
  "crawler_type": "search"
}
```

## 🎬 平台配置详情

### 小红书 (xhs)
- **主要内容类型**: 视频优先
- **视频筛选条件**: `type = 'video'`
- **特点**: 可以单独搜索视频内容，适合短视频爬取

### 抖音 (dy)
- **主要内容类型**: 视频
- **视频筛选条件**: `aweme_type IN ('video', 'aweme')`
- **特点**: 纯短视频平台

### 快手 (ks)
- **主要内容类型**: 视频
- **视频筛选条件**: `video_type = 'video'`
- **特点**: 纯短视频平台

### B站 (bili)
- **主要内容类型**: 视频
- **视频筛选条件**: `video_type IN ('video', 'short')`
- **特点**: 包含长短视频内容

## 📊 数据字段说明

### 统一内容模型 (UnifiedContent)
```json
{
  "id": 123,
  "platform": "xhs",
  "platform_name": "小红书",
  "content_id": "abc123",
  "content_type": "video",              // video/image/text/mixed
  "title": "视频标题",
  "description": "视频描述",
  "author_name": "作者昵称",
  "like_count": 1000,
  "comment_count": 50,
  "view_count": 5000,
  "video_url": "https://...",           // 视频链接
  "cover_url": "https://...",           // 封面图片
  "publish_time": 1703123456,
  "crawl_time": 1703123456,
  "source_keyword": "编程副业",
  "tags": ["编程", "副业"]
}
```

## 🚀 使用建议

1. **优先使用短视频专用API**: `/api/v1/content/videos` 获取最佳的短视频内容
2. **小红书视频搜索**: 设置 `video_priority=true` 优先搜索视频内容
3. **排除非视频平台**: 使用 `exclude_todo_platforms=true` 提高查询效率
4. **数据库存储**: 建议使用 `save_data_option="db"` 便于后续查询和管理

## 📝 注意事项

- 本平台专注短视频内容，其他类型内容为辅助功能
- 微博和贴吧平台的视频支持有限，建议优先使用其他平台
- 所有时间戳均为Unix时间戳格式
- 视频URL可能需要特定的访问权限或登录状态 