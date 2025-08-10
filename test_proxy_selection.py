#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代理选择功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import utils
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager

async def test_proxy_selection():
    """测试代理选择功能"""
    try:
        print("🌐 测试代理选择功能")
        print("=" * 50)
        
        # 获取代理管理器
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 1. 检查可用代理
        print("\n1. 检查可用代理")
        available_proxies = await proxy_manager.get_in_use_proxies()
        print(f"   可用代理数量: {len(available_proxies)}")
        
        if available_proxies:
            print("   可用代理列表:")
            for i, proxy in enumerate(available_proxies):
                print(f"     {i+1}. {proxy.ip}:{proxy.port} (区域: {proxy.area})")
        
        # 2. 测试自动获取代理
        print("\n2. 测试自动获取代理")
        auto_proxy = await proxy_manager.get_available_proxy()
        if auto_proxy:
            print(f"   ✅ 自动获取代理成功: {auto_proxy.ip}:{auto_proxy.port}")
        else:
            print("   ❌ 自动获取代理失败")
        
        # 3. 测试指定IP获取代理
        if available_proxies:
            print("\n3. 测试指定IP获取代理")
            test_ip = available_proxies[0].ip
            
            # 从数据库获取指定IP的代理信息
            from api.crawler_core import get_db_connection
            db = await get_db_connection()
            if db:
                query = "SELECT * FROM proxy_pool WHERE ip = %s AND status = 'active' AND enabled = 1"
                proxy_data = await db.get_first(query, test_ip)
                
                if proxy_data:
                    from proxy.qingguo_long_term_proxy import ProxyInfo, ProxyStatus
                    proxy_info = ProxyInfo(
                        id=str(proxy_data['id']),
                        ip=proxy_data['ip'],
                        port=proxy_data['port'],
                        username=proxy_data.get('username', ''),
                        password=proxy_data.get('password', ''),
                        proxy_type=proxy_data['proxy_type'],
                        expire_ts=proxy_data.get('expire_ts', 0),
                        created_at=proxy_data['created_at'],
                        status=ProxyStatus(proxy_data.get('status', 'active')),
                        enabled=proxy_data.get('enabled', True),
                        area=proxy_data.get('area'),
                        description=proxy_data.get('description')
                    )
                    print(f"   ✅ 指定IP获取代理成功: {proxy_info.ip}:{proxy_info.port}")
                else:
                    print(f"   ❌ 指定IP {test_ip} 的代理不可用")
        
        # 4. 测试API接口
        print("\n4. 测试API接口")
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8100/api/v1/qingguo/in-use")
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"   ✅ API接口正常，返回 {len(result.get('proxies', []))} 个代理")
                    else:
                        print(f"   ❌ API接口返回错误: {result}")
                else:
                    print(f"   ❌ API接口HTTP错误: {response.status_code}")
        except Exception as e:
            print(f"   ❌ API接口调用失败: {e}")
        
        print("\n✅ 代理选择功能测试完成")
        
    except Exception as e:
        print(f"❌ 代理选择功能测试失败: {e}")
        utils.logger.error(f"代理选择功能测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy_selection())
