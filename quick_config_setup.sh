#!/bin/bash

# MediaCrawler 快速配置设置脚本

echo "🚀 MediaCrawler 配置管理系统快速设置"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if ! python3 -c "import yaml" 2>/dev/null; then
    echo "📥 安装 PyYAML..."
    pip3 install PyYAML==6.0.1
fi

# 创建配置目录
echo "📁 创建配置目录..."
mkdir -p config
mkdir -p data/{development,production,test}

# 设置环境变量
echo "🔧 设置环境变量..."
export ENV=development

# 创建配置文件
echo "📝 创建配置文件..."

# 检查是否已有配置文件
if [ ! -f "config/config_development.yaml" ]; then
    echo "  创建开发环境配置文件..."
    python3 tools/config_tools.py create development
else
    echo "  开发环境配置文件已存在"
fi

if [ ! -f "config/config_production.yaml" ]; then
    echo "  创建生产环境配置文件..."
    python3 tools/config_tools.py create production
else
    echo "  生产环境配置文件已存在"
fi

if [ ! -f "config/config_test.yaml" ]; then
    echo "  创建测试环境配置文件..."
    python3 tools/config_tools.py create test
else
    echo "  测试环境配置文件已存在"
fi

# 显示当前配置
echo "📋 显示当前配置..."
python3 tools/config_tools.py show

# 提供使用说明
echo ""
echo "✅ 配置设置完成！"
echo ""
echo "📖 使用方法:"
echo "  1. 编辑配置文件:"
echo "     vim config/config_development.yaml"
echo ""
echo "  2. 设置环境变量（可选）:"
echo "     export ENV=development"
echo "     export qg_key='your_qingguo_key'"
echo "     export qg_pwd='your_qingguo_pwd'"
echo ""
echo "  3. 运行爬虫:"
echo "     python3 main.py"
echo ""
echo "  4. 查看配置:"
echo "     python3 tools/config_tools.py show"
echo ""
echo "  5. 测试配置:"
echo "     python3 test/test_config_manager.py"
echo ""
echo "📚 更多信息请查看:"
echo "   - config/CONFIG_GUIDE.md"
echo "   - proxy/QINGGUO_PROXY_GUIDE.md"
echo "   - README_API.md"
echo ""
echo "🎉 开始使用 MediaCrawler 吧！" 