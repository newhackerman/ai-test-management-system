#!/bin/bash
echo "🚀 启动AI测试管理系统前端服务..."

cd frontend

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 启动开发服务器
echo "🌟 启动前端开发服务器..."
npm run dev
