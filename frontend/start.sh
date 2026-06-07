#!/bin/bash

echo "启动AI测试管理系统前端服务..."

# 检查node_modules是否存在
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install --legacy-peer-deps
fi

# 启动服务
echo "启动服务..."
npm start