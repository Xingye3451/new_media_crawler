#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler 快速启动脚本
提供命令行接口快速启动各种爬虫任务
"""

import argparse
import asyncio
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

class QuickCrawlerStarter:
    """快速爬虫启动器"""
    
    def __init__(self, api_base: str = "http://localhost:8100"):
        self.api_base = api_base
        
    def log(self, message: str, level: str = "INFO"):
        """日志记录"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def check_api_health(self) -> bool:
        """检查API服务"""
        try:
            response = requests.get(f"{self.api_base}/api/v1/health", timeout=10)
            if response.status_code == 200:
                self.log("API服务运行正常", "SUCCESS")
                return True
            else:
                self.log(f"API服务异常: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"API服务连接失败: {e}", "ERROR")
            return False
    
    def start_single_platform_task(self, platform: str, keywords: str, 
                                 max_count: int = 20, 
                                 crawler_type: str = "search",
                                 save_format: str = "db",
                                 enable_comments: bool = True,
                                 account_id: Optional[int] = None) -> Optional[str]:
        """启动单平台任务"""
        
        request_data = {
            "platform": platform,
            "keywords": keywords,
            "max_notes_count": max_count,
            "login_type": "qrcode",
            "crawler_type": crawler_type,
            "get_comments": enable_comments,
            "save_data_option": save_format,
            "use_proxy": False,
            "proxy_strategy": "disabled"
        }
        
        if account_id:
            request_data["account_id"] = account_id
        
        try:
            self.log(f"启动 {platform} 平台任务，关键词: {keywords}")
            
            response = requests.post(
                f"{self.api_base}/api/v1/crawler/start",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                self.log(f"任务启动成功！任务ID: {task_id}", "SUCCESS")
                return task_id
            else:
                self.log(f"任务启动失败: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"启动任务时出错: {e}", "ERROR")
            return None
    
    def start_multi_platform_task(self, platforms: List[str], keywords: str,
                                max_count: int = 20,
                                save_format: str = "db",
                                enable_comments: bool = True) -> Optional[str]:
        """启动多平台任务"""
        
        request_data = {
            "platforms": platforms,
            "keywords": keywords,
            "max_count_per_platform": max_count,
            "enable_comments": enable_comments,
            "enable_images": False,
            "save_format": save_format,
            "use_proxy": False,
            "proxy_strategy": "disabled"
        }
        
        try:
            self.log(f"启动多平台任务，平台: {', '.join(platforms)}，关键词: {keywords}")
            
            response = requests.post(
                f"{self.api_base}/api/v1/multi-platform/start",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                self.log(f"多平台任务启动成功！任务ID: {task_id}", "SUCCESS")
                return task_id
            else:
                self.log(f"多平台任务启动失败: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"启动多平台任务时出错: {e}", "ERROR")
            return None
    
    async def monitor_task(self, task_id: str, is_multi_platform: bool = False) -> Dict[str, Any]:
        """监控任务状态"""
        
        if is_multi_platform:
            status_url = f"{self.api_base}/api/v1/multi-platform/status/{task_id}"
        else:
            status_url = f"{self.api_base}/api/v1/crawler/status/{task_id}"
        
        start_time = time.time()
        
        while True:
            try:
                response = requests.get(status_url, timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get("status", "unknown")
                    
                    if status == "completed":
                        duration = time.time() - start_time
                        self.log(f"任务完成！耗时: {duration:.1f}秒", "SUCCESS")
                        return {"success": True, "duration": duration, "result": status_data}
                    elif status == "failed":
                        error_msg = status_data.get("error", "未知错误")
                        self.log(f"任务失败: {error_msg}", "ERROR")
                        return {"success": False, "error": error_msg}
                    elif status == "running":
                        progress = status_data.get("progress", 0)
                        if is_multi_platform:
                            # 多平台任务的进度显示
                            prog_data = status_data.get("progress", {})
                            completed = prog_data.get("completed", 0)
                            total = prog_data.get("total", 0)
                            self.log(f"任务运行中... 进度: {completed}/{total}")
                        else:
                            # 单平台任务的进度显示
                            self.log(f"任务运行中... 进度: {progress*100:.1f}%")
                    else:
                        self.log(f"任务状态: {status}")
                    
                    await asyncio.sleep(10)  # 每10秒检查一次
                else:
                    self.log(f"查询任务状态失败: {response.status_code}", "WARNING")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                self.log(f"监控任务时出错: {e}", "WARNING")
                await asyncio.sleep(5)
    
    def get_task_list(self) -> List[Dict]:
        """获取任务列表"""
        try:
            response = requests.get(f"{self.api_base}/api/v1/crawler/tasks", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            self.log(f"获取任务列表失败: {e}", "ERROR")
            return []
    
    def show_task_status(self):
        """显示任务状态"""
        tasks = self.get_task_list()
        
        if not tasks:
            self.log("没有找到任务")
            return
        
        print("\n📋 任务状态列表:")
        print("-" * 80)
        
        for task in tasks:
            task_id = task.get('task_id', 'unknown')[:8]
            status = task.get('status', 'unknown')
            platform = task.get('request_params', {}).get('platform', 'unknown')
            keywords = task.get('request_params', {}).get('keywords', 'unknown')
            progress = task.get('progress', 0)
            created_at = task.get('created_at', '')
            
            emoji = {
                'pending': '⏳',
                'running': '🏃',
                'completed': '✅',
                'failed': '❌'
            }.get(status, '❓')
            
            print(f"{emoji} [{task_id}] {platform} - {keywords} - {status} ({progress*100:.1f}%) - {created_at}")
    
    def run_interactive_mode(self):
        """运行交互模式"""
        print("🚀 MediaCrawler 交互式启动器")
        print("=" * 50)
        
        while True:
            print("\n请选择操作:")
            print("1. 启动单平台任务")
            print("2. 启动多平台任务") 
            print("3. 查看任务状态")
            print("4. 监控任务")
            print("5. 退出")
            
            choice = input("\n请输入选择 (1-5): ").strip()
            
            if choice == "1":
                self._interactive_single_platform()
            elif choice == "2":
                self._interactive_multi_platform()
            elif choice == "3":
                self.show_task_status()
            elif choice == "4":
                self._interactive_monitor()
            elif choice == "5":
                print("👋 退出")
                break
            else:
                print("❌ 无效选择，请重新输入")
    
    def _interactive_single_platform(self):
        """交互式单平台任务创建"""
        print("\n📱 单平台任务配置:")
        
        # 平台选择
        platforms = ["xhs", "dy", "ks", "bili"]
        print(f"支持的平台: {', '.join(platforms)}")
        platform = input("请选择平台: ").strip()
        
        if platform not in platforms:
            print("❌ 无效平台")
            return
        
        # 关键词
        keywords = input("请输入关键词: ").strip()
        if not keywords:
            print("❌ 关键词不能为空")
            return
        
        # 数量
        try:
            max_count = int(input("请输入抓取数量 (默认20): ") or "20")
        except ValueError:
            max_count = 20
        
        # 保存格式（固定为数据库）
        save_format = "db"
        print("保存格式: 数据库 (默认)")
        
        # 是否抓取评论
        enable_comments = input("是否抓取评论 (y/n，默认y): ").strip().lower() != "n"
        
        # 启动任务
        task_id = self.start_single_platform_task(
            platform=platform,
            keywords=keywords,
            max_count=max_count,
            save_format=save_format,
            enable_comments=enable_comments
        )
        
        if task_id:
            # 询问是否监控
            if input("是否监控任务进度 (y/n): ").strip().lower() == "y":
                asyncio.run(self.monitor_task(task_id))
    
    def _interactive_multi_platform(self):
        """交互式多平台任务创建"""
        print("\n🌐 多平台任务配置:")
        
        # 平台选择
        available_platforms = ["xhs", "dy", "ks", "bili"]
        print(f"支持的平台: {', '.join(available_platforms)}")
        platform_input = input("请选择平台 (逗号分隔): ").strip()
        
        platforms = [p.strip() for p in platform_input.split(",") if p.strip() in available_platforms]
        
        if not platforms:
            print("❌ 没有选择有效平台")
            return
        
        # 关键词
        keywords = input("请输入关键词: ").strip()
        if not keywords:
            print("❌ 关键词不能为空")
            return
        
        # 数量
        try:
            max_count = int(input("请输入每个平台抓取数量 (默认20): ") or "20")
        except ValueError:
            max_count = 20
        
        # 保存格式（固定为数据库）
        save_format = "db"
        print("保存格式: 数据库 (默认)")
        
        # 是否抓取评论
        enable_comments = input("是否抓取评论 (y/n，默认y): ").strip().lower() != "n"
        
        # 启动任务
        task_id = self.start_multi_platform_task(
            platforms=platforms,
            keywords=keywords,
            max_count=max_count,
            save_format=save_format,
            enable_comments=enable_comments
        )
        
        if task_id:
            # 询问是否监控
            if input("是否监控任务进度 (y/n): ").strip().lower() == "y":
                asyncio.run(self.monitor_task(task_id, is_multi_platform=True))
    
    def _interactive_monitor(self):
        """交互式任务监控"""
        print("\n🔍 任务监控:")
        
        # 显示任务列表
        tasks = self.get_task_list()
        if not tasks:
            print("❌ 没有找到任务")
            return
        
        print("当前任务列表:")
        for i, task in enumerate(tasks[-10:], 1):  # 显示最近10个任务
            task_id = task.get('task_id', 'unknown')[:8]
            status = task.get('status', 'unknown')
            platform = task.get('request_params', {}).get('platform', 'unknown')
            print(f"{i}. [{task_id}] {platform} - {status}")
        
        try:
            choice = int(input("\n请选择要监控的任务序号: ")) - 1
            if 0 <= choice < len(tasks[-10:]):
                task = tasks[-10:][choice]
                task_id = task.get('task_id')
                asyncio.run(self.monitor_task(task_id))
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入数字")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MediaCrawler 快速启动器")
    parser.add_argument("--api-base", default="http://localhost:8100", 
                       help="API服务地址")
    parser.add_argument("--platform", choices=["xhs", "dy", "ks", "bili"], 
                       help="平台选择")
    parser.add_argument("--keywords", help="搜索关键词")
    parser.add_argument("--count", type=int, default=20, help="抓取数量")
    parser.add_argument("--format", choices=["db"], default="db", 
                       help="保存格式（仅数据库）")
    parser.add_argument("--no-comments", action="store_true", help="不抓取评论")
    parser.add_argument("--multi-platform", nargs="+", choices=["xhs", "dy", "ks", "bili"],
                       help="多平台抓取")
    parser.add_argument("--monitor", help="监控指定任务ID")
    parser.add_argument("--status", action="store_true", help="显示任务状态")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    starter = QuickCrawlerStarter(args.api_base)
    
    # 检查API服务
    if not starter.check_api_health():
        return
    
    # 交互模式
    if args.interactive:
        starter.run_interactive_mode()
        return
    
    # 显示任务状态
    if args.status:
        starter.show_task_status()
        return
    
    # 监控任务
    if args.monitor:
        asyncio.run(starter.monitor_task(args.monitor))
        return
    
    # 多平台任务
    if args.multi_platform:
        if not args.keywords:
            print("❌ 多平台任务需要指定关键词")
            return
        
        task_id = starter.start_multi_platform_task(
            platforms=args.multi_platform,
            keywords=args.keywords,
            max_count=args.count,
            save_format=args.format,
            enable_comments=not args.no_comments
        )
        
        if task_id:
            asyncio.run(starter.monitor_task(task_id, is_multi_platform=True))
        return
    
    # 单平台任务
    if args.platform and args.keywords:
        task_id = starter.start_single_platform_task(
            platform=args.platform,
            keywords=args.keywords,
            max_count=args.count,
            save_format=args.format,
            enable_comments=not args.no_comments
        )
        
        if task_id:
            asyncio.run(starter.monitor_task(task_id))
        return
    
    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main() 