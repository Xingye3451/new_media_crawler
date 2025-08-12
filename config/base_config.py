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
# @Desc    : 基础配置文件 - 使用新的配置管理器

# 导入配置管理器
from .config_manager import config_manager

# 获取配置对象
crawler_config = config_manager.get_crawler_config()
database_config = config_manager.get_database_config()
app_config = config_manager.get_app_config()
redis_config = config_manager.get_redis_config()
remote_desktop_config = config_manager.get_remote_desktop_config()
server_config = config_manager.get_server_config()
security_config = config_manager.get_security_config()
crawler_service_config = config_manager.get_crawler_service_config()
task_management_config = config_manager.get_task_management_config()
performance_config = config_manager.get_performance_config()
monitoring_config = config_manager.get_monitoring_config()
development_config = config_manager.get_development_config()

# 获取定时任务配置
scheduled_tasks_config = config_manager.get("scheduled_tasks", {})
login_status_check_config = scheduled_tasks_config.get("login_status_check", {})
scheduler_config = scheduled_tasks_config.get("scheduler", {})

# ==================== 代理配置 ====================
# 代理配置现在从数据库获取，这里保留默认值
# 是否开启 IP 代理
ENABLE_IP_PROXY = True  # 默认启用代理

# 代理IP池数量
IP_PROXY_POOL_COUNT = 10  # 默认代理池大小

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "qingguo"  # 默认提供商

# 代理IP验证
PROXY_VALIDATE_IP = True  # 默认验证IP

# ==================== 爬虫配置 ====================
# 基础配置
PLATFORM = crawler_config.platform
KEYWORDS = crawler_config.keywords
LOGIN_TYPE = crawler_config.login_type
CRAWLER_TYPE = crawler_config.crawler_type

# 爬取控制
CRAWLER_MAX_NOTES_COUNT = crawler_config.max_notes_count
ENABLE_GET_COMMENTS = crawler_config.enable_comments
ENABLE_GET_SUB_COMMENTS = crawler_config.enable_sub_comments
ENABLE_GET_IMAGES = crawler_config.enable_images
SAVE_DATA_OPTION = crawler_config.save_data_option

# 浏览器配置
HEADLESS = crawler_config.headless
CRAWLER_MAX_SLEEP_SEC = crawler_config.max_sleep_sec
MAX_CONCURRENCY_NUM = crawler_config.max_concurrency

# ==================== 应用配置 ====================
# 调试模式
DEBUG = app_config.debug
LOG_LEVEL = app_config.log_level

# 数据目录
DATA_DIR = app_config.data_dir
USER_DATA_DIR = app_config.user_data_dir

# ==================== 数据库配置 ====================
# 数据库连接配置
DB_HOST = database_config.host
DB_PORT = database_config.port
DB_USERNAME = database_config.username
DB_PASSWORD = database_config.password
DB_DATABASE = database_config.database
DB_CHARSET = database_config.charset

# ==================== Redis配置 ====================
# Redis连接配置
REDIS_HOST = redis_config.host
REDIS_PORT = redis_config.port
REDIS_DB = redis_config.db
REDIS_PASSWORD = redis_config.password
REDIS_CONNECTION_POOL_SIZE = redis_config.connection_pool_size
REDIS_MAX_CONNECTIONS = redis_config.max_connections
REDIS_SOCKET_TIMEOUT = redis_config.socket_timeout
REDIS_SOCKET_CONNECT_TIMEOUT = redis_config.socket_connect_timeout
REDIS_SOCKET_KEEPALIVE = redis_config.socket_keepalive
REDIS_SOCKET_KEEPALIVE_OPTIONS = redis_config.socket_keepalive_options
REDIS_HEALTH_CHECK_INTERVAL = redis_config.health_check_interval
REDIS_RETRY_ON_TIMEOUT = redis_config.retry_on_timeout

# 任务结果缓存配置
TASK_RESULT_TTL = redis_config.task_result_ttl
TASK_RESULT_KEY_PREFIX = redis_config.task_result_key_prefix

# 会话缓存配置
SESSION_TTL = redis_config.session_ttl
SESSION_KEY_PREFIX = redis_config.session_key_prefix

# ==================== 远程桌面配置 ====================
# 远程桌面连接配置
REMOTE_DESKTOP_ENABLED = remote_desktop_config.enabled
VNC_URL = remote_desktop_config.vnc_url
VNC_HOST = remote_desktop_config.vnc_host
VNC_PORT = remote_desktop_config.vnc_port
VNC_PASSWORD = remote_desktop_config.vnc_password
DISPLAY_NUMBER = remote_desktop_config.display_number
CONNECTION_TIMEOUT = remote_desktop_config.connection_timeout
MAX_WAIT_TIME = remote_desktop_config.max_wait_time
CHECK_INTERVAL = remote_desktop_config.check_interval

# ==================== 服务器配置 ====================
# 服务器基础配置
SERVER_PORT = server_config.port
SERVER_HOST = server_config.host
SERVER_DEBUG = server_config.debug
SERVER_ENABLE_CORS = server_config.enable_cors
SERVER_STATIC_PATH = server_config.static_path
SERVER_MAX_UPLOAD_SIZE = server_config.max_upload_size

# ==================== 安全配置 ====================
# 安全相关配置
SECURITY_ENABLE_HTTPS = security_config.enable_https
SECURITY_SSL_CERT = security_config.ssl_cert
SECURITY_SSL_KEY = security_config.ssl_key
SECURITY_SESSION_SECRET = security_config.session_secret
SECURITY_SESSION_EXPIRE = security_config.session_expire
SECURITY_ENABLE_API_AUTH = security_config.enable_api_auth
SECURITY_API_KEY = security_config.api_key

# ==================== 爬虫服务配置 ====================
# 爬虫服务相关配置
CRAWLER_SERVICE_MAX_PROCESSES = crawler_service_config.max_processes
CRAWLER_SERVICE_TASK_TIMEOUT = crawler_service_config.task_timeout
CRAWLER_SERVICE_RESULT_CACHE_TIME = crawler_service_config.result_cache_time
CRAWLER_SERVICE_ENABLE_MONITORING = crawler_service_config.enable_monitoring
CRAWLER_SERVICE_MONITOR_INTERVAL = crawler_service_config.monitor_interval
CRAWLER_SERVICE_CPU_WARNING_THRESHOLD = crawler_service_config.cpu_warning_threshold
CRAWLER_SERVICE_MEMORY_WARNING_THRESHOLD = crawler_service_config.memory_warning_threshold
CRAWLER_SERVICE_DISK_WARNING_THRESHOLD = crawler_service_config.disk_warning_threshold

# ==================== 任务管理配置 ====================
# 任务管理相关配置
TASK_MANAGEMENT_MAX_QUEUE_SIZE = task_management_config.max_queue_size
TASK_MANAGEMENT_MAX_RETRY_COUNT = task_management_config.max_retry_count
TASK_MANAGEMENT_RETRY_INTERVAL = task_management_config.retry_interval
TASK_MANAGEMENT_STATUS_CHECK_INTERVAL = task_management_config.status_check_interval
TASK_MANAGEMENT_RESULT_RETENTION_DAYS = task_management_config.result_retention_days

# ==================== 性能优化配置 ====================
# 性能优化相关配置
PERFORMANCE_ENABLE_CACHE = performance_config.enable_cache
PERFORMANCE_CACHE_SIZE_LIMIT = performance_config.cache_size_limit
PERFORMANCE_ENABLE_COMPRESSION = performance_config.enable_compression
PERFORMANCE_ENABLE_ASYNC = performance_config.enable_async
PERFORMANCE_ASYNC_QUEUE_SIZE = performance_config.async_queue_size
PERFORMANCE_ASYNC_TIMEOUT = performance_config.async_timeout

# ==================== 监控配置 ====================
# 监控相关配置
MONITORING_ENABLE_SYSTEM_MONITOR = monitoring_config.enable_system_monitor
MONITORING_DATA_RETENTION_DAYS = monitoring_config.data_retention_days
MONITORING_COLLECTION_INTERVAL = monitoring_config.collection_interval
MONITORING_ENABLE_ALERTS = monitoring_config.enable_alerts
MONITORING_ALERTS_CPU_THRESHOLD = monitoring_config.alerts.cpu_threshold
MONITORING_ALERTS_MEMORY_THRESHOLD = monitoring_config.alerts.memory_threshold
MONITORING_ALERTS_DISK_THRESHOLD = monitoring_config.alerts.disk_threshold
MONITORING_ALERTS_RESPONSE_TIME_THRESHOLD = monitoring_config.alerts.response_time_threshold

# ==================== 开发环境配置 ====================
# 开发环境相关配置
DEVELOPMENT_ENABLE_HOT_RELOAD = development_config.enable_hot_reload
DEVELOPMENT_ENABLE_DEBUG_TOOLBAR = development_config.enable_debug_toolbar
DEVELOPMENT_ENABLE_DETAILED_ERRORS = development_config.enable_detailed_errors
DEVELOPMENT_TEST_MODE = development_config.test_mode

# ==================== 任务隔离配置 ====================
# 任务隔离相关配置
TASK_ISOLATION_MODE = "strict"  # strict: 完全隔离, shared: 共享资源
TASK_MAX_CONCURRENT_TASKS = 10
TASK_MAX_TASKS_PER_SESSION = 50
TASK_ENABLE_RESOURCE_ISOLATION = True
TASK_ENABLE_CROSS_DATA_ACCESS = False

# 认证预留配置
AUTH_MIDDLEWARE_ENABLED = False  # 预留：将来集成用户认证
AUTH_TOKEN_HEADER = "Authorization"
AUTH_SESSION_TIMEOUT = 7200  # 2小时

# ==================== 定时任务配置 ====================
# 登录状态检查任务配置
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLED = login_status_check_config.get("enabled", True)
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_INTERVAL_HOURS = login_status_check_config.get("interval_hours", 6)
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_START_TIME = login_status_check_config.get("start_time", "02:00")
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_MAX_CONCURRENT = login_status_check_config.get("max_concurrent", 5)
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_TIMEOUT = login_status_check_config.get("timeout", 30)
SCHEDULED_TASKS_LOGIN_STATUS_CHECK_ENABLE_LOGGING = login_status_check_config.get("enable_logging", True)

# 调度器配置
SCHEDULED_TASKS_SCHEDULER_MAX_CONCURRENT_TASKS = scheduler_config.get("max_concurrent_tasks", 3)
SCHEDULED_TASKS_SCHEDULER_TASK_TIMEOUT_SECONDS = scheduler_config.get("task_timeout_seconds", 3600)
SCHEDULED_TASKS_SCHEDULER_ENABLE_LOGGING = scheduler_config.get("enable_logging", True)

# ==================== 基础配置 ====================
# 自定义User Agent
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
CUSTOM_WORDS = {
    "零几": "年份",  # 将"零几"识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# ==================== 配置管理工具函数 ====================
def reload_config():
    """重新加载配置"""
    config_manager.reload()
    # 重新获取配置对象
    global proxy_config, crawler_config, database_config, app_config, redis_config
    global remote_desktop_config, server_config, security_config, crawler_service_config
    global task_management_config, performance_config, monitoring_config, development_config
    global scheduled_tasks_config, login_status_check_config, scheduler_config
    
    # 🆕 修复：代理配置现在从proxy_management.py管理，不再需要get_proxy_config
    # proxy_config = config_manager.get_proxy_config()  # 已移除
    crawler_config = config_manager.get_crawler_config()
    database_config = config_manager.get_database_config()
    app_config = config_manager.get_app_config()
    redis_config = config_manager.get_redis_config()
    remote_desktop_config = config_manager.get_remote_desktop_config()
    server_config = config_manager.get_server_config()
    security_config = config_manager.get_security_config()
    crawler_service_config = config_manager.get_crawler_service_config()
    task_management_config = config_manager.get_task_management_config()
    performance_config = config_manager.get_performance_config()
    monitoring_config = config_manager.get_monitoring_config()
    development_config = config_manager.get_development_config()
    
    # 重新获取定时任务配置
    scheduled_tasks_config = config_manager.get("scheduled_tasks", {})
    login_status_check_config = scheduled_tasks_config.get("login_status_check", {})
    scheduler_config = scheduled_tasks_config.get("scheduler", {})

def export_config(env: str = "development", format: str = "yaml"):
    """导出配置"""
    if format.lower() == "yaml":
        config_manager.export_to_yaml(env)
    elif format.lower() == "json":
        config_manager.export_to_json(env)
    else:
        raise ValueError("Unsupported format. Use 'yaml' or 'json'")

def get_config_value(key: str, default=None):
    """获取配置值"""
    return config_manager.get(key, default)

def set_config_value(key: str, value):
    """设置配置值"""
    config_manager.set(key, value)