#!/usr/bin/env python3
"""
详细的远程桌面调试脚本
逐步检查每个组件的状态
"""

import os
import sys
import subprocess
import time
import requests
import json
from datetime import datetime

def run_command(cmd, timeout=10, shell=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Command timeout", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

def check_services():
    """检查所有相关服务状态"""
    print("🔍 检查服务状态...")
    print("=" * 50)
    
    # 检查VNC服务
    print("1. 检查VNC服务:")
    result = run_command("ps aux | grep vnc")
    if result['success'] and result['stdout']:
        print("✅ VNC进程运行中:")
        for line in result['stdout'].split('\n'):
            if 'vnc' in line.lower() and 'grep' not in line:
                print(f"   {line}")
    else:
        print("❌ VNC进程未运行")
    
    # 检查Xvfb服务
    print("\n2. 检查Xvfb服务:")
    result = run_command("ps aux | grep Xvfb")
    if result['success'] and result['stdout']:
        print("✅ Xvfb进程运行中:")
        for line in result['stdout'].split('\n'):
            if 'Xvfb' in line and 'grep' not in line:
                print(f"   {line}")
    else:
        print("❌ Xvfb进程未运行")
    
    # 检查X11服务
    print("\n3. 检查X11显示器:")
    result = run_command("DISPLAY=:1 xdpyinfo")
    if result['success']:
        print("✅ 显示器:1 可用")
        info = result['stdout'].split('\n')[:3]
        for line in info:
            if line.strip():
                print(f"   {line}")
    else:
        print("❌ 显示器:1 不可用")
        print(f"   错误: {result['stderr']}")
    
    # 检查端口监听
    print("\n4. 检查端口监听:")
    ports = [5901, 6080, 8100]
    for port in ports:
        result = run_command(f"netstat -tuln | grep :{port}")
        if result['success'] and result['stdout']:
            print(f"✅ 端口 {port} 正在监听")
        else:
            print(f"❌ 端口 {port} 未监听")
    
    return True

def check_vnc_access():
    """检查VNC访问"""
    print("\n🌐 检查VNC访问...")
    print("=" * 50)
    
    # 检查HTTP访问
    vnc_urls = [
        "http://localhost:6080",
        "http://192.168.31.231:6080", 
        "http://127.0.0.1:6080"
    ]
    
    for url in vnc_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {url} 可访问 (HTTP {response.status_code})")
            else:
                print(f"⚠️  {url} 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {url} 不可访问: {e}")
    
    return True

def test_browser_launch():
    """测试浏览器启动"""
    print("\n🚀 测试浏览器启动...")
    print("=" * 50)
    
    # 设置DISPLAY环境变量
    os.environ['DISPLAY'] = ':1'
    print(f"设置 DISPLAY={os.environ['DISPLAY']}")
    
    # 测试简单的X11应用
    print("\n1. 测试X11应用:")
    result = run_command("DISPLAY=:1 xterm -e 'echo test; sleep 2' &", timeout=3)
    if result['success']:
        print("✅ X11应用启动成功")
    else:
        print(f"❌ X11应用启动失败: {result['stderr']}")
    
    # 测试Chrome启动
    print("\n2. 测试Chrome启动:")
    chrome_cmd = [
        "google-chrome",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--start-maximized",
        "--no-first-run",
        "--disable-default-apps",
        "https://www.baidu.com"
    ]
    
    # 启动Chrome
    try:
        env = os.environ.copy()
        env['DISPLAY'] = ':1'
        
        process = subprocess.Popen(chrome_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✅ Chrome进程启动，PID: {process.pid}")
        
        # 等待一下让Chrome启动
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("✅ Chrome进程运行中")
            
            # 检查窗口
            result = run_command("DISPLAY=:1 xwininfo -root -tree")
            if result['success']:
                output = result['stdout']
                if 'Chrome' in output or 'Google Chrome' in output:
                    print("✅ 在远程桌面中找到Chrome窗口")
                    # 提取窗口信息
                    lines = output.split('\n')
                    for line in lines:
                        if 'Chrome' in line or 'Google Chrome' in line:
                            print(f"   {line.strip()}")
                else:
                    print("❌ 未在远程桌面中找到Chrome窗口")
                    print("可用窗口:")
                    lines = output.split('\n')
                    for line in lines[:15]:  # 显示前15行
                        if line.strip() and 'RootWindow' not in line:
                            print(f"   {line.strip()}")
            else:
                print(f"❌ 无法检查窗口: {result['stderr']}")
            
            # 终止Chrome进程
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
            print("🛑 Chrome进程已终止")
            
        else:
            print("❌ Chrome进程启动后立即退出")
            stdout, stderr = process.communicate()
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Chrome启动失败: {e}")
    
    return True

def test_api_call():
    """测试API调用"""
    print("\n📡 测试API调用...")
    print("=" * 50)
    
    base_url = "http://localhost:8100"
    
    # 获取账号
    try:
        response = requests.get(f"{base_url}/api/v1/accounts/", timeout=5)
        if response.status_code == 200:
            accounts = response.json()
            if accounts:
                account = accounts[0]
                account_id = account['id']
                print(f"✅ 找到账号: ID={account_id}, 平台={account['platform']}")
                
                # 启动远程桌面登录
                login_data = {
                    "account_id": account_id,
                    "login_method": "remote_desktop"
                }
                
                response = requests.post(f"{base_url}/api/v1/login/remote_start", 
                                       json=login_data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    session_id = result.get("session_id")
                    print(f"✅ 远程桌面登录启动成功")
                    print(f"   会话ID: {session_id}")
                    
                    # 检查状态几次
                    for i in range(5):
                        time.sleep(2)
                        try:
                            response = requests.get(f"{base_url}/api/v1/login/status/{session_id}", timeout=5)
                            if response.status_code == 200:
                                status_data = response.json()
                                status = status_data.get("status")
                                message = status_data.get("message")
                                progress = status_data.get("progress", 0)
                                
                                print(f"   状态检查 {i+1}: {status} - {message} ({progress}%)")
                                
                                if status == "error":
                                    print("❌ 登录过程中出现错误")
                                    break
                                elif status == "waiting_user_login":
                                    print("✅ 已进入等待用户登录状态")
                                    break
                        except Exception as e:
                            print(f"❌ 状态检查失败: {e}")
                    
                    return True
                else:
                    print(f"❌ 远程桌面登录启动失败: {response.status_code}")
                    print(f"   响应: {response.text}")
            else:
                print("❌ 没有可用账号")
        else:
            print(f"❌ 获取账号失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
    
    return False

def main():
    """主函数"""
    print("🔧 远程桌面详细调试")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 检查服务状态
    check_services()
    
    # 检查VNC访问
    check_vnc_access()
    
    # 测试浏览器启动
    test_browser_launch()
    
    # 测试API调用
    test_api_call()
    
    print("\n" + "=" * 50)
    print("🎯 调试完成")
    print("\n💡 建议:")
    print("1. 如果VNC服务未运行，请启动VNC服务")
    print("2. 如果浏览器无法启动，请检查Chrome是否已安装")
    print("3. 如果窗口未出现在远程桌面中，请检查DISPLAY环境变量")
    print("4. 访问 http://192.168.31.231:6080 查看远程桌面")

if __name__ == "__main__":
    main() 