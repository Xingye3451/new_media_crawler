"""
视频收藏API路由
"""

from fastapi import APIRouter, HTTPException, Query, Form
from typing import Dict, Any, List
import logging
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import aiohttp

from services.video_favorite_service import VideoFavoriteService

logger = logging.getLogger(__name__)

router = APIRouter()
favorite_service = VideoFavoriteService()

class VideoFavoriteRequest(BaseModel):
    platform: str
    content_id: str
    task_id: str = None
    original_url: str
    title: str
    author_name: str
    thumbnail_url: str = None
    metadata: Dict[str, Any] = None

class VideoDownloadRequest(BaseModel):
    file_hash: str
    storage_type: str = "minio"  # minio 或 local

@router.post("/favorites/add", response_model=Dict[str, Any])
async def add_favorite(request: VideoFavoriteRequest):
    """添加视频收藏"""
    try:
        result = await favorite_service.add_favorite(request.dict())
        
        if result["success"]:
            return {
                "code": 200,
                "message": result["message"],
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加收藏失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加收藏失败")

@router.post("/favorites/download", response_model=Dict[str, Any])
async def download_favorite(request: VideoDownloadRequest):
    """下载收藏的视频"""
    try:
        result = await favorite_service.download_and_store(
            file_hash=request.file_hash,
            storage_type=request.storage_type
        )
        
        if result["success"]:
            return {
                "code": 200,
                "message": result["message"],
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载收藏视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail="下载失败")

@router.get("/favorites/list", response_model=Dict[str, Any])
async def get_favorites(
    platform: str = Query(None, description="平台筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取收藏列表"""
    try:
        result = await favorite_service.get_favorites(
            platform=platform,
            page=page,
            page_size=page_size
        )
        
        if result["success"]:
            return {
                "code": 200,
                "message": "获取成功",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.delete("/favorites/{file_hash}", response_model=Dict[str, Any])
async def remove_favorite(file_hash: str):
    """移除收藏"""
    try:
        result = await favorite_service.remove_favorite(file_hash)
        
        if result["success"]:
            return {
                "code": 200,
                "message": result["message"],
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除收藏失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="移除失败")

@router.get("/favorites/{file_hash}", response_model=Dict[str, Any])
async def get_favorite_detail(file_hash: str):
    """获取收藏详情"""
    try:
        from services.video_favorite_service import VideoFavoriteService
        service = VideoFavoriteService()
        
        file_record = await service._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": file_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收藏详情失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.get("/favorites/{file_hash}/preview")
async def preview_favorite_video(file_hash: str):
    """预览收藏的视频（基于MinIO）"""
    try:
        # 获取收藏详情
        file_record = await favorite_service._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        # 检查是否已下载到MinIO
        if file_record.get("storage_type") != "minio" or not file_record.get("minio_object_key"):
            raise HTTPException(status_code=400, detail="视频未下载到MinIO存储")
        
        # 从MinIO获取预签名URL
        minio_url = await favorite_service.minio_client.get_presigned_url(
            bucket_name=file_record["minio_bucket"],
            object_name=file_record["minio_object_key"],
            expires=3600  # 1小时有效期
        )
        
        if not minio_url:
            raise HTTPException(status_code=500, detail="获取MinIO访问链接失败")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "preview_url": minio_url,
                "file_size": file_record.get("file_size"),
                "content_type": "video/mp4"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览收藏视频失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="预览失败")

@router.get("/favorites/{file_hash}/download")
async def download_favorite_video(file_hash: str):
    """下载收藏的视频（基于MinIO）"""
    try:
        # 获取收藏详情
        file_record = await favorite_service._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        # 检查是否已下载到MinIO
        if file_record.get("storage_type") != "minio" or not file_record.get("minio_object_key"):
            raise HTTPException(status_code=400, detail="视频未下载到MinIO存储")
        
        # 从MinIO获取预签名URL用于下载
        download_url = await favorite_service.minio_client.get_presigned_url(
            bucket_name=file_record["minio_bucket"],
            object_name=file_record["minio_object_key"],
            expires=3600  # 1小时有效期
        )
        
        if not download_url:
            raise HTTPException(status_code=500, detail="获取MinIO下载链接失败")
        
        # 生成文件名
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{file_record['platform']}_{file_record['content_id']}_{timestamp}.mp4"
        
        # 设置下载头
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Accept-Ranges": "bytes"
        }
        
        # 流式下载
        async def video_stream():
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    else:
                        raise HTTPException(status_code=response.status, detail="下载失败")
        
        return StreamingResponse(
            video_stream(),
            media_type="video/mp4",
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载收藏视频失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="下载失败") 