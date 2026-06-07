# MCP客户端实现文档

## 概述

本文档描述了AI助手模块中MCP (Model Context Protocol) 客户端的实现。MCP客户端是连接AI服务提供商的核心组件，提供统一的接口用于与多种AI服务进行通信。

## 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP客户端架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ MCP Integration │    │   MCP Config    │                │
│  │    Service      │    │    Manager      │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       │                        │
│           └───────────┬───────────┘                        │
│                       │                                    │
│              ┌─────────────────┐                           │
│              │   MCP Client    │                           │
│              └─────────────────┘                           │
│                       │                                    │
│       ┌───────────────┼───────────────┐                   │
│       │               │               │                   │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│  │ OpenAI  │    │ Claude  │    │ 百度文心 │                │
│  │ Server  │    │ Server  │    │ Server  │                │
│  └─────────┘    └─────────┘    └─────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 主要模块

1. **MCPClient** (`src/utils/mcp_client.py`)
   - 核心MCP协议客户端
   - 管理与多个MCP服务器的连接
   - 处理消息路由和负载均衡

2. **MCPConfigManager** (`src/utils/mcp_config.py`)
   - 配置文件加载和管理
   - 支持文件和环境变量配置
   - 配置热重载和验证

3. **MCPIntegrationService** (`src/services/mcp_integration_service.py`)
   - 高级集成服务
   - AI请求路由和处理
   - 健康检查和故障转移

## 功能特性

### 1. 多服务器支持

- 同时连接多个AI服务提供商
- 智能路由选择最适合的服务器
- 负载均衡和故障转移

### 2. 配置管理

- JSON配置文件支持
- 环境变量配置
- 配置热重载
- 配置验证和错误处理

### 3. 连接管理

- 自动连接和重连
- 连接健康检查
- 连接池管理
- 优雅关闭

### 4. 消息处理

- JSON-RPC 2.0协议支持
- 异步消息处理
- 流式响应支持
- 错误处理和重试

### 5. 监控和统计

- 连接状态监控
- 请求统计和性能指标
- 健康检查报告
- 日志记录和调试

## 使用指南

### 1. 配置文件设置

创建 `mcp.json` 配置文件：

```json
{
  "mcpServers": {
    "openai": {
      "command": "uvx",
      "args": ["openai-mcp-server@latest"],
      "env": {
        "OPENAI_API_KEY": "your-api-key-here"
      },
      "timeout": 30,
      "max_retries": 3,
      "retry_delay": 1.0,
      "health_check_interval": 60,
      "disabled": false,
      "autoApprove": ["chat/completions", "models/list"]
    },
    "anthropic": {
      "command": "uvx",
      "args": ["anthropic-mcp-server@latest"],
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key-here"
      },
      "timeout": 30,
      "disabled": false
    }
  }
}
```

### 2. 环境变量配置

也可以使用环境变量配置：

```bash
# OpenAI服务器配置
export MCP_SERVER_OPENAI_COMMAND="uvx"
export MCP_SERVER_OPENAI_ARGS='["openai-mcp-server@latest"]'
export MCP_SERVER_OPENAI_ENV_OPENAI_API_KEY="your-api-key"
export MCP_SERVER_OPENAI_DISABLED="false"

# Claude服务器配置
export MCP_SERVER_CLAUDE_COMMAND="uvx"
export MCP_SERVER_CLAUDE_ARGS='["anthropic-mcp-server@latest"]'
export MCP_SERVER_CLAUDE_ENV_ANTHROPIC_API_KEY="your-api-key"
```

### 3. 基本使用

```python
from src.services.mcp_integration_service import MCPIntegrationService, AIRequestType

# 初始化服务
service = MCPIntegrationService()
await service.initialize("mcp.json")

# 发送AI请求
result = await service.send_ai_request(
    AIRequestType.CHAT_COMPLETION,
    "请介绍一下人工智能",
    temperature=0.7,
    max_tokens=500
)

if result["success"]:
    print(f"AI回答: {result['result']['content']}")
    print(f"使用服务器: {result['server']}")
    print(f"处理时间: {result['processing_time']:.2f}秒")
else:
    print(f"请求失败: {result['error']}")

# 关闭服务
await service.shutdown()
```

### 4. 便捷函数使用

```python
from src.services.mcp_integration_service import (
    send_ai_chat_request,
    send_ai_code_request,
    send_ai_analysis_request
)

# 聊天请求
chat_result = await send_ai_chat_request(
    "你好，请介绍一下你自己",
    server="openai",
    temperature=0.8
)

# 代码生成请求
code_result = await send_ai_code_request(
    "请生成一个Python快速排序函数",
    model="gpt-4"
)

# 分析请求
analysis_result = await send_ai_analysis_request(
    "请分析这段代码的时间复杂度：def bubble_sort(arr): ...",
    server="claude"
)
```

### 5. 服务状态监控

```python
# 获取服务器状态
status = await service.get_server_status()
for server_name, server_status in status.items():
    print(f"服务器: {server_name}")
    print(f"  状态: {server_status['state']}")
    print(f"  健康: {server_status['health']}")
    print(f"  消息数: {server_status['message_count']}")
    print(f"  错误数: {server_status['error_count']}")

# 获取可用能力
capabilities = await service.get_available_capabilities()
print(f"可用AI能力: {capabilities}")

# 健康检查
health = await service.mcp_client.health_check()
print(f"健康检查结果: {health}")
```

## API参考

### MCPClient类

#### 主要方法

- `add_server(config: MCPServerConfig) -> bool`
  - 添加MCP服务器
  - 参数：服务器配置对象
  - 返回：是否成功添加

- `send_request(server_name: str, method: str, params: Dict) -> Any`
  - 发送请求到指定服务器
  - 参数：服务器名称、方法名、参数
  - 返回：响应结果

- `health_check(server_name: Optional[str] = None) -> Dict[str, bool]`
  - 执行健康检查
  - 参数：服务器名称（可选）
  - 返回：健康检查结果

- `shutdown()`
  - 关闭所有连接

### MCPConfigManager类

#### 主要方法

- `load_from_file(config_path: str, watch: bool = True) -> bool`
  - 从文件加载配置
  - 参数：配置文件路径、是否监控文件变化
  - 返回：是否加载成功

- `load_from_env() -> bool`
  - 从环境变量加载配置
  - 返回：是否加载成功

- `get_config(server_name: str) -> Optional[MCPServerConfig]`
  - 获取服务器配置
  - 参数：服务器名称
  - 返回：配置对象或None

- `add_config(config: MCPServerConfig) -> bool`
  - 添加服务器配置
  - 参数：配置对象
  - 返回：是否添加成功

### MCPIntegrationService类

#### 主要方法

- `initialize(config_path: Optional[str] = None) -> bool`
  - 初始化服务
  - 参数：配置文件路径（可选）
  - 返回：是否初始化成功

- `send_ai_request(request_type: AIRequestType, content: str, server_preference: Optional[str] = None, **kwargs) -> Dict[str, Any]`
  - 发送AI请求
  - 参数：请求类型、内容、首选服务器、其他参数
  - 返回：响应结果

- `get_server_status() -> Dict[str, Any]`
  - 获取服务器状态
  - 返回：状态信息字典

- `get_available_capabilities() -> Dict[str, List[str]]`
  - 获取可用AI能力
  - 返回：能力映射字典

## 配置参数说明

### 服务器配置参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | - | 服务器名称 |
| `command` | string | 是 | - | 启动命令 |
| `args` | array | 否 | [] | 命令参数 |
| `env` | object | 否 | {} | 环境变量 |
| `timeout` | integer | 否 | 30 | 请求超时时间（秒） |
| `max_retries` | integer | 否 | 3 | 最大重试次数 |
| `retry_delay` | float | 否 | 1.0 | 重试延迟（秒） |
| `health_check_interval` | integer | 否 | 60 | 健康检查间隔（秒） |
| `disabled` | boolean | 否 | false | 是否禁用 |
| `autoApprove` | array | 否 | [] | 自动批准的方法列表 |

### AI请求类型

- `CHAT_COMPLETION`: 聊天对话
- `TEXT_GENERATION`: 文本生成
- `CODE_GENERATION`: 代码生成
- `TRANSLATION`: 翻译
- `SUMMARIZATION`: 摘要
- `ANALYSIS`: 分析

## 错误处理

### 常见错误类型

1. **连接错误**
   - 服务器无法启动
   - 网络连接失败
   - 认证失败

2. **配置错误**
   - 配置文件格式错误
   - 必需参数缺失
   - 参数值无效

3. **请求错误**
   - 请求超时
   - 服务器返回错误
   - 响应格式错误

### 错误处理策略

1. **自动重试**
   - 网络错误自动重试
   - 可配置重试次数和延迟
   - 指数退避策略

2. **故障转移**
   - 服务器不可用时自动切换
   - 基于健康检查的路由
   - 负载均衡

3. **优雅降级**
   - 部分服务器失败时继续工作
   - 返回详细错误信息
   - 保持系统稳定性

## 性能优化

### 连接管理

- 连接池复用
- 长连接保持
- 自动重连机制

### 请求优化

- 请求队列管理
- 并发控制
- 响应缓存

### 监控指标

- 连接数统计
- 请求响应时间
- 错误率监控
- 资源使用情况

## 安全考虑

### API密钥管理

- 环境变量存储
- 配置文件加密
- 密钥轮换支持

### 网络安全

- TLS加密通信
- 请求签名验证
- 访问控制

### 数据保护

- 敏感数据过滤
- 日志脱敏
- 数据传输加密

## 测试

### 单元测试

运行MCP客户端测试：

```bash
cd backend
python test_mcp_client.py
```

### 集成测试

运行使用示例：

```bash
cd backend
python mcp_usage_example.py
```

### 测试覆盖

- 配置加载测试
- 连接管理测试
- 消息处理测试
- 错误处理测试
- 性能测试

## 部署指南

### 依赖安装

确保安装了必要的依赖：

```bash
pip install asyncio aiohttp
```

### MCP服务器安装

安装AI服务提供商的MCP服务器：

```bash
# 安装uv和uvx
pip install uv

# OpenAI MCP服务器
uvx openai-mcp-server@latest

# Anthropic MCP服务器
uvx anthropic-mcp-server@latest
```

### 配置部署

1. 创建配置文件 `mcp.json`
2. 设置环境变量（API密钥等）
3. 配置日志级别
4. 启动服务

### 监控部署

- 设置健康检查端点
- 配置日志收集
- 监控性能指标
- 设置告警规则

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查命令路径是否正确
   - 验证API密钥是否有效
   - 确认网络连接正常

2. **配置加载失败**
   - 检查JSON格式是否正确
   - 验证文件路径是否存在
   - 确认权限设置正确

3. **请求超时**
   - 增加超时时间设置
   - 检查网络延迟
   - 验证服务器负载

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查连接状态**
   ```python
   status = await client.get_all_server_status()
   print(json.dumps(status, indent=2, default=str))
   ```

3. **手动健康检查**
   ```python
   health = await client.health_check()
   print(f"Health check results: {health}")
   ```

## 扩展开发

### 添加新的AI服务提供商

1. 在配置中添加新服务器
2. 实现服务器特定的消息格式
3. 添加能力映射
4. 更新测试用例

### 自定义消息处理

1. 继承MCPConnection类
2. 重写消息处理方法
3. 实现自定义协议
4. 注册到客户端

### 插件系统

1. 定义插件接口
2. 实现插件加载机制
3. 提供插件配置
4. 支持动态加载

## 版本历史

### v1.0.0 (当前版本)

- 基础MCP协议支持
- 多服务器连接管理
- 配置文件和环境变量支持
- 健康检查和故障转移
- 完整的错误处理
- 性能监控和统计

### 未来计划

- 插件系统支持
- 更多AI服务提供商
- 高级负载均衡策略
- 分布式部署支持
- 图形化管理界面

## 贡献指南

### 代码规范

- 遵循PEP 8编码规范
- 使用类型提示
- 编写完整的文档字符串
- 添加单元测试

### 提交流程

1. Fork项目仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request
5. 代码审查和合并

### 问题报告

- 使用GitHub Issues
- 提供详细的错误信息
- 包含复现步骤
- 附加相关日志

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- GitHub Issues: [项目地址]
- 邮箱: [联系邮箱]
- 文档: [文档地址]