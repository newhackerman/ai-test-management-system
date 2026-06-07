# AI测试管理系统 - 后端服务

## 项目简介

这是AI测试管理系统的后端服务，提供用户管理、角色管理和权限管理等功能。

## 技术栈

- Python 3.8+
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Redis
- JWT

## 安装和运行

### Windows系统

1. 双击运行 `start.bat` 文件，或者手动执行以下命令：
   ```bash
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境
   venv\Scripts\activate.bat
   
   # 安装依赖
   pip install -r requirements.txt
   
   # 启动服务
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Linux/macOS系统

1. 运行 `start.sh` 文件，或者手动执行以下命令：
   ```bash
   # 创建虚拟环境
   python3 -m venv venv
   
   # 激活虚拟环境
   source venv/bin/activate
   
   # 安装依赖
   pip install -r requirements.txt
   
   # 启动服务
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API文档

服务启动后，可以通过以下地址访问API文档：

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 环境配置

可以通过 `.env` 文件配置环境变量，示例：

```env
# 应用配置
PROJECT_NAME="AI测试管理系统"
API_V1_STR="/api/v1"
DEBUG=True

# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/ai_test_management"

# Redis配置
REDIS_URL="redis://localhost:6379/0"

# JWT配置
SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS配置
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
ALLOWED_HOSTS=["*"]
```

## 项目结构

```
backend/
├── src/
│   ├── api/              # API路由
│   │   ├── auth.py       # 认证API
│   │   ├── users.py      # 用户API
│   │   ├── roles.py      # 角色API
│   │   ├── permissions.py # 权限API
│   │   └── __init__.py   # API路由初始化
│   ├── core/             # 核心配置
│   │   ├── config.py     # 配置管理
│   │   ├── database.py   # 数据库连接
│   │   ├── redis.py      # Redis配置
│   │   └── security.py   # 安全工具函数
│   ├── models/           # 数据模型
│   │   ├── base.py       # 基础模型
│   │   ├── user.py       # 用户模型
│   │   ├── role.py       # 角色模型
│   │   ├── permission.py # 权限模型
│   │   └── __init__.py   # 模型初始化
│   ├── schemas/          # 数据模型
│   │   ├── auth.py       # 认证数据模型
│   │   ├── user.py       # 用户数据模型
│   │   ├── role.py       # 角色数据模型
│   │   └── permission.py # 权限数据模型
│   ├── services/         # 服务层
│   │   ├── auth.py       # 认证服务
│   │   ├── user.py       # 用户服务
│   │   ├── role.py       # 角色服务
│   │   └── permission.py # 权限服务
│   ├── decorators.py     # 装饰器
│   └── main.py           # 主应用入口
├── requirements.txt      # 依赖包列表
├── start.bat            # Windows启动脚本
├── start.sh             # Linux/macOS启动脚本
└── README.md            # 说明文档
```

## 功能模块

### 认证模块
- 用户登录
- 用户注册
- 密码重置
- JWT令牌生成和验证

### 用户管理模块
- 用户列表查询
- 用户详情查看
- 用户创建
- 用户更新
- 用户删除
- 用户激活/停用
- 用户角色分配

### 角色管理模块
- 角色列表查询
- 角色详情查看
- 角色创建
- 角色更新
- 角色删除
- 角色激活/停用
- 角色权限分配

### 权限管理模块
- 权限列表查询
- 权限树结构
- 权限详情查看
- 权限创建
- 权限更新
- 权限删除
- 权限激活/停用