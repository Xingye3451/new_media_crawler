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
        """获取其他平台的表配置"""
        additional_tables = [
            # 快手表
            {
                'name': 'kuaishou_video',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'video_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'video_type', 'type': 'VARCHAR(16) NOT NULL COMMENT "视频类型"'},
                    {'name': 'title', 'type': 'VARCHAR(500) DEFAULT NULL COMMENT "视频标题"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "视频描述"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "视频发布时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'liked_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频点赞数"'},
                    {'name': 'viewd_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频浏览数量"'},
                    {'name': 'video_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频详情URL"'},
                    {'name': 'video_cover_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频封面图 URL"'},
                    {'name': 'video_play_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频播放 URL"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_kuaishou_video_video_id', 'columns': '(video_id)'},
                    {'name': 'idx_kuaishou_video_create_time', 'columns': '(create_time)'}
                ]
            },
            {
                'name': 'kuaishou_video_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'video_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "评论内容"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "评论时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'sub_comment_count', 'type': 'VARCHAR(16) NOT NULL COMMENT "评论回复数"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_kuaishou_video_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_kuaishou_video_comment_video_id', 'columns': '(video_id)'}
                ]
            },
            # B站表
            {
                'name': 'bilibili_video',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'video_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'video_type', 'type': 'VARCHAR(16) NOT NULL COMMENT "视频类型"'},
                    {'name': 'title', 'type': 'VARCHAR(500) DEFAULT NULL COMMENT "视频标题"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "视频描述"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "视频发布时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'view_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频观看数量"'},
                    {'name': 'danmaku_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频弹幕数量"'},
                    {'name': 'comment_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频评论数量"'},
                    {'name': 'liked_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频点赞数量"'},
                    {'name': 'video_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频详情URL"'},
                    {'name': 'video_cover_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频封面图 URL"'},
                    {'name': 'video_play_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "视频播放 URL"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_bilibili_video_video_id', 'columns': '(video_id)'},
                    {'name': 'idx_bilibili_video_create_time', 'columns': '(create_time)'}
                ]
            },
            {
                'name': 'bilibili_video_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'video_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "评论内容"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "评论时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'sub_comment_count', 'type': 'VARCHAR(16) NOT NULL COMMENT "评论回复数"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "父评论ID"'},
                    {'name': 'like_count', 'type': 'VARCHAR(255) NOT NULL DEFAULT "0" COMMENT "点赞数"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_bilibili_video_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_bilibili_video_comment_video_id', 'columns': '(video_id)'}
                ]
            },
            # 微博表
            {
                'name': 'weibo_note',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'note_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "帖子ID"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "帖子正文内容"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "帖子发布时间戳"'},
                    {'name': 'create_date_time', 'type': 'VARCHAR(32) NOT NULL COMMENT "帖子发布日期时间"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'gender', 'type': 'VARCHAR(12) DEFAULT NULL COMMENT "用户性别"'},
                    {'name': 'profile_url', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户主页地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(32) DEFAULT NULL COMMENT "发布微博的地理信息"'},
                    {'name': 'liked_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "帖子点赞数"'},
                    {'name': 'comments_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "帖子评论数量"'},
                    {'name': 'shared_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "帖子转发数量"'},
                    {'name': 'note_url', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "帖子详情URL"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_weibo_note_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_weibo_note_create_time', 'columns': '(create_time)'},
                    {'name': 'idx_weibo_note_create_date_time', 'columns': '(create_date_time)'}
                ]
            },
            {
                'name': 'weibo_note_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'note_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "帖子ID"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "评论内容"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "评论时间戳"'},
                    {'name': 'create_date_time', 'type': 'VARCHAR(32) NOT NULL COMMENT "评论日期时间"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'gender', 'type': 'VARCHAR(12) DEFAULT NULL COMMENT "用户性别"'},
                    {'name': 'profile_url', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户主页地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(32) DEFAULT NULL COMMENT "发布微博的地理信息"'},
                    {'name': 'comment_like_count', 'type': 'VARCHAR(16) NOT NULL COMMENT "评论点赞数量"'},
                    {'name': 'sub_comment_count', 'type': 'VARCHAR(16) NOT NULL COMMENT "评论回复数"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "父评论ID"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_weibo_note_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_weibo_note_comment_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_weibo_note_comment_create_date_time', 'columns': '(create_date_time)'}
                ]
            },
            # 贴吧表
            {
                'name': 'tieba_note',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'note_id', 'type': 'VARCHAR(644) NOT NULL COMMENT "帖子ID"'},
                    {'name': 'title', 'type': 'VARCHAR(255) NOT NULL COMMENT "帖子标题"'},
                    {'name': '`desc`', 'type': 'TEXT COMMENT "帖子描述"'},
                    {'name': 'note_url', 'type': 'VARCHAR(255) NOT NULL COMMENT "帖子链接"'},
                    {'name': 'publish_time', 'type': 'VARCHAR(255) NOT NULL COMMENT "发布时间"'},
                    {'name': 'user_link', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户主页链接"'},
                    {'name': 'user_nickname', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户昵称"'},
                    {'name': 'user_avatar', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户头像地址"'},
                    {'name': 'tieba_id', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "贴吧ID"'},
                    {'name': 'tieba_name', 'type': 'VARCHAR(255) NOT NULL COMMENT "贴吧名称"'},
                    {'name': 'tieba_link', 'type': 'VARCHAR(255) NOT NULL COMMENT "贴吧链接"'},
                    {'name': 'total_replay_num', 'type': 'INT DEFAULT 0 COMMENT "帖子回复总数"'},
                    {'name': 'total_replay_page', 'type': 'INT DEFAULT 0 COMMENT "帖子回复总页数"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "IP地理位置"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_tieba_note_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_tieba_note_publish_time', 'columns': '(publish_time)'}
                ]
            },
            {
                'name': 'tieba_comment',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(255) NOT NULL COMMENT "评论ID"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "父评论ID"'},
                    {'name': 'content', 'type': 'TEXT NOT NULL COMMENT "评论内容"'},
                    {'name': 'user_link', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户主页链接"'},
                    {'name': 'user_nickname', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户昵称"'},
                    {'name': 'user_avatar', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "用户头像地址"'},
                    {'name': 'tieba_id', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "贴吧ID"'},
                    {'name': 'tieba_name', 'type': 'VARCHAR(255) NOT NULL COMMENT "贴吧名称"'},
                    {'name': 'tieba_link', 'type': 'VARCHAR(255) NOT NULL COMMENT "贴吧链接"'},
                    {'name': 'publish_time', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "发布时间"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "IP地理位置"'},
                    {'name': 'sub_comment_count', 'type': 'INT DEFAULT 0 COMMENT "子评论数"'},
                    {'name': 'note_id', 'type': 'VARCHAR(255) NOT NULL COMMENT "帖子ID"'},
                    {'name': 'note_url', 'type': 'VARCHAR(255) NOT NULL COMMENT "帖子链接"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_tieba_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_tieba_comment_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_tieba_comment_publish_time', 'columns': '(publish_time)'}
                ]
            },
            # 知乎表
            {
                'name': 'zhihu_content',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'content_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "内容ID"'},
                    {'name': 'content_type', 'type': 'VARCHAR(16) NOT NULL COMMENT "内容类型(article | answer | zvideo)"'},
                    {'name': 'content_text', 'type': 'LONGTEXT COMMENT "内容文本, 如果是视频类型这里为空"'},
                    {'name': 'content_url', 'type': 'VARCHAR(255) NOT NULL COMMENT "内容落地链接"'},
                    {'name': 'question_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "问题ID, type为answer时有值"'},
                    {'name': 'title', 'type': 'VARCHAR(255) NOT NULL COMMENT "内容标题"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "内容描述"'},
                    {'name': 'created_time', 'type': 'VARCHAR(32) NOT NULL COMMENT "创建时间"'},
                    {'name': 'updated_time', 'type': 'VARCHAR(32) NOT NULL COMMENT "更新时间"'},
                    {'name': 'voteup_count', 'type': 'INT NOT NULL DEFAULT 0 COMMENT "赞同人数"'},
                    {'name': 'comment_count', 'type': 'INT NOT NULL DEFAULT 0 COMMENT "评论数量"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "来源关键词"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户ID"'},
                    {'name': 'user_link', 'type': 'VARCHAR(255) NOT NULL COMMENT "用户主页链接"'},
                    {'name': 'user_nickname', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户昵称"'},
                    {'name': 'user_avatar', 'type': 'VARCHAR(255) NOT NULL COMMENT "用户头像地址"'},
                    {'name': 'user_url_token', 'type': 'VARCHAR(255) NOT NULL COMMENT "用户url_token"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_zhihu_content_content_id', 'columns': '(content_id)'},
                    {'name': 'idx_zhihu_content_created_time', 'columns': '(created_time)'}
                ]
            },
            {
                'name': 'zhihu_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "父评论ID"'},
                    {'name': 'content', 'type': 'TEXT NOT NULL COMMENT "评论内容"'},
                    {'name': 'publish_time', 'type': 'VARCHAR(32) NOT NULL COMMENT "发布时间"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "IP地理位置"'},
                    {'name': 'sub_comment_count', 'type': 'INT NOT NULL DEFAULT 0 COMMENT "子评论数"'},
                    {'name': 'like_count', 'type': 'INT NOT NULL DEFAULT 0 COMMENT "点赞数"'},
                    {'name': 'dislike_count', 'type': 'INT NOT NULL DEFAULT 0 COMMENT "踩数"'},
                    {'name': 'content_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "内容ID"'},
                    {'name': 'content_type', 'type': 'VARCHAR(16) NOT NULL COMMENT "内容类型(article | answer | zvideo)"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户ID"'},
                    {'name': 'user_link', 'type': 'VARCHAR(255) NOT NULL COMMENT "用户主页链接"'},
                    {'name': 'user_nickname', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户昵称"'},
                    {'name': 'user_avatar', 'type': 'VARCHAR(255) NOT NULL COMMENT "用户头像地址"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_zhihu_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_zhihu_comment_content_id', 'columns': '(content_id)'},
                    {'name': 'idx_zhihu_comment_publish_time', 'columns': '(publish_time)'}
                ]
            }
        ]
        return additional_tables

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
            {
                'name': 'crawled_data',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'task_id', 'type': 'VARCHAR(36) NOT NULL'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL'},
                    {'name': 'content_id', 'type': 'VARCHAR(100) NOT NULL'},
                    {'name': 'title', 'type': 'TEXT'},
                    {'name': 'content', 'type': 'LONGTEXT'},
                    {'name': 'author', 'type': 'VARCHAR(100)'},
                    {'name': 'author_id', 'type': 'VARCHAR(100)'},
                    {'name': 'publish_time', 'type': 'DATETIME'},
                    {'name': 'likes', 'type': 'INT DEFAULT 0'},
                    {'name': 'comments', 'type': 'INT DEFAULT 0'},
                    {'name': 'shares', 'type': 'INT DEFAULT 0'},
                    {'name': 'views', 'type': 'INT DEFAULT 0'},
                    {'name': 'url', 'type': 'TEXT'},
                    {'name': 'tags', 'type': 'TEXT'},
                    {'name': 'images', 'type': 'TEXT'},
                    {'name': 'videos', 'type': 'TEXT'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'}
                ],
                'indexes': [
                    {'name': 'idx_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_platform', 'columns': '(platform)'},
                    {'name': 'idx_content_id', 'columns': '(content_id)'},
                    {'name': 'idx_publish_time', 'columns': '(publish_time)'}
                ]
            },
            {
                'name': 'comments',
                'columns': [
                    {'name': 'id', 'type': 'BIGINT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'content_id', 'type': 'VARCHAR(100) NOT NULL'},
                    {'name': 'comment_id', 'type': 'VARCHAR(100) NOT NULL'},
                    {'name': 'platform', 'type': 'VARCHAR(20) NOT NULL'},
                    {'name': 'content', 'type': 'TEXT'},
                    {'name': 'author', 'type': 'VARCHAR(100)'},
                    {'name': 'author_id', 'type': 'VARCHAR(100)'},
                    {'name': 'publish_time', 'type': 'DATETIME'},
                    {'name': 'likes', 'type': 'INT DEFAULT 0'},
                    {'name': 'parent_id', 'type': 'VARCHAR(100)'},
                    {'name': 'created_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'}
                ],
                'indexes': [
                    {'name': 'idx_content_id', 'columns': '(content_id)'},
                    {'name': 'idx_platform', 'columns': '(platform)'},
                    {'name': 'idx_comment_id', 'columns': '(comment_id)'}
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
            # 小红书表
            {
                'name': 'xhs_note',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'note_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "笔记ID"'},
                    {'name': 'type', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "笔记类型(normal | video)"'},
                    {'name': 'title', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "笔记标题"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "笔记描述"'},
                    {'name': 'video_url', 'type': 'LONGTEXT COMMENT "视频地址"'},
                    {'name': 'time', 'type': 'BIGINT NOT NULL COMMENT "笔记发布时间戳"'},
                    {'name': 'last_update_time', 'type': 'BIGINT NOT NULL COMMENT "笔记最后更新时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': 'liked_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "笔记点赞数"'},
                    {'name': 'collected_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "笔记收藏数"'},
                    {'name': 'comment_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "笔记评论数"'},
                    {'name': 'share_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "笔记分享数"'},
                    {'name': 'image_list', 'type': 'LONGTEXT COMMENT "笔记封面图片列表"'},
                    {'name': 'tag_list', 'type': 'LONGTEXT COMMENT "标签列表"'},
                    {'name': 'note_url', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "笔记详情页的URL"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'xsec_token', 'type': 'VARCHAR(50) DEFAULT NULL COMMENT "签名算法"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_xhs_note_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_xhs_note_time', 'columns': '(time)'}
                ]
            },
            {
                'name': 'xhs_note_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "评论时间戳"'},
                    {'name': 'note_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "笔记ID"'},
                    {'name': 'content', 'type': 'LONGTEXT NOT NULL COMMENT "评论内容"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': 'sub_comment_count', 'type': 'INT NOT NULL COMMENT "子评论数量"'},
                    {'name': 'pictures', 'type': 'VARCHAR(512) DEFAULT NULL COMMENT "评论图片"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "父评论ID"'},
                    {'name': 'like_count', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "评论点赞数量"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_xhs_note_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_xhs_note_comment_note_id', 'columns': '(note_id)'},
                    {'name': 'idx_xhs_note_comment_create_time', 'columns': '(create_time)'}
                ]
            },
            {
                'name': 'xhs_creator',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "用户描述"'},
                    {'name': 'gender', 'type': 'VARCHAR(1) DEFAULT NULL COMMENT "性别"'},
                    {'name': 'follows', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "关注数"'},
                    {'name': 'fans', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "粉丝数"'},
                    {'name': 'interaction', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "获赞和收藏数"'},
                    {'name': 'tag_list', 'type': 'LONGTEXT COMMENT "标签列表"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ]
            },
            # 抖音表
            {
                'name': 'douyin_aweme',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'aweme_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'aweme_type', 'type': 'VARCHAR(16) NOT NULL COMMENT "视频类型"'},
                    {'name': 'title', 'type': 'VARCHAR(1024) DEFAULT NULL COMMENT "视频标题"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "视频描述"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "视频发布时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'sec_uid', 'type': 'VARCHAR(128) DEFAULT NULL COMMENT "用户sec_uid"'},
                    {'name': 'short_user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户短ID"'},
                    {'name': 'user_unique_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户唯一ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'user_signature', 'type': 'VARCHAR(500) DEFAULT NULL COMMENT "用户签名"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': 'liked_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频点赞数"'},
                    {'name': 'comment_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频评论数"'},
                    {'name': 'share_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频分享数"'},
                    {'name': 'collected_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "视频收藏数"'},
                    {'name': 'aweme_url', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "视频详情页URL"'},
                    {'name': 'cover_url', 'type': 'VARCHAR(500) DEFAULT NULL COMMENT "视频封面图URL"'},
                    {'name': 'video_download_url', 'type': 'VARCHAR(1024) DEFAULT NULL COMMENT "视频下载地址"'},
                    {'name': 'video_play_url', 'type': 'VARCHAR(1024) DEFAULT NULL COMMENT "视频播放地址"'},
                    {'name': 'video_share_url', 'type': 'VARCHAR(1024) DEFAULT NULL COMMENT "视频分享地址"'},
                    {'name': 'is_favorite', 'type': 'BOOLEAN DEFAULT FALSE COMMENT "是否收藏"'},
                    {'name': 'minio_url', 'type': 'VARCHAR(1024) DEFAULT NULL COMMENT "MinIO存储地址"'},
                    {'name': 'task_id', 'type': 'VARCHAR(36) DEFAULT NULL COMMENT "关联任务ID"'},
                    {'name': 'source_keyword', 'type': 'VARCHAR(255) DEFAULT "" COMMENT "搜索来源关键字"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_douyin_aweme_aweme_id', 'columns': '(aweme_id)'},
                    {'name': 'idx_douyin_aweme_create_time', 'columns': '(create_time)'},
                    {'name': 'idx_douyin_aweme_task_id', 'columns': '(task_id)'},
                    {'name': 'idx_douyin_aweme_is_favorite', 'columns': '(is_favorite)'}
                ]
            },
            {
                'name': 'douyin_aweme_comment',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'comment_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "评论ID"'},
                    {'name': 'aweme_id', 'type': 'VARCHAR(64) NOT NULL COMMENT "视频ID"'},
                    {'name': 'content', 'type': 'LONGTEXT COMMENT "评论内容"'},
                    {'name': 'create_time', 'type': 'BIGINT NOT NULL COMMENT "评论时间戳"'},
                    {'name': 'user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户ID"'},
                    {'name': 'sec_uid', 'type': 'VARCHAR(128) DEFAULT NULL COMMENT "用户sec_uid"'},
                    {'name': 'short_user_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户短ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': 'sub_comment_count', 'type': 'VARCHAR(16) NOT NULL COMMENT "评论回复数"'},
                    {'name': 'parent_comment_id', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "父评论ID"'},
                    {'name': 'like_count', 'type': 'VARCHAR(255) NOT NULL DEFAULT "0" COMMENT "点赞数"'},
                    {'name': 'pictures', 'type': 'VARCHAR(500) NOT NULL DEFAULT "" COMMENT "评论图片列表"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
                ],
                'indexes': [
                    {'name': 'idx_douyin_aweme_comment_comment_id', 'columns': '(comment_id)'},
                    {'name': 'idx_douyin_aweme_comment_aweme_id', 'columns': '(aweme_id)'}
                ]
            },
            {
                'name': 'douyin_creator',
                'columns': [
                    {'name': 'id', 'type': 'INT AUTO_INCREMENT PRIMARY KEY'},
                    {'name': 'user_id', 'type': 'VARCHAR(128) NOT NULL COMMENT "用户ID"'},
                    {'name': 'nickname', 'type': 'VARCHAR(64) DEFAULT NULL COMMENT "用户昵称"'},
                    {'name': 'avatar', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "用户头像地址"'},
                    {'name': 'ip_location', 'type': 'VARCHAR(255) DEFAULT NULL COMMENT "IP地址"'},
                    {'name': '`desc`', 'type': 'LONGTEXT COMMENT "用户描述"'},
                    {'name': 'gender', 'type': 'VARCHAR(1) DEFAULT NULL COMMENT "性别"'},
                    {'name': 'follows', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "关注数"'},
                    {'name': 'fans', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "粉丝数"'},
                    {'name': 'interaction', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "获赞数"'},
                    {'name': 'videos_count', 'type': 'VARCHAR(16) DEFAULT NULL COMMENT "作品数"'},
                    {'name': 'add_ts', 'type': 'BIGINT NOT NULL COMMENT "记录添加时间戳"'},
                    {'name': 'last_modify_ts', 'type': 'BIGINT NOT NULL COMMENT "记录最后修改时间戳"'}
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