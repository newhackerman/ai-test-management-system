#!/bin/bash

# 前端开发服务器启动脚本

echo "🚀 启动前端开发服务器..."

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 18+"
    exit 1
fi

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装 npm"
    exit 1
fi

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo "📦 首次运行，安装依赖..."
    npm install
    
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
fi

# 启动开发服务器
echo "🌐 启动开发服务器 (http://localhost:3000)..."
echo "📡 API代理到: http://localhost:8000"
echo "💡 请确保FastAPI服务器已在8000端口运行"
echo ""

npm run dev