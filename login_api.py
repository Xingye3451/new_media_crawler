# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

"""
登录API接口 - 供AI赋能平台调用
提供登录状态检查、启动登录流程、等待验证等功能
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from login_manager import login_manager, LoginStatus, VerificationType


# 创建登录API路由器
login_router = APIRouter(prefix="/api/v1/login", tags=["登录管理"])


class LoginRequest(BaseModel):
    platform: str = Field(..., description="平台: xhs, dy, ks, bili, wb, tieba, zhihu")
    login_type: str = Field(default="qrcode", description="登录类型: qrcode, phone, cookie")
    session_id: Optional[str] = Field(default=None, description="会话ID，如果不提供则创建新会话")


class LoginResponse(BaseModel):
    session_id: str
    status: str
    message: str
    verification_required: bool = False
    verification_type: Optional[str] = None
    verification_data: Optional[Dict] = None
    browser_url: Optional[str] = None
    cookies: Optional[Dict] = None
    local_storage: Optional[Dict] = None


class VerificationRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    timeout: int = Field(default=300, description="等待验证超时时间（秒）")


class VerificationResponse(BaseModel):
    session_id: str
    status: str
    message: str
    verification_required: bool = False
    cookies: Optional[Dict] = None
    local_storage: Optional[Dict] = None


class SessionInfo(BaseModel):
    session_id: str
    platform: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    login_time: Optional[str] = None
    expire_time: Optional[str] = None
    status: str
    verification_required: bool


@login_router.post("/check", response_model=LoginResponse)
async def check_login_status(request: LoginRequest):
    """检查登录状态"""
    try:
        session = await login_manager.check_login_status(
            platform=request.platform,
            session_id=request.session_id
        )
        
        return LoginResponse(
            session_id=session.session_id,
            status=session.status.value,
            message=f"登录状态: {session.status.value}",
            verification_required=session.verification_required,
            verification_type=session.verification_type.value if session.verification_type else None,
            cookies=session.cookies,
            local_storage=session.local_storage
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查登录状态失败: {str(e)}")


@login_router.post("/start", response_model=LoginResponse)
async def start_login_process(request: LoginRequest):
    """启动登录流程"""
    try:
        result = await login_manager.start_login_process(
            platform=request.platform,
            login_type=request.login_type,
            session_id=request.session_id
        )
        
        return LoginResponse(
            session_id=result["session_id"],
            status=result["status"],
            message=result["message"],
            verification_required=result.get("verification_required", False),
            verification_type=result.get("verification_type"),
            verification_data=result.get("verification_data"),
            browser_url=result.get("verification_data", {}).get("browser_url") if result.get("verification_data") else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动登录流程失败: {str(e)}")


@login_router.post("/wait-verification", response_model=VerificationResponse)
async def wait_for_verification(request: VerificationRequest):
    """等待验证完成"""
    try:
        result = await login_manager.wait_for_verification(
            session_id=request.session_id,
            timeout=request.timeout
        )
        
        return VerificationResponse(
            session_id=result["session_id"],
            status=result["status"],
            message=result["message"],
            verification_required=result.get("verification_required", False),
            cookies=result.get("cookies"),
            local_storage=result.get("local_storage")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"等待验证失败: {str(e)}")


@login_router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(platform: Optional[str] = None):
    """获取会话列表"""
    try:
        sessions = []
        for session_id, session in login_manager.sessions.items():
            if platform and session.platform != platform:
                continue
                
            sessions.append(SessionInfo(
                session_id=session.session_id,
                platform=session.platform,
                user_id=session.user_id,
                username=session.username,
                login_time=session.login_time.isoformat() if session.login_time else None,
                expire_time=session.expire_time.isoformat() if session.expire_time else None,
                status=session.status.value,
                verification_required=session.verification_required
            ))
        
        return sessions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@login_router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """获取会话详情"""
    try:
        session = login_manager.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return SessionInfo(
            session_id=session.session_id,
            platform=session.platform,
            user_id=session.user_id,
            username=session.username,
            login_time=session.login_time.isoformat() if session.login_time else None,
            expire_time=session.expire_time.isoformat() if session.expire_time else None,
            status=session.status.value,
            verification_required=session.verification_required
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@login_router.get("/sessions/{session_id}/cookies")
async def get_session_cookies(session_id: str):
    """获取会话cookies"""
    try:
        cookies = await login_manager.get_session_cookies(session_id)
        if not cookies:
            raise HTTPException(status_code=404, detail="会话不存在或没有cookies")
        
        return {"session_id": session_id, "cookies": cookies}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取cookies失败: {str(e)}")


@login_router.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """关闭会话"""
    try:
        await login_manager.close_session(session_id)
        return {"message": "会话已关闭", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"关闭会话失败: {str(e)}")


@login_router.delete("/sessions")
async def close_all_sessions():
    """关闭所有会话"""
    try:
        await login_manager.close_all_sessions()
        return {"message": "所有会话已关闭"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"关闭所有会话失败: {str(e)}")


# 后台任务：定期检查会话状态
async def background_session_check():
    """后台检查会话状态"""
    while True:
        try:
            for session_id, session in list(login_manager.sessions.items()):
                if session.session_id in login_manager.browser_contexts:
                    await login_manager._check_browser_login_status(session)
            
            # 每30秒检查一次
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"后台会话检查异常: {e}")
            await asyncio.sleep(60)


# 启动后台任务
@login_router.on_event("startup")
async def startup_event():
    """应用启动时启动后台任务"""
    asyncio.create_task(background_session_check())


# 关闭时清理资源
@login_router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    await login_manager.close_all_sessions() 