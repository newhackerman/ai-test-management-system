# AI路由服务实现文档

## 概述

`AIRouterService` 是AI助手模块的智能路由服务，负责根据用户请求的特征和系统状态，智能选择最适合的AI服务提供商。该服务实现了多维度的路由决策算法，支持负载均衡、成本控制、性能优化等功能。

## 核心功能

### 1. 智能任务类型分析
- **多维度分析**: 基于内容长度、关键词匹配、中文字符比例等多个维度分析任务类型
- **支持的任务类型**:
  - `SIMPLE_QUERY`: 简单查询
  - `COMPLEX_ANALYSIS`: 复杂分析
  - `CHINESE_CONTENT`: 中文内容处理
  - `CODE_GENERATION`: 代码生成
  - `TEST_CASE_GENERATION`: 测试用例生成
  - `DOCUMENT_WRITING`: 文档写作
  - `CREATIVE_WRITING`: 创意写作
  - `DATA_ANALYSIS`: 数据分析
  - `TRANSLATION`: 翻译任务

### 2. 多提供商支持
- **OpenAI**: GPT系列模型，强大的通用能力
- **Anthropic**: Claude系列，擅长长文本处理和推理
- **Google Gemini**: 多模态能力，平衡的性能表现
- **百度文心一言**: 中文优化，本土化服务
- **阿里通义千问**: 企业级服务，中文支持
- **智谱ChatGLM**: 开源友好，成本效益高
- **讯飞星火**: 语言理解能力强
- **自定义提供商**: 支持用户自定义AI服务

### 3. 智能路由策略
- **ACCURACY_FIRST**: 准确性优先，适用于关键任务
- **COST_FIRST**: 成本优先，适用于大批量处理
- **SPEED_FIRST**: 速度优先，适用于实时交互
- **BALANCED**: 平衡策略，综合考虑各项指标
- **LOAD_BALANCED**: 负载均衡，优化系统资源利用

### 4. 健康状态监控
- **实时监控**: 监控各提供商的响应时间、成功率、错误率
- **负载管理**: 跟踪并发请求数，防止过载
- **自动故障转移**: 当主要提供商不可用时自动切换到备选方案

### 5. 成本控制
- **配额管理**: 支持系统级和用户级配额限制
- **成本估算**: 基于历史数据估算请求成本
- **预算控制**: 防止超出预算限制

## 技术实现

### 核心类和数据结构

#### AIRequest
```python
@dataclass
class AIRequest:
    content: str                                    # 请求内容
    user_id: int                                   # 用户ID
    task_type: Optional[TaskType] = None           # 任务类型
    context: Optional[Dict[str, Any]] = None       # 上下文信息
    preferred_provider: Optional[AIProvider] = None # 首选提供商
    routing_strategy: Optional[RoutingStrategy] = None # 路由策略
    max_tokens: Optional[int] = None               # 最大token数
    temperature: Optional[float] = None            # 温度参数
    priority: str = "normal"                       # 优先级
```

#### RoutingDecision
```python
@dataclass
class RoutingDecision:
    selected_provider: AIProvider      # 选择的提供商
    confidence: float                  # 决策置信度
    reasoning: str                     # 决策理由
    fallback_providers: List[AIProvider] # 备选提供商
    estimated_cost: float              # 估算成本
    estimated_time: float              # 估算时间
    routing_strategy_used: RoutingStrategy # 使用的策略
```

#### ProviderHealth
```python
@dataclass
class ProviderHealth:
    provider: AIProvider               # 提供商
    is_available: bool = True          # 是否可用
    response_time: float = 0.0         # 平均响应时间
    success_rate: float = 1.0          # 成功率
    last_check: datetime = None        # 最后检查时间
    error_count: int = 0               # 错误计数
    quota_remaining: int = 100         # 剩余配额
    current_load: int = 0              # 当前负载
    max_concurrent: int = 10           # 最大并发数
    cost_per_token: float = 0.0        # 每token成本
```

### 核心算法

#### 1. 任务类型分析算法
```python
def _analyze_task_type(self, request: AIRequest) -> TaskType:
    # 1. 计算中文字符比例
    # 2. 关键词权重分析
    # 3. 内容长度判断
    # 4. 综合评分选择最佳匹配
```

#### 2. 提供商评分算法
```python
async def _calculate_provider_score(self, provider: AIProvider, 
                                   request: AIRequest, 
                                   strategy: RoutingStrategy) -> float:
    # 1. 基础能力得分 (准确性、速度、成本效益)
    # 2. 任务特定得分 (针对特定任务类型的优化)
    # 3. 健康状态得分 (成功率、响应时间、负载)
    # 4. 策略权重调整
    # 5. 综合评分计算
```

#### 3. 路由决策算法
```python
async def _make_routing_decision(self, request: AIRequest, 
                               available_providers: List[AIProvider]) -> RoutingDecision:
    # 1. 获取任务策略配置
    # 2. 计算各提供商得分
    # 3. 排序选择最优方案
    # 4. 生成决策理由
    # 5. 估算成本和时间
```

## 使用示例

### 基本使用
```python
from services.ai_router_service import AIRouterService, AIRequest, TaskType

# 创建路由服务实例
router = AIRouterService(db_session)

# 创建请求
request = AIRequest(
    content="请帮我生成一个用户登录的测试用例",
    user_id=123,
    task_type=TaskType.TEST_CASE_GENERATION
)

# 获取路由决策
decision = await router.route_request(request)

print(f"选择的提供商: {decision.selected_provider.value}")
print(f"决策理由: {decision.reasoning}")
```

### 高级使用
```python
# 指定路由策略和首选提供商
request = AIRequest(
    content="分析这个复杂的业务场景",
    user_id=123,
    task_type=TaskType.COMPLEX_ANALYSIS,
    routing_strategy=RoutingStrategy.ACCURACY_FIRST,
    preferred_provider=AIProvider.OPENAI,
    priority="urgent"
)

decision = await router.route_request(request)
```

### 监控和管理
```python
# 获取提供商统计信息
stats = await router.get_provider_stats()

# 获取性能指标
metrics = await router.get_provider_performance_metrics(
    AIProvider.OPENAI, days=7
)

# 获取负载分布
load_dist = router.get_current_load_distribution()

# 获取路由推荐
recommendations = await router.get_routing_recommendations(request)
```

## 配置说明

### 路由策略配置
```python
self.routing_strategies = {
    TaskType.COMPLEX_ANALYSIS: {
        "strategy": RoutingStrategy.ACCURACY_FIRST,
        "preferred_providers": [AIProvider.OPENAI, AIProvider.ANTHROPIC],
        "min_accuracy": 0.9,
        "max_cost_per_token": 0.05,
        "timeout": 30.0
    },
    # ... 其他任务类型配置
}
```

### 提供商能力配置
```python
self.provider_capabilities = {
    AIProvider.OPENAI: {
        "accuracy": 0.95,
        "speed": 0.8,
        "cost_efficiency": 0.6,
        "chinese_support": 0.7,
        "code_generation": 0.95,
        "creative_writing": 0.9,
        "reasoning": 0.95
    },
    # ... 其他提供商配置
}
```

## 性能优化

### 1. 缓存策略
- 健康状态缓存，减少数据库查询
- 配置信息缓存，提高响应速度
- 路由决策缓存，避免重复计算

### 2. 负载均衡
- 实时负载监控
- 动态负载调整
- 智能故障转移

### 3. 异步处理
- 全异步设计，提高并发性能
- 非阻塞数据库操作
- 并行健康检查

## 监控指标

### 系统级指标
- 总请求数和成功率
- 平均响应时间
- 成本统计
- 错误率分析

### 提供商级指标
- 各提供商使用率
- 性能对比分析
- 成本效益评估
- 健康状态趋势

### 用户级指标
- 用户请求分布
- 个人使用统计
- 偏好分析

## 扩展性设计

### 1. 新提供商接入
- 标准化接口设计
- 配置驱动的提供商管理
- 插件化架构支持

### 2. 策略扩展
- 可配置的路由策略
- 自定义评分算法
- 机器学习优化支持

### 3. 监控扩展
- 可插拔的监控组件
- 自定义指标收集
- 第三方监控系统集成

## 故障处理

### 1. 提供商故障
- 自动检测和标记
- 故障转移机制
- 恢复检测和重启

### 2. 配额超限
- 实时配额监控
- 自动限流保护
- 优雅降级处理

### 3. 性能异常
- 响应时间监控
- 异常检测和告警
- 自动调整策略

## 安全考虑

### 1. 访问控制
- 用户权限验证
- API密钥管理
- 请求频率限制

### 2. 数据保护
- 敏感信息过滤
- 请求内容审核
- 日志脱敏处理

### 3. 成本保护
- 配额限制
- 异常使用检测
- 自动熔断机制

## 测试策略

### 1. 单元测试
- 核心算法测试
- 边界条件验证
- 异常处理测试

### 2. 集成测试
- 数据库交互测试
- 外部服务集成测试
- 端到端流程测试

### 3. 性能测试
- 并发性能测试
- 负载均衡测试
- 故障恢复测试

## 部署建议

### 1. 环境配置
- 数据库连接池配置
- 缓存服务配置
- 监控系统配置

### 2. 资源规划
- 内存使用优化
- CPU资源分配
- 网络带宽规划

### 3. 运维监控
- 健康检查端点
- 性能指标收集
- 告警规则配置

## 总结

AIRouterService 实现了一个完整的智能路由系统，具备以下特点：

1. **智能化**: 基于多维度分析的智能路由决策
2. **可扩展**: 支持新提供商和策略的灵活扩展
3. **高性能**: 异步处理和缓存优化
4. **可靠性**: 完善的故障处理和恢复机制
5. **可观测**: 全面的监控和统计功能
6. **安全性**: 多层次的安全保护措施

该服务为AI助手模块提供了强大的路由能力，能够根据不同场景自动选择最适合的AI服务提供商，确保系统的高效运行和用户体验的优化。