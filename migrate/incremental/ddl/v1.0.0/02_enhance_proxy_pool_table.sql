-- 完善proxy_pool表结构，添加青果代理所需的字段

-- 添加认证信息字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `username` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理用户名' AFTER `proxy_type`,
ADD COLUMN `password` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理密码' AFTER `username`;

-- 添加过期时间字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `expire_ts` bigint(20) DEFAULT NULL COMMENT '代理过期时间戳' AFTER `password`;

-- 添加关联字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `platform` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联平台(dy,xhs,ks,bili)' AFTER `expire_ts`,
ADD COLUMN `account_id` int(11) DEFAULT NULL COMMENT '关联账号ID' AFTER `platform`,
ADD COLUMN `provider` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'qingguo' COMMENT '代理提供商(qingguo,kuaidaili,jisuhttp)' AFTER `account_id`;

-- 添加使用统计字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `usage_count` int(11) DEFAULT 0 COMMENT '使用次数' AFTER `provider`,
ADD COLUMN `success_count` int(11) DEFAULT 0 COMMENT '成功次数' AFTER `usage_count`,
ADD COLUMN `fail_count` int(11) DEFAULT 0 COMMENT '失败次数' AFTER `success_count`,
ADD COLUMN `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间' AFTER `fail_count`;

-- 添加状态字段（替换is_active）
ALTER TABLE `proxy_pool` 
ADD COLUMN `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active' COMMENT '代理状态(active,expired,failed,rotating)' AFTER `last_used_at`;

-- 添加索引
ALTER TABLE `proxy_pool` 
ADD INDEX `idx_platform` (`platform`),
ADD INDEX `idx_account_id` (`account_id`),
ADD INDEX `idx_provider` (`provider`),
ADD INDEX `idx_status` (`status`),
ADD INDEX `idx_expire_ts` (`expire_ts`),
ADD INDEX `idx_last_used` (`last_used_at`);

-- 更新现有数据
UPDATE `proxy_pool` SET 
    `provider` = 'unknown',
    `status` = CASE WHEN `is_active` = 1 THEN 'active' ELSE 'inactive' END;

-- 添加注释
ALTER TABLE `proxy_pool` 
MODIFY COLUMN `proxy_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '代理唯一标识',
MODIFY COLUMN `ip` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '代理IP地址',
MODIFY COLUMN `port` int(11) NOT NULL COMMENT '代理端口',
MODIFY COLUMN `proxy_type` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'http' COMMENT '代理类型(http,https,socks5)',
MODIFY COLUMN `country` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理所在国家/地区',
MODIFY COLUMN `speed` int(11) DEFAULT '0' COMMENT '代理速度(ms)',
MODIFY COLUMN `anonymity` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '匿名级别(transparent,anonymous,elite)',
MODIFY COLUMN `success_rate` float DEFAULT '0' COMMENT '成功率(0-100)',
MODIFY COLUMN `last_check` timestamp NULL DEFAULT NULL COMMENT '最后检查时间',
MODIFY COLUMN `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活(兼容字段)';
