#!/usr/bin/env python3
"""
系统监控脚本
实时监控MediaCrawler系统的性能和资源使用情况
"""

import asyncio
import time
import psutil
import os
import httpx
from datetime import datetime
import json

class SystemMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        
    def get_system_info(self):
        """获取系统信息"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络IO
            network = psutil.net_io_counters()
            
            # 进程信息
            process_memory = self.process.memory_info()
            process_cpu = self.process.cpu_percent()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_used_gb": memory.used / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_rss_mb": process_memory.rss / (1024**2),
                    "memory_vms_mb": process_memory.vms / (1024**2),
                    "num_threads": self.process.num_threads(),
                    "num_fds": self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
                    "create_time": self.process.create_time()
                }
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_api_health(self):
        """获取API健康状态"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 单平台爬虫健康状态
                try:
                    response = await client.get("http://localhost:8100/api/v1/crawler/health")
                    crawler_health = response.json() if response.status_code == 200 else {"error": f"HTTP {response.status_code}"}
                except Exception as e:
                    crawler_health = {"error": str(e)}
                
                # 多平台爬虫健康状态
                try:
                    response = await client.get("http://localhost:8100/api/v1/multi-platform/health")
                    multi_health = response.json() if response.status_code == 200 else {"error": f"HTTP {response.status_code}"}
                except Exception as e:
                    multi_health = {"error": str(e)}
                
                return {
                    "crawler_health": crawler_health,
                    "multi_platform_health": multi_health
                }
        except Exception as e:
            return {"error": str(e)}

    def format_size(self, bytes_size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"

    def print_status(self, system_info, api_health):
        """打印状态信息"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("🖥️  MediaCrawler 系统监控")
        print("=" * 80)
        print(f"📅 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  运行时间: {time.time() - self.start_time:.1f} 秒")
        print()
        
        # 系统信息
        if "error" not in system_info:
            sys = system_info["system"]
            proc = system_info["process"]
            
            print("📊 系统资源:")
            print(f"  CPU使用率: {sys['cpu_percent']:.1f}%")
            print(f"  内存使用率: {sys['memory_percent']:.1f}% ({self.format_size(sys['memory_used_gb'] * 1024**3)} / {self.format_size(sys['memory_available_gb'] * 1024**3)})")
            print(f"  磁盘使用率: {sys['disk_percent']:.1f}% (可用: {self.format_size(sys['disk_free_gb'] * 1024**3)})")
            print(f"  网络发送: {self.format_size(sys['network_bytes_sent'])}")
            print(f"  网络接收: {self.format_size(sys['network_bytes_recv'])}")
            print()
            
            print("🔧 进程信息:")
            print(f"  进程CPU: {proc['cpu_percent']:.1f}%")
            print(f"  进程内存: {self.format_size(proc['memory_rss_mb'] * 1024**2)} (RSS)")
            print(f"  虚拟内存: {self.format_size(proc['memory_vms_mb'] * 1024**2)} (VMS)")
            print(f"  线程数: {proc['num_threads']}")
            print(f"  文件描述符: {proc['num_fds']}")
            print()
        else:
            print(f"❌ 系统信息获取失败: {system_info['error']}")
            print()
        
        # API健康状态
        print("🌐 API健康状态:")
        if "error" not in api_health:
            crawler = api_health.get("crawler_health", {})
            multi = api_health.get("multi_platform_health", {})
            
            if "error" not in crawler:
                tasks = crawler.get("tasks", {})
                print(f"  单平台爬虫: ✅ 健康")
                print(f"    总任务数: {tasks.get('total', 0)}")
                print(f"    运行中: {tasks.get('running', 0)}")
                print(f"    已完成: {tasks.get('completed', 0)}")
                print(f"    失败: {tasks.get('failed', 0)}")
            else:
                print(f"  单平台爬虫: ❌ {crawler['error']}")
            
            if "error" not in multi:
                tasks = multi.get("tasks", {})
                print(f"  多平台爬虫: ✅ 健康")
                print(f"    总任务数: {tasks.get('total', 0)}")
                print(f"    运行中: {tasks.get('running', 0)}")
                print(f"    已完成: {tasks.get('completed', 0)}")
                print(f"    失败: {tasks.get('failed', 0)}")
            else:
                print(f"  多平台爬虫: ❌ {multi['error']}")
        else:
            print(f"❌ API健康检查失败: {api_health['error']}")
        
        print()
        print("=" * 80)
        print("💡 提示: 按 Ctrl+C 停止监控")
        print("=" * 80)

    async def monitor_loop(self, interval=5):
        """监控循环"""
        print("🚀 开始系统监控...")
        print("⏱️  监控间隔: {interval} 秒")
        print()
        
        try:
            while True:
                # 获取系统信息
                system_info = self.get_system_info()
                
                # 获取API健康状态
                api_health = await self.get_api_health()
                
                # 打印状态
                self.print_status(system_info, api_health)
                
                # 等待下次监控
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")

async def main():
    """主函数"""
    monitor = SystemMonitor()
    await monitor.monitor_loop(interval=5)

if __name__ == "__main__":
    asyncio.run(main()) 