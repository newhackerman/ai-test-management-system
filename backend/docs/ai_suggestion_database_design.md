# AI建议系统数据库设计文档

## 概述

本文档描述了AI助手模块中建议系统的数据库设计，包括三个核心表：
- `ai_suggestions` - AI建议表
- `ai_requirements_analysis` - 需求分析表  
- `ai_requirements_suggestions` - 需求建议表

## 数据库表设计

### 1. AI建议表 (ai_suggestions)

**用途**: 存储AI生成的各类建议信息

**主要字段**:
- `id`: 主键ID
- `title`: 建议标题
- `description`: 建议描述
- `type`: 建议类型（枚举）
- `category`: 建议分类（枚举）
- `status`: 建议状态（枚举）
- `priority`: 优先级（枚举）
- `user_id`: 用户ID（外键）
- `project_id`: 项目ID（预留）
- `session_id`: 会话ID（外键，可选）
- `ai_provider`: AI服务提供商
- `ai_model`: AI模型名称
- `confidence_score`: 置信度分数
- `action_items`: 行动项列表（JSON）
- `expected_benefit`: 预期收益
- `estimated_effort`: 预估工作量
- `user_rating`: 用户评分（1-5）
- `implemented_at`: 实施时间
- `suggestion_metadata`: 建议元数据（JSON）

**枚举类型**:
- `SuggestionType`: QUALITY_IMPROVEMENT, TEST_IMPROVEMENT, AUTOMATION_IMPROVEMENT, PROJECT_MANAGEMENT, COVERAGE_IMPROVEMENT, URGENT_FIX, OPTIMIZATION
- `SuggestionStatus`: PENDING, ACCEPTED, REJECTED, IMPLEMENTED, CANCELLED
- `SuggestionPriority`: CRITICAL, HIGH, MEDIUM, LOW
- `SuggestionCategory`: COMPLETENESS, CLARITY, TESTABILITY, PROBLEMATIC_REQUIREMENTS, FUNCTIONAL_COVERAGE, NONFUNCTIONAL_COVERAGE, PERFORMANCE, SECURITY, MAINTAINABILITY

**索引**:
- `idx_ai_suggestions_user_id`: 用户ID索引
- `idx_ai_suggestions_type`: 建议类型索引
- `idx_ai_suggestions_status`: 建议状态索引
- `idx_ai_suggestions_priority`: 优先级索引
- `idx_ai_suggestions_category`: 建议分类索引
- `idx_ai_suggestions_project_id`: 项目ID索引
- `idx_ai_suggestions_session_id`: 会话ID索引
- `idx_ai_suggestions_ai_provider`: AI提供商索引
- `idx_ai_suggestions_created_at`: 创建时间索引

### 2. 需求分析表 (ai_requirements_analysis)

**用途**: 存储AI对需求进行分析的结果

**主要字段**:
- `id`: 主键ID
- `analysis_name`: 分析名称
- `description`: 分析描述
- `user_id`: 用户ID（外键）
- `project_id`: 项目ID（预留）
- `session_id`: 会话ID（外键，可选）
- `ai_provider`: AI服务提供商
- `ai_model`: AI模型名称
- `analysis_prompt`: 分析提示词
- `completeness_score`: 完整性得分
- `clarity_score`: 清晰度得分
- `consistency_score`: 一致性得分
- `testability_score`: 可测试性得分
- `overall_score`: 总体得分
- `total_requirements`: 需求总数
- `analyzed_requirements`: 已分析需求数
- `problematic_requirements_count`: 问题需求数
- `analysis_status`: 分析状态（枚举）
- `progress`: 分析进度（0-1）
- `analysis_results`: 详细分析结果（JSON）
- `identified_issues`: 识别的问题（JSON）
- `improvement_areas`: 改进领域（JSON）
- `started_at`: 开始分析时间
- `completed_at`: 完成分析时间

**枚举类型**:
- `AnalysisStatus`: PENDING, ANALYZING, COMPLETED, FAILED

**索引**:
- `idx_ai_requirements_analysis_user_id`: 用户ID索引
- `idx_ai_requirements_analysis_project_id`: 项目ID索引
- `idx_ai_requirements_analysis_session_id`: 会话ID索引
- `idx_ai_requirements_analysis_status`: 分析状态索引
- `idx_ai_requirements_analysis_ai_provider`: AI提供商索引
- `idx_ai_requirements_analysis_created_at`: 创建时间索引
- `idx_ai_requirements_analysis_completed_at`: 完成时间索引

### 3. 需求建议表 (ai_requirements_suggestions)

**用途**: 存储基于需求分析生成的具体建议

**主要字段**:
- `id`: 主键ID
- `title`: 建议标题
- `description`: 建议描述
- `suggestion_type`: 建议类型（枚举）
- `category`: 建议分类（枚举）
- `analysis_id`: 分析ID（外键）
- `requirement_id`: 需求ID（预留）
- `user_id`: 用户ID（外键）
- `priority`: 优先级（枚举）
- `status`: 建议状态（枚举）
- `action_items`: 行动项列表（JSON）
- `expected_benefit`: 预期收益
- `estimated_effort`: 预估工作量
- `identified_issues`: 识别的问题（JSON）
- `severity`: 问题严重程度（枚举）
- `ai_provider`: AI服务提供商
- `ai_model`: AI模型名称
- `confidence_score`: 置信度分数
- `generation_prompt`: 生成提示词
- `user_rating`: 用户评分（1-5）
- `is_accepted`: 是否被接受
- `implemented_at`: 实施时间
- `implementation_notes`: 实施说明

**枚举类型**:
- `IssueSeverity`: LOW, MEDIUM, HIGH, CRITICAL

**索引**:
- `idx_ai_requirements_suggestions_analysis_id`: 分析ID索引
- `idx_ai_requirements_suggestions_user_id`: 用户ID索引
- `idx_ai_requirements_suggestions_requirement_id`: 需求ID索引
- `idx_ai_requirements_suggestions_type`: 建议类型索引
- `idx_ai_requirements_suggestions_status`: 建议状态索引
- `idx_ai_requirements_suggestions_priority`: 优先级索引
- `idx_ai_requirements_suggestions_category`: 建议分类索引
- `idx_ai_requirements_suggestions_severity`: 严重程度索引
- `idx_ai_requirements_suggestions_ai_provider`: AI提供商索引
- `idx_ai_requirements_suggestions_created_at`: 创建时间索引

## 表关系设计

### 关系图

```
ai_chat_sessions (1) -----> (N) ai_suggestions
ai_chat_sessions (1) -----> (N) ai_requirements_analysis
ai_requirements_analysis (1) -----> (N) ai_requirements_suggestions

users (1) -----> (N) ai_suggestions
users (1) -----> (N) ai_requirements_analysis
users (1) -----> (N) ai_requirements_suggestions
```

### 外键约束

1. **ai_suggestions表**:
   - `user_id` → `users.id` (CASCADE DELETE)
   - `session_id` → `ai_chat_sessions.id` (SET NULL)

2. **ai_requirements_analysis表**:
   - `user_id` → `users.id` (CASCADE DELETE)
   - `session_id` → `ai_chat_sessions.id` (SET NULL)

3. **ai_requirements_suggestions表**:
   - `analysis_id` → `ai_requirements_analysis.id` (CASCADE DELETE)
   - `user_id` → `users.id` (CASCADE DELETE)

## 数据流程

### 1. 建议生成流程

```
用户请求 → AI分析 → 生成建议 → 存储到ai_suggestions表 → 用户反馈 → 更新状态
```

### 2. 需求分析流程

```
用户上传需求 → 创建分析记录 → AI分析需求 → 更新分析结果 → 生成具体建议 → 存储到ai_requirements_suggestions表
```

### 3. 建议实施流程

```
用户查看建议 → 接受/拒绝建议 → 实施建议 → 记录实施结果 → 评价建议效果
```

## 查询优化

### 常用查询模式

1. **按用户查询建议**:
   ```sql
   SELECT * FROM ai_suggestions WHERE user_id = ? ORDER BY created_at DESC;
   ```

2. **按项目查询分析**:
   ```sql
   SELECT * FROM ai_requirements_analysis WHERE project_id = ? AND analysis_status = 'COMPLETED';
   ```

3. **查询高优先级建议**:
   ```sql
   SELECT * FROM ai_suggestions WHERE priority IN ('CRITICAL', 'HIGH') AND status = 'PENDING';
   ```

4. **统计分析结果**:
   ```sql
   SELECT 
     AVG(overall_score) as avg_score,
     COUNT(*) as total_analyses,
     SUM(problematic_requirements_count) as total_issues
   FROM ai_requirements_analysis 
   WHERE analysis_status = 'COMPLETED';
   ```

### 性能优化建议

1. **索引优化**: 已为常用查询字段创建索引
2. **分区策略**: 可考虑按时间分区存储历史数据
3. **缓存策略**: 对频繁查询的统计数据进行缓存
4. **归档策略**: 定期归档旧的分析和建议数据

## 扩展性设计

### 预留字段

1. **project_id**: 为将来的项目管理功能预留
2. **requirement_id**: 为将来的需求管理功能预留
3. **metadata字段**: 使用JSON格式存储扩展信息

### 可扩展的枚举

所有枚举类型都可以通过数据库迁移进行扩展，支持新的建议类型、状态和分类。

### 插件化支持

通过metadata字段可以支持不同类型的AI服务和自定义分析算法。

## 数据安全

### 权限控制

1. **用户隔离**: 通过user_id确保用户只能访问自己的数据
2. **软删除**: 重要数据采用软删除策略
3. **审计日志**: 继承基础模型的审计功能

### 数据加密

1. **敏感字段**: 可对AI提示词等敏感信息进行加密存储
2. **传输加密**: 所有数据传输使用HTTPS
3. **访问控制**: 基于角色的访问控制

## 监控指标

### 业务指标

1. **建议生成量**: 每日/每月生成的建议数量
2. **建议采纳率**: 被接受和实施的建议比例
3. **用户满意度**: 基于用户评分的满意度统计
4. **分析完成率**: 成功完成的分析比例

### 技术指标

1. **查询性能**: 各类查询的响应时间
2. **存储增长**: 数据存储量的增长趋势
3. **AI调用成本**: AI服务的使用成本统计
4. **错误率**: 分析和建议生成的错误率

## 总结

本数据库设计支持AI助手模块的核心功能：
- ✅ 智能建议生成和管理
- ✅ 需求质量分析
- ✅ 用户反馈和评价
- ✅ 实施跟踪和效果评估
- ✅ 多AI服务支持
- ✅ 扩展性和可维护性

设计遵循了数据库设计的最佳实践，具有良好的性能、安全性和可扩展性。