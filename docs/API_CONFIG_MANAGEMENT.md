# MediaCrawler 配置管理API文档

## 概述

配置管理API提供了完整的爬虫配置管理功能，支持各平台的配置保存、加载、重置、预设应用等操作。

## 基础信息

- **基础URL**: `/api/v1/config`
- **内容类型**: `application/json`
- **认证**: 暂不需要

## API端点

### 1. 获取平台列表

**GET** `/api/v1/config/platforms`

获取所有支持的平台列表。

**响应示例**:
```json
{
  "platforms": ["xhs", "dy", "ks", "bili"],
  "total": 4,
  "status": "success"
}
```

### 2. 获取平台配置模板

**GET** `/api/v1/config/template/{platform}`

获取指定平台的默认配置模板。

**路径参数**:
- `platform`: 平台名称 (xhs, dy, ks, bili)

**响应示例**:
```json
{
  "platform": "xhs",
  "template": {
    "defaultKeywords": "编程副业,编程兼职",
    "defaultMaxCount": 20,
    "defaultCrawlerType": "search",
    "defaultLoginType": "qrcode",
    "enableComments": true,
    "enableSubComments": false,
    "enableImages": false,
    "enableVideos": true,
    "maxConcurrency": 2,
    "sleepInterval": 5,
    "timeoutSeconds": 300,
    "useProxy": false,
    "proxyStrategy": "disabled",
    "saveDataOption": "db",
    "dataRetentionDays": 30,
    "platformSpecific": {
      "searchNoteType": "video",
      "enableVideoFilter": true
    }
  },
  "status": "success"
}
```

### 3. 保存平台配置

**POST** `/api/v1/config/save/{platform}`

保存指定平台的配置。

**路径参数**:
- `platform`: 平台名称

**请求体**:
```json
{
  "platform": "xhs",
  "defaultKeywords": "编程副业,编程兼职",
  "defaultMaxCount": 20,
  "defaultCrawlerType": "search",
  "defaultLoginType": "qrcode",
  "enableComments": true,
  "enableSubComments": false,
  "enableImages": false,
  "enableVideos": true,
  "maxConcurrency": 2,
  "sleepInterval": 5,
  "timeoutSeconds": 300,
  "useProxy": false,
  "proxyStrategy": "disabled",
  "saveDataOption": "db",
  "dataRetentionDays": 30,
  "platformSpecific": {
    "searchNoteType": "video",
    "enableVideoFilter": true
  }
}
```

**响应示例**:
```json
{
  "platform": "xhs",
  "config": { ... },
  "last_updated": "2024-01-01T12:00:00",
  "status": "saved"
}
```

### 4. 加载平台配置

**GET** `/api/v1/config/load/{platform}`

加载指定平台的配置。

**路径参数**:
- `platform`: 平台名称

**响应示例**:
```json
{
  "platform": "xhs",
  "config": { ... },
  "last_updated": "2024-01-01T12:00:00",
  "status": "loaded"
}
```

### 5. 重置平台配置

**POST** `/api/v1/config/reset/{platform}`

重置指定平台的配置为默认值。

**路径参数**:
- `platform`: 平台名称

**响应示例**:
```json
{
  "platform": "xhs",
  "status": "reset",
  "message": "平台 xhs 配置已重置为默认值"
}
```

### 6. 应用配置预设

**POST** `/api/v1/config/preset`

应用预设配置到指定平台。

**请求体**:
```json
{
  "preset": "balanced",
  "platform": "xhs"
}
```

**预设类型**:
- `conservative`: 保守模式 - 低并发，长间隔
- `balanced`: 平衡模式 - 中等并发，适中间隔
- `aggressive`: 激进模式 - 高并发，短间隔

**响应示例**:
```json
{
  "preset": "balanced",
  "platform": "xhs",
  "config": { ... },
  "description": "已应用 balanced 预设配置"
}
```

### 7. 获取配置预设

**GET** `/api/v1/config/presets`

获取所有可用的配置预设。

**响应示例**:
```json
{
  "presets": {
    "conservative": {
      "name": "conservative",
      "description": "保守模式 - 低并发，长间隔，适合稳定环境",
      "config": { ... }
    },
    "balanced": {
      "name": "balanced", 
      "description": "平衡模式 - 中等并发，适中间隔，推荐使用",
      "config": { ... }
    },
    "aggressive": {
      "name": "aggressive",
      "description": "激进模式 - 高并发，短间隔，适合高性能环境", 
      "config": { ... }
    }
  },
  "total": 3,
  "status": "success"
}
```

### 8. 保存所有平台配置

**POST** `/api/v1/config/save-all`

保存所有平台的配置。

**响应示例**:
```json
{
  "saved_count": 4,
  "failed_platforms": [],
  "total_platforms": 4,
  "status": "completed"
}
```

### 9. 重置所有平台配置

**POST** `/api/v1/config/reset-all`

重置所有平台的配置为默认值。

**响应示例**:
```json
{
  "reset_count": 4,
  "total_platforms": 4,
  "status": "completed"
}
```

### 10. 导出所有配置

**GET** `/api/v1/config/export`

导出所有平台的配置。

**响应示例**:
```json
{
  "configs": {
    "xhs": { ... },
    "dy": { ... },
    "ks": { ... },
    "bili": { ... }
  },
  "export_time": "2024-01-01T12:00:00",
  "total_platforms": 4,
  "status": "success"
}
```

### 11. 导入配置

**POST** `/api/v1/config/import`

导入配置到各平台。

**请求体**:
```json
{
  "xhs": { ... },
  "dy": { ... },
  "ks": { ... },
  "bili": { ... }
}
```

**响应示例**:
```json
{
  "imported_count": 4,
  "failed_platforms": [],
  "total_platforms": 4,
  "status": "completed"
}
```

### 12. 获取配置概览

**GET** `/api/v1/config/overview`

获取所有平台的配置概览。

**响应示例**:
```json
{
  "total_platforms": 4,
  "configured_platforms": ["xhs", "dy"],
  "last_updated": "2024-01-01T12:00:00",
  "config_summary": {
    "xhs": {
      "has_custom_config": true,
      "last_updated": "2024-01-01T12:00:00",
      "default_keywords": "编程副业,编程兼职",
      "max_count": 20,
      "enable_videos": true
    },
    "dy": {
      "has_custom_config": true,
      "last_updated": "2024-01-01T12:00:00", 
      "default_keywords": "编程教程,技术分享",
      "max_count": 25,
      "enable_videos": true
    },
    "ks": {
      "has_custom_config": false,
      "last_updated": "never",
      "default_keywords": "编程学习,技术分享",
      "max_count": 20,
      "enable_videos": true
    },
    "bili": {
      "has_custom_config": false,
      "last_updated": "never",
      "default_keywords": "编程教程,技术分享", 
      "max_count": 30,
      "enable_videos": true
    }
  }
}
```

## 配置字段说明

### 基础配置字段

| 字段名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `defaultKeywords` | string | 默认搜索关键词 | "" |
| `defaultMaxCount` | integer | 默认爬取数量 | 20 |
| `defaultCrawlerType` | string | 默认爬虫类型 | "search" |
| `defaultLoginType` | string | 默认登录类型 | "qrcode" |

### 功能开关字段

| 字段名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `enableComments` | boolean | 是否获取评论 | false |
| `enableSubComments` | boolean | 是否获取子评论 | false |
| `enableImages` | boolean | 是否获取图片 | false |
| `enableVideos` | boolean | 是否获取视频 | true |

### 资源控制字段

| 字段名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `maxConcurrency` | integer | 最大并发数 | 2 |
| `sleepInterval` | integer | 请求间隔(秒) | 5 |
| `timeoutSeconds` | integer | 超时时间(秒) | 300 |

### 代理设置字段

| 字段名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `useProxy` | boolean | 是否启用代理 | false |
| `proxyStrategy` | string | 代理策略 | "disabled" |

### 数据存储字段

| 字段名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `saveDataOption` | string | 存储方式 | "db" |
| `dataRetentionDays` | integer | 数据保留天数 | 30 |

### 平台特定配置

#### 小红书 (xhs)
```json
{
  "searchNoteType": "video",
  "enableVideoFilter": true
}
```

#### 抖音 (dy)
```json
{
  "publishTimeType": 0,
  "enableVideoFilter": true
}
```

#### B站 (bili)
```json
{
  "allDay": false,
  "startDay": "2024-01-01",
  "endDay": "2024-01-31",
  "creatorMode": false
}
```

## 错误处理

所有API端点都遵循统一的错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

常见HTTP状态码：
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

## 使用示例

### cURL示例

1. **保存小红书配置**:
```bash
curl -X POST "http://localhost:8000/api/v1/config/save/xhs" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "defaultKeywords": "编程副业",
    "defaultMaxCount": 20,
    "enableVideos": true
  }'
```

2. **应用平衡预设**:
```bash
curl -X POST "http://localhost:8000/api/v1/config/preset" \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "balanced",
    "platform": "xhs"
  }'
```

3. **导出所有配置**:
```bash
curl -X GET "http://localhost:8000/api/v1/config/export" \
  -o configs.json
```

### Python示例

```python
import requests

# 保存配置
config_data = {
    "platform": "xhs",
    "defaultKeywords": "编程副业",
    "defaultMaxCount": 20,
    "enableVideos": True
}

response = requests.post(
    "http://localhost:8000/api/v1/config/save/xhs",
    json=config_data
)

if response.status_code == 200:
    print("配置保存成功")
else:
    print(f"保存失败: {response.json()}")
```

## 注意事项

1. **配置持久化**: 配置会保存到 `./data/configs/` 目录下的JSON文件中
2. **平台支持**: 目前支持 xhs、dy、ks、bili 四个平台
3. **预设配置**: 提供保守、平衡、激进三种预设模式
4. **配置验证**: 所有配置都会进行格式验证
5. **错误处理**: 详细的错误信息会返回给客户端

## 更新日志

- **v1.0.0**: 初始版本，支持基础配置管理功能
- **v1.1.0**: 添加配置预设和批量操作功能
- **v1.2.0**: 添加配置导入导出功能 