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
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, JSON, func
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


class DouyinAweme(Base):
    """抖音视频模型"""
    __tablename__ = 'douyin_aweme'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='数据库ID')
    aweme_id = Column(String(64), unique=True, nullable=False, comment='视频ID')
    desc = Column(Text, comment='视频描述')
    author_id = Column(String(64), comment='作者ID')
    author_name = Column(String(128), comment='作者昵称')
    author_avatar = Column(String(255), comment='作者头像')
    cover_url = Column(String(255), comment='封面图')
    play_url = Column(String(255), comment='播放页链接')
    download_url = Column(String(255), comment='无水印下载链接')
    share_url = Column(String(255), comment='分享链接')
    duration = Column(Integer, comment='时长')
    create_time = Column(DateTime, comment='发布时间')
    digg_count = Column(Integer, default=0, comment='点赞数')
    comment_count = Column(Integer, default=0, comment='评论数')
    share_count = Column(Integer, default=0, comment='分享数')
    collect_count = Column(Integer, default=0, comment='收藏数')
    music_id = Column(String(64), comment='配乐ID')
    music_name = Column(String(128), comment='配乐名')
    music_url = Column(String(255), comment='配乐链接')
    tags = Column(JSON, comment='标签')
    is_collected = Column(Boolean, default=False, comment='是否已收藏到minio')
    minio_url = Column(String(255), comment='minio存储链接')
    task_id = Column(String(36), comment='关联任务ID')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'aweme_id': self.aweme_id,
            'desc': self.desc,
            'author_id': self.author_id,
            'author_name': self.author_name,
            'author_avatar': self.author_avatar,
            'cover_url': self.cover_url,
            'play_url': self.play_url,
            'download_url': self.download_url,
            'share_url': self.share_url,
            'duration': self.duration,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'digg_count': self.digg_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'collect_count': self.collect_count,
            'music_id': self.music_id,
            'music_name': self.music_name,
            'music_url': self.music_url,
            'tags': self.tags,
            'is_collected': self.is_collected,
            'minio_url': self.minio_url,
            'task_id': self.task_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
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