# AI 测试管理系统

一个 AI 驱动的测试管理平台，覆盖项目管理、需求管理、测试设计与执行、缺陷与风险管理等完整测试流程，并内置多模型 AI 助手辅助需求分析与用例编写。

## 功能特性

### 测试管理
- 项目管理：项目、团队、里程碑、进度与统计分析
- 需求管理：需求变更、评审、讨论、通知、追踪矩阵，支持 AI 需求分析
- 测试管理:测试用例、测试计划、测试执行、测试报告（支持 Allure 集成与报告导出/订阅分发）
- 缺陷管理：缺陷全生命周期跟踪与质量度量
- 风险管理：风险识别、跟踪与项目风险分析

### AI 能力
- AI 助手：多轮对话、流式响应、上下文管理、对话 WebSocket
- 多模型接入:OpenAI、阿里通义、百度文心等，支持模型配置与智能路由
- AI 辅助：需求质量分析、用例生成建议、提示词模板、告警配置、成本控制与请求队列

### 平台能力
- 仪表盘:可配置组件、实时数据推送（WebSocket）
- 权限体系:用户/角色/权限（RBAC）、高级权限校验、MFA 多因素认证
- 系统管理:配置管理（含导入导出）、审计日志、通知、会议管理、任务管理、健康监控与自动恢复

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.9+ / FastAPI / SQLAlchemy / MySQL / Redis / JWT |
| 前端 | React 18 + TypeScript / Vite / Zustand / Radix UI / Tailwind CSS |
| 测试 | pytest（独立仓库目录 `pytest/`，支持 Allure 报告） |

## 快速启动

### 1. 环境准备

- Python 3.9+
- Node.js 16+
- MySQL 8.0+
- Redis 6.0+

### 2. 配置

在项目根目录准备 `.env` 文件（数据库、Redis、JWT、AI 模型密钥等）。
可使用配置 CLI 验证与生成模板：

```bash
cd backend
python -m src.cli.config_cli validate           # 验证配置
python -m src.cli.config_cli show               # 查看当前配置
python -m src.cli.config_cli generate-template  # 生成配置模板
```

详细配置说明见 [backend/CONFIG_MANAGEMENT.md](backend/CONFIG_MANAGEMENT.md)。

### 3. 启动后端

```bash
# Windows（推荐，包含配置验证与依赖安装）
.\start_backend.bat

# Linux/Mac
./start_backend.sh

# 或手动启动
cd backend
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 启动前端

```bash
# Windows
start_frontend.bat

# Linux/Mac
./start_frontend.sh
```

### 5. 访问系统

- 前端地址: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api/v1/docs （Swagger）/ `/api/v1/redoc` （ReDoc）

默认账户：`admin` / `TEST@test1`

## 项目结构

```
├── backend/            # FastAPI 后端服务
│   ├── src/api/        # API 路由（含 v1 全量业务模块）
│   ├── src/services/   # 业务服务层
│   ├── src/models/     # 数据模型
│   ├── src/adapters/   # AI 模型适配器
│   └── sql/            # 数据库脚本
├── frontend/           # React 前端应用
│   └── src/pages/      # 业务页面
├── docs/               # 项目文档（API / 部署 / 开发 / 用户手册）
├── pytest/             # 外部化 pytest 测试工程
├── k8s/                # Kubernetes 部署配置
├── scripts/            # 辅助脚本
└── deploy.sh           # 部署脚本
```

## 文档

- [后端服务说明](backend/README.md)
- [前端工程说明](frontend/README.md)
- [配置管理指南](backend/CONFIG_MANAGEMENT.md)
- [高级 API 文档](backend/ADVANCED_APIS_DOCUMENTATION.md)
- [MCP 客户端文档](backend/MCP_CLIENT_DOCUMENTATION.md)
- [开发者文档](docs/developer/README.md) · [部署文档](docs/deployment/README.md) · [用户手册](docs/user-manual/README.md) · [API 示例](docs/api/examples.md)
- [pytest 测试工程说明](pytest/README.md)

## 故障排除

- 配置验证失败：检查根目录 `.env` 是否存在，运行 `python -m src.cli.config_cli show` 查看详情
- 服务启动失败：检查端口占用、数据库与 Redis 连接，查看后端日志
- 前端请求跨域错误：确认 `BACKEND_CORS_ORIGINS` 包含前端地址
