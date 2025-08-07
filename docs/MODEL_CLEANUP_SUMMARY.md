# Model目录清理总结

## 🎯 清理目标

根据您的要求，项目已经统一使用三张核心表：
- `unified_content` - 统一内容表
- `unified_creator` - 统一创作者表  
- `unified_comment` - 统一评论表

因此需要完全摒弃 `model/` 目录中的平台特定模型，并修改相关代码。

## 📋 清理内容

### 1. **删除的目录**
- `model/` - 完全删除，包含以下文件：
  - `video_metadata.py` - 旧的视频元数据模型
  - `m_xiaohongshu.py` - 小红书模型
  - `m_douyin.py` - 抖音模型
  - `m_kuaishou.py` - 快手模型
  - `m_weibo.py` - 微博模型
  - `m_zhihu.py` - 知乎模型
  - `m_baidu_tieba.py` - 贴吧模型
  - `__init__.py` - 初始化文件

### 2. **修改的文件**

#### **小红书相关**
- `media_platform/xhs/help.py` - 内联 `NoteUrlInfo` 模型
- `media_platform/xhs/core.py` - 内联 `NoteUrlInfo` 模型

#### **知乎相关**
- `media_platform/zhihu/help.py` - 内联 `ZhihuContent`, `ZhihuComment`, `ZhihuCreator` 模型
- `media_platform/zhihu/client.py` - 内联 `ZhihuContent`, `ZhihuComment`, `ZhihuCreator` 模型
- `media_platform/zhihu/core.py` - 内联 `ZhihuContent`, `ZhihuCreator` 模型
- `store/zhihu/__init__.py` - 内联 `ZhihuContent`, `ZhihuComment`, `ZhihuCreator` 模型

#### **贴吧相关**
- `media_platform/tieba/help.py` - 内联 `TiebaNote`, `TiebaComment`, `TiebaCreator` 模型
- `media_platform/tieba/client.py` - 内联 `TiebaNote`, `TiebaComment`, `TiebaCreator` 模型
- `media_platform/tieba/core.py` - 内联 `TiebaNote`, `TiebaCreator` 模型
- `store/tieba/__init__.py` - 内联 `TiebaNote`, `TiebaComment`, `TiebaCreator` 模型

#### **视频存储相关**
- `video_storage_manager.py` - 移除 `VideoMetadata` 依赖，注释相关代码

#### **模型目录**
- `models/__init__.py` - 重新创建，只导入核心模型

## ✅ 统一数据库表结构

### **unified_content 表**
```sql
- id (bigint, 主键)
- content_id (varchar(100), 内容ID)
- platform (varchar(20), 平台名称)
- content_type (varchar(50), 内容类型)
- task_id (varchar(36), 任务ID)
- source_keyword (varchar(200), 来源关键词)
- title (varchar(500), 标题)
- description (text, 描述)
- content (longtext, 内容)
- create_time (bigint, 创建时间)
- publish_time (bigint, 发布时间)
- update_time (bigint, 更新时间)
- author_id (varchar(100), 作者ID)
- author_name (varchar(100), 作者名称)
- author_nickname (varchar(100), 作者昵称)
- author_avatar (text, 作者头像)
- author_signature (text, 作者签名)
- author_unique_id (varchar(100), 作者唯一ID)
- author_sec_uid (varchar(100), 作者sec_uid)
- author_short_id (varchar(100), 作者短ID)
- like_count (int, 点赞数)
- comment_count (int, 评论数)
- share_count (int, 分享数)
- collect_count (int, 收藏数)
- view_count (int, 播放数)
- cover_url (text, 封面URL)
- video_url (text, 视频URL)
- video_download_url (text, 视频下载URL)
- video_play_url (text, 视频播放URL)
- video_share_url (text, 视频分享URL)
- image_urls (text, 图片URL列表)
- audio_url (text, 音频URL)
- file_urls (text, 文件URL列表)
- ip_location (varchar(100), IP位置)
- location (varchar(200), 位置信息)
- tags (text, 标签)
- categories (text, 分类)
- topics (text, 话题)
- is_favorite (tinyint, 是否收藏)
- is_deleted (tinyint, 是否删除)
- is_private (tinyint, 是否私密)
- is_original (tinyint, 是否原创)
- minio_url (text, MinIO URL)
- local_path (varchar(500), 本地路径)
- file_size (bigint, 文件大小)
- storage_type (varchar(20), 存储类型)
- metadata (text, 元数据)
- raw_data (longtext, 原始数据)
- extra_info (text, 额外信息)
- add_ts (bigint, 添加时间戳)
- last_modify_ts (bigint, 最后修改时间戳)
```

### **unified_creator 表**
```sql
- id (bigint, 主键)
- creator_id (varchar(100), 创作者ID)
- platform (varchar(20), 平台名称)
- creator_type (varchar(50), 创作者类型)
- task_id (varchar(36), 任务ID)
- source_keyword (varchar(200), 来源关键词)
- name (varchar(100), 名称)
- nickname (varchar(100), 昵称)
- avatar (text, 头像)
- signature (text, 签名)
- description (text, 描述)
- unique_id (varchar(100), 唯一ID)
- sec_uid (varchar(100), sec_uid)
- short_id (varchar(100), 短ID)
- gender (varchar(10), 性别)
- ip_location (varchar(100), IP位置)
- location (varchar(200), 位置)
- follow_count (int, 关注数)
- fans_count (int, 粉丝数)
- like_count (int, 点赞数)
- content_count (int, 内容数)
- interaction_count (int, 互动数)
- verified (tinyint, 是否认证)
- verified_type (varchar(50), 认证类型)
- level (int, 等级)
- tags (text, 标签)
- categories (text, 分类)
- profile_url (text, 主页URL)
- is_deleted (tinyint, 是否删除)
- is_private (tinyint, 是否私密)
- is_blocked (tinyint, 是否被屏蔽)
- metadata (text, 元数据)
- raw_data (longtext, 原始数据)
- extra_info (text, 额外信息)
- add_ts (bigint, 添加时间戳)
- last_modify_ts (bigint, 最后修改时间戳)
- last_refresh_ts (bigint, 最后刷新时间戳)
```

### **unified_comment 表**
```sql
- id (bigint, 主键)
- comment_id (varchar(100), 评论ID)
- content_id (varchar(100), 内容ID)
- platform (varchar(20), 平台名称)
- parent_id (varchar(100), 父评论ID)
- reply_to_id (varchar(100), 回复ID)
- content (text, 评论内容)
- text (text, 文本内容)
- html_content (text, HTML内容)
- author_id (varchar(100), 作者ID)
- author_name (varchar(100), 作者名称)
- author_nickname (varchar(100), 作者昵称)
- author_avatar (text, 作者头像)
- like_count (int, 点赞数)
- reply_count (int, 回复数)
- share_count (int, 分享数)
- create_time (bigint, 创建时间)
- publish_time (bigint, 发布时间)
- is_deleted (tinyint, 是否删除)
- is_hidden (tinyint, 是否隐藏)
- is_top (tinyint, 是否置顶)
- metadata (text, 元数据)
- raw_data (longtext, 原始数据)
- add_ts (bigint, 添加时间戳)
- last_modify_ts (bigint, 最后修改时间戳)
```

## 🎯 清理优势

### 1. **数据统一**
- 所有平台数据统一存储在三张表中
- 便于数据分析和跨平台查询
- 减少数据冗余和复杂性

### 2. **代码简化**
- 移除平台特定的模型定义
- 减少代码重复和维护成本
- 统一的数据访问接口

### 3. **扩展性增强**
- 新增平台只需适配统一表结构
- 无需为每个平台创建独立模型
- 便于功能扩展和优化

### 4. **维护简单**
- 单一数据源，避免数据不一致
- 统一的数据库操作逻辑
- 便于监控和调试

## 💡 后续建议

### 1. **数据迁移**
- 如果有历史数据需要迁移到统一表结构
- 确保数据完整性和一致性

### 2. **API适配**
- 确保所有API接口使用统一的数据模型
- 更新前端代码以适配新的数据结构

### 3. **性能优化**
- 为统一表添加合适的索引
- 优化查询性能

### 4. **监控告警**
- 添加数据质量监控
- 设置异常数据告警

---

**总结**：成功清理了 `model/` 目录，移除了所有平台特定模型，统一使用三张核心表。这大大简化了项目结构，提高了数据一致性和可维护性。
