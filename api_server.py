# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import random
import time

# 导入数据模型
from models.content_models import (
    ContentType, Platform, UnifiedContent, ContentListRequest, ContentListResponse,
    CrawlerRequest, MultiPlatformCrawlerRequest, CrawlerResponse, TaskStatusResponse,
    MultiPlatformTaskStatusResponse, UnifiedResultResponse, PLATFORM_MAPPING, SUPPORTED_PLATFORMS
)

import db
import config  # 导入配置模块
from base.base_crawler import AbstractCrawler
from db_init import DatabaseInitializer
from config.env_config_loader import config_loader
from tools import utils

# 导入定时任务调度器
from utils.scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from utils.db_utils import (
    get_account_list_by_platform, 
    check_token_validity,
    cleanup_expired_tokens
)

# 导入Redis管理器
from utils.redis_manager import store_crawler_result, redis_manager

# 导入新的API路由
from api.routes import api_router

# 延迟导入，避免在数据库初始化前导入
# from media_platform.bilibili import BilibiliCrawler
# from media_platform.douyin import DouYinCrawler
# from media_platform.kuaishou import KuaishouCrawler
# from media_platform.tieba import TieBaCrawler
# from media_platform.weibo import WeiboCrawler
# from media_platform.xhs import XiaoHongShuCrawler
# from media_platform.zhihu import ZhihuCrawler
# from proxy import proxy_router, ProxyManager


# 延迟导入多平台抓取功能
multi_platform_crawler = None

# 延迟导入代理管理器
proxy_manager = None

# 创建FastAPI应用
app = FastAPI(
    title="MediaCrawler API",
    description="多平台媒体内容爬虫API服务",
    version="1.0.0"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


# 添加请求验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数验证错误"""
    utils.logger.error("=" * 80)
    utils.logger.error("[VALIDATION_ERROR] FastAPI参数验证失败")
    utils.logger.error(f"[VALIDATION_ERROR] 请求URL: {request.url}")
    utils.logger.error(f"[VALIDATION_ERROR] 请求方法: {request.method}")
    
    # 获取请求体（如果是POST请求）
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                utils.logger.error(f"[VALIDATION_ERROR] 请求体: {body.decode('utf-8')}")
    except Exception as e:
        utils.logger.error(f"[VALIDATION_ERROR] 无法读取请求体: {e}")
    
    # 详细记录验证错误
    utils.logger.error(f"[VALIDATION_ERROR] 验证错误详情:")
    for i, error in enumerate(exc.errors()):
        utils.logger.error(f"  错误 {i+1}:")
        utils.logger.error(f"    - 位置: {error['loc']}")
        utils.logger.error(f"    - 消息: {error['msg']}")
        utils.logger.error(f"    - 类型: {error['type']}")
        if 'input' in error:
            utils.logger.error(f"    - 输入值: {error['input']}")
    
    utils.logger.error("=" * 80)
    
    # 构造友好的错误消息
    error_details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error['loc'])
        error_details.append(f"{field_path}: {error['msg']}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "请求参数验证失败",
            "details": error_details,
            "validation_errors": exc.errors()
        }
    )


# 数据库初始化状态
db_initialized = False

# 延迟注册路由，在数据库初始化后注册
# app.include_router(proxy_router)
# app.include_router(login_router)
# app.include_router(account_router)
# app.include_router(login_management_router)

# 任务状态存储
task_status = {}

# 🆕 任务管理相关函数
async def create_task_record(task_id: str, request: CrawlerRequest):
    """创建任务记录到数据库"""
    try:
        # 构建任务参数JSON
        task_params = {
            "platform": request.platform,
            "keywords": request.keywords,
            "max_notes_count": request.max_notes_count,
            "account_id": request.account_id,
            "session_id": request.session_id,
            "login_type": request.login_type,
            "crawler_type": request.crawler_type,
            "get_comments": request.get_comments,
            "save_data_option": request.save_data_option,
            "use_proxy": request.use_proxy,
            "proxy_strategy": request.proxy_strategy
        }
        
        # 插入任务记录
        sql = """
        INSERT INTO crawler_tasks (
            id, platform, task_type, keywords, status, progress, 
            user_id, params, priority, is_favorite, deleted, is_pinned,
            ip_address, user_security_id, user_signature,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            NOW(), NOW()
        )
        """
        
        await db.execute(sql, (
            task_id,
            request.platform,
            "single_platform",
            request.keywords,
            "pending",
            0.0,
            None,  # user_id
            json.dumps(task_params),
            0,  # priority
            False,  # is_favorite
            False,  # deleted
            False,  # is_pinned
            None,  # ip_address
            None,  # user_security_id
            None,  # user_signature
        ))
        
        utils.logger.info(f"[TASK_RECORD] 任务记录创建成功: {task_id}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_RECORD] 创建任务记录失败: {e}")
        raise

async def save_video_to_database(platform: str, video_data: Dict, task_id: str):
    """保存视频数据到数据库"""
    try:
        if platform == "dy":  # 抖音
            # 构建抖音视频数据
            aweme_data = {
                "aweme_id": video_data.get("aweme_id", ""),
                "aweme_type": video_data.get("aweme_type", "0"),
                "title": video_data.get("title", ""),
                "desc": video_data.get("desc", ""),
                "create_time": video_data.get("create_time", int(time.time())),
                "user_id": video_data.get("user_id", ""),
                "sec_uid": video_data.get("sec_uid", ""),
                "short_user_id": video_data.get("short_user_id", ""),
                "user_unique_id": video_data.get("user_unique_id", ""),
                "nickname": video_data.get("nickname", ""),
                "avatar": video_data.get("avatar", ""),
                "user_signature": video_data.get("user_signature", ""),
                "ip_location": video_data.get("ip_location", ""),
                "liked_count": str(video_data.get("liked_count", 0)),
                "comment_count": str(video_data.get("comment_count", 0)),
                "share_count": str(video_data.get("share_count", 0)),
                "collected_count": str(video_data.get("collected_count", 0)),
                "aweme_url": video_data.get("aweme_url", ""),
                "cover_url": video_data.get("cover_url", ""),
                "video_download_url": video_data.get("video_url", ""),
                "video_play_url": video_data.get("video_play_url", ""),
                "video_share_url": video_data.get("video_share_url", ""),
                "is_favorite": False,
                "minio_url": None,
                "task_id": task_id,
                "source_keyword": video_data.get("source_keyword", ""),
                "add_ts": int(time.time()),
                "last_modify_ts": int(time.time())
            }
            
            # 检查是否已存在
            check_sql = "SELECT id FROM douyin_aweme WHERE aweme_id = %s"
            existing = await db.query(check_sql, aweme_data["aweme_id"])
            
            if existing:
                # 更新现有记录
                update_sql = """
                UPDATE douyin_aweme SET 
                    title = %s, desc = %s, nickname = %s, avatar = %s,
                    liked_count = %s, comment_count = %s, share_count = %s, collected_count = %s,
                    cover_url = %s, video_download_url = %s, video_play_url = %s, video_share_url = %s,
                    task_id = %s, last_modify_ts = %s
                WHERE aweme_id = %s
                """
                await db.execute(update_sql, (
                    aweme_data["title"], aweme_data["desc"], aweme_data["nickname"], aweme_data["avatar"],
                    aweme_data["liked_count"], aweme_data["comment_count"], aweme_data["share_count"], aweme_data["collected_count"],
                    aweme_data["cover_url"], aweme_data["video_download_url"], aweme_data["video_play_url"], aweme_data["video_share_url"],
                    aweme_data["task_id"], aweme_data["last_modify_ts"], aweme_data["aweme_id"]
                ))
            else:
                # 插入新记录
                insert_sql = """
                INSERT INTO douyin_aweme (
                    aweme_id, aweme_type, title, `desc`, create_time, user_id, sec_uid, short_user_id, user_unique_id,
                    nickname, avatar, user_signature, ip_location, liked_count, comment_count, share_count, collected_count,
                    aweme_url, cover_url, video_download_url, video_play_url, video_share_url, is_favorite, minio_url,
                    task_id, source_keyword, add_ts, last_modify_ts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """
                await db.execute(insert_sql, (
                    aweme_data["aweme_id"], aweme_data["aweme_type"], aweme_data["title"], aweme_data["desc"], aweme_data["create_time"],
                    aweme_data["user_id"], aweme_data["sec_uid"], aweme_data["short_user_id"], aweme_data["user_unique_id"],
                    aweme_data["nickname"], aweme_data["avatar"], aweme_data["user_signature"], aweme_data["ip_location"],
                    aweme_data["liked_count"], aweme_data["comment_count"], aweme_data["share_count"], aweme_data["collected_count"],
                    aweme_data["aweme_url"], aweme_data["cover_url"], aweme_data["video_download_url"], aweme_data["video_play_url"],
                    aweme_data["video_share_url"], aweme_data["is_favorite"], aweme_data["minio_url"],
                    aweme_data["task_id"], aweme_data["source_keyword"], aweme_data["add_ts"], aweme_data["last_modify_ts"]
                ))
            
            utils.logger.info(f"[VIDEO_SAVE] 抖音视频保存成功: {aweme_data['aweme_id']}")
            
        elif platform == "xhs":  # 小红书
            # 构建小红书笔记数据
            note_data = {
                "note_id": video_data.get("note_id", ""),
                "type": video_data.get("type", "normal"),
                "title": video_data.get("title", ""),
                "desc": video_data.get("desc", ""),
                "video_url": video_data.get("video_url", ""),
                "time": video_data.get("time", int(time.time())),
                "last_update_time": int(time.time()),
                "user_id": video_data.get("user_id", ""),
                "nickname": video_data.get("nickname", ""),
                "avatar": video_data.get("avatar", ""),
                "ip_location": video_data.get("ip_location", ""),
                "liked_count": str(video_data.get("liked_count", 0)),
                "collected_count": str(video_data.get("collected_count", 0)),
                "comment_count": str(video_data.get("comment_count", 0)),
                "share_count": str(video_data.get("share_count", 0)),
                "image_list": video_data.get("image_list", ""),
                "tag_list": video_data.get("tag_list", ""),
                "note_url": video_data.get("note_url", ""),
                "source_keyword": video_data.get("source_keyword", ""),
                "xsec_token": video_data.get("xsec_token", ""),
                "add_ts": int(time.time()),
                "last_modify_ts": int(time.time())
            }
            
            # 检查是否已存在
            check_sql = "SELECT id FROM xhs_note WHERE note_id = %s"
            existing = await db.query(check_sql, note_data["note_id"])
            
            if existing:
                # 更新现有记录
                update_sql = """
                UPDATE xhs_note SET 
                    title = %s, `desc` = %s, video_url = %s, nickname = %s, avatar = %s,
                    liked_count = %s, collected_count = %s, comment_count = %s, share_count = %s,
                    image_list = %s, tag_list = %s, note_url = %s, last_modify_ts = %s
                WHERE note_id = %s
                """
                await db.execute(update_sql, (
                    note_data["title"], note_data["desc"], note_data["video_url"], note_data["nickname"], note_data["avatar"],
                    note_data["liked_count"], note_data["collected_count"], note_data["comment_count"], note_data["share_count"],
                    note_data["image_list"], note_data["tag_list"], note_data["note_url"], note_data["last_modify_ts"], note_data["note_id"]
                ))
            else:
                # 插入新记录
                insert_sql = """
                INSERT INTO xhs_note (
                    note_id, type, title, `desc`, video_url, time, last_update_time, user_id,
                    nickname, avatar, ip_location, liked_count, collected_count, comment_count, share_count,
                    image_list, tag_list, note_url, source_keyword, xsec_token, add_ts, last_modify_ts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """
                await db.execute(insert_sql, (
                    note_data["note_id"], note_data["type"], note_data["title"], note_data["desc"], note_data["video_url"],
                    note_data["time"], note_data["last_update_time"], note_data["user_id"],
                    note_data["nickname"], note_data["avatar"], note_data["ip_location"], note_data["liked_count"],
                    note_data["collected_count"], note_data["comment_count"], note_data["share_count"],
                    note_data["image_list"], note_data["tag_list"], note_data["note_url"], note_data["source_keyword"],
                    note_data["xsec_token"], note_data["add_ts"], note_data["last_modify_ts"]
                ))
            
            utils.logger.info(f"[VIDEO_SAVE] 小红书笔记保存成功: {note_data['note_id']}")
            
        # 可以继续添加其他平台的处理逻辑...
        
    except Exception as e:
        utils.logger.error(f"[VIDEO_SAVE] 保存视频数据失败: {e}")
        raise

async def save_comment_to_database(platform: str, comment_data: Dict, task_id: str):
    """保存评论数据到数据库"""
    try:
        if platform == "dy":  # 抖音评论
            comment_record = {
                "comment_id": comment_data.get("comment_id", ""),
                "aweme_id": comment_data.get("aweme_id", ""),
                "content": comment_data.get("content", ""),
                "create_time": comment_data.get("create_time", int(time.time())),
                "user_id": comment_data.get("user_id", ""),
                "sec_uid": comment_data.get("sec_uid", ""),
                "short_user_id": comment_data.get("short_user_id", ""),
                "nickname": comment_data.get("nickname", ""),
                "avatar": comment_data.get("avatar", ""),
                "ip_location": comment_data.get("ip_location", ""),
                "sub_comment_count": str(comment_data.get("sub_comment_count", 0)),
                "parent_comment_id": comment_data.get("parent_comment_id", ""),
                "like_count": str(comment_data.get("like_count", 0)),
                "pictures": comment_data.get("pictures", ""),
                "add_ts": int(time.time()),
                "last_modify_ts": int(time.time())
            }
            
            # 检查是否已存在
            check_sql = "SELECT id FROM douyin_aweme_comment WHERE comment_id = %s"
            existing = await db.query(check_sql, comment_record["comment_id"])
            
            if not existing:
                # 插入新评论记录
                insert_sql = """
                INSERT INTO douyin_aweme_comment (
                    comment_id, aweme_id, content, create_time, user_id, sec_uid, short_user_id,
                    nickname, avatar, ip_location, sub_comment_count, parent_comment_id, like_count,
                    pictures, add_ts, last_modify_ts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """
                await db.execute(insert_sql, (
                    comment_record["comment_id"], comment_record["aweme_id"], comment_record["content"], comment_record["create_time"],
                    comment_record["user_id"], comment_record["sec_uid"], comment_record["short_user_id"],
                    comment_record["nickname"], comment_record["avatar"], comment_record["ip_location"], comment_record["sub_comment_count"],
                    comment_record["parent_comment_id"], comment_record["like_count"], comment_record["pictures"],
                    comment_record["add_ts"], comment_record["last_modify_ts"]
                ))
                
                utils.logger.info(f"[COMMENT_SAVE] 抖音评论保存成功: {comment_record['comment_id']}")
        
        elif platform == "xhs":  # 小红书评论
            comment_record = {
                "comment_id": comment_data.get("comment_id", ""),
                "create_time": comment_data.get("create_time", int(time.time())),
                "note_id": comment_data.get("note_id", ""),
                "content": comment_data.get("content", ""),
                "user_id": comment_data.get("user_id", ""),
                "nickname": comment_data.get("nickname", ""),
                "avatar": comment_data.get("avatar", ""),
                "ip_location": comment_data.get("ip_location", ""),
                "sub_comment_count": comment_data.get("sub_comment_count", 0),
                "pictures": comment_data.get("pictures", ""),
                "parent_comment_id": comment_data.get("parent_comment_id", ""),
                "like_count": str(comment_data.get("like_count", 0)),
                "add_ts": int(time.time()),
                "last_modify_ts": int(time.time())
            }
            
            # 检查是否已存在
            check_sql = "SELECT id FROM xhs_note_comment WHERE comment_id = %s"
            existing = await db.query(check_sql, comment_record["comment_id"])
            
            if not existing:
                # 插入新评论记录
                insert_sql = """
                INSERT INTO xhs_note_comment (
                    comment_id, create_time, note_id, content, user_id, nickname, avatar,
                    ip_location, sub_comment_count, pictures, parent_comment_id, like_count,
                    add_ts, last_modify_ts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s
                )
                """
                await db.execute(insert_sql, (
                    comment_record["comment_id"], comment_record["create_time"], comment_record["note_id"], comment_record["content"],
                    comment_record["user_id"], comment_record["nickname"], comment_record["avatar"],
                    comment_record["ip_location"], comment_record["sub_comment_count"], comment_record["pictures"],
                    comment_record["parent_comment_id"], comment_record["like_count"],
                    comment_record["add_ts"], comment_record["last_modify_ts"]
                ))
                
                utils.logger.info(f"[COMMENT_SAVE] 小红书评论保存成功: {comment_record['comment_id']}")
        
        # 可以继续添加其他平台的评论处理逻辑...
        
    except Exception as e:
        utils.logger.error(f"[COMMENT_SAVE] 保存评论数据失败: {e}")
        raise

async def update_task_progress(task_id: str, progress: float, status: str = None, result_count: int = None):
    """更新任务进度"""
    try:
        update_fields = ["progress = %s"]
        update_values = [progress]
        
        if status:
            update_fields.append("status = %s")
            update_values.append(status)
        
        if result_count is not None:
            update_fields.append("result_count = %s")
            update_values.append(result_count)
        
        update_fields.append("updated_at = NOW()")
        update_values.append(task_id)
        
        sql = f"UPDATE crawler_tasks SET {', '.join(update_fields)} WHERE id = %s"
        await db.execute(sql, update_values)
        
        utils.logger.info(f"[TASK_PROGRESS] 任务进度更新: {task_id}, 进度: {progress}, 状态: {status}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_PROGRESS] 更新任务进度失败: {e}")

async def log_task_step(task_id: str, platform: str, step: str, message: str, log_level: str = "INFO", progress: int = None):
    """记录任务步骤日志"""
    try:
        sql = """
        INSERT INTO crawler_task_logs (
            task_id, platform, account_id, log_level, message, step, progress, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        await db.execute(sql, (
            task_id,
            platform,
            None,  # account_id
            log_level,
            message,
            step,
            progress or 0
        ))
        
        utils.logger.info(f"[TASK_LOG] {task_id} - {step}: {message}")
        
    except Exception as e:
        utils.logger.error(f"[TASK_LOG] 记录任务日志失败: {e}")

class PlatformComingSoonException(Exception):
    """平台即将支持异常"""
    pass


class CrawlerFactory:
    # 视频优先平台 - 当前支持
    VIDEO_PLATFORMS = ["xhs", "dy", "ks", "bili"]
    
    # 文字平台 - 即将支持
    COMING_SOON_PLATFORMS = {
        "wb": "微博",
        "tieba": "贴吧", 
        "zhihu": "知乎"
    }

    @staticmethod
    def _get_crawler_class(platform: str):
        """延迟导入爬虫类 - 仅支持视频平台"""
        if platform == "xhs":
            from media_platform.xhs import XiaoHongShuCrawler
            return XiaoHongShuCrawler
        elif platform == "dy":
            from media_platform.douyin import DouYinCrawler
            return DouYinCrawler
        elif platform == "ks":
            from media_platform.kuaishou import KuaishouCrawler
            return KuaishouCrawler
        elif platform == "bili":
            from media_platform.bilibili import BilibiliCrawler
            return BilibiliCrawler
        else:
            raise ValueError(f"不支持的平台: {platform}")

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        # 检查是否为即将支持的平台
        if platform in CrawlerFactory.COMING_SOON_PLATFORMS:
            platform_name = CrawlerFactory.COMING_SOON_PLATFORMS[platform]
            raise PlatformComingSoonException(f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。")
        
        # 检查是否为支持的视频平台
        crawler_class = CrawlerFactory._get_crawler_class(platform)
        return crawler_class()

async def run_crawler_task(task_id: str, request: CrawlerRequest):
    """后台运行爬虫任务"""
    try:
        utils.logger.info("█" * 100)
        utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬虫任务")
        utils.logger.info(f"[TASK_{task_id}] 📝 请求参数详情:")
        utils.logger.info(f"[TASK_{task_id}]   ├─ platform: {request.platform}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ keywords: {request.keywords}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ max_count: {request.max_notes_count}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ account_id: {request.account_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ session_id: {request.session_id}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ login_type: {request.login_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ crawler_type: {request.crawler_type}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ get_comments: {request.get_comments}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ save_data_option: {request.save_data_option}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ use_proxy: {request.use_proxy}")
        utils.logger.info(f"[TASK_{task_id}]   └─ proxy_strategy: {request.proxy_strategy}")
        
        # 🆕 创建任务记录到数据库
        utils.logger.info(f"[TASK_{task_id}] 📝 创建任务记录到数据库...")
        await create_task_record(task_id, request)
        utils.logger.info(f"[TASK_{task_id}] ✅ 任务记录创建成功")
        
        # 更新任务状态
        utils.logger.info(f"[TASK_{task_id}] 🔄 更新任务状态为运行中...")
        task_status[task_id]["status"] = "running"
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        utils.logger.info(f"[TASK_{task_id}] ✅ 任务状态已更新")
        
        # 🆕 更新数据库中的任务状态
        await update_task_progress(task_id, 0.0, "running")
        await log_task_step(task_id, request.platform, "task_start", "任务开始执行", "INFO", 0)
        
        # 检查登录状态
        utils.logger.info(f"[任务 {task_id}] 检查登录状态...")
        await log_task_step(task_id, request.platform, "login_check", "检查登录状态", "INFO", 10)
        
        from login_manager import login_manager
        
        if request.session_id:
            utils.logger.info(f"[任务 {task_id}] 使用指定的会话ID: {request.session_id}")
            # 使用指定的会话ID
            session = await login_manager.check_login_status(request.platform, request.session_id)
            if session.status.value == "need_verification":
                utils.logger.warning(f"[任务 {task_id}] 需要验证，会话状态: {session.status.value}")
                task_status[task_id]["status"] = "need_verification"
                task_status[task_id]["error"] = "需要验证"
                task_status[task_id]["session_id"] = session.session_id
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "need_verification")
                await log_task_step(task_id, request.platform, "login_failed", "需要验证", "WARN", 0)
                return
            elif session.status.value == "logged_in":
                utils.logger.info(f"[任务 {task_id}] 会话状态正常")
                await log_task_step(task_id, request.platform, "login_success", "登录状态正常", "INFO", 20)
                # 已登录，cookies由爬虫直接从数据库读取
            else:
                utils.logger.warning(f"[任务 {task_id}] 会话状态异常: {session.status.value}")
                await log_task_step(task_id, request.platform, "login_error", f"会话状态异常: {session.status.value}", "ERROR", 0)
        else:
            utils.logger.info(f"[任务 {task_id}] 查找平台 {request.platform} 的最新会话")
            # 查找平台的最新会话
            session = await login_manager.check_login_status(request.platform)
            if session.status.value == "logged_in":
                utils.logger.info(f"[任务 {task_id}] 找到有效会话")
                await log_task_step(task_id, request.platform, "login_success", "找到有效会话", "INFO", 20)
                # 已登录，cookies由爬虫直接从数据库读取
            elif session.status.value in ["not_logged_in", "expired", "need_verification"]:
                utils.logger.warning(f"[任务 {task_id}] 需要登录，会话状态: {session.status.value}")
                # 需要登录或验证
                task_status[task_id]["status"] = "need_login"
                task_status[task_id]["error"] = "需要登录"
                task_status[task_id]["session_id"] = session.session_id
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "need_login")
                await log_task_step(task_id, request.platform, "login_failed", "需要登录", "WARN", 0)
                return
                
        # 检查指定账号的凭证有效性（如果提供了账号ID）
        if request.account_id:
            utils.logger.info(f"[任务 {task_id}] 检查指定账号凭证有效性: {request.account_id}")
            await log_task_step(task_id, request.platform, "account_check", f"检查账号凭证: {request.account_id}", "INFO", 25)
            
            validity = await check_token_validity(request.platform, request.account_id)
            if validity["status"] not in ["valid", "expiring_soon"]:
                utils.logger.error(f"[任务 {task_id}] 指定账号凭证无效: {validity['message']}")
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = f"指定账号凭证无效: {validity['message']}"
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "failed")
                await log_task_step(task_id, request.platform, "account_failed", f"账号凭证无效: {validity['message']}", "ERROR", 0)
                return
            elif validity["status"] == "expiring_soon":
                utils.logger.warning(f"[任务 {task_id}] 指定账号凭证即将过期: {validity['expires_at']}")
                await log_task_step(task_id, request.platform, "account_warning", f"账号凭证即将过期: {validity['expires_at']}", "WARN", 30)
            else:
                await log_task_step(task_id, request.platform, "account_success", "账号凭证有效", "INFO", 30)
        
        # 设置爬虫配置
        utils.logger.info(f"[TASK_{task_id}] ⚙️ 设置爬虫配置...")
        await log_task_step(task_id, request.platform, "config_setup", "设置爬虫配置", "INFO", 35)
        
        config.PLATFORM = request.platform
        config.KEYWORDS = request.keywords
        config.CRAWLER_MAX_NOTES_COUNT = request.max_notes_count
        config.CRAWLER_TYPE = request.crawler_type or "search"
        config.LOGIN_TYPE = request.login_type or "qrcode"
        config.ENABLE_GET_COMMENTS = request.get_comments if request.get_comments is not None else True
        config.SAVE_DATA_OPTION = request.save_data_option or "json"
        
        # 设置代理配置
        if hasattr(config, 'ENABLE_IP_PROXY'):
            config.ENABLE_IP_PROXY = request.use_proxy if request.use_proxy is not None else False
        if hasattr(config, 'PROXY_STRATEGY'):
            config.PROXY_STRATEGY = request.proxy_strategy or "disabled"
        
        # 设置账号ID（如果指定）
        if request.account_id:
            config.ACCOUNT_ID = str(request.account_id)  # 转换为字符串，因为config可能期望字符串
            utils.logger.info(f"[TASK_{task_id}] 🎯 设置指定账号ID: {request.account_id}")
        else:
            config.ACCOUNT_ID = None
            utils.logger.info(f"[TASK_{task_id}] 👤 使用默认账号")
        
        utils.logger.info(f"[TASK_{task_id}] ✅ 配置完成:")
        utils.logger.info(f"[TASK_{task_id}]   ├─ Platform: {config.PLATFORM}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ Keywords: {config.KEYWORDS}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ CrawlerType: {config.CRAWLER_TYPE}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ LoginType: {config.LOGIN_TYPE}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ Comments: {config.ENABLE_GET_COMMENTS}")
        utils.logger.info(f"[TASK_{task_id}]   ├─ SaveOption: {config.SAVE_DATA_OPTION}")
        utils.logger.info(f"[TASK_{task_id}]   └─ AccountID: {config.ACCOUNT_ID}")
        
        await log_task_step(task_id, request.platform, "config_complete", "爬虫配置完成", "INFO", 40)
        
        # 初始化数据库（如果需要保存到数据库）
        if config.SAVE_DATA_OPTION == "db":
            utils.logger.info(f"[TASK_{task_id}] 💾 初始化数据库连接...")
            await log_task_step(task_id, request.platform, "db_init", "初始化数据库连接", "INFO", 45)
            
            try:
                await db.init_db()
                utils.logger.info(f"[TASK_{task_id}] ✅ 数据库连接初始化成功")
                await log_task_step(task_id, request.platform, "db_success", "数据库连接初始化成功", "INFO", 50)
            except Exception as e:
                utils.logger.error(f"[TASK_{task_id}] ❌ 数据库连接初始化失败: {e}")
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = f"数据库连接初始化失败: {e}"
                task_status[task_id]["updated_at"] = datetime.now().isoformat()
                await update_task_progress(task_id, 0.0, "failed")
                await log_task_step(task_id, request.platform, "db_failed", f"数据库连接初始化失败: {e}", "ERROR", 0)
                return
        
        # 创建爬虫实例
        utils.logger.info(f"[TASK_{task_id}] 🏭 创建爬虫实例...")
        await log_task_step(task_id, request.platform, "crawler_create", "创建爬虫实例", "INFO", 55)
        
        crawler_instance: AbstractCrawler = CrawlerFactory.create_crawler(config.PLATFORM)
        utils.logger.info(f"[TASK_{task_id}] ✅ 爬虫实例创建成功: {type(crawler_instance).__name__}")
        await log_task_step(task_id, request.platform, "crawler_ready", f"爬虫实例创建成功: {type(crawler_instance).__name__}", "INFO", 60)
        
        # 🚀 新增：爬虫直接写入Redis和数据库
        utils.logger.info(f"[TASK_{task_id}] 📊 准备接收爬虫数据到Redis和数据库...")
        
        try:
            # 创建Redis和数据库存储回调函数，让爬虫直接写入
            async def storage_callback(platform: str, data: Dict, data_type: str = "video"):
                """Redis和数据库存储回调函数，供爬虫调用"""
                try:
                    if data_type == "video":
                        # 转换视频数据格式
                        video_data = {
                            "video_id": data.get("aweme_id" if platform == "dy" else "note_id", ""),
                            "title": data.get("title", ""),
                            "author_name": data.get("author_name", ""),
                            "download_url": data.get("video_url", ""),
                            "liked_count": data.get("liked_count", 0),
                            "comment_count": data.get("comment_count", 0),
                            "play_count": data.get("view_count", 0),
                            "share_count": data.get("share_count", 0),
                            "collected_count": data.get("collected_count", 0),
                            "video_size": 0,
                            "duration": data.get("duration", 0),
                            "cover_url": data.get("cover_url", ""),
                            "create_time": data.get("create_time", ""),
                            "raw_data": data  # 保存原始数据
                        }
                        
                        # 存储到Redis
                        await redis_manager.store_video_data(task_id, platform, video_data)
                        utils.logger.info(f"[TASK_{task_id}] ✅ 视频数据已存储到Redis: {video_data['video_id']}")
                        
                        # 🆕 存储到数据库
                        await save_video_to_database(platform, data, task_id)
                        utils.logger.info(f"[TASK_{task_id}] ✅ 视频数据已存储到数据库: {video_data['video_id']}")
                        
                    elif data_type == "comment":
                        # 处理评论数据
                        video_id = data.get("aweme_id" if platform == "dy" else "note_id", "")
                        if video_id:
                            comment_data = {
                                "comment_id": data.get("comment_id", ""),
                                "content": data.get("content", ""),
                                "author_name": data.get("comment_user_name", ""),
                                "liked_count": data.get("liked_count", 0),
                                "create_time": data.get("create_time", ""),
                                "raw_data": data  # 保存原始数据
                            }
                            
                            # 存储评论到Redis
                            await redis_manager.store_hot_comments(platform, video_id, [comment_data])
                            utils.logger.info(f"[TASK_{task_id}] ✅ 评论数据已存储到Redis: {comment_data['comment_id']}")
                            
                            # 🆕 存储评论到数据库
                            await save_comment_to_database(platform, data, task_id)
                            utils.logger.info(f"[TASK_{task_id}] ✅ 评论数据已存储到数据库: {comment_data['comment_id']}")
                            
                except Exception as e:
                    utils.logger.error(f"[TASK_{task_id}] ❌ 存储回调失败: {e}")
            
            # 将回调函数传递给爬虫
            crawler_instance.set_storage_callback(storage_callback)
            
            # 执行爬取
            utils.logger.info(f"[TASK_{task_id}] 🚀 开始执行爬取...")
            await log_task_step(task_id, request.platform, "crawler_start", "开始执行爬取", "INFO", 65)
            task_status[task_id]["progress"] = 0.1
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.1, "running")
            
            utils.logger.info(f"[TASK_{task_id}] 📞 调用爬虫start()方法...")
            await crawler_instance.start()
            utils.logger.info(f"[TASK_{task_id}] ✅ 爬虫执行完成")
            await log_task_step(task_id, request.platform, "crawler_complete", "爬虫执行完成", "INFO", 80)
            
            task_status[task_id]["progress"] = 0.8
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            await update_task_progress(task_id, 0.8, "running")
            
            # 从Redis读取任务结果
            utils.logger.info(f"[TASK_{task_id}] 📊 从Redis读取任务结果...")
            await log_task_step(task_id, request.platform, "result_read", "读取任务结果", "INFO", 85)
            
            # 获取任务统计信息
            task_result = await redis_manager.get_task_result(task_id)
            if task_result:
                videos_count = int(task_result.get("total_videos", 0))
                comments_count = int(task_result.get("total_comments", 0))
                
                # 更新任务结果信息
                task_status[task_id]["result"] = {
                    "success": True,
                    "data_count": videos_count,
                    "comment_count": comments_count,
                    "message": f"成功爬取 {videos_count} 个视频，{comments_count} 条评论"
                }
                
                utils.logger.info(f"[TASK_{task_id}] ✅ Redis读取完成: {videos_count} 个视频，{comments_count} 条评论")
                await log_task_step(task_id, request.platform, "result_success", f"读取完成: {videos_count} 个视频，{comments_count} 条评论", "INFO", 90)
            else:
                utils.logger.warning(f"[TASK_{task_id}] ⚠️ 未找到任务结果数据")
                task_status[task_id]["result"] = {
                    "success": True,
                    "data_count": 0,
                    "comment_count": 0,
                    "message": "任务完成，但未找到数据"
                }
                await log_task_step(task_id, request.platform, "result_empty", "未找到任务结果数据", "WARN", 90)
                    
        except Exception as redis_e:
            utils.logger.error(f"[TASK_{task_id}] ❌ Redis存储失败: {redis_e}")
            # 不影响主任务状态，只记录错误
            task_status[task_id]["redis_error"] = str(redis_e)

        # 兼容原有逻辑：读取结果文件（虽然现在不再使用文件存储）
        utils.logger.info(f"[任务 {task_id}] 读取爬取结果...")
        result_file_path = None
        data_dir = config_loader.get('app.data_dir', './data')
        
        # 查找最新的数据文件
        json_pattern = f"{data_dir}/*{config.PLATFORM}*.json"
        import glob
        json_files = glob.glob(json_pattern)
        if json_files:
            result_file_path = max(json_files, key=os.path.getmtime)
            utils.logger.info(f"[任务 {task_id}] 找到结果文件: {result_file_path}")
            
            # 读取并解析结果
            try:
                with open(result_file_path, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                    data_count = len(result_data) if isinstance(result_data, list) else 1
                    utils.logger.info(f"[任务 {task_id}] 成功爬取数据 {data_count} 条")
                    
                task_status[task_id]["result"] = {
                    "success": True,
                    "data_count": data_count,
                    "file_path": result_file_path,
                    "message": f"成功爬取 {data_count} 条数据"
                }
            except Exception as e:
                utils.logger.error(f"[任务 {task_id}] 读取结果文件失败: {e}")
                task_status[task_id]["result"] = {
                    "success": False,
                    "data_count": 0,
                    "file_path": result_file_path,
                    "message": f"读取结果失败: {e}"
                }
        else:
            utils.logger.warning(f"[任务 {task_id}] 未找到结果文件")
            task_status[task_id]["result"] = {
                "success": False,
                "data_count": 0,
                "file_path": None,
                "message": "未找到结果文件"
            }
        
        # 任务完成
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["progress"] = 1.0
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 1.0, "completed", task_status[task_id]["result"]["data_count"])
        await log_task_step(task_id, request.platform, "task_complete", "任务执行完成", "INFO", 100)
        
        # 关闭数据库连接（如果使用了数据库）
        if config.SAVE_DATA_OPTION == "db":
            try:
                utils.logger.info(f"[TASK_{task_id}] 🔌 关闭数据库连接...")
                await db.close()
                utils.logger.info(f"[TASK_{task_id}] ✅ 数据库连接已关闭")
            except Exception as e:
                utils.logger.warning(f"[TASK_{task_id}] ⚠️ 关闭数据库连接时出现警告: {e}")
        
        utils.logger.info(f"[TASK_{task_id}] 🎉 爬虫任务执行完成")
        utils.logger.info("█" * 100)
        
    except Exception as e:
        utils.logger.error("█" * 100)
        utils.logger.error(f"[TASK_{task_id}] ❌ 爬虫任务执行失败")
        utils.logger.error(f"[TASK_{task_id}] 🐛 错误详情: {str(e)}")
        utils.logger.error(f"[TASK_{task_id}] 📍 错误类型: {type(e).__name__}")
        import traceback
        utils.logger.error(f"[TASK_{task_id}] 📊 错误堆栈:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                utils.logger.error(f"[TASK_{task_id}]     {line}")
        
        # 更新任务状态
        utils.logger.error(f"[TASK_{task_id}] 🔄 更新任务状态为失败...")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        await update_task_progress(task_id, 0.0, "failed")
        await log_task_step(task_id, request.platform, "task_failed", f"任务执行失败: {str(e)}", "ERROR", 0)
        utils.logger.error(f"[TASK_{task_id}] ✅ 任务状态已更新")
        
        # 关闭数据库连接（如果使用了数据库）
        if config.SAVE_DATA_OPTION == "db":
            try:
                utils.logger.error(f"[TASK_{task_id}] 🔌 关闭数据库连接...")
                await db.close()
                utils.logger.error(f"[TASK_{task_id}] ✅ 数据库连接已关闭")
            except Exception as db_e:
                utils.logger.error(f"[TASK_{task_id}] ⚠️ 关闭数据库连接时出现警告: {db_e}")
        
        utils.logger.error("█" * 100)

async def run_multi_platform_task(task_id: str, request: MultiPlatformCrawlerRequest):
    """后台运行多平台抓取任务"""
    if multi_platform_crawler is None:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = "多平台抓取功能暂不可用"
        task_status[task_id]["updated_at"] = datetime.now().isoformat()
        return
    
    try:
        # 创建多平台抓取任务
        task_id_created = multi_platform_crawler.create_task(
            platforms=request.platforms,
            keywords=request.keywords,
            max_count_per_platform=request.max_count_per_platform,
            enable_comments=request.enable_comments,
            enable_images=request.enable_images,
            save_format=request.save_format,
            use_proxy=request.use_proxy,
            proxy_strategy=request.proxy_strategy
        )
        
        # 启动任务
        success = await multi_platform_crawler.start_task(task_id_created)
        
        if success:
            # 更新任务状态
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["multi_platform_task_id"] = task_id_created
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
        else:
            # 更新任务状态为失败
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = "多平台抓取任务失败"
            task_status[task_id]["updated_at"] = datetime.now().isoformat()
            
    except Exception as e:
        # 更新任务状态为失败
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["updated_at"] = datetime.now().isoformat()

@app.post("/api/v1/crawler/start", response_model=CrawlerResponse)
async def start_crawler(request: CrawlerRequest, background_tasks: BackgroundTasks):
    """启动爬虫任务"""
    # 记录详细的请求信息
    utils.logger.info("=" * 80)
    utils.logger.info("[CRAWLER_START] 收到爬虫启动请求")
    utils.logger.info(f"[CRAWLER_START] 请求参数详情:")
    utils.logger.info(f"  - platform: {request.platform}")
    utils.logger.info(f"  - keywords: {request.keywords}")
    utils.logger.info(f"  - max_notes_count: {request.max_notes_count}")
    utils.logger.info(f"  - account_id: {request.account_id}")
    utils.logger.info(f"  - session_id: {request.session_id}")
    utils.logger.info(f"  - login_type: {request.login_type}")
    utils.logger.info(f"  - crawler_type: {request.crawler_type}")
    utils.logger.info(f"  - get_comments: {request.get_comments}")
    utils.logger.info(f"  - save_data_option: {request.save_data_option}")
    utils.logger.info(f"  - use_proxy: {request.use_proxy}")
    utils.logger.info(f"  - proxy_strategy: {request.proxy_strategy}")
    
    try:
        # 验证平台参数 - 检查即将支持的平台
        try:
            CrawlerFactory.create_crawler(request.platform)
        except PlatformComingSoonException as e:
            error_msg = str(e)
            utils.logger.warning(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        except ValueError as e:
            error_msg = f"不支持的平台: {request.platform}，当前支持的平台: xhs, dy, ks, bili"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        # 验证关键词
        if not request.keywords or not request.keywords.strip():
            error_msg = "关键词不能为空"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        # 验证最大数量
        if request.max_notes_count <= 0:
            error_msg = f"最大爬取数量必须大于0，当前值: {request.max_notes_count}"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        # 验证账号ID（如果提供）
        if request.account_id is not None:
            if request.account_id <= 0:
                error_msg = f"账号ID必须大于0，当前值: {request.account_id}"
                utils.logger.error(f"[CRAWLER_START] {error_msg}")
                raise HTTPException(status_code=422, detail=error_msg)
            utils.logger.info(f"[CRAWLER_START] 指定账号ID: {request.account_id}")
        
        # 验证其他参数
        if request.login_type not in ["qrcode", "phone", "email", "password"]:
            error_msg = f"不支持的登录类型: {request.login_type}，支持的类型: qrcode, phone, email, password"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        if request.crawler_type not in ["search", "detail", "creator"]:
            error_msg = f"不支持的爬虫类型: {request.crawler_type}，支持的类型: search, detail, creator"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        if request.save_data_option not in ["db", "json", "csv"]:
            error_msg = f"不支持的数据保存选项: {request.save_data_option}，支持的选项: db, json, csv"
            utils.logger.error(f"[CRAWLER_START] {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        
        utils.logger.info(f"[CRAWLER_START] 参数验证通过")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        utils.logger.info(f"[CRAWLER_START] 生成任务ID: {task_id}")
        
        # 初始化任务状态
        task_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "request_params": {
                "platform": request.platform,
                "keywords": request.keywords,
                "max_notes_count": request.max_notes_count,
                "account_id": request.account_id,
                "session_id": request.session_id,
                "login_type": request.login_type,
                "crawler_type": request.crawler_type,
                "get_comments": request.get_comments,
                "save_data_option": request.save_data_option,
                "use_proxy": request.use_proxy,
                "proxy_strategy": request.proxy_strategy
            }
        }
        
        utils.logger.info(f"[CRAWLER_START] 任务状态已初始化")
        
        # 在后台运行爬虫任务
        background_tasks.add_task(run_crawler_task, task_id, request)
        utils.logger.info(f"[CRAWLER_START] 后台任务已添加")
        
        response = CrawlerResponse(
            task_id=task_id,
            status="pending",
            message="爬虫任务已启动，正在检查登录状态..."
        )
        
        utils.logger.info(f"[CRAWLER_START] 响应数据: {response.dict()}")
        utils.logger.info("=" * 80)
        
        return response
        
    except HTTPException as he:
        utils.logger.error(f"[CRAWLER_START] HTTP异常: 状态码={he.status_code}, 详情={he.detail}")
        utils.logger.info("=" * 80)
        raise he
    except Exception as e:
        error_msg = f"启动爬虫失败: {str(e)}"
        utils.logger.error(f"[CRAWLER_START] 系统异常: {error_msg}")
        utils.logger.error(f"[CRAWLER_START] 异常类型: {type(e).__name__}")
        import traceback
        utils.logger.error(f"[CRAWLER_START] 异常堆栈: {traceback.format_exc()}")
        utils.logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=error_msg)

# 新增多平台抓取API
@app.post("/api/v1/multi-platform/start", response_model=CrawlerResponse)
async def start_multi_platform_crawler(request: MultiPlatformCrawlerRequest, background_tasks: BackgroundTasks):
    """启动多平台抓取任务"""
    if multi_platform_crawler is None:
        raise HTTPException(status_code=503, detail="多平台抓取功能暂不可用")
    
    try:
        # 验证平台
        invalid_platforms = [p for p in request.platforms if p not in multi_platform_crawler.platform_mapping]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {invalid_platforms}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        task_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "platforms": request.platforms,
            "keywords": request.keywords,
            "progress": {"total": len(request.platforms), "completed": 0, "failed": 0, "pending": len(request.platforms)},
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 在后台运行多平台抓取任务
        background_tasks.add_task(run_multi_platform_task, task_id, request)
        
        return CrawlerResponse(
            task_id=task_id,
            status="pending",
            message=f"多平台抓取任务已启动，平台: {', '.join(request.platforms)}，关键词: {request.keywords}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动多平台抓取失败: {str(e)}")

@app.get("/api/v1/crawler/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(**task_status[task_id])

# 新增多平台任务状态API
@app.get("/api/v1/multi-platform/status/{task_id}", response_model=MultiPlatformTaskStatusResponse)
async def get_multi_platform_task_status(task_id: str):
    """获取多平台任务状态"""
    if multi_platform_crawler is None:
        raise HTTPException(status_code=503, detail="多平台抓取功能暂不可用")
    
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = task_status[task_id]
    
    # 如果是多平台任务，获取详细状态
    if "multi_platform_task_id" in task:
        multi_task_id = task["multi_platform_task_id"]
        multi_status = multi_platform_crawler.get_task_status(multi_task_id)
        
        if multi_status:
            return MultiPlatformTaskStatusResponse(
                task_id=task_id,
                status=multi_status["status"],
                platforms=multi_status["platforms"],
                keywords=multi_status["keywords"],
                progress=multi_status["progress"],
                results=multi_status.get("results"),
                errors=multi_status.get("errors"),
                created_at=task["created_at"],
                started_at=task.get("started_at"),
                completed_at=task.get("completed_at")
            )
    
    # 返回基本任务状态
    return MultiPlatformTaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        platforms=task.get("platforms", []),
        keywords=task.get("keywords", ""),
        progress=task.get("progress", {}),
        results=task.get("results"),
        errors=task.get("errors"),
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at")
    )

# 新增获取多平台任务结果API
@app.get("/api/v1/multi-platform/results/{task_id}")
async def get_multi_platform_results(task_id: str, format_type: str = "table"):
    """获取多平台任务结果"""
    if multi_platform_crawler is None:
        raise HTTPException(status_code=503, detail="多平台抓取功能暂不可用")
    
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = task_status[task_id]
    
    # 如果是多平台任务，获取详细结果
    if "multi_platform_task_id" in task:
        multi_task_id = task["multi_platform_task_id"]
        results = multi_platform_crawler.get_task_results(multi_task_id)
        
        if results:
            if format_type == "json":
                # JSON格式返回
                json_results = []
                for result in results:
                    json_results.append({
                        "platform": result.platform,
                        "platform_name": multi_platform_crawler.platform_mapping.get(result.platform, result.platform),
                        "content_id": result.content_id,
                        "title": result.title,
                        "author": result.author,
                        "publish_time": result.publish_time,
                        "content": result.content,
                        "likes": result.likes,
                        "comments": result.comments,
                        "shares": result.shares,
                        "views": result.views,
                        "download_links": result.download_links,
                        "tags": result.tags,
                        "url": result.url
                    })
                
                return {
                    "task_id": task_id,
                    "total_count": len(results),
                    "format": "json",
                    "results": json_results
                }
            else:
                # 表格格式返回
                table_results = []
                for result in results:
                    platform_name = multi_platform_crawler.platform_mapping.get(result.platform, result.platform)
                    table_results.append({
                        "platform": platform_name,
                        "title": result.title,
                        "author": result.author,
                        "likes": result.likes,
                        "comments": result.comments,
                        "download_links_count": len(result.download_links),
                        "url": result.url
                    })
                
                return {
                    "task_id": task_id,
                    "total_count": len(results),
                    "format": "table",
                    "results": table_results
                }
    
    raise HTTPException(status_code=404, detail="任务结果不存在")

@app.get("/api/v1/crawler/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {
        "tasks": list(task_status.values()),
        "total": len(task_status)
    }

# 新增多平台任务列表API
@app.get("/api/v1/multi-platform/tasks")
async def list_multi_platform_tasks():
    """获取所有多平台任务列表"""
    if multi_platform_crawler is None:
        return {"tasks": [], "total": 0, "message": "多平台抓取功能暂不可用"}
    
    multi_tasks = multi_platform_crawler.list_tasks()
    return {
        "tasks": multi_tasks,
        "total": len(multi_tasks)
    }

@app.delete("/api/v1/crawler/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del task_status[task_id]
    return {"message": "任务已删除", "task_id": task_id}

# 新增取消多平台任务API
@app.post("/api/v1/multi-platform/cancel/{task_id}")
async def cancel_multi_platform_task(task_id: str):
    """取消多平台任务"""
    if multi_platform_crawler is None:
        raise HTTPException(status_code=503, detail="多平台抓取功能暂不可用")
    
    success = multi_platform_crawler.cancel_task(task_id)
    if success:
        return {"message": "任务已取消", "task_id": task_id}
    else:
        raise HTTPException(status_code=400, detail="取消任务失败")

async def register_api_routes():
    """在数据库初始化完成后注册API路由"""
    try:
        # 延迟导入，避免在模块加载时访问数据库
        utils.logger.info("开始导入和注册路由模块...")
        
        # 注册账号管理路由
        try:
            from api.account_management import account_router
            app.include_router(account_router, prefix="/api/v1", tags=["账号管理"])
            utils.logger.info("账号管理路由注册成功")
        except Exception as e:
            utils.logger.error(f"账号管理路由注册失败: {e}")
        
        # 注册登录管理路由
        try:
            from api.login_management import login_router
            app.include_router(login_router, prefix="/api/v1", tags=["登录管理"])
            utils.logger.info("登录管理路由注册成功")
        except Exception as e:
            utils.logger.error(f"登录管理路由注册失败: {e}")
        
        # 注册代理管理路由
        try:
            from proxy import proxy_router
            app.include_router(proxy_router, prefix="/api/v1", tags=["代理管理"])
            utils.logger.info("代理管理路由注册成功")
        except Exception as e:
            utils.logger.error(f"代理管理路由注册失败（不影响基本功能）: {e}")
        
        # 注册视频文件管理路由
        try:
            from api_video_files import router as video_files_router, init_video_files_api
            from db_video_files import VideoFileManager
            
            # 初始化视频文件管理系统
            video_file_manager = VideoFileManager()
            await video_file_manager.init_video_files_tables()
            
            # 初始化MinIO配置（如果有的话）
            minio_config = None
            try:
                from config.base_config import MINIO_CONFIG
                minio_config = MINIO_CONFIG
            except ImportError:
                pass
            
            init_video_files_api(minio_config)
            app.include_router(video_files_router, tags=["视频文件管理"])
            utils.logger.info("视频文件管理路由注册成功")
        except Exception as e:
            utils.logger.error(f"视频文件管理路由注册失败（不影响基本功能）: {e}")
        
        # 注册新的任务结果管理API路由
        try:
            app.include_router(api_router, prefix="/api")
            utils.logger.info("任务结果管理API路由注册成功")
        except Exception as e:
            utils.logger.error(f"任务结果管理API路由注册失败: {e}")
        
        utils.logger.info("所有路由注册完成")
        
    except Exception as e:
        utils.logger.error(f"路由注册失败: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    utils.logger.info("=== MediaCrawler API Server 启动 ===")
    
    # 初始化数据库
    try:
        utils.logger.info("初始化数据库...")
        db_initializer = DatabaseInitializer()
        await db_initializer.initialize_database()
        utils.logger.info("数据库初始化完成")
        
        # 初始化主数据库连接
        utils.logger.info("初始化主数据库连接...")
        await db.init_db()
        utils.logger.info("主数据库连接初始化完成")
        
        # 启动定时任务调度器
        utils.logger.info("启动定时任务调度器...")
        await start_scheduler()
        utils.logger.info("定时任务调度器启动完成")
        
        # 注册API路由（在数据库初始化完成后）
        utils.logger.info("注册API路由...")
        await register_api_routes()
        utils.logger.info("API路由注册完成")
        
        # 设置数据库初始化标志
        global db_initialized
        db_initialized = True
        
        # 检查Redis连接
        try:
            pong = redis_manager.redis_client.ping()
            if pong:
                print("✅ Redis 连接成功 (PING 响应)")
            else:
                print("❌ Redis 连接失败 (PING 无响应)")
        except Exception as e:
            print(f"❌ Redis 连接异常: {e}")
        
    except Exception as e:
        utils.logger.error(f"应用启动失败: {e}")
        import traceback
        utils.logger.error(f"错误堆栈: {traceback.format_exc()}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    utils.logger.info("=== MediaCrawler API Server 关闭 ===")
    
    try:
        # 停止定时任务调度器
        utils.logger.info("停止定时任务调度器...")
        await stop_scheduler()
        utils.logger.info("定时任务调度器已停止")
        
        # 关闭数据库连接
        utils.logger.info("关闭数据库连接...")
        try:
            await db.close()
            utils.logger.info("数据库连接已关闭")
        except Exception as db_error:
            utils.logger.warning(f"关闭数据库连接时出现警告: {db_error}")
        
    except Exception as e:
        utils.logger.error(f"应用关闭时出错: {e}")


@app.get("/")
async def root():
    """根路径，返回测试页面"""
    return FileResponse("static/index.html")

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database_initialized": db_initialized
    }

@app.post("/api/v1/database/init")
async def init_database():
    """手动初始化数据库"""
    global db_initialized
    try:
        initializer = DatabaseInitializer()
        await initializer.initialize_database()
        db_initialized = True
        return {
            "status": "success",
            "message": "数据库初始化完成",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"数据库初始化失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/database/status")
async def get_database_status():
    """获取数据库状态"""
    return {
        "initialized": db_initialized,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": SUPPORTED_PLATFORMS
    }

# 新增多平台信息API
@app.get("/api/v1/multi-platform/info")
async def get_multi_platform_info():
    """获取多平台抓取功能信息"""
    if multi_platform_crawler is None:
        return {
            "feature": "多平台同时抓取",
            "description": "支持多个平台同时抓取相同关键词，统一结果格式",
            "supported_platforms": {},
            "capabilities": [
                "并发抓取多个平台",
                "统一结果格式输出",
                "任务状态跟踪",
                "进度监控",
                "错误处理"
            ],
            "output_formats": ["json", "csv"],
            "max_platforms": 7,
            "status": "unavailable"
        }
    
    return {
        "feature": "多平台同时抓取",
        "description": "支持多个平台同时抓取相同关键词，统一结果格式",
        "supported_platforms": multi_platform_crawler.platform_mapping,
        "capabilities": [
            "并发抓取多个平台",
            "统一结果格式输出",
            "任务状态跟踪",
            "进度监控",
            "错误处理"
        ],
        "output_formats": ["json", "csv"],
        "max_platforms": 7,
        "status": "available"
    }

@app.get("/api/v1/proxy/quick-get")
async def quick_get_proxy(
    strategy_type: str = "round_robin",
    platform: str = None,
    check_availability: bool = True
):
    """快速获取代理"""
    global proxy_manager
    
    if proxy_manager is None:
        try:
            from proxy import ProxyManager
            proxy_manager = ProxyManager()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"代理管理器不可用: {str(e)}")
    
    try:
        proxy = await proxy_manager.get_proxy(strategy_type, platform=platform)
        
        if not proxy:
            return {"message": "没有可用的代理", "proxy": None}
        
        if check_availability:
            is_available = await proxy_manager.check_proxy(proxy)
            if not is_available:
                return {"message": "代理不可用", "proxy": None}
        
        return {
            "message": "获取代理成功",
            "proxy": {
                "id": proxy.id,
                "ip": proxy.ip,
                "port": proxy.port,
                "proxy_type": proxy.proxy_type,
                "country": proxy.country,
                "speed": proxy.speed,
                "anonymity": proxy.anonymity,
                "success_rate": proxy.success_rate
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理失败: {str(e)}")

@app.get("/api/v1/proxy/quick-stats")
async def quick_proxy_stats():
    """快速获取代理统计"""
    global proxy_manager
    
    if proxy_manager is None:
        try:
            from proxy import ProxyManager
            proxy_manager = ProxyManager()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"代理管理器不可用: {str(e)}")
    
    try:
        stats = await proxy_manager.get_proxy_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理统计失败: {str(e)}")

@app.get("/accounts/{platform}")
async def get_platform_accounts(platform: str):
    """获取指定平台的账号列表"""
    try:
        accounts = await get_account_list_by_platform(platform)
        return {
            "success": True,
            "platform": platform,
            "accounts": accounts,
            "count": len(accounts)
        }
    except Exception as e:
        utils.logger.error(f"获取平台账号列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账号列表失败: {str(e)}")


@app.get("/accounts/{platform}/validity")
async def check_platform_token_validity(platform: str, account_id: Optional[str] = None):
    """检查指定平台和账号的凭证有效性"""
    try:
        validity = await check_token_validity(platform, account_id)
        return {
            "success": True,
            "platform": platform,
            "account_id": account_id,
            "validity": validity
        }
    except Exception as e:
        utils.logger.error(f"检查凭证有效性失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查凭证有效性失败: {str(e)}")


@app.post("/tokens/cleanup")
async def cleanup_expired_tokens_api():
    """清理过期的凭证"""
    try:
        count = await cleanup_expired_tokens()
        return {
            "success": True,
            "message": f"已清理 {count} 个过期凭证",
            "count": count
        }
    except Exception as e:
        utils.logger.error(f"清理过期凭证失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理过期凭证失败: {str(e)}")


@app.get("/scheduler/status")
async def get_scheduler_status_api():
    """获取定时任务调度器状态"""
    try:
        status = await get_scheduler_status()
        return {
            "success": True,
            "scheduler": status
        }
    except Exception as e:
        utils.logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")


@app.post("/scheduler/start")
async def start_scheduler_api():
    """启动定时任务调度器"""
    try:
        await start_scheduler()
        return {
            "success": True,
            "message": "定时任务调度器已启动"
        }
    except Exception as e:
        utils.logger.error(f"启动调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动调度器失败: {str(e)}")


@app.post("/scheduler/stop")
async def stop_scheduler_api():
    """停止定时任务调度器"""
    try:
        await stop_scheduler()
        return {
            "success": True,
            "message": "定时任务调度器已停止"
        }
    except Exception as e:
        utils.logger.error(f"停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}")



# 内容查询工具函数
async def get_unified_content_from_db(request: ContentListRequest) -> ContentListResponse:
    """从数据库查询统一格式的内容列表 - 支持短视频优先筛选"""
    if not db_initialized:
        raise HTTPException(status_code=503, detail="数据库未初始化")
    
    from models.content_models import (
        PLATFORM_MAPPING, 
        VIDEO_PRIORITY_PLATFORMS, 
        TODO_PLATFORMS,
        is_video_priority_platform,
        is_todo_platform
    )
    
    all_contents = []
    platforms_summary = {}
    
    # 确定要查询的平台 - 根据短视频优先设置
    if request.platform:
        platforms_to_query = [request.platform]
    else:
        # 根据筛选条件确定平台列表
        platforms_to_query = list(PLATFORM_MAPPING.keys())
        
        if request.video_platforms_only:
            # 仅视频主导平台
            platforms_to_query = VIDEO_PRIORITY_PLATFORMS
            utils.logger.info(f"[CONTENT_QUERY] 仅查询视频主导平台: {platforms_to_query}")
        elif request.exclude_todo_platforms:
            # 排除TODO平台
            platforms_to_query = [p for p in platforms_to_query if p not in TODO_PLATFORMS]
            utils.logger.info(f"[CONTENT_QUERY] 排除TODO平台，查询平台: {platforms_to_query}")
        
        # 如果只要视频内容，优先排序视频平台
        if request.video_only:
            video_platforms = [p for p in platforms_to_query if is_video_priority_platform(p)]
            other_platforms = [p for p in platforms_to_query if not is_video_priority_platform(p)]
            platforms_to_query = video_platforms + other_platforms
            utils.logger.info(f"[CONTENT_QUERY] 视频优先排序: 视频平台{video_platforms}, 其他平台{other_platforms}")
    
    for platform_key in platforms_to_query:
        if platform_key not in PLATFORM_MAPPING:
            continue
            
        platform_info = PLATFORM_MAPPING[platform_key]
        table_name = platform_info["table"]
        id_field = platform_info["id_field"]
        platform_name = platform_info["name"]
        
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            # 视频内容筛选
            if request.video_only and "video_filter" in platform_info:
                video_filter = platform_info["video_filter"]
                if video_filter and video_filter.strip():
                    conditions.append(f"({video_filter})")
                    utils.logger.info(f"[CONTENT_QUERY] {platform_key} 添加视频筛选: {video_filter}")
            
            # 内容类型筛选
            if request.content_type:
                if request.content_type == "video":
                    if "video_filter" in platform_info and platform_info["video_filter"]:
                        conditions.append(f"({platform_info['video_filter']})")
                elif request.content_type == "image" and platform_key == "xhs":
                    conditions.append("type = 'normal' AND image_list IS NOT NULL AND image_list != ''")
                elif request.content_type == "text":
                    if platform_key == "xhs":
                        conditions.append("type = 'normal' AND (image_list IS NULL OR image_list = '')")
                    elif platform_key in ["dy", "ks", "bili"]:
                        # 这些平台主要是视频，文本内容较少
                        conditions.append("1 = 0")  # 基本不返回结果
            
            # 关键词筛选
            if request.keyword:
                conditions.append("(title LIKE %s OR `desc` LIKE %s OR source_keyword LIKE %s)")
                keyword_param = f"%{request.keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param])
            
            # 作者筛选
            if request.author_name:
                conditions.append("nickname LIKE %s")
                params.append(f"%{request.author_name}%")
            
            # 时间筛选
            if request.start_time:
                try:
                    start_ts = int(datetime.fromisoformat(request.start_time.replace('Z', '+00:00')).timestamp())
                    if platform_key in ["xhs", "dy", "ks", "bili"]:
                        conditions.append("time >= %s" if platform_key == "xhs" else "create_time >= %s")
                    else:
                        conditions.append("add_ts >= %s")
                    params.append(start_ts)
                except:
                    pass
            
            if request.end_time:
                try:
                    end_ts = int(datetime.fromisoformat(request.end_time.replace('Z', '+00:00')).timestamp())
                    if platform_key in ["xhs", "dy", "ks", "bili"]:
                        conditions.append("time <= %s" if platform_key == "xhs" else "create_time <= %s")
                    else:
                        conditions.append("add_ts <= %s")
                    params.append(end_ts)
                except:
                    pass
            
            # 构建WHERE子句
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            # 构建排序
            sort_field_mapping = {
                "crawl_time": "add_ts",
                "publish_time": "time" if platform_key == "xhs" else "create_time",
                "like_count": "liked_count"
            }
            sort_field = sort_field_mapping.get(request.sort_by, "add_ts")
            sort_order = "DESC" if request.sort_order == "desc" else "ASC"
            
            # 计算偏移量
            offset = (request.page - 1) * request.page_size
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM {table_name} {where_clause}"
            count_result = await db.query(count_sql, *params)
            total_count = count_result[0]['total'] if count_result else 0
            platforms_summary[platform_key] = total_count
            
            if total_count == 0:
                continue
            
            # 查询数据
            data_sql = f"""
            SELECT * FROM {table_name} 
            {where_clause}
            ORDER BY {sort_field} {sort_order}
            LIMIT %s OFFSET %s
            """
            params.extend([request.page_size, offset])
            rows = await db.query(data_sql, *params)
            
            # 转换为统一格式
            for row in rows:
                unified_content = convert_to_unified_content(row, platform_key, platform_name, id_field)
                if unified_content:
                    all_contents.append(unified_content)
                    
        except Exception as e:
            utils.logger.error(f"查询平台 {platform_key} 数据失败: {e}")
            platforms_summary[platform_key] = 0
            continue
    
    # 如果是跨平台查询，需要重新排序和分页
    if not request.platform:
        # 按指定字段排序
        if request.sort_by == "crawl_time":
            all_contents.sort(key=lambda x: x.crawl_time or 0, reverse=(request.sort_order == "desc"))
        elif request.sort_by == "publish_time":
            all_contents.sort(key=lambda x: x.publish_time or 0, reverse=(request.sort_order == "desc"))
        elif request.sort_by == "like_count":
            all_contents.sort(key=lambda x: int(str(x.like_count or 0).replace(',', '')), reverse=(request.sort_order == "desc"))
        
        # 重新分页
        total = len(all_contents)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        all_contents = all_contents[start_idx:end_idx]
    else:
        total = platforms_summary.get(request.platform, 0)
    
    total_pages = (total + request.page_size - 1) // request.page_size
    
    return ContentListResponse(
        total=total,
        page=request.page,
        page_size=request.page_size,
        total_pages=total_pages,
        items=all_contents,
        platforms_summary=platforms_summary
    )

def convert_to_unified_content(row: Dict, platform: str, platform_name: str, id_field: str) -> Optional[UnifiedContent]:
    """将数据库行转换为统一格式"""
    try:
        # 基础信息
        content_id = str(row.get(id_field, ''))
        title = row.get('title', '')
        description = row.get('desc', '') or row.get('content', '') or row.get('content_text', '')
        
        # 判断内容类型
        content_type = "text"
        if platform in ["dy", "ks", "bili"]:
            content_type = "video"
        elif platform == "xhs":
            note_type = row.get('type', '')
            if note_type == "video":
                content_type = "video"
            elif row.get('image_list'):
                content_type = "image"
            else:
                content_type = "text"
        elif platform == "wb":
            if row.get('image_list') or row.get('video_url'):
                content_type = "mixed"
        elif platform == "zhihu":
            zhihu_type = row.get('content_type', '')
            if zhihu_type == "zvideo":
                content_type = "video"
            else:
                content_type = "text"
        
        # 作者信息
        author_id = str(row.get('user_id', ''))
        author_name = row.get('nickname', '') or row.get('user_nickname', '')
        author_avatar = row.get('avatar', '') or row.get('user_avatar', '')
        
        # 统计数据
        like_count = row.get('liked_count') or row.get('voteup_count') or row.get('like_count') or 0
        comment_count = row.get('comment_count') or row.get('comments_count') or 0
        share_count = row.get('share_count') or row.get('shared_count') or 0
        view_count = row.get('video_play_count') or row.get('viewd_count') or row.get('view_count') or 0
        collect_count = row.get('collected_count') or row.get('video_favorite_count') or 0
        
        # 时间信息
        publish_time = None
        publish_time_str = None
        crawl_time = row.get('add_ts')
        crawl_time_str = None
        
        # 根据平台获取发布时间
        if platform in ["xhs"]:
            publish_time = row.get('time')
        elif platform in ["dy", "ks", "bili"]:
            publish_time = row.get('create_time')
        elif platform == "wb":
            publish_time = row.get('create_time')
            publish_time_str = row.get('create_date_time')
        elif platform == "zhihu":
            created_time_str = row.get('created_time')
            if created_time_str:
                try:
                    publish_time = int(datetime.fromisoformat(created_time_str).timestamp())
                except:
                    pass
                publish_time_str = created_time_str
        elif platform == "tieba":
            publish_time_str = row.get('publish_time')
        
        # 格式化时间字符串
        if publish_time and not publish_time_str:
            try:
                publish_time_str = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        if crawl_time:
            try:
                crawl_time_str = datetime.fromtimestamp(crawl_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 关联信息
        source_keyword = row.get('source_keyword', '')
        content_url = row.get('note_url') or row.get('aweme_url') or row.get('video_url') or row.get('content_url') or ''
        cover_url = row.get('cover_url') or row.get('video_cover_url') or ''
        video_url = row.get('video_url') or row.get('video_play_url') or row.get('video_download_url') or ''
        
        # 标签处理
        tags = []
        tag_list = row.get('tag_list', '')
        if tag_list:
            try:
                if isinstance(tag_list, str):
                    if tag_list.startswith('['):
                        tags = json.loads(tag_list)
                    else:
                        tags = [tag.strip() for tag in tag_list.split(',') if tag.strip()]
                elif isinstance(tag_list, list):
                    tags = tag_list
            except:
                pass
        
        # IP地理位置
        ip_location = row.get('ip_location', '')
        
        return UnifiedContent(
            id=row.get('id', 0),
            platform=platform,
            platform_name=platform_name,
            content_id=content_id,
            content_type=content_type,
            title=title,
            description=description[:500] if description else None,  # 限制描述长度
            content=description,
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            view_count=view_count,
            collect_count=collect_count,
            publish_time=publish_time,
            publish_time_str=publish_time_str,
            crawl_time=crawl_time,
            crawl_time_str=crawl_time_str,
            source_keyword=source_keyword,
            content_url=content_url,
            cover_url=cover_url,
            video_url=video_url,
            tags=tags,
            ip_location=ip_location,
            extra_data=None
        )
        
    except Exception as e:
        utils.logger.error(f"转换内容数据失败: {e}, row: {row}")
        return None

# 内容相关API接口
@app.post("/api/v1/content/list", response_model=ContentListResponse)
async def get_content_list(request: ContentListRequest):
    """获取内容列表"""
    try:
        utils.logger.info(f"[CONTENT_LIST] 收到内容列表查询请求")
        utils.logger.info(f"[CONTENT_LIST] 查询参数: platform={request.platform}, keyword={request.keyword}, page={request.page}")
        
        result = await get_unified_content_from_db(request)
        
        utils.logger.info(f"[CONTENT_LIST] 查询完成: 总数={result.total}, 当前页={result.page}, 返回{len(result.items)}条数据")
        return result
        
    except Exception as e:
        utils.logger.error(f"[CONTENT_LIST] 查询内容列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询内容列表失败: {str(e)}")

@app.get("/api/v1/content/{platform}/{content_id}", response_model=UnifiedContent)
async def get_content_detail(platform: str, content_id: str):
    """获取内容详情"""
    try:
        utils.logger.info(f"[CONTENT_DETAIL] 获取内容详情: platform={platform}, content_id={content_id}")
        
        if not db_initialized:
            raise HTTPException(status_code=503, detail="数据库未初始化")
        
        platform_mapping = PLATFORM_MAPPING
        
        if platform not in platform_mapping:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")
        
        platform_info = platform_mapping[platform]
        table_name = platform_info["table"]
        id_field = platform_info["id_field"]
        platform_name = platform_info["name"]
        
        # 查询数据
        sql = f"SELECT * FROM {table_name} WHERE {id_field} = %s LIMIT 1"
        rows = await db.query(sql, content_id)
        
        if not rows:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        row = rows[0]
        unified_content = convert_to_unified_content(row, platform, platform_name, id_field)
        
        if not unified_content:
            raise HTTPException(status_code=500, detail="数据转换失败")
        
        utils.logger.info(f"[CONTENT_DETAIL] 获取详情成功: {unified_content.title}")
        return unified_content
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[CONTENT_DETAIL] 获取内容详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取内容详情失败: {str(e)}")

@app.get("/api/v1/content/platforms")
async def get_platforms_info():
    """获取平台信息和统计"""
    try:
        if not db_initialized:
            raise HTTPException(status_code=503, detail="数据库未初始化")
        
        from models.content_models import (
            PLATFORM_MAPPING, 
            VIDEO_PRIORITY_PLATFORMS, 
            TODO_PLATFORMS,
            get_platform_description,
            is_video_priority_platform
        )
        
        platforms_info = {}
        
        for platform_key, platform_info in PLATFORM_MAPPING.items():
            try:
                sql = f"SELECT COUNT(*) as total FROM {platform_info['table']}"
                result = await db.query(sql)
                total_count = result[0]['total'] if result else 0
                
                # 统计视频内容数量
                video_count = 0
                if "video_filter" in platform_info and platform_info["video_filter"]:
                    video_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']} WHERE {platform_info['video_filter']}"
                    video_result = await db.query(video_sql)
                    video_count = video_result[0]['total'] if video_result else 0
                
                # 获取最近的关键词
                recent_keywords_sql = f"""
                SELECT source_keyword, COUNT(*) as count 
                FROM {platform_info['table']} 
                WHERE source_keyword IS NOT NULL AND source_keyword != ''
                GROUP BY source_keyword 
                ORDER BY count DESC, MAX(add_ts) DESC
                LIMIT 5
                """
                keywords_result = await db.query(recent_keywords_sql)
                recent_keywords = [row['source_keyword'] for row in keywords_result]
                
                platforms_info[platform_key] = {
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": total_count,
                    "video_count": video_count,
                    "video_ratio": round(video_count / total_count * 100, 1) if total_count > 0 else 0,
                    "recent_keywords": recent_keywords,
                    "is_video_priority": is_video_priority_platform(platform_key),
                    "is_todo": platform_key in TODO_PLATFORMS,
                    "primary_content_type": platform_info.get("primary_content_type", "mixed")
                }
                
            except Exception as e:
                utils.logger.error(f"获取平台 {platform_key} 统计失败: {e}")
                platforms_info[platform_key] = {
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": 0,
                    "video_count": 0,
                    "video_ratio": 0,
                    "recent_keywords": [],
                    "is_video_priority": is_video_priority_platform(platform_key),
                    "is_todo": platform_key in TODO_PLATFORMS,
                    "primary_content_type": platform_info.get("primary_content_type", "mixed")
                }
        
        return {
            "platforms": platforms_info,
            "total_platforms": len(platforms_info),
            "video_priority_platforms": VIDEO_PRIORITY_PLATFORMS,
            "todo_platforms": TODO_PLATFORMS,
            "total_content": sum(info["total_count"] for info in platforms_info.values()),
            "total_video_content": sum(info["video_count"] for info in platforms_info.values())
        }
        
    except Exception as e:
        utils.logger.error(f"获取平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取平台信息失败: {str(e)}")


@app.post("/api/v1/content/videos", response_model=ContentListResponse)
async def get_video_content_list(
    keyword: Optional[str] = None,
    platform: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取短视频内容列表 - 专注短视频优先平台"""
    try:
        utils.logger.info(f"[VIDEO_CONTENT] 收到短视频内容查询请求: keyword={keyword}, platform={platform}")
        
        # 构建专门的短视频查询请求
        request = ContentListRequest(
            platform=platform,
            keyword=keyword,
            page=page,
            page_size=page_size,
            video_only=True,  # 仅视频内容
            video_platforms_only=True,  # 仅视频优先平台
            exclude_todo_platforms=True,  # 排除TODO平台
            sort_by="crawl_time",
            sort_order="desc"
        )
        
        result = await get_unified_content_from_db(request)
        
        utils.logger.info(f"[VIDEO_CONTENT] 短视频查询完成: 总数={result.total}, 返回{len(result.items)}条视频")
        return result
        
    except Exception as e:
        utils.logger.error(f"[VIDEO_CONTENT] 查询短视频内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询短视频内容失败: {str(e)}")


@app.get("/api/v1/content/video-platforms")
async def get_video_platforms_info():
    """获取短视频优先平台信息"""
    try:
        from models.content_models import (
            VIDEO_PRIORITY_PLATFORMS, 
            PLATFORM_MAPPING,
            get_platform_description
        )
        
        video_platforms = []
        for platform_key in VIDEO_PRIORITY_PLATFORMS:
            if platform_key in PLATFORM_MAPPING:
                platform_info = PLATFORM_MAPPING[platform_key]
                
                # 获取视频数量统计
                video_count = 0
                total_count = 0
                if db_initialized:
                    try:
                        # 总数量
                        total_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']}"
                        total_result = await db.query(total_sql)
                        total_count = total_result[0]['total'] if total_result else 0
                        
                        # 视频数量
                        if "video_filter" in platform_info and platform_info["video_filter"]:
                            video_sql = f"SELECT COUNT(*) as total FROM {platform_info['table']} WHERE {platform_info['video_filter']}"
                            video_result = await db.query(video_sql)
                            video_count = video_result[0]['total'] if video_result else 0
                        else:
                            video_count = total_count  # 如果没有视频筛选，假设全部是视频
                    except:
                        pass
                
                video_platforms.append({
                    "code": platform_key,
                    "name": platform_info["name"],
                    "description": get_platform_description(platform_key),
                    "total_count": total_count,
                    "video_count": video_count,
                    "video_ratio": round(video_count / total_count * 100, 1) if total_count > 0 else 100,
                    "primary_content_type": platform_info.get("primary_content_type", "video")
                })
        
        return {
            "video_priority_platforms": video_platforms,
            "total_platforms": len(video_platforms),
            "total_video_content": sum(p["video_count"] for p in video_platforms),
            "message": "本平台专注于短视频内容，以上为主要短视频平台"
        }
        
    except Exception as e:
        utils.logger.error(f"获取短视频平台信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取短视频平台信息失败: {str(e)}")

# ==================== 智能多平台爬取API端点 ====================

class SmartMultiPlatformRequest(BaseModel):
    """智能多平台爬取请求"""
    platforms: List[str] = Field(..., description="目标平台列表")
    keywords: str = Field(..., description="搜索关键词")
    max_count_per_platform: int = Field(default=20, description="每平台最大爬取数量")
    
    # 账号策略
    account_strategy: str = Field(default="random", description="账号使用策略: random/round_robin/priority/single")
    enable_anti_bot: bool = Field(default=True, description="启用智能反爬虫")
    enable_human_intervention: bool = Field(default=True, description="启用人工干预")
    
    # 代理策略配置
    enable_proxy: bool = Field(default=False, description="启用代理池")
    proxy_strategy: str = Field(default="round_robin", description="代理策略: round_robin/random/weighted/failover/sticky")
    proxy_quality: str = Field(default="auto", description="代理质量: auto/premium/datacenter/mobile")
    
    # 内容偏好
    content_preference: str = Field(default="video_priority", description="内容类型偏好: video_priority/all/video_only")
    sort_preference: str = Field(default="hot", description="排序偏好: hot/time/comprehensive")
    
    # 附加功能
    enable_comments: bool = Field(default=True, description="爬取评论")
    enable_creator_info: bool = Field(default=False, description="获取创作者信息")
    auto_download_videos: bool = Field(default=False, description="自动下载视频")
    
    # 数据存储配置
    save_format: str = Field(default="db_only", description="数据存储方式: db_only/db_json/db_csv/all")
    video_process_mode: str = Field(default="metadata_only", description="视频文件处理: metadata_only/download_later/auto_download")
    video_quality_preset: str = Field(default="auto", description="视频质量预设: auto/high/medium/fast")
    max_video_size: int = Field(default=100, description="单个视频最大尺寸(MB)")
    enable_file_size_check: bool = Field(default=True, description="启用文件大小检查")
    file_naming_rule: str = Field(default="platform_id", description="文件命名规则: platform_id/title_author/timestamp_id/custom")
    save_video_metadata: bool = Field(default=True, description="保存视频元数据")
    save_thumbnails: bool = Field(default=False, description="保存缩略图")

class HumanInterventionRequest(BaseModel):
    """人工干预请求"""
    type: str = Field(..., description="干预类型: captcha/login_required")
    data: str = Field(..., description="干预数据: 验证码/登录状态")

@app.post("/api/v1/multi-platform/smart-start", response_model=CrawlerResponse)
async def start_smart_multi_platform_crawler(request: SmartMultiPlatformRequest, background_tasks: BackgroundTasks):
    """启动智能多平台爬取任务"""
    try:
        # 验证平台选择
        from models.content_models import PLATFORM_MAPPING, VIDEO_PRIORITY_PLATFORMS, TODO_PLATFORMS
        
        invalid_platforms = [p for p in request.platforms if p not in PLATFORM_MAPPING]
        if invalid_platforms:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {invalid_platforms}")
        
        # 检查TODO平台
        todo_platforms = [p for p in request.platforms if p in TODO_PLATFORMS]
        if todo_platforms:
            utils.logger.warning(f"请求包含TODO平台: {todo_platforms}")
        
        # 生成任务ID
        task_id = f"smart_multi_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # 创建任务记录
        creation_time = datetime.now().isoformat()
        task_data = {
            "task_id": task_id,
            "type": "smart_multi_platform",
            "platforms": request.platforms,
            "keywords": request.keywords,
            "status": "pending",
            "config": request.dict(),
            "created_at": creation_time,
            "requires_intervention": False
        }
        
        # 存储到全局任务管理器
        if not hasattr(app.state, 'smart_multi_tasks'):
            app.state.smart_multi_tasks = {}
        app.state.smart_multi_tasks[task_id] = task_data
        
        # 启动后台任务
        background_tasks.add_task(run_smart_multi_platform_task, task_id, request)
        
        utils.logger.info(f"[SMART_MULTI] 智能多平台任务已创建: {task_id}, 平台: {request.platforms}")
        
        return CrawlerResponse(
            task_id=task_id,
            status="pending",
            message=f"智能多平台爬取任务已启动，将在 {len(request.platforms)} 个平台搜索关键词: {request.keywords}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[SMART_MULTI] 启动智能多平台任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动智能多平台任务失败: {str(e)}")

async def run_smart_multi_platform_task(task_id: str, request: SmartMultiPlatformRequest):
    """运行智能多平台爬取任务"""
    try:
        # 更新任务状态
        task_data = app.state.smart_multi_tasks[task_id]
        task_data["status"] = "running"
        task_data["started_at"] = datetime.now().isoformat()
        task_data["platform_progress"] = {}
        
        utils.logger.info(f"[SMART_MULTI] 开始执行智能多平台任务: {task_id}")
        
        # 初始化数据库连接
        await db.init_db()
        
        # 选择和验证账号
        selected_accounts = await select_accounts_for_platforms(request.platforms, request.account_strategy)
        
        # 更新进度
        task_data["overall_progress"] = 10
        task_data["message"] = "账号选择完成，开始爬取..."
        
        all_results = []
        platform_count = len(request.platforms)
        
        for idx, platform in enumerate(request.platforms):
            try:
                # 更新平台进度
                task_data["platform_progress"][platform] = {
                    "status": "running",
                    "message": "正在爬取...",
                    "completed": 0,
                    "total": request.max_count_per_platform
                }
                
                # 检查是否需要人工干预
                if await requires_human_intervention(platform, task_id):
                    task_data["requires_intervention"] = True
                    task_data["intervention_data"] = await get_intervention_data(platform)
                    
                    # 等待人工干预完成
                    while task_data.get("requires_intervention", False):
                        await asyncio.sleep(5)
                
                # 执行爬取任务
                platform_results = await crawl_platform_smart(
                    platform, 
                    request.keywords, 
                    request.max_count_per_platform,
                    selected_accounts.get(platform),
                    request
                )
                
                all_results.extend(platform_results)
                
                # 更新平台完成状态
                task_data["platform_progress"][platform] = {
                    "status": "completed",
                    "message": f"完成，获取 {len(platform_results)} 条内容",
                    "completed": len(platform_results),
                    "total": request.max_count_per_platform
                }
                
                # 更新总体进度
                task_data["overall_progress"] = 10 + int((idx + 1) / platform_count * 80)
                
            except Exception as e:
                utils.logger.error(f"[SMART_MULTI] 平台 {platform} 爬取失败: {e}")
                task_data["platform_progress"][platform] = {
                    "status": "error",
                    "message": f"爬取失败: {str(e)}",
                    "completed": 0,
                    "total": request.max_count_per_platform
                }
        
        # 按热度排序结果
        if request.sort_preference == "hot":
            all_results.sort(key=lambda x: (x.get('like_count', 0) + x.get('view_count', 0) + x.get('comment_count', 0)), reverse=True)
        elif request.sort_preference == "time":
            all_results.sort(key=lambda x: x.get('publish_time', ''), reverse=True)
        
        # 自动下载视频
        if request.auto_download_videos:
            await download_videos_batch(all_results, request.video_storage_type, request.video_quality)
        
        # 更新任务完成状态
        task_data["status"] = "completed"
        task_data["completed_at"] = datetime.now().isoformat()
        task_data["overall_progress"] = 100
        task_data["results"] = all_results
        task_data["message"] = f"任务完成，共获取 {len(all_results)} 条内容"
        
        utils.logger.info(f"[SMART_MULTI] 智能多平台任务完成: {task_id}, 总共获取 {len(all_results)} 条内容")
        
    except Exception as e:
        utils.logger.error(f"[SMART_MULTI] 智能多平台任务执行失败: {task_id}, 错误: {e}")
        task_data["status"] = "failed"
        task_data["error"] = str(e)
        task_data["overall_progress"] = 0

async def select_accounts_for_platforms(platforms: List[str], strategy: str) -> Dict[str, Optional[int]]:
    """为各平台选择账号"""
    selected_accounts = {}
    
    for platform in platforms:
        try:
            # 获取平台可用账号
            accounts_response = await get_platform_accounts(platform)
            if not accounts_response or not isinstance(accounts_response, list):
                selected_accounts[platform] = None
                continue
            
            # 筛选已登录账号
            logged_in_accounts = [acc for acc in accounts_response if acc.get('login_status') == 'logged_in']
            
            if not logged_in_accounts:
                utils.logger.warning(f"平台 {platform} 没有已登录账号")
                selected_accounts[platform] = None
                continue
            
            # 根据策略选择账号
            if strategy == "random":
                selected_account = random.choice(logged_in_accounts)
            elif strategy == "round_robin":
                # 简化实现，选择第一个
                selected_account = logged_in_accounts[0]
            elif strategy == "priority":
                # 按活跃度排序，选择最活跃的
                selected_account = max(logged_in_accounts, key=lambda x: x.get('activity_score', 0))
            else:  # single 或其他
                selected_account = logged_in_accounts[0]
            
            selected_accounts[platform] = selected_account.get('id')
            utils.logger.info(f"[ACCOUNT_SELECT] 平台 {platform} 选择账号: {selected_account.get('username', 'unknown')}")
            
        except Exception as e:
            utils.logger.error(f"[ACCOUNT_SELECT] 平台 {platform} 账号选择失败: {e}")
            selected_accounts[platform] = None
    
    return selected_accounts

async def requires_human_intervention(platform: str, task_id: str) -> bool:
    """检查是否需要人工干预"""
    # 模拟检查逻辑
    # 在实际实现中，这里会检查平台的反爬虫状态
    return False

async def get_intervention_data(platform: str) -> Dict:
    """获取人工干预数据"""
    # 模拟生成干预数据
    return {
        "platform": platform,
        "type": "captcha",
        "description": "需要输入验证码",
        "captcha_image": "/static/captcha_placeholder.png"
    }

async def crawl_platform_smart(platform: str, keywords: str, max_count: int, account_id: Optional[int], config: SmartMultiPlatformRequest) -> List[Dict]:
    """智能爬取单个平台"""
    try:
        # 构建传统爬虫请求
        crawler_request = CrawlerRequest(
            platform=platform,
            keywords=keywords,
            max_notes_count=max_count,
            account_id=account_id,
            get_comments=config.enable_comments,
            save_data_option=config.save_format,
            use_proxy=config.enable_proxy,
            video_priority=(config.content_preference == "video_priority"),
            video_only=(config.content_preference == "video_only")
        )
        
        # 创建爬虫实例
        crawler = CrawlerFactory.create_crawler(platform)
        if not crawler:
            raise Exception(f"无法创建 {platform} 爬虫")
        
        # 执行爬取
        await crawler.run(crawler_request)
        
        # 从数据库读取结果
        from models.content_models import PLATFORM_MAPPING
        platform_info = PLATFORM_MAPPING.get(platform, {})
        table_name = platform_info.get("table", "")
        
        if table_name:
            # 查询最近爬取的数据
            sql = f"""
            SELECT * FROM {table_name} 
            WHERE source_keyword = %s 
            ORDER BY add_ts DESC 
            LIMIT %s
            """
            results = await db.query(sql, keywords, max_count)
            results_list = [dict(row) for row in results]
            
            # 保存视频元数据到video_files表
            if config.save_video_metadata and results_list:
                await save_video_metadata_to_files_table(results_list, platform, task_id="smart_" + keywords, config=config)
            
            return results_list
        
        return []
        
    except Exception as e:
        utils.logger.error(f"[CRAWL_SMART] 平台 {platform} 智能爬取失败: {e}")
        return []

async def save_video_metadata_to_files_table(results: List[Dict], platform: str, task_id: str, config: SmartMultiPlatformRequest):
    """将视频元数据保存到video_files表"""
    try:
        from db_video_files import VideoFileManager
        
        video_file_manager = VideoFileManager()
        saved_count = 0
        
        for result in results:
            # 检查是否有视频URL
            video_url = result.get('video_url') or result.get('video_download_url')
            if not video_url:
                continue
            
            # 构建视频文件信息
            video_info = {
                'platform': platform,
                'content_id': str(result.get('note_id') or result.get('aweme_id') or result.get('id', '')),
                'task_id': task_id,
                'original_url': video_url,
                'title': result.get('title') or result.get('desc', ''),
                'author_name': result.get('nickname') or result.get('author_name', ''),
                'duration': result.get('video_duration'),
                'video_format': 'mp4',  # 默认格式
                'storage_type': 'url_only' if config.video_process_mode == 'metadata_only' else 'temp',
                'thumbnail_url': result.get('thumbnail_url') or result.get('cover_url'),
                'metadata': {
                    'like_count': result.get('like_count', 0),
                    'comment_count': result.get('comment_count', 0),
                    'view_count': result.get('view_count', 0),
                    'share_count': result.get('share_count', 0),
                    'publish_time': result.get('publish_time'),
                    'platform_specific': result  # 保存原始数据
                }
            }
            
            # 尝试从视频信息中提取更多技术参数
            if 'video_info' in result:
                video_details = result['video_info']
                if isinstance(video_details, dict):
                    video_info.update({
                        'resolution': video_details.get('resolution'),
                        'bitrate': video_details.get('bitrate'),
                        'fps': video_details.get('fps'),
                        'file_size': video_details.get('file_size')
                    })
            
            # 保存到数据库
            file_id = await video_file_manager.save_video_metadata(video_info)
            if file_id:
                saved_count += 1
        
        utils.logger.info(f"[VIDEO_METADATA] 成功保存 {saved_count} 个视频元数据到files表")
        
    except Exception as e:
        utils.logger.error(f"[VIDEO_METADATA] 保存视频元数据失败: {e}")

async def download_videos_batch(results: List[Dict], storage_type: str, quality: str):
    """批量下载视频"""
    try:
        utils.logger.info(f"[VIDEO_DOWNLOAD] 开始批量下载 {len(results)} 个视频")
        
        # 这里实现视频下载逻辑
        # 根据storage_type决定存储方式
        # 根据quality决定下载质量
        
        for result in results:
            video_url = result.get('video_url')
            if video_url:
                # 实际下载逻辑
                pass
        
        utils.logger.info(f"[VIDEO_DOWNLOAD] 批量下载完成")
        
    except Exception as e:
        utils.logger.error(f"[VIDEO_DOWNLOAD] 批量下载失败: {e}")

@app.get("/api/v1/multi-platform/status/{task_id}")
async def get_smart_multi_platform_status(task_id: str):
    """获取智能多平台任务状态"""
    try:
        if not hasattr(app.state, 'smart_multi_tasks') or task_id not in app.state.smart_multi_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_data = app.state.smart_multi_tasks[task_id]
        return task_data
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[SMART_MULTI_STATUS] 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@app.post("/api/v1/multi-platform/intervention/{task_id}")
async def handle_human_intervention(task_id: str, request: HumanInterventionRequest):
    """处理人工干预"""
    try:
        if not hasattr(app.state, 'smart_multi_tasks') or task_id not in app.state.smart_multi_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_data = app.state.smart_multi_tasks[task_id]
        
        # 处理不同类型的干预
        if request.type == "captcha":
            # 处理验证码
            utils.logger.info(f"[INTERVENTION] 收到验证码: {request.data}")
            # 这里实现验证码提交逻辑
            
        elif request.type == "login_required":
            # 处理登录要求
            utils.logger.info(f"[INTERVENTION] 处理登录要求")
            # 这里实现登录处理逻辑
        
        # 清除干预标志
        task_data["requires_intervention"] = False
        task_data["intervention_data"] = None
        
        return {"status": "success", "message": "人工干预处理完成"}
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[INTERVENTION] 处理人工干预失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理人工干预失败: {str(e)}")

@app.post("/api/v1/download/video/{platform}/{content_id}")
async def download_single_video(platform: str, content_id: str):
    """下载单个视频"""
    try:
        # 从数据库获取视频信息
        from models.content_models import PLATFORM_MAPPING
        platform_info = PLATFORM_MAPPING.get(platform)
        if not platform_info:
            raise HTTPException(status_code=400, detail="不支持的平台")
        
        table_name = platform_info["table"]
        id_field = platform_info["id_field"]
        
        sql = f"SELECT * FROM {table_name} WHERE {id_field} = %s"
        rows = await db.query(sql, content_id)
        
        if not rows:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        row = rows[0]
        video_url = row.get('video_url') or row.get('video_download_url')
        
        if not video_url:
            raise HTTPException(status_code=404, detail="该内容没有视频文件")
        
        # 这里实现视频下载逻辑
        # 返回视频文件流或下载链接
        
        return {"status": "success", "message": "视频下载已开始", "download_url": video_url}
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[VIDEO_DOWNLOAD] 下载单个视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载视频失败: {str(e)}")

@app.post("/api/v1/download/batch/{task_id}")
async def download_batch_videos(task_id: str):
    """批量下载任务相关的所有视频"""
    try:
        if not hasattr(app.state, 'smart_multi_tasks') or task_id not in app.state.smart_multi_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_data = app.state.smart_multi_tasks[task_id]
        results = task_data.get("results", [])
        
        if not results:
            raise HTTPException(status_code=404, detail="任务没有结果数据")
        
        # 启动批量下载
        video_count = len([r for r in results if r.get('video_url')])
        
        # 这里实现批量下载逻辑
        utils.logger.info(f"[BATCH_DOWNLOAD] 开始批量下载 {video_count} 个视频")
        
        return {
            "status": "success", 
            "message": f"批量下载已开始，共 {video_count} 个视频",
            "video_count": video_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[BATCH_DOWNLOAD] 批量下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量下载失败: {str(e)}")

@app.get("/api/v1/export/results/{task_id}")
async def export_task_results(task_id: str, format: str = "json"):
    """导出任务结果"""
    try:
        if not hasattr(app.state, 'smart_multi_tasks') or task_id not in app.state.smart_multi_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task_data = app.state.smart_multi_tasks[task_id]
        results = task_data.get("results", [])
        
        if not results:
            raise HTTPException(status_code=404, detail="任务没有结果数据")
        
        if format == "json":
            return {"task_id": task_id, "results": results, "total": len(results)}
        elif format == "csv":
            # 实现CSV导出
            import io
            import csv
            
            output = io.StringIO()
            if results:
                writer = csv.DictWriter(output, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            
            return {"status": "success", "data": output.getvalue(), "format": "csv"}
        elif format == "excel":
            # 实现Excel导出
            return {"status": "success", "message": "Excel导出功能开发中", "format": "excel"}
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[EXPORT] 导出结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出结果失败: {str(e)}")

# ==================== 智能多平台爬取API端点结束 ====================

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    ) 