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
# @Desc    : 配置管理器测试脚本
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config_manager import ConfigManager, ProxyConfig, CrawlerConfig, DatabaseConfig, AppConfig


def test_config_manager():
    """测试配置管理器"""
    print("=== 配置管理器测试开始 ===")
    
    # 创建临时配置目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 使用临时目录: {temp_dir}")
        
        # 创建配置管理器
        config_manager = ConfigManager(temp_dir)
        
        # 测试1: 默认配置
        print("\n🧪 测试1: 默认配置")
        proxy_config = config_manager.get_proxy_config()
        crawler_config = config_manager.get_crawler_config()
        database_config = config_manager.get_database_config()
        app_config = config_manager.get_app_config()
        
        print(f"  代理提供商: {proxy_config.provider_name}")
        print(f"  代理启用: {proxy_config.enabled}")
        print(f"  爬虫平台: {crawler_config.platform}")
        print(f"  数据库主机: {database_config.host}")
        print(f"  应用调试模式: {app_config.debug}")
        
        # 测试2: 设置配置值
        print("\n🧪 测试2: 设置配置值")
        config_manager.set("proxy.provider_name", "qingguo")
        config_manager.set("proxy.enabled", True)
        config_manager.set("crawler.platform", "dy")
        config_manager.set("crawler.max_notes_count", 100)
        
        # 重新初始化配置对象
        config_manager._init_config_objects()
        
        proxy_config = config_manager.get_proxy_config()
        crawler_config = config_manager.get_crawler_config()
        
        print(f"  代理提供商: {proxy_config.provider_name}")
        print(f"  代理启用: {proxy_config.enabled}")
        print(f"  爬虫平台: {crawler_config.platform}")
        print(f"  最大爬取数量: {crawler_config.max_notes_count}")
        
        # 测试3: 导出配置
        print("\n🧪 测试3: 导出配置")
        config_manager.export_to_yaml("test")
        config_manager.export_to_json("test")
        
        yaml_file = Path(temp_dir) / "config_test.yaml"
        json_file = Path(temp_dir) / "config_test.json"
        
        print(f"  YAML文件存在: {yaml_file.exists()}")
        print(f"  JSON文件存在: {json_file.exists()}")
        
        # 测试4: 从文件加载配置
        print("\n🧪 测试4: 从文件加载配置")
        new_config_manager = ConfigManager(temp_dir)
        new_proxy_config = new_config_manager.get_proxy_config()
        new_crawler_config = new_config_manager.get_crawler_config()
        
        print(f"  代理提供商: {new_proxy_config.provider_name}")
        print(f"  代理启用: {new_proxy_config.enabled}")
        print(f"  爬虫平台: {new_crawler_config.platform}")
        
        # 测试5: 配置优先级
        print("\n🧪 测试5: 配置优先级")
        # 设置环境变量
        os.environ["PROXY_PROVIDER_NAME"] = "jisuhttp"
        os.environ["PLATFORM"] = "ks"
        
        # 重新加载配置
        config_manager.reload()
        
        proxy_config = config_manager.get_proxy_config()
        crawler_config = config_manager.get_crawler_config()
        
        print(f"  环境变量优先级 - 代理提供商: {proxy_config.provider_name}")
        print(f"  环境变量优先级 - 爬虫平台: {crawler_config.platform}")
        
        # 清理环境变量
        os.environ.pop("PROXY_PROVIDER_NAME", None)
        os.environ.pop("PLATFORM", None)
    
    print("\n✅ 配置管理器测试完成")


def test_proxy_config():
    """测试代理配置"""
    print("\n=== 代理配置测试 ===")
    
    # 测试青果代理配置
    proxy_config = ProxyConfig(
        provider_name="qingguo",
        enabled=True,
        pool_count=10,
        qingguo_key="test_key",
        qingguo_pwd="test_pwd"
    )
    
    print(f"  提供商: {proxy_config.provider_name}")
    print(f"  启用: {proxy_config.enabled}")
    print(f"  池大小: {proxy_config.pool_count}")
    print(f"  青果Key: {proxy_config.qingguo_key}")
    print(f"  青果密码: {proxy_config.qingguo_pwd}")
    
    # 测试快代理配置
    proxy_config = ProxyConfig(
        provider_name="kuaidaili",
        enabled=True,
        pool_count=5,
        kuaidaili_secret_id="test_secret",
        kuaidaili_signature="test_sig",
        kuaidaili_user_name="test_user",
        kuaidaili_user_pwd="test_pass"
    )
    
    print(f"\n  提供商: {proxy_config.provider_name}")
    print(f"  启用: {proxy_config.enabled}")
    print(f"  池大小: {proxy_config.pool_count}")
    print(f"  快代理Secret ID: {proxy_config.kuaidaili_secret_id}")
    print(f"  快代理用户名: {proxy_config.kuaidaili_user_name}")


def test_crawler_config():
    """测试爬虫配置"""
    print("\n=== 爬虫配置测试 ===")
    
    crawler_config = CrawlerConfig(
        platform="xhs",
        keywords="测试关键词",
        login_type="qrcode",
        crawler_type="search",
        max_notes_count=50,
        enable_comments=True,
        enable_images=False,
        save_data_option="json",
        headless=False,
        max_sleep_sec=3,
        max_concurrency=2
    )
    
    print(f"  平台: {crawler_config.platform}")
    print(f"  关键词: {crawler_config.keywords}")
    print(f"  登录类型: {crawler_config.login_type}")
    print(f"  爬取类型: {crawler_config.crawler_type}")
    print(f"  最大数量: {crawler_config.max_notes_count}")
    print(f"  爬取评论: {crawler_config.enable_comments}")
    print(f"  爬取图片: {crawler_config.enable_images}")
    print(f"  保存方式: {crawler_config.save_data_option}")
    print(f"  无头模式: {crawler_config.headless}")
    print(f"  最大间隔: {crawler_config.max_sleep_sec}")
    print(f"  最大并发: {crawler_config.max_concurrency}")


def test_database_config():
    """测试数据库配置"""
    print("\n=== 数据库配置测试 ===")
    
    db_config = DatabaseConfig(
        host="localhost",
        port=3306,
        username="test_user",
        password="test_pass",
        database="test_db",
        charset="utf8mb4"
    )
    
    print(f"  主机: {db_config.host}")
    print(f"  端口: {db_config.port}")
    print(f"  用户名: {db_config.username}")
    print(f"  密码: {db_config.password}")
    print(f"  数据库: {db_config.database}")
    print(f"  字符集: {db_config.charset}")


def test_app_config():
    """测试应用配置"""
    print("\n=== 应用配置测试 ===")
    
    app_config = AppConfig(
        debug=True,
        log_level="DEBUG",
        data_dir="./data/test",
        user_data_dir="%s_user_data_dir_test"
    )
    
    print(f"  调试模式: {app_config.debug}")
    print(f"  日志级别: {app_config.log_level}")
    print(f"  数据目录: {app_config.data_dir}")
    print(f"  用户数据目录: {app_config.user_data_dir}")


def test_config_tools_integration():
    """测试配置工具集成"""
    print("\n=== 配置工具集成测试 ===")
    
    try:
        # 导入配置工具
        from tools.config_tools import show_config, export_config, get_config, set_config
        
        print("✅ 配置工具导入成功")
        
        # 测试配置获取
        value = get_config("proxy.provider_name")
        print(f"  获取配置值: {value}")
        
        # 测试配置设置
        set_config("test.key", "test_value")
        print("✅ 配置设置成功")
        
    except ImportError as e:
        print(f"❌ 配置工具导入失败: {e}")
    except Exception as e:
        print(f"❌ 配置工具测试失败: {e}")


if __name__ == "__main__":
    try:
        # 运行所有测试
        test_config_manager()
        test_proxy_config()
        test_crawler_config()
        test_database_config()
        test_app_config()
        test_config_tools_integration()
        
        print("\n🎉 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 