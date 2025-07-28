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
        
        # 缓存配置
        self._config_cache = env_config
        
        return env_config
    
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
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": "",
                "connection_pool_size": 5,
                "max_connections": 20,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "socket_keepalive": True,
                "socket_keepalive_options": {},
                "health_check_interval": 30,
                "retry_on_timeout": True,
                "task_result_ttl": 604800,
                "task_result_key_prefix": "mediacrawler:task:",
                "session_ttl": 3600,
                "session_key_prefix": "mediacrawler:session:"
            },
            "app": {
                "debug": True,
                "log_level": "DEBUG",
                "data_dir": "./data",
                "user_data_dir": "./data/user_data"
            },
            "remote_desktop": {
                "enabled": False,
                "vnc_url": "http://localhost:6080/vnc.html",
                "vnc_host": "localhost",
                "vnc_port": 6080,
                "vnc_password": "",
                "display_number": 1,
                "connection_timeout": 5,
                "max_wait_time": 1800,
                "check_interval": 3
            },
            "server": {
                "port": 8000,
                "host": "0.0.0.0",
                "debug": False,
                "enable_cors": True,
                "static_path": "static",
                "max_upload_size": 100
            },
            "security": {
                "enable_https": False,
                "ssl_cert": "",
                "ssl_key": "",
                "session_secret": "default-secret-key",
                "session_expire": 86400,
                "enable_api_auth": False,
                "api_key": "default-api-key"
            },
            "crawler_service": {
                "max_processes": 5,
                "task_timeout": 1800,
                "result_cache_time": 3600,
                "enable_monitoring": True,
                "monitor_interval": 30,
                "cpu_warning_threshold": 80,
                "memory_warning_threshold": 85,
                "disk_warning_threshold": 90
            },
            "task_management": {
                "max_queue_size": 100,
                "max_retry_count": 3,
                "retry_interval": 60,
                "status_check_interval": 10,
                "result_retention_days": 30
            },
            "performance": {
                "enable_cache": True,
                "cache_size_limit": 100,
                "enable_compression": True,
                "enable_async": True,
                "async_queue_size": 50,
                "async_timeout": 300
            },
            "monitoring": {
                "enable_system_monitor": True,
                "data_retention_days": 7,
                "collection_interval": 60,
                "enable_alerts": True,
                "alerts": {
                    "cpu_threshold": 80,
                    "memory_threshold": 85,
                    "disk_threshold": 90,
                    "response_time_threshold": 5000
                }
            },
            "development": {
                "enable_hot_reload": False,
                "enable_debug_toolbar": False,
                "enable_detailed_errors": False,
                "test_mode": False
            },
            "xhs": {
                "search_note_type": "video",
                "xhs_specified_id_list": [],
                "xhs_creator_id_list": []
            },
            "douyin": {
                "publish_time_type": 0,
                "dy_specified_id_list": [],
                "dy_creator_id_list": []
            },
            "kuaishou": {
                "ks_specified_id_list": [],
                "ks_creator_id_list": []
            },
            "bilibili": {
                "all_day": False,
                "start_day": "2024-01-01",
                "end_day": "2024-01-31",
                "bili_specified_id_list": [],
                "bili_creator_id_list": [],
                "creator_mode": False
            },
            "weibo": {
                "weibo_specified_id_list": [],
                "weibo_creator_id_list": []
            },
            "tieba": {
                "tieba_specified_id_list": [],
                "tieba_name_list": [],
                "tieba_creator_url_list": []
            },
            "zhihu": {
                "zhihu_specified_id_list": [],
                "zhihu_creator_url_list": []
            },
            "comments": {
                "max_comments_count_single_notes": 100,
                "max_sub_comments_count_single_notes": 50
            },
            "contacts": {
                "max_contacts_count_single_notes": 100
            },
            "dynamics": {
                "max_dynamics_count_single_notes": 100
            },
            "wordcloud": {
                "enable_get_wordcloud": False,
                "custom_words": {
                    "零几": "年份",
                    "高频词": "专业术语"
                },
                "stop_words_file": "./docs/hit_stopwords.txt",
                "font_path": "./docs/STZHONGS.TTF"
            },
            "ua": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
            "save_login_state": True,
            "cookies": "",
            "account_id": None,
            "start_page": 1,
            "crawler_max_comments_count_singlenotes": 10,
            "sort_type": "popularity_descending",
            "publish_time_type": 0,
            "xhs_specified_note_url_list": [],
            "start_day": '2024-01-01',
            "end_day": '2024-01-01',
            "all_day": False,
            "creator_mode": True,
            "start_contacs_page": 1,
            "crawler_max_contacs_count_singlenotes": 100,
            "crawler_max_dynamics_count_singlenotes": 50
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
    
    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        config = self._config_cache or self.load_config()
        return config.get("redis", {})
    
    def get_remote_desktop_config(self) -> Dict[str, Any]:
        """获取远程桌面配置"""
        config = self._config_cache or self.load_config()
        return config.get("remote_desktop", {})
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        config = self._config_cache or self.load_config()
        return config.get("server", {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        config = self._config_cache or self.load_config()
        return config.get("security", {})
    
    def get_crawler_service_config(self) -> Dict[str, Any]:
        """获取爬虫服务配置"""
        config = self._config_cache or self.load_config()
        return config.get("crawler_service", {})
    
    def get_task_management_config(self) -> Dict[str, Any]:
        """获取任务管理配置"""
        config = self._config_cache or self.load_config()
        return config.get("task_management", {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        config = self._config_cache or self.load_config()
        return config.get("performance", {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        config = self._config_cache or self.load_config()
        return config.get("monitoring", {})
    
    def get_development_config(self) -> Dict[str, Any]:
        """获取开发环境配置"""
        config = self._config_cache or self.load_config()
        return config.get("development", {})
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """获取平台特定配置"""
        config = self._config_cache or self.load_config()
        return config.get(platform, {})
    
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