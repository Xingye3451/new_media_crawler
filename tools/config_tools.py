# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:00
# @Desc    : 配置管理工具
import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config_manager import config_manager
from tools import utils


def show_config():
    """显示当前配置"""
    print("=== 当前配置信息 ===")
    
    # 代理配置
    proxy_config = config_manager.get_proxy_config()
    print("\n📡 代理配置:")
    print(f"  提供商: {proxy_config.provider_name}")
    print(f"  启用状态: {proxy_config.enabled}")
    print(f"  代理池大小: {proxy_config.pool_count}")
    print(f"  IP验证: {proxy_config.validate_ip}")
    
    if proxy_config.provider_name == "qingguo":
        print(f"  青果代理Key: {proxy_config.qingguo_key[:10]}..." if proxy_config.qingguo_key else "  青果代理Key: 未设置")
        print(f"  青果代理密码: {'已设置' if proxy_config.qingguo_pwd else '未设置'}")
    elif proxy_config.provider_name == "kuaidaili":
        print(f"  快代理Secret ID: {proxy_config.kuaidaili_secret_id[:10]}..." if proxy_config.kuaidaili_secret_id else "  快代理Secret ID: 未设置")
        print(f"  快代理用户名: {proxy_config.kuaidaili_user_name}")
    
    # 爬虫配置
    crawler_config = config_manager.get_crawler_config()
    print("\n🕷️ 爬虫配置:")
    print(f"  平台: {crawler_config.platform}")
    print(f"  关键词: {crawler_config.keywords}")
    print(f"  登录类型: {crawler_config.login_type}")
    print(f"  爬取类型: {crawler_config.crawler_type}")
    print(f"  最大爬取数量: {crawler_config.max_notes_count}")
    print(f"  爬取评论: {crawler_config.enable_comments}")
    print(f"  爬取图片: {crawler_config.enable_images}")
    print(f"  数据保存方式: {crawler_config.save_data_option}")
    print(f"  无头模式: {crawler_config.headless}")
    print(f"  最大并发数: {crawler_config.max_concurrency}")
    
    # 数据库配置
    database_config = config_manager.get_database_config()
    print("\n🗄️ 数据库配置:")
    print(f"  主机: {database_config.host}")
    print(f"  端口: {database_config.port}")
    print(f"  用户名: {database_config.username}")
    print(f"  数据库: {database_config.database}")
    print(f"  字符集: {database_config.charset}")
    
    # 应用配置
    app_config = config_manager.get_app_config()
    print("\n⚙️ 应用配置:")
    print(f"  调试模式: {app_config.debug}")
    print(f"  日志级别: {app_config.log_level}")
    print(f"  数据目录: {app_config.data_dir}")
    print(f"  用户数据目录: {app_config.user_data_dir}")


def export_config(env: str, format: str):
    """导出配置"""
    print(f"正在导出 {env} 环境的配置到 {format} 格式...")
    
    try:
        if format.lower() == "yaml":
            config_manager.export_to_yaml(env)
            print(f"✅ 配置已导出到 config/config_{env}.yaml")
        elif format.lower() == "json":
            config_manager.export_to_json(env)
            print(f"✅ 配置已导出到 config/config_{env}.json")
        else:
            print("❌ 不支持的格式，请使用 'yaml' 或 'json'")
    except Exception as e:
        print(f"❌ 导出配置失败: {e}")


def set_config(key: str, value: str):
    """设置配置值"""
    try:
        config_manager.set(key, value)
        print(f"✅ 配置已设置: {key} = {value}")
        print("💡 注意: 此设置仅在当前会话中有效，重启后需要重新设置")
    except Exception as e:
        print(f"❌ 设置配置失败: {e}")


def get_config(key: str):
    """获取配置值"""
    try:
        value = config_manager.get(key)
        print(f"📋 {key} = {value}")
    except Exception as e:
        print(f"❌ 获取配置失败: {e}")


def reload_config():
    """重新加载配置"""
    try:
        config_manager.reload()
        print("✅ 配置已重新加载")
    except Exception as e:
        print(f"❌ 重新加载配置失败: {e}")


def create_env_config(env: str):
    """创建环境配置文件"""
    print(f"正在创建 {env} 环境的配置文件...")
    
    try:
        # 导出YAML配置
        config_manager.export_to_yaml(env)
        print(f"✅ 已创建 config/config_{env}.yaml")
        
        # 导出JSON配置
        config_manager.export_to_json(env)
        print(f"✅ 已创建 config/config_{env}.json")
        
        print(f"\n💡 使用方法:")
        print(f"   export ENV={env}")
        print(f"   python main.py")
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="MediaCrawler 配置管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # show 命令
    subparsers.add_parser("show", help="显示当前配置")
    
    # export 命令
    export_parser = subparsers.add_parser("export", help="导出配置")
    export_parser.add_argument("env", help="环境名称 (development, production, test)")
    export_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="导出格式")
    
    # set 命令
    set_parser = subparsers.add_parser("set", help="设置配置值")
    set_parser.add_argument("key", help="配置键")
    set_parser.add_argument("value", help="配置值")
    
    # get 命令
    get_parser = subparsers.add_parser("get", help="获取配置值")
    get_parser.add_argument("key", help="配置键")
    
    # reload 命令
    subparsers.add_parser("reload", help="重新加载配置")
    
    # create 命令
    create_parser = subparsers.add_parser("create", help="创建环境配置文件")
    create_parser.add_argument("env", help="环境名称")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "show":
            show_config()
        elif args.command == "export":
            export_config(args.env, args.format)
        elif args.command == "set":
            set_config(args.key, args.value)
        elif args.command == "get":
            get_config(args.key)
        elif args.command == "reload":
            reload_config()
        elif args.command == "create":
            create_env_config(args.env)
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        utils.logger.error(f"配置工具执行失败: {e}")


if __name__ == "__main__":
    main() 