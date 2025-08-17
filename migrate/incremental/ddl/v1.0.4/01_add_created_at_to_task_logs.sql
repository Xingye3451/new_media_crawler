-- =============================================
-- MediaCrawler 增量迁移脚本
-- Version: v1.0.4
-- Description: 为crawler_task_logs表添加created_at字段
-- Execution Order: 01
-- 
-- 变更内容：
--   ✅ 为crawler_task_logs表添加created_at字段
--   ✅ 添加created_at索引
--   ✅ 保持与task_management_service.py的兼容性
-- =============================================

-- Set character set
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 为crawler_task_logs表添加created_at字段
-- =============================================

-- 添加created_at字段（如果不存在会报错，但会被迁移工具忽略）
ALTER TABLE `crawler_task_logs` 
ADD COLUMN `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created timestamp' AFTER `add_ts`;

-- 添加created_at索引（如果不存在会报错，但会被迁移工具忽略）
ALTER TABLE `crawler_task_logs` 
ADD KEY `idx_created_at` (`created_at`);

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 输出迁移结果
SELECT 'Migration v1.0.4 completed successfully' as result;
