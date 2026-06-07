# AI服务提供商适配器架构

## 概述

本模块实现了多AI服务提供商的统一适配器架构，支持多种主流AI服务的无缝集成和智能调度。

## 架构特点

### 🔧 统一接口
- 所有AI服务提供商使用相同的调用接口
- 标准化的请求/响应格式
- 一致的错误处理机制

### 🚀 高性能
- 异步编程模式，支持高并发
- 连接池管理和复用
- 智能缓存和优化

### 🔄 智能路由
- 多种负载均衡策略
- 自动故障转移
- 断路器模式保护

### 📊 监控完善
- 实时性能监控
- 详细的使用统计
- 健康状态检查

### 🔌 易于扩展
- 插件化架构设计
- 支持自定义适配器
- 配置热更新

## 支持的AI服务提供商

| 提供商 | 模型 | 状态 | 特性 |
|--------|------|------|------|
| **OpenAI** | GPT-4, GPT-3.5-turbo | ✅ | 函数调用、流式响应 |
| **Anthropic** | Claude-3 系列 | ✅ | 长文本处理、安全性 |
| **百度文心一言** | ERNIE-Bot 系列 | ✅ | 中文优化、本土化 |
| **阿里通义千问** | Qwen 系列 | ✅ | 中文理解、多模态 |
| **Google Gemini** | Gemini Pro/Ultra | ✅ | 多模态、推理能力 |
| **智谱ChatGLM** | ChatGLM 系列 | ✅ | 开源友好、成本低 |
| **科大讯飞星火** | Spark 系列 | ✅ | 语音处理、教育场景 |
| **自定义服务** | 用户定义 | ✅ | 灵活配置、私有部署 |

## 快速开始

### 1. 基本使用

```python
from adapters import AIAdapterFactory, AdapterConfig, AIProvider, AIRequest, MessageRole

# 创建适配器配置
config = AdapterConfig(
    provider=AIProvider.OPENAI,
    api_key="your-openai-api-key",
    default_model="gpt-3.5-turbo",
    max_concurrent_requests=10,
    timeout=30.0
)

# 创建适配器
adapter = AIAdapterFactory.create_adapter(config)

# 创建请求
request = AIRequest(
    messages=[
        {"role": MessageRole.USER, "content": "Hello, how are you?"}
    ],
    max_tokens=100,
    temperature=0.7
)

# 发送请求
response = await adapter.chat_completion(request)
print(response.content)
```

### 2. 使用适配器管理器

```python
from adapters import AIAdapterManager, AdapterConfig, AIProvider

# 创建管理器
manager = AIAdapterManager({
    "load_balance_strategy": "round_robin",
    "failover_strategy": "retry_then_failover",
    "health_check_interval": 60
})

await manager.start()

# 添加多个适配器
configs = [
    AdapterConfig(provider=AIProvider.OPENAI, api_key="openai-key"),
    AdapterConfig(provider=AIProvider.ANTHROPIC, api_key="claude-key"),
    AdapterConfig(provider=AIProvider.BAIDU_WENXIN, api_key="baidu-key", 
                 custom_params={"secret_key": "baidu-secret"})
]

for i, config in enumerate(configs):
    await manager.add_adapter(f"adapter_{i}", config)

# 发送请求（自动负载均衡和故障转移）
response = await manager.send_request(request)
```

### 3. 流式响应

```python
# 启用流式响应
request.stream = True

async for chunk in adapter.stream_chat_completion(request):
    if not chunk.is_final:
        print(chunk.content, end='', flush=True)
    else:
        print("\n[完成]")
```

## 配置说明

### AdapterConfig 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `provider` | AIProvider | ✅ | AI服务提供商 |
| `api_key` | str | ✅ | API密钥 |
| `api_endpoint` | str | ❌ | 自定义API端点 |
| `default_model` | str | ❌ | 默认模型名称 |
| `max_retries` | int | ❌ | 最大重试次数 (默认: 3) |
| `timeout` | float | ❌ | 请求超时时间 (默认: 30.0) |
| `max_concurrent_requests` | int | ❌ | 最大并发请求数 (默认: 10) |
| `rate_limit_per_minute` | int | ❌ | 每分钟请求限制 (默认: 60) |
| `cost_per_token` | float | ❌ | 每Token成本 |
| `custom_headers` | dict | ❌ | 自定义请求头 |
| `custom_params` | dict | ❌ | 自定义参数 |

### 特定提供商配置

#### OpenAI
```python
config = AdapterConfig(
    provider=AIProvider.OPENAI,
    api_key="sk-...",
    api_endpoint="https://api.openai.com/v1",  # 可选
    default_model="gpt-3.5-turbo"
)
```

#### Anthropic Claude
```python
config = AdapterConfig(
    provider=AIProvider.ANTHROPIC,
    api_key="sk-ant-...",
    api_version="2023-06-01",
    default_model="claude-3-sonnet-20240229"
)
```

#### 百度文心一言
```python
config = AdapterConfig(
    provider=AIProvider.BAIDU_WENXIN,
    api_key="your-api-key",
    custom_params={
        "secret_key": "your-secret-key"
    },
    default_model="ERNIE-Bot-4"
)
```

#### 自定义服务
```python
config = AdapterConfig(
    provider=AIProvider.CUSTOM,
    api_key="your-key",
    api_endpoint="https://your-ai-service.com/api",
    custom_params={
        "request_format": "openai",  # 或 "custom"
        "response_format": "openai", # 或 "custom"
        "auth_header": "Authorization",
        "auth_format": "Bearer {}",
        "supported_models": ["custom-model-1", "custom-model-2"]
    }
)
```

## 负载均衡策略

### 1. 轮询 (Round Robin)
```python
manager = AIAdapterManager({
    "load_balance_strategy": "round_robin"
})
```
按顺序轮流使用各个适配器。

### 2. 最少连接 (Least Connections)
```python
manager = AIAdapterManager({
    "load_balance_strategy": "least_connections"
})
```
选择当前连接数最少的适配器。

### 3. 加权轮询 (Weighted Round Robin)
```python
# 添加适配器时指定权重
await manager.add_adapter("high_priority", config1, weight=3.0)
await manager.add_adapter("low_priority", config2, weight=1.0)
```
根据权重分配请求。

### 4. 响应时间 (Response Time)
```python
manager = AIAdapterManager({
    "load_balance_strategy": "response_time"
})
```
选择平均响应时间最短的适配器。

## 故障转移机制

### 1. 立即转移 (Immediate)
```python
manager = AIAdapterManager({
    "failover_strategy": "immediate"
})
```
请求失败时立即切换到备用适配器。

### 2. 重试后转移 (Retry Then Failover)
```python
manager = AIAdapterManager({
    "failover_strategy": "retry_then_failover",
    "max_retries": 3
})
```
先重试指定次数，失败后切换适配器。

### 3. 断路器模式 (Circuit Breaker)
```python
manager = AIAdapterManager({
    "failover_strategy": "circuit_breaker",
    "unhealthy_threshold": 5,  # 连续失败5次后打开断路器
    "recovery_threshold": 2    # 连续成功2次后关闭断路器
})
```
自动检测故障并暂时停用不健康的适配器。

## 监控和统计

### 获取适配器状态
```python
# 获取单个适配器统计
stats = adapter.get_stats()
print(f"总请求数: {stats['total_requests']}")
print(f"成功率: {stats['successful_requests'] / stats['total_requests']:.2%}")
print(f"平均响应时间: {stats['avg_response_time']:.2f}s")

# 获取管理器状态
status = manager.get_status()
print(f"活跃适配器: {len(status['adapters'])}")
print(f"故障转移次数: {status['stats']['failover_count']}")
```

### 健康检查
```python
# 手动健康检查
is_healthy = await adapter.health_check()

# 检查所有适配器
health_results = await AIAdapterFactory.health_check_all()
for adapter_name, is_healthy in health_results.items():
    print(f"{adapter_name}: {'健康' if is_healthy else '不健康'}")
```

## 最佳实践

### 1. 配置管理
```python
# 使用环境变量管理敏感信息
import os

config = AdapterConfig(
    provider=AIProvider.OPENAI,
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=float(os.getenv("AI_TIMEOUT", "30.0")),
    max_concurrent_requests=int(os.getenv("AI_MAX_CONCURRENT", "10"))
)
```

### 2. 错误处理
```python
try:
    response = await adapter.chat_completion(request)
    if response.success:
        print(response.content)
    else:
        print(f"请求失败: {response.error_message}")
except Exception as e:
    print(f"系统错误: {str(e)}")
```

### 3. 成本控制
```python
# 设置成本限制
config = AdapterConfig(
    provider=AIProvider.OPENAI,
    api_key="your-key",
    cost_per_token=0.002,
    daily_token_limit=100000,
    monthly_token_limit=3000000
)

# 监控成本
stats = adapter.get_stats()
daily_cost = stats.get('total_cost', 0)
if daily_cost > 100:  # 每日成本超过100元
    print("警告: 每日成本超出预算!")
```

### 4. 性能优化
```python
# 使用连接池
config = AdapterConfig(
    provider=AIProvider.OPENAI,
    api_key="your-key",
    max_concurrent_requests=20,  # 增加并发数
    timeout=60.0,  # 适当增加超时时间
    custom_headers={
        "Connection": "keep-alive"  # 保持连接
    }
)

# 启用缓存
adapter = AIAdapterFactory.create_adapter(config, use_cache=True)
```

## 扩展开发

### 创建自定义适配器

```python
from adapters.base import BaseAIAdapter, AIRequest, AIResponse

class MyCustomAdapter(BaseAIAdapter):
    """自定义AI适配器"""
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        # 实现你的AI服务调用逻辑
        try:
            # 调用你的AI服务API
            result = await self._call_my_ai_service(request)
            
            return AIResponse(
                request_id=request.request_id,
                provider=self.provider,
                model="my-model",
                content=result["text"],
                response_time=result["time"]
            )
        except Exception as e:
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "CUSTOM_ERROR", str(e)
            )
    
    async def _call_my_ai_service(self, request: AIRequest):
        # 实现具体的API调用
        pass

# 注册自定义适配器
AIAdapterFactory.register_custom_adapter("my_provider", MyCustomAdapter)
```

### 添加中间件

```python
class LoggingMiddleware:
    """日志中间件"""
    
    def __init__(self, adapter: BaseAIAdapter):
        self.adapter = adapter
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        
        try:
            response = await self.adapter.chat_completion(request)
            duration = time.time() - start_time
            
            logger.info(f"请求完成: {request.request_id}, 耗时: {duration:.2f}s")
            return response
        except Exception as e:
            logger.error(f"请求失败: {request.request_id}, 错误: {str(e)}")
            raise

# 使用中间件
adapter = AIAdapterFactory.create_adapter(config)
adapter_with_logging = LoggingMiddleware(adapter)
```

## 故障排除

### 常见问题

1. **API密钥无效**
   ```
   错误: HTTP_401 - Invalid API key
   解决: 检查API密钥是否正确，是否有足够的权限
   ```

2. **请求超时**
   ```
   错误: TIMEOUT - Request timeout
   解决: 增加timeout配置，检查网络连接
   ```

3. **配额超限**
   ```
   错误: HTTP_429 - Rate limit exceeded
   解决: 降低请求频率，增加重试延迟
   ```

4. **模型不可用**
   ```
   错误: HTTP_404 - Model not found
   解决: 检查模型名称，确认模型可用性
   ```

### 调试技巧

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("adapters")

# 查看适配器状态
status = manager.get_status()
print(json.dumps(status, indent=2, ensure_ascii=False))

# 测试单个适配器
test_request = AIRequest(
    messages=[{"role": MessageRole.USER, "content": "test"}],
    max_tokens=10
)
response = await adapter.chat_completion(test_request)
print(f"测试结果: {response.success}")
```

## 更新日志

### v1.0.0 (2024-01-20)
- ✅ 初始版本发布
- ✅ 支持8种主流AI服务提供商
- ✅ 完整的负载均衡和故障转移机制
- ✅ 实时监控和统计功能
- ✅ 插件化架构设计

### 计划功能
- 🔄 支持更多AI服务提供商
- 🔄 图形化监控界面
- 🔄 自动成本优化
- 🔄 A/B测试支持
- 🔄 模型性能基准测试

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置
```bash
# 克隆项目
git clone <repository-url>

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest src/tests/test_ai_adapters.py -v

# 代码格式化
black src/adapters/
isort src/adapters/
```

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- test: 测试相关
- refactor: 代码重构

## 许可证

MIT License - 详见 LICENSE 文件