# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代理管理工具脚本
提供命令行工具来管理代理池
"""

import asyncio
import json
import sys
import time
from typing import List, Dict, Any
import argparse

import db
from proxy_manager import ProxyManager, ProxyInfo


class ProxyTools:
    def __init__(self):
        self.proxy_manager = ProxyManager()
    
    async def init_db(self):
        """初始化数据库"""
        await db.init_db()
    
    async def add_proxy_from_file(self, file_path: str):
        """从文件导入代理"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    proxies = json.load(f)
                else:
                    # 假设是文本文件，每行一个代理
                    proxies = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 解析格式: type://ip:port 或 type://user:pass@ip:port
                            parts = line.split('://')
                            if len(parts) == 2:
                                proxy_type = parts[0]
                                rest = parts[1]
                                
                                if '@' in rest:
                                    auth, addr = rest.split('@')
                                    username, password = auth.split(':')
                                    ip, port = addr.split(':')
                                else:
                                    username = password = None
                                    ip, port = rest.split(':')
                                
                                proxies.append({
                                    "proxy_type": proxy_type,
                                    "ip": ip,
                                    "port": int(port),
                                    "username": username,
                                    "password": password
                                })
            
            success_count = 0
            for proxy_data in proxies:
                try:
                    await self.proxy_manager.add_proxy(proxy_data)
                    success_count += 1
                    print(f"✅ 添加代理: {proxy_data['ip']}:{proxy_data['port']}")
                except Exception as e:
                    print(f"❌ 添加代理失败: {proxy_data['ip']}:{proxy_data['port']} - {e}")
            
            print(f"\n📊 导入完成: 成功 {success_count}/{len(proxies)} 个代理")
            
        except Exception as e:
            print(f"❌ 导入失败: {e}")
    
    async def check_all_proxies(self):
        """检测所有代理"""
        print("🔍 开始检测所有代理...")
        
        # 获取所有代理
        rows = await self.proxy_manager.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1"
        )
        
        if not rows:
            print("❌ 没有找到代理")
            return
        
        total = len(rows)
        available = 0
        
        for i, row in enumerate(rows, 1):
            proxy_info = ProxyInfo(**row)
            print(f"[{i}/{total}] 检测代理: {proxy_info.ip}:{proxy_info.port}")
            
            is_available = await self.proxy_manager.check_proxy(proxy_info)
            
            if is_available:
                available += 1
                print(f"  ✅ 可用")
            else:
                print(f"  ❌ 不可用")
            
            # 避免检测过于频繁
            await asyncio.sleep(1)
        
        print(f"\n📊 检测完成: {available}/{total} 个代理可用")
    
    async def show_proxy_stats(self):
        """显示代理统计信息"""
        stats = await self.proxy_manager.get_proxy_stats()
        
        print("📊 代理池统计信息")
        print("=" * 40)
        print(f"总代理数: {stats['total']}")
        print(f"启用代理: {stats['active']}")
        print(f"可用代理: {stats['available']}")
        print(f"平均速度: {stats['avg_speed']}ms")
        print(f"平均在线率: {stats['avg_uptime']}%")
        
        if stats['total'] > 0:
            availability_rate = round(stats['available'] / stats['total'] * 100, 2)
            print(f"可用率: {availability_rate}%")
    
    async def list_proxies(self, limit: int = 20):
        """列出代理"""
        rows = await self.proxy_manager.db.query(
            "SELECT * FROM proxy_pool ORDER BY priority DESC, speed ASC LIMIT %s",
            limit
        )
        
        if not rows:
            print("❌ 没有找到代理")
            return
        
        print(f"📋 代理列表 (显示前 {limit} 个)")
        print("=" * 80)
        print(f"{'ID':<4} {'类型':<6} {'IP':<16} {'端口':<6} {'国家':<8} {'速度':<8} {'匿名度':<10} {'状态':<6}")
        print("-" * 80)
        
        for row in rows:
            proxy_info = ProxyInfo(**row)
            status = "✅" if proxy_info.last_check_result else "❌"
            print(f"{proxy_info.id:<4} {proxy_info.proxy_type:<6} {proxy_info.ip:<16} "
                  f"{proxy_info.port:<6} {proxy_info.country or 'N/A':<8} "
                  f"{proxy_info.speed or 'N/A':<8} {proxy_info.anonymity or 'N/A':<10} {status:<6}")
    
    async def test_strategies(self):
        """测试所有策略"""
        print("🧪 测试代理策略")
        print("=" * 40)
        
        strategies = ["round_robin", "random", "weighted", "failover", "geo_based", "smart"]
        
        for strategy in strategies:
            print(f"\n测试策略: {strategy}")
            try:
                proxy_info = await self.proxy_manager.get_proxy(strategy)
                if proxy_info:
                    print(f"  ✅ 获取成功: {proxy_info.ip}:{proxy_info.port}")
                else:
                    print(f"  ❌ 没有可用代理")
            except Exception as e:
                print(f"  ❌ 策略失败: {e}")
    
    async def cleanup_failed_proxies(self, max_fail_count: int = 5):
        """清理失败次数过多的代理"""
        print(f"🧹 清理失败次数超过 {max_fail_count} 次的代理...")
        
        # 查找失败次数过多的代理
        rows = await self.proxy_manager.db.query(
            "SELECT * FROM proxy_pool WHERE fail_count >= %s",
            max_fail_count
        )
        
        if not rows:
            print("✅ 没有需要清理的代理")
            return
        
        print(f"找到 {len(rows)} 个需要清理的代理:")
        
        for row in rows:
            proxy_info = ProxyInfo(**row)
            print(f"  - {proxy_info.ip}:{proxy_info.port} (失败 {proxy_info.fail_count} 次)")
        
        # 确认删除
        confirm = input("\n确认删除这些代理? (y/N): ")
        if confirm.lower() == 'y':
            deleted_count = 0
            for row in rows:
                proxy_info = ProxyInfo(**row)
                try:
                    await self.proxy_manager.delete_proxy(proxy_info.id)
                    deleted_count += 1
                    print(f"  ✅ 删除: {proxy_info.ip}:{proxy_info.port}")
                except Exception as e:
                    print(f"  ❌ 删除失败: {proxy_info.ip}:{proxy_info.port} - {e}")
            
            print(f"\n📊 清理完成: 删除了 {deleted_count} 个代理")
        else:
            print("❌ 取消清理")


async def main():
    parser = argparse.ArgumentParser(description="代理管理工具")
    parser.add_argument("command", choices=[
        "import", "check", "stats", "list", "test", "cleanup"
    ], help="命令")
    parser.add_argument("--file", help="代理文件路径 (用于import命令)")
    parser.add_argument("--limit", type=int, default=20, help="显示数量限制 (用于list命令)")
    parser.add_argument("--max-fail", type=int, default=5, help="最大失败次数 (用于cleanup命令)")
    
    args = parser.parse_args()
    
    tools = ProxyTools()
    
    try:
        await tools.init_db()
        
        if args.command == "import":
            if not args.file:
                print("❌ 请指定代理文件路径 (--file)")
                return
            await tools.add_proxy_from_file(args.file)
        
        elif args.command == "check":
            await tools.check_all_proxies()
        
        elif args.command == "stats":
            await tools.show_proxy_stats()
        
        elif args.command == "list":
            await tools.list_proxies(args.limit)
        
        elif args.command == "test":
            await tools.test_strategies()
        
        elif args.command == "cleanup":
            await tools.cleanup_failed_proxies(args.max_fail)
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main()) 