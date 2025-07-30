#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
B站视频下载服务
处理B站视频的403错误和反爬虫机制
"""

import asyncio
import json
import random
import time
from typing import Dict, List, Optional, Tuple
import httpx
from tools import utils


class BilibiliVideoService:
    """B站视频下载服务"""
    
    def __init__(self):
        self.session = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
    
    async def get_video_url_with_retry(self, video_url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取B站视频URL，带重试机制
        Args:
            video_url: 原始视频URL
            max_retries: 最大重试次数
        Returns:
            处理后的视频URL或None
        """
        for attempt in range(max_retries):
            try:
                # 尝试不同的方法获取视频URL
                processed_url = await self._process_video_url(video_url, attempt)
                if processed_url:
                    utils.logger.info(f"[BilibiliVideoService] 成功获取视频URL: {processed_url[:100]}...")
                    return processed_url
                    
            except Exception as e:
                utils.logger.warning(f"[BilibiliVideoService] 第{attempt + 1}次尝试失败: {e}")
                
            # 等待一段时间再重试
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(1, 3))
        
        utils.logger.error(f"[BilibiliVideoService] 所有重试都失败，无法获取视频URL")
        return None
    
    async def _process_video_url(self, video_url: str, attempt: int) -> Optional[str]:
        """
        处理视频URL的不同方法
        Args:
            video_url: 原始视频URL
            attempt: 尝试次数
        Returns:
            处理后的URL
        """
        if attempt == 0:
            # 方法1: 直接使用原始URL，添加必要的请求头
            return await self._method_direct_access(video_url)
        elif attempt == 1:
            # 方法2: 通过B站API获取新的播放地址
            return await self._method_api_refresh(video_url)
        else:
            # 方法3: 使用备用CDN
            return await self._method_cdn_fallback(video_url)
    
    async def _method_direct_access(self, video_url: str) -> Optional[str]:
        """方法1: 直接访问，添加反爬虫请求头"""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(video_url, headers=headers)
                if response.status_code == 200:
                    return video_url
                else:
                    utils.logger.warning(f"[BilibiliVideoService] 直接访问失败，状态码: {response.status_code}")
                    return None
                    
        except Exception as e:
            utils.logger.warning(f"[BilibiliVideoService] 直接访问异常: {e}")
            return None
    
    async def _method_api_refresh(self, video_url: str) -> Optional[str]:
        """方法2: 通过API刷新播放地址"""
        try:
            # 从URL中提取aid和cid
            # 这里需要根据实际的URL格式来解析
            # 暂时返回原始URL，实际实现需要调用B站API
            utils.logger.info(f"[BilibiliVideoService] 尝试通过API刷新播放地址")
            return video_url
            
        except Exception as e:
            utils.logger.warning(f"[BilibiliVideoService] API刷新失败: {e}")
            return None
    
    async def _method_cdn_fallback(self, video_url: str) -> Optional[str]:
        """方法3: 使用备用CDN"""
        try:
            # 尝试不同的CDN域名
            cdn_domains = [
                "upos-hz-mirrorakam.akamaized.net",
                "upos-sz-mirrorakam.akamaized.net",
                "upos-cqn-mirrorakam.akamaized.net"
            ]
            
            # 从原始URL中提取路径
            if "bilivideo.com" in video_url:
                path = video_url.split("bilivideo.com")[1]
                for cdn in cdn_domains:
                    new_url = f"https://{cdn}{path}"
                    if await self._test_url_accessibility(new_url):
                        utils.logger.info(f"[BilibiliVideoService] 找到可用的CDN: {cdn}")
                        return new_url
            
            return None
            
        except Exception as e:
            utils.logger.warning(f"[BilibiliVideoService] CDN备用方案失败: {e}")
            return None
    
    async def _test_url_accessibility(self, url: str) -> bool:
        """测试URL是否可访问"""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Referer": "https://www.bilibili.com/"
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(url, headers=headers)
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def download_video_with_proxy(self, video_url: str, proxy_config: Dict = None) -> Optional[bytes]:
        """
        使用代理下载视频
        Args:
            video_url: 视频URL
            proxy_config: 代理配置
        Returns:
            视频内容或None
        """
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site"
            }
            
            # 设置代理
            proxies = None
            if proxy_config:
                proxy_url = f"http://{proxy_config.get('username')}:{proxy_config.get('password')}@{proxy_config.get('host')}:{proxy_config.get('port')}"
                proxies = {"http://": proxy_url, "https://": proxy_url}
            
            async with httpx.AsyncClient(
                timeout=30.0,
                proxies=proxies,
                follow_redirects=True
            ) as client:
                response = await client.get(video_url, headers=headers)
                
                if response.status_code == 200:
                    utils.logger.info(f"[BilibiliVideoService] 视频下载成功，大小: {len(response.content)} bytes")
                    return response.content
                else:
                    utils.logger.error(f"[BilibiliVideoService] 视频下载失败，状态码: {response.status_code}")
                    return None
                    
        except Exception as e:
            utils.logger.error(f"[BilibiliVideoService] 视频下载异常: {e}")
            return None
    
    async def get_video_info(self, video_url: str) -> Dict:
        """
        获取视频信息
        Args:
            video_url: 视频URL
        Returns:
            视频信息字典
        """
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Referer": "https://www.bilibili.com/"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(video_url, headers=headers)
                
                info = {
                    "url": video_url,
                    "status_code": response.status_code,
                    "content_length": response.headers.get("content-length"),
                    "content_type": response.headers.get("content-type"),
                    "accessible": response.status_code == 200
                }
                
                utils.logger.info(f"[BilibiliVideoService] 视频信息: {info}")
                return info
                
        except Exception as e:
            utils.logger.error(f"[BilibiliVideoService] 获取视频信息失败: {e}")
            return {"url": video_url, "error": str(e), "accessible": False}


# 全局实例
bilibili_video_service = BilibiliVideoService() 