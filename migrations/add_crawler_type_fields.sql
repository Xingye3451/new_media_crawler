-- Active: 1745808356165@@192.168.31.231@3306@mediacrawler
-- 添加爬取类型和创作者关联字段到爬取任务表
-- 执行时间: 2025-07-31

-- 为crawler_tasks表添加新字段
ALTER TABLE `crawler_tasks` 
ADD COLUMN `crawler_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'search' COMMENT '爬取类型：search(关键词搜索)、detail(指定内容)、creator(创作者主页)' AFTER `task_type`,
ADD COLUMN `creator_ref_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '创作者引用ID（当crawler_type为creator时，关联unified_creator表）' AFTER `crawler_type`;

-- 添加索引
ALTER TABLE `crawler_tasks` 
ADD INDEX `idx_crawler_tasks_crawler_type` (`crawler_type`),
ADD INDEX `idx_crawler_tasks_creator_ref_id` (`creator_ref_id`);

-- 更新现有数据
UPDATE `crawler_tasks` SET `crawler_type` = 'search' WHERE `crawler_type` IS NULL;

-- 验证数据
SELECT 
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN crawler_type = 'search' THEN 1 END) as search_count,
    COUNT(CASE WHEN crawler_type = 'detail' THEN 1 END) as detail_count,
    COUNT(CASE WHEN crawler_type = 'creator' THEN 1 END) as creator_count,
    COUNT(CASE WHEN creator_ref_id IS NOT NULL THEN 1 END) as creator_ref_count
FROM `crawler_tasks`; 