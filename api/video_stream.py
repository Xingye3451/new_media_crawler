"""
视频流API路由
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, FileResponse
from typing import Dict, Any
import logging
import os
import aiofiles

from services.video_stream_service import VideoStreamService

logger = logging.getLogger(__name__)

router = APIRouter()

# 使用懒加载模式，避免在模块导入时就创建实例
_stream_service = None

def get_stream_service():
    """获取视频流服务实例（懒加载）"""
    global _stream_service
    if _stream_service is None:
        _stream_service = VideoStreamService()
    return _stream_service

@router.get("/stream/video", response_model=Dict[str, Any])
async def get_stream_info(
    video_url: str = Query(..., description="视频URL"),
    platform: str = Query(..., description="平台"),
    content_id: str = Query(..., description="内容ID")
):
    """获取视频流信息"""
    try:
        result = await get_stream_service().stream_video(video_url, platform, content_id)
        
        if result["success"]:
            return {
                "code": 200,
                "message": "获取成功",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取流信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.get("/stream/cache/{cache_key}")
async def stream_cache_video(cache_key: str):
    """流式播放缓存视频"""
    try:
        cache_file = os.path.join(get_stream_service().cache_dir, f"{cache_key}.mp4")
        
        if not os.path.exists(cache_file):
            raise HTTPException(status_code=404, detail="缓存文件不存在")
        
        # 返回文件流
        return FileResponse(
            cache_file,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式播放缓存失败 {cache_key}: {str(e)}")
        raise HTTPException(status_code=500, detail="播放失败")

@router.get("/stream/local/{file_hash}")
async def stream_local_video(file_hash: str):
    """流式播放本地视频"""
    try:
        # 从数据库获取文件记录
        from api.video_favorites import get_favorite_service
        
        file_record = await get_favorite_service()._get_file_by_hash(file_hash)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件记录不存在")
        
        local_path = file_record.get("local_path")
        if not local_path or not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="本地文件不存在")
        
        # 返回文件流
        return FileResponse(
            local_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式播放本地视频失败 {file_hash}: {str(e)}")
        raise HTTPException(status_code=500, detail="播放失败")

@router.get("/stream/direct")
async def stream_direct_video(
    video_url: str = Query(..., description="视频URL"),
    platform: str = Query(..., description="平台")
):
    """直接流式传输视频"""
    try:
        import aiohttp
        import urllib.parse
        
        # URL解码
        decoded_url = urllib.parse.unquote(video_url)
        logger.info(f"开始直接流式传输: {decoded_url}, 平台: {platform}")
        
        # 根据平台设置不同的请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }
        
        # 🆕 修复：平台标准化处理
        platform_mapping = {
            'bili': 'bilibili',
            'bilibili': 'bilibili',
            'ks': 'kuaishou', 
            'kuaishou': 'kuaishou',
            'dy': 'douyin',
            'douyin': 'douyin',
            'xhs': 'xiaohongshu',
            'xiaohongshu': 'xiaohongshu',
            'wb': 'weibo',
            'weibo': 'weibo',
            'zhihu': 'zhihu'
        }
        
        # 标准化平台名称
        normalized_platform = platform_mapping.get(platform.lower(), platform.lower())
        
        # 根据标准化平台设置不同的Referer
        if normalized_platform == "xiaohongshu":
            headers.update({
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com"
            })
            logger.info(f"识别为小红书平台: {normalized_platform}")
        elif normalized_platform == "douyin":
            headers.update({
                "Referer": "https://www.douyin.com/",
                "Origin": "https://www.douyin.com"
            })
            logger.info(f"识别为抖音平台: {normalized_platform}")
        elif normalized_platform == "kuaishou":
            headers.update({
                "Referer": "https://www.kuaishou.com/",
                "Origin": "https://www.kuaishou.com"
            })
            logger.info(f"识别为快手平台: {normalized_platform}")
        elif normalized_platform == "bilibili":
            headers.update({
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            })
            logger.info(f"识别为B站平台: {normalized_platform}")
        elif normalized_platform == "weibo":
            headers.update({
                "Referer": "https://weibo.com/",
                "Origin": "https://weibo.com"
            })
            logger.info(f"识别为微博平台: {normalized_platform}")
        elif normalized_platform == "zhihu":
            headers.update({
                "Referer": "https://www.zhihu.com/",
                "Origin": "https://www.zhihu.com"
            })
            logger.info(f"识别为知乎平台: {normalized_platform}")
        else:
            # 默认使用Google的Referer
            headers.update({
                "Referer": "https://www.google.com/",
                "Origin": "https://www.google.com"
            })
            logger.info(f"使用默认Referer，平台: {normalized_platform}")
        
        async def video_stream():
            """视频流生成器"""
            # B站特殊处理：先尝试处理403错误
            final_url = decoded_url
            if normalized_platform == "bilibili" or 'bilibili' in decoded_url or 'bilivideo' in decoded_url:
                try:
                    from services.bilibili_video_service import bilibili_video_service
                    processed_url = await bilibili_video_service.get_video_url_with_retry(decoded_url)
                    if processed_url:
                        final_url = processed_url
                        logger.info(f"B站视频URL处理成功: {final_url[:100]}...")
                    else:
                        logger.warning(f"B站视频URL处理失败，使用原始URL")
                except Exception as e:
                    logger.warning(f"B站视频URL处理异常: {e}")
            
            # 快手特殊处理：处理m3u8和mp4格式视频
            elif normalized_platform == "kuaishou" or 'kuaishou' in decoded_url or '.m3u8' in decoded_url:
                try:
                    from services.kuaishou_video_service import kuaishou_video_service
                    if '.m3u8' in decoded_url:
                        logger.info(f"检测到快手m3u8格式视频，开始转换流...")
                        async for chunk in kuaishou_video_service.convert_m3u8_to_mp4_stream(decoded_url):
                            yield chunk
                        return
                    else:
                        # 对于mp4格式的快手视频，直接使用原始URL，但设置正确的请求头
                        logger.info(f"检测到快手mp4格式视频，使用原始URL: {decoded_url[:100]}...")
                        # 快手mp4视频需要特殊的请求头
                        headers.update({
                            "Referer": "https://www.kuaishou.com/",
                            "Origin": "https://www.kuaishou.com",
                            "Sec-Fetch-Dest": "video",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "cross-site"
                        })
                        final_url = decoded_url
                        logger.info(f"快手mp4视频URL处理完成")
                except Exception as e:
                    logger.warning(f"快手视频URL处理异常: {e}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(final_url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"开始流式传输视频，状态码: {response.status}")
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    else:
                        logger.error(f"视频下载失败，状态码: {response.status}")
                        yield b""
        
        return StreamingResponse(
            video_stream(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"直接流式传输失败 {video_url}: {str(e)}")
        raise HTTPException(status_code=500, detail="流式传输失败")

@router.get("/stream/cache-info")
async def get_cache_info():
    """获取缓存信息"""
    try:
        info = await get_stream_service().get_cache_info()
        return {
            "code": 200,
            "message": "获取成功",
            "data": info
        }
    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取失败")

@router.post("/stream/cleanup")
async def cleanup_cache():
    """清理过期缓存"""
    try:
        await get_stream_service().cleanup_expired_cache()
        return {
            "code": 200,
            "message": "清理完成",
            "data": {"cleaned": True}
        }
    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清理失败") 