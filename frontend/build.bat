@echo off
REM 前端构建脚本 (Windows)

echo 🚀 开始构建前端应用...

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

REM 安装依赖
echo 📦 安装依赖...
npm install
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    exit /b 1
)

REM 类型检查
echo 🔍 进行类型检查...
npm run type-check
if %errorlevel% neq 0 (
    echo ❌ 类型检查失败
    exit /b 1
)

REM 代码检查
echo 🔧 进行代码检查...
npm run lint
if %errorlevel% neq 0 (
    echo ❌ 代码检查失败
    exit /b 1
)

REM 构建应用
echo 🏗️ 构建应用...
npm run build
if %errorlevel% neq 0 (
    echo ❌ 构建失败
    exit /b 1
)

echo ✅ 前端应用构建完成！
echo 📁 构建文件已输出到: ../static/dist/
echo 🌐 现在可以启动FastAPI服务器来查看应用

pause