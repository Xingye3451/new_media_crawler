#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理API测试脚本
"""

import asyncio
import aiohttp
import json

async def test_account_api():
    """测试账号管理API"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 开始测试账号管理API...")
        
        # 测试获取平台列表
        print("\n1. 测试获取平台列表...")
        try:
            async with session.get(f"{base_url}/api/v1/accounts/platforms") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 平台列表获取成功: {len(data)} 个平台")
                    for platform in data:
                        print(f"   - {platform['name']} ({platform['code']})")
                else:
                    print(f"❌ 平台列表获取失败: HTTP {response.status}")
        except Exception as e:
            print(f"❌ 平台列表获取异常: {e}")
        
        # 测试获取账号列表
        print("\n2. 测试获取账号列表...")
        try:
            async with session.get(f"{base_url}/api/v1/accounts/") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 200:
                        accounts = data.get('data', [])
                        print(f"✅ 账号列表获取成功: {len(accounts)} 个账号")
                        for account in accounts:
                            print(f"   - {account['account_name']} ({account['platform']})")
                    else:
                        print(f"❌ 账号列表获取失败: {data.get('message')}")
                else:
                    print(f"❌ 账号列表获取失败: HTTP {response.status}")
        except Exception as e:
            print(f"❌ 账号列表获取异常: {e}")
        
        # 测试创建账号
        print("\n3. 测试创建账号...")
        test_account = {
            "platform": "xhs",
            "account_name": "测试账号",
            "account_id": "test123",
            "username": "testuser",
            "phone": "13800138000",
            "email": "test@example.com",
            "login_method": "qrcode",
            "is_active": True,
            "notes": "这是一个测试账号"
        }
        
        try:
            async with session.post(
                f"{base_url}/api/v1/accounts/",
                json=test_account,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 200:
                        print("✅ 账号创建成功")
                    else:
                        print(f"❌ 账号创建失败: {data.get('message')}")
                else:
                    print(f"❌ 账号创建失败: HTTP {response.status}")
        except Exception as e:
            print(f"❌ 账号创建异常: {e}")
        
        # 测试远程桌面状态
        print("\n4. 测试远程桌面状态...")
        try:
            async with session.get(f"{base_url}/api/v1/login/remote_desktop/status") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 200:
                        status = data.get('data', {})
                        print(f"✅ 远程桌面状态: {status.get('status', 'unknown')}")
                        print(f"   - 可用: {status.get('available', False)}")
                        print(f"   - 消息: {status.get('message', 'N/A')}")
                    else:
                        print(f"❌ 远程桌面状态获取失败: {data.get('message')}")
                else:
                    print(f"❌ 远程桌面状态获取失败: HTTP {response.status}")
        except Exception as e:
            print(f"❌ 远程桌面状态获取异常: {e}")
        
        print("\n🎉 账号管理API测试完成!")

if __name__ == "__main__":
    asyncio.run(test_account_api()) 