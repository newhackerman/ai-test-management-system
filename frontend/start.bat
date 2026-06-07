@echo off
echo 启动AI测试管理系统前端服务...

REM 检查node_modules是否存在
if not exist "node_modules" (
    echo 安装依赖...
    npm install --legacy-peer-deps
)

REM 启动服务
echo 启动服务...
npm start

pause