#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的数据模型模块
整合所有SQLAlchemy和Pydantic模型
"""

# 导入核心模型
from .content_models import (
    ContentType, Platform, UnifiedContent, ContentListRequest, 
    ContentListResponse, CrawlerRequest, MultiPlatformCrawlerRequest,
    CrawlerResponse, TaskStatusResponse, MultiPlatformTaskStatusResponse,
    UnifiedResultResponse
)

from .task_models import (
    TaskStatus, TaskType, ActionType, CrawlerTask, UnifiedContent as UnifiedContentDB,
    CrawlerTaskLog, TaskCreateRequest, TaskUpdateRequest, TaskListRequest,
    TaskResponse, TaskListResponse, VideoResponse, VideoListResponse,
    TaskLogResponse, TaskLogListResponse, TaskStatisticsResponse,
    VideoActionRequest, TaskActionRequest
)

from .social_accounts import (
    SocialAccount, LoginToken, CrawlerTaskLog as SocialCrawlerTaskLog
)

# 导出所有模型
__all__ = [
    # 内容模型
    'ContentType', 'Platform', 'UnifiedContent', 'ContentListRequest',
    'ContentListResponse', 'CrawlerRequest', 'MultiPlatformCrawlerRequest',
    'CrawlerResponse', 'TaskStatusResponse', 'MultiPlatformTaskStatusResponse',
    'UnifiedResultResponse',
    
    # 任务模型
    'TaskStatus', 'TaskType', 'ActionType', 'CrawlerTask', 'UnifiedContentDB',
    'CrawlerTaskLog', 'TaskCreateRequest', 'TaskUpdateRequest', 'TaskListRequest',
    'TaskResponse', 'TaskListResponse', 'VideoResponse', 'VideoListResponse',
    'TaskLogResponse', 'TaskLogListResponse', 'TaskStatisticsResponse',
    'VideoActionRequest', 'TaskActionRequest',
    
    # 社交账号模型
    'SocialAccount', 'LoginToken', 'SocialCrawlerTaskLog',
]
