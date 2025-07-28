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
proxy_config = config_manager.get_proxy_config()
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

# ==================== 代理配置 ====================
# 是否开启 IP 代理
ENABLE_IP_PROXY = proxy_config.enabled

# 代理IP池数量
IP_PROXY_POOL_COUNT = proxy_config.pool_count

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = proxy_config.provider_name

# 代理IP验证
PROXY_VALIDATE_IP = proxy_config.validate_ip

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

# ==================== 兼容性配置 ====================
# 为了保持向后兼容，保留原有的配置项
# 这些配置项会从新的配置管理器中获取值

# 自定义User Agent（暂时仅对XHS有效）
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 登录cookies（仅用于命令行参数兼容，爬虫实际从数据库读取）
COOKIES = ""

# 指定使用的账号ID（可选，如果不指定则使用最新登录的账号）
ACCOUNT_ID = None

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持小红书
SORT_TYPE = "popularity_descending"

# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持抖音
PUBLISH_TIME_TYPE = 0

# 已废弃⚠️⚠️⚠️指定小红书需要爬虫的笔记ID列表
# 已废弃⚠️⚠️⚠️ 指定笔记ID笔记列表会因为缺少xsec_token和xsec_source参数导致爬取失败
# XHS_SPECIFIED_ID_LIST = [
#     "66fad51c000000001b0224b8",
#     # ........................
# ]

# 指定小红书需要爬虫的笔记URL列表, 目前要携带xsec_token和xsec_source参数
XHS_SPECIFIED_NOTE_URL_LIST = [
    "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
    # ........................
]

# 指定抖音需要爬取的ID列表
DY_SPECIFIED_ID_LIST = [
    "7280854932641664319",
    "7202432992642387233",
    # ........................
]

# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = ["3xf8enb8dbj6uig", "3x6zz972bchmvqe"]

# 指定B站平台需要爬取的视频bvid列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定微博平台需要爬取的帖子列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# 指定weibo创作者ID列表
WEIBO_CREATOR_ID_LIST = [
    "5533390220",
    # ........................
]

# 指定贴吧需要爬取的帖子列表
TIEBA_SPECIFIED_ID_LIST = []

# 指定贴吧名称列表，爬取该贴吧下的帖子
TIEBA_NAME_LIST = [
    # "盗墓笔记"
]

# 指定贴吧创作者URL列表
TIEBA_CREATOR_URL_LIST = [
    "https://tieba.baidu.com/home/main/?id=tb.1.7f139e2e.6CyEwxu3VJruH_-QqpCi6g&fr=frs",
    # ........................
]

# 指定小红书创作者ID列表
XHS_CREATOR_ID_LIST = [
    "63e36c9a000000002703502b",
    # ........................
]

# 指定Dy创作者ID列表(sec_id)
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    # ........................
]

# 指定bili创作者ID列表(sec_id)
BILI_CREATOR_ID_LIST = [
    "20813884",
    # ........................
]

# 指定快手创作者ID列表
KS_CREATOR_ID_LIST = [
    "3x4sm73aye7jq7i",
    # ........................
]

# 指定知乎创作者主页url列表
ZHIHU_CREATOR_URL_LIST = [
    "https://www.zhihu.com/people/yd1234567",
    # ........................
]

# 指定知乎需要爬取的帖子ID列表
ZHIHU_SPECIFIED_ID_LIST = [
    "https://www.zhihu.com/question/826896610/answer/4885821440", # 回答
    "https://zhuanlan.zhihu.com/p/673461588", # 文章
    "https://www.zhihu.com/zvideo/1539542068422144000" # 视频
]

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将"零几"识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取开始的天数，仅支持 bilibili 关键字搜索，YYYY-MM-DD 格式，若为 None 则表示不设置时间范围，按照默认关键字最多返回 1000 条视频的结果处理
START_DAY = '2024-01-01'

# 爬取结束的天数，仅支持 bilibili 关键字搜索，YYYY-MM-DD 格式，若为 None 则表示不设置时间范围，按照默认关键字最多返回 1000 条视频的结果处理
END_DAY = '2024-01-01'

# 是否开启按每一天进行爬取的选项，仅支持 bilibili 关键字搜索
# 若为 False，则忽略 START_DAY 与 END_DAY 设置的值
# 若为 True，则按照 START_DAY 至 END_DAY 按照每一天进行筛选，这样能够突破 1000 条视频的限制，最大程度爬取该关键词下的所有视频
ALL_DAY = False

#!!! 下面仅支持 bilibili creator搜索
# 爬取评论creator主页还是爬取creator动态和关系列表(True为前者)
CREATOR_MODE = True

# 爬取creator粉丝列表时起始爬取页数
START_CONTACTS_PAGE = 1

# 爬取作者粉丝和关注列表数量控制(单作者)
CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100

# 爬取作者动态数量控制(单作者)
CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50

# ==================== 配置管理工具函数 ====================
def reload_config():
    """重新加载配置"""
    config_manager.reload()
    # 重新获取配置对象
    global proxy_config, crawler_config, database_config, app_config, redis_config
    global remote_desktop_config, server_config, security_config, crawler_service_config
    global task_management_config, performance_config, monitoring_config, development_config
    
    proxy_config = config_manager.get_proxy_config()
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