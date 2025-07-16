#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库权限检查脚本
用于诊断数据库连接和权限问题
"""

import asyncio
import aiomysql
import yaml
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_config(config_file="config/config_local.yaml"):
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return None

async def check_database_permissions():
    """检查数据库权限"""
    config = load_config()
    if not config:
        return
    
    db_config = config['database']
    print(f"=== 数据库权限检查 ===")
    print(f"主机: {db_config['host']}")
    print(f"端口: {db_config['port']}")
    print(f"用户: {db_config['username']}")
    print(f"数据库: {db_config['database']}")
    print()
    
    try:
        # 1. 测试基本连接（不指定数据库）
        print("1. 测试基本连接...")
        pool = await aiomysql.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            charset=db_config['charset'],
            autocommit=True,
            maxsize=1,
            minsize=1
        )
        print("✅ 基本连接成功")
        
        # 2. 检查用户权限
        print("\n2. 检查用户权限...")
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW GRANTS")
                grants = await cursor.fetchall()
                print("当前用户权限:")
                for grant in grants:
                    print(f"  {grant[0]}")
        
        # 3. 检查数据库是否存在
        print(f"\n3. 检查数据库 {db_config['database']} 是否存在...")
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW DATABASES")
                databases = await cursor.fetchall()
                db_names = [db[0] for db in databases]
                
                if db_config['database'] in db_names:
                    print(f"✅ 数据库 {db_config['database']} 存在")
                else:
                    print(f"❌ 数据库 {db_config['database']} 不存在")
                    print("可用的数据库:")
                    for db in db_names:
                        print(f"  - {db}")
        
        # 4. 尝试创建数据库（如果不存在）
        if db_config['database'] not in db_names:
            print(f"\n4. 尝试创建数据库 {db_config['database']}...")
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(f"CREATE DATABASE `{db_config['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                        print(f"✅ 数据库 {db_config['database']} 创建成功")
            except Exception as e:
                print(f"❌ 创建数据库失败: {e}")
                print("需要管理员权限来创建数据库")
        
        # 5. 测试连接到指定数据库
        print(f"\n5. 测试连接到数据库 {db_config['database']}...")
        try:
            # 关闭之前的连接池
            pool.close()
            await pool.wait_closed()
            
            # 创建新的连接池，指定数据库
            pool = await aiomysql.create_pool(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['username'],
                password=db_config['password'],
                db=db_config['database'],
                charset=db_config['charset'],
                autocommit=True,
                maxsize=1,
                minsize=1
            )
            print(f"✅ 成功连接到数据库 {db_config['database']}")
            
            # 6. 测试创建表权限
            print("\n6. 测试创建表权限...")
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 尝试创建一个测试表
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS test_permissions (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            test_field VARCHAR(50)
                        )
                    """)
                    print("✅ 创建表权限正常")
                    
                    # 删除测试表
                    await cursor.execute("DROP TABLE IF EXISTS test_permissions")
                    print("✅ 删除表权限正常")
            
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")
            print("\n可能的解决方案:")
            print("1. 确保数据库存在")
            print("2. 确保用户有访问该数据库的权限")
            print("3. 联系数据库管理员授予权限")
        
        # 关闭连接池
        pool.close()
        await pool.wait_closed()
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("\n可能的解决方案:")
        print("1. 检查数据库服务是否启动")
        print("2. 检查主机地址和端口是否正确")
        print("3. 检查用户名和密码是否正确")
        print("4. 检查网络连接")

async def main():
    """主函数"""
    await check_database_permissions()

if __name__ == "__main__":
    asyncio.run(main()) 