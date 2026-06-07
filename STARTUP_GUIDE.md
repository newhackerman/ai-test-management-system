# 🚀 启动指南

## 快速启动

### 1. 使用启动脚本（推荐）

```bash
# Windows
.\start_backend.bat

# 该脚本会自动：
# ✅ 检查并创建虚拟环境
# ✅ 安装依赖包
# ✅ 验证系统配置
# ✅ 启动后端服务
```

### 2. 手动启动

```bash
# 1. 进入后端目录
cd backend

# 2. 验证配置
python -m src.cli.config_cli validate

# 3. 启动服务
uvicorn src.main:app --reload
```

## 配置管理

### 验证配置
```bash
cd backend
python -m src.cli.config_cli validate
```

### 查看配置
```bash
python -m src.cli.config_cli show
```

### 生成配置模板
```bash
python -m src.cli.config_cli generate-template
```

## 故障排除

### 配置验证失败
如果启动时配置验证失败，请：

1. 检查 `.env` 文件是否存在
2. 运行配置诊断：`python -m src.cli.config_cli show`
3. 生成配置模板：`python -m src.cli.config_cli generate-template`

### 服务启动失败
1. 检查端口是否被占用
2. 验证数据库连接
3. 检查Redis连接
4. 查看详细错误日志

## 配置文档

详细的配置管理文档请参考：
- `backend/CONFIG_MANAGEMENT.md` - 完整配置指南
- `CONFIGURATION_REFACTOR_SUMMARY.md` - 配置重构总结