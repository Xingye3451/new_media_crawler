-- ----------------------------
-- 代理管理相关表结构
-- ----------------------------

-- ----------------------------
-- Table structure for proxy_pool
-- ----------------------------
DROP TABLE IF EXISTS `proxy_pool`;
CREATE TABLE `proxy_pool` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `proxy_type` varchar(16) NOT NULL COMMENT '代理类型: http, https, socks5',
    `ip` varchar(64) NOT NULL COMMENT '代理IP地址',
    `port` int NOT NULL COMMENT '代理端口',
    `username` varchar(64) DEFAULT NULL COMMENT '代理用户名',
    `password` varchar(128) DEFAULT NULL COMMENT '代理密码',
    `country` varchar(32) DEFAULT NULL COMMENT '代理所在国家',
    `region` varchar(64) DEFAULT NULL COMMENT '代理所在地区',
    `city` varchar(64) DEFAULT NULL COMMENT '代理所在城市',
    `isp` varchar(64) DEFAULT NULL COMMENT '网络服务商',
    `speed` int DEFAULT NULL COMMENT '代理速度(ms)',
    `anonymity` varchar(16) DEFAULT NULL COMMENT '匿名度: transparent, anonymous, elite',
    `uptime` decimal(5,2) DEFAULT NULL COMMENT '在线率(%)',
    `last_check_time` bigint DEFAULT NULL COMMENT '最后检测时间戳',
    `last_check_result` tinyint(1) DEFAULT 1 COMMENT '最后检测结果: 1-可用, 0-不可用',
    `fail_count` int DEFAULT 0 COMMENT '连续失败次数',
    `success_count` int DEFAULT 0 COMMENT '连续成功次数',
    `total_requests` int DEFAULT 0 COMMENT '总请求次数',
    `total_success` int DEFAULT 0 COMMENT '总成功次数',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
    `priority` int DEFAULT 0 COMMENT '优先级: 数字越大优先级越高',
    `tags` varchar(255) DEFAULT NULL COMMENT '标签，逗号分隔',
    `description` varchar(500) DEFAULT NULL COMMENT '代理描述',
    `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_proxy_ip_port` (`ip`, `port`),
    KEY `idx_proxy_type` (`proxy_type`),
    KEY `idx_proxy_status` (`status`),
    KEY `idx_proxy_last_check` (`last_check_time`),
    KEY `idx_proxy_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代理池';

-- ----------------------------
-- Table structure for proxy_strategy
-- ----------------------------
DROP TABLE IF EXISTS `proxy_strategy`;
CREATE TABLE `proxy_strategy` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `strategy_name` varchar(64) NOT NULL COMMENT '策略名称',
    `strategy_type` varchar(32) NOT NULL COMMENT '策略类型: round_robin, random, weighted, failover, geo_based',
    `description` varchar(500) DEFAULT NULL COMMENT '策略描述',
    `config` json DEFAULT NULL COMMENT '策略配置JSON',
    `is_default` tinyint(1) DEFAULT 0 COMMENT '是否默认策略: 1-是, 0-否',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
    `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_strategy_name` (`strategy_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代理使用策略';

-- ----------------------------
-- Table structure for proxy_strategy_rule
-- ----------------------------
DROP TABLE IF EXISTS `proxy_strategy_rule`;
CREATE TABLE `proxy_strategy_rule` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `strategy_id` int NOT NULL COMMENT '策略ID',
    `rule_name` varchar(64) NOT NULL COMMENT '规则名称',
    `rule_type` varchar(32) NOT NULL COMMENT '规则类型: filter, weight, geo, time',
    `rule_condition` json NOT NULL COMMENT '规则条件JSON',
    `rule_action` json NOT NULL COMMENT '规则动作JSON',
    `priority` int DEFAULT 0 COMMENT '规则优先级',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
    `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    KEY `idx_strategy_id` (`strategy_id`),
    KEY `idx_rule_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代理策略规则';

-- ----------------------------
-- Table structure for proxy_usage_log
-- ----------------------------
DROP TABLE IF EXISTS `proxy_usage_log`;
CREATE TABLE `proxy_usage_log` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `proxy_id` int NOT NULL COMMENT '代理ID',
    `strategy_id` int DEFAULT NULL COMMENT '使用的策略ID',
    `platform` varchar(16) DEFAULT NULL COMMENT '使用的平台',
    `request_url` varchar(512) DEFAULT NULL COMMENT '请求URL',
    `request_method` varchar(8) DEFAULT NULL COMMENT '请求方法',
    `response_status` int DEFAULT NULL COMMENT '响应状态码',
    `response_time` int DEFAULT NULL COMMENT '响应时间(ms)',
    `success` tinyint(1) DEFAULT 1 COMMENT '是否成功: 1-成功, 0-失败',
    `error_message` varchar(500) DEFAULT NULL COMMENT '错误信息',
    `user_agent` varchar(255) DEFAULT NULL COMMENT 'User-Agent',
    `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
    PRIMARY KEY (`id`),
    KEY `idx_proxy_id` (`proxy_id`),
    KEY `idx_strategy_id` (`strategy_id`),
    KEY `idx_platform` (`platform`),
    KEY `idx_add_ts` (`add_ts`),
    KEY `idx_success` (`success`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代理使用日志';

-- ----------------------------
-- Table structure for proxy_check_log
-- ----------------------------
DROP TABLE IF EXISTS `proxy_check_log`;
CREATE TABLE `proxy_check_log` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `proxy_id` int NOT NULL COMMENT '代理ID',
    `check_type` varchar(16) NOT NULL COMMENT '检测类型: health, speed, anonymity',
    `check_url` varchar(255) DEFAULT NULL COMMENT '检测URL',
    `response_time` int DEFAULT NULL COMMENT '响应时间(ms)',
    `success` tinyint(1) DEFAULT 1 COMMENT '是否成功: 1-成功, 0-失败',
    `error_message` varchar(500) DEFAULT NULL COMMENT '错误信息',
    `check_result` json DEFAULT NULL COMMENT '检测结果JSON',
    `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
    PRIMARY KEY (`id`),
    KEY `idx_proxy_id` (`proxy_id`),
    KEY `idx_check_type` (`check_type`),
    KEY `idx_add_ts` (`add_ts`),
    KEY `idx_success` (`success`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代理检测日志';

-- ----------------------------
-- 插入默认策略数据
-- ----------------------------
INSERT INTO `proxy_strategy` (`strategy_name`, `strategy_type`, `description`, `config`, `is_default`, `status`, `add_ts`, `last_modify_ts`) VALUES
('轮询策略', 'round_robin', '按顺序轮询使用代理', '{"max_fail_count": 3, "retry_interval": 300}', 1, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000),
('随机策略', 'random', '随机选择代理', '{"max_fail_count": 3, "retry_interval": 300}', 0, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000),
('权重策略', 'weighted', '根据代理权重选择', '{"weight_field": "priority", "max_fail_count": 3}', 0, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000),
('故障转移策略', 'failover', '优先使用高可用代理，失败时自动切换', '{"priority_order": ["elite", "anonymous", "transparent"], "max_fail_count": 2}', 0, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000),
('地理位置策略', 'geo_based', '根据目标网站地理位置选择代理', '{"geo_mapping": {"xhs": ["CN"], "dy": ["CN"], "ks": ["CN"]}}', 0, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000),
('智能策略', 'smart', '综合速度、可用性、地理位置等因素智能选择', '{"factors": ["speed", "uptime", "fail_count"], "weights": [0.4, 0.4, 0.2]}', 0, 1, UNIX_TIMESTAMP()*1000, UNIX_TIMESTAMP()*1000); 