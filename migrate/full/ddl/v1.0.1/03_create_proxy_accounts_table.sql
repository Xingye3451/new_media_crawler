-- 创建代理账号表
CREATE TABLE IF NOT EXISTS `proxy_accounts` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `account_id` varchar(64) NOT NULL COMMENT '账号唯一标识',
  `provider` varchar(32) NOT NULL COMMENT '代理提供商：qingguo, kuaidaili, jisuhttp',
  `provider_name` varchar(64) NOT NULL COMMENT '提供商中文名称',
  `api_key` varchar(128) NOT NULL COMMENT 'API密钥',
  `api_secret` varchar(128) DEFAULT NULL COMMENT 'API密钥（可选）',
  `username` varchar(64) DEFAULT NULL COMMENT '用户名（可选）',
  `password` varchar(128) DEFAULT NULL COMMENT '密码（可选）',
  `signature` varchar(128) DEFAULT NULL COMMENT '签名（可选）',
  `endpoint_url` varchar(255) DEFAULT NULL COMMENT 'API端点URL',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用：1启用，0禁用',
  `is_default` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否默认账号：1默认，0非默认',
  `max_pool_size` int(11) NOT NULL DEFAULT '10' COMMENT '最大代理池大小',
  `validate_ip` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否验证IP：1验证，0不验证',
  `description` text COMMENT '账号描述',
  `config_json` json DEFAULT NULL COMMENT '额外配置JSON',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `usage_count` int(11) NOT NULL DEFAULT '0' COMMENT '使用次数',
  `success_count` int(11) NOT NULL DEFAULT '0' COMMENT '成功次数',
  `fail_count` int(11) NOT NULL DEFAULT '0' COMMENT '失败次数',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_account_id` (`account_id`),
  KEY `idx_provider` (`provider`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_is_default` (`is_default`),
  KEY `idx_last_used` (`last_used_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='代理账号配置表';

-- 插入默认的青果代理账号
INSERT INTO `proxy_accounts` (
  `account_id`, 
  `provider`, 
  `provider_name`, 
  `api_key`, 
  `api_secret`, 
  `is_active`, 
  `is_default`, 
  `max_pool_size`, 
  `validate_ip`, 
  `description`
) VALUES (
  'qingguo_default',
  'qingguo',
  '青果代理',
  'EEFECFB3',
  'E169CFB91ACD',
  1,
  1,
  10,
  1,
  '默认青果代理账号'
) ON DUPLICATE KEY UPDATE
  `updated_at` = CURRENT_TIMESTAMP;

-- 创建代理账号使用日志表
CREATE TABLE IF NOT EXISTS `proxy_account_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `account_id` varchar(64) NOT NULL COMMENT '代理账号ID',
  `provider` varchar(32) NOT NULL COMMENT '代理提供商',
  `operation` varchar(32) NOT NULL COMMENT '操作类型：extract, release, test, sync',
  `proxy_id` varchar(64) DEFAULT NULL COMMENT '关联的代理ID',
  `ip` varchar(45) DEFAULT NULL COMMENT '代理IP地址',
  `port` int(11) DEFAULT NULL COMMENT '代理端口',
  `success` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否成功：1成功，0失败',
  `response_time` int(11) DEFAULT NULL COMMENT '响应时间（毫秒）',
  `error_message` text COMMENT '错误信息',
  `request_data` json DEFAULT NULL COMMENT '请求数据',
  `response_data` json DEFAULT NULL COMMENT '响应数据',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_provider` (`provider`),
  KEY `idx_operation` (`operation`),
  KEY `idx_success` (`success`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_proxy_id` (`proxy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='代理账号使用日志表';
