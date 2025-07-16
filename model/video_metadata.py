# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:00
# @Desc    : 视频元数据模型

from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json

Base = declarative_base()


class VideoMetadata(Base):
    """视频元数据表"""
    __tablename__ = 'video_metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基础信息
    platform = Column(String(50), nullable=False, index=True, comment='平台名称')
    content_id = Column(String(100), nullable=False, index=True, comment='内容ID')
    title = Column(String(500), comment='视频标题')
    description = Column(Text, comment='视频描述')
    author = Column(String(200), comment='作者')
    author_id = Column(String(100), comment='作者ID')
    
    # 存储信息
    storage_type = Column(String(20), nullable=False, comment='存储类型: local/minio')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(Integer, comment='文件大小(字节)')
    file_hash = Column(String(64), comment='文件哈希值')
    content_type = Column(String(100), comment='文件类型')
    local_path = Column(String(500), comment='本地文件路径')
    
    # 视频信息
    duration = Column(Float, comment='视频时长(秒)')
    width = Column(Integer, comment='视频宽度')
    height = Column(Integer, comment='视频高度')
    fps = Column(Float, comment='帧率')
    bitrate = Column(Integer, comment='比特率')
    format = Column(String(20), comment='视频格式')
    
    # 统计信息
    view_count = Column(Integer, default=0, comment='播放次数')
    like_count = Column(Integer, default=0, comment='点赞数')
    comment_count = Column(Integer, default=0, comment='评论数')
    share_count = Column(Integer, default=0, comment='分享数')
    
    # 标签和分类
    tags = Column(JSON, comment='标签列表')
    category = Column(String(100), comment='分类')
    
    # 时间信息
    publish_time = Column(DateTime, comment='发布时间')
    crawl_time = Column(DateTime, default=datetime.now, comment='爬取时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 状态信息
    is_deleted = Column(Boolean, default=False, comment='是否已删除')
    status = Column(String(20), default='active', comment='状态: active/deleted/error')
    
    # 扩展信息
    extra_data = Column(JSON, comment='扩展数据')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'platform': self.platform,
            'content_id': self.content_id,
            'title': self.title,
            'description': self.description,
            'author': self.author,
            'author_id': self.author_id,
            'storage_type': self.storage_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'content_type': self.content_type,
            'local_path': self.local_path,
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'format': self.format,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'tags': self.tags,
            'category': self.category,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'crawl_time': self.crawl_time.isoformat() if self.crawl_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'status': self.status,
            'extra_data': self.extra_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMetadata':
        """从字典创建实例"""
        # 处理时间字段
        if 'publish_time' in data and data['publish_time']:
            if isinstance(data['publish_time'], str):
                data['publish_time'] = datetime.fromisoformat(data['publish_time'])
        
        if 'crawl_time' in data and data['crawl_time']:
            if isinstance(data['crawl_time'], str):
                data['crawl_time'] = datetime.fromisoformat(data['crawl_time'])
        
        # 处理JSON字段
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        
        if 'extra_data' in data and isinstance(data['extra_data'], str):
            data['extra_data'] = json.loads(data['extra_data'])
        
        return cls(**data)


class VideoMetadataManager:
    """视频元数据管理器"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(self.engine)
    
    def save_metadata(self, metadata: VideoMetadata) -> int:
        """保存元数据"""
        session = self.Session()
        try:
            session.add(metadata)
            session.commit()
            return metadata.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_metadata_by_id(self, metadata_id: int) -> Optional[VideoMetadata]:
        """根据ID获取元数据"""
        session = self.Session()
        try:
            return session.query(VideoMetadata).filter(
                VideoMetadata.id == metadata_id,
                VideoMetadata.is_deleted == False
            ).first()
        finally:
            session.close()
    
    def get_metadata_by_content_id(self, platform: str, content_id: str) -> Optional[VideoMetadata]:
        """根据平台和内容ID获取元数据"""
        session = self.Session()
        try:
            return session.query(VideoMetadata).filter(
                VideoMetadata.platform == platform,
                VideoMetadata.content_id == content_id,
                VideoMetadata.is_deleted == False
            ).first()
        finally:
            session.close()
    
    def update_metadata(self, metadata_id: int, update_data: Dict[str, Any]) -> bool:
        """更新元数据"""
        session = self.Session()
        try:
            metadata = session.query(VideoMetadata).filter(
                VideoMetadata.id == metadata_id,
                VideoMetadata.is_deleted == False
            ).first()
            
            if metadata:
                for key, value in update_data.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)
                metadata.updated_at = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_metadata(self, metadata_id: int, soft_delete: bool = True) -> bool:
        """删除元数据"""
        session = self.Session()
        try:
            metadata = session.query(VideoMetadata).filter(
                VideoMetadata.id == metadata_id,
                VideoMetadata.is_deleted == False
            ).first()
            
            if metadata:
                if soft_delete:
                    metadata.is_deleted = True
                    metadata.status = 'deleted'
                    metadata.updated_at = datetime.now()
                else:
                    session.delete(metadata)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def list_metadata(self, 
                     platform: Optional[str] = None,
                     author: Optional[str] = None,
                     status: Optional[str] = None,
                     limit: int = 100,
                     offset: int = 0) -> List[VideoMetadata]:
        """列出元数据"""
        session = self.Session()
        try:
            query = session.query(VideoMetadata).filter(VideoMetadata.is_deleted == False)
            
            if platform:
                query = query.filter(VideoMetadata.platform == platform)
            
            if author:
                query = query.filter(VideoMetadata.author == author)
            
            if status:
                query = query.filter(VideoMetadata.status == status)
            
            return query.order_by(VideoMetadata.created_at.desc()).limit(limit).offset(offset).all()
        finally:
            session.close()
    
    def search_metadata(self, 
                       keyword: str,
                       platform: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[VideoMetadata]:
        """搜索元数据"""
        session = self.Session()
        try:
            query = session.query(VideoMetadata).filter(
                VideoMetadata.is_deleted == False,
                (VideoMetadata.title.contains(keyword) |
                 VideoMetadata.description.contains(keyword) |
                 VideoMetadata.author.contains(keyword))
            )
            
            if platform:
                query = query.filter(VideoMetadata.platform == platform)
            
            return query.order_by(VideoMetadata.created_at.desc()).limit(limit).offset(offset).all()
        finally:
            session.close()
    
    def get_statistics(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        session = self.Session()
        try:
            query = session.query(VideoMetadata).filter(VideoMetadata.is_deleted == False)
            
            if platform:
                query = query.filter(VideoMetadata.platform == platform)
            
            total_count = query.count()
            total_size = query.with_entities(VideoMetadata.file_size).all()
            total_size = sum(size[0] or 0 for size in total_size)
            
            # 按平台统计
            platform_stats = {}
            if not platform:
                platform_query = session.query(
                    VideoMetadata.platform,
                    session.query(VideoMetadata).filter(
                        VideoMetadata.platform == VideoMetadata.platform,
                        VideoMetadata.is_deleted == False
                    ).count().label('count')
                ).filter(VideoMetadata.is_deleted == False).group_by(VideoMetadata.platform).all()
                
                platform_stats = {p: c for p, c in platform_query}
            
            return {
                'total_count': total_count,
                'total_size': total_size,
                'platform_stats': platform_stats
            }
        finally:
            session.close() 