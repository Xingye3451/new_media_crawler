-- 添加 expires_at 字段到 login_tokens 表
-- 这个字段用于存储token的过期时间，与现有的 expire_time 字段并存
-- expire_time 是 bigint 类型的时间戳，expires_at 是 datetime 类型

ALTER TABLE `login_tokens` 
ADD COLUMN `expires_at` datetime NULL COMMENT 'Token过期时间(datetime格式)' AFTER `expire_time`;

-- 为 expires_at 字段添加索引
ALTER TABLE `login_tokens` 
ADD INDEX `idx_expires_at` (`expires_at`);

-- 添加复合索引
ALTER TABLE `login_tokens` 
ADD INDEX `idx_is_valid_expires_at` (`is_valid`, `expires_at`);
