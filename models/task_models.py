#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务管理相关的数据模型
用于API请求响应的数据结构定义
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, JSON, func, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型枚举"""
    SEARCH = "search"
    USER = "user"
    HASHTAG = "hashtag"
    COMMENT = "comment"


class ActionType(str, Enum):
    """操作类型枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    START = "start"
    COMPLETE = "complete"
    FAIL = "fail"
    FAVORITE = "favorite"
    UNFAVORITE = "unfavorite"
    PIN = "pin"
    UNPIN = "unpin"
    DOWNLOAD = "download"
    COLLECT = "collect"


# SQLAlchemy 模型定义
class CrawlerTask(Base):
    """爬虫任务模型"""
    __tablename__ = 'crawler_tasks'
    
    id = Column(String(36), primary_key=True, comment='任务ID')
    platform = Column(String(20), nullable=False, comment='平台名称')
    task_type = Column(String(20), nullable=False, comment='任务类型')
    keywords = Column(Text, comment='关键词')
    status = Column(String(20), nullable=False, default='pending', comment='任务状态')
    progress = Column(Float, default=0, comment='进度')
    result_count = Column(Integer, default=0, comment='结果数量')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    
    # 新增字段
    user_id = Column(String(36), comment='用户ID')
    params = Column(JSON, comment='任务参数')
    priority = Column(Integer, default=0, comment='优先级')
    is_favorite = Column(Boolean, default=False, comment='是否收藏')
    deleted = Column(Boolean, default=False, comment='软删除')
    is_pinned = Column(Boolean, default=False, comment='是否置顶')
    ip_address = Column(String(45), comment='IP地址')
    user_security_id = Column(String(64), comment='用户安全ID')
    user_signature = Column(String(255), comment='用户signature')
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'task_type': self.task_type,
            'keywords': self.keywords,
            'status': self.status,
            'progress': self.progress,
            'result_count': self.result_count,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'user_id': self.user_id,
            'params': self.params,
            'priority': self.priority,
            'is_favorite': self.is_favorite,
            'deleted': self.deleted,
            'is_pinned': self.is_pinned,
            'ip_address': self.ip_address,
            'user_security_id': self.user_security_id,
            'user_signature': self.user_signature
        }


class UnifiedContent(Base):
    """统一内容模型"""
    __tablename__ = 'unified_content'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='数据库ID')
    content_id = Column(String(100), nullable=False, comment='内容ID')
    platform = Column(String(20), nullable=False, comment='平台名称')
    content_type = Column(String(50), comment='内容类型')
    task_id = Column(String(36), comment='任务ID')
    source_keyword = Column(String(200), comment='来源关键词')
    title = Column(String(500), comment='标题')
    description = Column(Text, comment='描述')
    content = Column(Text, comment='内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    publish_time = Column(BigInteger, comment='发布时间戳')
    update_time = Column(BigInteger, comment='更新时间戳')
    author_id = Column(String(100), comment='作者ID')
    author_name = Column(String(100), comment='作者名称')
    author_nickname = Column(String(100), comment='作者昵称')
    author_avatar = Column(Text, comment='作者头像')
    author_signature = Column(Text, comment='作者签名')
    author_unique_id = Column(String(100), comment='作者唯一ID')
    author_sec_uid = Column(String(100), comment='作者sec_uid')
    author_short_id = Column(String(100), comment='作者短ID')
    like_count = Column(Integer, default=0, comment='点赞数')
    comment_count = Column(Integer, default=0, comment='评论数')
    share_count = Column(Integer, default=0, comment='分享数')
    collect_count = Column(Integer, default=0, comment='收藏数')
    view_count = Column(Integer, default=0, comment='播放数')
    cover_url = Column(Text, comment='封面URL')
    video_url = Column(Text, comment='视频URL')
    video_download_url = Column(Text, comment='视频下载URL')
    video_play_url = Column(Text, comment='视频播放URL')
    video_share_url = Column(Text, comment='视频分享URL')
    image_urls = Column(Text, comment='图片URL列表')
    audio_url = Column(Text, comment='音频URL')
    file_urls = Column(Text, comment='文件URL列表')
    ip_location = Column(String(100), comment='IP位置')
    location = Column(String(200), comment='位置信息')
    tags = Column(Text, comment='标签')
    categories = Column(Text, comment='分类')
    topics = Column(Text, comment='话题')
    is_favorite = Column(Boolean, default=False, comment='是否收藏')
    is_deleted = Column(Boolean, default=False, comment='是否删除')
    is_private = Column(Boolean, default=False, comment='是否私密')
    is_original = Column(Boolean, default=False, comment='是否原创')
    minio_url = Column(Text, comment='MinIO URL')
    local_path = Column(String(500), comment='本地路径')
    file_size = Column(BigInteger, comment='文件大小')
    storage_type = Column(String(20), default='url_only', comment='存储类型')
    meta_data = Column(Text, comment='元数据')
    raw_data = Column(Text, comment='原始数据')
    extra_info = Column(Text, comment='额外信息')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'platform': self.platform,
            'content_type': self.content_type,
            'task_id': self.task_id,
            'source_keyword': self.source_keyword,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'create_time': self.create_time,
            'publish_time': self.publish_time,
            'update_time': self.update_time,
            'author_id': self.author_id,
            'author_name': self.author_name,
            'author_nickname': self.author_nickname,
            'author_avatar': self.author_avatar,
            'author_signature': self.author_signature,
            'author_unique_id': self.author_unique_id,
            'author_sec_uid': self.author_sec_uid,
            'author_short_id': self.author_short_id,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'collect_count': self.collect_count,
            'view_count': self.view_count,
            'cover_url': self.cover_url,
            'video_url': self.video_url,
            'video_download_url': self.video_download_url,
            'video_play_url': self.video_play_url,
            'video_share_url': self.video_share_url,
            'image_urls': self.image_urls,
            'audio_url': self.audio_url,
            'file_urls': self.file_urls,
            'ip_location': self.ip_location,
            'location': self.location,
            'tags': self.tags,
            'categories': self.categories,
            'topics': self.topics,
            'is_favorite': self.is_favorite,
            'is_deleted': self.is_deleted,
            'is_private': self.is_private,
            'is_original': self.is_original,
            'minio_url': self.minio_url,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'storage_type': self.storage_type,
            'meta_data': self.meta_data,
            'raw_data': self.raw_data,
            'extra_info': self.extra_info,
            'add_ts': self.add_ts,
            'last_modify_ts': self.last_modify_ts
        }


class CrawlerTaskLog(Base):
    """任务日志模型"""
    __tablename__ = 'crawler_task_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='日志ID')
    task_id = Column(String(36), nullable=False, comment='任务ID')
    action_type = Column(String(32), nullable=False, comment='操作类型')
    content = Column(Text, comment='日志内容')
    operator = Column(String(64), comment='操作者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'action_type': self.action_type,
            'content': self.content,
            'operator': self.operator,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Pydantic 请求/响应模型
class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    platform: str = Field(..., description="平台名称")
    task_type: str = Field(..., description="任务类型")
    keywords: str = Field(..., description="关键词")
    user_id: Optional[str] = Field(None, description="用户ID")
    params: Optional[Dict] = Field(None, description="任务参数")
    priority: int = Field(default=0, description="优先级")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_security_id: Optional[str] = Field(None, description="用户安全ID")
    user_signature: Optional[str] = Field(None, description="用户signature")


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[float] = Field(None, description="进度")
    result_count: Optional[int] = Field(None, description="结果数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    is_pinned: Optional[bool] = Field(None, description="是否置顶")


class TaskListRequest(BaseModel):
    """任务列表查询请求"""
    platform: Optional[str] = Field(None, description="平台筛选")
    status: Optional[str] = Field(None, description="状态筛选")
    task_type: Optional[str] = Field(None, description="任务类型筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    is_favorite: Optional[bool] = Field(None, description="收藏筛选")
    is_pinned: Optional[bool] = Field(None, description="置顶筛选")
    user_id: Optional[str] = Field(None, description="用户ID筛选")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    platform: str
    task_type: str
    keywords: Optional[str]
    status: str
    progress: float
    result_count: int
    error_message: Optional[str]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    user_id: Optional[str]
    params: Optional[Dict]
    priority: int
    is_favorite: bool
    is_pinned: bool
    ip_address: Optional[str]
    user_security_id: Optional[str]
    user_signature: Optional[str]


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[TaskResponse]
    statistics: Dict[str, Any]


class VideoResponse(BaseModel):
    """视频响应"""
    id: int
    aweme_id: str
    desc: Optional[str]
    author_id: Optional[str]
    author_name: Optional[str]
    author_avatar: Optional[str]
    cover_url: Optional[str]
    play_url: Optional[str]
    download_url: Optional[str]
    share_url: Optional[str]
    duration: Optional[int]
    create_time: Optional[str]
    digg_count: int
    comment_count: int
    share_count: int
    collect_count: int
    music_id: Optional[str]
    music_name: Optional[str]
    music_url: Optional[str]
    tags: Optional[List[str]]
    is_collected: bool
    minio_url: Optional[str]
    task_id: Optional[str]
    created_at: str
    updated_at: str


class VideoListResponse(BaseModel):
    """视频列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[VideoResponse]


class TaskLogResponse(BaseModel):
    """任务日志响应"""
    id: int
    task_id: str
    action_type: str
    content: Optional[str]
    operator: Optional[str]
    created_at: str


class TaskLogListResponse(BaseModel):
    """任务日志列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[TaskLogResponse]


class TaskStatisticsResponse(BaseModel):
    """任务统计响应"""
    total_tasks: int
    completed_tasks: int
    running_tasks: int
    failed_tasks: int
    total_videos: int
    total_size: int
    platform_stats: Dict[str, int]
    recent_tasks: List[TaskResponse]


class VideoActionRequest(BaseModel):
    """视频操作请求"""
    action: str = Field(..., description="操作类型：favorite/unfavorite/download/collect")
    video_id: int = Field(..., description="视频ID")


class TaskActionRequest(BaseModel):
    """任务操作请求"""
    action: str = Field(..., description="操作类型：favorite/unfavorite/pin/unpin/delete")
    task_id: str = Field(..., description="任务ID") 