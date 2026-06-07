# 配置管理指南

## 概述

本系统采用分层配置管理方式，避免硬编码，提供灵活的配置管理机制。

## 配置层次结构

配置按以下优先级顺序加载（高优先级覆盖低优先级）：

1. **环境变量** (最高优先级)
2. **Settings类默认值**
3. **配置文件** (config/*.json)
4. **代码默认值** (最低优先级)

## 配置文件结构

```
backend/
├── .env                    # 主环境配置文件
├── .env.example           # 环境配置模板
├── config/                # 配置文件目录
│   ├── api_routes.json    # API路由配置
│   ├── server.json        # 服务器配置
│   └── ...               # 其他配置文件
└── src/
    ├── core/config.py     # 配置类定义
    ├── utils/config_manager.py  # 配置管理器
    └── cli/config_cli.py  # 配置管理CLI工具
```

## 主要配置项

### 服务器配置
```bash
HOST=0.0.0.0                    # 服务器主机
PORT=8000                       # 服务器端口
DEBUG=false                     # 调试模式
LOG_LEVEL=INFO                  # 日志级别
```

### 数据库配置
```bash
DATABASE_URL=mysql+asyncmy://user:pass@host:port/db
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=aitestdb
DATABASE_USER=aitest
DATABASE_PASSWORD=your_password
```

### Redis配置
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### JWT配置
```bash
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_HOURS=1
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### API路由配置
```bash
API_V1_STR=/api/v1
API_AUTH_PREFIX=/auth
API_USERS_PREFIX=/users
API_ROLES_PREFIX=/roles
API_PERMISSIONS_PREFIX=/permissions
```

### CORS配置
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### AI服务配置
```bash
# OpenAI
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# Anthropic
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Gemini
GEMINI_API_KEY=your_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_MODEL=gemini-pro
```

## 使用配置管理器

### 在代码中使用配置

```python
from src.utils.config_manager import get_config_manager

# 获取配置管理器实例
config_manager = get_config_manager()

# 获取单个配置项
host = config_manager.get_config("HOST", "0.0.0.0")
port = config_manager.get_config("PORT", 8000)

# 获取配置组
server_config = config_manager.get_server_config()
database_config = config_manager.get_database_config()
redis_config = config_manager.get_redis_config()
jwt_config = config_manager.get_jwt_config()
cors_config = config_manager.get_cors_config()
api_config = config_manager.get_api_config()
ai_config = config_manager.get_ai_config()
```

### 配置验证

```python
# 重新加载配置
config_manager.reload_config()

# 验证必需的配置项
required_configs = ["DATABASE_URL", "JWT_SECRET_KEY", "HOST", "PORT"]
for config_key in required_configs:
    value = config_manager.get_config(config_key)
    if not value:
        raise ValueError(f"缺少必需的配置项: {config_key}")
```

## CLI工具使用

系统提供了配置管理CLI工具，用于验证、查看和管理配置。

### 安装和使用

```bash
# 进入后端目录
cd backend

# 验证配置
python -m src.cli.config_cli validate

# 显示当前配置
python -m src.cli.config_cli show

# 导出配置到文件
python -m src.cli.config_cli export --output config_backup.json

# 检查环境文件
python -m src.cli.config_cli check-env

# 生成环境变量模板
python -m src.cli.config_cli generate-template
```

### CLI命令详解

1. **validate**: 验证所有必需的配置项是否已设置
2. **show**: 显示当前所有配置项（隐藏敏感信息）
3. **export**: 导出配置到JSON文件（隐藏敏感信息）
4. **check-env**: 检查环境配置文件是否存在
5. **generate-template**: 生成环境变量配置模板

## 配置文件示例

### API路由配置 (config/api_routes.json)

```json
{
  "api_routes": {
    "auth": {
      "prefix": "/auth",
      "tags": ["认证管理"],
      "description": "用户认证相关接口"
    },
    "users": {
      "prefix": "/users",
      "tags": ["用户管理"],
      "description": "用户管理相关接口"
    }
  }
}
```

### 服务器配置 (config/server.json)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 1,
    "reload": true,
    "debug": false,
    "log_level": "INFO"
  },
  "performance": {
    "max_request_size": 104857600,
    "timeout": 30,
    "keepalive_timeout": 5,
    "max_concurrent_requests": 1000
  }
}
```

## 最佳实践

### 1. 环境变量命名规范
- 使用大写字母和下划线
- 使用描述性名称
- 按功能模块分组

### 2. 敏感信息处理
- 敏感信息（密码、API密钥）只存储在环境变量中
- 不要将敏感信息提交到版本控制系统
- 使用 `.env.example` 提供配置模板

### 3. 配置验证
- 在应用启动时验证必需的配置项
- 提供有意义的错误消息
- 使用类型检查确保配置值的正确性

### 4. 配置文档
- 为每个配置项提供清晰的描述
- 说明配置项的默认值和可选值
- 提供配置示例

### 5. 配置管理
- 定期备份配置
- 使用版本控制管理配置模板
- 为不同环境提供不同的配置

## 故障排除

### 常见问题

1. **配置项未生效**
   - 检查环境变量是否正确设置
   - 确认配置项名称拼写正确
   - 验证配置加载顺序

2. **敏感信息泄露**
   - 检查 `.env` 文件是否在 `.gitignore` 中
   - 确认日志中不包含敏感信息
   - 使用配置管理工具时注意隐藏敏感信息

3. **配置验证失败**
   - 使用 CLI 工具验证配置
   - 检查必需配置项是否缺失
   - 确认配置值的格式正确

### 调试配置

```bash
# 使用CLI工具检查配置
python -m src.cli.config_cli validate
python -m src.cli.config_cli show

# 检查环境变量
env | grep -E "(DATABASE|REDIS|JWT|API|CORS)"

# 查看配置文件
ls -la config/
cat config/api_routes.json
```

## 配置迁移

当需要更新配置结构时：

1. 更新配置类定义
2. 更新配置管理器
3. 更新环境变量模板
4. 更新文档
5. 提供迁移脚本（如需要）

## 安全注意事项

1. **不要在代码中硬编码敏感信息**
2. **使用强密码和密钥**
3. **定期轮换密钥**
4. **限制配置文件访问权限**
5. **监控配置变更**

## 总结

通过使用分层配置管理系统，我们实现了：

- ✅ 避免硬编码
- ✅ 灵活的配置管理
- ✅ 环境特定配置
- ✅ 配置验证和管理工具
- ✅ 安全的敏感信息处理
- ✅ 易于维护和扩展

这种配置管理方式使系统更加灵活、安全和易于维护。