@echo off
chcp 65001 >nul
echo =====================================================
echo 在线会议模块数据库迁移工具
echo =====================================================
echo.

echo 🔍 验证迁移脚本...
python test_meeting_migration.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 迁移脚本验证失败，请检查脚本内容
    pause
    exit /b 1
)

echo.
echo 📋 准备执行迁移...
echo 请确保：
echo   1. MySQL服务正在运行
echo   2. users表和projects表已存在
echo   3. 数据库连接信息正确
echo.

set /p confirm="确认执行迁移？(y/N): "
if /i not "%confirm%"=="y" (
    echo 取消迁移
    pause
    exit /b 0
)

echo.
echo 🚀 执行迁移脚本...
mysql -u root -p aitestdb < migrations/meeting_module_migration.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 迁移执行成功！
    echo.
    echo 📊 验证结果...
    mysql -u root -p -e "USE aitestdb; SHOW TABLES LIKE 'meeting%%'; SELECT COUNT(*) as meeting_tables FROM information_schema.tables WHERE table_schema='aitestdb' AND table_name LIKE 'meeting%%';"
) else (
    echo.
    echo ❌ 迁移执行失败，错误代码: %ERRORLEVEL%
    echo 请检查：
    echo   1. 数据库连接信息
    echo   2. users和projects表是否存在
    echo   3. 数据类型是否匹配
)

echo.
pause