"""
视频下载API路由
"""

from fastapi import APIRouter, HTTPException, Query, Form
from typing import Dict, Any, List
import logging
from pydantic import BaseModel
from datetime import datetime

from services.video_download_service import VideoDownloadService

logger = logging.getLogger(__name__)

router = APIRouter()
download_service = VideoDownloadService()

class VideoDownloadRequest(BaseModel):
    video_url: str
    video_id: str
    platform: str
    download_type: str = "local"  # local 或 server

@router.post("/videos/download")
async def download_video(request: VideoDownloadRequest):
    """下载视频到用户本地"""
    try:
        # 直接返回文件流，让浏览器下载
        from fastapi.responses import StreamingResponse
        import aiohttp
        
        # 🆕 修复：确保平台参数正确传递和识别
        platform = request.platform.lower()
        video_url = request.video_url.lower()
        
        # 平台标准化处理
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
        normalized_platform = platform_mapping.get(platform, platform)
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # 根据标准化平台设置不同的Referer
        if normalized_platform == "xiaohongshu" or 'xiaohongshu' in video_url or 'xhscdn' in video_url or 'xhs' in video_url:
            headers['Referer'] = 'https://www.xiaohongshu.com/'
            headers['Origin'] = 'https://www.xiaohongshu.com'
            logger.info(f"识别为小红书平台: {normalized_platform}")
            
        elif normalized_platform == "douyin" or 'douyin' in video_url or 'aweme' in video_url or 'amemv' in video_url:
            headers['Referer'] = 'https://www.douyin.com/'
            headers['Origin'] = 'https://www.douyin.com'
            logger.info(f"识别为抖音平台: {normalized_platform}")
            
        elif normalized_platform == "kuaishou" or 'kuaishou' in video_url or 'gifshow' in video_url or 'ks' in video_url:
            headers['Referer'] = 'https://www.kuaishou.com/'
            headers['Origin'] = 'https://www.kuaishou.com'
            logger.info(f"识别为快手平台: {normalized_platform}")
            
        elif normalized_platform == "bilibili" or 'bilibili' in video_url or 'b23.tv' in video_url or 'bilivideo' in video_url:
            headers['Referer'] = 'https://www.bilibili.com/'
            headers['Origin'] = 'https://www.bilibili.com'
            # B站特殊处理：添加更多反爬虫请求头
            headers.update({
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            logger.info(f"识别为B站平台: {normalized_platform}")
            
        elif normalized_platform == "weibo" or 'weibo' in video_url or 'sina' in video_url:
            headers['Referer'] = 'https://weibo.com/'
            headers['Origin'] = 'https://weibo.com'
            logger.info(f"识别为微博平台: {normalized_platform}")
            
        elif normalized_platform == "zhihu" or 'zhihu' in video_url:
            headers['Referer'] = 'https://www.zhihu.com/'
            headers['Origin'] = 'https://www.zhihu.com'
            logger.info(f"识别为知乎平台: {normalized_platform}")
            
        else:
            # 默认使用Google作为Referer
            headers['Referer'] = 'https://www.google.com/'
            headers['Origin'] = 'https://www.google.com'
            logger.info(f"使用默认Referer，平台: {normalized_platform}")
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{normalized_platform}_{request.video_id}_{timestamp}.mp4"
        
        async def video_stream():
            logger.info(f"开始下载视频: {request.video_url}, 平台: {normalized_platform}")
            
            # B站特殊处理：先尝试处理403错误
            final_video_url = request.video_url
            if normalized_platform == "bilibili" or 'bilibili' in video_url or 'bilivideo' in video_url:
                try:
                    from services.bilibili_video_service import bilibili_video_service
                    processed_url = await bilibili_video_service.get_video_url_with_retry(request.video_url)
                    if processed_url:
                        final_video_url = processed_url
                        logger.info(f"B站视频URL处理成功: {final_video_url[:100]}...")
                    else:
                        logger.warning(f"B站视频URL处理失败，使用原始URL")
                except Exception as e:
                    logger.warning(f"B站视频URL处理异常: {e}")
            
            # 快手特殊处理：处理m3u8和mp4格式视频
            elif normalized_platform == "kuaishou" or 'kuaishou' in video_url or '.m3u8' in video_url:
                try:
                    from services.kuaishou_video_service import kuaishou_video_service
                    if '.m3u8' in request.video_url:
                        logger.info(f"检测到快手m3u8格式视频，开始转换下载...")
                        # 下载完整视频：使用full_video=True
                        async for chunk in kuaishou_video_service.convert_m3u8_to_mp4_stream(request.video_url, full_video=True):
                            yield chunk
                        logger.info(f"快手m3u8视频转换下载完成")
                        return
                    else:
                        # 对于mp4格式的快手视频，直接使用原始URL，但设置正确的请求头
                        logger.info(f"检测到快手mp4格式视频，使用原始URL: {request.video_url[:100]}...")
                        # 快手mp4视频需要特殊的请求头
                        headers.update({
                            "Referer": "https://www.kuaishou.com/",
                            "Origin": "https://www.kuaishou.com",
                            "Sec-Fetch-Dest": "video",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "cross-site"
                        })
                        final_video_url = request.video_url
                        logger.info(f"快手mp4视频URL处理完成")
                except Exception as e:
                    logger.warning(f"快手视频URL处理异常: {e}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(final_video_url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"视频下载成功，开始流式传输: {final_video_url}")
                        # 流式传输视频数据
                        chunk_count = 0
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                            chunk_count += 1
                        logger.info(f"视频流式传输完成，共传输 {chunk_count} 个数据块: {final_video_url}")
                    else:
                        # 记录错误但不抛出异常
                        logger.error(f"视频下载失败，状态码: {response.status}, URL: {final_video_url}")
                        # 返回空内容，让前端处理
                        yield b""
        
        return StreamingResponse(
            video_stream(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Accept-Ranges": "bytes"
            }
        )
        
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail="下载视频失败")



@router.get("/downloads/statistics", response_model=Dict[str, Any])
async def get_download_statistics():
    """获取下载统计信息"""
    try:
        results = await download_service.get_download_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取下载统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取下载统计失败") 