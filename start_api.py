#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MediaCrawler API 服务器启动脚本
"""

import uvicorn
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("启动 MediaCrawler API 服务器...")
    print("访问地址: http://localhost:8100")
    print("API文档: http://localhost:8100/docs")
    print("按 Ctrl+C 停止服务器")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        log_level="info"
    ) 