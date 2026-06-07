# 对话上下文管理机制实现文档

## 概述

本文档描述了AI助手模块中对话上下文管理机制的完整实现。该机制负责智能管理AI对话的上下文，包括上下文构建、压缩、缓存和跨模型适配等功能。

## 核心组件

### 1. ContextManager (上下文管理器)

**文件位置**: `backend/src/services/context_manager.py`

**主要职责**:
- 构建和维护对话上下文
- 实现多种智能压缩策略
- 管理消息优先级
- 适配不同AI模型的上下文限制
- 提供上下文统计和分析

**核心功能**:

#### 1.1 模型上下文限制配置
```python
MODEL_LIMITS = {
    "gpt-4": ModelContextLimits(
        model_name="gpt-4",
        max_tokens=8000,
        recommended_tokens=6000,
        compression_strategy=CompressionStrategy.INTELLIGENT_TRUNCATION,
        supports_long_context=False
    ),
    "claude-3-opus": ModelContextLimits(
        model_name="claude-3-opus", 
        max_tokens=200000,
        recommended_tokens=150000,
        compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE,
        supports_long_context=True
    ),
    # ... 其他模型配置
}
```

#### 1.2 压缩策略

**滑动窗口压缩** (`SLIDING_WINDOW`):
- 保留关键消息和最新消息
- 适用于短上下文模型 (如 GPT-3.5-turbo)
- 简单高效，性能好

**智能截断** (`INTELLIGENT_TRUNCATION`):
- 基于消息优先级进行选择性保留
- 适用于中等上下文模型 (如 GPT-4)
- 平衡上下文质量和长度

**摘要压缩** (`SUMMARY_COMPRESSION`):
- 使用AI生成历史对话摘要
- 保留关键信息，压缩冗余内容
- 适用于需要长期记忆的场景

**分层存储** (`HIERARCHICAL_STORAGE`):
- 适用于长上下文模型 (如 Claude-3)
- 分层管理不同重要性的信息
- 最大化利用模型的上下文容量

**模板压缩** (`TEMPLATE_COMPRESSION`):
- 适用于国产AI模型
- 使用模板化方式组织上下文
- 优化中文对话场景

#### 1.3 消息优先级管理

**优先级分类**:
- `CRITICAL`: 关键信息，必须保留 (系统消息、收藏消息)
- `HIGH`: 高优先级 (高评分消息、代码消息、最近消息)
- `MEDIUM`: 中等优先级 (一般消息)
- `LOW`: 低优先级 (错误消息、低评分消息)
- `TEMPORARY`: 临时信息，可随时删除

**优先级确定规则**:
```python
def _determine_message_priority(self, message, metadata):
    if message.is_bookmarked:
        return ContextPriority.CRITICAL
    if message.role == MessageRole.SYSTEM:
        return ContextPriority.CRITICAL
    if message.is_error:
        return ContextPriority.LOW
    if message.user_rating >= 4:
        return ContextPriority.HIGH
    if message.content_type == ContentType.CODE:
        return ContextPriority.HIGH
    # ... 其他规则
```

### 2. ContextCache (上下文缓存)

**文件位置**: `backend/src/services/context_cache.py`

**主要职责**:
- 管理上下文数据的Redis缓存
- 提供高性能的上下文访问
- 实现缓存失效和预加载策略
- 支持上下文数据的序列化和反序列化

**核心功能**:

#### 2.1 缓存键管理
```python
def get_context_cache_key(self, conversation_id: int, ai_model: str = None) -> str:
    if ai_model:
        return f"{self.cache_prefix}conv:{conversation_id}:model:{ai_model}"
    else:
        return f"{self.cache_prefix}conv:{conversation_id}"
```

#### 2.2 上下文序列化
- 使用pickle进行高效序列化
- 支持复杂数据结构的完整保存
- 自动处理枚举类型和日期时间

#### 2.3 缓存策略
- **默认TTL**: 1小时 (活跃对话)
- **压缩内容TTL**: 2小时 (压缩后的上下文)
- **摘要TTL**: 24小时 (对话摘要)
- **自动失效**: 消息更新时自动清理相关缓存

### 3. ConversationServiceSync 集成

**文件位置**: `backend/src/services/conversation_service_sync.py`

**集成功能**:

#### 3.1 上下文获取
```python
def get_conversation_context(self, conversation_id: int, ai_model: str = None):
    # 1. 尝试从缓存获取
    cached_context = self.context_cache.get_cached_context_window(conversation_id, ai_model)
    if cached_context:
        return cached_context
    
    # 2. 从数据库构建上下文
    context_window = self.context_manager.get_conversation_context(...)
    
    # 3. 缓存结果
    self.context_cache.cache_context_window(conversation_id, context_window, ai_model)
    
    return context_window
```

#### 3.2 消息添加时的上下文更新
```python
def add_message(self, conversation_id: int, message: Message):
    # ... 保存消息到数据库
    
    # 更新上下文
    self.context_manager.update_context(conversation_id, saved_message)
    
    # 使相关缓存失效
    self.context_cache.invalidate_conversation_cache(conversation_id)
```

## API接口

### 1. 上下文管理API端点

**文件位置**: `backend/src/api/v1/ai_assistant.py`

#### 1.1 获取对话上下文
```http
GET /api/v1/ai-assistant/conversations/{conversation_id}/context
```

**参数**:
- `ai_model`: 目标AI模型 (可选)
- `max_messages`: 最大消息数量 (可选)
- `include_system_prompt`: 是否包含系统提示词 (默认true)

**响应**:
```json
{
  "conversation_id": 123,
  "messages": [...],
  "summary": "对话摘要",
  "token_count": 1500,
  "compression_strategy": "intelligent_truncation"
}
```

#### 1.2 获取上下文摘要
```http
GET /api/v1/ai-assistant/conversations/{conversation_id}/context/summary
```

#### 1.3 获取上下文统计
```http
GET /api/v1/ai-assistant/conversations/{conversation_id}/context/stats
```

#### 1.4 标记重要消息
```http
POST /api/v1/ai-assistant/conversations/{conversation_id}/messages/{message_id}/mark-important
```

#### 1.5 获取格式化上下文
```http
GET /api/v1/ai-assistant/conversations/{conversation_id}/context/formatted?ai_model=gpt-4
```

#### 1.6 预加载上下文缓存
```http
POST /api/v1/ai-assistant/conversations/{conversation_id}/context/preload
```

#### 1.7 获取缓存信息
```http
GET /api/v1/ai-assistant/conversations/{conversation_id}/context/cache-info
```

## 数据模型

### 1. ContextWindow (上下文窗口)
```python
@dataclass
class ContextWindow:
    messages: List[ContextMessage]
    total_tokens: int
    max_tokens: int
    compression_strategy: CompressionStrategy
    summary: Optional[str] = None
    compressed_content: Optional[str] = None
```

### 2. ContextMessage (上下文消息)
```python
@dataclass
class ContextMessage:
    id: int
    role: MessageRole
    content: str
    content_type: ContentType
    timestamp: datetime
    tokens: int
    priority: ContextPriority
    is_bookmarked: bool
    metadata: Dict[str, Any]
```

### 3. ModelContextLimits (模型上下文限制)
```python
@dataclass
class ModelContextLimits:
    model_name: str
    max_tokens: int
    recommended_tokens: int
    compression_strategy: CompressionStrategy
    supports_long_context: bool
```

## 使用示例

### 1. 基本上下文获取
```python
from src.services.conversation_service_sync import ConversationServiceSync

# 创建服务实例
service = ConversationServiceSync(db)

# 获取对话上下文
context_window = service.get_conversation_context(
    conversation_id=123,
    ai_model="gpt-4",
    max_messages=50
)

print(f"上下文包含 {len(context_window.messages)} 条消息")
print(f"总Token数: {context_window.total_tokens}")
print(f"压缩策略: {context_window.compression_strategy}")
```

### 2. 格式化为AI输入
```python
# 获取格式化的上下文
formatted_context = service.format_context_for_ai(
    conversation_id=123,
    ai_model="gpt-4"
)

# 直接用于AI API调用
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=formatted_context + [{"role": "user", "content": "新问题"}]
)
```

### 3. 标记重要消息
```python
# 标记消息为重要，提高其在上下文中的优先级
success = service.mark_message_important(message_id=456)
if success:
    print("消息已标记为重要")
```

### 4. 预加载缓存
```python
# 为多个AI模型预加载上下文缓存
success = service.preload_context_cache(
    conversation_id=123,
    ai_models=["gpt-4", "claude-3-opus", "gpt-3.5-turbo"]
)
```

## 性能优化

### 1. 缓存策略
- **多层缓存**: Redis缓存 + 内存缓存
- **智能失效**: 消息更新时精确失效相关缓存
- **预加载**: 支持批量预加载热点对话的上下文
- **压缩存储**: 使用pickle压缩存储复杂对象

### 2. 数据库优化
- **索引优化**: 对话ID、创建时间、消息角色等关键字段建立索引
- **分页查询**: 支持大量消息的分页加载
- **批量操作**: 批量获取和处理消息

### 3. 算法优化
- **Token估算**: 快速的Token数量估算算法
- **优先级计算**: 高效的消息优先级计算
- **压缩算法**: 针对不同场景优化的压缩策略

## 测试覆盖

### 1. 单元测试
**文件**: `backend/test_context_management.py`

**测试覆盖**:
- 模型限制配置测试
- Token估算准确性测试
- 消息优先级确定测试
- 各种压缩策略测试
- 上下文窗口构建测试
- 缓存序列化/反序列化测试

### 2. 集成测试
**文件**: `backend/test_context_integration.py`

**测试覆盖**:
- 对话服务集成测试
- 缓存机制集成测试
- API端点功能测试
- 完整工作流测试

### 3. 测试运行
```bash
# 运行所有上下文管理相关测试
python -m pytest backend/test_context_management.py -v
python -m pytest backend/test_context_integration.py -v

# 运行特定测试类
python -m pytest backend/test_context_management.py::TestContextManager -v
```

## 配置说明

### 1. Redis配置
```python
# 在 settings 中配置Redis连接
REDIS_URL = "redis://localhost:6379/0"

# 上下文缓存配置
CONTEXT_CACHE_TTL = 3600  # 1小时
CONTEXT_SUMMARY_TTL = 86400  # 24小时
```

### 2. 模型配置
```python
# 可以通过配置文件或环境变量调整模型限制
AI_MODEL_LIMITS = {
    "gpt-4": {
        "max_tokens": 8000,
        "recommended_tokens": 6000,
        "compression_strategy": "intelligent_truncation"
    }
}
```

## 监控和日志

### 1. 关键指标
- 上下文构建时间
- 缓存命中率
- 压缩效果 (压缩前后Token数对比)
- 内存使用情况
- API响应时间

### 2. 日志记录
```python
# 关键操作都有详细日志
logger.info(f"Built context with {len(messages)} messages, {total_tokens} tokens")
logger.debug(f"Cache hit for conversation {conversation_id}")
logger.warning(f"Context compression reduced tokens from {before} to {after}")
```

## 故障排除

### 1. 常见问题

**问题**: 上下文获取缓慢
**解决**: 检查Redis连接，启用缓存预加载

**问题**: 压缩效果不佳
**解决**: 调整压缩策略，检查消息优先级设置

**问题**: 缓存占用过多内存
**解决**: 调整TTL设置，清理过期缓存

### 2. 调试工具
```python
# 获取上下文统计信息
stats = service.get_context_statistics(conversation_id)
print(f"消息分布: {stats['role_distribution']}")
print(f"优先级分布: {stats['priority_distribution']}")

# 获取缓存信息
cache_info = service.get_cache_info(conversation_id)
print(f"缓存键数量: {len(cache_info['cache_keys'])}")
```

## 扩展性

### 1. 新增压缩策略
```python
def _custom_compression(self, context_window, model_limits):
    # 实现自定义压缩逻辑
    pass

# 在压缩方法中添加新策略
if strategy == CompressionStrategy.CUSTOM:
    return self._custom_compression(context_window, model_limits)
```

### 2. 新增AI模型支持
```python
# 在MODEL_LIMITS中添加新模型配置
MODEL_LIMITS["new-model"] = ModelContextLimits(
    model_name="new-model",
    max_tokens=16000,
    recommended_tokens=12000,
    compression_strategy=CompressionStrategy.INTELLIGENT_TRUNCATION,
    supports_long_context=True
)
```

### 3. 自定义缓存后端
```python
class CustomContextCache(ContextCache):
    def __init__(self, custom_backend):
        self.backend = custom_backend
    
    def cache_context_window(self, conversation_id, context_window):
        # 使用自定义缓存后端
        pass
```

## 总结

对话上下文管理机制是AI助手模块的核心功能之一，通过智能的上下文构建、压缩和缓存策略，为不同AI模型提供了优化的上下文管理能力。该实现具有以下特点：

1. **智能化**: 多种压缩策略适应不同场景
2. **高性能**: 多层缓存和优化算法
3. **可扩展**: 支持新模型和自定义策略
4. **可靠性**: 完整的测试覆盖和错误处理
5. **易用性**: 简洁的API和丰富的配置选项

该机制为AI助手提供了强大的上下文管理能力，确保AI能够在各种场景下获得最优的上下文信息，从而提供更准确和连贯的回复。