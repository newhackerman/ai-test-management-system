# AI测试管理系统 - 用户管理模块

## 🚀 快速启动

### 1. 环境准备
- Python 3.9+
- Node.js 16+
- MySQL 8.0+
- Redis 6.0+

### 2. 后端启动
```bash
# Windows（推荐 - 包含配置验证）
.\start_backend.bat

# Linux/Mac
./start_backend.sh
```

> 💡 启动脚本会自动验证配置、安装依赖并启动服务
> 📚 详细启动指南请参考: [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

### 3. 前端启动
```bash
# Windows
start_frontend.bat

# Linux/Mac
./start_frontend.sh
```

### 4. 访问系统
- 前端地址: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/api/v1/docs

### 5. 默认账户
- 用户名: admin
- 密码: TEST@test1

## 📋 功能特性

### ✅ 已实现功能
- 用户认证 (登录/注册/登出)
- 用户管理 (CRUD操作)
- 角色权限管理
- 批量操作
- 用户导入导出
- 密码管理
- 会话管理
- AI需求分析，AI用例编写

### 🔄 开发中功能
- 多因素认证 (MFA)
- 单点登录 (SSO)
- 安全监控告警
- 详细审计日志

## 🛠️ 技术栈

### 后端
- FastAPI + Python
- SQLAlchemy + MySQL
- Redis缓存
- JWT认证
- bcrypt密码加密

### 前端
- React 18 + TypeScript
- Vite构建工具
- Zustand状态管理
- Radix UI组件
- Tailwind CSS样式

## 📚 文档

- [启动指南](STARTUP_GUIDE.md) - 快速启动和故障排除
- [配置管理指南](backend/CONFIG_MANAGEMENT.md) - 详细配置说明
- [配置重构总结](CONFIGURATION_REFACTOR_SUMMARY.md) - 配置管理改进说明

## 📞 支持

如有问题，请查看：
1. 用户管理模块实现分析报告
2. API文档: http://localhost:8000/api/v1/docs
3. 测试报告: user_management_test_report_*.json
4. 配置验证: `cd backend && python -m src.cli.config_cli validate`
