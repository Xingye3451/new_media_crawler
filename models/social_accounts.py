from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class SocialAccount(Base):
    __tablename__ = 'social_accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, comment='平台名称(xhs,dy,ks,bili,wb,tieba,zhihu)')
    account_name = Column(String(100), nullable=False, comment='账号名称/昵称')
    account_id = Column(String(100), comment='账号ID')
    username = Column(String(100), comment='用户名')
    password = Column(String(255), comment='密码(加密存储)')
    phone = Column(String(20), comment='手机号')
    email = Column(String(100), comment='邮箱')
    is_active = Column(Boolean, default=True, comment='是否启用')
    login_method = Column(String(20), default='qrcode', comment='登录方式(qrcode,phone,email,password)')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    notes = Column(Text, comment='备注')
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'account_name': self.account_name,
            'account_id': self.account_id,
            'username': self.username,
            'phone': self.phone,
            'email': self.email,
            'is_active': self.is_active,
            'login_method': self.login_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes,
            'has_password': bool(self.password)  # 只显示是否有密码，不显示密码内容
        }

class LoginToken(Base):
    __tablename__ = 'login_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, comment='关联的账号ID')
    platform = Column(String(20), nullable=False, comment='平台名称')
    token_type = Column(String(20), default='cookie', comment='令牌类型(cookie,session,token)')
    token_data = Column(Text, comment='令牌数据(JSON格式)')
    user_agent = Column(Text, comment='用户代理')
    proxy_info = Column(Text, comment='代理信息(JSON格式)')
    is_valid = Column(Boolean, default=True, comment='是否有效')
    expires_at = Column(DateTime, comment='过期时间')
    last_used_at = Column(DateTime, comment='最后使用时间')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'platform': self.platform,
            'token_type': self.token_type,
            'token_data': self.token_data,
            'user_agent': self.user_agent,
            'proxy_info': self.proxy_info,
            'is_valid': self.is_valid,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CrawlerTaskLog(Base):
    __tablename__ = 'crawler_task_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, comment='任务ID')
    platform = Column(String(20), nullable=False, comment='平台名称')
    account_id = Column(Integer, comment='使用的账号ID')
    log_level = Column(String(10), default='INFO', comment='日志级别(DEBUG,INFO,WARN,ERROR)')
    message = Column(Text, comment='日志消息')
    step = Column(String(50), comment='当前步骤')
    progress = Column(Integer, default=0, comment='进度百分比')
    extra_data = Column(Text, comment='额外数据(JSON格式)')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'platform': self.platform,
            'account_id': self.account_id,
            'log_level': self.log_level,
            'message': self.message,
            'step': self.step,
            'progress': self.progress,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 