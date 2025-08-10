-- 修复代理池表中account_id字段类型
-- 版本: v1.0.1
-- 描述: 将account_id字段从int(11)改为varchar(64)

-- 修改account_id字段类型
ALTER TABLE `proxy_pool` 
MODIFY COLUMN `account_id` varchar(64) DEFAULT NULL COMMENT '关联的代理账号ID';

-- 更新现有数据，将数字ID转换为字符串
UPDATE `proxy_pool` 
SET `account_id` = 'qingguo_default' 
WHERE `account_id` IS NOT NULL AND `provider` = 'qingguo';
