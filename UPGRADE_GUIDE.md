# MediaCrawler 数据库升级指南

## 概述

本次升级为 MediaCrawler 项目添加了完整的任务管理功能，包括：

1. **任务管理表结构扩展** - 支持任务收藏、置顶、删除等功能
2. **视频数据表结构扩展** - 支持视频收藏、MinIO存储、任务关联等功能
3. **任务日志记录** - 详细记录任务执行过程
4. **单平台爬取数据存储** - 爬取的数据直接存储到数据库

## 升级步骤

### 1. 备份数据库（推荐）

在升级前，建议先备份现有数据库：

```bash
# 备份数据库
mysqldump -h localhost -u root -p mediacrawler > backup_mediacrawler_$(date +%Y%m%d_%H%M%S).sql
```

### 2. 执行数据库升级

#### 方法一：使用升级脚本（推荐）

```bash
# 运行升级脚本
python upgrade_database.py
```

#### 方法二：手动执行SQL

```bash
# 连接到MySQL并执行升级SQL
mysql -h localhost -u root -p mediacrawler < database_upgrade.sql
```

### 3. 验证升级结果

升级完成后，可以检查以下表结构是否正确：

```sql
-- 检查crawler_tasks表的新字段
DESCRIBE crawler_tasks;

-- 检查douyin_aweme表的新字段
DESCRIBE douyin_aweme;

-- 检查任务统计视图
SELECT * FROM task_statistics;

-- 检查视频统计视图
SELECT * FROM video_statistics;
```

## 新增功能说明

### 1. 任务管理功能

#### crawler_tasks 表新增字段：
- `user_id` - 用户ID
- `params` - 任务参数JSON
- `priority` - 优先级
- `is_favorite` - 是否收藏
- `deleted` - 是否删除
- `is_pinned` - 是否置顶
- `ip_address` - IP地址
- `user_security_id` - 用户安全ID
- `user_signature` - 用户签名

#### crawler_task_logs 表：
- 记录任务执行过程中的详细日志
- 支持不同日志级别（DEBUG, INFO, WARN, ERROR）
- 记录任务进度和步骤信息

### 2. 视频数据功能

#### douyin_aweme 表新增字段：
- `video_play_url` - 视频播放地址
- `video_share_url` - 视频分享地址
- `is_favorite` - 是否收藏
- `minio_url` - MinIO存储地址
- `task_id` - 关联任务ID

#### 其他平台表也添加了类似字段：
- `xhs_note` - 小红书笔记表
- `kuaishou_video` - 快手表
- `bilibili_video` - B站表
- `weibo_note` - 微博表
- `tieba_note` - 贴吧表
- `zhihu_content` - 知乎表

### 3. 统计视图

#### task_statistics 视图：
- 按平台统计任务数量
- 统计任务状态分布
- 计算平均进度和总结果数

#### video_statistics 视图：
- 按平台统计视频数量
- 统计收藏视频数量
- 统计任务关联视频数量

## API 功能增强

### 1. 单平台爬取增强

现在单平台爬取任务会：

1. **创建任务记录** - 在 `crawler_tasks` 表中创建任务记录
2. **记录执行日志** - 在 `crawler_task_logs` 表中记录详细日志
3. **存储视频数据** - 将爬取的视频数据存储到对应平台的数据表
4. **存储评论数据** - 将爬取的评论数据存储到对应平台的评论表
5. **更新任务进度** - 实时更新任务执行进度
6. **关联任务ID** - 视频数据与任务ID关联

### 2. 任务管理API

新增的任务管理API包括：

- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{task_id}` - 获取任务详情
- `POST /api/tasks/{task_id}/favorite` - 收藏任务
- `POST /api/tasks/{task_id}/pin` - 置顶任务
- `DELETE /api/tasks/{task_id}` - 删除任务
- `GET /api/tasks/{task_id}/logs` - 获取任务日志

### 3. 视频管理API

新增的视频管理API包括：

- `GET /api/videos` - 获取视频列表
- `GET /api/videos/{video_id}` - 获取视频详情
- `POST /api/videos/{video_id}/favorite` - 收藏视频
- `POST /api/videos/{video_id}/download` - 下载视频
- `POST /api/videos/{video_id}/save-to-minio` - 保存到MinIO

## 使用示例

### 1. 启动单平台爬取任务

```bash
curl -X POST "http://localhost:8000/api/v1/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "dy",
    "keywords": "测试关键词",
    "max_notes_count": 10,
    "get_comments": true,
    "save_data_option": "db"
  }'
```

### 2. 查看任务列表

```bash
curl "http://localhost:8000/api/tasks"
```

### 3. 查看任务详情

```bash
curl "http://localhost:8000/api/tasks/{task_id}"
```

### 4. 查看任务日志

```bash
curl "http://localhost:8000/api/tasks/{task_id}/logs"
```

### 5. 收藏任务

```bash
curl -X POST "http://localhost:8000/api/tasks/{task_id}/favorite"
```

## 故障排除

### 1. 升级失败

如果升级过程中出现错误：

1. **检查数据库连接** - 确保数据库服务正常运行
2. **检查权限** - 确保数据库用户有足够权限
3. **查看错误日志** - 检查具体的错误信息
4. **回滚操作** - 如果有备份，可以恢复备份

### 2. 数据不完整

如果升级后发现数据不完整：

1. **检查SQL执行** - 确认所有SQL语句都执行成功
2. **检查表结构** - 使用 `DESCRIBE` 命令检查表结构
3. **重新执行升级** - 可以重新运行升级脚本

### 3. API功能异常

如果API功能异常：

1. **检查数据库连接** - 确保API能正常连接数据库
2. **检查表结构** - 确认相关表结构正确
3. **查看API日志** - 检查API服务的错误日志
4. **重启服务** - 重启API服务

## 注意事项

1. **备份重要** - 升级前务必备份数据库
2. **测试环境** - 建议先在测试环境验证升级
3. **数据兼容** - 升级后现有数据仍然可用
4. **性能影响** - 新增字段和索引可能影响查询性能
5. **存储空间** - 新增字段会增加存储空间需求

## 联系支持

如果在升级过程中遇到问题，请：

1. 查看项目日志文件
2. 检查数据库错误日志
3. 提供详细的错误信息
4. 联系技术支持团队

---

**升级完成后，您就可以使用完整的任务管理功能了！** 🎉 