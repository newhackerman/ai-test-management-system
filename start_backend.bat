@echo off
echo 🚀 启动AI测试管理系统后端服务...
cd backend
REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建Python虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo 🔧 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️ 虚拟环境不存在，使用系统Python环境
)

REM 安装依赖
echo 📦 安装依赖...
pip install -r requirements.txt

REM 进入后端目录
cd backend

REM 检查环境配置
if not exist ".env" (
    echo ❌ .env文件不存在，请先配置环境变量
    echo 💡 可以运行: python -m src.cli.config_cli generate-template
    pause
    exit /b 1
)

REM 验证配置
echo 🔍 验证系统配置...
python -m src.cli.config_cli validate
if %ERRORLEVEL% neq 0 (
    echo ❌ 配置验证失败，请检查配置文件
    echo 💡 可以运行: python -m src.cli.config_cli show
    pause
    exit /b 1
)

echo ✅ 配置验证通过

REM 启动服务
echo 🌟 启动后端服务...
echo 💡 使用配置管理器动态加载配置
echo 📚 配置文档: CONFIG_MANAGEMENT.md
echo.

uvicorn src.main:app --reload

pause
