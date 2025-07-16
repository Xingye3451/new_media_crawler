#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
支持环境变量的启动脚本
使用方法:
  ENV=local python start_with_env.py
  ENV=dev python start_with_env.py
  ENV=prod python start_with_env.py
"""

import os
import sys
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    # 获取环境变量
    env = os.getenv("ENV", "local").lower()
    
    print(f"=== MediaCrawler API 服务器启动 ===")
    print(f"环境: {env}")
    print(f"配置文件: config/config_{env}.yaml")
    print(f"访问地址: http://localhost:8100")
    print(f"API文档: http://localhost:8100/docs")
    print("按 Ctrl+C 停止服务器")
    print()
    
    # 启动服务器
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 