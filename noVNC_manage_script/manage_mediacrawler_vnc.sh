#!/bin/bash

# MediaCrawler Web远程桌面服务管理脚本
# 作者: MediaCrawler Team
# 功能: 管理Web远程桌面服务的启动、停止、状态检查等

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

show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  start    - 启动服务"
    echo "  stop     - 停止服务"
    echo "  restart  - 重启服务"
    echo "  status   - 查看服务状态"
    echo "  test     - 测试服务连通性"
    echo "  logs     - 查看服务日志"
    echo "  enable   - 启用开机自启"
    echo "  disable  - 禁用开机自启"
    echo "  install  - 重新安装服务"
    echo "  uninstall - 卸载服务"
    echo "  help     - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start        # 启动服务"
    echo "  $0 status       # 查看状态"
    echo "  $0 test         # 测试连通性"
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

test_connectivity() {
    echo "🌐 测试服务连通性..."
    
    # 测试VNC端口
    if nc -z localhost $VNC_PORT 2>/dev/null; then
        echo "✅ VNC服务 (端口 $VNC_PORT) 可访问"
    else
        echo "❌ VNC服务 (端口 $VNC_PORT) 不可访问"
    fi
    
    # 测试Web端口
    if nc -z localhost $WEB_PORT 2>/dev/null; then
        echo "✅ Web服务 (端口 $WEB_PORT) 可访问"
    else
        echo "❌ Web服务 (端口 $WEB_PORT) 不可访问"
    fi
    
    # 测试HTTP响应
    if curl -s --max-time 5 "http://localhost:$WEB_PORT/vnc.html" > /dev/null; then
        echo "✅ Web界面可正常访问"
    else
        echo "❌ Web界面访问失败"
    fi
}

show_processes() {
    echo "🔍 相关进程状态:"
    echo "==============="
    ps aux | grep -E "(Xvfb|x11vnc|fluxbox|websockify)" | grep -v grep | while read line; do
        echo "  $line"
    done
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
        echo ""
        show_processes
        ;;
        
    test)
        show_banner
        check_service_status
        check_ports
        test_connectivity
        ;;
        
    logs)
        show_banner
        echo "📋 实时日志 (按Ctrl+C退出):"
        echo "=========================="
        sudo journalctl -u mediacrawler-vnc.service -f
        ;;
        
    enable)
        show_banner
        echo "🔧 启用开机自启..."
        sudo systemctl enable mediacrawler-vnc.service
        if systemctl is-enabled --quiet mediacrawler-vnc.service; then
            echo "✅ 开机自启已启用"
        else
            echo "❌ 开机自启启用失败"
        fi
        ;;
        
    disable)
        show_banner
        echo "🔧 禁用开机自启..."
        sudo systemctl disable mediacrawler-vnc.service
        if ! systemctl is-enabled --quiet mediacrawler-vnc.service; then
            echo "✅ 开机自启已禁用"
        else
            echo "❌ 开机自启禁用失败"
        fi
        ;;
        
    install)
        show_banner
        echo "🔧 重新安装服务..."
        ./simple_systemd_service.sh
        ;;
        
    uninstall)
        show_banner
        echo "🗑️ 卸载服务..."
        sudo systemctl stop mediacrawler-vnc.service
        sudo systemctl disable mediacrawler-vnc.service
        sudo rm -f /etc/systemd/system/mediacrawler-vnc.service
        sudo systemctl daemon-reload
        echo "✅ 服务已卸载"
        ;;
        
    help|--help|-h)
        show_banner
        show_help
        ;;
        
    "")
        show_banner
        echo "📊 当前状态:"
        echo "============"
        check_service_status
        check_ports
        echo ""
        echo "💡 使用 '$0 help' 查看所有可用命令"
        echo "🌐 访问地址: http://$LOCAL_IP:$WEB_PORT/vnc.html"
        ;;
        
    *)
        show_banner
        echo "❌ 未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 