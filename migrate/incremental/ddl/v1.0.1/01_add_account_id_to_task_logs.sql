-- =============================================
-- MediaCrawler 增量迁移脚本
-- Version: v1.0.1
-- Description: 为crawler_task_logs表添加account_id字段
-- Execution Order: 01
-- 
-- 变更内容：
--   ✅ 为crawler_task_logs表添加account_id字段
--   ✅ 添加相关索引
-- =============================================

-- Set character set
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 为crawler_task_logs表添加account_id字段
-- =============================================

-- 添加account_id字段（如果不存在会报错，但会被迁移工具忽略）
ALTER TABLE `crawler_task_logs` 
ADD COLUMN `account_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Account ID' AFTER `platform`;

-- 添加account_id索引（如果不存在会报错，但会被迁移工具忽略）
ALTER TABLE `crawler_task_logs` 
ADD KEY `idx_account_id` (`account_id`);

-- 添加复合索引（如果不存在会报错，但会被迁移工具忽略）
ALTER TABLE `crawler_task_logs` 
ADD KEY `idx_account_id_log_level` (`account_id`,`log_level`);

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 输出迁移结果
SELECT 'Migration v1.0.1 completed successfully' as result;
