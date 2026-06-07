@echo off
REM 前端开发服务器启动脚本 (Windows)

echo 🚀 启动前端开发服务器...

REM 检查Node.js是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js 未安装，请先安装 Node.js 18+
    exit /b 1
)

REM 检查npm是否安装
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ npm 未安装，请先安装 npm
    exit /b 1
)

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo 📦 首次运行，安装依赖...
    npm install
    
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        exit /b 1
    )
)

REM 启动开发服务器
echo 🌐 启动开发服务器 (http://localhost:3000)...
echo 📡 API代理到: http://localhost:8000
echo 💡 请确保FastAPI服务器已在8000端口运行
echo.

npm run dev