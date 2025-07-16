#!/bin/bash

# MediaCrawler Web远程桌面部署验证脚本
# 版本: 1.0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
LOCAL_IP=$(hostname -I | awk '{print $1}')
VNC_PORT=5901
WEB_PORT=6080
ERRORS=0
WARNINGS=0

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((ERRORS++))
}

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "🔍 MediaCrawler Web远程桌面部署验证"
    echo "===================================="
    echo "📱 验证地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    echo -e "${NC}"
}

# 检查系统服务
check_systemd_service() {
    log_info "检查systemd服务..."
    
    # 检查服务文件是否存在
    if [ ! -f "/etc/systemd/system/mediacrawler-vnc.service" ]; then
        log_error "systemd服务文件不存在"
        return 1
    fi
    
    # 检查服务状态
    if systemctl is-active --quiet mediacrawler-vnc.service; then
        log_success "服务正在运行"
    else
        log_error "服务未运行"
        echo "服务状态详情:"
        sudo systemctl status mediacrawler-vnc.service --no-pager -l
        return 1
    fi
    
    # 检查开机自启
    if systemctl is-enabled --quiet mediacrawler-vnc.service; then
        log_success "开机自启已启用"
    else
        log_warning "开机自启未启用"
    fi
}

# 检查进程
check_processes() {
    log_info "检查相关进程..."
    
    local processes=("Xvfb" "x11vnc" "fluxbox" "websockify")
    
    for process in "${processes[@]}"; do
        if pgrep -f "$process" > /dev/null; then
            log_success "$process 进程运行中"
        else
            log_error "$process 进程未运行"
        fi
    done
}

# 检查端口
check_ports() {
    log_info "检查端口状态..."
    
    # 检查VNC端口
    if netstat -tuln | grep -q ":$VNC_PORT "; then
        log_success "VNC端口 $VNC_PORT 正常监听"
    else
        log_error "VNC端口 $VNC_PORT 未监听"
    fi
    
    # 检查Web端口
    if netstat -tuln | grep -q ":$WEB_PORT "; then
        log_success "Web端口 $WEB_PORT 正常监听"
    else
        log_error "Web端口 $WEB_PORT 未监听"
    fi
}

# 检查网络连接
check_network() {
    log_info "检查网络连接..."
    
    # 检查VNC连接
    if nc -z localhost $VNC_PORT 2>/dev/null; then
        log_success "VNC服务可连接"
    else
        log_error "VNC服务不可连接"
    fi
    
    # 检查Web连接
    if nc -z localhost $WEB_PORT 2>/dev/null; then
        log_success "Web服务可连接"
    else
        log_error "Web服务不可连接"
    fi
}

# 检查HTTP响应
check_http_response() {
    log_info "检查HTTP响应..."
    
    # 检查noVNC主页
    if curl -s --max-time 10 "http://localhost:$WEB_PORT/vnc.html" > /dev/null; then
        log_success "noVNC主页响应正常"
    else
        log_error "noVNC主页无响应"
    fi
    
    # 检查API端点
    if curl -s --max-time 10 "http://localhost:$WEB_PORT/" > /dev/null; then
        log_success "根路径响应正常"
    else
        log_warning "根路径无响应"
    fi
}

# 检查文件和目录
check_files() {
    log_info "检查文件和目录..."
    
    # 检查关键文件
    local files=(
        "/opt/noVNC/vnc.html"
        "/opt/noVNC/app/ui.js"
        "/opt/websockify/websockify"
        "$HOME/start_vnc_simple.sh"
        "./manage_vnc.sh"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            log_success "文件存在: $file"
        else
            log_error "文件缺失: $file"
        fi
    done
    
    # 检查目录
    local dirs=(
        "/opt/noVNC"
        "/opt/websockify"
        "$HOME/.vnc"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_success "目录存在: $dir"
        else
            log_error "目录缺失: $dir"
        fi
    done
}

# 检查依赖包
check_dependencies() {
    log_info "检查系统依赖..."
    
    local packages=("xvfb" "x11vnc" "fluxbox" "curl" "netcat-openbsd")
    
    for package in "${packages[@]}"; do
        if dpkg -l | grep -q "^ii  $package "; then
            log_success "依赖包已安装: $package"
        else
            log_error "依赖包未安装: $package"
        fi
    done
}

# 检查防火墙
check_firewall() {
    log_info "检查防火墙设置..."
    
    if ! command -v ufw &> /dev/null; then
        log_warning "未安装ufw防火墙"
        return 0
    fi
    
    # 检查端口规则
    if sudo ufw status | grep -q "$WEB_PORT/tcp"; then
        log_success "Web端口 $WEB_PORT 已开放"
    else
        log_warning "Web端口 $WEB_PORT 未在防火墙中开放"
    fi
}

# 性能测试
performance_test() {
    log_info "执行性能测试..."
    
    # 测试响应时间
    local response_time=$(curl -o /dev/null -s -w "%{time_total}\n" "http://localhost:$WEB_PORT/vnc.html")
    
    if (( $(echo "$response_time < 5.0" | bc -l) )); then
        log_success "HTTP响应时间正常: ${response_time}s"
    else
        log_warning "HTTP响应时间较慢: ${response_time}s"
    fi
    
    # 检查内存使用
    local memory_usage=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
    log_info "当前内存使用: $memory_usage"
}

# 显示测试结果
show_test_results() {
    echo ""
    echo -e "${BLUE}📊 验证结果汇总${NC}"
    echo "===================="
    
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✅ 所有检查通过！${NC}"
        echo ""
        echo "🎉 部署验证成功!"
        echo "📱 可以开始使用Web远程桌面了"
        echo "🌐 访问地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    else
        echo -e "${RED}❌ 发现 $ERRORS 个错误${NC}"
        echo ""
        echo "🛠️ 建议解决方案:"
        echo "1. 检查服务日志: sudo journalctl -u mediacrawler-vnc.service -f"
        echo "2. 重启服务: ./manage_vnc.sh restart"
        echo "3. 重新部署: ./deploy_mediacrawler_vnc.sh"
    fi
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  发现 $WARNINGS 个警告${NC}"
        echo "这些警告不影响基本功能，但建议关注"
    fi
    
    echo ""
}

# 显示使用指南
show_usage_guide() {
    echo -e "${BLUE}📋 使用指南${NC}"
    echo "============"
    echo ""
    echo "🚀 服务管理:"
    echo "   启动: ./manage_vnc.sh start"
    echo "   停止: ./manage_vnc.sh stop"
    echo "   状态: ./manage_vnc.sh status"
    echo ""
    echo "🔧 故障排除:"
    echo "   查看日志: sudo journalctl -u mediacrawler-vnc.service -f"
    echo "   重新验证: ./verify_deployment.sh"
    echo ""
    echo "📱 用户操作:"
    echo "   1. 访问: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    echo "   2. 点击 'Connect' 连接"
    echo "   3. 在远程桌面中操作验证码"
    echo ""
}

# 主函数
main() {
    show_banner
    
    echo "开始验证MediaCrawler Web远程桌面部署..."
    echo ""
    
    # 执行各项检查
    check_systemd_service
    check_processes
    check_ports
    check_network
    check_http_response
    check_files
    check_dependencies
    check_firewall
    performance_test
    
    # 显示结果
    show_test_results
    
    if [ $ERRORS -eq 0 ]; then
        show_usage_guide
    fi
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 