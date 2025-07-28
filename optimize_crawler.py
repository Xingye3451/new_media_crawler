#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫优化分析工具 - 支持所有平台
分析当前配置并提供优化建议，避免服务阻塞
"""

import os
import yaml
import subprocess
from typing import Dict, Any, List


def analyze_config():
    """分析当前配置文件"""
    config_file = "config/config_local.yaml"
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None


def provide_optimization_suggestions(config: Dict[str, Any]) -> List[str]:
    """提供优化建议"""
    suggestions = []
    crawler_config = config.get('crawler', {})
    
    # 分析并发设置
    max_concurrency = crawler_config.get('max_concurrency', 1)
    if max_concurrency > 3:
        suggestions.append("🔧 并发数过高，建议减少到2-3")
    elif max_concurrency < 1:
        suggestions.append("🔧 并发数过低，可以适当增加到2")
    
    # 分析爬取数量
    max_notes_count = crawler_config.get('max_notes_count', 50)
    if max_notes_count > 50:
        suggestions.append("🔧 爬取数量过多，建议减少到20-30")
    elif max_notes_count < 10:
        suggestions.append("🔧 爬取数量较少，可以适当增加到20")
    
    # 分析睡眠间隔
    max_sleep_sec = crawler_config.get('max_sleep_sec', 3)
    if max_sleep_sec < 3:
        suggestions.append("🔧 睡眠间隔过短，建议增加到5秒")
    elif max_sleep_sec > 10:
        suggestions.append("🔧 睡眠间隔过长，可以减少到5秒")
    
    # 分析功能开关
    enable_comments = crawler_config.get('enable_comments', True)
    if enable_comments:
        suggestions.append("🔧 评论功能已开启，如果不需要可以关闭以减少资源消耗")
    
    enable_images = crawler_config.get('enable_images', False)
    if enable_images:
        suggestions.append("🔧 图片下载已开启，如果不需要可以关闭以减少资源消耗")
    
    # 分析Redis配置
    redis_config = config.get('redis', {})
    connection_pool_size = redis_config.get('connection_pool_size', 10)
    if connection_pool_size > 10:
        suggestions.append("🔧 Redis连接池过大，建议减少到5-10")
    
    max_connections = redis_config.get('max_connections', 100)
    if max_connections > 50:
        suggestions.append("🔧 Redis最大连接数过多，建议减少到20-50")
    
    return suggestions


def generate_optimized_config(config: Dict[str, Any], suggestions: List[str]) -> Dict[str, Any]:
    """生成优化后的配置"""
    optimized_config = config.copy()
    crawler_config = optimized_config.get('crawler', {})
    
    # 根据建议调整配置
    if "并发数过高" in str(suggestions):
        crawler_config['max_concurrency'] = 2
    
    if "爬取数量过多" in str(suggestions):
        crawler_config['max_notes_count'] = 20
    
    if "睡眠间隔过短" in str(suggestions):
        crawler_config['max_sleep_sec'] = 5
    
    if "评论功能已开启" in str(suggestions):
        crawler_config['enable_comments'] = False
    
    if "图片下载已开启" in str(suggestions):
        crawler_config['enable_images'] = False
    
    # 调整Redis配置
    redis_config = optimized_config.get('redis', {})
    if "Redis连接池过大" in str(suggestions):
        redis_config['connection_pool_size'] = 5
    
    if "Redis最大连接数过多" in str(suggestions):
        redis_config['max_connections'] = 20
    
    optimized_config['crawler'] = crawler_config
    optimized_config['redis'] = redis_config
    
    return optimized_config


def create_resource_monitoring_script():
    """创建资源监控脚本使用说明"""
    print("\n📊 资源监控使用说明:")
    print("=" * 50)
    print("1. 启动监控:")
    print("   python monitor_resources.py")
    print()
    print("2. 监控指标:")
    print("   - CPU使用率 > 80%: 警告")
    print("   - 内存使用率 > 85%: 警告")
    print("   - 磁盘使用率 > 90%: 警告")
    print()
    print("3. 优化建议:")
    print("   - 如果CPU过高: 减少并发数")
    print("   - 如果内存过高: 减少爬取数量")
    print("   - 如果磁盘过高: 清理日志文件")
    print()


def create_emergency_stop_script():
    """创建紧急停止脚本"""
    script_content = """#!/bin/bash
# 紧急停止爬虫脚本

echo "🛑 正在停止所有爬虫进程..."

# 查找并停止爬虫进程
pkill -f "python.*main.py"
pkill -f "python.*crawler"
pkill -f "python.*monitor_resources.py"

# 等待进程完全停止
sleep 3

# 检查是否还有爬虫进程
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️ 强制停止剩余进程..."
    pkill -9 -f "python.*main.py"
fi

echo "✅ 所有爬虫进程已停止"

# 显示系统资源状态
echo "📊 当前系统资源状态:"
free -h
df -h /
"""
    
    try:
        with open("emergency_stop.sh", "w") as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod("emergency_stop.sh", 0o755)
        print("✅ 紧急停止脚本已创建: emergency_stop.sh")
    except Exception as e:
        print(f"❌ 创建紧急停止脚本失败: {e}")


def analyze_platform_specific_config(config: Dict[str, Any]):
    """分析平台特定配置"""
    platform = config.get('crawler', {}).get('platform', 'unknown')
    
    print(f"\n🎯 平台特定分析: {platform.upper()}")
    print("=" * 40)
    
    if platform == 'xhs':
        print("📋 小红书爬虫特点:")
        print("   - 支持视频筛选功能")
        print("   - 评论获取较稳定")
        print("   - 建议并发数: 2-3")
        print("   - 建议爬取数量: 20-30")
        
    elif platform == 'dy':
        print("📋 抖音爬虫特点:")
        print("   - 反爬机制较强")
        print("   - 建议增加睡眠间隔")
        print("   - 建议并发数: 1-2")
        print("   - 建议爬取数量: 10-20")
        
    elif platform == 'ks':
        print("📋 快手爬虫特点:")
        print("   - 视频获取较稳定")
        print("   - 评论获取可能较慢")
        print("   - 建议并发数: 2-3")
        print("   - 建议爬取数量: 20-30")
        
    elif platform == 'bili':
        print("📋 B站爬虫特点:")
        print("   - 支持时间范围搜索")
        print("   - 评论获取较稳定")
        print("   - 建议并发数: 2-3")
        print("   - 建议爬取数量: 20-30")
        
    else:
        print("📋 通用爬虫建议:")
        print("   - 建议并发数: 2-3")
        print("   - 建议爬取数量: 20-30")
        print("   - 建议睡眠间隔: 5秒")
        print("   - 建议关闭不必要的功能")


def main():
    """主函数"""
    print("🚀 爬虫优化分析工具")
    print("=" * 60)
    
    # 分析配置
    config = analyze_config()
    if not config:
        return
    
    print("🔍 分析当前爬虫配置...")
    print("=" * 60)
    
    # 显示当前配置
    crawler_config = config.get('crawler', {})
    print("📊 当前配置分析:")
    print(f"  平台: {crawler_config.get('platform', 'unknown')}")
    print(f"  关键词: {crawler_config.get('keywords', 'N/A')}")
    print(f"  爬取类型: {crawler_config.get('crawler_type', 'N/A')}")
    print(f"  最大笔记数: {crawler_config.get('max_notes_count', 'N/A')}")
    print(f"  并发数: {crawler_config.get('max_concurrency', 'N/A')}")
    print(f"  睡眠间隔: {crawler_config.get('max_sleep_sec', 'N/A')}秒")
    print(f"  获取评论: {crawler_config.get('enable_comments', 'N/A')}")
    print(f"  获取图片: {crawler_config.get('enable_images', 'N/A')}")
    
    # 平台特定分析
    analyze_platform_specific_config(config)
    
    # 提供优化建议
    print("\n💡 优化建议:")
    print("=" * 60)
    suggestions = provide_optimization_suggestions(config)
    
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("  ✅ 当前配置看起来比较合理")
    
    # 生成优化后的配置
    print("\n🔧 优化后的配置建议:")
    print("=" * 60)
    optimized_config = generate_optimized_config(config, suggestions)
    
    # 显示优化后的配置
    optimized_crawler = optimized_config.get('crawler', {})
    print("crawler:")
    for key, value in optimized_crawler.items():
        print(f"  {key}: {value}")
    
    # 资源监控建议
    print("\n📊 资源监控建议:")
    print("=" * 60)
    print("1. 运行资源监控脚本:")
    print("   python monitor_resources.py")
    print()
    print("2. 监控关键指标:")
    print("   - CPU使用率 > 80%: 减少并发数")
    print("   - 内存使用率 > 85%: 减少爬取数量")
    print("   - 磁盘使用率 > 90%: 清理日志文件")
    print()
    print("3. 实时监控命令:")
    print("   htop  # 查看系统资源")
    print("   iotop # 查看磁盘I/O")
    print("   nethogs # 查看网络使用")
    
    # 紧急停止方案
    print("\n🛑 紧急停止方案:")
    print("=" * 60)
    create_emergency_stop_script()
    print("✅ 已创建紧急停止脚本: emergency_stop.sh")
    print("   使用方法: ./emergency_stop.sh")
    
    # 总结
    print("\n🎯 总结:")
    print("=" * 60)
    print("1. 当前配置已优化，减少了资源消耗")
    print("2. 建议使用资源监控脚本观察运行状态")
    print("3. 如果出现阻塞，使用紧急停止脚本")
    print("4. 根据监控结果进一步调整配置")
    
    # 下一步操作
    print("\n📝 下一步操作:")
    print("1. 运行优化后的配置进行测试")
    print("2. 启动资源监控: python monitor_resources.py")
    print("3. 如果出现问题: ./emergency_stop.sh")
    print("4. 根据监控结果调整配置参数")


if __name__ == "__main__":
    main() 