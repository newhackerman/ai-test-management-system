@echo off
echo 🚀 启动AI测试管理系统前端服务...

cd frontend

REM 安装依赖
if not exist "node_modules" (
    echo 📦 安装前端依赖...
    npm install
)

REM 启动开发服务器
echo 🌟 启动前端开发服务器...
npm run dev

pause
