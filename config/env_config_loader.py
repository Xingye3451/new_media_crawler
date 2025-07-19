#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于环境变量的配置加载器
支持读取 config_{ENV}.yaml 格式的配置文件
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class EnvConfigLoader:
    """环境变量配置加载器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
        self._storage_config: Optional[Dict[str, Any]] = None
        
    def get_environment(self) -> str:
        """获取当前环境"""
        return os.getenv("ENV", "local").lower()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        env = self.get_environment()
        config_file = f"config_{env}.yaml"
        config_path = self.config_dir / config_file
        
        # 检查配置文件是否存在
        if not config_path.exists():
            print(f"警告: 配置文件 {config_path} 不存在，使用默认配置")
            return self._get_default_config()
        
        # 加载环境特定配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f)
        except Exception as e:
            print(f"错误: 加载配置文件 {config_path} 失败: {e}")
            return self._get_default_config()
        
        # 加载存储配置（所有环境都需要）
        storage_config = self._load_storage_config()
        
        # 合并配置
        merged_config = self._merge_configs(env_config, storage_config)
        
        # 缓存配置
        self._config_cache = merged_config
        
        return merged_config
    
    def _load_storage_config(self) -> Dict[str, Any]:
        """加载存储配置"""
        storage_config_path = self.config_dir / "config_storage.yaml"
        
        if not storage_config_path.exists():
            print(f"警告: 存储配置文件 {storage_config_path} 不存在，使用默认存储配置")
            return self._get_default_storage_config()
        
        try:
            with open(storage_config_path, 'r', encoding='utf-8') as f:
                storage_config = yaml.safe_load(f)
                self._storage_config = storage_config
                return storage_config
        except Exception as e:
            print(f"错误: 加载存储配置文件失败: {e}")
            return self._get_default_storage_config()
    
    def _merge_configs(self, env_config: Dict[str, Any], storage_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并环境配置和存储配置"""
        merged = {}
        
        # 合并环境配置
        if env_config:
            merged.update(env_config)
        
        # 合并存储配置
        if storage_config:
            merged.update(storage_config)
        
        return merged
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "proxy": {
                "enabled": False,
                "provider_name": "none"
            },
            "crawler": {
                "platform": "xhs",
                "keywords": "编程副业",
                "login_type": "qrcode",
                "crawler_type": "search",
                "max_notes_count": 10,
                "enable_comments": False,
                "enable_sub_comments": False,
                "enable_images": False,
                "save_data_option": "db",
                "headless": False,
                "max_sleep_sec": 3,
                "max_concurrency": 1
            },
            "database": {
                "host": "localhost",
                "port": 3306,
                "username": "root",
                "password": "",
                "database": "mediacrawler",
                "charset": "utf8mb4"
            },
            "app": {
                "debug": True,
                "log_level": "DEBUG",
                "data_dir": "./data",
                "user_data_dir": "./data/user_data"
            }
        }
    
    def _get_default_storage_config(self) -> Dict[str, Any]:
        """获取默认存储配置"""
        return {
            "storage": {
                "local_base_path": "./data",
                "small_file_threshold": 10485760,
                "enable_minio": False,
                "minio_endpoint": "localhost:9000",
                "minio_access_key": "minioadmin",
                "minio_secret_key": "minioadmin",
                "minio_secure": False,
                "minio_bucket": "mediacrawler-videos",
                "database": {
                    "url": "mysql+pymysql://root:password@localhost:3306/mediacrawler",
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600
                },
                "file_management": {
                    "naming_pattern": "{platform}/{date}/{content_id}/{filename}",
                    "date_format": "%Y/%m/%d",
                    "supported_formats": ["mp4", "avi", "mov", "mkv", "flv", "webm", "m4v", "3gp"],
                    "max_file_size": 1073741824,
                    "min_file_size": 1024,
                    "duplicate_check": True,
                    "duplicate_strategy": "skip"
                },
                "performance": {
                    "max_concurrent_downloads": 5,
                    "chunk_size": 8192,
                    "download_timeout": 300,
                    "max_retries": 3,
                    "retry_delay": 5
                },
                "monitoring": {
                    "storage_usage_threshold": 0.8,
                    "file_count_threshold": 10000,
                    "monitor_interval": 3600
                }
            }
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        config = self._config_cache or self.load_config()
        return config.get("database", {})
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """获取代理配置"""
        config = self._config_cache or self.load_config()
        return config.get("proxy", {})
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """获取爬虫配置"""
        config = self._config_cache or self.load_config()
        return config.get("crawler", {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        config = self._config_cache or self.load_config()
        return config.get("storage", {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """获取应用配置"""
        config = self._config_cache or self.load_config()
        return config.get("app", {})
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        config = self._config_cache or self.load_config()
        
        # 支持点号分隔的键路径
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def reload(self):
        """重新加载配置"""
        self._config_cache.clear()
        self._storage_config = None
        return self.load_config()


# 全局配置加载器实例
config_loader = EnvConfigLoader() 