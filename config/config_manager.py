# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:00
# @Desc    : 配置管理器 - 支持多种配置源
import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass, field
from enum import Enum

import logging


class ConfigSource(Enum):
    """配置源类型"""
    ENV = "env"           # 环境变量
    YAML = "yaml"         # YAML配置文件
    JSON = "json"         # JSON配置文件
    DATABASE = "database" # 数据库配置
    MEMORY = "memory"     # 内存配置


@dataclass
class ProxyConfig:
    """代理配置模型"""
    provider_name: str = "kuaidaili"
    enabled: bool = False
    pool_count: int = 5
    validate_ip: bool = True
    
    # 青果代理配置
    qingguo_key: str = ""
    qingguo_pwd: str = ""
    
    # 快代理配置
    kuaidaili_secret_id: str = ""
    kuaidaili_signature: str = ""
    kuaidaili_user_name: str = ""
    kuaidaili_user_pwd: str = ""
    
    # 极速HTTP代理配置
    jisu_http_key: str = ""


@dataclass
class CrawlerConfig:
    """爬虫配置模型"""
    platform: str = "xhs"
    keywords: str = "编程副业,编程兼职"
    login_type: str = "qrcode"
    crawler_type: str = "search"
    max_notes_count: int = 200
    enable_comments: bool = True
    enable_sub_comments: bool = False
    enable_images: bool = False
    save_data_option: str = "db"
    headless: bool = False
    max_sleep_sec: int = 2
    max_concurrency: int = 1


@dataclass
class DatabaseConfig:
    """数据库配置模型"""
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "media_crawler"
    charset: str = "utf8mb4"


@dataclass
class StorageConfig:
    """存储配置模型"""
    # 本地存储配置
    local_base_path: str = "/app/data"
    small_file_threshold: int = 10485760  # 10MB
    
    # MinIO配置
    enable_minio: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "mediacrawler-videos"
    
    # 数据库配置
    database_url: str = "mysql+pymysql://root:password@localhost:3306/mediacrawler"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # 文件管理配置
    naming_pattern: str = "{platform}/{date}/{content_id}/{filename}"
    date_format: str = "%Y/%m/%d"
    supported_formats: list = field(default_factory=lambda: ["mp4", "avi", "mov", "mkv", "flv", "webm", "m4v", "3gp"])
    max_file_size: int = 1073741824  # 1GB
    min_file_size: int = 1024  # 1KB
    duplicate_check: bool = True
    duplicate_strategy: str = "skip"
    
    # 性能优化配置
    max_concurrent_downloads: int = 5
    chunk_size: int = 8192
    download_timeout: int = 300
    max_retries: int = 3
    retry_delay: int = 5


@dataclass
class RemoteDesktopConfig:
    """远程桌面配置模型"""
    enabled: bool = True
    vnc_url: str = "http://localhost:6080/vnc.html"
    vnc_host: str = "localhost"
    vnc_port: int = 6080
    vnc_password: str = ""
    display_number: int = 1
    connection_timeout: int = 5
    max_wait_time: int = 1800  # 30分钟
    check_interval: int = 3    # 3秒检查一次


@dataclass
class AppConfig:
    """应用配置模型"""
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = "./data"
    user_data_dir: str = "%s_user_data_dir"


@dataclass
class RedisConfig:
    """Redis配置模型"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    connection_pool_size: int = 10
    max_connections: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: dict = field(default_factory=dict)
    health_check_interval: int = 30
    retry_on_timeout: bool = True
    
    # 任务结果缓存配置
    task_result_ttl: int = 604800  # 7天过期时间
    task_result_key_prefix: str = "mediacrawler:task:"
    
    # 会话缓存配置
    session_ttl: int = 3600  # 1小时过期时间
    session_key_prefix: str = "mediacrawler:session:"


@dataclass
class ServerConfig:
    """服务器配置模型"""
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = False
    enable_cors: bool = True
    static_path: str = "static"
    max_upload_size: int = 100  # MB

@dataclass
class SecurityConfig:
    """安全配置模型"""
    enable_https: bool = False
    ssl_cert: str = ""
    ssl_key: str = ""
    session_secret: str = "your-secret-key-here"
    session_expire: int = 86400
    enable_api_auth: bool = False
    api_key: str = "your-api-key-here"

@dataclass
class CrawlerServiceConfig:
    """爬虫服务配置模型"""
    max_processes: int = 5
    task_timeout: int = 1800
    result_cache_time: int = 3600
    enable_monitoring: bool = True
    monitor_interval: int = 30
    cpu_warning_threshold: int = 80
    memory_warning_threshold: int = 85
    disk_warning_threshold: int = 90

@dataclass
class TaskManagementConfig:
    """任务管理配置模型"""
    max_queue_size: int = 100
    max_retry_count: int = 3
    retry_interval: int = 60
    status_check_interval: int = 10
    result_retention_days: int = 30

@dataclass
class PerformanceConfig:
    """性能优化配置模型"""
    enable_cache: bool = True
    cache_size_limit: int = 100
    enable_compression: bool = True
    enable_async: bool = True
    async_queue_size: int = 50
    async_timeout: int = 300

@dataclass
class MonitoringConfig:
    """监控配置模型"""
    enable_system_monitor: bool = True
    data_retention_days: int = 7
    collection_interval: int = 60
    enable_alerts: bool = True
    
    @dataclass
    class AlertsConfig:
        cpu_threshold: int = 80
        memory_threshold: int = 85
        disk_threshold: int = 90
        response_time_threshold: int = 5000
    
    alerts: AlertsConfig = field(default_factory=AlertsConfig)

@dataclass
class DevelopmentConfig:
    """开发环境配置模型"""
    enable_hot_reload: bool = False
    enable_debug_toolbar: bool = False
    enable_detailed_errors: bool = False
    test_mode: bool = False


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._proxy_config: Optional[ProxyConfig] = None
        self._crawler_config: Optional[CrawlerConfig] = None
        self._database_config: Optional[DatabaseConfig] = None
        self._storage_config: Optional[StorageConfig] = None
        self._app_config: Optional[AppConfig] = None
        self._remote_desktop_config: Optional[RemoteDesktopConfig] = None
        self._redis_config: Optional[RedisConfig] = None
        
        # 配置优先级（从高到低）
        self.config_priority = [
            ConfigSource.ENV,
            ConfigSource.YAML,
            ConfigSource.JSON,
            ConfigSource.DATABASE,
            ConfigSource.MEMORY
        ]
        
        # 初始化配置
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 1. 加载环境变量配置
        self._load_env_config()
        
        # 2. 加载YAML配置文件
        self._load_yaml_config()
        
        # 3. 加载JSON配置文件
        self._load_json_config()
        
        # 4. 初始化配置对象
        self._init_config_objects()
    
    def _load_env_config(self):
        """从环境变量加载配置"""
        env_config = {}
        
        # 代理配置
        env_config.update({
            "proxy.provider_name": os.getenv("PROXY_PROVIDER_NAME", "kuaidaili"),
            "proxy.enabled": os.getenv("ENABLE_IP_PROXY", "false").lower() == "true",
            "proxy.pool_count": int(os.getenv("IP_PROXY_POOL_COUNT", "5")),
            "proxy.validate_ip": os.getenv("PROXY_VALIDATE_IP", "true").lower() == "true",
            
            # 青果代理
            "proxy.qingguo_key": os.getenv("qg_key", ""),
            "proxy.qingguo_pwd": os.getenv("qg_pwd", ""),
            
            # 快代理
            "proxy.kuaidaili_secret_id": os.getenv("kdl_secret_id", ""),
            "proxy.kuaidaili_signature": os.getenv("kdl_signature", ""),
            "proxy.kuaidaili_user_name": os.getenv("kdl_user_name", ""),
            "proxy.kuaidaili_user_pwd": os.getenv("kdl_user_pwd", ""),
            
            # 极速HTTP代理
            "proxy.jisu_http_key": os.getenv("jisu_http_key", ""),
        })
        
        # 远程桌面配置
        env_config.update({
            "remote_desktop.enabled": os.getenv("REMOTE_DESKTOP_ENABLED", "true").lower() == "true",
            "remote_desktop.vnc_url": os.getenv("VNC_URL", "http://localhost:6080/vnc.html"),
            "remote_desktop.vnc_host": os.getenv("VNC_HOST", "localhost"),
            "remote_desktop.vnc_port": int(os.getenv("VNC_PORT", "6080")),
            "remote_desktop.vnc_password": os.getenv("VNC_PASSWORD", ""),
            "remote_desktop.display_number": int(os.getenv("DISPLAY_NUMBER", "1")),
            "remote_desktop.connection_timeout": int(os.getenv("VNC_CONNECTION_TIMEOUT", "5")),
            "remote_desktop.max_wait_time": int(os.getenv("VNC_MAX_WAIT_TIME", "1800")),
            "remote_desktop.check_interval": int(os.getenv("VNC_CHECK_INTERVAL", "3")),
        })
        
        # 爬虫配置
        env_config.update({
            "crawler.platform": os.getenv("PLATFORM", "xhs"),
            "crawler.keywords": os.getenv("KEYWORDS", "编程副业,编程兼职"),
            "crawler.login_type": os.getenv("LOGIN_TYPE", "qrcode"),
            "crawler.crawler_type": os.getenv("CRAWLER_TYPE", "search"),
            "crawler.max_notes_count": int(os.getenv("CRAWLER_MAX_NOTES_COUNT", "200")),
            "crawler.enable_comments": os.getenv("ENABLE_GET_COMMENTS", "true").lower() == "true",
            "crawler.enable_sub_comments": os.getenv("ENABLE_GET_SUB_COMMENTS", "false").lower() == "true",
            "crawler.enable_images": os.getenv("ENABLE_GET_IMAGES", "false").lower() == "true",
            "crawler.save_data_option": os.getenv("SAVE_DATA_OPTION", "db"),
            "crawler.headless": os.getenv("HEADLESS", "false").lower() == "true",
            "crawler.max_sleep_sec": int(os.getenv("CRAWLER_MAX_SLEEP_SEC", "2")),
            "crawler.max_concurrency": int(os.getenv("MAX_CONCURRENCY_NUM", "1")),
        })
        
        # 数据库配置
        env_config.update({
            "database.host": os.getenv("DB_HOST", "localhost"),
            "database.port": int(os.getenv("DB_PORT", "3306")),
            "database.username": os.getenv("DB_USERNAME", "root"),
            "database.password": os.getenv("DB_PASSWORD", ""),
            "database.database": os.getenv("DB_DATABASE", "media_crawler"),
            "database.charset": os.getenv("DB_CHARSET", "utf8mb4"),
        })
        
        # Redis配置
        env_config.update({
            "redis.host": os.getenv("REDIS_HOST", "localhost"),
            "redis.port": int(os.getenv("REDIS_PORT", "6379")),
            "redis.db": int(os.getenv("REDIS_DB", "0")),
            "redis.password": os.getenv("REDIS_PASSWORD", ""),
            "redis.connection_pool_size": int(os.getenv("REDIS_CONNECTION_POOL_SIZE", "10")),
            "redis.max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
            "redis.socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            "redis.socket_connect_timeout": int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
            "redis.socket_keepalive": os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true",
            "redis.health_check_interval": int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
            "redis.retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
            "redis.task_result_ttl": int(os.getenv("REDIS_TASK_RESULT_TTL", "604800")),
            "redis.task_result_key_prefix": os.getenv("REDIS_TASK_RESULT_KEY_PREFIX", "mediacrawler:task:"),
            "redis.session_ttl": int(os.getenv("REDIS_SESSION_TTL", "3600")),
            "redis.session_key_prefix": os.getenv("REDIS_SESSION_KEY_PREFIX", "mediacrawler:session:"),
        })
        
        # 存储配置
        env_config.update({
            "storage.local_base_path": os.getenv("STORAGE_LOCAL_BASE_PATH", "/app/data"),
            "storage.small_file_threshold": int(os.getenv("STORAGE_SMALL_FILE_THRESHOLD", "10485760")),
            "storage.enable_minio": os.getenv("STORAGE_ENABLE_MINIO", "false").lower() == "true",
            "storage.minio_endpoint": os.getenv("STORAGE_MINIO_ENDPOINT", "localhost:9000"),
            "storage.minio_access_key": os.getenv("STORAGE_MINIO_ACCESS_KEY", "minioadmin"),
            "storage.minio_secret_key": os.getenv("STORAGE_MINIO_SECRET_KEY", "minioadmin"),
            "storage.minio_secure": os.getenv("STORAGE_MINIO_SECURE", "false").lower() == "true",
            "storage.minio_bucket": os.getenv("STORAGE_MINIO_BUCKET", "mediacrawler-videos"),
            "storage.database_url": os.getenv("STORAGE_DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/mediacrawler"),
            "storage.max_concurrent_downloads": int(os.getenv("STORAGE_MAX_CONCURRENT_DOWNLOADS", "5")),
            "storage.download_timeout": int(os.getenv("STORAGE_DOWNLOAD_TIMEOUT", "300")),
        })
        
        # 应用配置
        env_config.update({
            "app.debug": os.getenv("DEBUG", "false").lower() == "true",
            "app.log_level": os.getenv("LOG_LEVEL", "INFO"),
            "app.data_dir": os.getenv("DATA_DIR", "./data"),
            "app.user_data_dir": os.getenv("USER_DATA_DIR", "%s_user_data_dir"),
        })
        
        self._config_cache.update(env_config)
    
    def _load_yaml_config(self):
        """从YAML配置文件加载配置"""
        # 获取当前环境
        env = os.getenv("ENV", "development")
        yaml_file = self.config_dir / f"config_{env}.yaml"
        
        if yaml_file.exists():
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    self._flatten_dict(yaml_config, self._config_cache)
                    logging.getLogger(__name__).info(f"Loaded YAML config from {yaml_file}")
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load YAML config: {e}")
    
    def _load_json_config(self):
        """从JSON配置文件加载配置"""
        # 获取当前环境
        env = os.getenv("ENV", "development")
        json_file = self.config_dir / f"config_{env}.json"
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                    self._flatten_dict(json_config, self._config_cache)
                    logging.getLogger(__name__).info(f"Loaded JSON config from {json_file}")
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load JSON config: {e}")
    
    def _flatten_dict(self, d: Dict, target: Dict, prefix: str = ""):
        """将嵌套字典扁平化"""
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_dict(value, target, new_key)
            else:
                target[new_key] = value
    
    def _init_config_objects(self):
        """初始化配置对象"""
        # 代理配置
        self._proxy_config = ProxyConfig(
            provider_name=self.get("proxy.provider_name", "kuaidaili"),
            enabled=self.get("proxy.enabled", False),
            pool_count=self.get("proxy.pool_count", 5),
            validate_ip=self.get("proxy.validate_ip", True),
            qingguo_key=self.get("proxy.qingguo_key", ""),
            qingguo_pwd=self.get("proxy.qingguo_pwd", ""),
            kuaidaili_secret_id=self.get("proxy.kuaidaili_secret_id", ""),
            kuaidaili_signature=self.get("proxy.kuaidaili_signature", ""),
            kuaidaili_user_name=self.get("proxy.kuaidaili_user_name", ""),
            kuaidaili_user_pwd=self.get("proxy.kuaidaili_user_pwd", ""),
            jisu_http_key=self.get("proxy.jisu_http_key", ""),
        )
        
        # 爬虫配置
        self._crawler_config = CrawlerConfig(
            platform=self.get("crawler.platform", "xhs"),
            keywords=self.get("crawler.keywords", "编程副业,编程兼职"),
            login_type=self.get("crawler.login_type", "qrcode"),
            crawler_type=self.get("crawler.crawler_type", "search"),
            max_notes_count=self.get("crawler.max_notes_count", 200),
            enable_comments=self.get("crawler.enable_comments", True),
            enable_sub_comments=self.get("crawler.enable_sub_comments", False),
            enable_images=self.get("crawler.enable_images", False),
            save_data_option=self.get("crawler.save_data_option", "db"),
            headless=self.get("crawler.headless", False),
            max_sleep_sec=self.get("crawler.max_sleep_sec", 2),
            max_concurrency=self.get("crawler.max_concurrency", 1),
        )
        
        # 数据库配置
        self._database_config = DatabaseConfig(
            host=self.get("database.host", "localhost"),
            port=self.get("database.port", 3306),
            username=self.get("database.username", "root"),
            password=self.get("database.password", ""),
            database=self.get("database.database", "media_crawler"),
            charset=self.get("database.charset", "utf8mb4"),
        )
        
        # Redis配置
        self._redis_config = RedisConfig(
            host=self.get("redis.host", "localhost"),
            port=self.get("redis.port", 6379),
            db=self.get("redis.db", 0),
            password=self.get("redis.password", ""),
            connection_pool_size=self.get("redis.connection_pool_size", 10),
            max_connections=self.get("redis.max_connections", 100),
            socket_timeout=self.get("redis.socket_timeout", 5),
            socket_connect_timeout=self.get("redis.socket_connect_timeout", 5),
            socket_keepalive=self.get("redis.socket_keepalive", True),
            socket_keepalive_options=self.get("redis.socket_keepalive_options", {}),
            health_check_interval=self.get("redis.health_check_interval", 30),
            retry_on_timeout=self.get("redis.retry_on_timeout", True),
            task_result_ttl=self.get("redis.task_result_ttl", 604800),
            task_result_key_prefix=self.get("redis.task_result_key_prefix", "mediacrawler:task:"),
            session_ttl=self.get("redis.session_ttl", 3600),
            session_key_prefix=self.get("redis.session_key_prefix", "mediacrawler:session:"),
        )
        
        # 存储配置
        self._storage_config = StorageConfig(
            local_base_path=self.get("storage.local_base_path", "/app/data"),
            small_file_threshold=self.get("storage.small_file_threshold", 10485760),
            enable_minio=self.get("storage.enable_minio", False),
            minio_endpoint=self.get("storage.minio_endpoint", "localhost:9000"),
            minio_access_key=self.get("storage.minio_access_key", "minioadmin"),
            minio_secret_key=self.get("storage.minio_secret_key", "minioadmin"),
            minio_secure=self.get("storage.minio_secure", False),
            minio_bucket=self.get("storage.minio_bucket", "mediacrawler-videos"),
            database_url=self.get("storage.database_url", "mysql+pymysql://root:password@localhost:3306/mediacrawler"),
            max_concurrent_downloads=self.get("storage.max_concurrent_downloads", 5),
            download_timeout=self.get("storage.download_timeout", 300),
        )
        
        # 应用配置
        self._app_config = AppConfig(
            debug=self.get("app.debug", False),
            log_level=self.get("app.log_level", "INFO"),
            data_dir=self.get("app.data_dir", "./data"),
            user_data_dir=self.get("app.user_data_dir", "%s_user_data_dir"),
        )
        
        # 远程桌面配置
        self._remote_desktop_config = RemoteDesktopConfig(
            enabled=self.get("remote_desktop.enabled", True),
            vnc_url=self.get("remote_desktop.vnc_url", "http://localhost:6080/vnc.html"),
            vnc_host=self.get("remote_desktop.vnc_host", "localhost"),
            vnc_port=self.get("remote_desktop.vnc_port", 6080),
            vnc_password=self.get("remote_desktop.vnc_password", ""),
            display_number=self.get("remote_desktop.display_number", 1),
            connection_timeout=self.get("remote_desktop.connection_timeout", 5),
            max_wait_time=self.get("remote_desktop.max_wait_time", 1800),
            check_interval=self.get("remote_desktop.check_interval", 3),
        )
        
        # 服务器配置
        self._server_config = ServerConfig(
            port=self.get("server.port", 8000),
            host=self.get("server.host", "0.0.0.0"),
            debug=self.get("server.debug", False),
            enable_cors=self.get("server.enable_cors", True),
            static_path=self.get("server.static_path", "static"),
            max_upload_size=self.get("server.max_upload_size", 100),
        )
        
        # 安全配置
        self._security_config = SecurityConfig(
            enable_https=self.get("security.enable_https", False),
            ssl_cert=self.get("security.ssl_cert", ""),
            ssl_key=self.get("security.ssl_key", ""),
            session_secret=self.get("security.session_secret", "your-secret-key-here"),
            session_expire=self.get("security.session_expire", 86400),
            enable_api_auth=self.get("security.enable_api_auth", False),
            api_key=self.get("security.api_key", "your-api-key-here"),
        )
        
        # 爬虫服务配置
        self._crawler_service_config = CrawlerServiceConfig(
            max_processes=self.get("crawler_service.max_processes", 5),
            task_timeout=self.get("crawler_service.task_timeout", 1800),
            result_cache_time=self.get("crawler_service.result_cache_time", 3600),
            enable_monitoring=self.get("crawler_service.enable_monitoring", True),
            monitor_interval=self.get("crawler_service.monitor_interval", 30),
            cpu_warning_threshold=self.get("crawler_service.cpu_warning_threshold", 80),
            memory_warning_threshold=self.get("crawler_service.memory_warning_threshold", 85),
            disk_warning_threshold=self.get("crawler_service.disk_warning_threshold", 90),
        )
        
        # 任务管理配置
        self._task_management_config = TaskManagementConfig(
            max_queue_size=self.get("task_management.max_queue_size", 100),
            max_retry_count=self.get("task_management.max_retry_count", 3),
            retry_interval=self.get("task_management.retry_interval", 60),
            status_check_interval=self.get("task_management.status_check_interval", 10),
            result_retention_days=self.get("task_management.result_retention_days", 30),
        )
        
        # 性能优化配置
        self._performance_config = PerformanceConfig(
            enable_cache=self.get("performance.enable_cache", True),
            cache_size_limit=self.get("performance.cache_size_limit", 100),
            enable_compression=self.get("performance.enable_compression", True),
            enable_async=self.get("performance.enable_async", True),
            async_queue_size=self.get("performance.async_queue_size", 50),
            async_timeout=self.get("performance.async_timeout", 300),
        )
        
        # 监控配置
        alerts_config = MonitoringConfig.AlertsConfig(
            cpu_threshold=self.get("monitoring.alerts.cpu_threshold", 80),
            memory_threshold=self.get("monitoring.alerts.memory_threshold", 85),
            disk_threshold=self.get("monitoring.alerts.disk_threshold", 90),
            response_time_threshold=self.get("monitoring.alerts.response_time_threshold", 5000),
        )
        
        self._monitoring_config = MonitoringConfig(
            enable_system_monitor=self.get("monitoring.enable_system_monitor", True),
            data_retention_days=self.get("monitoring.data_retention_days", 7),
            collection_interval=self.get("monitoring.collection_interval", 60),
            enable_alerts=self.get("monitoring.enable_alerts", True),
            alerts=alerts_config,
        )
        
        # 开发环境配置
        self._development_config = DevelopmentConfig(
            enable_hot_reload=self.get("development.enable_hot_reload", False),
            enable_debug_toolbar=self.get("development.enable_debug_toolbar", False),
            enable_detailed_errors=self.get("development.enable_detailed_errors", False),
            test_mode=self.get("development.test_mode", False),
        )
    
    def get_proxy_config(self) -> ProxyConfig:
        """获取代理配置"""
        return self._proxy_config
    
    def get_crawler_config(self) -> CrawlerConfig:
        """获取爬虫配置"""
        return self._crawler_config
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self._database_config
    
    def get_redis_config(self) -> RedisConfig:
        """获取Redis配置"""
        return self._redis_config
    
    def get_storage_config(self) -> StorageConfig:
        """获取存储配置"""
        return self._storage_config
    
    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        return self._app_config
    
    def get_remote_desktop_config(self) -> RemoteDesktopConfig:
        """获取远程桌面配置"""
        return self._remote_desktop_config
    
    def get_server_config(self) -> ServerConfig:
        """获取服务器配置"""
        return self._server_config
    
    def get_security_config(self) -> SecurityConfig:
        """获取安全配置"""
        return self._security_config
    
    def get_crawler_service_config(self) -> CrawlerServiceConfig:
        """获取爬虫服务配置"""
        return self._crawler_service_config
    
    def get_task_management_config(self) -> TaskManagementConfig:
        """获取任务管理配置"""
        return self._task_management_config
    
    def get_performance_config(self) -> PerformanceConfig:
        """获取性能优化配置"""
        return self._performance_config
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """获取监控配置"""
        return self._monitoring_config
    
    def get_development_config(self) -> DevelopmentConfig:
        """获取开发环境配置"""
        return self._development_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config_cache.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config_cache[key] = value
    
    def reload(self):
        """重新加载配置"""
        self._config_cache.clear()
        self._load_config()
    
    def export_to_yaml(self, env: str = "development"):
        """导出配置到YAML文件"""
        yaml_file = self.config_dir / f"config_{env}.yaml"
        
        config_dict = {
            "proxy": {
                "provider_name": self._proxy_config.provider_name,
                "enabled": self._proxy_config.enabled,
                "pool_count": self._proxy_config.pool_count,
                "validate_ip": self._proxy_config.validate_ip,
                "qingguo_key": self._proxy_config.qingguo_key,
                "qingguo_pwd": self._proxy_config.qingguo_pwd,
                "kuaidaili_secret_id": self._proxy_config.kuaidaili_secret_id,
                "kuaidaili_signature": self._proxy_config.kuaidaili_signature,
                "kuaidaili_user_name": self._proxy_config.kuaidaili_user_name,
                "kuaidaili_user_pwd": self._proxy_config.kuaidaili_user_pwd,
                "jisu_http_key": self._proxy_config.jisu_http_key,
            },
            "crawler": {
                "platform": self._crawler_config.platform,
                "keywords": self._crawler_config.keywords,
                "login_type": self._crawler_config.login_type,
                "crawler_type": self._crawler_config.crawler_type,
                "max_notes_count": self._crawler_config.max_notes_count,
                "enable_comments": self._crawler_config.enable_comments,
                "enable_sub_comments": self._crawler_config.enable_sub_comments,
                "enable_images": self._crawler_config.enable_images,
                "save_data_option": self._crawler_config.save_data_option,
                "headless": self._crawler_config.headless,
                "max_sleep_sec": self._crawler_config.max_sleep_sec,
                "max_concurrency": self._crawler_config.max_concurrency,
            },
            "database": {
                "host": self._database_config.host,
                "port": self._database_config.port,
                "username": self._database_config.username,
                "password": self._database_config.password,
                "database": self._database_config.database,
                "charset": self._database_config.charset,
            },
            "redis": {
                "host": self._redis_config.host,
                "port": self._redis_config.port,
                "db": self._redis_config.db,
                "password": self._redis_config.password,
                "connection_pool_size": self._redis_config.connection_pool_size,
                "max_connections": self._redis_config.max_connections,
                "socket_timeout": self._redis_config.socket_timeout,
                "socket_connect_timeout": self._redis_config.socket_connect_timeout,
                "socket_keepalive": self._redis_config.socket_keepalive,
                "socket_keepalive_options": self._redis_config.socket_keepalive_options,
                "health_check_interval": self._redis_config.health_check_interval,
                "retry_on_timeout": self._redis_config.retry_on_timeout,
                "task_result_ttl": self._redis_config.task_result_ttl,
                "task_result_key_prefix": self._redis_config.task_result_key_prefix,
                "session_ttl": self._redis_config.session_ttl,
                "session_key_prefix": self._redis_config.session_key_prefix,
            },
            "storage": {
                "local_base_path": self._storage_config.local_base_path,
                "small_file_threshold": self._storage_config.small_file_threshold,
                "enable_minio": self._storage_config.enable_minio,
                "minio_endpoint": self._storage_config.minio_endpoint,
                "minio_access_key": self._storage_config.minio_access_key,
                "minio_secret_key": self._storage_config.minio_secret_key,
                "minio_secure": self._storage_config.minio_secure,
                "minio_bucket": self._storage_config.minio_bucket,
                "database_url": self._storage_config.database_url,
                "max_concurrent_downloads": self._storage_config.max_concurrent_downloads,
                "download_timeout": self._storage_config.download_timeout,
            },
            "app": {
                "debug": self._app_config.debug,
                "log_level": self._app_config.log_level,
                "data_dir": self._app_config.data_dir,
                "user_data_dir": self._app_config.user_data_dir,
            },
            "remote_desktop": {
                "enabled": self._remote_desktop_config.enabled,
                "vnc_url": self._remote_desktop_config.vnc_url,
                "vnc_host": self._remote_desktop_config.vnc_host,
                "vnc_port": self._remote_desktop_config.vnc_port,
                "vnc_password": self._remote_desktop_config.vnc_password,
                "display_number": self._remote_desktop_config.display_number,
                "connection_timeout": self._remote_desktop_config.connection_timeout,
                "max_wait_time": self._remote_desktop_config.max_wait_time,
                "check_interval": self._remote_desktop_config.check_interval,
            },
            "server": {
                "port": self._server_config.port,
                "host": self._server_config.host,
                "debug": self._server_config.debug,
                "enable_cors": self._server_config.enable_cors,
                "static_path": self._server_config.static_path,
                "max_upload_size": self._server_config.max_upload_size,
            },
            "security": {
                "enable_https": self._security_config.enable_https,
                "ssl_cert": self._security_config.ssl_cert,
                "ssl_key": self._security_config.ssl_key,
                "session_secret": self._security_config.session_secret,
                "session_expire": self._security_config.session_expire,
                "enable_api_auth": self._security_config.enable_api_auth,
                "api_key": self._security_config.api_key,
            },
            "crawler_service": {
                "max_processes": self._crawler_service_config.max_processes,
                "task_timeout": self._crawler_service_config.task_timeout,
                "result_cache_time": self._crawler_service_config.result_cache_time,
                "enable_monitoring": self._crawler_service_config.enable_monitoring,
                "monitor_interval": self._crawler_service_config.monitor_interval,
                "cpu_warning_threshold": self._crawler_service_config.cpu_warning_threshold,
                "memory_warning_threshold": self._crawler_service_config.memory_warning_threshold,
                "disk_warning_threshold": self._crawler_service_config.disk_warning_threshold,
            },
            "task_management": {
                "max_queue_size": self._task_management_config.max_queue_size,
                "max_retry_count": self._task_management_config.max_retry_count,
                "retry_interval": self._task_management_config.retry_interval,
                "status_check_interval": self._task_management_config.status_check_interval,
                "result_retention_days": self._task_management_config.result_retention_days,
            },
            "performance": {
                "enable_cache": self._performance_config.enable_cache,
                "cache_size_limit": self._performance_config.cache_size_limit,
                "enable_compression": self._performance_config.enable_compression,
                "enable_async": self._performance_config.enable_async,
                "async_queue_size": self._performance_config.async_queue_size,
                "async_timeout": self._performance_config.async_timeout,
            },
            "monitoring": {
                "enable_system_monitor": self._monitoring_config.enable_system_monitor,
                "data_retention_days": self._monitoring_config.data_retention_days,
                "collection_interval": self._monitoring_config.collection_interval,
                "enable_alerts": self._monitoring_config.enable_alerts,
                "alerts": {
                    "cpu_threshold": self._monitoring_config.alerts.cpu_threshold,
                    "memory_threshold": self._monitoring_config.alerts.memory_threshold,
                    "disk_threshold": self._monitoring_config.alerts.disk_threshold,
                    "response_time_threshold": self._monitoring_config.alerts.response_time_threshold,
                },
            },
            "development": {
                "enable_hot_reload": self._development_config.enable_hot_reload,
                "enable_debug_toolbar": self._development_config.enable_debug_toolbar,
                "enable_detailed_errors": self._development_config.enable_detailed_errors,
                "test_mode": self._development_config.test_mode,
            },
        }
        
        try:
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            utils.logger.info(f"Config exported to {yaml_file}")
        except Exception as e:
            utils.logger.error(f"Failed to export config to YAML: {e}")
    
    def export_to_json(self, env: str = "development"):
        """导出配置到JSON文件"""
        json_file = self.config_dir / f"config_{env}.json"
        
        config_dict = {
            "proxy": {
                "provider_name": self._proxy_config.provider_name,
                "enabled": self._proxy_config.enabled,
                "pool_count": self._proxy_config.pool_count,
                "validate_ip": self._proxy_config.validate_ip,
                "qingguo_key": self._proxy_config.qingguo_key,
                "qingguo_pwd": self._proxy_config.qingguo_pwd,
                "kuaidaili_secret_id": self._proxy_config.kuaidaili_secret_id,
                "kuaidaili_signature": self._proxy_config.kuaidaili_signature,
                "kuaidaili_user_name": self._proxy_config.kuaidaili_user_name,
                "kuaidaili_user_pwd": self._proxy_config.kuaidaili_user_pwd,
                "jisu_http_key": self._proxy_config.jisu_http_key,
            },
            "crawler": {
                "platform": self._crawler_config.platform,
                "keywords": self._crawler_config.keywords,
                "login_type": self._crawler_config.login_type,
                "crawler_type": self._crawler_config.crawler_type,
                "max_notes_count": self._crawler_config.max_notes_count,
                "enable_comments": self._crawler_config.enable_comments,
                "enable_sub_comments": self._crawler_config.enable_sub_comments,
                "enable_images": self._crawler_config.enable_images,
                "save_data_option": self._crawler_config.save_data_option,
                "headless": self._crawler_config.headless,
                "max_sleep_sec": self._crawler_config.max_sleep_sec,
                "max_concurrency": self._crawler_config.max_concurrency,
            },
            "database": {
                "host": self._database_config.host,
                "port": self._database_config.port,
                "username": self._database_config.username,
                "password": self._database_config.password,
                "database": self._database_config.database,
                "charset": self._database_config.charset,
            },
            "redis": {
                "host": self._redis_config.host,
                "port": self._redis_config.port,
                "db": self._redis_config.db,
                "password": self._redis_config.password,
                "connection_pool_size": self._redis_config.connection_pool_size,
                "max_connections": self._redis_config.max_connections,
                "socket_timeout": self._redis_config.socket_timeout,
                "socket_connect_timeout": self._redis_config.socket_connect_timeout,
                "socket_keepalive": self._redis_config.socket_keepalive,
                "socket_keepalive_options": self._redis_config.socket_keepalive_options,
                "health_check_interval": self._redis_config.health_check_interval,
                "retry_on_timeout": self._redis_config.retry_on_timeout,
                "task_result_ttl": self._redis_config.task_result_ttl,
                "task_result_key_prefix": self._redis_config.task_result_key_prefix,
                "session_ttl": self._redis_config.session_ttl,
                "session_key_prefix": self._redis_config.session_key_prefix,
            },
            "storage": {
                "local_base_path": self._storage_config.local_base_path,
                "small_file_threshold": self._storage_config.small_file_threshold,
                "enable_minio": self._storage_config.enable_minio,
                "minio_endpoint": self._storage_config.minio_endpoint,
                "minio_access_key": self._storage_config.minio_access_key,
                "minio_secret_key": self._storage_config.minio_secret_key,
                "minio_secure": self._storage_config.minio_secure,
                "minio_bucket": self._storage_config.minio_bucket,
                "database_url": self._storage_config.database_url,
                "max_concurrent_downloads": self._storage_config.max_concurrent_downloads,
                "download_timeout": self._storage_config.download_timeout,
            },
            "app": {
                "debug": self._app_config.debug,
                "log_level": self._app_config.log_level,
                "data_dir": self._app_config.data_dir,
                "user_data_dir": self._app_config.user_data_dir,
            },
            "remote_desktop": {
                "enabled": self._remote_desktop_config.enabled,
                "vnc_url": self._remote_desktop_config.vnc_url,
                "vnc_host": self._remote_desktop_config.vnc_host,
                "vnc_port": self._remote_desktop_config.vnc_port,
                "vnc_password": self._remote_desktop_config.vnc_password,
                "display_number": self._remote_desktop_config.display_number,
                "connection_timeout": self._remote_desktop_config.connection_timeout,
                "max_wait_time": self._remote_desktop_config.max_wait_time,
                "check_interval": self._remote_desktop_config.check_interval,
            },
            "server": {
                "port": self._server_config.port,
                "host": self._server_config.host,
                "debug": self._server_config.debug,
                "enable_cors": self._server_config.enable_cors,
                "static_path": self._server_config.static_path,
                "max_upload_size": self._server_config.max_upload_size,
            },
            "security": {
                "enable_https": self._security_config.enable_https,
                "ssl_cert": self._security_config.ssl_cert,
                "ssl_key": self._security_config.ssl_key,
                "session_secret": self._security_config.session_secret,
                "session_expire": self._security_config.session_expire,
                "enable_api_auth": self._security_config.enable_api_auth,
                "api_key": self._security_config.api_key,
            },
            "crawler_service": {
                "max_processes": self._crawler_service_config.max_processes,
                "task_timeout": self._crawler_service_config.task_timeout,
                "result_cache_time": self._crawler_service_config.result_cache_time,
                "enable_monitoring": self._crawler_service_config.enable_monitoring,
                "monitor_interval": self._crawler_service_config.monitor_interval,
                "cpu_warning_threshold": self._crawler_service_config.cpu_warning_threshold,
                "memory_warning_threshold": self._crawler_service_config.memory_warning_threshold,
                "disk_warning_threshold": self._crawler_service_config.disk_warning_threshold,
            },
            "task_management": {
                "max_queue_size": self._task_management_config.max_queue_size,
                "max_retry_count": self._task_management_config.max_retry_count,
                "retry_interval": self._task_management_config.retry_interval,
                "status_check_interval": self._task_management_config.status_check_interval,
                "result_retention_days": self._task_management_config.result_retention_days,
            },
            "performance": {
                "enable_cache": self._performance_config.enable_cache,
                "cache_size_limit": self._performance_config.cache_size_limit,
                "enable_compression": self._performance_config.enable_compression,
                "enable_async": self._performance_config.enable_async,
                "async_queue_size": self._performance_config.async_queue_size,
                "async_timeout": self._performance_config.async_timeout,
            },
            "monitoring": {
                "enable_system_monitor": self._monitoring_config.enable_system_monitor,
                "data_retention_days": self._monitoring_config.data_retention_days,
                "collection_interval": self._monitoring_config.collection_interval,
                "enable_alerts": self._monitoring_config.enable_alerts,
                "alerts": {
                    "cpu_threshold": self._monitoring_config.alerts.cpu_threshold,
                    "memory_threshold": self._monitoring_config.alerts.memory_threshold,
                    "disk_threshold": self._monitoring_config.alerts.disk_threshold,
                    "response_time_threshold": self._monitoring_config.alerts.response_time_threshold,
                },
            },
            "development": {
                "enable_hot_reload": self._development_config.enable_hot_reload,
                "enable_debug_toolbar": self._development_config.enable_debug_toolbar,
                "enable_detailed_errors": self._development_config.enable_detailed_errors,
                "test_mode": self._development_config.test_mode,
            },
        }
        
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            utils.logger.info(f"Config exported to {json_file}")
        except Exception as e:
            utils.logger.error(f"Failed to export config to JSON: {e}")


# 全局配置管理器实例
config_manager = ConfigManager() 