#!/bin/bash

# 前端构建脚本

echo "🚀 开始构建前端应用..."

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

# 安装依赖
echo "📦 安装依赖..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

# 类型检查
echo "🔍 进行类型检查..."
npm run type-check

if [ $? -ne 0 ]; then
    echo "❌ 类型检查失败"
    exit 1
fi

# 代码检查
echo "🔧 进行代码检查..."
npm run lint

if [ $? -ne 0 ]; then
    echo "❌ 代码检查失败"
    exit 1
fi

# 构建应用
echo "🏗️ 构建应用..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo "✅ 前端应用构建完成！"
echo "📁 构建文件已输出到: ../static/dist/"
echo "🌐 现在可以启动FastAPI服务器来查看应用"