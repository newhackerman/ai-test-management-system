# AI助手模块数据库设计文档

## 概述

本文档详细描述了AI助手模块的数据库表结构设计，包括对话管理、AI模型配置、提示词模板、使用统计等核心功能的数据存储方案。

## 数据库表结构

### 1. AI模型配置表 (ai_model_configs)

**表名**: `ai_model_configs`  
**用途**: 存储AI服务提供商和模型的配置信息  
**对应任务要求**: `ai_provider_configs` - AI服务配置表

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| provider | VARCHAR(50) | NOT NULL | AI服务提供商 (openai, anthropic, baidu_wenxin等) |
| model_name | VARCHAR(100) | NOT NULL | 模型名称 (gpt-4, claude-3-opus等) |
| display_name | VARCHAR(200) | NOT NULL | 显示名称 |
| description | TEXT | NULL | 模型描述 |
| **配置信息** |
| api_endpoint | VARCHAR(500) | NULL | API端点URL |
| api_key | VARCHAR(500) | NULL | API密钥 (加密存储) |
| api_version | VARCHAR(50) | NULL | API版本 |
| **模型参数** |
| max_tokens | INTEGER | DEFAULT 4000 | 最大Token数 |
| temperature | FLOAT | DEFAULT 0.7 | 温度参数 (0.0-2.0) |
| top_p | FLOAT | DEFAULT 1.0 | Top-p参数 (0.0-1.0) |
| frequency_penalty | FLOAT | DEFAULT 0.0 | 频率惩罚 (-2.0-2.0) |
| presence_penalty | FLOAT | DEFAULT 0.0 | 存在惩罚 (-2.0-2.0) |
| **状态和限制** |
| is_enabled | BOOLEAN | DEFAULT TRUE | 是否启用 |
| is_default | BOOLEAN | DEFAULT FALSE | 是否为默认模型 |
| daily_quota | INTEGER | NULL | 每日配额 (请求数) |
| monthly_quota | INTEGER | NULL | 每月配额 (请求数) |
| cost_per_token | FLOAT | NULL | 每Token成本 (美元) |
| **能力标签** |
| capabilities | JSON | NULL | 模型能力标签 |
| supported_languages | JSON | NULL | 支持的语言列表 |
| use_cases | JSON | NULL | 适用场景列表 |
| **性能指标** |
| avg_response_time | FLOAT | NULL | 平均响应时间 (秒) |
| success_rate | FLOAT | NULL | 成功率 (0.0-1.0) |
| last_health_check | DATETIME | NULL | 最后健康检查时间 |
| **使用统计** |
| total_requests | INTEGER | DEFAULT 0 | 总请求数 |
| total_tokens_used | INTEGER | DEFAULT 0 | 总Token使用量 |
| total_cost | FLOAT | DEFAULT 0.0 | 总成本 |

#### 索引设计

- `idx_ai_model_configs_provider`: provider字段索引，用于按提供商查询
- `idx_ai_model_configs_is_enabled`: is_enabled字段索引，用于查询可用模型
- `idx_ai_model_configs_is_default`: is_default字段索引，用于查询默认模型
- `uk_provider_model`: (provider, model_name)唯一约束，确保同一提供商下模型名称唯一

#### 示例数据

```json
{
  "provider": "openai",
  "model_name": "gpt-4-turbo",
  "display_name": "GPT-4 Turbo",
  "description": "最新的GPT-4模型，具有更快的响应速度和更低的成本",
  "api_endpoint": "https://api.openai.com/v1/chat/completions",
  "max_tokens": 4000,
  "temperature": 0.7,
  "capabilities": ["text_generation", "code_generation", "analysis"],
  "supported_languages": ["zh", "en", "ja", "ko"],
  "use_cases": ["general_chat", "code_assistance", "document_writing"]
}
```

### 2. AI聊天会话表 (ai_chat_sessions)

**表名**: `ai_chat_sessions`  
**用途**: 存储用户的AI对话会话信息  
**对应任务要求**: `conversations` - 对话会话表

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| title | VARCHAR(200) | NOT NULL | 会话标题 |
| user_id | INTEGER | NOT NULL, FK | 用户ID (外键关联users表) |
| status | ENUM | NOT NULL, DEFAULT 'ACTIVE' | 会话状态 (ACTIVE, ARCHIVED, DELETED) |
| **会话配置** |
| ai_provider | VARCHAR(50) | NULL | AI服务提供商 |
| ai_model | VARCHAR(100) | NULL | AI模型名称 |
| system_prompt | TEXT | NULL | 系统提示词 |
| **统计信息** |
| message_count | INTEGER | DEFAULT 0 | 消息数量 |
| total_tokens | INTEGER | DEFAULT 0 | 总Token数 |
| last_activity_at | DATETIME | NULL | 最后活动时间 |
| **会话元数据** |
| tags | TEXT | NULL | 标签 (JSON格式) |
| session_metadata | TEXT | NULL | 元数据 (JSON格式) |

#### 索引设计

- `idx_ai_chat_sessions_user_id`: user_id字段索引，用于查询用户的会话
- `idx_ai_chat_sessions_status`: status字段索引，用于按状态查询
- `idx_ai_chat_sessions_ai_provider`: ai_provider字段索引，用于按AI提供商查询
- `idx_ai_chat_sessions_last_activity_at`: last_activity_at字段索引，用于按活动时间排序

#### 关联关系

- `user_id` → `users.id`: 多对一关系，一个用户可以有多个会话
- `messages`: 一对多关系，一个会话可以有多条消息

### 3. AI聊天消息表 (ai_chat_messages)

**表名**: `ai_chat_messages`  
**用途**: 存储AI对话中的具体消息内容  
**对应任务要求**: `conversation_messages` - 消息表

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| session_id | INTEGER | NOT NULL, FK | 会话ID (外键关联ai_chat_sessions表) |
| role | ENUM | NOT NULL | 消息角色 (USER, ASSISTANT, SYSTEM) |
| content | TEXT | NOT NULL | 消息内容 |
| content_type | ENUM | DEFAULT 'TEXT' | 内容类型 (TEXT, MARKDOWN, CODE, IMAGE, FILE) |
| **AI相关信息** |
| ai_provider | VARCHAR(50) | NULL | AI服务提供商 |
| ai_model | VARCHAR(100) | NULL | AI模型名称 |
| tokens_used | INTEGER | DEFAULT 0 | 使用的Token数 |
| confidence_score | FLOAT | NULL | 置信度分数 (0.0-1.0) |
| **消息状态** |
| is_streaming | BOOLEAN | DEFAULT FALSE | 是否为流式消息 |
| is_error | BOOLEAN | DEFAULT FALSE | 是否为错误消息 |
| error_message | TEXT | NULL | 错误信息 |
| **消息元数据** |
| message_metadata | TEXT | NULL | 元数据 (JSON格式) |
| parent_message_id | INTEGER | NULL, FK | 父消息ID (自关联) |
| **用户交互** |
| user_rating | INTEGER | NULL | 用户评分 (1-5) |
| user_feedback | TEXT | NULL | 用户反馈 |
| is_bookmarked | BOOLEAN | DEFAULT FALSE | 是否收藏 |

#### 索引设计

- `idx_ai_chat_messages_session_id`: session_id字段索引，用于查询会话的消息
- `idx_ai_chat_messages_role`: role字段索引，用于按角色查询
- `idx_ai_chat_messages_ai_provider`: ai_provider字段索引，用于按AI提供商查询
- `idx_ai_chat_messages_created_at`: created_at字段索引，用于按时间排序
- `idx_ai_chat_messages_parent_message_id`: parent_message_id字段索引，用于查询子消息

#### 关联关系

- `session_id` → `ai_chat_sessions.id`: 多对一关系，一个会话可以有多条消息
- `parent_message_id` → `ai_chat_messages.id`: 自关联，支持消息回复和分支

### 4. AI提示词模板表 (ai_prompt_templates)

**表名**: `ai_prompt_templates`  
**用途**: 存储用户创建和共享的提示词模板

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| name | VARCHAR(200) | NOT NULL | 模板名称 |
| description | TEXT | NULL | 模板描述 |
| category | ENUM | NOT NULL | 模板分类 |
| **模板内容** |
| content | TEXT | NOT NULL | 模板内容 |
| variables | JSON | NULL | 模板变量定义 |
| example_values | JSON | NULL | 示例变量值 |
| **作者和权限** |
| author_id | INTEGER | NOT NULL, FK | 作者ID |
| visibility | ENUM | DEFAULT 'PRIVATE' | 可见性 (PRIVATE, TEAM, PUBLIC) |
| team_id | INTEGER | NULL | 团队ID |
| **模板配置** |
| recommended_models | JSON | NULL | 推荐的AI模型 |
| default_parameters | JSON | NULL | 默认参数配置 |
| **统计信息** |
| usage_count | INTEGER | DEFAULT 0 | 使用次数 |
| rating_sum | INTEGER | DEFAULT 0 | 评分总和 |
| rating_count | INTEGER | DEFAULT 0 | 评分次数 |
| last_used_at | DATETIME | NULL | 最后使用时间 |
| **状态** |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| is_featured | BOOLEAN | DEFAULT FALSE | 是否为精选模板 |
| **版本控制** |
| version | VARCHAR(20) | DEFAULT '1.0.0' | 版本号 |
| parent_template_id | INTEGER | NULL, FK | 父模板ID |
| **标签和元数据** |
| tags | JSON | NULL | 标签 |
| template_metadata | JSON | NULL | 元数据 |

#### 模板分类枚举

- `GENERAL`: 通用对话
- `CODE_GENERATION`: 代码生成
- `TEST_CASE`: 测试用例
- `DOCUMENT_WRITING`: 文档写作
- `DATA_ANALYSIS`: 数据分析
- `CREATIVE_WRITING`: 创意写作
- `LEARNING_EDUCATION`: 学习教育
- `PROJECT_MANAGEMENT`: 项目管理

### 5. AI提示词模板使用记录表 (ai_prompt_template_usage)

**表名**: `ai_prompt_template_usage`  
**用途**: 记录提示词模板的使用情况和用户反馈

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| template_id | INTEGER | NOT NULL, FK | 模板ID |
| user_id | INTEGER | NOT NULL, FK | 用户ID |
| **使用信息** |
| ai_provider | VARCHAR(50) | NULL | 使用的AI服务提供商 |
| ai_model | VARCHAR(100) | NULL | 使用的AI模型 |
| use_case | VARCHAR(200) | NULL | 使用场景 |
| **使用结果** |
| success | BOOLEAN | DEFAULT TRUE | 是否成功 |
| tokens_used | INTEGER | NULL | 使用的Token数 |
| response_time | FLOAT | NULL | 响应时间 (秒) |
| **用户反馈** |
| user_rating | INTEGER | NULL | 用户评分 (1-5) |
| user_feedback | TEXT | NULL | 用户反馈 |
| **使用的变量值** |
| variable_values | JSON | NULL | 使用的变量值 |

### 6. AI使用统计表 (ai_usage_stats)

**表名**: `ai_usage_stats`  
**用途**: 按用户和日期统计AI服务的使用情况

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| user_id | INTEGER | NOT NULL, FK | 用户ID |
| date | DATE | NOT NULL | 统计日期 |
| **AI服务信息** |
| ai_provider | VARCHAR(50) | NOT NULL | AI服务提供商 |
| ai_model | VARCHAR(100) | NOT NULL | AI模型 |
| **使用统计** |
| request_count | INTEGER | DEFAULT 0 | 请求次数 |
| success_count | INTEGER | DEFAULT 0 | 成功次数 |
| error_count | INTEGER | DEFAULT 0 | 错误次数 |
| **Token统计** |
| input_tokens | INTEGER | DEFAULT 0 | 输入Token数 |
| output_tokens | INTEGER | DEFAULT 0 | 输出Token数 |
| total_tokens | INTEGER | DEFAULT 0 | 总Token数 |
| **成本统计** |
| total_cost | FLOAT | DEFAULT 0.0 | 总成本 |
| **性能统计** |
| avg_response_time | FLOAT | NULL | 平均响应时间 (秒) |
| min_response_time | FLOAT | NULL | 最小响应时间 (秒) |
| max_response_time | FLOAT | NULL | 最大响应时间 (秒) |
| **使用场景统计** |
| use_case_stats | JSON | NULL | 使用场景统计 |

#### 唯一约束

- `uk_user_date_provider_model`: (user_id, date, ai_provider, ai_model)唯一约束，确保每个用户每天每个模型只有一条统计记录

### 7. AI系统统计表 (ai_system_stats)

**表名**: `ai_system_stats`  
**用途**: 系统级别的AI使用统计，支持按日期和小时统计

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| created_by | INTEGER | NULL | 创建人ID |
| updated_by | INTEGER | NULL | 更新人ID |
| **基本信息** |
| date | DATE | NOT NULL | 统计日期 |
| hour | INTEGER | NULL | 小时 (0-23，用于小时级统计) |
| **系统级统计** |
| total_users | INTEGER | DEFAULT 0 | 总用户数 |
| active_users | INTEGER | DEFAULT 0 | 活跃用户数 |
| total_requests | INTEGER | DEFAULT 0 | 总请求数 |
| total_tokens | INTEGER | DEFAULT 0 | 总Token数 |
| total_cost | FLOAT | DEFAULT 0.0 | 总成本 |
| **各提供商统计** |
| provider_stats | JSON | NULL | 各提供商统计 |
| model_stats | JSON | NULL | 各模型统计 |
| **性能统计** |
| avg_response_time | FLOAT | NULL | 平均响应时间 |
| system_availability | FLOAT | NULL | 系统可用性 |
| **错误统计** |
| error_count | INTEGER | DEFAULT 0 | 错误次数 |
| error_types | JSON | NULL | 错误类型统计 |

#### 唯一约束

- `uk_date_hour`: (date, hour)唯一约束，确保每个时间点只有一条统计记录

## 数据关系图

```
users (用户表)
  ├── ai_chat_sessions (AI聊天会话表)
  │   └── ai_chat_messages (AI聊天消息表)
  ├── ai_prompt_templates (AI提示词模板表)
  │   └── ai_prompt_template_usage (模板使用记录表)
  └── ai_usage_stats (AI使用统计表)

ai_model_configs (AI模型配置表) - 独立表，被其他表引用

ai_system_stats (AI系统统计表) - 系统级统计，独立表
```

## 数据迁移说明

### 迁移文件

- **文件名**: `005_create_ai_assistant_tables.py`
- **版本**: 005_create_ai_assistant_tables
- **依赖**: 004_init_config_data

### 执行迁移

```bash
# 进入后端目录
cd backend

# 执行数据库迁移
alembic upgrade head

# 或者执行到特定版本
alembic upgrade 005_create_ai_assistant_tables
```

### 回滚迁移

```bash
# 回滚到上一个版本
alembic downgrade 004_init_config_data
```

## 性能优化建议

### 1. 索引优化

- 为高频查询字段创建索引
- 考虑复合索引优化多字段查询
- 定期分析查询性能并调整索引

### 2. 分区策略

- 对于大数据量的统计表，考虑按日期分区
- `ai_usage_stats`和`ai_system_stats`表可以按月分区

### 3. 数据清理

- 定期清理过期的会话和消息数据
- 归档历史统计数据
- 实施数据保留策略

### 4. 缓存策略

- 热点数据使用Redis缓存
- AI模型配置信息缓存
- 用户会话上下文缓存

## 安全考虑

### 1. 数据加密

- API密钥字段加密存储
- 敏感用户数据加密
- 传输过程中使用HTTPS

### 2. 访问控制

- 基于用户权限的数据访问控制
- 会话数据隔离
- 审计日志记录

### 3. 数据备份

- 定期数据库备份
- 重要数据多地备份
- 备份数据加密存储

## 监控和维护

### 1. 性能监控

- 数据库查询性能监控
- 表大小和增长趋势监控
- 索引使用情况分析

### 2. 数据质量

- 数据完整性检查
- 异常数据检测
- 数据一致性验证

### 3. 容量规划

- 存储空间使用监控
- 数据增长预测
- 扩容计划制定

## 总结

本数据库设计完全满足AI助手模块的功能需求，包括：

1. **对话管理**: `ai_chat_sessions`和`ai_chat_messages`表支持完整的对话功能
2. **AI服务配置**: `ai_model_configs`表管理多种AI服务提供商和模型
3. **提示词管理**: `ai_prompt_templates`和使用记录表支持模板系统
4. **使用统计**: 多层级的统计表支持成本控制和性能监控

设计遵循了数据库设计的最佳实践，具有良好的扩展性、性能和安全性。