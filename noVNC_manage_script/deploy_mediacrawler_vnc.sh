#!/bin/bash

# MediaCrawler Web远程桌面一键部署脚本
# 版本: 2.0
# 适用: Ubuntu 18.04+ 生产服务器
# 作者: MediaCrawler Team

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER=$(whoami)
HOME_DIR=$(eval echo ~$CURRENT_USER)
LOCAL_IP=$(hostname -I | awk '{print $1}')
VNC_PORT=5901
WEB_PORT=6080

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "🚀 MediaCrawler Web远程桌面一键部署脚本"
    echo "=========================================="
    echo "📱 部署完成后可在浏览器中操作验证码"
    echo "🌐 访问地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    echo -e "${NC}"
}

# 环境检查
check_environment() {
    log_info "正在检查部署环境..."
    
    # 检查操作系统
    if ! grep -q "Ubuntu" /etc/os-release; then
        log_warning "检测到非Ubuntu系统，可能存在兼容性问题"
    fi
    
    # 检查用户权限
    if [ "$EUID" -eq 0 ]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
    
    # 检查sudo权限
    if ! sudo -n true 2>/dev/null; then
        log_error "需要sudo权限来安装系统组件"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $python_version"
    
    # 检查内存
    local memory_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$memory_gb" -lt 2 ]; then
        log_warning "系统内存不足2GB，可能影响性能"
    fi
    
    # 检查端口占用
    for port in $VNC_PORT $WEB_PORT 8100 80; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_warning "端口 $port 已被占用，可能需要停止相关服务"
        fi
    done
    
    log_success "环境检查完成"
}

# 安装系统依赖
install_system_packages() {
    log_info "正在安装系统组件..."
    
    # 更新包列表
    sudo apt update
    
    # 安装必要组件
    local packages=(
        "xvfb"           # 虚拟显示器
        "x11vnc"         # VNC服务器
        "fluxbox"        # 窗口管理器
        "xterm"          # 终端
        "wget"           # 下载工具
        "unzip"          # 解压工具
        "curl"           # HTTP客户端
        "netcat-openbsd" # 网络测试
        "supervisor"     # 进程管理
        "nginx"          # Web服务器
        "git"            # 版本控制
        "python3-pip"    # Python包管理器
        "python3-numpy"  # Python科学计算库
        "python3-full"   # Python完整包
    )
    
    if sudo apt install -y "${packages[@]}"; then
        log_success "系统组件安装成功"
    else
        log_error "系统组件安装失败，请检查网络连接和权限"
        exit 1
    fi
}

# 安装noVNC和websockify
install_novnc() {
    log_info "正在安装noVNC Web界面..."
    
    cd /opt
    
    # 安装noVNC
    if [ ! -d "/opt/noVNC" ]; then
        if sudo git clone https://github.com/novnc/noVNC.git; then
            log_success "noVNC下载成功"
        else
            log_warning "Git下载失败，使用wget备用方案..."
            sudo wget https://github.com/novnc/noVNC/archive/refs/heads/master.zip
            sudo unzip master.zip
            sudo mv noVNC-master noVNC
            sudo rm master.zip
            log_success "noVNC下载成功(备用方案)"
        fi
    else
        log_success "noVNC已存在"
    fi
    
    # 安装websockify
    if [ ! -d "/opt/websockify" ]; then
        if sudo git clone https://github.com/novnc/websockify.git; then
            log_success "websockify下载成功"
        else
            log_warning "Git下载失败，使用wget备用方案..."
            sudo wget https://github.com/novnc/websockify/archive/refs/heads/master.zip -O websockify.zip
            sudo unzip websockify.zip
            sudo mv websockify-master websockify
            sudo rm websockify.zip
            log_success "websockify下载成功(备用方案)"
        fi
    else
        log_success "websockify已存在"
    fi
    
    # 安装websockify
    install_websockify
}

# 安装websockify
install_websockify() {
    log_info "正在配置websockify..."
    
    # 方案1: 系统包管理器
    if sudo apt install -y python3-websockify 2>/dev/null; then
        log_success "使用系统包管理器安装websockify成功"
        return 0
    fi
    
    # 方案2: pip安装
    cd /opt/websockify
    if sudo pip3 install -e . --break-system-packages 2>/dev/null; then
        log_success "使用pip安装websockify成功"
        return 0
    fi
    
    # 方案3: 符号链接
    log_warning "pip安装失败，创建符号链接..."
    sudo ln -sf /opt/websockify/websockify /usr/local/bin/websockify
    sudo chmod +x /usr/local/bin/websockify
    log_success "创建websockify符号链接成功"
}

# 创建VNC启动脚本
create_vnc_scripts() {
    log_info "正在创建VNC启动脚本..."
    
    # 创建VNC配置目录
    mkdir -p ~/.vnc
    
    # 创建VNC启动脚本
    cat > $HOME_DIR/start_vnc_simple.sh << 'SCRIPT_EOF'
#!/bin/bash

export DISPLAY=:1
VNC_PORT=5901
WEB_PORT=6080

echo "🖥️ 启动MediaCrawler Web远程桌面服务..."

# 手动清理可能的残留进程
pkill -f "Xvfb :1" 2>/dev/null || true
pkill -f "x11vnc.*:1" 2>/dev/null || true
pkill -f "websockify.*6080" 2>/dev/null || true
pkill -f "fluxbox" 2>/dev/null || true

sleep 2

# 启动虚拟显示器
echo "🖥️ 启动虚拟显示器..."
Xvfb :1 -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

sleep 3

# 启动窗口管理器
echo "🪟 启动窗口管理器..."
DISPLAY=:1 fluxbox &
FLUXBOX_PID=$!

sleep 2

# 启动VNC服务器
echo "📡 启动VNC服务器..."
x11vnc -display :1 -nopw -listen localhost -xkb -ncache 10 -ncache_cr -forever -rfbport $VNC_PORT &
X11VNC_PID=$!

sleep 2

# 启动noVNC Web界面
echo "🌐 启动Web VNC界面..."
cd /opt/noVNC

if command -v websockify &> /dev/null; then
    echo "📡 使用系统websockify..."
    websockify --web . $WEB_PORT localhost:$VNC_PORT &
    WEBSOCKIFY_PID=$!
elif [ -f "./utils/novnc_proxy" ]; then
    echo "📡 使用noVNC内置proxy..."
    ./utils/novnc_proxy --vnc localhost:$VNC_PORT --listen $WEB_PORT &
    WEBSOCKIFY_PID=$!
else
    echo "❌ 未找到websockify"
    exit 1
fi

sleep 3

# 验证服务
echo "🔍 验证服务状态..."
if netstat -tuln | grep -q ":$VNC_PORT "; then
    echo "✅ VNC服务器运行正常 (端口: $VNC_PORT)"
else
    echo "❌ VNC服务器启动失败"
    exit 1
fi

if netstat -tuln | grep -q ":$WEB_PORT "; then
    echo "✅ Web VNC界面运行正常 (端口: $WEB_PORT)"
else
    echo "❌ Web VNC界面启动失败"
    exit 1
fi

echo ""
echo "✅ Web远程桌面服务启动完成!"
echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}'):$WEB_PORT/vnc.html"
echo "📋 进程ID: Xvfb=$XVFB_PID, Fluxbox=$FLUXBOX_PID, x11vnc=$X11VNC_PID, websockify=$WEBSOCKIFY_PID"
echo ""

# 进程监控和信号处理
cleanup() {
    echo "🛑 正在停止服务..."
    kill $WEBSOCKIFY_PID 2>/dev/null || true
    kill $X11VNC_PID 2>/dev/null || true
    kill $FLUXBOX_PID 2>/dev/null || true
    kill $XVFB_PID 2>/dev/null || true
    echo "✅ 服务已停止"
}

trap cleanup SIGTERM SIGINT

# 保持脚本运行
while true; do
    sleep 10
done
SCRIPT_EOF

    chmod +x $HOME_DIR/start_vnc_simple.sh
    log_success "VNC启动脚本创建完成"
}

# 创建systemd服务
create_systemd_service() {
    log_info "正在创建systemd服务..."
    
    # 停止现有服务
    sudo systemctl stop mediacrawler-vnc.service 2>/dev/null || true
    
    # 创建systemd服务文件
    sudo tee /etc/systemd/system/mediacrawler-vnc.service > /dev/null << EOF
[Unit]
Description=MediaCrawler Web Remote Desktop Service
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=10
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment=HOME=$HOME_DIR
Environment=USER=$CURRENT_USER
Environment=DISPLAY=:1
ExecStart=$HOME_DIR/start_vnc_simple.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mediacrawler-vnc

[Install]
WantedBy=multi-user.target
EOF

    # 重载systemd配置
    sudo systemctl daemon-reload
    
    # 启用开机自启
    sudo systemctl enable mediacrawler-vnc.service
    
    log_success "systemd服务创建完成"
}

# 创建管理脚本
create_management_script() {
    log_info "正在创建管理脚本..."
    
    # 使用修正版的管理脚本（移除不存在的依赖）
    cat > $SCRIPT_DIR/manage_vnc.sh << 'MANAGE_EOF'
#!/bin/bash

LOCAL_IP=$(hostname -I | awk '{print $1}')
VNC_PORT=5901
WEB_PORT=6080

show_banner() {
    echo "🚀 MediaCrawler Web远程桌面服务管理"
    echo "===================================="
    echo "📱 访问地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    echo "🔧 VNC端口: $VNC_PORT | Web端口: $WEB_PORT"
    echo ""
}

check_service_status() {
    if systemctl is-active --quiet mediacrawler-vnc.service; then
        echo "✅ 服务正在运行"
        return 0
    else
        echo "❌ 服务未运行"
        return 1
    fi
}

check_ports() {
    echo "🔍 检查端口状态..."
    if netstat -tuln | grep -q ":$VNC_PORT "; then
        echo "✅ VNC端口 $VNC_PORT 正常"
    else
        echo "❌ VNC端口 $VNC_PORT 未开放"
    fi
    
    if netstat -tuln | grep -q ":$WEB_PORT "; then
        echo "✅ Web端口 $WEB_PORT 正常"
    else
        echo "❌ Web端口 $WEB_PORT 未开放"
    fi
}

case "$1" in
    start)
        show_banner
        echo "🚀 启动服务..."
        sudo systemctl start mediacrawler-vnc.service
        sleep 3
        check_service_status && check_ports
        ;;
    stop)
        show_banner
        echo "🛑 停止服务..."
        sudo systemctl stop mediacrawler-vnc.service
        sleep 2
        check_service_status
        ;;
    restart)
        show_banner
        echo "🔄 重启服务..."
        sudo systemctl restart mediacrawler-vnc.service
        sleep 3
        check_service_status && check_ports
        ;;
    status)
        show_banner
        echo "📊 服务状态:"
        echo "============"
        sudo systemctl status mediacrawler-vnc.service --no-pager -l
        echo ""
        check_ports
        ;;
    enable)
        show_banner
        echo "🔧 启用开机自启..."
        sudo systemctl enable mediacrawler-vnc.service
        ;;
    disable)
        show_banner
        echo "🔧 禁用开机自启..."
        sudo systemctl disable mediacrawler-vnc.service
        ;;
    *)
        show_banner
        echo "用法: $0 {start|stop|restart|status|enable|disable}"
        echo ""
        echo "当前状态:"
        check_service_status
        check_ports
        ;;
esac
MANAGE_EOF

    chmod +x $SCRIPT_DIR/manage_vnc.sh
    log_success "管理脚本创建完成"
}

# 配置防火墙
configure_firewall() {
    log_info "正在配置防火墙..."
    
    # 检查ufw是否安装
    if ! command -v ufw &> /dev/null; then
        log_warning "未安装ufw防火墙，跳过防火墙配置"
        return 0
    fi
    
    # 开放必要端口
    sudo ufw allow $WEB_PORT/tcp    # noVNC Web端口
    sudo ufw allow 8100/tcp         # MediaCrawler API端口
    
    log_success "防火墙配置完成"
}

# 启动并测试服务
start_and_test_service() {
    log_info "正在启动并测试服务..."
    
    # 启动服务
    sudo systemctl start mediacrawler-vnc.service
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态
    if systemctl is-active --quiet mediacrawler-vnc.service; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败"
        sudo systemctl status mediacrawler-vnc.service --no-pager
        return 1
    fi
    
    # 检查端口
    if netstat -tuln | grep -q ":$WEB_PORT "; then
        log_success "Web端口 $WEB_PORT 正常监听"
    else
        log_error "Web端口 $WEB_PORT 未监听"
        return 1
    fi
    
    # 测试HTTP响应
    if curl -s --max-time 10 "http://localhost:$WEB_PORT/vnc.html" > /dev/null; then
        log_success "Web界面响应正常"
    else
        log_warning "Web界面测试失败，但服务可能正在启动中"
    fi
}

# 显示部署结果
show_deployment_result() {
    echo ""
    echo -e "${GREEN}"
    echo "🎉 MediaCrawler Web远程桌面部署完成!"
    echo "===================================="
    echo -e "${NC}"
    
    echo "📱 访问地址:"
    echo "   主要地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
    echo "   备用地址: http://localhost:$WEB_PORT/vnc.html"
    echo ""
    
    echo "🔧 服务管理:"
    echo "   启动服务: ./manage_vnc.sh start"
    echo "   停止服务: ./manage_vnc.sh stop"
    echo "   重启服务: ./manage_vnc.sh restart"
    echo "   查看状态: ./manage_vnc.sh status"
    echo ""
    
    echo "🚀 开机自启:"
    echo "   已启用 - 服务器重启后自动运行"
    echo "   禁用自启: ./manage_vnc.sh disable"
    echo ""
    
    echo "📋 使用流程:"
    echo "   1. 访问MediaCrawler爬虫界面"
    echo "   2. 开始登录流程"
    echo "   3. 出现验证码时，打开Web远程桌面"
    echo "   4. 在远程桌面中手动完成验证码"
    echo "   5. 返回爬虫界面继续流程"
    echo ""
    
    echo "🛠️ 故障排除:"
    echo "   查看日志: sudo journalctl -u mediacrawler-vnc.service -f"
    echo "   重新部署: ./deploy_mediacrawler_vnc.sh"
    echo ""
}

# 主函数
main() {
    show_banner
    
    echo "开始部署MediaCrawler Web远程桌面服务..."
    echo ""
    
    # 执行部署步骤
    check_environment
    install_system_packages
    install_novnc
    create_vnc_scripts
    create_systemd_service
    create_management_script
    configure_firewall
    start_and_test_service
    
    # 显示部署结果
    show_deployment_result
    
    log_success "部署完成! 🎉"
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 