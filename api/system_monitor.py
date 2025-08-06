"""
系统监控API模块
提供系统状态监控、资源使用统计、性能分析等接口
"""

import asyncio
import psutil
import os
import time
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class SystemStats(BaseModel):
    """系统统计信息模型"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    crawler_processes: List[Dict[str, Any]]

def get_system_stats() -> SystemStats:
    """获取系统统计信息"""
    try:
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
        process_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                process_count += 1
                
                # 检查是否是爬虫相关进程
                cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
                if any(keyword in cmdline for keyword in ['main.py', 'crawler', 'xhs', 'dy', 'ks', 'bili', 'api_server']):
                    crawler_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                        'cmdline': ' '.join(proc_info.get('cmdline', [])[:3])
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return SystemStats(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            memory_total_gb=memory.total / (1024**3),
            disk_percent=disk.percent,
            disk_used_gb=disk.used / (1024**3),
            disk_total_gb=disk.total / (1024**3),
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            process_count=process_count,
            crawler_processes=crawler_processes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统统计信息失败: {str(e)}")

@router.get("/system/stats", response_model=SystemStats)
async def get_system_statistics():
    """获取系统统计信息"""
    return get_system_stats()

@router.get("/system/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        system_stats = get_system_stats()
        
        # 计算整体健康状态
        overall_status = "healthy"
        warnings = []
        
        # 检查系统资源
        if system_stats.cpu_percent > 80:
            overall_status = "warning"
            warnings.append("CPU使用率过高")
        
        if system_stats.memory_percent > 85:
            overall_status = "warning"
            warnings.append("内存使用率过高")
        
        if system_stats.disk_percent > 90:
            overall_status = "warning"
            warnings.append("磁盘使用率过高")
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "system_stats": system_stats.dict(),
            "warnings": warnings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统健康状态失败: {str(e)}")

@router.get("/system/processes")
async def get_crawler_processes():
    """获取爬虫进程信息"""
    try:
        system_stats = get_system_stats()
        return {
            "timestamp": datetime.now().isoformat(),
            "total_processes": system_stats.process_count,
            "crawler_processes": system_stats.crawler_processes,
            "crawler_process_count": len(system_stats.crawler_processes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程信息失败: {str(e)}")

@router.get("/system/resources")
async def get_resource_usage():
    """获取资源使用情况"""
    try:
        system_stats = get_system_stats()
        
        # 计算资源使用率
        memory_usage = {
            "percent": system_stats.memory_percent,
            "used_gb": system_stats.memory_used_gb,
            "total_gb": system_stats.memory_total_gb,
            "available_gb": system_stats.memory_total_gb - system_stats.memory_used_gb
        }
        
        disk_usage = {
            "percent": system_stats.disk_percent,
            "used_gb": system_stats.disk_used_gb,
            "total_gb": system_stats.disk_total_gb,
            "available_gb": system_stats.disk_total_gb - system_stats.disk_used_gb
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": system_stats.cpu_percent,
                "cores": psutil.cpu_count(),
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0
            },
            "memory": memory_usage,
            "disk": disk_usage,
            "network": {
                "bytes_sent": system_stats.network_bytes_sent,
                "bytes_recv": system_stats.network_bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资源使用情况失败: {str(e)}") 