@echo off
chcp 65001 >nul
echo [启动] 启动AI测试管理系统后端服务...
cd backend

REM 直接使用本机Python环境（不再使用venv，减少硬盘占用）

REM 安装依赖
echo [安装] 安装依赖...
pip install -r requirements.txt

REM 进入后端目录
cd backend

REM 检查环境配置
if not exist ".env" (
    echo [错误] .env文件不存在，请先配置环境变量
    echo [提示] 可以运行: python -m src.cli.config_cli generate-template
    pause
    exit /b 1
)

REM 验证配置
echo [验证] 验证系统配置...
python -m src.cli.config_cli validate
if %ERRORLEVEL% neq 0 (
    echo [错误] 配置验证失败，请检查配置文件
    echo [提示] 可以运行: python -m src.cli.config_cli show
    pause
    exit /b 1
)

echo [成功] 配置验证通过

REM 启动服务
echo 启动后端服务
echo 使用配置管理器动态加载配置
echo 配置文档 CONFIG_MANAGEMENT.md
echo.

uvicorn src.main:app --reload

pause
