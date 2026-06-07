# AI助手组件

这个目录包含AI助手相关的React组件，提供智能对话、流式响应和连接管理功能。

## 组件列表

### 核心组件

- **`StreamingChat.tsx`** - 基础流式聊天组件
- **`EnhancedStreamingChat.tsx`** - 增强版流式聊天组件
- **`TypewriterText.tsx`** - 打字机效果文本组件
- **`ConnectionStatusManager.tsx`** - 连接状态管理器

### 演示组件

- **`TypewriterDemo.tsx`** - 打字机效果演示
- **`ConnectionStatusDemo.tsx`** - 连接状态管理演示

## 连接状态管理

### 基本用法

```tsx
import { AIConnectionProvider, useAIConnection } from './ConnectionStatusManager';

function MyAIComponent() {
  const { isConnected, connect, disconnect, send } = useAIConnection();
  
  return (
    <div>
      <p>连接状态: {isConnected ? '已连接' : '未连接'}</p>
      <button onClick={connect}>连接</button>
      <button onClick={disconnect}>断开</button>
    </div>
  );
}

function App() {
  return (
    <AIConnectionProvider wsUrl="/api/v1/ai-assistant/ws">
      <MyAIComponent />
    </AIConnectionProvider>
  );
}
```

### 连接状态指示器

```tsx
import { ConnectionStatusIndicator, ConnectionQualityIndicator } from './ConnectionStatusManager';

function Header() {
  return (
    <div className="header">
      <h1>AI助手</h1>
      <div className="status-indicators">
        <ConnectionStatusIndicator />
        <ConnectionQualityIndicator />
      </div>
    </div>
  );
}
```

### 连接统计面板

```tsx
import { ConnectionStatsPanel } from './ConnectionStatusManager';

function SettingsPage() {
  return (
    <div>
      <h2>连接统计</h2>
      <ConnectionStatsPanel />
    </div>
  );
}
```

## 配置选项

### AIConnectionProvider 配置

```tsx
<AIConnectionProvider 
  wsUrl="/api/v1/ai-assistant/ws"
  config={{
    autoReconnect: true,           // 自动重连
    maxReconnectAttempts: 5,       // 最大重连次数
    reconnectInterval: 3000,       // 重连间隔 (ms)
    heartbeatInterval: 30000,      // 心跳间隔 (ms)
    connectionTimeout: 10000,      // 连接超时 (ms)
    qualityCheckInterval: 5000,    // 质量检查间隔 (ms)
    enableNotifications: true,     // 启用通知
    persistState: true             // 持久化状态
  }}
>
  {children}
</AIConnectionProvider>
```

## 连接状态类型

- `disconnected` - 未连接
- `connecting` - 连接中
- `connected` - 已连接
- `reconnecting` - 重连中
- `error` - 连接错误
- `unstable` - 连接不稳定

## 连接质量指标

- **延迟 (latency)** - 网络延迟，单位毫秒
- **丢包率 (packetLoss)** - 数据包丢失率，百分比
- **吞吐量 (throughput)** - 数据传输速率，字节/秒
- **稳定性 (stability)** - 连接稳定性等级
  - `excellent` - 优秀 (延迟 < 100ms)
  - `good` - 良好 (延迟 < 300ms)
  - `fair` - 一般 (延迟 < 500ms)
  - `poor` - 较差 (延迟 >= 500ms)

## 事件处理

### 订阅消息

```tsx
const { subscribe } = useAIConnection();

useEffect(() => {
  const unsubscribe = subscribe('chat_message', (data) => {
    console.log('收到聊天消息:', data);
  });
  
  return unsubscribe;
}, [subscribe]);
```

### 发送消息

```tsx
const { send } = useAIConnection();

const sendChatMessage = (content: string) => {
  const success = send({
    type: 'chat_message',
    payload: { content, timestamp: Date.now() }
  });
  
  if (!success) {
    console.warn('发送失败 - 连接未建立');
  }
};
```

## 错误处理

连接管理器会自动处理以下错误情况：

1. **连接超时** - 自动重试连接
2. **网络中断** - 自动重连机制
3. **服务器错误** - 错误状态显示和重连
4. **消息发送失败** - 消息队列和重发机制

## 性能优化

1. **消息队列** - 离线时缓存消息，连接恢复后自动发送
2. **心跳机制** - 定期检查连接状态，及时发现连接问题
3. **质量监控** - 实时监控连接质量，提供用户反馈
4. **状态持久化** - 保存连接统计信息，跨会话保持数据

## 测试

运行连接状态管理器的测试：

```bash
npm test src/components/ai/__tests__/ConnectionStatusManager.test.tsx
```

## 演示

查看连接状态管理的完整演示：

```tsx
import ConnectionStatusDemo from './ConnectionStatusDemo';

function App() {
  return <ConnectionStatusDemo />;
}
```

这个演示展示了所有连接管理功能，包括手动连接控制、状态监控、质量指标和配置管理。