# WebSocket连接管理系统

## 概述

本系统实现了企业级的WebSocket连接管理功能，为AI助手模块提供可靠的实时通信能力。系统包含自动重连、消息队列、健康监控、错误处理等完整功能。

## 核心特性

### 🔄 自动重连机制
- 指数退避算法，避免服务器压力
- 可配置的最大重连次数和间隔
- 智能重连条件判断
- 网络状态感知重连

### 📨 消息队列管理
- 离线消息缓存
- 优先级队列支持
- 队列大小限制
- 自动队列处理

### 💓 健康监控
- 实时延迟测量
- 心跳机制
- 连接状态跟踪
- 性能指标统计

### 🛡️ 错误处理
- 全面的错误捕获
- 错误历史记录
- 自动错误恢复
- 用户友好的错误提示

### 🎛️ 灵活配置
- 可配置的连接参数
- 运行时配置更新
- 多种显示模式
- 个性化设置

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket连接管理系统                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   React Hook    │  │   Context API   │  │  Components │ │
│  │                 │  │                 │  │             │ │
│  │ useWebSocket    │  │ WebSocketContext│  │ Connection  │ │
│  │ Manager         │  │ Provider        │  │ Manager     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│           │                     │                   │       │
│           └─────────────────────┼───────────────────┘       │
│                                 │                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            WebSocket连接管理器核心服务                    │ │
│  │                                                         │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │ │
│  │  │ 连接管理     │ │ 消息队列     │ │ 健康监控         │   │ │
│  │  │             │ │             │ │                 │   │ │
│  │  │ • 自动重连   │ │ • 优先级队列 │ │ • 延迟测量       │   │ │
│  │  │ • 状态跟踪   │ │ • 离线缓存   │ │ • 心跳检测       │   │ │
│  │  │ • 错误处理   │ │ • 队列限制   │ │ • 性能统计       │   │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                 │                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 原生WebSocket API                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 文件结构

```
frontend/src/
├── services/
│   └── websocket-connection-manager.ts    # 核心连接管理器
├── hooks/
│   └── useWebSocketManager.ts             # React Hook接口
├── contexts/
│   └── WebSocketContext.tsx               # 全局状态管理
├── components/ai/
│   ├── WebSocketConnectionManager.tsx     # UI组件
│   ├── WebSocketDemo.tsx                  # 演示组件
│   └── __tests__/
│       └── WebSocketConnectionManager.test.tsx  # 测试文件
└── types/
    └── ai-assistant.ts                    # 类型定义
```

## 使用方法

### 1. 基础使用

```tsx
import { useWebSocketManager } from '@/hooks/useWebSocketManager';

function MyComponent() {
  const webSocket = useWebSocketManager({
    conversationId: 123,
    autoConnect: true
  });

  const sendMessage = () => {
    webSocket.sendMessage({
      type: 'message',
      data: { content: 'Hello!' }
    });
  };

  return (
    <div>
      <div>状态: {webSocket.connectionStatus}</div>
      <button onClick={sendMessage} disabled={!webSocket.isConnected}>
        发送消息
      </button>
    </div>
  );
}
```

### 2. 使用Context Provider

```tsx
import { WebSocketProvider } from '@/contexts/WebSocketContext';

function App() {
  return (
    <WebSocketProvider userId={1} autoConnect={true}>
      <MyComponent />
    </WebSocketProvider>
  );
}
```

### 3. 使用UI组件

```tsx
import { WebSocketConnectionManager } from '@/components/ai/WebSocketConnectionManager';

function ChatInterface() {
  return (
    <div>
      <WebSocketConnectionManager 
        conversationId={123}
        showControls={true}
        showDetails={true}
        showMetrics={true}
      />
      {/* 其他聊天界面内容 */}
    </div>
  );
}
```

## API参考

### WebSocketConnectionManager类

#### 构造函数
```typescript
constructor(config: WebSocketConfig)
```

#### 主要方法
- `connect(): Promise<void>` - 连接WebSocket
- `disconnect(): void` - 断开连接
- `send(message: WSMessage): boolean` - 发送消息
- `subscribe(type: WSMessageType, callback: Function): Function` - 订阅消息
- `getMetrics(): ConnectionMetrics` - 获取连接指标
- `getQueueStatus(): QueueStatus` - 获取队列状态

#### 事件
- `connected` - 连接成功
- `disconnected` - 连接断开
- `message` - 收到消息
- `error` - 发生错误
- `statusChange` - 状态变化

### useWebSocketManager Hook

#### 参数
```typescript
interface UseWebSocketManagerOptions {
  autoConnect?: boolean;
  userId?: number;
  conversationId?: number;
  url?: string;
  // ... 其他配置选项
}
```

#### 返回值
```typescript
interface UseWebSocketManagerReturn {
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendMessage: (message: WSMessage) => boolean;
  subscribe: (type: WSMessageType, callback: Function) => Function;
  metrics: ConnectionMetrics;
  // ... 其他属性和方法
}
```

### WebSocketConnectionManager组件

#### Props
```typescript
interface WebSocketConnectionManagerProps {
  conversationId?: number;
  showDetails?: boolean;
  showControls?: boolean;
  showMetrics?: boolean;
  compact?: boolean;
  onStatusChange?: (status: ConnectionStatus) => void;
}
```

## 配置选项

### 连接配置
```typescript
interface WebSocketConfig {
  url: string;                    // WebSocket服务器地址
  protocols?: string[];           // 协议列表
  reconnectInterval?: number;     // 重连间隔(ms)
  maxReconnectAttempts?: number;  // 最大重连次数
  heartbeatInterval?: number;     // 心跳间隔(ms)
  messageQueueSize?: number;      // 消息队列大小
  connectionTimeout?: number;     // 连接超时(ms)
}
```

### 默认配置
```typescript
const defaultConfig = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 1000,
  connectionTimeout: 10000
};
```

## 消息格式

### 基础消息结构
```typescript
interface WSMessage {
  type: WSMessageType;
  conversation_id?: number;
  data: any;
  timestamp: string;
  user_id?: number;
  metadata?: Record<string, any>;
}
```

### 消息类型
- `message` - 普通消息
- `typing` - 打字指示器
- `status` - 状态消息
- `error` - 错误消息
- `analysis_progress` - 分析进度
- `suggestion_update` - 建议更新

## 状态管理

### 连接状态
- `connected` - 已连接
- `disconnected` - 已断开
- `connecting` - 连接中
- `reconnecting` - 重连中

### 同步状态
- `synced` - 已同步
- `syncing` - 同步中
- `error` - 同步错误
- `offline` - 离线模式

## 错误处理

### 错误类型
1. **连接错误** - 无法建立WebSocket连接
2. **网络错误** - 网络中断或不稳定
3. **超时错误** - 连接或操作超时
4. **协议错误** - 消息格式或协议错误
5. **服务器错误** - 服务器返回错误

### 错误恢复策略
1. **自动重连** - 网络恢复后自动重连
2. **消息重发** - 失败消息自动重新发送
3. **状态同步** - 连接恢复后同步状态
4. **用户提示** - 友好的错误提示和操作建议

## 性能优化

### 连接优化
- 智能重连算法，避免频繁重连
- 连接池复用，减少连接开销
- 心跳优化，降低网络负载

### 消息优化
- 消息压缩，减少传输数据量
- 批量发送，提高传输效率
- 优先级队列，重要消息优先处理

### 内存优化
- 消息历史限制，避免内存泄漏
- 定期清理，释放无用资源
- 懒加载，按需加载组件

## 测试

### 单元测试
```bash
npm test WebSocketConnectionManager
```

### 集成测试
```bash
npm test -- --testPathPattern=integration
```

### 端到端测试
```bash
npm run test:e2e
```

## 部署注意事项

### 服务器配置
1. **WebSocket支持** - 确保服务器支持WebSocket协议
2. **代理配置** - 正确配置Nginx等代理服务器
3. **防火墙** - 开放WebSocket端口
4. **SSL证书** - HTTPS环境下使用WSS协议

### 客户端配置
1. **浏览器兼容性** - 确保目标浏览器支持WebSocket
2. **网络环境** - 考虑企业网络限制
3. **移动端适配** - 处理移动网络切换
4. **离线处理** - 提供离线模式支持

## 监控和调试

### 日志记录
- 连接状态变化日志
- 消息发送接收日志
- 错误和异常日志
- 性能指标日志

### 调试工具
- 浏览器开发者工具
- WebSocket调试插件
- 自定义调试面板
- 性能分析工具

### 监控指标
- 连接成功率
- 平均延迟
- 消息丢失率
- 重连频率
- 错误率

## 最佳实践

### 开发建议
1. **错误处理** - 始终处理WebSocket错误
2. **状态管理** - 正确管理连接状态
3. **资源清理** - 组件卸载时清理资源
4. **用户体验** - 提供清晰的状态反馈

### 性能建议
1. **消息频率** - 控制消息发送频率
2. **数据大小** - 限制单次传输数据量
3. **连接复用** - 避免频繁建立连接
4. **内存管理** - 及时清理无用数据

### 安全建议
1. **输入验证** - 验证所有输入数据
2. **权限控制** - 实施适当的权限检查
3. **数据加密** - 使用WSS加密传输
4. **防护措施** - 防止XSS和CSRF攻击

## 故障排除

### 常见问题
1. **连接失败** - 检查服务器地址和端口
2. **频繁断线** - 检查网络稳定性
3. **消息丢失** - 检查队列配置
4. **性能问题** - 检查消息频率和大小

### 解决方案
1. **网络诊断** - 使用网络工具诊断连接
2. **日志分析** - 分析错误日志找出问题
3. **配置调整** - 根据环境调整配置参数
4. **版本更新** - 更新到最新版本

## 更新日志

### v1.0.0 (2024-01-XX)
- ✅ 实现基础WebSocket连接管理
- ✅ 添加自动重连机制
- ✅ 实现消息队列功能
- ✅ 添加健康监控
- ✅ 完善错误处理
- ✅ 创建React Hook接口
- ✅ 实现UI组件
- ✅ 添加完整测试覆盖

## 贡献指南

### 开发流程
1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

### 代码规范
- 使用TypeScript
- 遵循ESLint规则
- 编写单元测试
- 添加文档注释

## 许可证

MIT License - 详见LICENSE文件

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与讨论