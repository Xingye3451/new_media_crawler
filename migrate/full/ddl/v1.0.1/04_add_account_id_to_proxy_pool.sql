-- 为代理池表添加代理账号关联字段
-- 版本: v1.0.1
-- 描述: 添加account_id字段，关联代理账号

-- 添加代理账号关联字段
ALTER TABLE `proxy_pool` 
ADD COLUMN `account_id` varchar(64) DEFAULT NULL COMMENT '关联的代理账号ID' AFTER `provider`;

-- 添加索引
ALTER TABLE `proxy_pool` 
ADD INDEX `idx_account_id` (`account_id`);

-- 更新现有代理的account_id为默认青果账号
UPDATE `proxy_pool` 
SET `account_id` = 'qingguo_default' 
WHERE `provider` = 'qingguo' AND `account_id` IS NULL;

-- 添加外键约束（可选，如果数据库支持）
-- ALTER TABLE `proxy_pool` 
-- ADD CONSTRAINT `fk_proxy_pool_account_id` 
-- FOREIGN KEY (`account_id`) REFERENCES `proxy_accounts` (`account_id`) 
-- ON DELETE SET NULL ON UPDATE CASCADE;
