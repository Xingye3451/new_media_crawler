#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaCrawler 环境配置检查脚本
检查爬虫运行所需的环境和配置是否正确
"""

import os
import sys
import json
import requests
import subprocess
import psutil
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
import importlib.util

class CrawlerEnvironmentChecker:
    """爬虫环境检查器"""
    
    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []
        
    def log(self, message: str, level: str = "INFO"):
        """日志记录"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️",
            "CHECK": "🔍"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
        
        if level == "ERROR":
            self.errors.append(message)
        elif level == "WARNING":
            self.warnings.append(message)
    
    def check_python_version(self) -> bool:
        """检查Python版本"""
        self.log("检查Python版本...", "CHECK")
        
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            self.log(f"Python版本: {version.major}.{version.minor}.{version.micro}", "SUCCESS")
            return True
        else:
            self.log(f"Python版本过低: {version.major}.{version.minor}.{version.micro}，需要Python 3.9+", "ERROR")
            return False
    
    def check_required_packages(self) -> bool:
        """检查必需的Python包"""
        self.log("检查必需的Python包...", "CHECK")
        
        required_packages = [
            "playwright", "fastapi", "uvicorn", "httpx", "asyncio",
            "pandas", "mysql-connector-python", "psutil", "PyYAML",
            "tenacity", "requests", "aiofiles"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                spec = importlib.util.find_spec(package)
                if spec is None:
                    missing_packages.append(package)
                else:
                    self.log(f"✓ {package}", "SUCCESS")
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.log(f"缺少以下包: {', '.join(missing_packages)}", "ERROR")
            self.log("请运行: pip install -r requirements.txt", "ERROR")
            return False
        
        return True
    
    def check_playwright_browsers(self) -> bool:
        """检查Playwright浏览器"""
        self.log("检查Playwright浏览器...", "CHECK")
        
        try:
            result = subprocess.run(
                ["playwright", "install", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if "chromium" in result.stdout.lower():
                self.log("Playwright浏览器已安装", "SUCCESS")
                return True
            else:
                self.log("Playwright浏览器未安装", "ERROR")
                self.log("请运行: playwright install", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Playwright检查超时", "WARNING")
            return False
        except FileNotFoundError:
            self.log("Playwright未找到，请确保已安装", "ERROR")
            return False
        except Exception as e:
            self.log(f"Playwright检查失败: {e}", "ERROR")
            return False
    
    def check_api_service(self) -> bool:
        """检查API服务"""
        self.log("检查API服务...", "CHECK")
        
        try:
            response = requests.get("http://localhost:8100/api/v1/health", timeout=10)
            if response.status_code == 200:
                self.log("API服务运行正常", "SUCCESS")
                return True
            else:
                self.log(f"API服务异常: {response.status_code}", "ERROR")
                return False
        except requests.exceptions.ConnectionError:
            self.log("API服务未启动", "ERROR")
            self.log("请运行: ENV=local python start_with_env.py", "ERROR")
            return False
        except Exception as e:
            self.log(f"API服务检查失败: {e}", "ERROR")
            return False
    
    def check_config_files(self) -> bool:
        """检查配置文件"""
        self.log("检查配置文件...", "CHECK")
        
        config_files = [
            "config/config_local.yaml",
            "config/base_config.py"
        ]
        
        all_exist = True
        
        for config_file in config_files:
            if os.path.exists(config_file):
                self.log(f"✓ {config_file}", "SUCCESS")
            else:
                self.log(f"✗ {config_file} 不存在", "ERROR")
                all_exist = False
        
        # 检查配置文件格式
        if os.path.exists("config/config_local.yaml"):
            try:
                with open("config/config_local.yaml", 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.log("配置文件格式正确", "SUCCESS")
                    
                    # 检查关键配置项
                    if "crawler" in config:
                        self.log("✓ 爬虫配置存在", "SUCCESS")
                    else:
                        self.log("✗ 爬虫配置缺失", "WARNING")
                        
                    if "database" in config:
                        self.log("✓ 数据库配置存在", "SUCCESS")
                    else:
                        self.log("✗ 数据库配置缺失", "WARNING")
                        
            except yaml.YAMLError as e:
                self.log(f"配置文件格式错误: {e}", "ERROR")
                all_exist = False
        
        return all_exist
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        self.log("检查数据库连接...", "CHECK")
        
        try:
            # 读取数据库配置
            if not os.path.exists("config/config_local.yaml"):
                self.log("配置文件不存在，跳过数据库检查", "WARNING")
                return False
            
            with open("config/config_local.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            db_config = config.get("database", {})
            
            if not db_config:
                self.log("数据库配置不存在", "WARNING")
                return False
            
            # 尝试连接数据库
            import mysql.connector
            
            connection = mysql.connector.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 3306),
                user=db_config.get("username", "root"),
                password=db_config.get("password", ""),
                database=db_config.get("database", "mediacrawler"),
                charset=db_config.get("charset", "utf8mb4"),
                connection_timeout=10
            )
            
            if connection.is_connected():
                self.log("数据库连接正常", "SUCCESS")
                
                # 检查表结构
                cursor = connection.cursor()
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                if tables:
                    self.log(f"数据库表数量: {len(tables)}", "SUCCESS")
                else:
                    self.log("数据库表为空，可能需要初始化", "WARNING")
                
                cursor.close()
                connection.close()
                return True
            else:
                self.log("数据库连接失败", "ERROR")
                return False
                
        except ImportError:
            self.log("mysql-connector-python 未安装", "ERROR")
            return False
        except Exception as e:
            self.log(f"数据库连接检查失败: {e}", "ERROR")
            return False
    
    def check_directories(self) -> bool:
        """检查目录结构"""
        self.log("检查目录结构...", "CHECK")
        
        required_dirs = [
            "data",
            "logs",
            "config",
            "media_platform",
            "api",
            "base"
        ]
        
        all_exist = True
        
        for directory in required_dirs:
            if os.path.exists(directory):
                self.log(f"✓ {directory}/", "SUCCESS")
            else:
                self.log(f"✗ {directory}/ 不存在", "ERROR")
                all_exist = False
        
        # 检查数据目录权限
        if os.path.exists("data"):
            try:
                test_file = "data/.test_write"
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                self.log("数据目录可写", "SUCCESS")
            except Exception as e:
                self.log(f"数据目录权限问题: {e}", "ERROR")
                all_exist = False
        
        return all_exist
    
    def check_system_resources(self) -> bool:
        """检查系统资源"""
        self.log("检查系统资源...", "CHECK")
        
        # 检查内存
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        
        if available_gb >= 2:
            self.log(f"可用内存: {available_gb:.1f}GB", "SUCCESS")
        else:
            self.log(f"可用内存不足: {available_gb:.1f}GB，建议至少2GB", "WARNING")
        
        # 检查磁盘空间
        disk = psutil.disk_usage('.')
        free_gb = disk.free / (1024 ** 3)
        
        if free_gb >= 5:
            self.log(f"可用磁盘空间: {free_gb:.1f}GB", "SUCCESS")
        else:
            self.log(f"磁盘空间不足: {free_gb:.1f}GB，建议至少5GB", "WARNING")
        
        # 检查CPU
        cpu_count = psutil.cpu_count()
        self.log(f"CPU核心数: {cpu_count}", "SUCCESS")
        
        return True
    
    def check_network_connectivity(self) -> bool:
        """检查网络连接"""
        self.log("检查网络连接...", "CHECK")
        
        test_urls = [
            "https://www.xiaohongshu.com",
            "https://www.douyin.com",
            "https://www.kuaishou.com",
            "https://www.bilibili.com"
        ]
        
        success_count = 0
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    platform = url.split('.')[-2]
                    self.log(f"✓ {platform} 网络连接正常", "SUCCESS")
                    success_count += 1
                else:
                    platform = url.split('.')[-2]
                    self.log(f"✗ {platform} 网络连接异常: {response.status_code}", "WARNING")
            except Exception as e:
                platform = url.split('.')[-2]
                self.log(f"✗ {platform} 网络连接失败: {e}", "WARNING")
        
        if success_count >= 3:
            self.log("网络连接状态良好", "SUCCESS")
            return True
        else:
            self.log("网络连接状态不佳", "WARNING")
            return False
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        self.log("检查登录状态...", "CHECK")
        
        platforms = ["xhs", "dy", "ks", "bili"]
        logged_in_count = 0
        
        for platform in platforms:
            try:
                response = requests.post(
                    "http://localhost:8100/api/v1/login/verify",
                    json={"platform": platform},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("is_logged_in", False):
                        self.log(f"✓ {platform} 已登录", "SUCCESS")
                        logged_in_count += 1
                    else:
                        self.log(f"✗ {platform} 未登录", "WARNING")
                else:
                    self.log(f"✗ {platform} 登录状态检查失败", "WARNING")
                    
            except Exception as e:
                self.log(f"✗ {platform} 登录状态检查失败: {e}", "WARNING")
        
        if logged_in_count >= 3:
            self.log("登录状态良好", "SUCCESS")
            return True
        else:
            self.log("需要更多平台登录", "WARNING")
            return False
    
    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查"""
        self.log("开始环境配置检查...", "INFO")
        print("=" * 60)
        
        checks = [
            ("Python版本", self.check_python_version),
            ("必需包", self.check_required_packages),
            ("Playwright浏览器", self.check_playwright_browsers),
            ("API服务", self.check_api_service),
            ("配置文件", self.check_config_files),
            ("数据库连接", self.check_database_connection),
            ("目录结构", self.check_directories),
            ("系统资源", self.check_system_resources),
            ("网络连接", self.check_network_connectivity),
            ("登录状态", self.check_login_status)
        ]
        
        results = {}
        
        for name, check_func in checks:
            print(f"\n{'='*20} {name} {'='*20}")
            try:
                result = check_func()
                results[name] = result
            except Exception as e:
                self.log(f"{name}检查失败: {e}", "ERROR")
                results[name] = False
        
        # 生成总结报告
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results: Dict[str, bool]):
        """生成总结报告"""
        print("\n" + "=" * 60)
        self.log("环境检查总结", "INFO")
        print("=" * 60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        success_rate = passed / total * 100
        
        print(f"\n📊 检查结果统计:")
        print(f"  总检查项: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {total - passed}")
        print(f"  成功率: {success_rate:.1f}%")
        
        if self.errors:
            print(f"\n❌ 严重错误 ({len(self.errors)}项):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)}项):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        # 给出建议
        print(f"\n💡 建议:")
        
        if success_rate >= 90:
            print("  🎉 环境配置完美！可以开始数据抓取了。")
        elif success_rate >= 70:
            print("  ✅ 环境配置基本正常，建议解决警告项目。")
        elif success_rate >= 50:
            print("  ⚠️  环境配置需要改进，请解决错误项目。")
        else:
            print("  🚨 环境配置存在严重问题，请先解决所有错误。")
        
        # 保存报告
        report = {
            "检查时间": datetime.now().isoformat(),
            "检查结果": results,
            "成功率": f"{success_rate:.1f}%",
            "错误": self.errors,
            "警告": self.warnings
        }
        
        report_file = f"env_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n📄 详细报告已保存: {report_file}")
        except Exception as e:
            print(f"\n❌ 保存报告失败: {e}")


def main():
    """主函数"""
    print("🔧 MediaCrawler 环境配置检查工具")
    print("=" * 60)
    
    checker = CrawlerEnvironmentChecker()
    results = checker.run_all_checks()
    
    # 返回退出码
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    success_rate = passed / total * 100
    
    if success_rate >= 70:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败


if __name__ == "__main__":
    main() 