#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代理信息打印功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager, ProxyInfo, ProxyStatus
from datetime import datetime

async def test_proxy_logging():
    """测试代理信息打印功能"""
    try:
        print("📋 测试代理信息打印功能")
        print("=" * 50)
        
        # 获取代理管理器
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 1. 获取可用代理
        print("\n1. 获取可用代理")
        available_proxies = await proxy_manager.get_in_use_proxies()
        print(f"   可用代理数量: {len(available_proxies)}")
        
        if not available_proxies:
            print("   ❌ 没有可用代理，无法测试")
            return
        
        # 2. 模拟代理信息打印
        print("\n2. 模拟代理信息打印")
        proxy_info = available_proxies[0]
        
        print(f"   📋 代理详细信息:")
        print(f"     ├─ 代理ID: {proxy_info.id}")
        print(f"     ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
        print(f"     ├─ 代理类型: {proxy_info.proxy_type}")
        print(f"     ├─ 用户名: {proxy_info.username}")
        print(f"     ├─ 区域: {proxy_info.area}")
        print(f"     ├─ 描述: {proxy_info.description}")
        print(f"     └─ 过期时间: {proxy_info.expire_ts}")
        
        print(f"\n   🌐 代理使用信息:")
        print(f"     ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
        print(f"     ├─ 代理类型: {proxy_info.proxy_type}")
        print(f"     ├─ 认证信息: {proxy_info.username}:{proxy_info.password}")
        print(f"     ├─ 区域: {proxy_info.area}")
        print(f"     ├─ 描述: {proxy_info.description}")
        print(f"     └─ 使用方式: curl -x {proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port} https://httpbin.org/ip")
        
        # 3. 测试日志打印
        print("\n3. 测试日志打印")
        utils.logger.info("=" * 60)
        utils.logger.info("📋 代理详细信息:")
        utils.logger.info(f"  ├─ 代理ID: {proxy_info.id}")
        utils.logger.info(f"  ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
        utils.logger.info(f"  ├─ 代理类型: {proxy_info.proxy_type}")
        utils.logger.info(f"  ├─ 用户名: {proxy_info.username}")
        utils.logger.info(f"  ├─ 区域: {proxy_info.area}")
        utils.logger.info(f"  ├─ 描述: {proxy_info.description}")
        utils.logger.info(f"  └─ 过期时间: {proxy_info.expire_ts}")
        
        utils.logger.info("🌐 代理使用信息:")
        utils.logger.info(f"  ├─ 代理地址: {proxy_info.ip}:{proxy_info.port}")
        utils.logger.info(f"  ├─ 代理类型: {proxy_info.proxy_type}")
        utils.logger.info(f"  ├─ 认证信息: {proxy_info.username}:{proxy_info.password}")
        utils.logger.info(f"  ├─ 区域: {proxy_info.area}")
        utils.logger.info(f"  ├─ 描述: {proxy_info.description}")
        utils.logger.info(f"  └─ 使用方式: curl -x {proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port} https://httpbin.org/ip")
        utils.logger.info("=" * 60)
        
        # 4. 测试curl命令
        print("\n4. 测试curl命令")
        curl_command = f"curl -x {proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port} https://httpbin.org/ip"
        print(f"   Curl命令: {curl_command}")
        
        # 5. 测试Playwright配置
        print("\n5. 测试Playwright配置")
        playwright_config = {
            "server": f"{proxy_info.proxy_type}://{proxy_info.ip}:{proxy_info.port}",
            "username": proxy_info.username,
            "password": proxy_info.password
        }
        print(f"   Playwright配置: {playwright_config}")
        
        # 6. 测试httpx配置
        print("\n6. 测试httpx配置")
        httpx_config = {
            "http://": f"{proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port}",
            "https://": f"{proxy_info.proxy_type}://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port}"
        }
        print(f"   httpx配置: {httpx_config}")
        
        print("\n✅ 代理信息打印功能测试完成")
        
    except Exception as e:
        print(f"❌ 代理信息打印功能测试失败: {e}")
        utils.logger.error(f"代理信息打印功能测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy_logging())
