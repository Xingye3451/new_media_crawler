#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为social_accounts表添加password字段
使用方法：python migrate_add_password_field.py
"""

import asyncio
import aiomysql
import os
from config.config_manager import ConfigManager

async def migrate_add_password_field():
    """为social_accounts表添加password字段"""
    print("开始数据库迁移：添加password字段...")
    
    # 设置环境变量（如果没有设置的话）
    if not os.getenv('ENV'):
        os.environ['ENV'] = 'local'
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 获取数据库配置
    db_config = config_manager.get_database_config()
    
    print(f"使用环境: {os.getenv('ENV', 'local')}")
    print(f"数据库连接: {db_config.host}:{db_config.port}/{db_config.database}")
    print(f"用户名: {db_config.username}")
    print(f"密码: {'***' if db_config.password else '(空)'}")
    print("="*50)
    
    try:
        # 创建数据库连接
        connection = await aiomysql.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.username,
            password=db_config.password,
            db=db_config.database,
            charset=db_config.charset,
            autocommit=True
        )
        
        cursor = await connection.cursor()
        
        # 检查password字段是否已存在
        check_query = """
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = 'social_accounts' AND column_name = 'password'
        """
        
        await cursor.execute(check_query, (db_config.database,))
        result = await cursor.fetchone()
        
        if result[0] > 0:
            print("password字段已存在，无需迁移")
            return
        
        # 添加password字段
        alter_query = """
        ALTER TABLE social_accounts 
        ADD COLUMN password VARCHAR(255) COMMENT '密码(加密存储)' 
        AFTER username
        """
        
        await cursor.execute(alter_query)
        print("成功添加password字段")
        
        # 更新login_method字段的注释，包含password选项
        update_comment_query = """
        ALTER TABLE social_accounts 
        MODIFY COLUMN login_method VARCHAR(20) DEFAULT 'qrcode' 
        COMMENT '登录方式(qrcode,phone,email,password)'
        """
        
        await cursor.execute(update_comment_query)
        print("成功更新login_method字段注释")
        
        await cursor.close()
        connection.close()
        
        print("数据库迁移完成！")
        
    except Exception as e:
        print(f"数据库迁移失败: {e}")
        raise

async def main():
    """主函数"""
    await migrate_add_password_field()

if __name__ == "__main__":
    asyncio.run(main()) 