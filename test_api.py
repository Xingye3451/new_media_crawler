#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MediaCrawler API 测试脚本
用于测试容器化后的API服务功能
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx
import requests

class MediaCrawlerAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_health_check(self) -> bool:
        """测试健康检查"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查通过: {data}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    async def test_get_platforms(self) -> bool:
        """测试获取支持的平台列表"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/platforms")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 获取平台列表成功: {data}")
                return True
            else:
                print(f"❌ 获取平台列表失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 获取平台列表异常: {e}")
            return False
    
    async def test_start_crawler_task(self, platform: str = "xhs", keywords: str = "编程") -> str:
        """测试启动爬虫任务"""
        try:
            payload = {
                "platform": platform,
                "login_type": "qrcode",
                "crawler_type": "search",
                "keywords": keywords,
                "start_page": 1,
                "get_comments": True,
                "get_sub_comments": False,
                "save_data_option": "json",
                "max_notes_count": 5,  # 测试时只爬取少量数据
                "enable_images": False
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/crawler/start",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data["data"]["task_id"]
                print(f"✅ 启动爬虫任务成功: {task_id}")
                return task_id
            else:
                print(f"❌ 启动爬虫任务失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 启动爬虫任务异常: {e}")
            return None
    
    async def test_get_task_status(self, task_id: str) -> Dict[str, Any]:
        """测试获取任务状态"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/crawler/status/{task_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 获取任务状态成功: {data['status']}")
                return data
            else:
                print(f"❌ 获取任务状态失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取任务状态异常: {e}")
            return None
    
    async def test_list_tasks(self) -> bool:
        """测试列出所有任务"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/crawler/tasks")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 列出任务成功: 共 {data['total']} 个任务")
                return True
            else:
                print(f"❌ 列出任务失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 列出任务异常: {e}")
            return False
    
    async def wait_for_task_completion(self, task_id: str, timeout: int = 300) -> bool:
        """等待任务完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_data = await self.test_get_task_status(task_id)
            if status_data:
                if status_data["status"] == "completed":
                    print(f"✅ 任务完成: {task_id}")
                    if status_data.get("result"):
                        print(f"📊 爬取结果: {len(status_data['result'])} 条数据")
                    return True
                elif status_data["status"] == "failed":
                    print(f"❌ 任务失败: {status_data.get('error', '未知错误')}")
                    return False
                else:
                    print(f"⏳ 任务进行中: {status_data['status']}")
            
            await asyncio.sleep(5)  # 每5秒检查一次
        
        print(f"⏰ 任务超时: {timeout}秒")
        return False
    
    async def run_full_test(self):
        """运行完整测试"""
        print("🚀 开始 MediaCrawler API 测试")
        print("=" * 50)
        
        # 1. 健康检查
        print("\n1. 测试健康检查...")
        if not await self.test_health_check():
            print("❌ 健康检查失败，停止测试")
            return False
        
        # 2. 获取平台列表
        print("\n2. 测试获取平台列表...")
        if not await self.test_get_platforms():
            print("❌ 获取平台列表失败")
            return False
        
        # 3. 启动爬虫任务
        print("\n3. 测试启动爬虫任务...")
        task_id = await self.test_start_crawler_task("xhs", "编程")
        if not task_id:
            print("❌ 启动爬虫任务失败")
            return False
        
        # 4. 列出任务
        print("\n4. 测试列出任务...")
        await self.test_list_tasks()
        
        # 5. 等待任务完成
        print("\n5. 等待任务完成...")
        success = await self.wait_for_task_completion(task_id, timeout=300)
        
        if success:
            print("\n✅ 所有测试通过!")
        else:
            print("\n❌ 部分测试失败!")
        
        return success
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

def test_sync_api():
    """同步API测试（用于快速验证）"""
    base_url = "http://localhost:8000"
    
    print("🔍 同步API测试")
    print("=" * 30)
    
    # 健康检查
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ 健康检查通过: {response.json()}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False
    
    # 获取平台列表
    try:
        response = requests.get(f"{base_url}/api/v1/platforms", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 获取平台列表成功: {data['platforms']}")
        else:
            print(f"❌ 获取平台列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 获取平台列表异常: {e}")
        return False
    
    print("✅ 同步API测试通过!")
    return True

async def main():
    """主函数"""
    print("MediaCrawler API 测试工具")
    print("=" * 40)
    
    # 首先进行同步测试
    if not test_sync_api():
        print("❌ 同步API测试失败，请检查服务是否启动")
        return
    
    # 然后进行异步完整测试
    tester = MediaCrawlerAPITester()
    try:
        await tester.run_full_test()
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main()) 