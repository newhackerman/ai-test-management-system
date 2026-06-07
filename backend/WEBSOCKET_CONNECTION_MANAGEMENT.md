# AI助手WebSocket连接管理实现文档

## 概述

本文档描述了AI助手模块的WebSocket连接管理系统的实现，该系统提供了完整的实时通信功能，支持AI对话的流式响应、状态同步和连接管理。

## 架构设计

### 核心组件

1. **AIWebSocketManager** (`ai_websocket_manager.py`)
   - 主要的WebSocket连接管理器
   - 处理用户连接、消息路由、对话订阅
   - 支持离线消息缓存和实时通知

2. **WebSocketStateManager** (`websocket_state_manager.py`)
   - 连接状态管理和监控
   - 自动重连机制
   - 状态持久化和恢复

3. **AI WebSocket API** (`ai_websocket.py`)
   - WebSocket API端点
   - 连接管理接口
   - 统计和监控接口

### 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   客户端应用     │    │   客户端应用     │    │   客户端应用     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │ WebSocket            │ WebSocket            │ WebSocket
          │                      │                      │
┌─────────▼──────────────────────▼──────────────────────▼─────────┐
│                    AI WebSocket API                             │
├─────────────────────────────────────────────────────────────────┤
│                  AIWebSocketManager                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   连接管理       │  │   消息路由       │  │   对话订阅       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                WebSocketStateManager                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   状态跟踪       │  │   重连管理       │  │   状态持久化     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Redis缓存                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   离线消息       │  │   连接状态       │  │   会话数据       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 功能特性

### 1. 连接管理

- **多连接支持**: 每个用户可以建立多个WebSocket连接
- **连接限制**: 可配置每用户最大连接数（默认5个）
- **自动清理**: 自动清理过期和无效连接
- **连接统计**: 实时连接数量和状态统计

### 2. 状态管理

- **状态跟踪**: 跟踪每个连接的详细状态信息
- **状态持久化**: 将连接状态持久化到Redis
- **状态恢复**: 服务重启后恢复连接状态
- **状态同步**: 跨实例的状态同步

### 3. 重连机制

- **多种重连策略**:
  - 立即重连 (IMMEDIATE)
  - 指数退避 (EXPONENTIAL_BACKOFF)
  - 线性退避 (LINEAR_BACKOFF)
  - 固定间隔 (FIXED_INTERVAL)
  - 不重连 (NO_RECONNECT)

- **重连配置**:
  - 最大重连次数
  - 初始延迟时间
  - 最大延迟时间
  - 退避倍数
  - 随机抖动

### 4. 消息系统

- **消息类型**:
  - 连接管理消息
  - AI响应消息
  - 状态更新消息
  - 用户操作消息
  - 系统通知消息

- **消息路由**:
  - 点对点消息
  - 对话广播
  - 全局广播
  - 离线消息缓存

### 5. 对话订阅

- **订阅管理**: 用户可以订阅/取消订阅特定对话
- **消息推送**: 向对话订阅者推送相关消息
- **订阅状态**: 跟踪用户的订阅状态

## API接口

### WebSocket端点

#### 1. 通用AI助手连接
```
ws://localhost:8000/api/v1/ai-websocket/ws/ai-assistant
```

参数:
- `conversation_id` (可选): 要自动订阅的对话ID
- `auto_subscribe` (可选): 是否自动订阅对话，默认true

#### 2. 对话专用连接
```
ws://localhost:8000/api/v1/ai-websocket/ws/ai-assistant/{conversation_id}
```

自动订阅指定对话的WebSocket连接。

### HTTP接口

#### 1. 获取WebSocket统计
```http
GET /api/v1/ai-websocket/ws/stats
```

#### 2. 获取用户连接信息
```http
GET /api/v1/ai-websocket/ws/users/{user_id}/connections
```

#### 3. 获取对话订阅者
```http
GET /api/v1/ai-websocket/ws/conversations/{conversation_id}/subscribers
```

#### 4. 向对话发送通知
```http
POST /api/v1/ai-websocket/ws/conversations/{conversation_id}/notify
```

#### 5. 向用户发送通知
```http
POST /api/v1/ai-websocket/ws/users/{user_id}/notify
```

#### 6. 广播通知
```http
POST /api/v1/ai-websocket/ws/broadcast
```

## 消息格式

### WebSocket消息格式

```json
{
  "type": "message_type",
  "data": {...},
  "conversation_id": 123,
  "message_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 消息类型

#### 连接管理
- `connection_established`: 连接建立
- `connection_error`: 连接错误
- `heartbeat`: 心跳消息

#### AI响应
- `ai_response_start`: AI开始响应
- `ai_response_chunk`: AI响应数据块
- `ai_response_complete`: AI响应完成
- `ai_response_error`: AI响应错误

#### 状态更新
- `typing_indicator`: 输入状态指示
- `message_status`: 消息状态更新
- `conversation_status`: 对话状态更新

#### 用户操作
- `user_message`: 用户消息
- `user_typing`: 用户开始输入
- `user_stop_typing`: 用户停止输入

#### 系统通知
- `system_notification`: 系统通知
- `error`: 错误消息

## 客户端使用示例

### JavaScript客户端

```javascript
class AIWebSocketClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.websocket = null;
    this.isConnected = false;
  }

  async connect(conversationId = null, autoSubscribe = true) {
    const url = new URL(this.serverUrl);
    if (conversationId) {
      url.searchParams.set('conversation_id', conversationId);
      url.searchParams.set('auto_subscribe', autoSubscribe);
    }

    this.websocket = new WebSocket(url.toString());
    
    this.websocket.onopen = () => {
      this.isConnected = true;
      console.log('Connected to AI WebSocket');
      this.startHeartbeat();
    };

    this.websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.websocket.onclose = () => {
      this.isConnected = false;
      console.log('Disconnected from AI WebSocket');
    };

    this.websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  sendMessage(type, data, conversationId = null) {
    if (!this.isConnected) return;

    const message = {
      type: type,
      data: data,
      conversation_id: conversationId,
      timestamp: new Date().toISOString()
    };

    this.websocket.send(JSON.stringify(message));
  }

  subscribeToConversation(conversationId) {
    this.sendMessage('subscribe_conversation', {
      conversation_id: conversationId
    });
  }

  startHeartbeat() {
    setInterval(() => {
      if (this.isConnected) {
        this.sendMessage('heartbeat', {});
      }
    }, 30000); // 每30秒发送心跳
  }

  handleMessage(message) {
    switch (message.type) {
      case 'ai_response_chunk':
        this.onAIResponseChunk(message);
        break;
      case 'typing_indicator':
        this.onTypingIndicator(message);
        break;
      // 处理其他消息类型...
    }
  }
}
```

### Python客户端

```python
import asyncio
import json
import websockets

class AIWebSocketClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.websocket = None
        self.is_connected = False

    async def connect(self, conversation_id=None, auto_subscribe=True):
        url = self.server_url
        if conversation_id:
            url += f"?conversation_id={conversation_id}&auto_subscribe={auto_subscribe}"
        
        self.websocket = await websockets.connect(url)
        self.is_connected = True
        
        # 启动消息处理和心跳任务
        asyncio.create_task(self.message_handler())
        asyncio.create_task(self.heartbeat_loop())

    async def send_message(self, message_type, data, conversation_id=None):
        if not self.is_connected:
            return
        
        message = {
            "type": message_type,
            "data": data,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket.send(json.dumps(message))

    async def message_handler(self):
        async for message in self.websocket:
            data = json.loads(message)
            await self.handle_message(data)

    async def heartbeat_loop(self):
        while self.is_connected:
            await self.send_message("heartbeat", {})
            await asyncio.sleep(30)
```

## 配置参数

### AIWebSocketManager配置

```python
# 心跳间隔（秒）
heartbeat_interval = 30

# 连接超时（秒）
connection_timeout = 300

# 最大离线消息数
max_offline_messages = 100

# 每用户最大连接数
max_connections_per_user = 5
```

### WebSocketStateManager配置

```python
# 状态持久化
state_persistence_enabled = True

# 清理间隔（秒）
cleanup_interval = 300

# 最大非活跃时间（秒）
max_inactive_time = 3600

# 默认重连配置
default_reconnect_config = ReconnectConfig(
    strategy=ReconnectStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    backoff_multiplier=2.0,
    jitter=True
)
```

## 监控和统计

### 连接统计

- 总连接数
- 活跃连接数
- 活跃用户数
- 活跃对话数
- 消息发送/接收统计
- 连接错误统计

### 状态统计

- 重连尝试次数
- 成功重连次数
- 失败重连次数
- 状态变更次数
- 离线消息队列统计

## 部署和运维

### 环境要求

- Python 3.9+
- FastAPI
- Redis 6.0+
- WebSocket支持的负载均衡器

### 部署配置

1. **Redis配置**
```bash
# Redis连接URL
REDIS_URL=redis://localhost:6379/0
```

2. **WebSocket配置**
```python
# 在settings中配置
WEBSOCKET_HEARTBEAT_INTERVAL = 30
WEBSOCKET_CONNECTION_TIMEOUT = 300
WEBSOCKET_MAX_CONNECTIONS_PER_USER = 5
```

3. **负载均衡配置**
```nginx
# Nginx配置示例
upstream websocket_backend {
    ip_hash;  # 确保同一用户的连接路由到同一服务器
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
}

server {
    location /api/v1/ai-websocket/ws/ {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

### 监控指标

1. **连接指标**
   - 并发连接数
   - 连接建立/断开速率
   - 连接持续时间

2. **消息指标**
   - 消息发送/接收速率
   - 消息延迟
   - 消息丢失率

3. **错误指标**
   - 连接错误率
   - 重连失败率
   - 消息发送失败率

### 故障排除

1. **连接问题**
   - 检查网络连接
   - 验证WebSocket URL
   - 检查防火墙设置

2. **性能问题**
   - 监控Redis性能
   - 检查内存使用
   - 分析连接数量

3. **消息丢失**
   - 检查Redis连接
   - 验证消息序列化
   - 检查网络稳定性

## 测试

### 单元测试

运行WebSocket管理器测试:
```bash
cd backend
python test_websocket_connection_management.py
```

### 集成测试

使用客户端示例进行测试:
```bash
# 单客户端测试
python websocket_client_example.py

# 多客户端测试
python websocket_client_example.py multi
```

### 压力测试

可以使用工具如`websocket-bench`进行压力测试:
```bash
# 安装websocket-bench
npm install -g websocket-bench

# 运行压力测试
websocket-bench -c 100 -d 60 ws://localhost:8000/api/v1/ai-websocket/ws/ai-assistant
```

## 扩展和定制

### 添加新消息类型

1. 在`MessageType`枚举中添加新类型
2. 在消息处理器中添加处理逻辑
3. 更新客户端代码

### 自定义重连策略

1. 在`ReconnectStrategy`枚举中添加新策略
2. 在`_calculate_reconnect_delay`方法中实现逻辑
3. 配置默认策略

### 集成其他服务

可以通过事件回调机制集成其他服务:
```python
# 添加事件处理器
ai_websocket_manager.add_event_handler("user_connected", on_user_connected)
ai_websocket_manager.add_event_handler("user_disconnected", on_user_disconnected)

async def on_user_connected(data):
    # 处理用户连接事件
    pass

async def on_user_disconnected(data):
    # 处理用户断开事件
    pass
```

## 总结

AI助手WebSocket连接管理系统提供了完整的实时通信解决方案，支持：

- 高并发WebSocket连接管理
- 智能重连和状态管理
- 灵活的消息路由和广播
- 完善的监控和统计
- 易于扩展和定制

该系统为AI助手模块的实时功能提供了坚实的基础，确保用户能够获得流畅的实时交互体验。