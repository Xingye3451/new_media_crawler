-- 代理池表重新设计迁移（最终版本）
-- 添加代理与平台解耦后的新字段

-- 注意：这个版本使用传统的ALTER TABLE语句
-- 如果字段已存在，执行时会报错，但不会影响数据库结构

-- 添加启用状态字段
-- 如果字段已存在，会报错但可以忽略
ALTER TABLE `proxy_pool` 
ADD COLUMN `enabled` tinyint(1) DEFAULT 1 COMMENT '是否启用(1:启用,0:禁用)';

-- 添加区域信息字段
-- 如果字段已存在，会报错但可以忽略
ALTER TABLE `proxy_pool` 
ADD COLUMN `area` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理区域信息';

-- 添加描述信息字段
-- 如果字段已存在，会报错但可以忽略
ALTER TABLE `proxy_pool` 
ADD COLUMN `description` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理描述信息';

-- 添加speed字段
-- 如果字段已存在，会报错但可以忽略
ALTER TABLE `proxy_pool` 
ADD COLUMN `speed` int(11) DEFAULT NULL COMMENT '代理速度(ms)';

-- 添加索引
-- 如果索引已存在，会报错但可以忽略
ALTER TABLE `proxy_pool` 
ADD INDEX `idx_enabled` (`enabled`);

ALTER TABLE `proxy_pool` 
ADD INDEX `idx_area` (`area`);

-- 更新现有数据
-- 将现有的is_active字段值复制到enabled字段
UPDATE `proxy_pool` SET `enabled` = `is_active` WHERE `enabled` IS NULL;

-- 为现有代理添加默认区域信息（如果为空）
UPDATE `proxy_pool` SET `area` = '未知区域' WHERE `area` IS NULL AND `provider` = 'qingguo';

-- 为现有代理添加默认描述信息（如果为空）
UPDATE `proxy_pool` SET `description` = CONCAT('青果代理 - ', COALESCE(`area`, '未知区域')) 
WHERE `description` IS NULL AND `provider` = 'qingguo';

-- 更新表注释
ALTER TABLE `proxy_pool` 
COMMENT = '代理池表 - 重新设计版本，支持代理与平台解耦';
