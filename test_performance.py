#!/usr/bin/env python3
"""
性能测试脚本
用于测试修复后的系统性能和资源管理
"""

import asyncio
import time
import httpx
from datetime import datetime

async def test_health_endpoints():
    """测试健康检查端点"""
    print("🔍 测试健康检查端点...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 测试单平台爬虫健康状态
            response = await client.get("http://localhost:8100/api/v1/crawler/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 单平台爬虫健康状态: {data}")
            else:
                print(f"❌ 单平台爬虫健康检查失败: {response.status_code}")
                
            # 测试多平台爬虫健康状态
            response = await client.get("http://localhost:8100/api/v1/multi-platform/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 多平台爬虫健康状态: {data}")
            else:
                print(f"❌ 多平台爬虫健康检查失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 健康检查测试失败: {e}")

async def test_task_creation():
    """测试任务创建性能"""
    print("🚀 测试任务创建性能...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 测试单平台任务创建
            start_time = time.time()
            response = await client.post(
                "http://localhost:8100/api/v1/crawler/start",
                json={
                    "platform": "xhs",
                    "keywords": "测试关键词",
                    "max_notes_count": 5,
                    "crawler_type": "search",
                    "get_comments": False,
                    "save_data_option": "db"
                },
                timeout=30.0
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 单平台任务创建成功: {data['task_id']}")
                print(f"⏱️ 响应时间: {end_time - start_time:.2f}秒")
            else:
                print(f"❌ 单平台任务创建失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                
        except Exception as e:
            print(f"❌ 任务创建测试失败: {e}")

async def test_concurrent_requests():
    """测试并发请求性能"""
    print("🔄 测试并发请求性能...")
    
    async def make_request(client, i):
        try:
            response = await client.get("http://localhost:8100/api/v1/crawler/health")
            return f"请求 {i}: {response.status_code}"
        except Exception as e:
            return f"请求 {i}: 失败 - {e}"
    
    async with httpx.AsyncClient() as client:
        # 创建10个并发请求
        tasks = [make_request(client, i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            print(f"  {result}")

async def test_memory_usage():
    """测试内存使用情况"""
    print("💾 测试内存使用情况...")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    print(f"📊 内存使用情况:")
    print(f"  RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"  VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    print(f"  进程ID: {process.pid}")

async def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 MediaCrawler 性能测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now()}")
    print()
    
    # 测试健康检查
    await test_health_endpoints()
    print()
    
    # 测试内存使用
    await test_memory_usage()
    print()
    
    # 测试并发请求
    await test_concurrent_requests()
    print()
    
    # 测试任务创建
    await test_task_creation()
    print()
    
    print("=" * 60)
    print("✅ 性能测试完成")
    print(f"结束时间: {datetime.now()}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 