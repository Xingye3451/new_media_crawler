#!/usr/bin/env python3
"""
临时调试脚本：检查登录会话状态
"""
import requests
import json

API_BASE = "http://localhost:8100/api/v1"

def check_sessions():
    """检查当前活跃的登录会话"""
    print("🔍 检查当前登录会话状态...")
    
    # 这里我们需要通过API间接检查
    # 由于login_sessions是内存变量，我们先尝试获取账号列表
    try:
        response = requests.get(f"{API_BASE}/accounts/")
        if response.status_code == 200:
            accounts = response.json()
            print(f"✅ 找到 {len(accounts)} 个账号:")
            
            for account in accounts[:5]:  # 只显示前5个
                print(f"  - ID: {account['id']}, 平台: {account['platform']}, 名称: {account['account_name']}")
            
            return accounts
        else:
            print(f"❌ 获取账号列表失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

def start_test_login(account_id):
    """启动一个测试登录会话"""
    print(f"\n🚀 启动测试登录会话，账号ID: {account_id}")
    
    try:
        data = {
            "account_id": account_id,
            "login_method": "qrcode"
        }
        
        response = requests.post(
            f"{API_BASE}/login/start",
            headers={"Content-Type": "application/json"},
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            session_id = result["session_id"]
            print(f"✅ 登录会话创建成功!")
            print(f"   Session ID: {session_id}")
            print(f"   状态: {result['status']}")
            print(f"   消息: {result['message']}")
            
            return session_id
        else:
            print(f"❌ 创建登录会话失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_current_page_api(session_id):
    """测试获取当前页面API"""
    print(f"\n🔗 测试获取页面URL API，Session ID: {session_id}")
    
    try:
        response = requests.get(f"{API_BASE}/login/current_page/{session_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API调用成功!")
            print(f"   当前URL: {result.get('current_url', 'N/A')}")
            print(f"   状态: {result.get('status', 'N/A')}")
            print(f"   消息: {result.get('message', 'N/A')}")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    print("=" * 60)
    print("🔧 MediaCrawler 登录会话调试工具")
    print("=" * 60)
    
    # 1. 检查账号列表
    accounts = check_sessions()
    
    if not accounts:
        print("\n❌ 没有可用账号，请先添加账号")
        return
    
    # 2. 找一个抖音账号进行测试
    dy_account = None
    for account in accounts:
        if account['platform'] == 'dy':
            dy_account = account
            break
    
    if not dy_account:
        print("\n⚠️ 没有找到抖音账号，使用第一个账号进行测试")
        dy_account = accounts[0]
    
    # 3. 启动测试登录
    session_id = start_test_login(dy_account['id'])
    
    if session_id:
        # 4. 等待一下让后台任务运行
        import time
        print("\n⏳ 等待3秒让后台登录任务运行...")
        time.sleep(3)
        
        # 5. 测试获取页面URL API
        test_current_page_api(session_id)
        
        print(f"\n🎯 现在你可以在界面中使用这个 Session ID: {session_id}")
    else:
        print("\n❌ 无法创建登录会话")

if __name__ == "__main__":
    main() 