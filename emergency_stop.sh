#!/bin/bash
# 紧急停止爬虫脚本

echo "🛑 正在停止所有Python爬虫进程..."

# 查找并停止爬虫进程
pkill -f "python.*main.py"
pkill -f "python.*crawler"

# 等待进程完全停止
sleep 3

# 检查是否还有爬虫进程
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️ 强制停止剩余进程..."
    pkill -9 -f "python.*main.py"
fi

echo "✅ 所有爬虫进程已停止"

# 显示系统资源状态
echo "📊 当前系统资源状态:"
free -h
df -h /
