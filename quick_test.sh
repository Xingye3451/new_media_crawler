#!/bin/bash

# MediaCrawler 快速测试脚本
# 用于快速验证容器化后的功能

set -e

echo "🚀 MediaCrawler 快速测试脚本"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印带颜色的消息
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    print_step "检查Docker环境..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    print_status "Docker环境检查通过"
}

# 构建并启动容器
start_container() {
    print_step "构建并启动MediaCrawler API容器..."
    
    # 停止并删除现有容器
    docker-compose down 2>/dev/null || true
    
    # 构建并启动
    docker-compose up -d --build
    
    print_status "容器启动完成"
}

# 等待服务启动
wait_for_service() {
    print_step "等待API服务启动..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/api/v1/health >/dev/null 2>&1; then
            print_status "API服务启动成功"
            return 0
        fi
        
        print_warning "等待服务启动... (尝试 $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "服务启动超时"
    return 1
}

# 测试API功能
test_api() {
    print_step "测试API功能..."
    
    # 测试健康检查
    print_status "测试健康检查..."
    response=$(curl -s http://localhost:8000/api/v1/health)
    if echo "$response" | grep -q "healthy"; then
        print_status "健康检查通过"
    else
        print_error "健康检查失败"
        return 1
    fi
    
    # 测试获取平台列表
    print_status "测试获取平台列表..."
    response=$(curl -s http://localhost:8000/api/v1/platforms)
    if echo "$response" | grep -q "xhs"; then
        print_status "获取平台列表成功"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        print_error "获取平台列表失败"
        return 1
    fi
    
    print_status "API功能测试通过"
}

# 测试爬虫功能（可选）
test_crawler() {
    print_step "测试爬虫功能（可选）..."
    
    read -p "是否要测试爬虫功能？这可能需要较长时间 (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "启动爬虫测试任务..."
        
        # 创建测试任务
        task_response=$(curl -s -X POST http://localhost:8000/api/v1/crawler/start \
            -H "Content-Type: application/json" \
            -d '{
                "platform": "xhs",
                "login_type": "qrcode",
                "crawler_type": "search",
                "keywords": "编程",
                "start_page": 1,
                "get_comments": false,
                "save_data_option": "json",
                "max_notes_count": 2
            }')
        
        task_id=$(echo "$task_response" | jq -r '.data.task_id' 2>/dev/null)
        
        if [ "$task_id" != "null" ] && [ -n "$task_id" ]; then
            print_status "测试任务已启动: $task_id"
            print_warning "注意：爬虫任务需要手动扫码登录，请在容器日志中查看二维码"
            print_status "可以通过以下命令查看任务状态："
            echo "curl http://localhost:8000/api/v1/crawler/status/$task_id"
        else
            print_error "启动测试任务失败"
            echo "$task_response"
        fi
    else
        print_status "跳过爬虫功能测试"
    fi
}

# 显示使用说明
show_usage() {
    print_step "API使用说明"
    echo "================"
    echo "1. 健康检查: curl http://localhost:8000/api/v1/health"
    echo "2. 获取平台列表: curl http://localhost:8000/api/v1/platforms"
    echo "3. 启动爬虫任务:"
    echo "   curl -X POST http://localhost:8000/api/v1/crawler/start \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"platform\": \"xhs\", \"keywords\": \"编程\"}'"
    echo "4. 查看任务状态: curl http://localhost:8000/api/v1/crawler/status/{task_id}"
    echo "5. 查看API文档: http://localhost:8000/docs"
    echo ""
    print_status "容器日志查看: docker-compose logs -f mediacrawler-api"
}

# 主函数
main() {
    check_docker
    start_container
    wait_for_service
    test_api
    test_crawler
    show_usage
    
    print_status "🎉 测试完成！"
    print_status "API服务运行在: http://localhost:8000"
    print_status "API文档地址: http://localhost:8000/docs"
}

# 错误处理
trap 'print_error "脚本执行失败"; exit 1' ERR

# 执行主函数
main "$@" 