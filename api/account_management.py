from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import hashlib
import base64
from datetime import datetime
from var import media_crawler_db_var
from tools import utils

account_router = APIRouter(tags=["账号管理"])

def encrypt_password(password: str) -> str:
    """加密密码"""
    if not password:
        return None
    # 使用SHA256加密密码
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, encrypted_password: str) -> bool:
    """验证密码"""
    if not password or not encrypted_password:
        return False
    return encrypt_password(password) == encrypted_password

class SocialAccountCreate(BaseModel):
    platform: str = Field(..., description="平台名称")
    account_name: str = Field(..., description="账号名称/昵称")
    account_id: Optional[str] = Field(None, description="账号ID")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    is_active: bool = Field(default=True, description="是否启用")
    login_method: str = Field(default="qrcode", description="登录方式")
    notes: Optional[str] = Field(None, description="备注")

class SocialAccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, description="账号名称/昵称")
    account_id: Optional[str] = Field(None, description="账号ID")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    is_active: Optional[bool] = Field(None, description="是否启用")
    login_method: Optional[str] = Field(None, description="登录方式")
    notes: Optional[str] = Field(None, description="备注")

class SocialAccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    account_id: Optional[str]
    username: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    login_method: str
    created_at: str
    updated_at: str
    notes: Optional[str]
    has_password: bool = False  # 是否设置了密码
    login_status: Optional[str] = None  # 登录状态

class LoginTokenCreate(BaseModel):
    account_id: int = Field(..., description="账号ID")
    platform: str = Field(..., description="平台名称")
    token_type: str = Field(default="cookie", description="令牌类型")
    token_data: str = Field(..., description="令牌数据(JSON格式)")
    user_agent: Optional[str] = Field(None, description="用户代理")
    proxy_info: Optional[str] = Field(None, description="代理信息(JSON格式)")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    proxy_id: Optional[str] = Field(None, description="代理ID")

class LoginTokenResponse(BaseModel):
    id: int
    account_id: int
    platform: str
    token_type: str
    token_data: str
    user_agent: Optional[str]
    proxy_info: Optional[str]
    proxy_id: Optional[str]
    is_valid: bool
    expires_at: Optional[str]
    last_used_at: Optional[str]
    created_at: str
    updated_at: str

async def get_db():
    """获取数据库连接"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        # 如果上下文变量没有设置，尝试初始化数据库连接
        from db import init_mediacrawler_db
        await init_mediacrawler_db()
        return media_crawler_db_var.get()

@account_router.get("/accounts/platforms")
async def get_platforms():
    """获取支持的平台列表"""
    # 当前支持的视频优先平台
    supported_platforms = [
        {"code": "xhs", "name": "小红书", "description": "小红书笔记和评论爬取", "status": "active", "type": "video"},
        {"code": "dy", "name": "抖音", "description": "抖音视频和评论爬取", "status": "active", "type": "video"},
        {"code": "ks", "name": "快手", "description": "快手视频和评论爬取", "status": "active", "type": "video"},
        {"code": "bili", "name": "B站", "description": "B站视频和评论爬取", "status": "active", "type": "video"},
    ]
    
    # 即将支持的文字平台
    coming_soon_platforms = [
        {"code": "wb", "name": "微博", "description": "微博内容和评论爬取（即将支持）", "status": "coming_soon", "type": "text"},
        {"code": "tieba", "name": "贴吧", "description": "贴吧帖子和回复爬取（即将支持）", "status": "coming_soon", "type": "text"},
        {"code": "zhihu", "name": "知乎", "description": "知乎问答和评论爬取（即将支持）", "status": "coming_soon", "type": "text"}
    ]
    
    return {
        "code": 200,
        "message": "获取平台列表成功",
        "data": supported_platforms + coming_soon_platforms
    }

@account_router.get("/accounts/")
async def get_accounts(platform: Optional[str] = None, is_active: Optional[bool] = None):
    """获取账号列表"""
    db = await get_db()
    
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if platform:
            conditions.append("platform = %s")
            params.append(platform)
        
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 查询账号
        query = f"""
        SELECT id, platform, account_name, account_id, username, phone, email, 
               is_active, login_method, created_at, updated_at, notes,
               CASE WHEN password IS NOT NULL AND password != '' THEN 1 ELSE 0 END as has_password
        FROM social_accounts{where_clause}
        ORDER BY created_at DESC
        """
        
        results = await db.query(query, *params)
        
        # 转换结果
        accounts = []
        for row in results:
            account = SocialAccountResponse(
                id=row['id'],
                platform=row['platform'],
                account_name=row['account_name'],
                account_id=row['account_id'],
                username=row['username'],
                phone=row['phone'],
                email=row['email'],
                is_active=bool(row['is_active']),
                login_method=row['login_method'],
                created_at=row['created_at'].isoformat() if row['created_at'] else None,
                updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
                notes=row['notes'],
                has_password=bool(row['has_password'])
            )
            
            # 检查登录状态
            login_status = await check_login_status(db, account.id)
            account.login_status = login_status
            
            accounts.append(account)
        
        return {
            "code": 200,
            "message": "获取账号列表成功",
            "data": accounts
        }
    
    except Exception as e:
        utils.logger.error(f"获取账号列表失败: {e}")
        return {
            "code": 500,
            "message": f"获取账号列表失败: {str(e)}",
            "data": []
        }

@account_router.post("/accounts/")
async def create_account(account: SocialAccountCreate):
    """创建新账号"""
    db = await get_db()
    
    try:
        # 检查账号是否已存在
        check_query = "SELECT COUNT(*) FROM social_accounts WHERE platform = %s AND account_name = %s"
        result = await db.get_first(check_query, account.platform, account.account_name)
        
        if result and list(result.values())[0] > 0:
            return {
                "code": 400,
                "message": "该平台下已存在同名账号",
                "data": None
            }
        
        # 加密密码
        encrypted_password = encrypt_password(account.password) if account.password else None
        
        # 插入新账号
        insert_query = """
        INSERT INTO social_accounts (platform, account_name, account_id, username, password, phone, email, is_active, login_method, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query, 
            account.platform, account.account_name, account.account_id,
            account.username, encrypted_password, account.phone, account.email,
            1 if account.is_active else 0, account.login_method, account.notes
        )
        
        # 获取新创建的账号
        select_query = """
        SELECT id, platform, account_name, account_id, username, phone, email, 
               is_active, login_method, created_at, updated_at, notes,
               CASE WHEN password IS NOT NULL AND password != '' THEN 1 ELSE 0 END as has_password
        FROM social_accounts 
        WHERE platform = %s AND account_name = %s
        ORDER BY created_at DESC LIMIT 1
        """
        
        row = await db.get_first(select_query, account.platform, account.account_name)
        
        if not row:
            return {
                "code": 500,
                "message": "创建账号后无法获取账号信息",
                "data": None
            }
        
        created_account = SocialAccountResponse(
            id=row['id'],
            platform=row['platform'],
            account_name=row['account_name'],
            account_id=row['account_id'],
            username=row['username'],
            phone=row['phone'],
            email=row['email'],
            is_active=bool(row['is_active']),
            login_method=row['login_method'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
            notes=row['notes'],
            has_password=bool(row['has_password']),
            login_status="not_logged_in"
        )
        
        return {
            "code": 200,
            "message": "账号创建成功",
            "data": created_account
        }
    
    except Exception as e:
        utils.logger.error(f"创建账号失败: {e}")
        return {
            "code": 500,
            "message": f"创建账号失败: {str(e)}",
            "data": None
        }

@account_router.get("/accounts/{account_id}")
async def get_account(account_id: int):
    """获取单个账号详情"""
    db = await get_db()
    
    try:
        query = """
        SELECT id, platform, account_name, account_id, username, phone, email, 
               is_active, login_method, created_at, updated_at, notes,
               CASE WHEN password IS NOT NULL AND password != '' THEN 1 ELSE 0 END as has_password
        FROM social_accounts 
        WHERE id = %s
        """
        
        row = await db.get_first(query, account_id)
        
        if not row:
            return {
                "code": 404,
                "message": "账号不存在",
                "data": None
            }
        
        account = SocialAccountResponse(
            id=row['id'],
            platform=row['platform'],
            account_name=row['account_name'],
            account_id=row['account_id'],
            username=row['username'],
            phone=row['phone'],
            email=row['email'],
            is_active=bool(row['is_active']),
            login_method=row['login_method'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
            notes=row['notes'],
            has_password=bool(row['has_password'])
        )
        
        # 检查登录状态
        login_status = await check_login_status(db, account.id)
        account.login_status = login_status
        
        return {
            "code": 200,
            "message": "获取账号详情成功",
            "data": account
        }
    
    except Exception as e:
        utils.logger.error(f"获取账号详情失败: {e}")
        return {
            "code": 500,
            "message": f"获取账号详情失败: {str(e)}",
            "data": None
        }

@account_router.put("/accounts/{account_id}")
async def update_account(account_id: int, account: SocialAccountUpdate):
    """更新账号信息"""
    db = await get_db()
    
    try:
        # 检查账号是否存在
        check_query = "SELECT COUNT(*) FROM social_accounts WHERE id = %s"
        result = await db.get_first(check_query, account_id)
        
        if not result or list(result.values())[0] == 0:
            return {
                "code": 404,
                "message": "账号不存在",
                "data": None
            }
        
        # 构建更新语句
        updates = []
        params = []
        
        if account.account_name is not None:
            updates.append("account_name = %s")
            params.append(account.account_name)
        
        if account.account_id is not None:
            updates.append("account_id = %s")
            params.append(account.account_id)
        
        if account.username is not None:
            updates.append("username = %s")
            params.append(account.username)
        
        if account.password is not None:
            updates.append("password = %s")
            params.append(encrypt_password(account.password) if account.password else None)
        
        if account.phone is not None:
            updates.append("phone = %s")
            params.append(account.phone)
        
        if account.email is not None:
            updates.append("email = %s")
            params.append(account.email)
        
        if account.is_active is not None:
            updates.append("is_active = %s")
            params.append(account.is_active)
        
        if account.login_method is not None:
            updates.append("login_method = %s")
            params.append(account.login_method)
        
        if account.notes is not None:
            updates.append("notes = %s")
            params.append(account.notes)
        
        if not updates:
            return {
                "code": 400,
                "message": "没有提供要更新的字段",
                "data": None
            }
        
        # 执行更新
        update_query = f"UPDATE social_accounts SET {', '.join(updates)} WHERE id = %s"
        params.append(account_id)
        
        await db.execute(update_query, *params)
        
        # 返回更新后的账号信息
        updated_account = await get_account(account_id)
        return updated_account
    
    except Exception as e:
        utils.logger.error(f"更新账号失败: {e}")
        return {
            "code": 500,
            "message": f"更新账号失败: {str(e)}",
            "data": None
        }

@account_router.delete("/accounts/{account_id}")
async def delete_account(account_id: int):
    """删除账号"""
    db = await get_db()
    
    try:
        # 检查账号是否存在
        check_query = "SELECT COUNT(*) FROM social_accounts WHERE id = %s"
        result = await db.get_first(check_query, account_id)
        
        if not result or list(result.values())[0] == 0:
            return {
                "code": 404,
                "message": "账号不存在",
                "data": None
            }
        
        # 删除账号（会级联删除相关的登录凭证）
        delete_query = "DELETE FROM social_accounts WHERE id = %s"
        await db.execute(delete_query, account_id)
        
        return {
            "code": 200,
            "message": "账号删除成功",
            "data": None
        }
    
    except Exception as e:
        utils.logger.error(f"删除账号失败: {e}")
        return {
            "code": 500,
            "message": f"删除账号失败: {str(e)}",
            "data": None
        }

async def check_login_status(db, account_id: int) -> str:
    """检查账号登录状态"""
    try:
        query = """
        SELECT is_valid, expires_at, last_used_at
        FROM login_tokens 
        WHERE account_id = %s AND is_valid = 1
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        result = await db.get_first(query, account_id)
        
        if not result:
            return "not_logged_in"
        
        is_valid, expires_at, last_used_at = result['is_valid'], result['expires_at'], result['last_used_at']
        
        # 检查是否过期
        if expires_at and expires_at < datetime.now():
            # 更新token为无效
            update_query = "UPDATE login_tokens SET is_valid = 0 WHERE account_id = %s"
            await db.execute(update_query, account_id)
            return "expired"
        
        return "logged_in"
    
    except Exception as e:
        utils.logger.error(f"检查登录状态失败: {e}")
        return "unknown" 