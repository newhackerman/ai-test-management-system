# AI助手模块数据库迁移指南

本目录包含AI助手模块的数据库迁移脚本和相关文档。

## 文件说明

### SQL脚本文件
- `ai_assistant_tables.sql` - AI助手模块表结构定义
- `ai_assistant_data.sql` - 基础数据和配置
- `init_ai_assistant.sql` - 完整初始化脚本（包含表结构和数据）

### Alembic迁移文件
- `../src/migrations/versions/001_create_ai_assistant_tables.py` - 核心表结构迁移
- `../src/migrations/versions/002_create_ai_assistant_extended_tables.py` - 扩展表结构迁移

### Python迁移工具
- `../migrate_ai_assistant.py` - Python迁移工具脚本

## 数据库表结构

AI助手模块包含以下主要表：

### 核心表
1. **ai_chat_sessions** - AI聊天会话表
   - 存储用户的AI对话会话信息
   - 包含会话配置、统计信息、元数据等

2. **ai_chat_messages** - AI聊天消息表
   - 存储会话中的所有消息
   - 支持多种内容类型和用户交互功能

3. **ai_model_configs** - AI模型配置表
   - 管理所有可用的AI模型配置
   - 包含模型参数、配额限制、成本配置等

4. **ai_prompt_templates** - AI提示词模板表
   - 存储可重用的提示词模板
   - 支持参数化、版本控制、权限管理

### 扩展表
5. **ai_suggestions** - AI建议表
   - 存储AI生成的优化建议
   - 支持建议分类、状态跟踪、效果评估

6. **ai_requirements_analysis** - AI需求分析表
   - 存储需求质量分析结果
   - 包含评分、问题识别、改进建议

7. **ai_usage_stats** - AI使用统计表
   - 记录AI服务使用统计数据
   - 支持多维度统计和成本分析

8. **ai_template_usage** - AI模板使用记录表
   - 记录模板使用情况和用户反馈
   - 用于模板效果分析和优化

## 使用方法

### 方法一：使用SQL脚本（推荐用于生产环境）

#### 1. 完整初始化（新部署）
```bash
# 在MySQL中执行完整初始化脚本
mysql -u root -p your_database_name < init_ai_assistant.sql
```

#### 2. 分步执行
```bash
# 1. 创建表结构
mysql -u root -p your_database_name < ai_assistant_tables.sql

# 2. 插入基础数据
mysql -u root -p your_database_name < ai_assistant_data.sql
```

### 方法二：使用Alembic迁移（推荐用于开发环境）

#### 1. 确保Alembic已配置
```bash
cd backend/src/migrations
```

#### 2. 执行迁移
```bash
# 升级到最新版本
alembic upgrade head

# 或者逐步升级
alembic upgrade 001_ai_assistant
alembic upgrade 002_ai_assistant_extended
```

#### 3. 回滚迁移（如需要）
```bash
# 回滚到指定版本
alembic downgrade 001_ai_assistant

# 回滚所有迁移
alembic downgrade base
```

### 方法三：使用Python迁移工具

#### 1. 检查当前状态
```bash
cd backend
python migrate_ai_assistant.py --status
```

#### 2. 创建表结构
```bash
python migrate_ai_assistant.py --upgrade
```

#### 3. 初始化默认数据
```bash
python migrate_ai_assistant.py --init-data
```

#### 4. 删除表结构（谨慎使用）
```bash
python migrate_ai_assistant.py --downgrade --force
```

## 环境要求

### 数据库要求
- MySQL 8.0+ 或 MariaDB 10.5+
- 支持JSON数据类型
- 支持UTF8MB4字符集

### Python环境要求（使用Python工具时）
- Python 3.9+
- SQLAlchemy 2.0+
- Alembic 1.8+
- PyMySQL 或 mysqlclient

### 权限要求
数据库用户需要以下权限：
- CREATE - 创建表
- ALTER - 修改表结构
- DROP - 删除表（回滚时需要）
- INSERT - 插入数据
- UPDATE - 更新数据
- DELETE - 删除数据
- INDEX - 创建索引
- REFERENCES - 创建外键

## 配置说明

### 环境变量配置
在执行迁移前，请确保设置以下环境变量：

```bash
# 数据库连接
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/database_name

# AI服务API密钥（用于初始化数据）
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
BAIDU_API_KEY=your_baidu_api_key
ALIYUN_API_KEY=your_aliyun_api_key
```

### 生产环境配置注意事项

1. **API密钥安全**
   - 修改默认的API密钥配置
   - 使用环境变量或密钥管理服务
   - 定期轮换API密钥

2. **配额限制**
   - 根据实际需求调整模型配额
   - 设置合理的成本控制阈值
   - 配置使用监控和告警

3. **性能优化**
   - 根据数据量调整索引策略
   - 配置合适的连接池大小
   - 设置定期数据清理任务

## 验证和测试

### 1. 表结构验证
```sql
-- 检查所有AI相关表是否创建成功
SHOW TABLES LIKE 'ai_%';

-- 检查表结构
DESCRIBE ai_chat_sessions;
DESCRIBE ai_model_configs;
```

### 2. 数据验证
```sql
-- 检查基础数据是否插入成功
SELECT COUNT(*) FROM ai_model_configs WHERE is_enabled = 1;
SELECT COUNT(*) FROM ai_prompt_templates WHERE visibility = 'PUBLIC';
```

### 3. 功能测试
```sql
-- 测试创建会话
INSERT INTO ai_chat_sessions (title, user_id, ai_provider, ai_model) 
VALUES ('测试会话', 1, 'openai', 'gpt-4-turbo');

-- 测试创建消息
INSERT INTO ai_chat_messages (session_id, role, content) 
VALUES (1, 'USER', '你好，这是一条测试消息');
```

## 故障排除

### 常见问题

1. **外键约束错误**
   - 确保用户表(users)已存在
   - 检查外键引用的数据是否存在

2. **字符集问题**
   - 确保数据库使用UTF8MB4字符集
   - 检查连接字符串是否正确

3. **权限不足**
   - 检查数据库用户权限
   - 确保有创建表和索引的权限

4. **JSON字段不支持**
   - 确保MySQL版本 >= 5.7
   - 或使用TEXT字段替代JSON字段

### 日志和监控

1. **迁移日志**
   - 保存迁移执行日志
   - 记录错误信息和解决方案

2. **性能监控**
   - 监控表大小增长
   - 监控查询性能
   - 设置慢查询日志

## 备份和恢复

### 备份策略
```bash
# 备份AI助手相关表
mysqldump -u root -p database_name \
  ai_chat_sessions ai_chat_messages ai_model_configs \
  ai_prompt_templates ai_suggestions ai_requirements_analysis \
  ai_usage_stats ai_template_usage > ai_assistant_backup.sql
```

### 恢复数据
```bash
# 恢复备份数据
mysql -u root -p database_name < ai_assistant_backup.sql
```

## 版本历史

- **v1.0** (2024-12-19)
  - 初始版本
  - 包含核心表结构和基础数据
  - 支持多种迁移方式

## 联系和支持

如果在迁移过程中遇到问题，请：

1. 检查本文档的故障排除部分
2. 查看迁移日志和错误信息
3. 确认环境配置是否正确
4. 联系开发团队获取支持

---

**重要提醒**：在生产环境执行迁移前，请务必：
1. 备份现有数据
2. 在测试环境验证迁移脚本
3. 制定回滚计划
4. 通知相关团队成员