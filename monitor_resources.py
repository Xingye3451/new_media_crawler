#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源监控脚本 - 监控所有平台爬虫的系统资源使用情况
"""

import asyncio
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any

try:
    import psutil
except ImportError:
    print("❌ 缺少依赖包: psutil")
    print("请运行: pip install psutil")
    sys.exit(1)


class ResourceMonitor:
    def __init__(self, log_file: str = "resource_monitor.log"):
        self.log_file = log_file
        self.running = False
        self.monitor_interval = 5  # 监控间隔（秒）
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器，优雅关闭监控"""
        print(f"\n🛑 收到信号 {signum}，正在停止监控...")
        self.running = False
    
    async def start_monitoring(self):
        """开始监控"""
        self.running = True
        print("🚀 开始监控系统资源...")
        print(f"📝 日志文件: {self.log_file}")
        print("⏱️  监控间隔: 5秒")
        print("🛑 按 Ctrl+C 停止监控")
        print("=" * 60)
        
        while self.running:
            try:
                stats = self._get_system_stats()
                self._log_stats(stats)
                warning_level = self.get_warning_level(stats)
                
                if warning_level == "high":
                    print(f"🚨 警告: {stats['timestamp']} - 系统资源使用率过高!")
                elif warning_level == "medium":
                    print(f"⚠️  注意: {stats['timestamp']} - 系统资源使用率较高")
                
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                print(f"❌ 监控过程中出现错误: {e}")
                await asyncio.sleep(self.monitor_interval)
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        print("\n✅ 资源监控已停止")
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 网络I/O
        network = psutil.net_io_counters()
        
        # 进程信息 - 查找爬虫相关进程
        crawler_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                # 检查是否是爬虫相关进程
                if any(keyword in str(proc_info.get('cmdline', '')).lower() 
                       for keyword in ['main.py', 'crawler', 'xhs', 'dy', 'ks', 'bili']):
                    crawler_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                        'cmdline': ' '.join(proc_info.get('cmdline', [])[:3])  # 只显示前3个参数
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'memory_total_gb': memory.total / (1024**3),
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024**3),
            'disk_total_gb': disk.total / (1024**3),
            'network_bytes_sent': network.bytes_sent,
            'network_bytes_recv': network.bytes_recv,
            'crawler_processes': crawler_processes
        }
    
    def _log_stats(self, stats: Dict[str, Any]):
        """记录统计信息"""
        # 控制台输出
        print(f"📊 {stats['timestamp']}")
        print(f"   CPU: {stats['cpu_percent']:5.1f}% | "
              f"内存: {stats['memory_percent']:5.1f}% ({stats['memory_used_gb']:.1f}GB/{stats['memory_total_gb']:.1f}GB) | "
              f"磁盘: {stats['disk_percent']:5.1f}% ({stats['disk_used_gb']:.1f}GB/{stats['disk_total_gb']:.1f}GB)")
        
        if stats['crawler_processes']:
            print(f"   🕷️  爬虫进程: {len(stats['crawler_processes'])} 个")
            for proc in stats['crawler_processes'][:3]:  # 只显示前3个
                print(f"      PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, 内存: {proc['memory_percent']:.1f}%)")
        
        # 文件记录
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{stats['timestamp']},{stats['cpu_percent']:.1f},{stats['memory_percent']:.1f},"
                       f"{stats['memory_used_gb']:.2f},{stats['disk_percent']:.1f},{stats['disk_used_gb']:.2f},"
                       f"{len(stats['crawler_processes'])}\n")
        except Exception as e:
            print(f"❌ 写入日志文件失败: {e}")
    
    def get_warning_level(self, stats: Dict[str, Any]) -> str:
        """获取警告级别"""
        if (stats['cpu_percent'] > 80 or 
            stats['memory_percent'] > 85 or 
            stats['disk_percent'] > 90):
            return "high"
        elif (stats['cpu_percent'] > 60 or 
              stats['memory_percent'] > 70 or 
              stats['disk_percent'] > 80):
            return "medium"
        return "normal"
    
    def get_recommendations(self, stats: Dict[str, Any]) -> list:
        """获取优化建议"""
        recommendations = []
        
        if stats['cpu_percent'] > 80:
            recommendations.append("🔧 CPU使用率过高，建议减少并发数或暂停部分爬虫")
        
        if stats['memory_percent'] > 85:
            recommendations.append("🔧 内存使用率过高，建议减少爬取数量或重启爬虫")
        
        if stats['disk_percent'] > 90:
            recommendations.append("🔧 磁盘使用率过高，建议清理日志文件或增加磁盘空间")
        
        if len(stats['crawler_processes']) > 5:
            recommendations.append("🔧 爬虫进程过多，建议检查是否有僵尸进程")
        
        return recommendations


async def main():
    """主函数"""
    print("🕷️  爬虫资源监控工具")
    print("=" * 60)
    
    # 创建监控器
    monitor = ResourceMonitor()
    
    try:
        # 开始监控
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 用户中断监控")
    except Exception as e:
        print(f"❌ 监控过程中出现错误: {e}")
    finally:
        monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main()) 