#!/usr/bin/env python3
"""
测试creator_ref_ids字段迁移
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_creator_ref_ids_migration():
    """测试creator_ref_ids字段迁移"""
    try:
        from config.env_config_loader import config_loader
        import aiomysql
        
        # 获取数据库配置
        db_config = config_loader.get_database_config()
        
        # 创建数据库连接
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
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                print("🔍 开始测试creator_ref_ids字段...")
                
                # 1. 检查字段是否存在
                print("\n📝 步骤1: 检查字段结构")
                await cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'crawler_tasks' 
                    AND COLUMN_NAME IN ('creator_ref_id', 'creator_ref_ids')
                    ORDER BY COLUMN_NAME
                """, (db_config['database'],))
                
                columns = await cursor.fetchall()
                print("📊 字段信息:")
                for column in columns:
                    print(f"  - {column[0]}: {column[1]} ({column[2]}) - {column[3]}")
                
                # 2. 检查索引
                print("\n📝 步骤2: 检查索引")
                await cursor.execute("""
                    SELECT INDEX_NAME, COLUMN_NAME
                    FROM INFORMATION_SCHEMA.STATISTICS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'crawler_tasks' 
                    AND INDEX_NAME LIKE '%creator_ref%'
                    ORDER BY INDEX_NAME
                """, (db_config['database'],))
                
                indexes = await cursor.fetchall()
                print("📊 索引信息:")
                for index in indexes:
                    print(f"  - {index[0]}: {index[1]}")
                
                # 3. 检查数据
                print("\n📝 步骤3: 检查数据")
                await cursor.execute("""
                    SELECT id, platform, crawler_type, creator_ref_ids, keywords, created_at
                    FROM crawler_tasks 
                    WHERE crawler_type = 'creator' 
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                rows = await cursor.fetchall()
                if rows:
                    print("📊 创作者任务数据:")
                    for row in rows:
                        task_id, platform, crawler_type, creator_ref_ids, keywords, created_at = row
                        print(f"  - 任务ID: {task_id}")
                        print(f"    平台: {platform}")
                        print(f"    类型: {crawler_type}")
                        print(f"    创作者IDs: {creator_ref_ids}")
                        print(f"    关键词: {keywords}")
                        print(f"    创建时间: {created_at}")
                        
                        # 测试JSON解析
                        if creator_ref_ids:
                            try:
                                parsed_ids = json.loads(creator_ref_ids)
                                print(f"    ✅ JSON解析成功: {parsed_ids}")
                                print(f"    创作者数量: {len(parsed_ids)}")
                            except json.JSONDecodeError as e:
                                print(f"    ❌ JSON解析失败: {e}")
                        else:
                            print("    ⚠️ 创作者IDs为空")
                        print()
                else:
                    print("📊 暂无创作者任务数据")
                
                # 4. 测试插入新数据
                print("\n📝 步骤4: 测试插入新数据")
                test_task_id = "test_creator_ref_ids_" + str(int(asyncio.get_event_loop().time()))
                test_creator_ids = ["test_creator_1", "test_creator_2", "test_creator_3"]
                
                try:
                    await cursor.execute("""
                        INSERT INTO crawler_tasks (
                            id, platform, task_type, crawler_type, creator_ref_ids, 
                            keywords, status, progress, result_count, 
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        test_task_id, "ks", "single_platform", "creator", 
                        json.dumps(test_creator_ids), "测试关键词", "completed", 
                        100.0, 0, "2024-01-01 00:00:00", "2024-01-01 00:00:00"
                    ))
                    
                    print(f"✅ 测试数据插入成功: {test_task_id}")
                    
                    # 验证插入的数据
                    await cursor.execute("""
                        SELECT creator_ref_ids FROM crawler_tasks WHERE id = %s
                    """, (test_task_id,))
                    
                    result = await cursor.fetchone()
                    if result:
                        stored_ids = result[0]
                        print(f"📊 存储的数据: {stored_ids}")
                        
                        # 解析并验证
                        parsed_ids = json.loads(stored_ids)
                        print(f"📊 解析后的数据: {parsed_ids}")
                        print(f"📊 数据类型: {type(parsed_ids)}")
                        print(f"📊 数据长度: {len(parsed_ids)}")
                        
                        if parsed_ids == test_creator_ids:
                            print("✅ 数据验证成功！")
                        else:
                            print("❌ 数据验证失败！")
                    
                    # 清理测试数据
                    await cursor.execute("DELETE FROM crawler_tasks WHERE id = %s", (test_task_id,))
                    print("✅ 测试数据清理完成")
                    
                except Exception as e:
                    print(f"❌ 测试数据插入失败: {e}")
                
                print("\n🎉 测试完成！")
                
        pool.close()
        await pool.wait_closed()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🚀 开始测试creator_ref_ids字段迁移")
    
    # 执行测试
    asyncio.run(test_creator_ref_ids_migration())
    
    print("\n🎯 测试说明:")
    print("1. 检查字段结构是否正确")
    print("2. 检查索引是否正确")
    print("3. 检查现有数据")
    print("4. 测试新数据插入和解析")

if __name__ == "__main__":
    main() 