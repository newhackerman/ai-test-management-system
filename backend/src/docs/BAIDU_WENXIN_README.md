# 百度文心一言集成

## 快速开始

### 1. 配置API密钥

在 `.env` 文件中添加百度文心一言的API配置：

```bash
# 百度文心一言配置
BAIDU_API_KEY=your_api_key_here
BAIDU_SECRET_KEY=your_secret_key_here
BAIDU_ENVIRONMENT=production
BAIDU_TIMEOUT=30.0
BAIDU_MAX_CONCURRENT=20
BAIDU_ENABLE_STREAMING=true
BAIDU_ENABLE_CACHING=true
```

### 2. 获取API密钥

1. 访问 [百度智能云控制台](https://console.bce.baidu.com/)
2. 创建应用并获取 API Key 和 Secret Key
3. 确保应用已开通文心一言服务

### 3. 测试连接

运行初始化脚本测试连接：

```bash
python -m backend.src.scripts.init_baidu_wenxin \
  --api-key YOUR_API_KEY \
  --secret-key YOUR_SECRET_KEY \
  --test-type connection
```

### 4. 基础使用

```python
from backend.src.services.baidu_wenxin_service import get_wenxin_service
from backend.src.adapters.base import ChatMessage, MessageRole

# 获取服务实例
service = await get_wenxin_service()

# 创建聊天消息
messages = [
    ChatMessage(role=MessageRole.USER, content="你好，请介绍一下你自己")
]

# 发送聊天请求
response = await service.chat_completion(
    messages=messages,
    user_id=1,
    model="ernie-3.5-8k"
)

print(f"AI回复: {response.content}")
```

## 支持的模型

| 模型 | 描述 | 成本 | 适用场景 |
|------|------|------|----------|
| `ernie-4.0-8k` | 最强推理能力 | 0.12元/1K tokens | 复杂分析、创意写作 |
| `ernie-3.5-8k` | 平衡性能成本 | 0.08元/1K tokens | 通用对话、文本生成 |
| `ernie-turbo-8k` | 快速响应 | 0.04元/1K tokens | 实时对话、简单问答 |
| `ernie-speed-8k` | 极速响应 | 0.02元/1K tokens | 高并发、基础对话 |

## API接口

### 聊天完成

```http
POST /api/v1/baidu-wenxin/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "model": "ernie-3.5-8k",
    "temperature": 0.7,
    "stream": false
}
```

### 流式聊天

```http
POST /api/v1/baidu-wenxin/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "请写一首诗"}
    ],
    "model": "ernie-4.0-8k",
    "stream": true
}
```

### 模型推荐

```http
POST /api/v1/baidu-wenxin/models/recommend
Content-Type: application/json

{
    "task_description": "请分析技术架构"
}
```

### 使用统计

```http
GET /api/v1/baidu-wenxin/usage/statistics
```

## 特色功能

### 1. 智能模型推荐

系统会根据任务复杂度自动推荐最适合的模型：

- **简单任务**: 自动选择快速、低成本模型
- **复杂任务**: 自动选择高质量模型
- **成本控制**: 在预算范围内选择最佳模型

### 2. 中文内容优化

- **标点符号优化**: 自动转换为中文标点
- **文化背景适配**: 添加中文文化背景
- **礼貌用语**: 自动添加适当的礼貌用语
- **语言风格**: 优化为符合中文表达习惯

### 3. 成本监控

- **实时统计**: Token使用量、成本统计
- **预算控制**: 设置日/月成本限制
- **使用分析**: 详细的使用报告和趋势分析
- **成本优化**: 智能推荐成本优化策略

### 4. 性能优化

- **连接池**: 高效的HTTP连接管理
- **并发控制**: 智能并发请求控制
- **缓存机制**: 智能响应缓存
- **错误重试**: 自动重试和降级策略

## 配置选项

### 环境变量

```bash
# 基础配置
BAIDU_API_KEY=your_api_key
BAIDU_SECRET_KEY=your_secret_key
BAIDU_ENVIRONMENT=production  # production, sandbox, development
BAIDU_BASE_URL=https://aip.baidubce.com
BAIDU_TIMEOUT=30.0

# 并发控制
BAIDU_MAX_CONCURRENT=20

# 成本控制
BAIDU_DAILY_COST_LIMIT=100.0
BAIDU_MONTHLY_COST_LIMIT=3000.0

# 功能开关
BAIDU_ENABLE_STREAMING=true
BAIDU_ENABLE_CACHING=true
BAIDU_ENABLE_MONITORING=true
```

### 中文优化配置

```python
chinese_optimization = {
    "enable_context_enhancement": True,    # 上下文增强
    "use_chinese_punctuation": True,       # 中文标点
    "optimize_for_chinese_culture": True,  # 文化背景优化
    "enable_idiom_usage": True,           # 成语使用
    "enhance_politeness": True,           # 礼貌用语
    "prefer_formal_language": False       # 正式语言
}
```

## 监控和运维

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/api/v1/baidu-wenxin/health

# 测试连接
curl -X POST http://localhost:8000/api/v1/baidu-wenxin/test \
  -H "Content-Type: application/json" \
  -d '{"test_message": "你好"}'
```

### 性能监控

```bash
# 查看使用统计
curl http://localhost:8000/api/v1/baidu-wenxin/usage/statistics

# 获取可用模型
curl http://localhost:8000/api/v1/baidu-wenxin/models
```

### 日志监控

```bash
# 查看百度文心一言相关日志
tail -f logs/app.log | grep -i "wenxin\|baidu"

# 查看错误日志
grep "ERROR" logs/app.log | grep -i "wenxin"
```

## 故障排除

### 常见问题

1. **认证失败**
   ```
   错误: BaiduWenxinError [invalid_client]: Invalid client credentials
   解决: 检查API Key和Secret Key是否正确
   ```

2. **请求限流**
   ```
   错误: BaiduWenxinError [18]: Open api qps request limit reached
   解决: 降低请求频率或升级API套餐
   ```

3. **响应超时**
   ```
   错误: TimeoutError
   解决: 增加超时时间或使用更快的模型
   ```

### 诊断命令

```bash
# 运行完整测试
python -m backend.src.scripts.init_baidu_wenxin \
  --api-key YOUR_API_KEY \
  --secret-key YOUR_SECRET_KEY \
  --test-type full

# 性能测试
python -m backend.src.scripts.init_baidu_wenxin \
  --api-key YOUR_API_KEY \
  --secret-key YOUR_SECRET_KEY \
  --test-type performance

# 运行示例
python -m backend.src.examples.baidu_wenxin_example
```

## 最佳实践

### 1. 模型选择

- **日常对话**: 使用 `ernie-turbo-8k` 或 `ernie-3.5-8k`
- **创意写作**: 使用 `ernie-4.0-8k`
- **快速响应**: 使用 `ernie-speed-8k`
- **复杂分析**: 使用 `ernie-4.0-8k`

### 2. 成本优化

- 设置合理的成本限制
- 使用缓存减少重复请求
- 根据任务复杂度选择合适模型
- 定期分析使用统计优化策略

### 3. 性能优化

- 合理设置并发数量
- 使用流式响应提升用户体验
- 启用响应缓存
- 配置合适的超时时间

### 4. 错误处理

- 实现重试机制
- 设置降级策略
- 监控错误率和响应时间
- 及时处理异常情况

## 更多资源

- [完整文档](./BAIDU_WENXIN_INTEGRATION.md)
- [API参考](../api/v1/baidu_wenxin.py)
- [配置参考](../config/baidu_wenxin_config.py)
- [使用示例](../examples/baidu_wenxin_example.py)
- [集成测试](../tests/test_baidu_wenxin_integration.py)