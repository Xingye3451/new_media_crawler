-- 为login_tokens表添加proxy_id字段
-- 用于关联代理池中的代理记录

ALTER TABLE `login_tokens` 
ADD COLUMN `proxy_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理ID，关联proxy_pool表的id' 
AFTER `proxy_info`;

-- 添加索引以提高查询性能
ALTER TABLE `login_tokens` 
ADD INDEX `idx_proxy_id` (`proxy_id`);

-- 添加注释说明
ALTER TABLE `login_tokens` 
MODIFY COLUMN `proxy_info` text COLLATE utf8mb4_unicode_ci COMMENT '代理信息(JSON格式，包含完整的代理配置)';
