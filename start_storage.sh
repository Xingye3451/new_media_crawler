#!/bin/bash

# MediaCrawler 存储系统快速启动脚本

echo "🚀 启动 MediaCrawler 存储系统..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data
mkdir -p logs
mkdir -p config

# 检查环境配置文件是否存在
if [ ! -f "config/config_local.yaml" ] && [ ! -f "config/config_dev.yaml" ] && [ ! -f "config/config_docker.yaml" ] && [ ! -f "config/config_prod.yaml" ]; then
    echo "⚠️  环境配置文件不存在，请先配置相应的环境配置文件..."
    echo "   可用的配置文件："
    echo "   - config/config_local.yaml (本地环境)"
    echo "   - config/config_dev.yaml (开发环境)"
    echo "   - config/config_docker.yaml (Docker环境)"
    echo "   - config/config_prod.yaml (生产环境)"
    echo ""
    echo "   请根据你的环境选择合适的配置文件进行配置"
    exit 1
fi

# 启动存储服务
echo "🐳 启动 MinIO 和 MySQL 服务..."
docker-compose -f docker-compose.storage.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.storage.yml ps

# 显示访问信息
echo ""
echo "✅ 存储系统启动完成！"
echo ""
echo "📊 服务访问地址："
echo "   - MinIO API: http://localhost:9000"
echo "   - MinIO 控制台: http://localhost:9001"
echo "   - MySQL: localhost:3306"
echo "   - Nginx: http://localhost"
echo ""
echo "🔑 默认登录信息："
echo "   - MinIO 用户名: minioadmin"
echo "   - MinIO 密码: minioadmin"
echo "   - MySQL 用户名: root"
echo "   - MySQL 密码: password"
echo ""
echo "📝 使用说明："
echo "   1. 访问 MinIO 控制台创建 bucket: mediacrawler-videos"
echo "   2. 配置相应环境的配置文件 (如 config/config_local.yaml)"
echo "   3. 运行 Python 脚本测试存储功能"
echo ""
echo "🛑 停止服务："
echo "   docker-compose -f docker-compose.storage.yml down"
echo ""
echo "📋 查看日志："
echo "   docker-compose -f docker-compose.storage.yml logs -f" 