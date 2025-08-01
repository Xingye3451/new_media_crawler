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

# 使用懒加载模式，避免在模块导入时就创建实例
_favorite_service = None

def get_favorite_service():
    """获取视频收藏服务实例（懒加载）"""
    global _favorite_service
    if _favorite_service is None:
        _favorite_service = VideoFavoriteService()
    return _favorite_service

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
        result = await get_favorite_service().add_favorite(request.dict())
        
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
        result = await get_favorite_service().download_and_store(
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

@router.get("/favorites/statistics", response_model=Dict[str, Any])
async def get_favorites_statistics():
    """获取收藏统计信息"""
    try:
        result = await get_favorite_service().get_favorites_statistics()
        
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
        logger.error(f"获取收藏统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计失败")

@router.get("/favorites/list", response_model=Dict[str, Any])
async def get_favorites(
    platform: str = Query(None, description="平台筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取收藏列表"""
    try:
        result = await get_favorite_service().get_favorites(
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
        result = await get_favorite_service().remove_favorite(file_hash)
        
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
        service = get_favorite_service()
        
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
        file_record = await get_favorite_service()._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        # 检查是否已下载到MinIO
        if file_record.get("storage_type") != "minio" or not file_record.get("minio_object_key"):
            raise HTTPException(status_code=400, detail="视频未下载到MinIO存储")
        
        # 从MinIO获取预签名URL
        minio_url = await get_favorite_service().minio_client.get_presigned_url(
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
        file_record = await get_favorite_service()._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        # 检查是否已下载到MinIO
        if file_record.get("storage_type") != "minio" or not file_record.get("minio_object_key"):
            raise HTTPException(status_code=400, detail="视频未下载到MinIO存储")
        
        # 从MinIO获取预签名URL用于下载
        download_url = await get_favorite_service().minio_client.get_presigned_url(
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
            # B站特殊处理：先尝试处理403错误
            final_download_url = download_url
            if file_record.get("platform") == "bilibili" or 'bilibili' in download_url or 'bilivideo' in download_url:
                try:
                    from services.bilibili_video_service import bilibili_video_service
                    processed_url = await bilibili_video_service.get_video_url_with_retry(download_url)
                    if processed_url:
                        final_download_url = processed_url
                        logger.info(f"B站视频URL处理成功: {final_download_url[:100]}...")
                    else:
                        logger.warning(f"B站视频URL处理失败，使用原始URL")
                except Exception as e:
                    logger.warning(f"B站视频URL处理异常: {e}")
            
            # 快手特殊处理：处理m3u8和mp4格式视频
            elif file_record.get("platform") == "kuaishou" or 'kuaishou' in download_url or '.m3u8' in download_url:
                try:
                    from services.kuaishou_video_service import kuaishou_video_service
                    if '.m3u8' in download_url:
                        logger.info(f"检测到快手m3u8格式视频，开始转换下载...")
                        # 下载完整视频：使用full_video=True
                        async for chunk in kuaishou_video_service.convert_m3u8_to_mp4_stream(download_url, full_video=True):
                            yield chunk
                        logger.info(f"快手m3u8视频转换下载完成")
                        return
                    else:
                        # 对于mp4格式的快手视频，直接使用原始URL，但设置正确的请求头
                        logger.info(f"检测到快手mp4格式视频，使用原始URL: {download_url[:100]}...")
                        # 快手mp4视频需要特殊的请求头
                        headers.update({
                            "Referer": "https://www.kuaishou.com/",
                            "Origin": "https://www.kuaishou.com",
                            "Sec-Fetch-Dest": "video",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "cross-site"
                        })
                        final_download_url = download_url
                        logger.info(f"快手mp4视频URL处理完成")
                except Exception as e:
                    logger.warning(f"快手视频URL处理异常: {e}")
            
            # 设置通用请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            
            # 根据平台设置特殊请求头
            if file_record.get("platform") == "bilibili":
                headers.update({
                    "Referer": "https://www.bilibili.com/",
                    "Origin": "https://www.bilibili.com",
                    "Sec-Fetch-Dest": "video",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                })
            elif file_record.get("platform") == "kuaishou":
                headers.update({
                    "Referer": "https://www.kuaishou.com/",
                    "Origin": "https://www.kuaishou.com",
                    "Sec-Fetch-Dest": "video",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site"
                })
            
            async with aiohttp.ClientSession() as session:
                async with session.get(final_download_url, headers=headers) as response:
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