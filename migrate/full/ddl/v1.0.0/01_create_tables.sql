-- =============================================
-- MediaCrawler 数据库完整迁移脚本
-- Version: v1.0.0 (整合版)
-- Description: 创建所有数据表，整合了从 v1.0.0 到 v1.0.3 的所有变更
-- Execution Order: 01
-- 
-- 包含内容：
--   ✅ 核心内容管理表 (unified_content, unified_creator, unified_comment)
--   ✅ 任务管理系统表 (crawler_tasks, crawler_task_logs, task_statistics)
--   ✅ 账号认证系统表 (social_accounts, login_tokens, login_sessions)
--   ✅ 代理管理系统表 (proxy_pool, proxy_accounts, proxy_account_logs)
--   ✅ 视频管理系统表 (video_download_tasks, video_files, video_statistics, video_storage_stats)
--   ✅ 平台配置表 (platforms)
--   ✅ 时间戳触发器 (tr_login_tokens_timestamps)
--   ✅ 初始数据 (默认代理账号)
-- =============================================

-- Set character set
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 1. 统一内容表 (核心表)
-- 功能：存储所有平台的内容数据，包括视频、图片、文章等
-- =============================================
DROP TABLE IF EXISTS `unified_content`;
CREATE TABLE `unified_content` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `content_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `content_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Content type',
  `task_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Task ID',
  `source_keyword` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Source keyword',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Title',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT 'Description',
  `content` longtext COLLATE utf8mb4_unicode_ci COMMENT 'Content',
  `create_time` bigint(20) DEFAULT NULL COMMENT 'Create timestamp',
  `publish_time` bigint(20) DEFAULT NULL COMMENT 'Publish timestamp',
  `update_time` bigint(20) DEFAULT NULL COMMENT 'Update timestamp',
  `author_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author ID',
  `author_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author name',
  `author_nickname` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author nickname',
  `author_avatar` text COLLATE utf8mb4_unicode_ci COMMENT 'Author avatar',
  `author_signature` text COLLATE utf8mb4_unicode_ci COMMENT 'Author signature',
  `author_unique_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author unique ID',
  `author_sec_uid` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author sec_uid',
  `author_short_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author short ID',
  `like_count` int(11) DEFAULT '0' COMMENT 'Like count',
  `comment_count` int(11) DEFAULT '0' COMMENT 'Comment count',
  `share_count` int(11) DEFAULT '0' COMMENT 'Share count',
  `collect_count` int(11) DEFAULT '0' COMMENT 'Collect count',
  `view_count` int(11) DEFAULT '0' COMMENT 'View count',
  `cover_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Cover URL',
  `video_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Video URL',
  `video_download_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Video download URL',
  `video_play_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Video play URL',
  `video_share_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Video share URL',
  `image_urls` text COLLATE utf8mb4_unicode_ci COMMENT 'Image URL list',
  `audio_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Audio URL',
  `file_urls` text COLLATE utf8mb4_unicode_ci COMMENT 'File URL list',
  `ip_location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP location',
  `location` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Location info',
  `tags` text COLLATE utf8mb4_unicode_ci COMMENT 'Tags',
  `categories` text COLLATE utf8mb4_unicode_ci COMMENT 'Categories',
  `topics` text COLLATE utf8mb4_unicode_ci COMMENT 'Topics',
  `is_favorite` tinyint(4) DEFAULT '0' COMMENT 'Is favorite',
  `is_deleted` tinyint(4) DEFAULT '0' COMMENT 'Is deleted',
  `is_private` tinyint(4) DEFAULT '0' COMMENT 'Is private',
  `is_original` tinyint(4) DEFAULT '0' COMMENT 'Is original',
  `minio_url` text COLLATE utf8mb4_unicode_ci COMMENT 'MinIO URL',
  `local_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Local path',
  `file_size` bigint(20) DEFAULT NULL COMMENT 'File size',
  `storage_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'url_only' COMMENT 'Storage type',
  `metadata` text COLLATE utf8mb4_unicode_ci COMMENT 'Metadata',
  `raw_data` longtext COLLATE utf8mb4_unicode_ci COMMENT 'Raw data',
  `extra_info` text COLLATE utf8mb4_unicode_ci COMMENT 'Extra info',
  `add_ts` bigint(20) DEFAULT NULL COMMENT 'Add timestamp',
  `last_modify_ts` bigint(20) DEFAULT NULL COMMENT 'Last modify timestamp',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_content_id` (`platform`,`content_id`),
  KEY `idx_unified_content_platform_content_id` (`platform`,`content_id`),
  KEY `idx_unified_content_task_id` (`task_id`),
  KEY `idx_unified_content_author_id` (`author_id`),
  KEY `idx_unified_content_create_time` (`create_time`),
  KEY `idx_unified_content_add_ts` (`add_ts`),
  KEY `idx_unified_content_publish_time` (`publish_time`),
  KEY `idx_unified_content_content_type` (`content_type`),
  KEY `idx_unified_content_platform_content_type` (`platform`,`content_type`),
  KEY `idx_unified_content_platform_publish_time` (`platform`,`publish_time`),
  KEY `idx_unified_content_author_publish_time` (`author_id`,`publish_time`),
  KEY `idx_unified_content_is_deleted` (`is_deleted`),
  KEY `idx_unified_content_storage_type` (`storage_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Unified content table';

-- =============================================
-- 2. 统一创作者表
-- 功能：存储所有平台的创作者/用户信息
-- =============================================
DROP TABLE IF EXISTS `unified_creator`;
CREATE TABLE `unified_creator` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `creator_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Creator ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `creator_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator type',
  `task_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Task ID',
  `source_keyword` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Source keyword',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator name',
  `nickname` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator nickname',
  `avatar` text COLLATE utf8mb4_unicode_ci COMMENT 'Creator avatar',
  `signature` text COLLATE utf8mb4_unicode_ci COMMENT 'Creator signature',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT 'Creator description',
  `unique_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator unique ID',
  `sec_uid` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator sec_uid',
  `short_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Creator short ID',
  `gender` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Gender',
  `ip_location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP location',
  `location` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Location info',
  `follow_count` int(11) DEFAULT '0' COMMENT 'Follow count',
  `fans_count` int(11) DEFAULT '0' COMMENT 'Fans count',
  `like_count` int(11) DEFAULT '0' COMMENT 'Like count',
  `content_count` int(11) DEFAULT '0' COMMENT 'Content count',
  `interaction_count` int(11) DEFAULT '0' COMMENT 'Interaction count',
  `verified` tinyint(4) DEFAULT '0' COMMENT 'Is verified',
  `verified_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Verified type',
  `level` int(11) DEFAULT '0' COMMENT 'Level',
  `tags` text COLLATE utf8mb4_unicode_ci COMMENT 'Tags',
  `categories` text COLLATE utf8mb4_unicode_ci COMMENT 'Categories',
  `profile_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Profile URL',
  `is_deleted` tinyint(4) DEFAULT '0' COMMENT 'Is deleted',
  `is_private` tinyint(4) DEFAULT '0' COMMENT 'Is private',
  `is_blocked` tinyint(4) DEFAULT '0' COMMENT 'Is blocked',
  `metadata` text COLLATE utf8mb4_unicode_ci COMMENT 'Metadata',
  `raw_data` longtext COLLATE utf8mb4_unicode_ci COMMENT 'Raw data',
  `extra_info` text COLLATE utf8mb4_unicode_ci COMMENT 'Extra info',
  `add_ts` bigint(20) DEFAULT NULL COMMENT 'Add timestamp',
  `last_modify_ts` bigint(20) DEFAULT NULL COMMENT 'Last modify timestamp',
  `last_refresh_ts` bigint(20) DEFAULT NULL COMMENT 'Last refresh timestamp',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_creator_id` (`platform`,`creator_id`),
  KEY `idx_unified_creator_platform_creator_id` (`platform`,`creator_id`),
  KEY `idx_unified_creator_task_id` (`task_id`),
  KEY `idx_unified_creator_name` (`name`),
  KEY `idx_unified_creator_fans_count` (`fans_count`),
  KEY `idx_unified_creator_add_ts` (`add_ts`),
  KEY `idx_unified_creator_platform_followers` (`platform`,`fans_count`),
  KEY `idx_unified_creator_platform_verified` (`platform`,`verified`),
  KEY `idx_unified_creator_verified` (`verified`),
  KEY `idx_unified_creator_level` (`level`),
  KEY `idx_unified_creator_is_deleted` (`is_deleted`),
  KEY `idx_unified_creator_is_private` (`is_private`),
  KEY `idx_unified_creator_is_blocked` (`is_blocked`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Unified creator table';

-- =============================================
-- 3. 统一评论表
-- 功能：存储所有平台的内容评论数据
-- =============================================
DROP TABLE IF EXISTS `unified_comment`;
CREATE TABLE `unified_comment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `comment_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Comment ID',
  `content_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `parent_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Parent comment ID',
  `reply_to_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Reply to comment ID',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT 'Comment content',
  `text` text COLLATE utf8mb4_unicode_ci COMMENT 'Plain text content',
  `html_content` text COLLATE utf8mb4_unicode_ci COMMENT 'HTML content',
  `author_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author ID',
  `author_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author name',
  `author_nickname` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Author nickname',
  `author_avatar` text COLLATE utf8mb4_unicode_ci COMMENT 'Author avatar',
  `like_count` int(11) DEFAULT '0' COMMENT 'Like count',
  `reply_count` int(11) DEFAULT '0' COMMENT 'Reply count',
  `share_count` int(11) DEFAULT '0' COMMENT 'Share count',
  `create_time` bigint(20) DEFAULT NULL COMMENT 'Create timestamp',
  `publish_time` bigint(20) DEFAULT NULL COMMENT 'Publish timestamp',
  `is_deleted` tinyint(4) DEFAULT '0' COMMENT 'Is deleted',
  `is_hidden` tinyint(4) DEFAULT '0' COMMENT 'Is hidden',
  `is_top` tinyint(4) DEFAULT '0' COMMENT 'Is top',
  `metadata` text COLLATE utf8mb4_unicode_ci COMMENT 'Metadata',
  `raw_data` longtext COLLATE utf8mb4_unicode_ci COMMENT 'Raw data',
  `add_ts` bigint(20) DEFAULT NULL COMMENT 'Add timestamp',
  `last_modify_ts` bigint(20) DEFAULT NULL COMMENT 'Last modify timestamp',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_comment_id` (`platform`,`comment_id`),
  KEY `idx_unified_comment_platform_comment_id` (`platform`,`comment_id`),
  KEY `idx_unified_comment_content_id` (`content_id`),
  KEY `idx_unified_comment_author_id` (`author_id`),
  KEY `idx_unified_comment_create_time` (`create_time`),
  KEY `idx_unified_comment_add_ts` (`add_ts`),
  KEY `idx_unified_comment_platform_content_id` (`platform`,`content_id`),
  KEY `idx_unified_comment_platform_publish_time` (`platform`,`publish_time`),
  KEY `idx_unified_comment_parent_id` (`parent_id`),
  KEY `idx_unified_comment_reply_to_id` (`reply_to_id`),
  KEY `idx_unified_comment_publish_time` (`publish_time`),
  KEY `idx_unified_comment_is_deleted` (`is_deleted`),
  KEY `idx_unified_comment_is_hidden` (`is_hidden`),
  KEY `idx_unified_comment_is_top` (`is_top`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Unified comment table';

-- =============================================
-- 4. 爬虫任务表
-- 功能：管理爬虫任务的创建、执行和状态跟踪
-- =============================================
DROP TABLE IF EXISTS `crawler_tasks`;
CREATE TABLE `crawler_tasks` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `crawler_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'search' COMMENT 'Crawler type: search(keyword search), detail(specified content), creator(creator profile)',
  `keywords` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `progress` float DEFAULT '0',
  `result_count` int(11) DEFAULT '0',
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `user_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User ID',
  `params` text COLLATE utf8mb4_unicode_ci COMMENT 'Task parameters JSON',
  `priority` int(11) DEFAULT '0' COMMENT 'Priority',
  `is_favorite` tinyint(1) DEFAULT '0' COMMENT 'Is favorite',
  `deleted` tinyint(1) DEFAULT '0' COMMENT 'Is deleted',
  `is_pinned` tinyint(1) DEFAULT '0' COMMENT 'Is pinned',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP address',
  `user_security_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User security ID',
  `user_signature` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User signature',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `started_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `creator_ref_ids` json DEFAULT NULL COMMENT 'Creator reference ID list (when crawler_type is creator, related to unified_creator table)',
  PRIMARY KEY (`id`),
  KEY `idx_crawler_tasks_platform` (`platform`),
  KEY `idx_crawler_tasks_status` (`status`),
  KEY `idx_crawler_tasks_user_id` (`user_id`),
  KEY `idx_crawler_tasks_created_at` (`created_at`),
  KEY `idx_crawler_tasks_crawler_type` (`crawler_type`),
  KEY `idx_crawler_tasks_platform_task_type` (`platform`,`task_type`),
  KEY `idx_crawler_tasks_platform_status` (`platform`,`status`),
  KEY `idx_crawler_tasks_start_time_status` (`started_at`,`status`),
  KEY `idx_crawler_tasks_priority` (`priority`),
  KEY `idx_crawler_tasks_deleted` (`deleted`),
  KEY `idx_crawler_tasks_is_favorite` (`is_favorite`),
  KEY `idx_crawler_tasks_is_pinned` (`is_pinned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Crawler tasks table';

-- =============================================
-- 5. 爬虫任务日志表
-- 功能：记录爬虫任务的执行日志和详细信息
-- =============================================
DROP TABLE IF EXISTS `crawler_task_logs`;
CREATE TABLE `crawler_task_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Task ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `account_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Account ID',
  `log_level` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Log level: DEBUG, INFO, WARNING, ERROR',
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Log message',
  `step` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Execution step',
  `progress` int(11) DEFAULT NULL COMMENT 'Progress percentage',
  `extra_data` json DEFAULT NULL COMMENT 'Extra data',
  `add_ts` bigint(20) NOT NULL COMMENT 'Add timestamp',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_log_level` (`log_level`),
  KEY `idx_add_ts` (`add_ts`),
  KEY `idx_task_id_log_level` (`task_id`,`log_level`),
  KEY `idx_platform_log_level` (`platform`,`log_level`),
  KEY `idx_account_id_log_level` (`account_id`,`log_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Crawler task logs table';

-- =============================================
-- 6. 社交账号表
-- 功能：管理各平台的登录账号信息
-- =============================================
DROP TABLE IF EXISTS `social_accounts`;
CREATE TABLE `social_accounts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name(xhs,dy,ks,bili,wb,tieba,zhihu)',
  `account_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Account name/nickname',
  `account_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Account ID',
  `username` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Username',
  `password` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Password(encrypted storage)',
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Phone number',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Email',
  `is_active` tinyint(1) DEFAULT '1' COMMENT 'Is active',
  `login_method` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'qrcode' COMMENT 'Login method(qrcode,phone,email,password)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  `notes` text COLLATE utf8mb4_unicode_ci COMMENT 'Notes',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_account_id` (`platform`,`account_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_platform_login_status` (`platform`,`is_active`),
  KEY `idx_platform_status` (`platform`,`is_active`),
  KEY `idx_account_name` (`account_name`),
  KEY `idx_username` (`username`),
  KEY `idx_phone` (`phone`),
  KEY `idx_email` (`email`),
  KEY `idx_login_method` (`login_method`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Social accounts table';

-- =============================================
-- 7. 登录令牌表
-- 功能：存储各平台的登录令牌和会话信息
-- =============================================
DROP TABLE IF EXISTS `login_tokens`;
CREATE TABLE `login_tokens` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `platform` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform identifier',
  `account_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Account ID',
  `token_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Token type: cookie, session, oauth',
  `token_data` json NOT NULL COMMENT 'Token data',
  `user_agent` text COLLATE utf8mb4_unicode_ci COMMENT 'User agent',
  `proxy_info` text COLLATE utf8mb4_unicode_ci COMMENT '代理信息(JSON格式，包含完整的代理配置)',
  `proxy_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理ID，关联proxy_pool表的id',
  `expire_time` bigint(20) DEFAULT NULL COMMENT 'Expire timestamp',
  `expires_at` datetime DEFAULT NULL COMMENT 'Token过期时间',
  `last_used_at` datetime DEFAULT NULL COMMENT 'Token最后使用时间',
  `is_valid` tinyint(1) DEFAULT '1' COMMENT 'Is valid: 1-valid, 0-invalid',
  `add_ts` bigint(20) NOT NULL COMMENT 'Add timestamp',
  `last_modify_ts` bigint(20) NOT NULL COMMENT 'Last modify timestamp',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_token_type` (`token_type`),
  KEY `idx_proxy_id` (`proxy_id`),
  KEY `idx_expire_time` (`expire_time`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_last_used_at` (`last_used_at`),
  KEY `idx_is_valid` (`is_valid`),
  KEY `idx_add_ts` (`add_ts`),
  KEY `idx_platform_account_id` (`platform`,`account_id`),
  KEY `idx_token_type_is_valid` (`token_type`,`is_valid`),
  KEY `idx_is_valid_expires_at` (`is_valid`,`expires_at`),
  KEY `idx_is_valid_last_used_at` (`is_valid`,`last_used_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Login tokens table';

-- =============================================
-- 8. 登录会话表
-- 功能：管理用户登录会话状态
-- =============================================
DROP TABLE IF EXISTS `login_sessions`;
CREATE TABLE `login_sessions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `session_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Session ID',
  `platform` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform identifier',
  `account_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Account ID',
  `session_data` json NOT NULL COMMENT 'Session data',
  `expire_time` bigint(20) DEFAULT NULL COMMENT 'Expire timestamp',
  `is_active` tinyint(1) DEFAULT '1' COMMENT 'Is active: 1-active, 0-inactive',
  `add_ts` bigint(20) NOT NULL COMMENT 'Add timestamp',
  `last_modify_ts` bigint(20) NOT NULL COMMENT 'Last modify timestamp',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_expire_time` (`expire_time`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_platform_account_id` (`platform`,`account_id`),
  KEY `idx_platform_is_active` (`platform`,`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Login sessions table';

-- =============================================
-- 9. 代理池表
-- 功能：管理代理IP池，支持多平台代理使用
-- =============================================
DROP TABLE IF EXISTS `proxy_pool`;
CREATE TABLE `proxy_pool` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `proxy_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '代理唯一标识',
  `ip` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '代理IP地址',
  `port` int(11) NOT NULL COMMENT '代理端口',
  `proxy_type` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'http' COMMENT '代理类型(http,https,socks5)',
  `username` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理用户名',
  `password` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理密码',
  `country` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理所在国家/地区',
  `speed` int(11) DEFAULT NULL COMMENT '代理速度(ms)',
  `anonymity` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '匿名级别(transparent,anonymous,elite)',
  `success_rate` float DEFAULT '0' COMMENT '成功率(0-100)',
  `expire_ts` bigint(20) DEFAULT NULL COMMENT '代理过期时间戳',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联平台(dy,xhs,ks,bili)',
  `account_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联的代理账号ID',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'qingguo' COMMENT '代理提供商(qingguo,kuaidaili,jisuhttp)',
  `usage_count` int(11) DEFAULT 0 COMMENT '使用次数',
  `success_count` int(11) DEFAULT 0 COMMENT '成功次数',
  `fail_count` int(11) DEFAULT 0 COMMENT '失败次数',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active' COMMENT '代理状态(active,expired,failed,rotating)',
  `enabled` tinyint(1) DEFAULT 1 COMMENT '是否启用(1:启用,0:禁用)',
  `area` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理区域信息',
  `description` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '代理描述信息',
  `last_check` timestamp NULL DEFAULT NULL COMMENT '最后检查时间',
  `task_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '青果代理的task_id',
  `proxy_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '真实出口IP地址',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活(兼容字段)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_proxy_ip_port` (`ip`,`port`),
  KEY `idx_proxy_id` (`proxy_id`),
  KEY `idx_ip_port` (`ip`,`port`),
  KEY `idx_platform` (`platform`),
  KEY `idx_account_id` (`account_id`),
  KEY `idx_provider` (`provider`),
  KEY `idx_status` (`status`),
  KEY `idx_enabled` (`enabled`),
  KEY `idx_area` (`area`),
  KEY `idx_expire_ts` (`expire_ts`),
  KEY `idx_last_used` (`last_used_at`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_proxy_type_status` (`proxy_type`,`is_active`),
  KEY `idx_last_check_time_result` (`last_check`,`is_active`),
  KEY `idx_country` (`country`),
  KEY `idx_speed` (`speed`),
  KEY `idx_success_rate` (`success_rate`),
  KEY `idx_anonymity` (`anonymity`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_proxy_ip` (`proxy_ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='代理池表 - 重新设计版本，支持代理与平台解耦';

-- =============================================
-- 10. 代理账号表
-- 功能：管理代理服务商的账号配置信息
-- =============================================
DROP TABLE IF EXISTS `proxy_accounts`;
CREATE TABLE `proxy_accounts` (
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

-- =============================================
-- 11. 代理账号日志表
-- 功能：记录代理账号的使用日志和操作历史
-- =============================================
DROP TABLE IF EXISTS `proxy_account_logs`;
CREATE TABLE `proxy_account_logs` (
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

-- =============================================
-- 12. 平台配置表
-- 功能：管理支持的平台配置信息
-- =============================================
DROP TABLE IF EXISTS `platforms`;
CREATE TABLE `platforms` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `platform_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform code',
  `platform_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `platform_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Platform URL',
  `is_active` tinyint(1) DEFAULT '1' COMMENT 'Is active',
  `config` json DEFAULT NULL COMMENT 'Platform configuration',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_code` (`platform_code`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_platform_name` (`platform_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Platforms table';

-- =============================================
-- 13. 任务统计表
-- 功能：存储任务执行统计数据和指标
-- =============================================
DROP TABLE IF EXISTS `task_statistics`;
CREATE TABLE `task_statistics` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Task ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `statistics_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Statistics type',
  `statistics_data` json NOT NULL COMMENT 'Statistics data',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_statistics_type` (`statistics_type`),
  KEY `idx_platform_statistics_type` (`platform`,`statistics_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Task statistics table';

-- =============================================
-- 14. 视频下载任务表
-- 功能：管理视频文件的下载任务
-- =============================================
DROP TABLE IF EXISTS `video_download_tasks`;
CREATE TABLE `video_download_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Task ID',
  `content_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `video_url` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Video URL',
  `download_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Download URL',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT 'Status',
  `progress` float DEFAULT '0' COMMENT 'Progress percentage',
  `file_size` bigint(20) DEFAULT NULL COMMENT 'File size',
  `local_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Local path',
  `minio_url` text COLLATE utf8mb4_unicode_ci COMMENT 'MinIO URL',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT 'Error message',
  `retry_count` int(11) DEFAULT '0' COMMENT 'Retry count',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `started_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_content_id` (`content_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_status` (`status`),
  KEY `idx_platform_status` (`platform`,`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_started_at` (`started_at`),
  KEY `idx_completed_at` (`completed_at`),
  KEY `idx_retry_count` (`retry_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Video download tasks table';

-- =============================================
-- 15. 视频文件表
-- 功能：管理下载的视频文件信息
-- =============================================
DROP TABLE IF EXISTS `video_files`;
CREATE TABLE `video_files` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `file_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'File ID',
  `content_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'File name',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'File path',
  `file_size` bigint(20) NOT NULL COMMENT 'File size',
  `file_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'File type',
  `storage_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'local' COMMENT 'Storage type',
  `minio_url` text COLLATE utf8mb4_unicode_ci COMMENT 'MinIO URL',
  `download_url` text COLLATE utf8mb4_unicode_ci COMMENT 'Download URL',
  `metadata` json DEFAULT NULL COMMENT 'File metadata',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT 'Is deleted',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_id` (`file_id`),
  KEY `idx_content_id` (`content_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_storage_type` (`storage_type`),
  KEY `idx_file_type` (`file_type`),
  KEY `idx_file_size` (`file_size`),
  KEY `idx_is_deleted` (`is_deleted`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_platform_storage_type` (`platform`,`storage_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Video files table';

-- =============================================
-- 16. 视频统计表
-- 功能：存储视频相关的统计数据
-- =============================================
DROP TABLE IF EXISTS `video_statistics`;
CREATE TABLE `video_statistics` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `content_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Content ID',
  `platform` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Platform name',
  `statistics_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Statistics type',
  `statistics_data` json NOT NULL COMMENT 'Statistics data',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_content_id` (`content_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_statistics_type` (`statistics_type`),
  KEY `idx_platform_statistics_type` (`platform`,`statistics_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Video statistics table';

-- =============================================
-- 17. 视频存储统计表
-- 功能：统计视频存储空间使用情况
-- =============================================
DROP TABLE IF EXISTS `video_storage_stats`;
CREATE TABLE `video_storage_stats` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `storage_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Storage type',
  `total_files` int(11) DEFAULT '0' COMMENT 'Total files',
  `total_size` bigint(20) DEFAULT '0' COMMENT 'Total size',
  `used_space` bigint(20) DEFAULT '0' COMMENT 'Used space',
  `free_space` bigint(20) DEFAULT '0' COMMENT 'Free space',
  `statistics_date` date NOT NULL COMMENT 'Statistics date',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_storage_type` (`storage_type`),
  KEY `idx_statistics_date` (`statistics_date`),
  KEY `idx_storage_type_date` (`storage_type`,`statistics_date`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Video storage statistics table';

-- =============================================
-- 初始数据插入
-- =============================================

-- 插入默认代理账号
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

-- =============================================
-- 创建时间戳字段触发器
-- =============================================

-- 为 login_tokens 表创建时间戳字段触发器
DROP TRIGGER IF EXISTS `tr_login_tokens_timestamps`;
DELIMITER $$
CREATE TRIGGER `tr_login_tokens_timestamps` 
BEFORE INSERT ON `login_tokens` 
FOR EACH ROW 
BEGIN
    SET NEW.add_ts = IFNULL(NEW.add_ts, UNIX_TIMESTAMP() * 1000);
    SET NEW.last_modify_ts = IFNULL(NEW.last_modify_ts, UNIX_TIMESTAMP() * 1000);
END$$
DELIMITER ;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;
