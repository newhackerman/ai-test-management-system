# 需求管理高级功能API文档

## 概述

本文档描述了需求管理模块的高级功能API接口，包括评审管理、变更管理和追溯分析三个核心功能模块。

## API模块统计

- **需求管理API**: 19个端点
- **需求评审API**: 15个端点  
- **需求变更API**: 11个端点
- **需求追溯API**: 10个端点
- **总计**: 55个API端点

## 1. 需求评审管理API

### 基础路径: `/api/v1/requirement-reviews`

#### 核心功能

1. **创建评审** - `POST /`
   - 创建新的需求评审
   - 支持正式评审、非正式评审、走查、检查等类型
   - 指定评审主持人和评审人员

2. **开始评审** - `POST /{review_id}/start`
   - 由评审主持人启动评审流程
   - 更新评审状态为进行中

3. **提交评审意见** - `POST /comments`
   - 评审人员提交评审意见
   - 支持问题、建议、疑问、批准、拒绝等类型
   - 包含严重程度分级

4. **解决评审意见** - `PUT /comments/{comment_id}/resolve`
   - 处理和解决评审意见
   - 记录解决方案和处理人

5. **完成评审** - `POST /{review_id}/complete`
   - 评审主持人完成评审并做出决策
   - 支持批准、有条件批准、需要重大修改、拒绝等决策

6. **取消评审** - `POST /{review_id}/cancel`
   - 取消正在进行的评审

#### 查询功能

- **获取评审详情** - `GET /{review_id}`
- **获取评审列表** - `GET /`
- **获取需求的所有评审** - `GET /requirements/{requirement_id}/reviews`
- **获取评审意见列表** - `GET /{review_id}/comments`
- **获取用户评审列表** - `GET /users/{user_id}/reviews`
- **获取评审统计信息** - `GET /statistics`

#### 批量操作

- **批量解决评审意见** - `POST /comments/batch-resolve`

#### 通知和导出

- **发送评审通知** - `POST /{review_id}/notifications`
- **导出评审数据** - `POST /export`

## 2. 需求变更管理API

### 基础路径: `/api/v1/requirement-changes`

#### 核心功能

1. **创建变更请求** - `POST /`
   - 创建需求变更请求
   - 支持新增、修改、删除、澄清等变更类型
   - 自动进行影响分析

2. **获取变更请求详情** - `GET /{change_request_id}`
   - 获取变更请求的详细信息

3. **更新变更请求** - `PUT /{change_request_id}`
   - 更新变更请求信息

4. **审批变更请求** - `POST /{change_request_id}/approve`
   - 审批变更请求
   - 支持批准、拒绝等状态
   - 可指定实施人员

5. **实施变更** - `POST /{change_request_id}/implement`
   - 实施已批准的变更
   - 记录实施说明和实际工作量

#### 查询功能

- **获取需求的变更请求** - `GET /requirement/{requirement_id}`
- **获取待审批的变更请求** - `GET /pending-approvals`
- **搜索变更请求** - `GET /search`
- **获取变更统计信息** - `GET /statistics`

#### 影响分析

- **分析变更影响** - `POST /impact-analysis`
  - 全面的变更影响分析
  - 支持多维度分析（技术、业务、时间、成本）
  - 可配置分析深度

- **快速影响分析** - `GET /impact-analysis/{requirement_id}`
  - 基于需求ID的快速影响分析

## 3. 需求追溯分析API

### 基础路径: `/api/v1/requirement-traceability`

#### 追溯链接管理

1. **创建追溯链接** - `POST /links`
   - 在对象间建立追溯关系
   - 支持派生、实现、测试、验证、细化等链接类型

2. **获取追溯链接详情** - `GET /links/{link_id}`
   - 获取追溯链接的详细信息

3. **删除追溯链接** - `DELETE /links/{link_id}`
   - 删除指定的追溯链接

4. **搜索追溯链接** - `GET /links`
   - 根据条件搜索追溯链接

#### 追溯分析

1. **获取需求追溯关系** - `GET /requirements/{requirement_id}`
   - 获取需求的完整追溯关系
   - 支持上游、下游、双向追溯
   - 包含覆盖率分析

2. **生成追溯矩阵** - `POST /matrix`
   - 生成项目的追溯矩阵
   - 支持需求到测试、需求到任务等矩阵类型
   - 包含覆盖率统计

3. **分析变更影响** - `POST /impact-analysis`
   - 基于追溯关系分析变更影响
   - 识别直接和间接影响
   - 提供风险评估和建议

#### 质量分析

- **获取追溯覆盖率** - `GET /coverage/{project_id}`
- **获取孤立需求** - `GET /orphaned-requirements/{project_id}`
- **检查追溯一致性** - `GET /consistency-check/{project_id}`

## 4. 集成测试

### 测试覆盖范围

已实现完整的集成测试，覆盖以下场景：

#### 需求评审测试
- 创建评审流程测试
- 获取评审详情测试
- 提交评审意见测试
- 完成评审决策测试

#### 需求变更测试
- 创建变更请求测试
- 获取变更请求详情测试
- 审批变更请求测试
- 变更影响分析测试

#### 需求追溯测试
- 创建追溯链接测试
- 获取需求追溯关系测试
- 生成追溯矩阵测试
- 变更影响分析测试
- 获取追溯覆盖率测试
- 获取孤立需求测试
- 检查追溯一致性测试

### 测试执行

```bash
# 运行集成测试
python -m pytest src/tests/test_requirement_advanced_apis.py -v

# 运行简单API测试
python test_advanced_apis_simple.py
```

## 5. 技术特性

### 认证和授权
- 所有API端点都需要用户认证
- 基于JWT令牌的身份验证
- 支持基于角色的访问控制

### 数据验证
- 使用Pydantic进行请求数据验证
- 完整的错误处理和响应
- 支持多种数据格式验证

### 异步处理
- 基于FastAPI的异步API设计
- 支持高并发请求处理
- 异步数据库操作

### 错误处理
- 统一的异常处理机制
- 详细的错误信息返回
- 支持多语言错误消息

### 性能优化
- 数据库查询优化
- 支持分页和排序
- 缓存机制集成

## 6. 使用示例

### 创建需求评审

```python
import httpx

# 创建评审请求
review_data = {
    "requirement_id": 1,
    "review_type": "FORMAL",
    "title": "需求评审",
    "description": "对需求进行正式评审",
    "moderator_id": 1,
    "reviewers": [2, 3, 4],
    "scheduled_date": "2024-12-04T10:00:00"
}

response = httpx.post(
    "http://localhost:8000/api/v1/requirement-reviews/",
    json=review_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

### 创建变更请求

```python
# 创建变更请求
change_data = {
    "requirement_id": 1,
    "title": "需求功能增强",
    "description": "增加新的功能模块",
    "reason": "客户需求变更",
    "change_type": "ADDITION",
    "priority": "HIGH"
}

response = httpx.post(
    "http://localhost:8000/api/v1/requirement-changes/",
    json=change_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

### 创建追溯链接

```python
# 创建追溯链接
link_data = {
    "source_type": "requirement",
    "source_id": 1,
    "target_type": "test_case",
    "target_id": 10,
    "link_type": "TESTS",
    "description": "测试用例验证需求"
}

response = httpx.post(
    "http://localhost:8000/api/v1/requirement-traceability/links",
    json=link_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

## 7. 部署说明

### 依赖要求
- Python 3.8+
- FastAPI
- SQLAlchemy
- Pydantic
- 其他依赖见requirements.txt

### 配置要求
- 数据库连接配置
- JWT密钥配置
- 日志配置
- 缓存配置

### 启动服务
```bash
# 开发环境
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 8. 后续扩展

### 计划功能
- 需求模板管理
- 需求导入导出
- 需求报告生成
- 需求分析仪表板
- 实时协作功能

### 性能优化
- 数据库索引优化
- 查询缓存机制
- 异步任务处理
- 分布式部署支持

---

**文档版本**: 1.0  
**最后更新**: 2024-12-03  
**维护人员**: AI测试管理系统开发团队