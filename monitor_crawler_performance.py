#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler 性能监控工具
实时监控爬虫任务状态、资源使用情况和数据产出
"""

import asyncio
import requests
import time
import json
import psutil
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict, deque

class CrawlerPerformanceMonitor:
    """爬虫性能监控器"""
    
    def __init__(self, api_base: str = "http://localhost:8100"):
        self.api_base = api_base
        self.monitoring = False
        self.task_stats = defaultdict(dict)
        self.system_stats = deque(maxlen=60)  # 保存最近60次的系统状态
        self.data_stats = defaultdict(int)
        
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统资源信息"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 获取Python进程信息
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / 1024 / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "process_memory_mb": process_memory,
                "process_cpu_percent": process.cpu_percent()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_api_tasks(self) -> List[Dict]:
        """获取API任务列表"""
        try:
            response = requests.get(f"{self.api_base}/api/v1/crawler/tasks", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"获取任务列表失败: {e}")
            return []
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取单个任务状态"""
        try:
            response = requests.get(f"{self.api_base}/api/v1/crawler/status/{task_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            return {"error": str(e)}
    
    def check_data_directory(self) -> Dict[str, Any]:
        """检查数据目录"""
        data_dir = "./data"
        if not os.path.exists(data_dir):
            return {"error": "数据目录不存在"}
        
        try:
            files = os.listdir(data_dir)
            json_files = [f for f in files if f.endswith('.json')]
            csv_files = [f for f in files if f.endswith('.csv')]
            
            total_size = 0
            file_count = 0
            latest_time = 0
            
            for file in files:
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    total_size += stat.st_size
                    file_count += 1
                    latest_time = max(latest_time, stat.st_mtime)
            
            return {
                "total_files": file_count,
                "json_files": len(json_files),
                "csv_files": len(csv_files),
                "total_size_mb": total_size / 1024 / 1024,
                "latest_modified": datetime.fromtimestamp(latest_time).isoformat() if latest_time > 0 else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def print_dashboard(self):
        """打印监控面板"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🖥️  MediaCrawler 性能监控面板")
        print("=" * 80)
        print(f"📅 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 系统资源信息
        if self.system_stats:
            latest_system = self.system_stats[-1]
            print("🖥️  系统资源状态:")
            print(f"  CPU使用率: {latest_system.get('cpu_percent', 0):.1f}%")
            print(f"  内存使用率: {latest_system.get('memory_percent', 0):.1f}%")
            print(f"  可用内存: {latest_system.get('memory_available_gb', 0):.1f}GB")
            print(f"  磁盘使用率: {latest_system.get('disk_percent', 0):.1f}%")
            print(f"  可用磁盘: {latest_system.get('disk_free_gb', 0):.1f}GB")
            print(f"  进程内存: {latest_system.get('process_memory_mb', 0):.1f}MB")
            print()
        
        # API任务状态
        tasks = self.get_api_tasks()
        print(f"📊 API任务状态 (共{len(tasks)}个任务):")
        
        status_count = defaultdict(int)
        for task in tasks:
            status = task.get('status', 'unknown')
            status_count[status] += 1
        
        for status, count in status_count.items():
            emoji = {
                'pending': '⏳',
                'running': '🏃',
                'completed': '✅',
                'failed': '❌',
                'unknown': '❓'
            }.get(status, '❓')
            print(f"  {emoji} {status}: {count}")
        
        # 显示最近的5个任务
        if tasks:
            print("\n📋 最近任务:")
            for task in tasks[-5:]:
                task_id = task.get('task_id', 'unknown')[:8]
                status = task.get('status', 'unknown')
                platform = task.get('request_params', {}).get('platform', 'unknown')
                progress = task.get('progress', 0)
                
                emoji = {
                    'pending': '⏳',
                    'running': '🏃',
                    'completed': '✅',
                    'failed': '❌'
                }.get(status, '❓')
                
                print(f"  {emoji} [{task_id}] {platform} - {status} ({progress*100:.1f}%)")
        
        print()
        
        # 数据目录信息
        data_info = self.check_data_directory()
        print("📁 数据目录状态:")
        if "error" not in data_info:
            print(f"  总文件数: {data_info['total_files']}")
            print(f"  JSON文件: {data_info['json_files']}")
            print(f"  CSV文件: {data_info['csv_files']}")
            print(f"  总大小: {data_info['total_size_mb']:.1f}MB")
            if data_info['latest_modified']:
                print(f"  最新修改: {data_info['latest_modified']}")
        else:
            print(f"  ❌ {data_info['error']}")
        
        print()
        print("🔄 按 Ctrl+C 停止监控")
        print("=" * 80)
    
    async def start_monitoring(self, interval: int = 5):
        """开始监控"""
        self.monitoring = True
        print("🚀 开始性能监控...")
        
        try:
            while self.monitoring:
                # 收集系统信息
                system_info = self.get_system_info()
                if "error" not in system_info:
                    self.system_stats.append(system_info)
                
                # 打印监控面板
                self.print_dashboard()
                
                # 等待指定间隔
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
            self.monitoring = False
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")
            self.monitoring = False
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        if not self.system_stats:
            return {"error": "没有收集到系统数据"}
        
        # 计算系统资源统计
        cpu_values = [s.get('cpu_percent', 0) for s in self.system_stats]
        memory_values = [s.get('memory_percent', 0) for s in self.system_stats]
        
        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        cpu_max = max(cpu_values) if cpu_values else 0
        
        memory_avg = sum(memory_values) / len(memory_values) if memory_values else 0
        memory_max = max(memory_values) if memory_values else 0
        
        # 获取任务信息
        tasks = self.get_api_tasks()
        task_status_count = defaultdict(int)
        for task in tasks:
            status = task.get('status', 'unknown')
            task_status_count[status] += 1
        
        # 获取数据目录信息
        data_info = self.check_data_directory()
        
        report = {
            "生成时间": datetime.now().isoformat(),
            "监控时长": len(self.system_stats) * 5,  # 每5秒一次
            "系统性能": {
                "CPU平均使用率": f"{cpu_avg:.1f}%",
                "CPU最高使用率": f"{cpu_max:.1f}%",
                "内存平均使用率": f"{memory_avg:.1f}%",
                "内存最高使用率": f"{memory_max:.1f}%"
            },
            "任务统计": dict(task_status_count),
            "数据产出": data_info
        }
        
        return report
    
    def save_performance_report(self):
        """保存性能报告"""
        report = self.generate_performance_report()
        
        filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"📄 性能报告已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")


async def main():
    """主函数"""
    print("🔧 MediaCrawler 性能监控工具")
    print("=" * 60)
    
    monitor = CrawlerPerformanceMonitor()
    
    try:
        await monitor.start_monitoring(interval=5)
    except KeyboardInterrupt:
        print("\n🛑 监控已停止")
    finally:
        # 保存性能报告
        monitor.save_performance_report()


if __name__ == "__main__":
    asyncio.run(main()) 