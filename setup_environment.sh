#!/bin/bash

# MediaCrawler 项目环境设置脚本
# 适用于 Anaconda 环境

echo "=== MediaCrawler 项目环境设置 ==="

# 1. 创建新的conda环境
echo "1. 创建conda环境..."
conda create -n mediacrawler python=3.9 -y

# 2. 激活环境
echo "2. 激活环境..."
conda activate mediacrawler

# 3. 升级pip
echo "3. 升级pip..."
pip install --upgrade pip

# 4. 安装基础依赖
echo "4. 安装基础依赖..."
pip install fastapi uvicorn pydantic

# 5. 安装Playwright
echo "5. 安装Playwright..."
pip install playwright
playwright install

# 6. 安装数据库相关
echo "6. 安装数据库相关..."
pip install aiomysql pymysql

# 7. 安装其他工具库
echo "7. 安装其他工具库..."
pip install aiofiles pyyaml requests beautifulsoup4 lxml

# 8. 安装开发工具
echo "8. 安装开发工具..."
pip install pytest pytest-asyncio black flake8

# 9. 创建必要的目录
echo "9. 创建项目目录..."
mkdir -p data
mkdir -p logs
mkdir -p static
mkdir -p config

# 10. 设置环境变量
echo "10. 设置环境变量..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "=== 环境设置完成 ==="
echo ""
echo "使用以下命令激活环境："
echo "conda activate mediacrawler"
echo ""
echo "启动API服务器："
echo "python start_api.py"
echo ""
echo "访问测试页面："
echo "http://localhost:8100" 