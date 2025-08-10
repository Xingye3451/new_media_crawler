-- 为代理池表添加task_id和proxy_ip字段
-- 版本: v1.0.2
-- 描述: 添加青果代理的task_id和真实出口IP字段

-- 添加task_id字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `task_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '青果代理的task_id';

-- 添加proxy_ip字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `proxy_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '真实出口IP地址';

-- 添加索引
ALTER TABLE `proxy_pool` 
ADD INDEX `idx_task_id` (`task_id`),
ADD INDEX `idx_proxy_ip` (`proxy_ip`);
