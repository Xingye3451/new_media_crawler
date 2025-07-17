-- MediaCrawler 数据库升级脚本
-- 用于更新现有表结构以支持任务管理功能

-- 1. 更新 crawler_tasks 表，添加新字段
ALTER TABLE crawler_tasks 
ADD COLUMN user_id VARCHAR(50) DEFAULT NULL COMMENT "用户ID" AFTER error_message,
ADD COLUMN params TEXT COMMENT "任务参数JSON" AFTER user_id,
ADD COLUMN priority INT DEFAULT 0 COMMENT "优先级" AFTER params,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER priority,
ADD COLUMN deleted BOOLEAN DEFAULT FALSE COMMENT "是否删除" AFTER is_favorite,
ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE COMMENT "是否置顶" AFTER deleted,
ADD COLUMN ip_address VARCHAR(45) DEFAULT NULL COMMENT "IP地址" AFTER is_pinned,
ADD COLUMN user_security_id VARCHAR(100) DEFAULT NULL COMMENT "用户安全ID" AFTER ip_address,
ADD COLUMN user_signature VARCHAR(255) DEFAULT NULL COMMENT "用户签名" AFTER user_security_id;

-- 2. 为 crawler_tasks 表添加索引
ALTER TABLE crawler_tasks 
ADD INDEX idx_crawler_tasks_platform (platform),
ADD INDEX idx_crawler_tasks_status (status),
ADD INDEX idx_crawler_tasks_user_id (user_id),
ADD INDEX idx_crawler_tasks_created_at (created_at);

-- 3. 更新 crawler_task_logs 表索引名称
ALTER TABLE crawler_task_logs 
DROP INDEX idx_task_id,
DROP INDEX idx_platform,
DROP INDEX idx_account_id,
DROP INDEX idx_log_level;

ALTER TABLE crawler_task_logs 
ADD INDEX idx_crawler_task_logs_task_id (task_id),
ADD INDEX idx_crawler_task_logs_platform (platform),
ADD INDEX idx_crawler_task_logs_account_id (account_id),
ADD INDEX idx_crawler_task_logs_log_level (log_level),
ADD INDEX idx_crawler_task_logs_created_at (created_at);

-- 4. 更新 douyin_aweme 表，添加新字段
ALTER TABLE douyin_aweme 
ADD COLUMN video_play_url VARCHAR(1024) DEFAULT NULL COMMENT "视频播放地址" AFTER video_download_url,
ADD COLUMN video_share_url VARCHAR(1024) DEFAULT NULL COMMENT "视频分享地址" AFTER video_play_url,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER video_share_url,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite,
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER minio_url;

-- 5. 为 douyin_aweme 表添加新索引
ALTER TABLE douyin_aweme 
ADD INDEX idx_douyin_aweme_task_id (task_id),
ADD INDEX idx_douyin_aweme_is_favorite (is_favorite);

-- 6. 更新 xhs_note 表，添加任务关联字段（如果需要）
ALTER TABLE xhs_note 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER xsec_token,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

-- 7. 为 xhs_note 表添加新索引
ALTER TABLE xhs_note 
ADD INDEX idx_xhs_note_task_id (task_id),
ADD INDEX idx_xhs_note_is_favorite (is_favorite);

-- 8. 更新其他平台表，添加任务关联字段
-- 快手表
ALTER TABLE kuaishou_video 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER source_keyword,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

ALTER TABLE kuaishou_video 
ADD INDEX idx_kuaishou_video_task_id (task_id),
ADD INDEX idx_kuaishou_video_is_favorite (is_favorite);

-- B站表
ALTER TABLE bilibili_video 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER source_keyword,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

ALTER TABLE bilibili_video 
ADD INDEX idx_bilibili_video_task_id (task_id),
ADD INDEX idx_bilibili_video_is_favorite (is_favorite);

-- 微博表
ALTER TABLE weibo_note 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER source_keyword,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

ALTER TABLE weibo_note 
ADD INDEX idx_weibo_note_task_id (task_id),
ADD INDEX idx_weibo_note_is_favorite (is_favorite);

-- 贴吧表
ALTER TABLE tieba_note 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER source_keyword,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

ALTER TABLE tieba_note 
ADD INDEX idx_tieba_note_task_id (task_id),
ADD INDEX idx_tieba_note_is_favorite (is_favorite);

-- 知乎表
ALTER TABLE zhihu_content 
ADD COLUMN task_id VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID" AFTER source_keyword,
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE COMMENT "是否收藏" AFTER task_id,
ADD COLUMN minio_url VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址" AFTER is_favorite;

ALTER TABLE zhihu_content 
ADD INDEX idx_zhihu_content_task_id (task_id),
ADD INDEX idx_zhihu_content_is_favorite (is_favorite);

-- 9. 创建任务统计视图
CREATE OR REPLACE VIEW task_statistics AS
SELECT 
    platform,
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_tasks,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_tasks,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
    AVG(progress) as avg_progress,
    SUM(result_count) as total_results,
    MAX(created_at) as last_task_time
FROM crawler_tasks 
WHERE deleted = FALSE
GROUP BY platform;

-- 10. 创建视频统计视图
CREATE OR REPLACE VIEW video_statistics AS
SELECT 
    'douyin' as platform,
    COUNT(*) as total_videos,
    COUNT(CASE WHEN is_favorite = TRUE THEN 1 END) as favorite_videos,
    COUNT(CASE WHEN task_id IS NOT NULL THEN 1 END) as task_videos,
    MAX(add_ts) as last_video_time
FROM douyin_aweme
UNION ALL
SELECT 
    'xhs' as platform,
    COUNT(*) as total_videos,
    COUNT(CASE WHEN is_favorite = TRUE THEN 1 END) as favorite_videos,
    COUNT(CASE WHEN task_id IS NOT NULL THEN 1 END) as task_videos,
    MAX(add_ts) as last_video_time
FROM xhs_note
UNION ALL
SELECT 
    'kuaishou' as platform,
    COUNT(*) as total_videos,
    COUNT(CASE WHEN is_favorite = TRUE THEN 1 END) as favorite_videos,
    COUNT(CASE WHEN task_id IS NOT NULL THEN 1 END) as task_videos,
    MAX(add_ts) as last_video_time
FROM kuaishou_video
UNION ALL
SELECT 
    'bilibili' as platform,
    COUNT(*) as total_videos,
    COUNT(CASE WHEN is_favorite = TRUE THEN 1 END) as favorite_videos,
    COUNT(CASE WHEN task_id IS NOT NULL THEN 1 END) as task_videos,
    MAX(add_ts) as last_video_time
FROM bilibili_video;

-- 11. 插入默认任务记录（可选）
-- INSERT INTO crawler_tasks (id, platform, task_type, keywords, status, progress, created_at, updated_at)
-- VALUES 
-- ('demo-task-001', 'dy', 'single_platform', '测试关键词', 'completed', 1.0, NOW(), NOW()),
-- ('demo-task-002', 'xhs', 'single_platform', '测试关键词', 'completed', 1.0, NOW(), NOW());

-- 升级完成提示
SELECT 'Database upgrade completed successfully!' as status; 