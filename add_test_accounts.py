#!/usr/bin/env python3
"""
添加测试账号数据脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.env_config_loader import config_loader
from async_db import AsyncMysqlDB
import aiomysql
import utils

async def add_test_accounts():
    """添加测试账号数据"""
    try:
        # 获取数据库配置
        db_config = config_loader.get_database_config()
        
        # 创建数据库连接池
        pool = await aiomysql.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            db=db_config['database'],
            autocommit=True,
            minsize=1,
            maxsize=10,
        )
        
        async_db = AsyncMysqlDB(pool)
        
        # 测试账号数据
        test_accounts = [
            {
                'platform': 'xhs',
                'account_name': '测试小红书账号',
                'account_id': 'test_xhs_001',
                'username': 'test_xhs_user',
                'phone': '13800138001',
                'email': 'test_xhs@example.com',
                'is_active': True,
                'login_method': 'qrcode',
                'notes': '测试用小红书账号'
            },
            {
                'platform': 'dy',
                'account_name': '测试抖音账号',
                'account_id': 'test_dy_001',
                'username': 'test_dy_user',
                'phone': '13800138002',
                'email': 'test_dy@example.com',
                'is_active': True,
                'login_method': 'qrcode',
                'notes': '测试用抖音账号'
            },
            {
                'platform': 'ks',
                'account_name': '测试快手账号',
                'account_id': 'test_ks_001',
                'username': 'test_ks_user',
                'phone': '13800138003',
                'email': 'test_ks@example.com',
                'is_active': True,
                'login_method': 'qrcode',
                'notes': '测试用快手账号'
            },
            {
                'platform': 'bili',
                'account_name': '测试B站账号',
                'account_id': 'test_bili_001',
                'username': 'test_bili_user',
                'phone': '13800138004',
                'email': 'test_bili@example.com',
                'is_active': True,
                'login_method': 'qrcode',
                'notes': '测试用B站账号'
            }
        ]
        
        # 检查是否已有账号
        check_query = "SELECT COUNT(*) as count FROM social_accounts"
        result = await async_db.get_first(check_query)
        existing_count = result['count'] if result else 0
        
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个账号，跳过添加测试账号")
            return
        
        # 添加测试账号
        for account in test_accounts:
            insert_query = """
            INSERT INTO social_accounts 
            (platform, account_name, account_id, username, phone, email, is_active, login_method, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            await async_db.execute(insert_query,
                account['platform'], account['account_name'], account['account_id'],
                account['username'], account['phone'], account['email'],
                1 if account['is_active'] else 0, account['login_method'], account['notes']
            )
            
            print(f"✅ 已添加 {account['platform']} 平台测试账号: {account['account_name']}")
        
        print("🎉 所有测试账号添加完成！")
        
        # 关闭连接池
        pool.close()
        await pool.wait_closed()
        
    except Exception as e:
        print(f"❌ 添加测试账号失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_test_accounts()) 