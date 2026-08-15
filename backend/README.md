# AI 测试管理系统 - 后端服务

## 技术栈

- Python 3.9+ / FastAPI / Pydantic
- SQLAlchemy（异步）+ MySQL
- Redis 缓存
- JWT 认证（支持 MFA 多因素认证）
- WebSocket 实时推送（AI 对话、仪表盘、健康监控等）

## 安装和运行

```bash
# 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 验证配置（需在 backend 目录下，根目录需有 .env）
python -m src.cli.config_cli validate

# 启动服务
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

也可以使用仓库根目录的 `start_backend.bat`（Windows）或 `start_backend.sh`（Linux/Mac）一键启动。

## API 文档

服务启动后：

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 环境配置

通过根目录 `.env` 文件配置，示例：

```env
PROJECT_NAME="AI测试管理系统"
API_V1_STR="/api/v1"
DEBUG=True

DATABASE_URL="mysql+asyncmy://user:password@localhost:3306/aitestdb"
REDIS_URL="redis://localhost:6379/0"

SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

配置管理与诊断 CLI：

```bash
python -m src.cli.config_cli validate           # 验证配置
python -m src.cli.config_cli show               # 查看当前配置
python -m src.cli.config_cli generate-template  # 生成配置模板
```

详细说明见 [CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md)。

## 项目结构

```
backend/
├── src/
│   ├── api/            # API 路由（v1/ 下为全量业务模块）
│   ├── adapters/       # AI 模型适配器（OpenAI、通义、文心等）
│   ├── cli/            # 配置管理等命令行工具
│   ├── core/           # 配置、数据库、Redis、安全等核心组件
│   ├── middleware/     # 中间件
│   ├── migrations/     # 数据库迁移
│   ├── models/         # SQLAlchemy 数据模型
│   ├── repositories/   # 数据访问层
│   ├── schemas/        # Pydantic 数据模型
│   ├── services/       # 业务服务层
│   ├── tasks/          # 后台任务
│   └── main.py         # 应用入口
├── sql/                # 数据库脚本
└── requirements.txt    # 依赖列表
```

## 主要业务模块

- 认证与账户：登录/注册/登出、MFA、个人资料、会话管理
- 权限体系：用户 / 角色 / 权限（RBAC）、高级权限校验、审计日志
- 项目管理：项目、团队、里程碑、进度、统计分析
- 需求管理：需求全流程（变更、评审、讨论、追踪）与 AI 需求分析
- 测试管理：测试用例、测试计划、测试执行、测试报告与导出
- 质量域：缺陷管理、风险管理、质量度量
- AI 服务：AI 助手（多模型路由、流式响应、上下文缓存）、提示词模板、告警配置、成本控制
- 平台服务：仪表盘、通知、会议、任务、健康监控、自动恢复、缓存优化
