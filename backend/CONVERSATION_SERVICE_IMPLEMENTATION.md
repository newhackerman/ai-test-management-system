# ConversationService 对话管理服务实现文档

## 概述

ConversationService 是 AI 助手模块的核心对话管理服务，负责管理 AI 对话会话的完整生命周期，包括会话创建、消息管理、上下文处理、智能压缩、导出分享等功能。

## 核心特性

### 1. 智能会话管理
- **会话模板系统**: 支持多种预定义模板（代码助手、测试专家、文档写作等）
- **智能标题生成**: 根据模板类型和目标自动生成有意义的标题
- **会话分组管理**: 支持工作、学习、项目等分组
- **标签系统**: 支持自定义标签和自动标签
- **会话统计**: 消息数、Token消耗、使用时长等统计信息

### 2. 智能上下文管理
- **多模型适配**: 针对不同AI模型的上下文策略
- **智能压缩**: 多种压缩策略（滑动窗口、智能截断、关键信息提取等）
- **重要消息保留**: 自动识别和保留重要消息
- **上下文摘要**: 自动生成对话摘要
- **跨会话引用**: 支持引用其他会话内容

### 3. 高级会话操作
- **会话分支**: 从指定消息点创建分支对话
- **会话合并**: 将多个相关会话合并
- **会话导出**: 支持 Markdown、JSON、TXT 格式导出
- **会话分享**: 生成安全的分享链接
- **批量操作**: 支持批量重命名、标签管理等

## 技术架构

### 类结构

```python
class ConversationService:
    """对话管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.max_context_messages = 50
        self.context_token_limit = 8000
        self.model_context_strategies = {...}  # 模型特定策略
```

### 核心枚举

```python
class ContextCompressionStrategy(str, Enum):
    """上下文压缩策略"""
    SMART_TRUNCATE = "smart_truncate"      # 智能截断
    SLIDING_WINDOW = "sliding_window"      # 滑动窗口
    FULL_RETAIN = "full_retain"           # 完整保留
    ADAPTIVE = "adaptive"                 # 自适应
    SUMMARY_COMPRESS = "summary_compress"  # 摘要压缩
    KEY_INFO_EXTRACT = "key_info_extract" # 关键信息提取
    LAYERED_STORAGE = "layered_storage"   # 分层存储
    TEMPLATE_COMPRESS = "template_compress" # 模板压缩

class ConversationGroup(str, Enum):
    """会话分组"""
    WORK = "work"           # 工作
    STUDY = "study"         # 学习
    PROJECT = "project"     # 项目
    PERSONAL = "personal"   # 个人
    RESEARCH = "research"   # 研究
    DEVELOPMENT = "development" # 开发
    TESTING = "testing"     # 测试
    OTHER = "other"         # 其他
```

## 主要功能实现

### 1. 会话创建与管理

#### 创建会话
```python
async def create_conversation(
    self, 
    user_id: int, 
    title: str = None,
    ai_provider: str = None, 
    ai_model: str = None,
    system_prompt: str = None, 
    template_type: str = None,
    group: ConversationGroup = None, 
    tags: List[str] = None,
    goal: str = None
) -> AIChatSession
```

**特性**:
- 智能标题生成
- 模板类型自动配置
- AI模型智能选择
- 系统提示词自动设置
- 元数据和标签管理

#### 获取会话列表
```python
async def get_user_conversations(
    self, 
    user_id: int, 
    status: SessionStatus = None,
    group: ConversationGroup = None, 
    tags: List[str] = None,
    sort_by: str = "last_activity", 
    sort_order: str = "desc",
    page: int = 1, 
    size: int = 20
) -> Tuple[List[AIChatSession], int]
```

**特性**:
- 多维度过滤（状态、分组、标签）
- 灵活排序（时间、活跃度、消息数等）
- 分页支持
- 返回总数统计

### 2. 智能上下文管理

#### 获取对话上下文
```python
async def get_conversation_context(
    self, 
    conversation_id: int,
    max_messages: int = None, 
    ai_model: str = None,
    include_important_only: bool = False
) -> ConversationContext
```

**特性**:
- 模型特定的上下文策略
- 智能压缩算法
- 重要消息优先保留
- 上下文摘要生成

#### 上下文压缩策略

**滑动窗口压缩**:
```python
async def _sliding_window_compress(
    self, 
    messages: List[AIChatMessage], 
    max_tokens: int
) -> List[AIChatMessage]
```
- 保留最近的消息直到达到Token限制
- 适用于GPT-3.5等Token限制较严格的模型

**智能截断压缩**:
```python
async def _smart_truncate_compress(
    self, 
    messages: List[AIChatMessage], 
    max_tokens: int
) -> List[AIChatMessage]
```
- 保留系统消息、重要消息和最近消息
- 适用于GPT-4等高级模型

**关键信息提取压缩**:
```python
async def _key_info_extract_compress(
    self, 
    messages: List[AIChatMessage], 
    max_tokens: int
) -> List[AIChatMessage]
```
- 基于关键词识别重要消息
- 适用于需要保留关键信息的场景

### 3. 高级会话操作

#### 会话分支
```python
async def branch_conversation(
    self, 
    conversation_id: int, 
    from_message_id: int,
    user_id: int, 
    new_title: str = None
) -> AIChatSession
```

**功能**:
- 从指定消息点创建新分支
- 复制分支点之前的所有消息
- 保留原会话配置
- 记录分支关系元数据

#### 会话合并
```python
async def merge_conversations(
    self, 
    target_conversation_id: int, 
    source_conversation_ids: List[int],
    user_id: int, 
    new_title: str = None
) -> AIChatSession
```

**功能**:
- 将多个会话合并为一个
- 按时间顺序重新排列消息
- 更新统计信息
- 归档源会话

#### 会话导出
```python
async def export_conversation(
    self, 
    conversation_id: int, 
    user_id: int,
    format: str = "markdown"
) -> str
```

**支持格式**:
- **Markdown**: 结构化文档格式
- **JSON**: 完整数据结构
- **TXT**: 纯文本格式

#### 会话分享
```python
async def generate_share_link(
    self, 
    conversation_id: int, 
    user_id: int,
    expires_in_hours: int = 24, 
    permissions: List[str] = None
) -> str
```

**功能**:
- 生成安全的分享Token
- 设置过期时间
- 权限控制（查看、评论、复制等）
- 分享统计跟踪

### 4. 标签管理

#### 添加标签
```python
async def add_conversation_tags(
    self, 
    conversation_id: int, 
    user_id: int, 
    tags: List[str]
) -> bool
```

#### 移除标签
```python
async def remove_conversation_tags(
    self, 
    conversation_id: int, 
    user_id: int, 
    tags: List[str]
) -> bool
```

## 模型上下文策略配置

```python
self.model_context_strategies = {
    "gpt-4": {
        "max_tokens": 8000,
        "strategy": ContextCompressionStrategy.SMART_TRUNCATE,
        "compression": ContextCompressionStrategy.SUMMARY_COMPRESS
    },
    "gpt-3.5-turbo": {
        "max_tokens": 4000,
        "strategy": ContextCompressionStrategy.SLIDING_WINDOW,
        "compression": ContextCompressionStrategy.KEY_INFO_EXTRACT
    },
    "claude-3": {
        "max_tokens": 100000,
        "strategy": ContextCompressionStrategy.FULL_RETAIN,
        "compression": ContextCompressionStrategy.LAYERED_STORAGE
    },
    "default": {
        "max_tokens": 2000,
        "strategy": ContextCompressionStrategy.ADAPTIVE,
        "compression": ContextCompressionStrategy.TEMPLATE_COMPRESS
    }
}
```

## 会话模板系统

### 模板类型与配置

| 模板类型 | AI模型 | 系统提示词关键词 | 适用场景 |
|----------|--------|------------------|----------|
| `code_assistant` | GPT-4 | 编程助手 | 代码生成、调试、优化 |
| `test_expert` | GPT-4-turbo | 测试专家 | 测试用例、测试策略 |
| `document_writer` | Claude-3-opus | 文档写作 | 技术文档、报告撰写 |
| `data_analyst` | GPT-4-turbo | 数据分析 | 数据处理、统计分析 |
| `creative_design` | GPT-4 | 创意设计 | 方案设计、创意思考 |
| `academic_research` | Claude-3-opus | 学术研究 | 深度分析、学术写作 |
| `project_management` | GPT-3.5-turbo | 项目管理 | 项目规划、风险管理 |
| `general` | GPT-3.5-turbo | AI助手 | 日常对话、通用问答 |

### 智能标题生成

```python
async def _generate_intelligent_title(
    self, 
    template_type: str = None, 
    goal: str = None
) -> str
```

**生成规则**:
- 基于模板类型选择前缀
- 包含用户目标（如果提供）
- 添加时间戳
- 限制长度避免过长

**示例**:
- `代码助手 - 学习Python编程... (08-24 13:47)`
- `测试专家 - 编写测试用例... (08-24 13:47)`
- `AI对话 (08-24 13:47)`

## ConversationContext 上下文对象

```python
class ConversationContext:
    """对话上下文对象"""
    
    def __init__(self, conversation_id: int, messages: List[AIChatMessage],
                 business_context: Optional[Dict] = None,
                 user_preferences: Optional[Dict] = None,
                 summary: Optional[str] = None,
                 compression_strategy: Optional[str] = None,
                 token_count: Optional[int] = None):
        self.conversation_id = conversation_id
        self.messages = messages
        self.business_context = business_context or {}
        self.user_preferences = user_preferences or {}
        self.summary = summary
        self.compression_strategy = compression_strategy
        self.token_count = token_count or sum(msg.tokens_used or 0 for msg in messages)
    
    def get_context_for_model(self, model_name: str) -> str:
        """获取适合特定模型的上下文字符串"""
        
    def get_important_messages(self) -> List[AIChatMessage]:
        """获取重要消息"""
        
    def get_recent_messages(self, count: int = 10) -> List[AIChatMessage]:
        """获取最近的消息"""
```

## 使用示例

### 1. 创建代码助手会话

```python
conversation_service = ConversationService(db)

conversation = await conversation_service.create_conversation(
    user_id=1,
    template_type="code_assistant",
    group=ConversationGroup.DEVELOPMENT,
    tags=["编程", "Python"],
    goal="学习Python编程"
)

print(f"创建会话: {conversation.title}")
print(f"AI模型: {conversation.ai_model}")
print(f"系统提示词: {conversation.system_prompt}")
```

### 2. 获取智能上下文

```python
context = await conversation_service.get_conversation_context(
    conversation_id=1,
    ai_model="gpt-4",
    include_important_only=False
)

print(f"上下文消息数: {len(context.messages)}")
print(f"Token数量: {context.token_count}")
print(f"压缩策略: {context.compression_strategy}")

# 获取适合模型的上下文字符串
context_str = context.get_context_for_model("gpt-4")
```

### 3. 会话分支操作

```python
# 从消息ID为10的位置创建分支
branch_conversation = await conversation_service.branch_conversation(
    conversation_id=1,
    from_message_id=10,
    user_id=1,
    new_title="Python学习 - 高级特性分支"
)

print(f"分支会话ID: {branch_conversation.id}")
```

### 4. 导出会话

```python
# 导出为Markdown格式
markdown_content = await conversation_service.export_conversation(
    conversation_id=1,
    user_id=1,
    format="markdown"
)

# 保存到文件
with open("conversation.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)
```

### 5. 生成分享链接

```python
share_token = await conversation_service.generate_share_link(
    conversation_id=1,
    user_id=1,
    expires_in_hours=24,
    permissions=["view", "comment"]
)

share_url = f"https://example.com/share/{share_token}"
print(f"分享链接: {share_url}")
```

## 性能优化

### 1. 数据库查询优化
- 使用索引优化常用查询
- 分页查询避免大量数据加载
- 预加载关联数据减少N+1查询

### 2. 上下文压缩优化
- 根据模型特性选择最优压缩策略
- 缓存压缩结果避免重复计算
- 异步处理大量消息的压缩

### 3. 内存管理
- 及时释放不需要的消息对象
- 使用生成器处理大量数据
- 限制同时处理的会话数量

## 错误处理

### 1. 数据库错误
- 自动回滚事务
- 记录详细错误日志
- 提供用户友好的错误信息

### 2. 业务逻辑错误
- 参数验证
- 权限检查
- 状态一致性验证

### 3. 外部依赖错误
- AI服务调用失败处理
- 网络超时重试机制
- 降级策略

## 测试覆盖

### 1. 单元测试
- 所有公共方法的测试
- 边界条件测试
- 异常情况测试

### 2. 集成测试
- 数据库操作测试
- 服务间交互测试
- 端到端流程测试

### 3. 性能测试
- 大量数据处理性能
- 并发操作性能
- 内存使用测试

## 安全考虑

### 1. 数据安全
- 敏感信息加密存储
- 访问权限控制
- 数据传输加密

### 2. 操作安全
- 用户身份验证
- 操作权限验证
- 防止SQL注入

### 3. 分享安全
- 分享链接加密
- 过期时间控制
- 权限级别限制

## 扩展性设计

### 1. 插件化架构
- 压缩策略插件化
- 导出格式插件化
- 模板系统插件化

### 2. 配置化管理
- 模型策略配置化
- 压缩参数配置化
- 业务规则配置化

### 3. 微服务支持
- 服务接口标准化
- 异步消息处理
- 分布式缓存支持

## 监控与日志

### 1. 性能监控
- 响应时间监控
- 资源使用监控
- 错误率监控

### 2. 业务监控
- 会话创建统计
- 功能使用统计
- 用户行为分析

### 3. 日志记录
- 操作日志记录
- 错误日志记录
- 性能日志记录

## 总结

ConversationService 是一个功能完整、设计精良的对话管理服务，具备以下优势：

1. **功能完整**: 涵盖会话管理的所有核心功能
2. **智能化**: 智能标题生成、模型选择、上下文压缩
3. **灵活性**: 支持多种模板、分组、标签管理
4. **扩展性**: 插件化架构，易于扩展新功能
5. **性能优化**: 多种压缩策略，高效的数据处理
6. **安全可靠**: 完善的错误处理和安全机制

该服务为AI助手模块提供了坚实的基础，支持复杂的对话管理需求，并为未来的功能扩展预留了充分的空间。