# 统一存储系统设计文档

## 概述

为了简化多平台爬虫的数据存储管理，我们设计了一套统一的存储系统，将所有平台的内容和评论数据统一存储到标准化的表中。

## 设计目标

1. **统一数据结构**: 所有平台的内容和评论使用相同的表结构
2. **字段映射**: 通过配置化的字段映射，将平台特定字段转换为统一字段
3. **向后兼容**: 保持现有API接口不变，内部实现使用统一存储
4. **数据完整性**: 保留原始数据，同时提供标准化的查询接口

## 表结构设计

### 统一内容表 (`unified_content`)

```sql
CREATE TABLE `unified_content` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content_id` varchar(100) NOT NULL COMMENT '内容ID',
  `platform` varchar(20) NOT NULL COMMENT '平台名称',
  `content_type` varchar(50) COMMENT '内容类型',
  `task_id` varchar(36) COMMENT '任务ID',
  `source_keyword` varchar(200) COMMENT '来源关键词',
  `title` varchar(500) COMMENT '标题',
  `description` text COMMENT '描述',
  `content` longtext COMMENT '内容',
  `create_time` bigint COMMENT '创建时间戳',
  `publish_time` bigint COMMENT '发布时间戳',
  `update_time` bigint COMMENT '更新时间戳',
  `author_id` varchar(100) COMMENT '作者ID',
  `author_name` varchar(100) COMMENT '作者名称',
  `author_nickname` varchar(100) COMMENT '作者昵称',
  `author_avatar` text COMMENT '作者头像',
  `author_signature` text COMMENT '作者签名',
  `author_unique_id` varchar(100) COMMENT '作者唯一ID',
  `author_sec_uid` varchar(100) COMMENT '作者sec_uid',
  `author_short_id` varchar(100) COMMENT '作者短ID',
  `like_count` int DEFAULT '0' COMMENT '点赞数',
  `comment_count` int DEFAULT '0' COMMENT '评论数',
  `share_count` int DEFAULT '0' COMMENT '分享数',
  `collect_count` int DEFAULT '0' COMMENT '收藏数',
  `view_count` int DEFAULT '0' COMMENT '播放数',
  `cover_url` text COMMENT '封面URL',
  `video_url` text COMMENT '视频URL',
  `video_download_url` text COMMENT '视频下载URL',
  `video_play_url` text COMMENT '视频播放URL',
  `video_share_url` text COMMENT '视频分享URL',
  `image_urls` text COMMENT '图片URL列表',
  `audio_url` text COMMENT '音频URL',
  `file_urls` text COMMENT '文件URL列表',
  `ip_location` varchar(100) COMMENT 'IP位置',
  `location` varchar(200) COMMENT '位置信息',
  `tags` text COMMENT '标签',
  `categories` text COMMENT '分类',
  `topics` text COMMENT '话题',
  `is_favorite` tinyint DEFAULT '0' COMMENT '是否收藏',
  `is_deleted` tinyint DEFAULT '0' COMMENT '是否删除',
  `is_private` tinyint DEFAULT '0' COMMENT '是否私密',
  `is_original` tinyint DEFAULT '0' COMMENT '是否原创',
  `minio_url` text COMMENT 'MinIO URL',
  `local_path` varchar(500) COMMENT '本地路径',
  `file_size` bigint COMMENT '文件大小',
  `storage_type` varchar(20) DEFAULT 'url_only' COMMENT '存储类型',
  `metadata` text COMMENT '元数据',
  `raw_data` longtext COMMENT '原始数据',
  `extra_info` text COMMENT '额外信息',
  `add_ts` bigint COMMENT '添加时间戳',
  `last_modify_ts` bigint COMMENT '最后修改时间戳',
  PRIMARY KEY (`id`),
  KEY `idx_unified_content_platform_content_id` (`platform`,`content_id`),
  KEY `idx_unified_content_task_id` (`task_id`),
  KEY `idx_unified_content_author_id` (`author_id`),
  KEY `idx_unified_content_create_time` (`create_time`),
  KEY `idx_unified_content_add_ts` (`add_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 统一评论表 (`unified_comment`)

```sql
CREATE TABLE `unified_comment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment_id` varchar(100) NOT NULL COMMENT '评论ID',
  `content_id` varchar(100) NOT NULL COMMENT '内容ID',
  `platform` varchar(20) NOT NULL COMMENT '平台名称',
  `parent_id` varchar(100) COMMENT '父评论ID',
  `reply_to_id` varchar(100) COMMENT '回复评论ID',
  `content` text COMMENT '评论内容',
  `text` text COMMENT '纯文本内容',
  `html_content` text COMMENT 'HTML内容',
  `author_id` varchar(100) COMMENT '作者ID',
  `author_name` varchar(100) COMMENT '作者名称',
  `author_nickname` varchar(100) COMMENT '作者昵称',
  `author_avatar` text COMMENT '作者头像',
  `like_count` int DEFAULT '0' COMMENT '点赞数',
  `reply_count` int DEFAULT '0' COMMENT '回复数',
  `share_count` int DEFAULT '0' COMMENT '分享数',
  `create_time` bigint COMMENT '创建时间戳',
  `publish_time` bigint COMMENT '发布时间戳',
  `is_deleted` tinyint DEFAULT '0' COMMENT '是否删除',
  `is_hidden` tinyint DEFAULT '0' COMMENT '是否隐藏',
  `is_top` tinyint DEFAULT '0' COMMENT '是否置顶',
  `metadata` text COMMENT '元数据',
  `raw_data` longtext COMMENT '原始数据',
  `add_ts` bigint COMMENT '添加时间戳',
  `last_modify_ts` bigint COMMENT '最后修改时间戳',
  PRIMARY KEY (`id`),
  KEY `idx_unified_comment_platform_comment_id` (`platform`,`comment_id`),
  KEY `idx_unified_comment_content_id` (`content_id`),
  KEY `idx_unified_comment_author_id` (`author_id`),
  KEY `idx_unified_comment_create_time` (`create_time`),
  KEY `idx_unified_comment_add_ts` (`add_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 字段映射配置

### 平台字段映射

每个平台都有特定的字段映射配置，将平台特定字段映射到统一字段：

```python
PLATFORM_FIELD_MAPPINGS = {
    "douyin": {
        "content_id": "aweme_id",
        "content_type": "aweme_type", 
        "title": "title",
        "description": "desc",
        "author_id": "user_id",
        "author_name": "nickname",
        # ... 更多映射
    },
    "xhs": {
        "content_id": "note_id",
        "content_type": "note_type",
        "title": "title",
        "description": "desc",
        # ... 更多映射
    },
    # ... 其他平台
}
```

## 核心功能

### 1. 统一存储接口

```python
# 内容操作
async def query_content_by_content_id(platform: str, content_id: str) -> Dict
async def add_new_content(platform: str, content_item: Dict, task_id: str = None) -> int
async def update_content_by_content_id(platform: str, content_id: str, content_item: Dict) -> int

# 评论操作
async def query_comment_by_comment_id(platform: str, comment_id: str) -> Dict
async def add_new_comment(platform: str, comment_item: Dict) -> int
async def update_comment_by_comment_id(platform: str, comment_id: str, comment_item: Dict) -> int

# 列表查询
async def get_content_list(platform: str = None, task_id: str = None, page: int = 1, page_size: int = 20) -> Dict
async def get_comment_list(content_id: str = None, platform: str = None, page: int = 1, page_size: int = 20) -> Dict
```

### 2. 字段映射

```python
def map_platform_fields(platform: str, data: Dict) -> Dict:
    """将平台特定字段映射到统一字段"""
    if platform not in PLATFORM_FIELD_MAPPINGS:
        return data
    
    mapping = PLATFORM_FIELD_MAPPINGS[platform]
    mapped_data = {}
    
    # 添加平台标识
    mapped_data["platform"] = platform
    
    # 映射字段
    for unified_field, platform_field in mapping.items():
        if platform_field in data:
            mapped_data[unified_field] = data[platform_field]
    
    # 保留原始数据
    mapped_data["raw_data"] = json.dumps(data, ensure_ascii=False)
    
    return mapped_data
```

### 3. 数据序列化

```python
def serialize_for_db(data):
    """序列化数据，将dict/list转换为JSON字符串"""
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                new_data[k] = json.dumps(v, ensure_ascii=False)
            else:
                new_data[k] = v
        return new_data
    elif isinstance(data, list):
        return json.dumps(data, ensure_ascii=False)
    else:
        return data
```

## 迁移策略

### 1. 数据迁移

使用 `migrate_to_unified_tables.py` 脚本将现有平台特定表的数据迁移到统一表中：

```bash
python migrate_to_unified_tables.py
```

### 2. 代码适配

更新各平台的存储实现，使用统一存储接口：

```python
# 原来的实现
async def query_content_by_content_id(content_id: str) -> Dict:
    sql = f"SELECT * FROM douyin_aweme WHERE aweme_id = '{content_id}'"
    # ...

# 新的实现
async def query_content_by_content_id(content_id: str) -> Dict:
    return await unified_query_content("douyin", content_id)
```

### 3. 旧表清理

迁移完成后，可以选择删除旧表：

```python
async def drop_old_tables():
    old_tables = [
        "douyin_aweme", "douyin_aweme_comment",
        "xhs_note", "xhs_note_comment",
        # ... 其他旧表
    ]
    for table in old_tables:
        await db.execute(f"DROP TABLE IF EXISTS {table}")
```

## 优势

1. **统一管理**: 所有平台数据使用相同的表结构和查询接口
2. **简化维护**: 减少重复代码，统一数据操作逻辑
3. **扩展性强**: 新增平台只需配置字段映射即可
4. **数据完整性**: 保留原始数据，支持复杂查询需求
5. **性能优化**: 统一的索引设计，提高查询效率

## 使用示例

### 存储内容

```python
from store.unified_store import add_new_content

# 存储抖音内容
content_data = {
    "aweme_id": "123456789",
    "title": "测试视频",
    "desc": "这是一个测试视频",
    "user_id": "user123",
    "nickname": "测试用户",
    # ... 其他字段
}

await add_new_content("douyin", content_data, task_id="task_001")
```

### 查询内容

```python
from store.unified_store import get_content_list

# 查询所有平台内容
all_content = await get_content_list(page=1, page_size=20)

# 查询特定平台内容
douyin_content = await get_content_list(platform="douyin", page=1, page_size=20)

# 查询特定任务内容
task_content = await get_content_list(task_id="task_001", page=1, page_size=20)
```

## 注意事项

1. **数据迁移**: 在生产环境执行迁移前，请先备份数据库
2. **兼容性**: 确保所有使用旧存储接口的代码都已更新
3. **性能**: 大量数据迁移时，建议分批进行
4. **监控**: 迁移过程中需要监控数据库性能和存储空间

## 后续计划

1. **API接口**: 为统一存储系统提供RESTful API接口
2. **数据统计**: 基于统一表结构的数据统计和分析功能
3. **缓存优化**: 添加Redis缓存层，提高查询性能
4. **数据导出**: 支持多种格式的数据导出功能 