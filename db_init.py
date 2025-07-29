#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库初始化脚本
包含建表和基础数据插入
"""

import asyncio
import aiomysql
import logging
from typing import Optional
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置加载器
from config.env_config_loader import config_loader

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        self.pool = None
        self.config = config_loader.load_config()
        
    async def create_connection_pool(self):
        """创建数据库连接池"""
        try:
            db_config = self.config.get('database', {})
            
            # 先连接到MySQL服务器（不指定数据库）
            self.pool = await aiomysql.create_pool(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('username', 'root'),
                password=db_config.get('password', ''),
                charset=db_config.get('charset', 'utf8mb4'),
                autocommit=True,
                maxsize=10,
                minsize=1
            )
            logger.info("数据库连接池创建成功")
            
            # 检查并创建数据库
            database_name = db_config.get('database', 'mediacrawler')
            await self.ensure_database_exists(database_name)
            
            # 重新创建连接池，这次指定数据库
            self.pool.close()
            await self.pool.wait_closed()
            
            self.pool = await aiomysql.create_pool(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('username', 'root'),
                password=db_config.get('password', ''),
                db=database_name,
                charset=db_config.get('charset', 'utf8mb4'),
                autocommit=True,
                maxsize=10,
                minsize=1
            )
            logger.info(f"已连接到数据库: {database_name}")
            
        except Exception as e:
            logger.error(f"创建数据库连接池失败: {e}")
            raise
    
    async def ensure_database_exists(self, database_name):
        """确保数据库存在"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查数据库是否存在
                    await cursor.execute("SHOW DATABASES LIKE %s", (database_name,))
                    result = await cursor.fetchone()
                    
                    if not result:
                        # 创建数据库
                        await cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                        logger.info(f"数据库 {database_name} 创建成功")
                    else:
                        logger.info(f"数据库 {database_name} 已存在")
                        
        except Exception as e:
            logger.error(f"检查/创建数据库失败: {e}")
            raise
    
    async def close_pool(self):
        """关闭数据库连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("数据库连接池已关闭")
    
    async def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        db_config = self.config.get('database', {})
        database_name = db_config.get('database', 'mediacrawler')
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                """, (database_name, table_name))
                result = await cursor.fetchone()
                return result[0] > 0
    
    async def check_table_structure(self, table_name: str, expected_columns: list) -> bool:
        """检查表结构是否匹配"""
        db_config = self.config.get('database', {})
        database_name = db_config.get('database', 'mediacrawler')
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ORDINAL_POSITION
                """, (database_name, table_name))
                columns = await cursor.fetchall()
                
                if len(columns) != len(expected_columns):
                    return False
                
                # 简单检查列名是否匹配
                actual_column_names = [col[0] for col in columns]
                expected_column_names = [col['name'] for col in expected_columns]
                
                return set(actual_column_names) == set(expected_column_names)
    
    def get_additional_platform_tables(self):
        """获取其他平台的表配置 - 已废弃，统一使用unified_*表"""
        return []

    async def create_tables(self):
        """创建所有必要的表"""
        tables_config = [
            {
                'name': 'crawler_tasks',
                'columns': [
                    {'name': 'id', 'type': 'VARCHAR(36) PRIMARY KEY'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL'},
                    {'name': 'task_type', 'type': 'VARCHAR(20) NOT NULL'},
                    {'name': 'keywords', 'type': 'TEXT'},
                    {'name': 'status', 'type': 'VARCHAR(20) NOT NULL DEFAULT "pending"'},
                    {'name': 'progress', 'type': 'FLOAT DEFAULT 0.0'},
                    {'name': 'result_count', 'type': 'INT DEFAULT 0'},
                    {'name': 'error_message', 'type': 'TEXT'},
                    {'name': 'user_id', 'type': 'VARCHAR(50) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'params', 'type': 'TEXT COMMENT "任务参数JSON"'},
                    {'name': 'priority', 'type': 'INT DEFAULT 0 COMMENT "优先级"'},
                    {'name': 'is_favorite', 'type': 'BOOLEAN DEFAULT FALSE COMMENT "是否收藏"'},
                    {'name': 'deleted', 'type': 'BOOLEAN DEFAULT FALSE COMMENT "是否删除"'},
                    {'name': 'is_pinned', 'type': 'BOOLEAN DEFAULT FALSE COMMENT "是否置顶"'},
                    {'name': 'ip_address', 'type': 'VARCHAR(45) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': 'user_security_id', 'type': 'VARCHAR(100) DEFAULT NULL COMMENT "用户安全ID"'},
                    {'name': 'user_signature', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户签名"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'},
                    {'name': 'started_at', 'type': 'TIMESTAMP NULL'},
                    {'name': 'completed_at', 'type': 'TIMESTAMP NULL'}
                ],
                'indexes': [
                    {'name': 'idx_crawler_tasks_platform', 'columns': '(platform)'},
                    {'name': 'idx_crawler_tasks_status', 'columns': '(status)'},
                    {'name': 'idx_crawler_tasks_user_id', 'columns': '(user_id)'},
                    {'name': 'idx_crawler_tasks_created_at', 'columns': '(created_at)'}
                ]
            },
            {
                'name': 'social_accounts',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称(xhs,dy,ks,bili,wb,tieba,zhihu)"'},
                    {'name': 'account_name', 'type': 'VARCHAR(100) NOT NULL COMMENT "账号名称/昵称"'},
                    {'name': 'account_id', 'type': 'VARCHAR(100) COMMENT "账号ID"'},
                    {'name': 'username', 'type': 'VARCHAR(100) COMMENT "用户名"'},
                    {'name': 'password', 'type': 'VARCHAR(255) COMMENT "密码(加密存储)"'},
                    {'name': 'phone', 'type': 'VARCHAR(20) COMMENT "手机号"'},
                    {'name': 'email', 'type': 'VARCHAR(100) COMMENT "邮箱"'},
                    {'name': 'is_active', 'type': 'BOOLEAN DEFAULT TRUE COMMENT "是否启用"'},
                    {'name': 'login_method', 'type': 'VARCHAR(20) DEFAULT "qrcode" COMMENT "登录方式(qrcode,phone,email,password)"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'},
                    {'name': 'notes', 'type': 'TEXT COMMENT "备注"'}
                ],
                'indexes': [
                    {'name': 'idx_platform', 'columns': '(platform)'},
                    {'name': 'idx_is_active', 'columns': '(is_active)'}
                ]
            },
            {
                'name': 'login_tokens',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'account_id', 'type': 'INT NOT NULL COMMENT "关联的账号ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称"'},
                    {'name': 'token_type', 'type': 'VARCHAR(20) DEFAULT "cookie" COMMENT "令牌类型(cookie,session,token)"'},
                    {'name': 'token_data', 'type': 'TEXT COMMENT "令牌数据(JSON格式)"'},
                    {'name': 'user_agent', 'type': 'TEXT COMMENT "用户代理"'},
                    {'name': 'proxy_info', 'type': 'TEXT COMMENT "代理信息(JSON格式)"'},
                    {'name': 'is_valid', 'type': 'BOOLEAN DEFAULT TRUE COMMENT "是否有效"'},
                    {'name': 'expires_at', 'type': 'TIMESTAMP NULL COMMENT "过期时间"'},
                    {'name': 'last_used_at', 'type': 'TIMESTAMP NULL COMMENT "最后使用时间"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'}
                ],
                'indexes': [
                    {'name': 'idx_account_id', 'columns': '(account_id)'},
                    {'name': 'idx_platform', 'columns': '(platform)'},
                    {'name': 'idx_is_valid', 'columns': '(is_valid)'}
                ],
                'foreign_keys': [
                    {'name': 'fk_login_tokens_account_id', 'columns': 'account_id', 'references': 'social_accounts(id)', 'on_delete': 'CASCADE'}
                ]
            },
            {
                'name': 'crawler_task_logs',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'task_id', 'type': 'VARCHAR(50) NOT NULL COMMENT "任务ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称"'},
                    {'name': 'account_id', 'type': 'INT COMMENT "使用的账号ID"'},
                    {'name': 'log_level', 'type': 'VARCHAR(10) DEFAULT "INFO" COMMENT "日志级别(DEBUG,INFO,WARN,ERROR)"'},
                    {'name': 'message', 'type': 'TEXT COMMENT "日志消息"'},
                    {'name': 'step', 'type': 'VARCHAR(50) COMMENT "当前步骤"'},
                    {'name': 'progress', 'type': 'INT DEFAULT 0 COMMENT "进度百分比"'},
                    {'name': 'extra_data', 'type': 'TEXT COMMENT "额外数据(JSON格式)"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'}
                ],
                'indexes': [
                    {'name': 'idx_crawler_task_logs_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_crawler_task_logs_platform', 'columns': '(platform)'},
                    {'name': 'idx_crawler_task_logs_account_id', 'columns': '(account_id)'},
                    {'name': 'idx_crawler_task_logs_log_level', 'columns': '(log_level)'},
                    {'name': 'idx_crawler_task_logs_created_at', 'columns': '(created_at)'}
                ]
            },
            # 统一内容表 - 替代所有平台特定的内容表
            {
                'name': 'unified_content',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'content_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "内容ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称"'},
                    {'name': 'content_type', 'type': 'VARCHAR(50) COMMENT "内容类型"'},
                    {'name': 'task_id', 'type': 'VARCHAR(36) COMMENT "任务ID"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(200) COMMENT "来源关键词"'},
                    {'name': 'title', 'type': 'VARCHAR(500) COMMENT "标题"'},
                    {'name': 'description', 'type': 'TEXT COMMENT "描述"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "内容"'},
                    {'name': 'create_time', 'type': 'BIGINT COMMENT "创建时间戳"'},
                    {'name': 'publish_time', 'type': 'BIGINT COMMENT "发布时间戳"'},
                    {'name': 'update_time', 'type': 'BIGINT COMMENT "更新时间戳"'},
                    {'name': 'author_id', 'type': 'VARCHAR(100) COMMENT "作者ID"'},
                    {'name': 'author_name', 'type': 'VARCHAR(100) COMMENT "作者名称"'},
                    {'name': 'author_nickname', 'type': 'VARCHAR(100) COMMENT "作者昵称"'},
                    {'name': 'author_avatar', 'type': 'TEXT COMMENT "作者头像"'},
                    {'name': 'author_signature', 'type': 'TEXT COMMENT "作者签名"'},
                    {'name': 'author_unique_id', 'type': 'VARCHAR(100) COMMENT "作者唯一ID"'},
                    {'name': 'author_sec_uid', 'type': 'VARCHAR(100) COMMENT "作者sec_uid"'},
                    {'name': 'author_short_id', 'type': 'VARCHAR(100) COMMENT "作者短ID"'},
                    {'name': 'like_count', 'type': 'INT DEFAULT 0 COMMENT "点赞数"'},
                    {'name': 'comment_count', 'type': 'INT DEFAULT 0 COMMENT "评论数"'},
                    {'name': 'share_count', 'type': 'INT DEFAULT 0 COMMENT "分享数"'},
                    {'name': 'collect_count', 'type': 'INT DEFAULT 0 COMMENT "收藏数"'},
                    {'name': 'view_count', 'type': 'INT DEFAULT 0 COMMENT "播放数"'},
                    {'name': 'cover_url', 'type': 'TEXT COMMENT "封面URL"'},
                    {'name': 'video_url', 'type': 'TEXT COMMENT "视频URL"'},
                    {'name': 'video_download_url', 'type': 'TEXT COMMENT "视频下载URL"'},
                    {'name': 'video_play_url', 'type': 'TEXT COMMENT "视频播放URL"'},
                    {'name': 'video_share_url', 'type': 'TEXT COMMENT "视频分享URL"'},
                    {'name': 'image_urls', 'type': 'TEXT COMMENT "图片URL列表"'},
                    {'name': 'audio_url', 'type': 'TEXT COMMENT "音频URL"'},
                    {'name': 'file_urls', 'type': 'TEXT COMMENT "文件URL列表"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(100) COMMENT "IP位置"'},
                    {'name': 'location', 'type': 'VARCHAR(200) COMMENT "位置信息"'},
                    {'name': 'tags', 'type': 'TEXT COMMENT "标签"'},
                    {'name': 'categories', 'type': 'TEXT COMMENT "分类"'},
                    {'name': 'topics', 'type': 'TEXT COMMENT "话题"'},
                    {'name': 'is_favorite', 'type': 'TINYINT DEFAULT 0 COMMENT "是否收藏"'},
                    {'name': 'is_deleted', 'type': 'TINYINT DEFAULT 0 COMMENT "是否删除"'},
                    {'name': 'is_private', 'type': 'TINYINT DEFAULT 0 COMMENT "是否私密"'},
                    {'name': 'is_original', 'type': 'TINYINT DEFAULT 0 COMMENT "是否原创"'},
                    {'name': 'minio_url', 'type': 'TEXT COMMENT "MinIO URL"'},
                    {'name': 'local_path', 'type': 'VARCHAR(500) COMMENT "本地路径"'},
                    {'name': 'file_size', 'type': 'BIGINT COMMENT "文件大小"'},
                    {'name': 'storage_type', 'type': 'VARCHAR(20) DEFAULT "url_only" COMMENT "存储类型"'},
                    {'name': 'metadata', 'type': 'TEXT COMMENT "元数据"'},
                    {'name': 'raw_data', 'type': 'LONGTEXT COMMENT "原始数据"'},
                    {'name': 'extra_info', 'type': 'TEXT COMMENT "额外信息"'},
                    {'name': 'add_ts', 'type': 'BIGINT COMMENT "添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT COMMENT "最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_unified_content_platform_content_id', 'columns': '(platform, content_id)'},
                    {'name': 'idx_unified_content_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_unified_content_author_id', 'columns': '(author_id)'},
                    {'name': 'idx_unified_content_create_time', 'columns': '(create_time)'},
                    {'name': 'idx_unified_content_add_ts', 'columns': '(add_ts)'}
                ]
            },
            # 统一评论表 - 替代所有平台特定的评论表
            {
                'name': 'unified_comment',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "评论ID"'},
                    {'name': 'content_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "内容ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称"'},
                    {'name': 'parent_id', 'type': 'VARCHAR(100) COMMENT "父评论ID"'},
                    {'name': 'reply_to_id', 'type': 'VARCHAR(100) COMMENT "回复评论ID"'},
                    {'name': 'content', 'type': 'TEXT COMMENT "评论内容"'},
                    {'name': 'text', 'type': 'TEXT COMMENT "纯文本内容"'},
                    {'name': 'html_content', 'type': 'TEXT COMMENT "HTML内容"'},
                    {'name': 'author_id', 'type': 'VARCHAR(100) COMMENT "作者ID"'},
                    {'name': 'author_name', 'type': 'VARCHAR(100) COMMENT "作者名称"'},
                    {'name': 'author_nickname', 'type': 'VARCHAR(100) COMMENT "作者昵称"'},
                    {'name': 'author_avatar', 'type': 'TEXT COMMENT "作者头像"'},
                    {'name': 'like_count', 'type': 'INT DEFAULT 0 COMMENT "点赞数"'},
                    {'name': 'reply_count', 'type': 'INT DEFAULT 0 COMMENT "回复数"'},
                    {'name': 'share_count', 'type': 'INT DEFAULT 0 COMMENT "分享数"'},
                    {'name': 'create_time', 'type': 'BIGINT COMMENT "创建时间戳"'},
                    {'name': 'publish_time', 'type': 'BIGINT COMMENT "发布时间戳"'},
                    {'name': 'is_deleted', 'type': 'TINYINT DEFAULT 0 COMMENT "是否删除"'},
                    {'name': 'is_hidden', 'type': 'TINYINT DEFAULT 0 COMMENT "是否隐藏"'},
                    {'name': 'is_top', 'type': 'TINYINT DEFAULT 0 COMMENT "是否置顶"'},
                    {'name': 'metadata', 'type': 'TEXT COMMENT "元数据"'},
                    {'name': 'raw_data', 'type': 'LONGTEXT COMMENT "原始数据"'},
                    {'name': 'add_ts', 'type': 'BIGINT COMMENT "添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT COMMENT "最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_unified_comment_platform_comment_id', 'columns': '(platform, comment_id)'},
                    {'name': 'idx_unified_comment_content_id', 'columns': '(content_id)'},
                    {'name': 'idx_unified_comment_author_id', 'columns': '(author_id)'},
                    {'name': 'idx_unified_comment_create_time', 'columns': '(create_time)'},
                    {'name': 'idx_unified_comment_add_ts', 'columns': '(add_ts)'}
                ]
            },
            # 统一创作者表 - 替代所有平台特定的创作者表
            {
                'name': 'unified_creator',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'creator_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "创作者ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台名称"'},
                    {'name': 'creator_type', 'type': 'VARCHAR(50) COMMENT "创作者类型"'},
                    {'name': 'task_id', 'type': 'VARCHAR(36) COMMENT "任务ID"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(200) COMMENT "来源关键词"'},
                    {'name': 'name', 'type': 'VARCHAR(100) COMMENT "创作者名称"'},
                    {'name': 'nickname', 'type': 'VARCHAR(100) COMMENT "创作者昵称"'},
                    {'name': 'avatar', 'type': 'TEXT COMMENT "创作者头像"'},
                    {'name': 'signature', 'type': 'TEXT COMMENT "创作者签名"'},
                    {'name': 'description', 'type': 'TEXT COMMENT "创作者描述"'},
                    {'name': 'unique_id', 'type': 'VARCHAR(100) COMMENT "创作者唯一ID"'},
                    {'name': 'sec_uid', 'type': 'VARCHAR(100) COMMENT "创作者sec_uid"'},
                    {'name': 'short_id', 'type': 'VARCHAR(100) COMMENT "创作者短ID"'},
                    {'name': 'gender', 'type': 'VARCHAR(10) COMMENT "性别"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(100) COMMENT "IP位置"'},
                    {'name': 'location', 'type': 'VARCHAR(200) COMMENT "位置信息"'},
                    {'name': 'follow_count', 'type': 'INT DEFAULT 0 COMMENT "关注数"'},
                    {'name': 'fans_count', 'type': 'INT DEFAULT 0 COMMENT "粉丝数"'},
                    {'name': 'like_count', 'type': 'INT DEFAULT 0 COMMENT "获赞数"'},
                    {'name': 'content_count', 'type': 'INT DEFAULT 0 COMMENT "作品数"'},
                    {'name': 'interaction_count', 'type': 'INT DEFAULT 0 COMMENT "互动数"'},
                    {'name': 'verified', 'type': 'TINYINT DEFAULT 0 COMMENT "是否认证"'},
                    {'name': 'verified_type', 'type': 'VARCHAR(50) COMMENT "认证类型"'},
                    {'name': 'level', 'type': 'INT DEFAULT 0 COMMENT "等级"'},
                    {'name': 'tags', 'type': 'TEXT COMMENT "标签"'},
                    {'name': 'categories', 'type': 'TEXT COMMENT "分类"'},
                    {'name': 'profile_url', 'type': 'TEXT COMMENT "主页URL"'},
                    {'name': 'is_deleted', 'type': 'TINYINT DEFAULT 0 COMMENT "是否删除"'},
                    {'name': 'is_private', 'type': 'TINYINT DEFAULT 0 COMMENT "是否私密"'},
                    {'name': 'is_blocked', 'type': 'TINYINT DEFAULT 0 COMMENT "是否被屏蔽"'},
                    {'name': 'metadata', 'type': 'TEXT COMMENT "元数据"'},
                    {'name': 'raw_data', 'type': 'LONGTEXT COMMENT "原始数据"'},
                    {'name': 'extra_info', 'type': 'TEXT COMMENT "额外信息"'},
                    {'name': 'add_ts', 'type': 'BIGINT COMMENT "添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT COMMENT "最后修改时间戳"'},
                    {'name': 'last_refresh_ts', 'type': 'BIGINT COMMENT "最后刷新时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_unified_creator_platform_creator_id', 'columns': '(platform, creator_id)'},
                    {'name': 'idx_unified_creator_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_unified_creator_name', 'columns': '(name)'},
                    {'name': 'idx_unified_creator_fans_count', 'columns': '(fans_count)'},
                    {'name': 'idx_unified_creator_add_ts', 'columns': '(add_ts)'}
                ]
            },
            # 视频文件表 - 用于视频收藏功能
            {
                'name': 'video_files',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT "文件ID"'},
                    {'name': 'file_hash', 'type': 'VARCHAR(64) NOT NULL UNIQUE COMMENT "文件哈希值(MD5)"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "来源平台"'},
                    {'name': 'content_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "内容ID"'},
                    {'name': 'task_id', 'type': 'VARCHAR(100) DEFAULT NULL COMMENT "关联任务ID"'},
                    {'name': 'original_url', 'type': 'TEXT COMMENT "原始视频URL"'},
                    {'name': 'title', 'type': 'VARCHAR(500) DEFAULT NULL COMMENT "视频标题"'},
                    {'name': 'author_name', 'type': 'VARCHAR(100) DEFAULT NULL COMMENT "作者名称"'},
                    {'name': 'duration', 'type': 'INT DEFAULT NULL COMMENT "视频时长(秒)"'},
                    {'name': 'file_size', 'type': 'BIGINT DEFAULT NULL COMMENT "文件大小(字节)"'},
                    {'name': 'video_format', 'type': 'VARCHAR(20) DEFAULT NULL COMMENT "视频格式(mp4/webm等)"'},
                    {'name': 'resolution', 'type': 'VARCHAR(20) DEFAULT NULL COMMENT "分辨率(1920x1080)"'},
                    {'name': 'video_codec', 'type': 'VARCHAR(50) DEFAULT NULL COMMENT "视频编码(H.264/VP9等)"'},
                    {'name': 'audio_codec', 'type': 'VARCHAR(50) DEFAULT NULL COMMENT "音频编码(AAC/Opus等)"'},
                    {'name': 'bitrate', 'type': 'INT DEFAULT NULL COMMENT "码率(kbps)"'},
                    {'name': 'fps', 'type': 'DECIMAL(5,2) DEFAULT NULL COMMENT "帧率"'},
                    {'name': 'storage_type', 'type': 'ENUM("local","minio","url_only","temp") DEFAULT "url_only" COMMENT "存储类型"'},
                    {'name': 'local_path', 'type': 'TEXT COMMENT "本地存储路径"'},
                    {'name': 'minio_bucket', 'type': 'VARCHAR(100) COMMENT "MinIO桶名"'},
                    {'name': 'minio_object_key', 'type': 'VARCHAR(500) COMMENT "MinIO对象键"'},
                    {'name': 'cdn_url', 'type': 'TEXT COMMENT "CDN访问地址"'},
                    {'name': 'download_status', 'type': 'ENUM("pending","downloading","completed","failed","expired") DEFAULT "pending" COMMENT "下载状态"'},
                    {'name': 'download_progress', 'type': 'DECIMAL(5,2) DEFAULT 0 COMMENT "下载进度(%)"'},
                    {'name': 'download_error', 'type': 'TEXT COMMENT "下载错误信息"'},
                    {'name': 'download_attempts', 'type': 'INT DEFAULT 0 COMMENT "下载尝试次数"'},
                    {'name': 'download_count', 'type': 'INT DEFAULT 0 COMMENT "下载次数"'},
                    {'name': 'last_accessed_at', 'type': 'TIMESTAMP NULL COMMENT "最后访问时间"'},
                    {'name': 'expiry_date', 'type': 'TIMESTAMP NULL COMMENT "过期时间"'},
                    {'name': 'metadata', 'type': 'JSON COMMENT "扩展元数据"'},
                    {'name': 'thumbnail_url', 'type': 'TEXT COMMENT "缩略图URL"'},
                    {'name': 'thumbnail_path', 'type': 'TEXT COMMENT "缩略图本地路径"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'}
                ],
                'indexes': [
                    {'name': 'idx_video_files_platform_content', 'columns': '(platform, content_id)'},
                    {'name': 'idx_video_files_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_video_files_storage_type', 'columns': '(storage_type)'},
                    {'name': 'idx_video_files_download_status', 'columns': '(download_status)'},
                    {'name': 'idx_video_files_created_at', 'columns': '(created_at)'}
                ]
            },
            {
                'name': 'login_sessions',
                'columns': [
                    {'name': 'id', 'type': 'VARCHAR(36) PRIMARY KEY'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL'},
                    {'name': 'status', 'type': 'VARCHAR(20) NOT NULL DEFAULT "not_logged_in"'},
                    {'name': 'cookies', 'type': 'TEXT'},
                    {'name': 'user_info', 'type': 'TEXT'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'},
                    {'name': 'expires_at', 'type': 'TIMESTAMP NULL'}
                ],
                'indexes': [
                    {'name': 'idx_platform', 'columns': '(platform)'},
                    {'name': 'idx_status', 'columns': '(status)'}
                ]
            },
            {
                'name': 'proxy_pool',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'proxy_id', 'type': 'VARCHAR(100) NOT NULL'},
                    {'name': 'ip', 'type': 'VARCHAR(45) NOT NULL'},
                    {'name': 'port', 'type': 'INT NOT NULL'},
                    {'name': 'proxy_type', 'type': 'VARCHAR(10) NOT NULL DEFAULT "http"'},
                    {'name': 'country', 'type': 'VARCHAR(50)'},
                    {'name': 'speed', 'type': 'INT DEFAULT 0'},
                    {'name': 'anonymity', 'type': 'VARCHAR(20)'},
                    {'name': 'success_rate', 'type': 'FLOAT DEFAULT 0.0'},
                    {'name': 'last_check', 'type': 'TIMESTAMP NULL'},
                    {'name': 'is_active', 'type': 'BOOLEAN DEFAULT TRUE'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'}
                ],
                'indexes': [
                    {'name': 'idx_proxy_id', 'columns': '(proxy_id)'},
                    {'name': 'idx_ip_port', 'columns': '(ip, port)'},
                    {'name': 'idx_is_active', 'columns': '(is_active)'}
                ]
            },
            # 视频下载任务表
            {
                'name': 'video_download_tasks',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT "任务ID"'},
                    {'name': 'task_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "任务唯一标识"'},
                    {'name': 'video_id', 'type': 'VARCHAR(100) NOT NULL COMMENT "视频ID"'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL COMMENT "平台"'},
                    {'name': 'video_url', 'type': 'TEXT NOT NULL COMMENT "视频URL"'},
                    {'name': 'download_type', 'type': 'VARCHAR(20) DEFAULT "local" COMMENT "下载类型"'},
                    {'name': 'status', 'type': 'VARCHAR(20) DEFAULT "created" COMMENT "状态"'},
                    {'name': 'result', 'type': 'JSON DEFAULT NULL COMMENT "结果信息"'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'},
                    {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'}
                ],
                'indexes': [
                    {'name': 'idx_video_download_tasks_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_video_download_tasks_video_id', 'columns': '(video_id)'},
                    {'name': 'idx_video_download_tasks_platform', 'columns': '(platform)'},
                    {'name': 'idx_video_download_tasks_status', 'columns': '(status)'},
                    {'name': 'idx_video_download_tasks_created_at', 'columns': '(created_at)'}
                ]
            }
        ]
        
        # 添加其他平台表
        additional_platform_tables = self.get_additional_platform_tables()
        tables_config.extend(additional_platform_tables)
        
        for table_config in tables_config:
            table_name = table_config['name']
            columns = table_config['columns']
            indexes = table_config.get('indexes', [])
            foreign_keys = table_config.get('foreign_keys', [])
            
            # 检查表是否存在
            if await self.check_table_exists(table_name):
                logger.info(f"表 {table_name} 已存在，跳过创建")
                continue
            
            # 创建表
            await self.create_table(table_name, columns, indexes, foreign_keys)
            logger.info(f"表 {table_name} 创建成功")
    
    async def create_table(self, table_name: str, columns: list, indexes: list = None, foreign_keys: list = None):
        """创建单个表"""
        column_definitions = []
        index_definitions = []
        foreign_key_definitions = []
        
        # 处理列定义
        for column in columns:
            column_definitions.append(f"{column['name']} {column['type']}")
        
        # 处理索引定义
        if indexes:
            for index in indexes:
                index_definitions.append(f"INDEX {index['name']} {index['columns']}")
        
        # 处理外键定义
        if foreign_keys:
            for fk in foreign_keys:
                foreign_key_definitions.append(f"CONSTRAINT {fk['name']} FOREIGN KEY ({fk['columns']}) REFERENCES {fk['references']} ON DELETE {fk['on_delete']}")
        
        # 构建CREATE TABLE语句
        create_sql = f"CREATE TABLE {table_name} (\n"
        create_sql += ",\n".join(column_definitions)
        if index_definitions:
            create_sql += ",\n" + ",\n".join(index_definitions)
        if foreign_key_definitions:
            create_sql += ",\n" + ",\n".join(foreign_key_definitions)
        create_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(create_sql)
    
    async def insert_basic_data(self):
        """插入基础数据"""
        # 插入平台信息
        platforms = [
            ('xhs', '小红书', '小红书笔记和评论爬取'),
            ('dy', '抖音', '抖音视频和评论爬取'),
            ('ks', '快手', '快手视频和评论爬取'),
            ('bili', 'B站', 'B站视频和评论爬取'),
            ('wb', '微博', '微博内容和评论爬取'),
            ('tieba', '贴吧', '贴吧帖子和回复爬取'),
            ('zhihu', '知乎', '知乎问答和评论爬取')
        ]
        
        # 创建platforms表（如果不存在）
        if not await self.check_table_exists('platforms'):
            await self.create_table('platforms', [
                {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                {'name': 'code', 'type': 'VARCHAR(20) UNIQUE NOT NULL'},
                {'name': 'name', 'type': 'VARCHAR(50) NOT NULL'},
                {'name': 'description', 'type': 'TEXT'},
                {'name': 'is_active', 'type': 'BOOLEAN DEFAULT TRUE'},
                {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'}
            ])
            logger.info("platforms表创建成功")
        
        # 检查是否已有平台数据
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT COUNT(*) FROM platforms")
                    result = await cursor.fetchone()
                    if result[0] > 0:
                        logger.info("平台数据已存在，跳过插入")
                    else:
                        # 插入平台数据
                        for platform in platforms:
                            await cursor.execute("""
                                INSERT INTO platforms (code, name, description) 
                                VALUES (%s, %s, %s)
                                ON DUPLICATE KEY UPDATE 
                                name = VALUES(name), 
                                description = VALUES(description)
                            """, platform)
                        logger.info("平台数据插入完成")
        except Exception as e:
            logger.error(f"处理平台数据失败: {e}")
            raise
        
        # 插入默认社交账号
        default_accounts = [
            ('xhs', '小红书默认账号', 'qrcode', '系统默认创建的小红书账号'),
            ('dy', '抖音默认账号', 'qrcode', '系统默认创建的抖音账号'),
            ('ks', '快手默认账号', 'qrcode', '系统默认创建的快手账号'),
            ('bili', 'B站默认账号', 'qrcode', '系统默认创建的B站账号'),
            ('wb', '微博默认账号', 'qrcode', '系统默认创建的微博账号'),
            ('tieba', '贴吧默认账号', 'qrcode', '系统默认创建的贴吧账号'),
            ('zhihu', '知乎默认账号', 'qrcode', '系统默认创建的知乎账号')
        ]
        
        # 检查是否已有社交账号数据
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT COUNT(*) FROM social_accounts")
                    result = await cursor.fetchone()
                    if result[0] > 0:
                        logger.info("社交账号数据已存在，跳过插入")
                    else:
                        # 插入默认社交账号
                        for account in default_accounts:
                            await cursor.execute("""
                                INSERT INTO social_accounts (platform, account_name, login_method, notes) 
                                VALUES (%s, %s, %s, %s)
                            """, account)
                        logger.info("默认社交账号插入完成")
        except Exception as e:
            logger.error(f"处理社交账号数据失败: {e}")
            raise
    
    async def initialize_database(self):
        """初始化数据库"""
        try:
            await self.create_connection_pool()
            await self.create_tables()
            await self.insert_basic_data()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
        finally:
            await self.close_pool()

async def main():
    """主函数"""
    initializer = DatabaseInitializer()
    await initializer.initialize_database()

if __name__ == "__main__":
    asyncio.run(main()) 