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
    
    def run_migration(self, migration_type: str = "full", version: str = None) -> bool:
        """Run database migration"""
        if version is None:
            version = self.get_project_version()
        
        self.logger.info(f"Starting {migration_type} migration for version {version}")
        
        if not self.connect_database():
            return False
        
        try:
            migration_files = self.get_migration_files(migration_type, version)
            
            if not migration_files:
                self.logger.error(f"No migration files found for {migration_type}/{version}")
                return False
            
            self.logger.info(f"Found {len(migration_files)} migration files")
            
            for file_path in migration_files:
                self.logger.info(f"Executing migration file: {file_path}")
                if not self.execute_sql_file(file_path):
                    return False
            
            self.logger.info(f"Migration completed successfully for {migration_type}/{version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
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
            
            return {
                'database': database_name,
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
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = DatabaseMigrator(args.config)
    
    if args.get_version:
        # Get current project version
        version = migrator.get_project_version()
        print(f"Current project version: {version}")
        return
    
    if args.check:
        # Check database status
        status = migrator.check_database_status()
        if status:
            print("\n=== Database Status ===")
            print(f"Database: {status['database']}")
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
