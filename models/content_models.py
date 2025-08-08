#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内容相关的数据模型
用于API请求响应的数据结构定义
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """内容类型枚举"""
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    MIXED = "mixed"


class Platform(str, Enum):
    """支持的平台枚举"""
    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class UnifiedContent(BaseModel):
    """统一的内容数据模型"""
    id: int = Field(..., description="数据库ID")
    platform: str = Field(..., description="平台名称")
    platform_name: str = Field(..., description="平台中文名称")
    content_id: str = Field(..., description="内容ID")
    content_type: str = Field(..., description="内容类型：video/image/text/mixed")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    content: Optional[str] = Field(None, description="内容文本")
    
    # 作者信息
    author_id: Optional[str] = Field(None, description="作者ID")
    author_name: Optional[str] = Field(None, description="作者昵称")
    author_avatar: Optional[str] = Field(None, description="作者头像")
    
    # 统计数据
    like_count: Optional[Union[str, int]] = Field(None, description="点赞数")
    comment_count: Optional[Union[str, int]] = Field(None, description="评论数")
    share_count: Optional[Union[str, int]] = Field(None, description="分享数")
    view_count: Optional[Union[str, int]] = Field(None, description="浏览数")
    collect_count: Optional[Union[str, int]] = Field(None, description="收藏数")
    
    # 时间信息
    publish_time: Optional[int] = Field(None, description="发布时间戳")
    publish_time_str: Optional[str] = Field(None, description="发布时间字符串")
    crawl_time: Optional[int] = Field(None, description="爬取时间戳")
    crawl_time_str: Optional[str] = Field(None, description="爬取时间字符串")
    
    # 关联信息
    source_keyword: Optional[str] = Field(None, description="搜索关键词")
    content_url: Optional[str] = Field(None, description="内容详情URL")
    cover_url: Optional[str] = Field(None, description="封面图片URL")
    video_url: Optional[str] = Field(None, description="视频URL")
    
    # 标签和分类
    tags: Optional[List[str]] = Field(None, description="标签列表")
    ip_location: Optional[str] = Field(None, description="IP地理位置")
    
    # 扩展数据
    extra_data: Optional[Dict] = Field(None, description="扩展数据")


class ContentListRequest(BaseModel):
    """内容列表查询请求 - 优先短视频内容"""
    platform: Optional[str] = Field(None, description="平台筛选")
    content_type: Optional[str] = Field(None, description="内容类型筛选")
    keyword: Optional[str] = Field(None, description="关键词筛选")
    author_name: Optional[str] = Field(None, description="作者筛选")
    start_time: Optional[str] = Field(None, description="开始时间（ISO格式）")
    end_time: Optional[str] = Field(None, description="结束时间（ISO格式）")
    sort_by: Optional[str] = Field(default="crawl_time", description="排序字段：crawl_time/publish_time/like_count")
    sort_order: Optional[str] = Field(default="desc", description="排序方向：asc/desc")
    page: int = Field(default=1, description="页码", ge=1)
    page_size: int = Field(default=20, description="每页数量", ge=1, le=100)
    
    # 短视频优先相关参数
    video_only: bool = Field(default=False, description="仅显示视频内容（短视频优先模式）")
    video_platforms_only: bool = Field(default=False, description="仅显示视频主导平台（抖音、快手、小红书视频等）")
    exclude_todo_platforms: bool = Field(default=True, description="排除TODO/待开发平台的内容")


class ContentListResponse(BaseModel):
    """内容列表响应"""
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    items: List[UnifiedContent] = Field(..., description="内容列表")
    platforms_summary: Dict[str, int] = Field(..., description="各平台数量统计")


class CrawlerRequest(BaseModel):
    """爬虫请求模型 - 专注短视频内容"""
    platform: str = Field(..., description="平台名称", example="xhs")
    keywords: str = Field(..., description="搜索关键词", example="编程副业")
    max_notes_count: int = Field(default=20, description="最大爬取数量", example=20)
    account_id: Optional[int] = Field(default=None, description="指定账号ID（可选）", example=8)
    session_id: Optional[str] = Field(default=None, description="会话ID（可选）", example="session_123")
    
    # 新增前端发送的参数
    login_type: Optional[str] = Field(default="qrcode", description="登录类型", example="qrcode")
    crawler_type: Optional[str] = Field(default="search", description="爬虫类型", example="search")
    get_comments: Optional[bool] = Field(default=True, description="是否获取评论", example=True)
    save_data_option: Optional[str] = Field(default="db", description="数据保存选项", example="db")
    use_proxy: Optional[bool] = Field(default=False, description="是否使用代理", example=False)
    proxy_strategy: Optional[str] = Field(default="disabled", description="代理策略", example="disabled")
    
    # 创作者主页模式参数
    selected_creators: Optional[List[str]] = Field(default=None, description="选中的创作者ID列表（创作者主页模式使用）", example=["creator_1", "creator_2"])
    creator_ref_id: Optional[str] = Field(default=None, description="创作者引用ID（当crawler_type为creator时，关联unified_creator表）", example="creator_123")
    
    # 短视频优先参数
    video_priority: Optional[bool] = Field(default=True, description="短视频优先模式（如小红书优先搜索视频内容）", example=True)
    video_only: Optional[bool] = Field(default=False, description="仅爬取视频内容", example=False)
    
    # 分页参数
    start_page: Optional[int] = Field(default=1, description="起始页码", example=1)


class MultiPlatformCrawlerRequest(BaseModel):
    """多平台抓取请求模型"""
    platforms: List[str] = Field(..., description="平台列表: xhs, dy, ks, bili, wb, tieba, zhihu")
    keywords: str = Field(..., description="搜索关键词")
    max_count_per_platform: int = Field(default=50, description="每个平台最大抓取数量")
    enable_comments: bool = Field(default=False, description="是否抓取评论")
    enable_images: bool = Field(default=False, description="是否抓取图片")
    save_format: str = Field(default="db", description="保存格式: db (固定数据库存储)")
    session_ids: Optional[Dict[str, str]] = Field(default=None, description="各平台的登录会话ID")
    account_ids: Optional[Dict[str, int]] = Field(default=None, description="各平台的账号ID")
    # 新增代理相关参数
    use_proxy: bool = Field(default=False, description="是否使用代理")
    proxy_strategy: str = Field(default="round_robin", description="代理策略: round_robin, random, weighted, failover, geo_based, smart, disabled")
    # 新增账号策略和执行模式参数
    account_strategy: str = Field(default="smart", description="账号策略: random, round_robin, priority, smart, single")
    execution_mode: str = Field(default="parallel", description="执行模式: parallel(并行), sequential(顺序)")


class CrawlerResponse(BaseModel):
    """爬虫响应模型"""
    task_id: str
    status: str
    message: str
    data: Optional[Dict] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class MultiPlatformTaskStatusResponse(BaseModel):
    """多平台任务状态响应模型"""
    task_id: str
    status: str
    platforms: List[str]
    keywords: str
    progress: Dict[str, Any]
    results: Optional[Dict[str, int]] = None
    errors: Optional[Dict[str, str]] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class UnifiedResultResponse(BaseModel):
    """统一结果模型"""
    platform: str
    platform_name: str
    content_id: str
    title: str
    author: str
    publish_time: str
    content: str
    likes: int
    comments: int
    shares: int
    views: int
    download_links: List[str]
    tags: List[str]
    url: str


# 平台映射配置 - 专注短视频内容
PLATFORM_MAPPING = {
    "xhs": {
        "name": "小红书", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "video",  # 优先视频内容
        "video_filter": "content_type = 'video'",  # 视频筛选条件
        "description": "小红书短视频内容"
    },
    "dy": {
        "name": "抖音", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "video",
        "video_filter": "content_type = 'video'",
        "description": "抖音短视频内容"
    },
    "ks": {
        "name": "快手", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "video",
        "video_filter": "content_type = 'video'",
        "description": "快手短视频内容"
    },
    "bili": {
        "name": "B站", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "video",
        "video_filter": "content_type = 'video'",
        "description": "B站短视频内容"
    },
    "wb": {
        "name": "微博", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "mixed",  # 微博内容混合，视频为辅
        "video_filter": "content_type = 'video'",
        "description": "微博视频内容"
    },
    "tieba": {
        "name": "贴吧", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "text",  # 贴吧视频支持较少，暂时忽略
        "video_filter": "content_type = 'video'",
        "description": "贴吧内容"
    },
    "zhihu": {
        "name": "知乎", 
        "table": "unified_content", 
        "id_field": "content_id",
        "primary_content_type": "mixed",  # 知乎有专门的zvideo类型
        "video_filter": "content_type = 'video'",
        "description": "知乎视频内容"
    }
}


# 支持的平台列表
SUPPORTED_PLATFORMS = [
    # 当前支持的视频优先平台
    {"code": "xhs", "name": "小红书", "description": "小红书笔记和评论爬取", "status": "active", "type": "video"},
    {"code": "dy", "name": "抖音", "description": "抖音视频和评论爬取", "status": "active", "type": "video"},
    {"code": "ks", "name": "快手", "description": "快手视频和评论爬取", "status": "active", "type": "video"},
    {"code": "bili", "name": "B站", "description": "B站视频和评论爬取", "status": "active", "type": "video"},
    # 即将支持的文字平台
    {"code": "wb", "name": "微博", "description": "微博内容和评论爬取（即将支持）", "status": "coming_soon", "type": "text"},
    {"code": "tieba", "name": "贴吧", "description": "贴吧帖子和回复爬取（即将支持）", "status": "coming_soon", "type": "text"},
    {"code": "zhihu", "name": "知乎", "description": "知乎问答和评论爬取（即将支持）", "status": "coming_soon", "type": "text"}
]


# 短视频优先平台配置
VIDEO_PRIORITY_PLATFORMS = ["xhs", "dy", "ks", "bili"]  # 专注短视频的主要平台
COMING_SOON_PLATFORMS = ["tieba", "wb", "zhihu"]  # 即将支持的平台（专注短视频后暂时禁用）
MIXED_PLATFORMS = []  # 混合平台（暂时为空，专注短视频）


def get_video_platforms():
    """获取视频优先平台列表"""
    return VIDEO_PRIORITY_PLATFORMS


def get_coming_soon_platforms():
    """获取即将支持的平台列表"""
    return COMING_SOON_PLATFORMS


def get_supported_platforms_for_video():
    """获取支持短视频的平台列表（仅视频优先平台）"""
    return VIDEO_PRIORITY_PLATFORMS


def get_platform_description(platform_code: str) -> str:
    """获取平台的详细描述信息"""
    if platform_code in PLATFORM_MAPPING:
        return PLATFORM_MAPPING[platform_code].get("description", "")
    return "未知平台"


def is_video_priority_platform(platform_code: str) -> bool:
    """判断是否为短视频优先平台"""
    return platform_code in VIDEO_PRIORITY_PLATFORMS


def is_coming_soon_platform(platform_code: str) -> bool:
    """判断是否为即将支持的平台"""
    return platform_code in COMING_SOON_PLATFORMS


def is_todo_platform(platform_code: str) -> bool:
    """判断是否为TODO/待开发平台（已弃用，使用is_coming_soon_platform）"""
    return platform_code in COMING_SOON_PLATFORMS 