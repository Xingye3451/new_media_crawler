"""
快手视频播放服务
处理快手m3u8格式的视频流
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
import re

logger = logging.getLogger(__name__)

class KuaishouVideoService:
    """快手视频播放服务"""
    
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        """获取aiohttp会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_video_url_with_retry(self, video_url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取快手视频URL，支持重试
        
        Args:
            video_url: 原始视频URL
            max_retries: 最大重试次数
        
        Returns:
            处理后的视频URL
        """
        try:
            # 检查是否为m3u8格式
            if '.m3u8' in video_url:
                logger.info(f"检测到m3u8格式视频: {video_url[:100]}...")
                return await self._process_m3u8_url(video_url)
            else:
                logger.info(f"非m3u8格式视频，直接返回: {video_url[:100]}...")
                return video_url
                
        except Exception as e:
            logger.error(f"处理快手视频URL失败: {e}")
            return video_url
    
    async def _process_m3u8_url(self, m3u8_url: str) -> str:
        """
        处理m3u8格式的URL
        
        Args:
            m3u8_url: m3u8格式的URL
        
        Returns:
            处理后的URL
        """
        try:
            session = await self.get_session()
            
            # 设置快手特定的请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.kuaishou.com/",
                "Origin": "https://www.kuaishou.com",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site"
            }
            
            # 获取m3u8文件内容
            async with session.get(m3u8_url, headers=headers) as response:
                if response.status == 200:
                    m3u8_content = await response.text()
                    logger.info(f"成功获取m3u8内容，长度: {len(m3u8_content)}")
                    
                    # 解析m3u8文件，获取第一个ts文件的URL
                    ts_url = await self._extract_first_ts_url(m3u8_url, m3u8_content)
                    if ts_url:
                        logger.info(f"提取到ts文件URL: {ts_url[:100]}...")
                        return ts_url
                    else:
                        logger.warning("无法从m3u8文件中提取ts文件URL")
                        return m3u8_url
                else:
                    logger.error(f"获取m3u8文件失败，状态码: {response.status}")
                    return m3u8_url
                    
        except Exception as e:
            logger.error(f"处理m3u8 URL失败: {e}")
            return m3u8_url
    
    async def _extract_first_ts_url(self, m3u8_url: str, m3u8_content: str) -> Optional[str]:
        """
        从m3u8内容中提取第一个ts文件的URL
        
        Args:
            m3u8_url: 原始m3u8 URL
            m3u8_content: m3u8文件内容
        
        Returns:
            第一个ts文件的URL
        """
        try:
            # 解析m3u8文件
            lines = m3u8_content.strip().split('\n')
            
            # 查找第一个ts文件
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '.ts' in line:
                    # 如果是相对路径，转换为绝对路径
                    if line.startswith('http'):
                        return line
                    else:
                        # 构建绝对URL - 快手视频的特殊处理
                        # 从m3u8 URL中提取基础路径
                        if 'kwaicdn.com' in m3u8_url:
                            # 快手CDN的特殊处理
                            base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                            full_url = base_url + line
                            logger.info(f"构建快手ts文件URL: {full_url[:100]}...")
                            return full_url
                        else:
                            # 通用处理
                            base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                            return base_url + line
            
            # 如果没有找到.ts文件，尝试查找其他视频格式
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and ('.mp4' in line or '.m4v' in line):
                    if line.startswith('http'):
                        return line
                    else:
                        base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                        return base_url + line
            
            logger.warning("在m3u8文件中未找到视频文件")
            return None
            
        except Exception as e:
            logger.error(f"提取ts文件URL失败: {e}")
            return None
    
    async def convert_m3u8_to_mp4_stream(self, m3u8_url: str, full_video: bool = False):
        """
        将m3u8流转换为mp4流
        
        Args:
            m3u8_url: m3u8格式的URL
            full_video: 是否下载完整视频（True用于下载/收藏，False用于预览）
        
        Yields:
            视频数据块
        """
        try:
            session = await self.get_session()
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.kuaishou.com/",
                "Origin": "https://www.kuaishou.com"
            }
            
            # 获取m3u8文件内容
            async with session.get(m3u8_url, headers=headers) as response:
                if response.status == 200:
                    m3u8_content = await response.text()
                    logger.info(f"成功获取m3u8内容，长度: {len(m3u8_content)}")
                    
                    # 解析m3u8文件
                    lines = m3u8_content.strip().split('\n')
                    base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                    
                    # 收集所有ts文件URL
                    ts_urls = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and '.ts' in line:
                            # 构建ts文件URL
                            if line.startswith('http'):
                                ts_url = line
                            else:
                                # 快手CDN的特殊处理
                                if 'kwaicdn.com' in m3u8_url:
                                    base_url = m3u8_url.rsplit('/', 1)[0] + '/'
                                    ts_url = base_url + line
                                else:
                                    ts_url = base_url + line
                            ts_urls.append(ts_url)
                    
                    logger.info(f"找到 {len(ts_urls)} 个ts文件片段")
                    
                    if ts_urls:
                        if full_video:
                            # 下载完整视频：下载所有ts文件
                            logger.info(f"开始下载完整视频，共 {len(ts_urls)} 个片段")
                            for i, ts_url in enumerate(ts_urls, 1):
                                logger.info(f"下载ts文件 {i}/{len(ts_urls)}: {ts_url[:100]}...")
                                async with session.get(ts_url, headers=headers) as ts_response:
                                    if ts_response.status == 200:
                                        async for chunk in ts_response.content.iter_chunked(8192):
                                            yield chunk
                                    else:
                                        logger.warning(f"下载ts文件失败: {ts_url}, 状态码: {ts_response.status}")
                        else:
                            # 预览模式：直接返回第一个ts文件，让浏览器尝试播放
                            first_ts_url = ts_urls[0]
                            logger.info(f"预览模式：使用第一个ts文件作为预览: {first_ts_url[:100]}...")
                            
                            # 直接下载第一个ts文件
                            async with session.get(first_ts_url, headers=headers) as ts_response:
                                if ts_response.status == 200:
                                    async for chunk in ts_response.content.iter_chunked(8192):
                                        yield chunk
                                else:
                                    logger.warning(f"预览模式下载ts文件失败: {first_ts_url}, 状态码: {ts_response.status}")
                    else:
                        logger.warning("未找到ts文件片段")
                    
                else:
                    logger.error(f"获取m3u8文件失败，状态码: {response.status}")
                    
        except Exception as e:
            logger.error(f"转换m3u8流失败: {e}")
            # 如果转换失败，尝试直接返回第一个ts文件
            try:
                first_ts_url = await self._extract_first_ts_url(m3u8_url, "")
                if first_ts_url:
                    logger.info(f"转换失败，尝试直接返回第一个ts文件: {first_ts_url[:100]}...")
                    async with session.get(first_ts_url, headers=headers) as response:
                        if response.status == 200:
                            async for chunk in response.content.iter_chunked(8192):
                                yield chunk
            except Exception as fallback_error:
                logger.error(f"备用方案也失败: {fallback_error}")

# 全局实例
kuaishou_video_service = KuaishouVideoService() 