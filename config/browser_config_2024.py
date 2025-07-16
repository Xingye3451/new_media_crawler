#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器反检测配置 - 2024年优化版
专门针对快手、抖音、B站等平台的检测机制优化
"""

import random
import os
from typing import Dict, List, Optional

class BrowserConfig2024:
    """2024年浏览器反检测配置"""
    
    # =============================================
    # 2024年最新User-Agent列表
    # =============================================
    
    LATEST_USER_AGENTS = {
        # Chrome 130-131 (最新稳定版)
        "chrome_latest": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ],
        
        # Chrome 128-129 (广泛兼容版)
        "chrome_stable": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        ],
        
        # 移动端User-Agent
        "mobile": [
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/131.0.6613.98 Mobile/15E148 Safari/604.1",
        ]
    }
    
    # =============================================
    # 平台特定User-Agent优化
    # =============================================
    
    PLATFORM_USER_AGENTS = {
        "kuaishou": [
            # 快手推荐使用Windows桌面版Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ],
        "douyin": [
            # 抖音偏好macOS和Windows混合
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ],
        "bilibili": [
            # B站对版本要求较高
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ],
        "xhs": [
            # 小红书通用配置
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ]
    }
    
    # =============================================
    # 增强版浏览器启动参数
    # =============================================
    
    ENHANCED_BROWSER_ARGS = [
        # 基础安全参数
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        
        # 反检测核心参数
        "--disable-blink-features=AutomationControlled",
        "--disable-features=VizDisplayCompositor,TranslateUI",
        "--disable-automation",
        "--disable-default-apps",
        "--disable-component-update",
        
        # 内存和性能优化
        "--max_old_space_size=4096",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-field-trial-config",
        
        # 网络和安全
        "--disable-ipc-flooding-protection",
        "--disable-hang-monitor",
        "--disable-prompt-on-repost",
        "--disable-domain-reliability",
        "--disable-background-networking",
        
        # WebRTC和媒体
        "--disable-webrtc-multiple-routes",
        "--disable-webrtc-hw-decoding", 
        "--disable-webrtc-hw-encoding",
        
        # 快手特定优化
        "--disable-web-security",  # 快手可能需要
        "--disable-features=TranslateUI",
        "--ignore-certificate-errors",
        "--ignore-ssl-errors",
        "--ignore-certificate-errors-spki-list",
        
        # 抖音特定优化
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        
        # 通用反检测
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-logging",
        "--disable-plugins-discovery",
        "--disable-translate",
    ]
    
    # =============================================
    # 远程桌面环境特殊参数
    # =============================================
    
    REMOTE_DESKTOP_ARGS = [
        # X11显示优化
        "--use-gl=swiftshader",
        "--disable-software-rasterizer",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=TranslateUI,BlinkGenPropertyTrees",
        "--run-all-compositor-stages-before-draw",
        "--disable-new-content-rendering-timeout",
        
        # VNC环境优化
        "--disable-gpu-sandbox",
        "--disable-software-rasterizer",
        "--ignore-gpu-blacklist",
        "--enable-gpu-rasterization",
        "--enable-oop-rasterization",
        
        # 显示相关
        "--force-device-scale-factor=1",
        "--high-dpi-support=1",
        "--force-color-profile=srgb",
    ]
    
    # =============================================
    # 视窗大小配置（优化远程桌面显示）
    # =============================================
    
    VIEWPORT_SIZES = [
        {"width": 1260, "height": 680},   # VNC远程桌面优化（主推荐）
        {"width": 1200, "height": 650},   # VNC备选1
        {"width": 1150, "height": 600},   # VNC备选2  
        {"width": 1100, "height": 580},   # VNC最小尺寸
        {"width": 1280, "height": 720},   # 兼容性保底
    ]
    
    # =============================================
    # 媒体设备伪装
    # =============================================
    
    FAKE_MEDIA_CONFIG = {
        "audio": {
            "sampleRate": 44100,
            "sampleSize": 16,
            "channelCount": 2
        },
        "video": {
            "width": 1280,
            "height": 720,
            "frameRate": 30,
            "facingMode": "user"
        }
    }
    
    @classmethod
    def get_user_agent(cls, platform: str = "auto") -> str:
        """获取适合的User-Agent"""
        if platform == "auto":
            # 自动选择最新稳定版本
            return random.choice(cls.LATEST_USER_AGENTS["chrome_latest"])
        elif platform in cls.PLATFORM_USER_AGENTS:
            return random.choice(cls.PLATFORM_USER_AGENTS[platform])
        else:
            return random.choice(cls.LATEST_USER_AGENTS["chrome_stable"])
    
    @classmethod
    def get_browser_args(cls, platform: str = "auto", remote_desktop: bool = True) -> List[str]:
        """获取浏览器启动参数"""
        args = cls.ENHANCED_BROWSER_ARGS.copy()
        
        if remote_desktop:
            args.extend(cls.REMOTE_DESKTOP_ARGS)
        
        # 平台特定参数
        if platform == "kuaishou":
            args.extend([
                "--disable-features=VizDisplayCompositor,ChromeLabs",
                "--enable-features=NetworkService,NetworkServiceInProcess",
            ])
        elif platform == "douyin": 
            args.extend([
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=MediaRouter",
            ])
        elif platform == "bilibili":
            args.extend([
                "--enable-features=VaapiVideoDecoder",
                "--disable-features=UseChromeOSDirectVideoDecoder",
            ])
            
        return args
    
    @classmethod
    def get_viewport(cls) -> Dict[str, int]:
        """获取随机视窗大小"""
        return random.choice(cls.VIEWPORT_SIZES)
    
    @classmethod
    def get_browser_context_config(cls, platform: str = "auto") -> Dict:
        """获取完整的浏览器上下文配置"""
        user_agent = cls.get_user_agent(platform)
        viewport = cls.get_viewport()
        
        return {
            "user_agent": user_agent,
            "viewport": viewport,
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "geolocation": {"longitude": 116.3975, "latitude": 39.9085},  # 北京坐标
            "permissions": ["geolocation", "notifications"],
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "forced_colors": "none",
            "extra_http_headers": {
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            }
        }

# =============================================
# 快手专用配置
# =============================================

class KuaishouConfig(BrowserConfig2024):
    """快手平台专用配置"""
    
    @classmethod
    def get_enhanced_config(cls):
        config = cls.get_browser_context_config("kuaishou")
        
        # 快手特定的HTTP头
        config["extra_http_headers"].update({
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-User": "?1",
        })
        
        # 快手可能需要的特殊权限
        config["permissions"].extend(["camera", "microphone"])
        
        return config

# =============================================
# 抖音专用配置  
# =============================================

class DouyinConfig(BrowserConfig2024):
    """抖音平台专用配置"""
    
    @classmethod
    def get_enhanced_config(cls):
        config = cls.get_browser_context_config("douyin")
        
        # 抖音特定的HTTP头
        config["extra_http_headers"].update({
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0", 
            "Sec-Ch-Ua-Platform": '"macOS"',  # 抖音偏好macOS
            "Referer": "https://www.douyin.com/",
        })
        
        return config

# =============================================
# B站专用配置
# =============================================

class BilibiliConfig(BrowserConfig2024):
    """B站平台专用配置"""
    
    @classmethod 
    def get_enhanced_config(cls):
        config = cls.get_browser_context_config("bilibili")
        
        # B站特定的HTTP头
        config["extra_http_headers"].update({
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Origin": "https://www.bilibili.com",
            "Referer": "https://www.bilibili.com/",
        })
        
        return config

# =============================================
# 使用示例
# =============================================

def get_platform_config(platform: str) -> Dict:
    """根据平台获取最优配置"""
    configs = {
        "kuaishou": KuaishouConfig,
        "douyin": DouyinConfig, 
        "bilibili": BilibiliConfig,
        "xhs": BrowserConfig2024,
    }
    
    config_class = configs.get(platform, BrowserConfig2024)
    if hasattr(config_class, 'get_enhanced_config'):
        return config_class.get_enhanced_config()
    else:
        return config_class.get_browser_context_config(platform)

if __name__ == "__main__":
    # 测试配置
    print("=== 快手配置 ===")
    ks_config = get_platform_config("kuaishou")
    print(f"User-Agent: {ks_config['user_agent']}")
    print(f"Viewport: {ks_config['viewport']}")
    
    print("\n=== 抖音配置 ===") 
    dy_config = get_platform_config("douyin")
    print(f"User-Agent: {dy_config['user_agent']}")
    
    print("\n=== B站配置 ===")
    bili_config = get_platform_config("bilibili") 
    print(f"User-Agent: {bili_config['user_agent']}") 