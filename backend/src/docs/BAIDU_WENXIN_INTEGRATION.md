# 百度文心一言集成实现文档

## 概述

百度文心一言集成是AI助手模块的重要组成部分，提供了完整的百度文心一言API集成功能，包括多模型支持、中文内容优化、智能模型推荐、成本控制等企业级功能。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    百度文心一言集成架构                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   API接口层      │   服务层         │      适配器层                │
│                │                 │                            │
│ - 聊天完成接口   │ - 智能服务管理   │   - 百度API适配              │
│ - 流式聊天接口   │ - 模型推荐       │   - 认证管理                 │
│ - 模型管理接口   │ - 中文优化       │   - 错误处理                 │
│ - 统计监控接口   │ - 成本控制       │   - 流式处理                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
├─────────────────────────────────────────────────────────────────┤
│                      配置管理                                    │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   模型配置       │   优化配置       │      监控配置                │
│                │                 │                            │
│ - 模型参数       │ - 中文优化       │   - 使用统计                 │
│ - 成本设置       │ - 文化背景       │   - 性能监控                 │
│ - 性能参数       │ - 标点优化       │   - 告警配置                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 核心组件

#### 1. BaiduAdapter (适配器层)
- **功能**: 百度文心一言API的底层适配
- **职责**: API调用、认证管理、错误处理、流式响应
- **特性**: 支持多模型、自动重试、Token管理

#### 2. BaiduWenxinService (服务层)
- **功能**: 高级业务逻辑处理
- **职责**: 智能模型推荐、中文优化、成本控制、质量评估
- **特性**: 任务复杂度分析、使用统计、配置管理

#### 3. API接口层
- **功能**: RESTful API接口
- **职责**: 请求处理、参数验证、响应格式化
- **特性**: 流式支持、错误处理、文档生成

## 支持的模型

### 模型列表

| 模型名称 | 显示名称 | 上下文长度 | 成本(元/1K tokens) | 平均响应时间 | 适用场景 |
|----------|----------|------------|-------------------|--------------|----------|
| `ernie-4.0-8k` | ERNIE-4.0-8K | 8192 | 0.12 | 3.5s | 复杂推理、创意写作、专业分析 |
| `ernie-3.5-8k` | ERNIE-3.5-8K | 8192 | 0.08 | 2.8s | 通用对话、文本生成、知识问答 |
| `ernie-turbo-8k` | ERNIE-Turbo-8K | 8192 | 0.04 | 1.5s | 快速对话、简单问答、实时交互 |
| `ernie-speed-8k` | ERNIE-Speed-8K | 8192 | 0.02 | 0.8s | 极速响应、基础对话、高并发 |

### 模型特性对比

#### ERNIE-4.0-8K
- **优势**: 推理能力强、创意丰富、中文理解优秀、逻辑严密
- **劣势**: 响应时间较长、成本较高
- **推荐场景**: 复杂分析、创意写作、专业咨询、代码生成

#### ERNIE-3.5-8K
- **优势**: 平衡性好、通用性强、成本适中、响应稳定
- **劣势**: 创意能力一般、复杂推理有限
- **推荐场景**: 日常对话、内容生成、知识问答、文档写作

#### ERNIE-Turbo-8K
- **优势**: 响应快速、成本低廉、并发能力强
- **劣势**: 质量一般、复杂任务能力有限
- **推荐场景**: 客服对话、快速问答、实时交互

#### ERNIE-Speed-8K
- **优势**: 极速响应、成本极低、高并发支持
- **劣势**: 质量较低、功能有限
- **推荐场景**: 简单问答、状态查询、高并发场景

## 核心功能

### 1. 智能模型推荐

#### 1.1 任务复杂度分析
系统会自动分析用户输入的任务复杂度，并推荐最适合的模型：

```python
class TaskComplexity(Enum):
    SIMPLE = "simple"      # 简单问答、基础对话
    MEDIUM = "medium"      # 一般分析、内容生成
    COMPLEX = "complex"    # 复杂推理、创意写作
    CRITICAL = "critical"  # 关键业务、高质量要求
```

#### 1.2 复杂度评估算法
```python
async def _analyze_task_complexity(self, messages: List[ChatMessage]) -> TaskComplexity:
    """
    基于以下因素评估任务复杂度：
    1. 关键词匹配（分析、设计、架构等）
    2. 文本长度
    3. 问题数量
    4. 上下文长度
    """
    complexity_score = 0
    
    # 复杂度关键词权重
    complex_keywords = ["分析", "设计", "架构", "算法", "优化"]
    medium_keywords = ["解释", "说明", "介绍", "总结"]
    
    # 综合评分后确定复杂度级别
    if complexity_score >= 6:
        return TaskComplexity.COMPLEX
    elif complexity_score >= 3:
        return TaskComplexity.MEDIUM
    else:
        return TaskComplexity.SIMPLE
```

#### 1.3 模型推荐策略
- **复杂任务**: 推荐ERNIE-4.0-8K，确保高质量输出
- **中等任务**: 推荐ERNIE-3.5-8K，平衡质量和成本
- **简单任务**: 根据优先级推荐ERNIE-Turbo或ERNIE-Speed
- **成本限制**: 在满足成本要求的前提下选择最佳模型

### 2. 中文内容优化

#### 2.1 优化策略
```python
@dataclass
class ChineseOptimizationConfig:
    enable_context_enhancement: bool = True    # 上下文增强
    use_chinese_punctuation: bool = True       # 中文标点
    optimize_for_chinese_culture: bool = True  # 文化背景优化
    enable_idiom_usage: bool = True           # 成语使用
    enhance_politeness: bool = True           # 礼貌用语
    prefer_formal_language: bool = False      # 正式语言
```

#### 2.2 标点符号优化
自动将英文标点符号转换为中文标点符号：
- `,` → `，`
- `.` → `。`
- `?` → `？`
- `!` → `！`
- `:` → `：`
- `;` → `；`

#### 2.3 文化背景优化
- **系统消息**: 添加中文文化背景提示
- **用户消息**: 自动添加礼貌用语（请、您、谢谢等）
- **助手回复**: 优化语言风格，符合中文表达习惯

#### 2.4 质量评估
```python
async def _evaluate_response_quality(self, content: str) -> float:
    """
    评估响应质量的多个维度：
    1. 长度合理性 (50-2000字符)
    2. 中文内容比例 (>70%)
    3. 结构完整性 (以句号结尾)
    4. 内容重复度 (<20%)
    5. 专业术语使用
    """
    quality_score = 0.5  # 基础分数
    # ... 评估逻辑
    return min(1.0, quality_score)
```

### 3. 成本控制与监控

#### 3.1 使用统计
```python
@dataclass
class WenxinUsageStats:
    total_requests: int = 0           # 总请求数
    successful_requests: int = 0      # 成功请求数
    failed_requests: int = 0          # 失败请求数
    total_tokens: int = 0             # 总Token数
    total_cost: float = 0.0           # 总成本
    avg_response_time: float = 0.0    # 平均响应时间
    model_usage: Dict[str, int] = {}  # 模型使用统计
```

#### 3.2 成本计算
```python
def calculate_cost(tokens: int, model: str) -> float:
    """
    根据模型和Token数量计算成本
    """
    model_config = WENXIN_MODELS[model]
    cost_per_1k = model_config.cost_per_1k_tokens
    return (tokens / 1000) * cost_per_1k
```

#### 3.3 成本控制策略
- **预算限制**: 支持日/月成本限制
- **告警机制**: 达到80%预算时告警
- **自动降级**: 超出预算时自动选择低成本模型
- **使用分析**: 提供详细的使用和成本分析报告

### 4. 流式响应支持

#### 4.1 Server-Sent Events (SSE)
```python
async def _handle_stream_request(messages, request, user_id, wenxin_service):
    """处理流式请求，返回SSE格式数据"""
    
    async def generate_stream():
        async for chunk in wenxin_service.stream_chat_completion(...):
            chunk_data = {
                "id": chunk.request_id,
                "object": "chat.completion.chunk",
                "created": int(chunk.timestamp.timestamp()),
                "model": chunk.metadata.get("model"),
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk.content},
                    "finish_reason": "stop" if chunk.is_final else None
                }]
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

#### 4.2 流式处理特性
- **实时响应**: 逐字符流式输出
- **进度控制**: 支持暂停、继续、取消
- **错误处理**: 流式错误恢复机制
- **连接管理**: 自动重连和状态同步

## API接口

### 1. 聊天完成接口

#### 1.1 基础聊天
```http
POST /api/v1/baidu-wenxin/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "你好，请介绍一下文心一言"}
    ],
    "model": "ernie-3.5-8k",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": false
}
```

#### 1.2 流式聊天
```http
POST /api/v1/baidu-wenxin/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "请写一篇关于AI的文章"}
    ],
    "model": "ernie-4.0-8k",
    "stream": true
}
```

#### 1.3 响应格式
```json
{
    "id": "req_123456",
    "model": "ernie-3.5-8k",
    "content": "文心一言是百度开发的大语言模型...",
    "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 120,
        "total_tokens": 135
    },
    "response_time": 2.3,
    "confidence_score": 0.85,
    "finish_reason": "stop",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. 模型管理接口

#### 2.1 获取可用模型
```http
GET /api/v1/baidu-wenxin/models
```

响应：
```json
{
    "models": [
        {
            "id": "ernie-4.0-8k",
            "name": "ERNIE-4.0-8K",
            "description": "文心大模型4.0版本，具有更强的理解和生成能力",
            "max_tokens": 8192,
            "context_window": 8192,
            "cost_per_1k_tokens": 0.12,
            "strengths": ["推理能力强", "中文理解优秀", "创意写作"]
        }
    ],
    "total_count": 4
}
```

#### 2.2 模型推荐
```http
POST /api/v1/baidu-wenxin/models/recommend
Content-Type: application/json

{
    "task_description": "请帮我分析一个复杂的技术架构问题"
}
```

响应：
```json
[
    {
        "recommended_model": "ernie-4.0-8k",
        "confidence": 0.95,
        "reasoning": "复杂任务需要高质量模型",
        "estimated_cost": 0.24,
        "estimated_time": 3.5
    }
]
```

### 3. 统计监控接口

#### 3.1 使用统计
```http
GET /api/v1/baidu-wenxin/usage/statistics
```

响应：
```json
{
    "total_requests": 1250,
    "successful_requests": 1198,
    "failed_requests": 52,
    "success_rate": 0.958,
    "total_tokens": 125000,
    "total_cost": 10.5,
    "avg_response_time": 2.3,
    "model_usage": {
        "ernie-3.5-8k": 800,
        "ernie-4.0-8k": 300,
        "ernie-turbo-8k": 150
    },
    "cost_per_request": 0.0088
}
```

#### 3.2 健康检查
```http
GET /api/v1/baidu-wenxin/health
```

响应：
```json
{
    "healthy": true,
    "adapter_stats": {
        "total_requests": 1250,
        "success_rate": 0.958,
        "avg_response_time": 2.3
    },
    "usage_stats": {...},
    "available_models": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-turbo-8k", "ernie-speed-8k"]
}
```

### 4. 配置管理接口

#### 4.1 获取配置
```http
GET /api/v1/baidu-wenxin/config
```

#### 4.2 更新中文优化配置
```http
POST /api/v1/baidu-wenxin/config/chinese-optimization
Content-Type: application/json

{
    "enable_context_enhancement": true,
    "use_chinese_punctuation": true,
    "optimize_for_chinese_culture": true,
    "enable_idiom_usage": true
}
```

### 5. 测试接口

#### 5.1 连接测试
```http
POST /api/v1/baidu-wenxin/test
Content-Type: application/json

{
    "test_message": "你好，请介绍一下你自己",
    "model": "ernie-speed-8k"
}
```

## 配置管理

### 1. 环境变量配置

```bash
# 百度API配置
BAIDU_API_KEY=your_api_key
BAIDU_SECRET_KEY=your_secret_key
BAIDU_ENVIRONMENT=production  # production, sandbox, development
BAIDU_BASE_URL=https://aip.baidubce.com
BAIDU_TIMEOUT=30.0
BAIDU_MAX_CONCURRENT=20

# 成本控制
BAIDU_DAILY_COST_LIMIT=100.0
BAIDU_MONTHLY_COST_LIMIT=3000.0

# 功能开关
BAIDU_ENABLE_STREAMING=true
BAIDU_ENABLE_CACHING=true
BAIDU_ENABLE_MONITORING=true
```

### 2. 配置文件

#### 2.1 基础配置
```python
from backend.src.config.baidu_wenxin_config import (
    WenxinConfig, WenxinAPIConfig, ChineseOptimizationConfig,
    WenxinEnvironment
)

config = WenxinConfig(
    api_config=WenxinAPIConfig(
        api_key="your_api_key",
        secret_key="your_secret_key",
        environment=WenxinEnvironment.PRODUCTION,
        timeout=30.0,
        max_concurrent_requests=20,
        daily_cost_limit=100.0
    ),
    chinese_optimization=ChineseOptimizationConfig(
        enable_context_enhancement=True,
        use_chinese_punctuation=True,
        optimize_for_chinese_culture=True
    ),
    enable_streaming=True,
    enable_response_caching=True
)
```

#### 2.2 场景化配置
```python
from backend.src.config.baidu_wenxin_config import get_scenario_config

# 客服场景
customer_service_config = get_scenario_config("customer_service")

# 创意写作场景
creative_writing_config = get_scenario_config("creative_writing")

# 技术分析场景
technical_analysis_config = get_scenario_config("technical_analysis")
```

### 3. 动态配置更新

支持运行时动态更新配置，无需重启服务：

```python
# 更新中文优化配置
await wenxin_service.update_chinese_optimization({
    "enable_context_enhancement": True,
    "use_chinese_punctuation": True,
    "optimize_for_chinese_culture": True
})

# 更新成本限制
await wenxin_service.update_cost_limits(
    daily_limit=150.0,
    monthly_limit=4000.0
)
```

## 部署和集成

### 1. 服务初始化

#### 1.1 在应用启动时初始化
```python
# main.py
from backend.src.services.baidu_wenxin_service import initialize_wenxin_service

async def startup():
    # 初始化文心一言服务
    await initialize_wenxin_service(
        api_key=settings.BAIDU_API_KEY,
        secret_key=settings.BAIDU_SECRET_KEY,
        api_endpoint=settings.BAIDU_BASE_URL
    )
```

#### 1.2 依赖注入配置
```python
# 在FastAPI应用中注册依赖
from backend.src.services.baidu_wenxin_service import get_wenxin_service

app.dependency_overrides[get_wenxin_service] = get_wenxin_service
```

### 2. 路由注册

```python
# api/__init__.py
from backend.src.api.v1.baidu_wenxin import router as baidu_wenxin_router

api_router.include_router(
    baidu_wenxin_router, 
    prefix="/baidu-wenxin", 
    tags=["百度文心一言"]
)
```

### 3. 中间件集成

#### 3.1 认证中间件
```python
from backend.src.services.auth import get_current_user

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),  # 认证检查
    wenxin_service: BaiduWenxinService = Depends(get_wenxin_service)
):
    # 处理逻辑
```

#### 3.2 成本控制中间件
```python
async def cost_control_middleware(request, call_next):
    """成本控制中间件"""
    user_id = get_user_id_from_request(request)
    
    # 检查用户成本限制
    if await check_user_cost_limit(user_id):
        response = await call_next(request)
        
        # 记录成本
        await record_usage_cost(user_id, response)
        
        return response
    else:
        return JSONResponse(
            status_code=429,
            content={"error": "Cost limit exceeded"}
        )
```

### 4. 监控集成

#### 4.1 Prometheus指标
```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
wenxin_requests_total = Counter(
    'wenxin_requests_total',
    'Total Wenxin requests',
    ['model', 'status']
)

wenxin_response_time = Histogram(
    'wenxin_response_time_seconds',
    'Wenxin response time',
    ['model']
)

wenxin_cost_total = Gauge(
    'wenxin_cost_total',
    'Total Wenxin cost'
)
```

#### 4.2 日志集成
```python
import logging

# 配置专用日志记录器
wenxin_logger = logging.getLogger('wenxin')
wenxin_logger.setLevel(logging.INFO)

# 添加处理器
handler = logging.FileHandler('logs/wenxin.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
wenxin_logger.addHandler(handler)
```

## 最佳实践

### 1. 模型选择策略

#### 1.1 基于任务类型选择
- **创意写作**: ERNIE-4.0-8K (高质量输出)
- **技术分析**: ERNIE-4.0-8K 或 ERNIE-3.5-8K
- **客服对话**: ERNIE-Turbo-8K (快速响应)
- **简单问答**: ERNIE-Speed-8K (成本优化)

#### 1.2 基于用户等级选择
- **VIP用户**: 优先使用高质量模型
- **普通用户**: 平衡质量和成本
- **试用用户**: 使用低成本模型

#### 1.3 基于时间段选择
- **高峰期**: 使用快速模型保证响应
- **低峰期**: 使用高质量模型提升体验

### 2. 成本优化策略

#### 2.1 智能缓存
```python
# 缓存常见问题的回答
cache_key = f"wenxin:{hash(user_message)}"
cached_response = await redis.get(cache_key)

if cached_response:
    return cached_response
else:
    response = await wenxin_service.chat_completion(...)
    await redis.setex(cache_key, 3600, response)  # 缓存1小时
    return response
```

#### 2.2 请求合并
```python
# 合并相似请求
async def batch_process_requests(requests: List[ChatRequest]):
    """批量处理相似请求"""
    grouped_requests = group_similar_requests(requests)
    
    results = []
    for group in grouped_requests:
        # 处理一个代表性请求
        representative_request = group[0]
        response = await wenxin_service.chat_completion(representative_request)
        
        # 为组内所有请求生成响应
        for request in group:
            adapted_response = adapt_response_for_request(response, request)
            results.append(adapted_response)
    
    return results
```

#### 2.3 预算管理
```python
class BudgetManager:
    def __init__(self, daily_limit: float, monthly_limit: float):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
    
    async def check_budget(self, estimated_cost: float) -> bool:
        """检查预算是否充足"""
        daily_usage = await self.get_daily_usage()
        monthly_usage = await self.get_monthly_usage()
        
        return (
            daily_usage + estimated_cost <= self.daily_limit and
            monthly_usage + estimated_cost <= self.monthly_limit
        )
    
    async def reserve_budget(self, cost: float):
        """预留预算"""
        await self.update_usage(cost)
```

### 3. 性能优化策略

#### 3.1 连接池管理
```python
# 配置HTTP连接池
connector = aiohttp.TCPConnector(
    limit=100,           # 总连接数限制
    limit_per_host=20,   # 单主机连接数限制
    ttl_dns_cache=300,   # DNS缓存时间
    use_dns_cache=True,  # 启用DNS缓存
)

session = aiohttp.ClientSession(
    connector=connector,
    timeout=aiohttp.ClientTimeout(total=30)
)
```

#### 3.2 并发控制
```python
import asyncio

# 使用信号量控制并发
semaphore = asyncio.Semaphore(10)  # 最多10个并发请求

async def controlled_request(request):
    async with semaphore:
        return await wenxin_service.chat_completion(request)
```

#### 3.3 响应时间优化
```python
# 设置合理的超时时间
timeout_config = {
    "ernie-speed-8k": 5.0,    # 快速模型短超时
    "ernie-turbo-8k": 10.0,   # 中等超时
    "ernie-3.5-8k": 20.0,     # 较长超时
    "ernie-4.0-8k": 30.0      # 最长超时
}

async def adaptive_timeout_request(request):
    timeout = timeout_config.get(request.model, 20.0)
    
    try:
        return await asyncio.wait_for(
            wenxin_service.chat_completion(request),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        # 超时后降级到快速模型
        request.model = "ernie-speed-8k"
        return await wenxin_service.chat_completion(request)
```

### 4. 错误处理策略

#### 4.1 重试机制
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def robust_chat_completion(request):
    """带重试的聊天完成"""
    try:
        return await wenxin_service.chat_completion(request)
    except BaiduWenxinError as e:
        if e.error_code in ["18", "19"]:  # 限流错误
            await asyncio.sleep(5)  # 等待5秒后重试
            raise
        else:
            # 其他错误不重试
            raise
```

#### 4.2 降级策略
```python
async def fallback_chat_completion(request):
    """带降级的聊天完成"""
    try:
        # 尝试首选模型
        return await wenxin_service.chat_completion(request)
    except Exception as e:
        logger.warning(f"Primary model failed: {e}")
        
        # 降级到备用模型
        original_model = request.model
        request.model = "ernie-speed-8k"  # 降级到最快模型
        
        try:
            response = await wenxin_service.chat_completion(request)
            response.metadata["fallback"] = True
            response.metadata["original_model"] = original_model
            return response
        except Exception as fallback_error:
            logger.error(f"Fallback model also failed: {fallback_error}")
            raise
```

#### 4.3 错误监控
```python
class ErrorMonitor:
    def __init__(self):
        self.error_counts = {}
        self.error_rates = {}
    
    async def record_error(self, error_type: str, model: str):
        """记录错误"""
        key = f"{model}:{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # 计算错误率
        total_requests = await self.get_total_requests(model)
        error_rate = self.error_counts[key] / total_requests
        self.error_rates[key] = error_rate
        
        # 错误率过高时告警
        if error_rate > 0.1:  # 10%错误率
            await self.send_alert(f"High error rate for {key}: {error_rate:.2%}")
```

## 监控和运维

### 1. 关键指标监控

#### 1.1 性能指标
- **响应时间**: 平均响应时间、P95响应时间
- **吞吐量**: 每秒请求数、每分钟请求数
- **成功率**: 请求成功率、各模型成功率
- **并发数**: 当前并发请求数、峰值并发数

#### 1.2 业务指标
- **Token使用**: 每日Token消耗、各模型Token分布
- **成本统计**: 每日成本、每月成本、成本趋势
- **用户活跃**: 活跃用户数、用户使用频率
- **模型分布**: 各模型使用比例、模型切换频率

#### 1.3 系统指标
- **内存使用**: 服务内存占用、内存增长趋势
- **CPU使用**: CPU占用率、CPU峰值
- **网络IO**: 网络带宽使用、连接数
- **错误统计**: 错误类型分布、错误频率

### 2. 告警配置

#### 2.1 告警规则
```yaml
alerts:
  - name: wenxin_high_error_rate
    condition: error_rate > 0.1
    duration: 5m
    severity: warning
    message: "Wenxin error rate is high: {{ $value }}"
  
  - name: wenxin_high_response_time
    condition: avg_response_time > 10s
    duration: 2m
    severity: critical
    message: "Wenxin response time is too high: {{ $value }}"
  
  - name: wenxin_cost_limit_approaching
    condition: daily_cost > daily_limit * 0.8
    severity: warning
    message: "Daily cost limit approaching: {{ $value }}/{{ $limit }}"
```

#### 2.2 告警通道
- **邮件通知**: 发送给运维团队
- **短信通知**: 紧急告警发送短信
- **钉钉/企业微信**: 团队群组通知
- **监控面板**: 实时显示告警状态

### 3. 日志管理

#### 3.1 日志分类
```python
# 请求日志
request_logger.info({
    "request_id": request.request_id,
    "user_id": request.user_id,
    "model": request.model,
    "message_count": len(request.messages),
    "timestamp": datetime.utcnow().isoformat()
})

# 响应日志
response_logger.info({
    "request_id": response.request_id,
    "model": response.model,
    "response_time": response.response_time,
    "tokens_used": response.usage.total_tokens,
    "cost": calculate_cost(response.usage.total_tokens, response.model),
    "success": response.success
})

# 错误日志
error_logger.error({
    "request_id": request.request_id,
    "error_type": type(error).__name__,
    "error_message": str(error),
    "model": request.model,
    "retry_count": retry_count
})
```

#### 3.2 日志分析
```bash
# 分析错误模式
grep "BaiduWenxinError" logs/wenxin.log | jq '.error_type' | sort | uniq -c

# 分析响应时间分布
grep "response_time" logs/wenxin.log | jq '.response_time' | awk '{sum+=$1; count++} END {print "Average:", sum/count}'

# 分析成本趋势
grep "cost" logs/wenxin.log | jq '.cost' | awk '{sum+=$1} END {print "Total cost:", sum}'
```

### 4. 性能调优

#### 4.1 模型选择优化
```python
class ModelOptimizer:
    def __init__(self):
        self.model_performance = {}
        self.user_preferences = {}
    
    async def optimize_model_selection(self, request):
        """优化模型选择"""
        # 分析历史性能数据
        performance_data = self.model_performance.get(request.complexity)
        
        # 考虑用户偏好
        user_pref = self.user_preferences.get(request.user_id, {})
        
        # 综合评分选择最优模型
        best_model = self.calculate_best_model(
            performance_data, user_pref, request
        )
        
        return best_model
```

#### 4.2 缓存策略优化
```python
class CacheOptimizer:
    def __init__(self):
        self.cache_hit_rates = {}
        self.cache_sizes = {}
    
    async def optimize_cache_strategy(self):
        """优化缓存策略"""
        for cache_type, hit_rate in self.cache_hit_rates.items():
            if hit_rate < 0.3:  # 命中率低于30%
                # 调整缓存策略
                await self.adjust_cache_policy(cache_type, "reduce_ttl")
            elif hit_rate > 0.8:  # 命中率高于80%
                # 增加缓存容量
                await self.adjust_cache_policy(cache_type, "increase_size")
```

## 故障排除

### 1. 常见问题

#### 1.1 认证失败
**问题**: API Key或Secret Key错误
**解决方案**:
```bash
# 检查环境变量
echo $BAIDU_API_KEY
echo $BAIDU_SECRET_KEY

# 验证API Key格式
python -c "
import os
key = os.getenv('BAIDU_API_KEY')
secret = os.getenv('BAIDU_SECRET_KEY')
print(f'API Key: {key[:8]}...')
print(f'Secret Key: {secret[:8]}...')
"
```

#### 1.2 请求限流
**问题**: 超出API调用频率限制
**解决方案**:
```python
# 实现指数退避重试
import asyncio
import random

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except BaiduWenxinError as e:
            if e.error_code == "18":  # 限流错误
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

#### 1.3 响应超时
**问题**: 请求响应时间过长
**解决方案**:
```python
# 调整超时配置
config = AdapterConfig(
    timeout=60.0,  # 增加超时时间
    max_retries=2,  # 减少重试次数
)

# 或者使用更快的模型
request.model = "ernie-speed-8k"
```

#### 1.4 成本超限
**问题**: 超出预算限制
**解决方案**:
```python
# 实施成本控制
async def cost_aware_request(request):
    estimated_cost = estimate_request_cost(request)
    
    if await check_budget(estimated_cost):
        return await wenxin_service.chat_completion(request)
    else:
        # 降级到低成本模型
        request.model = "ernie-speed-8k"
        return await wenxin_service.chat_completion(request)
```

### 2. 诊断工具

#### 2.1 健康检查脚本
```python
#!/usr/bin/env python3
"""
百度文心一言健康检查脚本
"""
import asyncio
import sys
from backend.src.services.baidu_wenxin_service import get_wenxin_service

async def health_check():
    try:
        service = await get_wenxin_service()
        health_info = await service.health_check()
        
        if health_info["healthy"]:
            print("✅ 服务健康")
            print(f"可用模型: {len(health_info['available_models'])}")
            print(f"成功率: {health_info['usage_stats'].get('success_rate', 0):.2%}")
            return 0
        else:
            print("❌ 服务异常")
            print(f"错误: {health_info.get('error', 'Unknown')}")
            return 1
            
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(health_check())
    sys.exit(exit_code)
```

#### 2.2 性能测试脚本
```python
#!/usr/bin/env python3
"""
百度文心一言性能测试脚本
"""
import asyncio
import time
import statistics
from backend.src.services.baidu_wenxin_service import get_wenxin_service
from backend.src.adapters.base import ChatMessage, MessageRole

async def performance_test(concurrent_requests=10, total_requests=100):
    service = await get_wenxin_service()
    
    async def single_request():
        start_time = time.time()
        try:
            messages = [ChatMessage(role=MessageRole.USER, content="你好")]
            response = await service.chat_completion(messages)
            end_time = time.time()
            return end_time - start_time, response.success
        except Exception as e:
            end_time = time.time()
            return end_time - start_time, False
    
    # 执行并发测试
    semaphore = asyncio.Semaphore(concurrent_requests)
    
    async def controlled_request():
        async with semaphore:
            return await single_request()
    
    print(f"开始性能测试: {total_requests}个请求, {concurrent_requests}并发")
    
    start_time = time.time()
    results = await asyncio.gather(*[
        controlled_request() for _ in range(total_requests)
    ])
    end_time = time.time()
    
    # 分析结果
    response_times = [r[0] for r in results]
    success_count = sum(1 for r in results if r[1])
    
    print(f"\n测试结果:")
    print(f"总耗时: {end_time - start_time:.2f}秒")
    print(f"成功率: {success_count/total_requests:.2%}")
    print(f"平均响应时间: {statistics.mean(response_times):.2f}秒")
    print(f"P95响应时间: {statistics.quantiles(response_times, n=20)[18]:.2f}秒")
    print(f"QPS: {total_requests/(end_time - start_time):.2f}")

if __name__ == "__main__":
    asyncio.run(performance_test())
```

## 总结

百度文心一言集成提供了完整的企业级AI服务解决方案，具有以下特点：

### 核心优势
1. **多模型支持**: 支持ERNIE系列所有主流模型
2. **智能推荐**: 基于任务复杂度自动推荐最适合的模型
3. **中文优化**: 专门针对中文内容进行优化处理
4. **成本控制**: 完善的成本监控和控制机制
5. **高可用性**: 完善的错误处理和降级策略

### 技术特性
1. **异步处理**: 全异步架构，支持高并发
2. **流式响应**: 支持实时流式输出
3. **缓存优化**: 智能缓存策略提升性能
4. **监控完善**: 全面的监控和告警机制
5. **易于集成**: 标准化接口，易于集成到现有系统

### 适用场景
1. **企业客服**: 智能客服对话系统
2. **内容生成**: 文档、报告、创意内容生成
3. **技术分析**: 代码审查、架构分析、技术咨询
4. **教育培训**: 智能问答、知识传授
5. **业务分析**: 数据分析、决策支持

通过合理配置和使用，百度文心一言集成能够为AI助手模块提供强大的中文AI能力支持，显著提升用户体验和业务效率。