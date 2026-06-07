# 阿里通义千问集成

## 快速开始

### 1. 配置API密钥

在 `.env` 文件中添加阿里通义千问的API配置：

```bash
# 阿里通义千问配置
ALIYUN_API_KEY=your_api_key_here
ALIYUN_API_ENDPOINT=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
ALIYUN_ENVIRONMENT=production
ALIYUN_TIMEOUT=30.0
ALIYUN_MAX_CONCURRENT=20
ALIYUN_ENABLE_STREAMING=true
ALIYUN_ENABLE_CACHING=true
```

### 2. 获取API密钥

1. 访问 [阿里云控制台](https://dashscope.console.aliyun.com/)
2. 开通DashScope服务并获取 API Key
3. 确保账户有足够的余额或已开通按量付费

### 3. 测试连接

运行初始化脚本测试连接：

```bash
python -m backend.src.scripts.init_aliyun_tongyi \
  --api-key YOUR_API_KEY \
  --test-type connection
```

### 4. 基础使用

```python
from backend.src.services.aliyun_tongyi_service import get_tongyi_service
from backend.src.adapters.base import ChatMessage, MessageRole

# 获取服务实例
service = await get_tongyi_service()

# 创建聊天消息
messages = [
    ChatMessage(role=MessageRole.USER, content="你好，请介绍一下通义千问")
]

# 发送聊天请求
response = await service.chat_completion(
    messages=messages,
    user_id=1,
    model="qwen-turbo"
)

print(f"AI回复: {response.content}")
```

## 支持的模型

| 模型 | 描述 | 成本 | 适用场景 |
|------|------|------|----------|
| `qwen-max` | 最强推理能力 | 0.12元/1K tokens | 复杂分析、创意写作 |
| `qwen-max-1201` | 最新优化版本 | 0.12元/1K tokens | 最新任务、高质量对话 |
| `qwen-plus` | 平衡性能成本 | 0.08元/1K tokens | 通用对话、文档处理 |
| `qwen-turbo` | 快速响应 | 0.02元/1K tokens | 实时对话、简单问答 |
| `qwen-long` | 超长文本 | 0.05元/1K tokens | 长文档分析、深度研究 |
| `qwen-vl-plus` | 视觉理解 | 0.15元/1K tokens | 图像分析、多模态 |
| `qwen-vl-max` | 顶级视觉 | 0.20元/1K tokens | 专业图像分析 |

## API接口

### 聊天完成

```http
POST /api/v1/aliyun-tongyi/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "model": "qwen-turbo",
    "temperature": 0.7,
    "stream": false
}
```

### 流式聊天

```http
POST /api/v1/aliyun-tongyi/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "请写一首诗"}
    ],
    "model": "qwen-plus",
    "stream": true
}
```

### 模型推荐

```http
POST /api/v1/aliyun-tongyi/models/recommend
Content-Type: application/json

{
    "task_description": "请分析技术架构",
    "cost_priority": false
}
```

### 使用统计

```http
GET /api/v1/aliyun-tongyi/usage/statistics
```

## 特色功能

### 1. 智能模型推荐

系统会根据任务复杂度自动推荐最适合的模型：

- **简单任务**: 自动选择快速、低成本模型 (qwen-turbo)
- **中等任务**: 自动选择平衡型模型 (qwen-plus)
- **复杂任务**: 自动选择高质量模型 (qwen-max)
- **超长文本**: 自动选择长文本模型 (qwen-long)

### 2. 中文内容优化

- **标点符号优化**: 自动转换为中文标点符号
- **文化背景适配**: 添加中文文化背景理解
- **礼貌用语**: 自动添加适当的礼貌用语
- **语言风格**: 优化为符合中文表达习惯
- **成语使用**: 智能使用中文成语和俗语

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
ALIYUN_API_KEY=your_api_key
ALIYUN_API_ENDPOINT=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
ALIYUN_ENVIRONMENT=production  # production, sandbox, development
ALIYUN_TIMEOUT=30.0
ALIYUN_MAX_RETRIES=3

# 并发控制
ALIYUN_MAX_CONCURRENT=20

# 成本控制
ALIYUN_DAILY_COST_LIMIT=100.0
ALIYUN_MONTHLY_COST_LIMIT=3000.0

# 功能开关
ALIYUN_ENABLE_STREAMING=true
ALIYUN_ENABLE_CACHING=true
ALIYUN_ENABLE_MONITORING=true

# 中文优化
ALIYUN_ENABLE_CONTEXT_ENHANCEMENT=true
ALIYUN_USE_CHINESE_PUNCTUATION=true
ALIYUN_OPTIMIZE_FOR_CHINESE_CULTURE=true
ALIYUN_ENABLE_IDIOM_USAGE=true
ALIYUN_ENHANCE_POLITENESS=true
ALIYUN_PREFER_FORMAL_LANGUAGE=false
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
curl http://localhost:8000/api/v1/aliyun-tongyi/health

# 测试连接
curl -X POST http://localhost:8000/api/v1/aliyun-tongyi/test \
  -H "Content-Type: application/json" \
  -d '{"test_message": "你好"}'
```

### 性能监控

```bash
# 查看使用统计
curl http://localhost:8000/api/v1/aliyun-tongyi/usage/statistics

# 获取可用模型
curl http://localhost:8000/api/v1/aliyun-tongyi/models
```

### 日志监控

```bash
# 查看通义千问相关日志
tail -f logs/app.log | grep -i "tongyi\|aliyun"

# 查看错误日志
grep "ERROR" logs/app.log | grep -i "tongyi"
```

## 故障排除

### 常见问题

1. **认证失败**
   ```
   错误: TongyiAdapterError [invalid_api_key]: Invalid API key
   解决: 检查API Key是否正确，确保已开通DashScope服务
   ```

2. **请求限流**
   ```
   错误: TongyiAdapterError [throttling]: Request rate limit exceeded
   解决: 降低请求频率或升级API套餐
   ```

3. **响应超时**
   ```
   错误: TimeoutError
   解决: 增加超时时间或使用更快的模型
   ```

4. **余额不足**
   ```
   错误: TongyiAdapterError [insufficient_balance]: Insufficient account balance
   解决: 充值账户余额或开通按量付费
   ```

### 诊断命令

```bash
# 运行完整测试
python -m backend.src.scripts.init_aliyun_tongyi \
  --api-key YOUR_API_KEY \
  --test-type full

# 性能测试
python -m backend.src.scripts.init_aliyun_tongyi \
  --api-key YOUR_API_KEY \
  --test-type performance

# 运行示例
python -m backend.src.examples.aliyun_tongyi_example
```

## 最佳实践

### 1. 模型选择

- **日常对话**: 使用 `qwen-turbo` 或 `qwen-plus`
- **创意写作**: 使用 `qwen-max` 或 `qwen-max-1201`
- **快速响应**: 使用 `qwen-turbo`
- **复杂分析**: 使用 `qwen-max-1201`
- **长文档处理**: 使用 `qwen-long`
- **图像分析**: 使用 `qwen-vl-plus` 或 `qwen-vl-max`

### 2. 成本优化

- 设置合理的成本限制
- 使用缓存减少重复请求
- 根据任务复杂度选择合适模型
- 定期分析使用统计优化策略
- 优先使用成本效益高的模型

### 3. 性能优化

- 合理设置并发数量
- 使用流式响应提升用户体验
- 启用响应缓存
- 配置合适的超时时间
- 使用连接池管理HTTP连接

### 4. 中文优化

- 启用中文标点符号转换
- 使用文化背景优化
- 启用礼貌用语增强
- 根据场景选择正式或非正式语言
- 利用成语和俗语提升表达效果

### 5. 错误处理

- 实现重试机制
- 设置降级策略
- 监控错误率和响应时间
- 及时处理异常情况
- 记录详细的错误日志

## 与其他AI服务对比

| 特性 | 通义千问 | 文心一言 | GPT-4 |
|------|----------|----------|-------|
| **中文理解** | 优秀 | 优秀 | 良好 |
| **成本** | 低-中 | 低-中 | 高 |
| **响应速度** | 快 | 快 | 中等 |
| **模型选择** | 丰富 | 中等 | 有限 |
| **长文本处理** | 优秀(qwen-long) | 良好 | 良好 |
| **多模态支持** | 支持 | 有限 | 支持 |
| **API稳定性** | 高 | 高 | 高 |

## 更多资源

- [完整文档](./ALIYUN_TONGYI_INTEGRATION.md)
- [API参考](../api/v1/aliyun_tongyi.py)
- [配置参考](../config/aliyun_tongyi_config.py)
- [使用示例](../examples/aliyun_tongyi_example.py)
- [集成测试](../tests/test_aliyun_tongyi_integration.py)
- [阿里云DashScope官方文档](https://help.aliyun.com/zh/dashscope/)