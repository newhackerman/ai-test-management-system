#!/bin/bash
echo "🚀 启动AI测试管理系统后端服务..."

cd backend

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt

# 检查环境配置
if [ ! -f ".env" ]; then
    echo "❌ .env文件不存在，请先运行 python3 quick_fix_critical_issues.py"
    exit 1
fi

# 启动服务
echo "🌟 启动后端服务..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
