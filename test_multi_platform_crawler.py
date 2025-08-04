#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多平台爬取功能测试脚本
"""

import asyncio
import httpx
import json
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8100/api/v1"

async def test_multi_platform_crawler():
    """测试多平台爬取功能"""
    print("=" * 80)
    print("🚀 开始测试多平台爬取功能")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # 1. 测试多平台功能信息
        print("\n1. 获取多平台功能信息...")
        try:
            response = await client.get(f"{BASE_URL}/multi-platform/info")
            if response.status_code == 200:
                info = response.json()
                print("✅ 多平台功能信息获取成功:")
                print(f"   支持平台: {info.get('supported_platforms', [])}")
                print(f"   账号策略: {info.get('account_strategies', [])}")
                print(f"   执行模式: {info.get('execution_modes', [])}")
                print(f"   保存格式: {info.get('save_formats', [])}")
            else:
                print(f"❌ 获取多平台功能信息失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取多平台功能信息异常: {e}")
        
        # 2. 测试启动多平台爬取任务
        print("\n2. 启动多平台爬取任务...")
        try:
            request_data = {
                "platforms": ["xhs", "dy"],  # 测试小红书和抖音
                "keywords": "编程教程",
                "max_count_per_platform": 5,
                "enable_comments": False,
                "enable_images": False,
                "save_format": "db",
                "use_proxy": False,
                "proxy_strategy": "disabled",
                "account_strategy": "smart",
                "execution_mode": "parallel"
            }
            
            response = await client.post(
                f"{BASE_URL}/multi-platform/start",
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('task_id')
                print(f"✅ 多平台爬取任务启动成功:")
                print(f"   任务ID: {task_id}")
                print(f"   状态: {result.get('status')}")
                print(f"   平台: {result.get('platforms')}")
                print(f"   关键词: {result.get('keywords')}")
                
                # 3. 监控任务状态
                if task_id:
                    print(f"\n3. 监控任务状态 (任务ID: {task_id})...")
                    await monitor_task_status(client, task_id)
            else:
                print(f"❌ 启动多平台爬取任务失败: {response.status_code}")
                print(f"   响应: {response.text}")
                
        except Exception as e:
            print(f"❌ 启动多平台爬取任务异常: {e}")
        
        # 4. 测试获取任务列表
        print("\n4. 获取多平台任务列表...")
        try:
            response = await client.get(f"{BASE_URL}/multi-platform/tasks")
            if response.status_code == 200:
                tasks = response.json()
                print(f"✅ 获取多平台任务列表成功:")
                print(f"   总任务数: {tasks.get('total', 0)}")
                for i, task in enumerate(tasks.get('tasks', [])[:3]):  # 只显示前3个
                    print(f"   任务{i+1}: {task.get('task_id', 'N/A')} - {task.get('status', 'N/A')}")
            else:
                print(f"❌ 获取多平台任务列表失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取多平台任务列表异常: {e}")
    
    print("\n" + "=" * 80)
    print("🏁 多平台爬取功能测试完成")
    print("=" * 80)

async def monitor_task_status(client: httpx.AsyncClient, task_id: str, max_wait: int = 300):
    """监控任务状态"""
    start_time = datetime.now()
    
    while True:
        try:
            response = await client.get(f"{BASE_URL}/multi-platform/status/{task_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                progress = data.get('progress', {})
                results = data.get('results', {})
                errors = data.get('errors', {})
                
                print(f"   状态: {status}")
                if progress:
                    print(f"   进度: {progress.get('completed', 0)}/{progress.get('total', 0)} 平台完成")
                if results:
                    print(f"   结果: {results}")
                if errors:
                    print(f"   错误: {errors}")
                
                # 检查任务是否完成
                if status in ['completed', 'completed_with_errors', 'failed']:
                    print(f"✅ 任务完成，最终状态: {status}")
                    break
                    
            else:
                print(f"❌ 获取任务状态失败: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ 监控任务状态异常: {e}")
            break
        
        # 检查超时
        if (datetime.now() - start_time).seconds > max_wait:
            print(f"⏰ 任务监控超时 ({max_wait}秒)")
            break
            
        # 等待3秒后再次检查
        await asyncio.sleep(3)

async def test_single_platform_crawler():
    """测试单平台爬取功能（对比）"""
    print("\n" + "=" * 80)
    print("🎯 对比测试：单平台爬取功能")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # 测试小红书单平台爬取
        print("\n1. 测试小红书单平台爬取...")
        try:
            request_data = {
                "platform": "xhs",
                "keywords": "编程教程",
                "max_notes_count": 3,
                "crawler_type": "search",
                "get_comments": False,
                "save_data_option": "db",
                "use_proxy": False,
                "proxy_strategy": "disabled"
            }
            
            response = await client.post(
                f"{BASE_URL}/crawler/start",
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('task_id')
                print(f"✅ 小红书单平台爬取任务启动成功:")
                print(f"   任务ID: {task_id}")
                print(f"   状态: {result.get('status')}")
                print(f"   消息: {result.get('message')}")
                
                if task_id:
                    print(f"\n2. 监控单平台任务状态...")
                    await monitor_single_task_status(client, task_id)
            else:
                print(f"❌ 启动小红书单平台爬取任务失败: {response.status_code}")
                print(f"   响应: {response.text}")
                
        except Exception as e:
            print(f"❌ 启动小红书单平台爬取任务异常: {e}")

async def monitor_single_task_status(client: httpx.AsyncClient, task_id: str, max_wait: int = 180):
    """监控单平台任务状态"""
    start_time = datetime.now()
    
    while True:
        try:
            response = await client.get(f"{BASE_URL}/crawler/status/{task_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                progress = data.get('progress', 0)
                result_count = data.get('result_count', 0)
                
                print(f"   状态: {status}, 进度: {progress}%, 结果数: {result_count}")
                
                # 检查任务是否完成
                if status in ['completed', 'failed']:
                    print(f"✅ 单平台任务完成，最终状态: {status}")
                    break
                    
            else:
                print(f"❌ 获取单平台任务状态失败: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ 监控单平台任务状态异常: {e}")
            break
        
        # 检查超时
        if (datetime.now() - start_time).seconds > max_wait:
            print(f"⏰ 单平台任务监控超时 ({max_wait}秒)")
            break
            
        # 等待3秒后再次检查
        await asyncio.sleep(3)

async def main():
    """主函数"""
    print("🔧 MediaCrawler 多平台爬取功能测试")
    print("📅 测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 测试多平台爬取功能
    await test_multi_platform_crawler()
    
    # 对比测试单平台爬取功能
    await test_single_platform_crawler()
    
    print("\n🎉 所有测试完成！")

if __name__ == "__main__":
    asyncio.run(main()) 