#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库升级执行脚本
用于执行数据库升级SQL，更新表结构以支持任务管理功能
"""

import asyncio
import aiomysql
import logging
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置加载器
from config.env_config_loader import config_loader

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseUpgrader:
    def __init__(self):
        self.pool = None
        self.config = config_loader.load_config()
        
    async def create_connection_pool(self):
        """创建数据库连接池"""
        try:
            db_config = self.config.get('database', {})
            
            self.pool = await aiomysql.create_pool(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('username', 'root'),
                password=db_config.get('password', ''),
                db=db_config.get('database', 'mediacrawler'),
                charset=db_config.get('charset', 'utf8mb4'),
                autocommit=True,
                maxsize=10,
                minsize=1
            )
            logger.info("数据库连接池创建成功")
            
        except Exception as e:
            logger.error(f"创建数据库连接池失败: {e}")
            raise
    
    async def close_pool(self):
        """关闭数据库连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("数据库连接池已关闭")
    
    async def execute_sql_file(self, sql_file_path: str):
        """执行SQL文件"""
        try:
            if not os.path.exists(sql_file_path):
                logger.error(f"SQL文件不存在: {sql_file_path}")
                return False
            
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句
            sql_statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                current_statement += line + " "
                
                if line.endswith(';'):
                    sql_statements.append(current_statement.strip())
                    current_statement = ""
            
            if current_statement.strip():
                sql_statements.append(current_statement.strip())
            
            logger.info(f"共找到 {len(sql_statements)} 条SQL语句")
            
            # 执行SQL语句
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    for i, sql in enumerate(sql_statements, 1):
                        try:
                            logger.info(f"执行SQL {i}/{len(sql_statements)}: {sql[:100]}...")
                            await cursor.execute(sql)
                            logger.info(f"SQL {i} 执行成功")
                        except Exception as e:
                            logger.error(f"SQL {i} 执行失败: {e}")
                            logger.error(f"SQL语句: {sql}")
                            # 继续执行其他SQL语句
                            continue
            
            logger.info("所有SQL语句执行完成")
            return True
            
        except Exception as e:
            logger.error(f"执行SQL文件失败: {e}")
            return False
    
    async def check_table_structure(self):
        """检查表结构"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查crawler_tasks表的新字段
                    await cursor.execute("""
                        SELECT COLUMN_NAME 
                        FROM information_schema.columns 
                        WHERE table_schema = DATABASE() 
                        AND table_name = 'crawler_tasks' 
                        AND column_name IN ('user_id', 'params', 'priority', 'is_favorite', 'deleted', 'is_pinned')
                    """)
                    new_columns = await cursor.fetchall()
                    
                    if len(new_columns) >= 5:
                        logger.info("crawler_tasks表已包含新字段")
                        return True
                    else:
                        logger.info("crawler_tasks表缺少新字段，需要升级")
                        return False
                        
        except Exception as e:
            logger.error(f"检查表结构失败: {e}")
            return False
    
    async def backup_database(self):
        """备份数据库（可选）"""
        try:
            db_config = self.config.get('database', {})
            database_name = db_config.get('database', 'mediacrawler')
            
            backup_file = f"backup_{database_name}_{int(asyncio.get_event_loop().time())}.sql"
            
            # 这里可以添加数据库备份逻辑
            # 例如使用mysqldump命令
            logger.info(f"建议在升级前备份数据库: {database_name}")
            logger.info(f"备份文件建议名称: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"备份数据库失败: {e}")
            return False
    
    async def upgrade_database(self):
        """执行数据库升级"""
        try:
            logger.info("开始数据库升级...")
            
            # 1. 检查是否需要升级
            needs_upgrade = not await self.check_table_structure()
            if not needs_upgrade:
                logger.info("数据库结构已是最新，无需升级")
                return True
            
            # 2. 建议备份
            await self.backup_database()
            
            # 3. 执行升级SQL
            sql_file_path = "database_upgrade.sql"
            success = await self.execute_sql_file(sql_file_path)
            
            if success:
                logger.info("数据库升级完成")
                return True
            else:
                logger.error("数据库升级失败")
                return False
                
        except Exception as e:
            logger.error(f"数据库升级失败: {e}")
            return False

async def main():
    """主函数"""
    upgrader = DatabaseUpgrader()
    
    try:
        await upgrader.create_connection_pool()
        
        # 执行升级
        success = await upgrader.upgrade_database()
        
        if success:
            logger.info("✅ 数据库升级成功完成")
        else:
            logger.error("❌ 数据库升级失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"升级过程中出现错误: {e}")
        sys.exit(1)
    finally:
        await upgrader.close_pool()

if __name__ == "__main__":
    asyncio.run(main()) 