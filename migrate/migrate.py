#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler Database Migration Tool
Version: v1.0.0
Description: Database migration tool for MediaCrawler project
"""

import os
import sys
import argparse
import logging
import mysql.connector
from mysql.connector import Error
import yaml
from pathlib import Path
from typing import List, Dict, Optional
import time
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseMigrator:
    """Database migration tool for MediaCrawler"""
    
    def __init__(self, config_path: str = "config/config_local.yaml"):
        """Initialize migrator with configuration"""
        self.config_path = config_path
        self.config = self._load_config()
        self.connection = None
        self.logger = self._setup_logging()
        self.project_root = Path(__file__).parent.parent
        self.version_file = self.project_root / "VERSION"
        self.migration_log_file = self.project_root / "migrate" / "migration_history.json"
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to load config from {self.config_path}: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('migrate.log', encoding='utf-8')
            ]
        )
        return logging.getLogger(__name__)
    
    def get_project_version(self) -> str:
        """Get current project version from VERSION file"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    self.logger.info(f"Current project version: {version}")
                    return version
            else:
                self.logger.warning(f"VERSION file not found at {self.version_file}")
                return "v1.0.0"  # Default version
        except Exception as e:
            self.logger.error(f"Failed to read VERSION file: {e}")
            return "v1.0.0"  # Default version
    
    def update_project_version(self, new_version: str) -> bool:
        """Update project version in VERSION file"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(f"{new_version}\n")
            self.logger.info(f"Updated project version to: {new_version}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update VERSION file: {e}")
            return False
    
    def log_migration(self, migration_type: str, version: str, action: str, status: str, details: Dict = None):
        """记录迁移执行日志"""
        try:
            # 确保日志目录存在
            self.migration_log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有日志
            migration_history = []
            if self.migration_log_file.exists():
                try:
                    with open(self.migration_log_file, 'r', encoding='utf-8') as f:
                        migration_history = json.load(f)
                except Exception:
                    migration_history = []
            
            # 添加新的迁移记录
            migration_record = {
                "timestamp": datetime.now().isoformat(),
                "migration_type": migration_type,
                "version": version,
                "action": action,  # "migrate", "rollback"
                "status": status,  # "success", "failed", "in_progress"
                "details": details or {},
                "config_file": self.config_path
            }
            
            migration_history.append(migration_record)
            
            # 写入日志文件
            with open(self.migration_log_file, 'w', encoding='utf-8') as f:
                json.dump(migration_history, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Migration log recorded: {action} {migration_type} {version} - {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to log migration: {e}")
    
    def get_migration_history(self) -> List[Dict]:
        """获取迁移历史记录"""
        try:
            if self.migration_log_file.exists():
                with open(self.migration_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Failed to read migration history: {e}")
            return []
    
    def get_current_db_version(self) -> str:
        """获取当前数据库版本"""
        try:
            if not self.connect_database():
                return "unknown"
            
            cursor = self.connection.cursor()
            
            # 检查是否存在版本表
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'migration_versions'
            """)
            
            if cursor.fetchone()[0] == 0:
                # 创建版本表
                cursor.execute("""
                    CREATE TABLE migration_versions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        version VARCHAR(50) NOT NULL,
                        migration_type VARCHAR(20) NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'success',
                        details TEXT
                    )
                """)
                self.connection.commit()
                return "v0.0.0"  # 初始版本
            
            # 查询最新版本
            cursor.execute("""
                SELECT version FROM migration_versions 
                WHERE status = 'success' 
                ORDER BY applied_at DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            return result[0] if result else "v0.0.0"
            
        except Exception as e:
            self.logger.error(f"Failed to get current DB version: {e}")
            return "unknown"
        finally:
            self.disconnect_database()
    
    def record_db_version(self, version: str, migration_type: str, status: str = "success", details: str = None):
        """记录数据库版本"""
        try:
            if not self.connect_database():
                return False
            
            cursor = self.connection.cursor()
            
            # 确保版本表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_versions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    migration_type VARCHAR(20) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'success',
                    details TEXT
                )
            """)
            
            # 插入版本记录
            cursor.execute("""
                INSERT INTO migration_versions (version, migration_type, status, details)
                VALUES (%s, %s, %s, %s)
            """, (version, migration_type, status, details))
            
            self.connection.commit()
            self.logger.info(f"Database version recorded: {version} ({migration_type}) - {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record DB version: {e}")
            return False
        finally:
            self.disconnect_database()
    
    def connect_database(self) -> bool:
        """Connect to database"""
        try:
            db_config = self.config.get('database', {})
            self.connection = mysql.connector.connect(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('username', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'mediacrawler'),
                charset=db_config.get('charset', 'utf8mb4'),
                autocommit=False
            )
            self.logger.info("Database connection established successfully")
            return True
        except Error as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect_database(self):
        """Disconnect from database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Database connection closed")
    
    def execute_sql_file(self, file_path: str) -> bool:
        """Execute SQL file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split SQL statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            cursor = self.connection.cursor()
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    try:
                        cursor.execute(statement)
                        self.logger.info(f"Executed statement {i}/{len(statements)}")
                    except Error as e:
                        self.logger.error(f"Failed to execute statement {i}: {e}")
                        self.connection.rollback()
                        return False
            
            self.connection.commit()
            self.logger.info(f"Successfully executed SQL file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute SQL file {file_path}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_migration_files(self, migration_type: str, version: str) -> List[str]:
        """Get migration files for specified type and version"""
        base_path = Path(__file__).parent
        migration_path = base_path / migration_type / "ddl" / version
        
        if not migration_path.exists():
            self.logger.warning(f"Migration path does not exist: {migration_path}")
            return []
        
        # Get all SQL files sorted by name
        sql_files = sorted([f for f in migration_path.glob("*.sql")])
        return [str(f) for f in sql_files]
    
    def get_rollback_files(self, version: str) -> List[str]:
        """Get rollback files for specified version"""
        base_path = Path(__file__).parent
        rollback_path = base_path / "rollback" / "ddl" / version
        
        if not rollback_path.exists():
            self.logger.warning(f"Rollback path does not exist: {rollback_path}")
            return []
        
        # Get all SQL files sorted by name (reverse order for rollback)
        sql_files = sorted([f for f in rollback_path.glob("*.sql")], reverse=True)
        return [str(f) for f in sql_files]
    
    def run_migration(self, migration_type: str = "full", version: str = None) -> bool:
        """Run database migration"""
        if version is None:
            version = self.get_project_version()
        
        self.logger.info(f"Starting {migration_type} migration for version {version}")
        
        # 记录迁移开始
        self.log_migration(migration_type, version, "migrate", "in_progress", {
            "start_time": datetime.now().isoformat()
        })
        
        if not self.connect_database():
            self.log_migration(migration_type, version, "migrate", "failed", {
                "error": "Database connection failed"
            })
            return False
        
        try:
            migration_files = self.get_migration_files(migration_type, version)
            
            if not migration_files:
                error_msg = f"No migration files found for {migration_type}/{version}"
                self.logger.error(error_msg)
                self.log_migration(migration_type, version, "migrate", "failed", {
                    "error": error_msg
                })
                return False
            
            self.logger.info(f"Found {len(migration_files)} migration files")
            
            start_time = time.time()
            
            for file_path in migration_files:
                self.logger.info(f"Executing migration file: {file_path}")
                if not self.execute_sql_file(file_path):
                    error_msg = f"Failed to execute migration file: {file_path}"
                    self.log_migration(migration_type, version, "migrate", "failed", {
                        "error": error_msg,
                        "failed_file": file_path
                    })
                    return False
            
            # 记录数据库版本
            self.record_db_version(version, migration_type, "success")
            
            # 记录迁移成功
            execution_time = time.time() - start_time
            self.log_migration(migration_type, version, "migrate", "success", {
                "execution_time": execution_time,
                "files_executed": len(migration_files)
            })
            
            self.logger.info(f"Migration completed successfully for {migration_type}/{version}")
            return True
            
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            self.logger.error(error_msg)
            self.log_migration(migration_type, version, "migrate", "failed", {
                "error": error_msg
            })
            return False
        finally:
            self.disconnect_database()
    
    def rollback_migration(self, target_version: str) -> bool:
        """Rollback migration to specified version"""
        current_version = self.get_current_db_version()
        
        self.logger.info(f"Starting rollback from {current_version} to {target_version}")
        
        # 记录回滚开始
        self.log_migration("rollback", target_version, "rollback", "in_progress", {
            "from_version": current_version,
            "to_version": target_version,
            "start_time": datetime.now().isoformat()
        })
        
        if not self.connect_database():
            self.log_migration("rollback", target_version, "rollback", "failed", {
                "error": "Database connection failed"
            })
            return False
        
        try:
            rollback_files = self.get_rollback_files(target_version)
            
            if not rollback_files:
                error_msg = f"No rollback files found for version {target_version}"
                self.logger.error(error_msg)
                self.log_migration("rollback", target_version, "rollback", "failed", {
                    "error": error_msg
                })
                return False
            
            self.logger.info(f"Found {len(rollback_files)} rollback files")
            
            start_time = time.time()
            
            for file_path in rollback_files:
                self.logger.info(f"Executing rollback file: {file_path}")
                if not self.execute_sql_file(file_path):
                    error_msg = f"Failed to execute rollback file: {file_path}"
                    self.log_migration("rollback", target_version, "rollback", "failed", {
                        "error": error_msg,
                        "failed_file": file_path
                    })
                    return False
            
            # 记录数据库版本
            self.record_db_version(target_version, "rollback", "success")
            
            # 记录回滚成功
            execution_time = time.time() - start_time
            self.log_migration("rollback", target_version, "rollback", "success", {
                "from_version": current_version,
                "to_version": target_version,
                "execution_time": execution_time,
                "files_executed": len(rollback_files)
            })
            
            self.logger.info(f"Rollback completed successfully to {target_version}")
            return True
            
        except Exception as e:
            error_msg = f"Rollback failed: {e}"
            self.logger.error(error_msg)
            self.log_migration("rollback", target_version, "rollback", "failed", {
                "error": error_msg
            })
            return False
        finally:
            self.disconnect_database()
    
    def check_database_status(self) -> Dict:
        """Check database status and table information"""
        if not self.connect_database():
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Get database information
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]
            
            # Get table count
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            # Get table details
            table_info = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = cursor.fetchone()[0]
                table_info[table_name] = row_count
            
            # Get current version
            current_version = self.get_current_db_version()
            
            return {
                'database': database_name,
                'current_version': current_version,
                'table_count': table_count,
                'tables': table_info
            }
            
        except Error as e:
            self.logger.error(f"Failed to check database status: {e}")
            return {}
        finally:
            self.disconnect_database()
    
    def backup_database(self, backup_path: str) -> bool:
        """Backup database before migration"""
        try:
            db_config = self.config.get('database', {})
            backup_file = f"{backup_path}/backup_{int(time.time())}.sql"
            
            # Create backup directory if not exists
            os.makedirs(backup_path, exist_ok=True)
            
            # Use mysqldump for backup
            import subprocess
            cmd = [
                'mysqldump',
                f'--host={db_config.get("host", "localhost")}',
                f'--port={db_config.get("port", 3306)}',
                f'--user={db_config.get("username", "root")}',
                f'--password={db_config.get("password", "")}',
                '--single-transaction',
                '--routines',
                '--triggers',
                db_config.get('database', 'mediacrawler')
            ]
            
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            self.logger.info(f"Database backup created: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {e}")
            return False
    
    def validate_migration_files(self, migration_type: str, version: str) -> bool:
        """Validate migration files exist and are properly formatted"""
        try:
            migration_files = self.get_migration_files(migration_type, version)
            
            if not migration_files:
                self.logger.error(f"No migration files found for {migration_type}/{version}")
                return False
            
            for file_path in migration_files:
                if not os.path.exists(file_path):
                    self.logger.error(f"Migration file not found: {file_path}")
                    return False
                
                # Check if file is readable and contains valid SQL
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not content.strip():
                            self.logger.warning(f"Empty migration file: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to read migration file {file_path}: {e}")
                    return False
            
            self.logger.info(f"Migration files validation passed for {migration_type}/{version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration files validation failed: {e}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MediaCrawler Database Migration Tool')
    parser.add_argument('--config', default='config/config_local.yaml', help='Configuration file path')
    parser.add_argument('--type', choices=['full', 'incremental'], default='full', help='Migration type')
    parser.add_argument('--version', help='Migration version (default: read from VERSION file)')
    parser.add_argument('--backup', action='store_true', help='Create backup before migration')
    parser.add_argument('--backup-path', default='./backups', help='Backup directory path')
    parser.add_argument('--check', action='store_true', help='Check database status')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (show what would be executed)')
    parser.add_argument('--validate', action='store_true', help='Validate migration files')
    parser.add_argument('--get-version', action='store_true', help='Get current project version')
    parser.add_argument('--rollback', help='Rollback to specified version')
    parser.add_argument('--history', action='store_true', help='Show migration history')
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = DatabaseMigrator(args.config)
    
    if args.get_version:
        # Get current project version
        version = migrator.get_project_version()
        print(f"Current project version: {version}")
        return
    
    if args.history:
        # Show migration history
        history = migrator.get_migration_history()
        print("\n=== Migration History ===")
        for record in history[-10:]:  # Show last 10 records
            print(f"{record['timestamp']} - {record['action']} {record['migration_type']} {record['version']} - {record['status']}")
        return
    
    if args.check:
        # Check database status
        status = migrator.check_database_status()
        if status:
            print("\n=== Database Status ===")
            print(f"Database: {status['database']}")
            print(f"Current Version: {status['current_version']}")
            print(f"Table Count: {status['table_count']}")
            print("\n=== Table Information ===")
            for table, count in status['tables'].items():
                print(f"{table}: {count} rows")
        else:
            print("Failed to check database status")
        return
    
    if args.validate:
        # Validate migration files
        version = args.version or migrator.get_project_version()
        if migrator.validate_migration_files(args.type, version):
            print(f"✅ Migration files validation passed for {args.type}/{version}")
        else:
            print(f"❌ Migration files validation failed for {args.type}/{version}")
            sys.exit(1)
        return
    
    if args.rollback:
        # Rollback migration
        success = migrator.rollback_migration(args.rollback)
        if success:
            print(f"\n✅ Rollback completed successfully to {args.rollback}!")
        else:
            print(f"\n❌ Rollback failed!")
            sys.exit(1)
        return
    
    if args.dry_run:
        # Show migration files that would be executed
        version = args.version or migrator.get_project_version()
        migration_files = migrator.get_migration_files(args.type, version)
        print(f"\n=== Dry Run: {args.type} migration for version {version} ===")
        for file_path in migration_files:
            print(f"Would execute: {file_path}")
        return
    
    # Create backup if requested
    if args.backup:
        if not migrator.backup_database(args.backup_path):
            print("Failed to create backup. Aborting migration.")
            return
    
    # Run migration
    success = migrator.run_migration(args.type, args.version)
    
    if success:
        print(f"\n✅ Migration completed successfully!")
        print(f"Type: {args.type}")
        print(f"Version: {args.version or migrator.get_project_version()}")
    else:
        print(f"\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
