# AI助手用户权限集成实现文档

## 概述

本文档描述了AI助手模块与主系统用户权限体系的集成实现。通过这个集成，AI助手的所有功能都受到统一的权限控制，确保系统安全性和用户访问控制的一致性。

## 实现架构

### 1. 权限服务层
```
AIPermissionService
├── 权限定义和管理
├── 用户权限检查
├── 权限统计分析
└── 权限验证逻辑
```

### 2. 权限装饰器层
```
ai_permission.py
├── @ai_permission_required 装饰器
├── AIPermissionChecker 检查器类
├── 权限中间件
└── 便捷检查函数
```

### 3. 服务集成层
```
AIAssistantService (更新)
├── 集成权限检查
├── 基于权限的模型选择
├── 操作权限验证
└── 权限感知的功能调用
```

## 权限体系设计

### 权限分类

#### 1. 基础权限
- **ai_chat_basic**: AI基础对话权限
- **ai_chat_advanced**: AI高级对话权限

#### 2. 会话管理权限
- **ai_session_create**: 创建AI会话
- **ai_session_read**: 查看AI会话
- **ai_session_update**: 编辑AI会话
- **ai_session_delete**: 删除AI会话

#### 3. 模型使用权限
- **ai_model_gpt4**: 使用GPT-4系列模型
- **ai_model_claude**: 使用Claude系列模型
- **ai_model_chinese**: 使用中文AI模型（文心一言、通义千问等）

#### 4. 提示词模板权限
- **ai_template_read**: 查看提示词模板
- **ai_template_create**: 创建提示词模板
- **ai_template_update**: 编辑提示词模板
- **ai_template_delete**: 删除提示词模板
- **ai_template_share**: 分享提示词模板

#### 5. 管理权限
- **ai_admin_config**: AI配置管理
- **ai_admin_monitor**: AI使用监控
- **ai_admin_quota**: AI配额管理

#### 6. 高级功能权限
- **ai_suggestion_generate**: 生成智能建议
- **ai_analysis_advanced**: 高级分析功能
- **ai_file_upload**: AI文件上传

### 权限层级

```
超级管理员 (super_admin)
├── 所有AI权限
└── 系统管理权限

系统管理员 (admin)
├── AI管理权限
├── AI监控权限
└── AI配额管理权限

高级用户 (advanced_user)
├── 高级对话权限
├── 高级模型权限
├── 智能建议权限
└── 高级分析权限

标准用户 (user)
├── 基础对话权限
├── 会话管理权限
├── 中文模型权限
└── 模板管理权限

受限用户 (limited_user)
├── 基础对话权限
└── 会话查看权限
```

## 核心实现

### 1. 权限服务 (AIPermissionService)

```python
class AIPermissionService:
    """AI助手权限管理服务"""
    
    async def check_user_ai_permission(self, user_id: int, permission_code: str) -> Tuple[bool, str]:
        """检查用户是否有指定的AI权限"""
        
    async def check_ai_chat_permission(self, user_id: int, advanced: bool = False) -> Tuple[bool, str]:
        """检查用户AI对话权限"""
        
    async def check_ai_model_permission(self, user_id: int, model_provider: str) -> Tuple[bool, str]:
        """检查用户AI模型使用权限"""
        
    async def validate_ai_operation_permission(self, user_id: int, operation: str, **kwargs) -> None:
        """验证AI操作权限，如果无权限则抛出异常"""
```

### 2. 权限装饰器

```python
@ai_permission_required("chat_basic")
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建聊天会话 - 需要基础聊天权限"""
    pass

@ai_permission_required("model_use", model_provider="openai")
async def use_gpt4_model(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """使用GPT-4模型 - 需要GPT-4使用权限"""
    pass
```

### 3. 服务集成

```python
class AIAssistantService:
    async def process_user_query(self, query: UserQuery, user_id: Optional[int] = None) -> AIResponse:
        # 权限检查
        if user_id and self.permission_service:
            await self.permission_service.validate_ai_operation_permission(
                user_id, "chat_basic"
            )
        
        # 选择AI服务时考虑权限
        selected_provider = await self._select_ai_provider(query, task_type, user_id)
        
        # 检查模型使用权限
        if user_id and self.permission_service:
            await self.permission_service.validate_ai_operation_permission(
                user_id, "model_use", model_provider=selected_provider.value
            )
```

## API接口

### 权限管理API

```
POST /api/v1/ai-permissions/initialize
- 初始化AI权限（管理员）

GET /api/v1/ai-permissions/me
- 获取当前用户AI权限

GET /api/v1/ai-permissions/user/{user_id}
- 获取指定用户AI权限（管理员）

POST /api/v1/ai-permissions/check
- 检查AI操作权限

GET /api/v1/ai-permissions/stats
- 获取AI权限统计（管理员）

GET /api/v1/ai-permissions/available-models
- 获取用户可用的AI模型

GET /api/v1/ai-permissions/features
- 获取用户可用的AI功能
```

## 数据库设计

### 权限表扩展

AI权限作为系统权限的一部分，存储在现有的 `permissions` 表中：

```sql
-- AI权限示例
INSERT INTO permissions (code, name, description, module, type, resource, action) VALUES
('ai_chat_basic', 'AI基础对话', '允许用户进行基础AI对话', 'ai_assistant', 'FUNCTION', 'ai_chat', 'basic_chat'),
('ai_model_gpt4', '使用GPT-4模型', '允许用户使用GPT-4系列模型', 'ai_assistant', 'FUNCTION', 'ai_model', 'use_gpt4');
```

### 角色权限关联

通过现有的 `role_permissions` 表关联角色和AI权限：

```sql
-- 为超级管理员分配所有AI权限
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.code = 'super_admin' AND p.module = 'ai_assistant';

-- 为标准用户分配基础AI权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'user' AND p.code IN ('ai_chat_basic', 'ai_session_create', 'ai_model_chinese');
```

## 安全特性

### 1. 多层权限验证
- API层权限检查（装饰器）
- 服务层权限验证（业务逻辑）
- 数据层权限控制（资源访问）

### 2. 权限继承
- 超级用户自动拥有所有权限
- 角色权限继承机制
- 权限组合和叠加

### 3. 动态权限检查
- 运行时权限验证
- 权限变更实时生效
- 会话级权限缓存

### 4. 审计和监控
- 权限检查日志记录
- 权限使用统计
- 异常权限访问告警

## 使用示例

### 1. 检查用户权限

```python
from src.services.ai_permission_service import AIPermissionService

async def check_user_permissions(user_id: int, db: AsyncSession):
    ai_permission_service = AIPermissionService(db)
    
    # 检查基础聊天权限
    has_chat, message = await ai_permission_service.check_ai_chat_permission(user_id)
    print(f"聊天权限: {has_chat} - {message}")
    
    # 检查模型使用权限
    has_gpt4, message = await ai_permission_service.check_ai_model_permission(user_id, "openai")
    print(f"GPT-4权限: {has_gpt4} - {message}")
```

### 2. 使用权限装饰器

```python
from src.decorators.ai_permission import ai_permission_required

@router.post("/chat")
@ai_permission_required("chat_basic")
async def create_chat(
    message: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 这里的代码只有在用户有chat_basic权限时才会执行
    return {"message": "Chat created successfully"}
```

### 3. 服务层权限验证

```python
from src.services.ai_assistant_service import AIAssistantService

async def process_ai_request(user_id: int, query: str):
    ai_service = AIAssistantService(db)
    
    # 服务会自动检查用户权限
    response = await ai_service.process_user_query(
        UserQuery(content=query, user_id=user_id),
        user_id=user_id
    )
    
    return response
```

## 测试验证

### 运行集成测试

```bash
cd backend
python test_ai_permission_integration.py
```

### 测试覆盖范围

1. **权限初始化测试**: 验证AI权限正确创建和配置
2. **用户权限检查测试**: 验证各种权限检查功能
3. **权限统计测试**: 验证权限使用统计功能
4. **权限验证测试**: 验证权限验证逻辑

## 部署说明

### 1. 数据库迁移

```bash
# 运行AI权限迁移
alembic upgrade head
```

### 2. 权限初始化

系统启动时会自动初始化AI权限，也可以手动调用：

```python
from src.services.ai_permission_init_service import AIPermissionInitService

# 确保AI权限存在
result = await AIPermissionInitService.ensure_ai_permissions()
```

### 3. 角色配置

根据业务需求为不同角色分配适当的AI权限：

```sql
-- 为高级用户角色添加高级AI权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.code = 'advanced_user' 
AND p.code IN ('ai_chat_advanced', 'ai_model_gpt4', 'ai_suggestion_generate');
```

## 维护和监控

### 1. 权限使用监控

```python
# 获取权限使用统计
stats = await ai_permission_service.get_ai_permission_usage_stats()
print(f"总AI权限数: {stats['summary']['total_ai_permissions']}")
print(f"活跃权限数: {stats['summary']['active_permissions']}")
```

### 2. 用户权限审计

```python
# 获取用户权限详情
user_permissions = await ai_permission_service.get_user_ai_permissions(user_id)
print(f"用户拥有权限数: {user_permissions['summary']['granted_permissions']}")
```

### 3. 权限问题排查

```python
# 检查特定操作权限
has_permission, message = await ai_permission_service.check_user_ai_permission(
    user_id, "ai_chat_advanced"
)
if not has_permission:
    print(f"权限检查失败: {message}")
```

## 总结

AI助手用户权限集成实现了以下目标：

1. **统一权限管理**: AI功能完全集成到现有权限体系
2. **细粒度控制**: 支持功能级、操作级、资源级权限控制
3. **安全保障**: 多层权限验证确保系统安全
4. **易于维护**: 清晰的权限结构和完善的管理工具
5. **可扩展性**: 支持新增AI功能和权限类型

通过这个集成，AI助手模块成为了主系统权限体系的有机组成部分，为用户提供了安全、可控的AI服务体验。