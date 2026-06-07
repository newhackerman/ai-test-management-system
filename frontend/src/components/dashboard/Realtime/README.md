# 实时数据更新组件

这个模块实现了任务 6.7 "实现实时数据更新" 的所有功能，包括 WebSocket 连接管理、数据更新动画和用户提示。

## 🎯 核心功能

### 1. RealtimeProvider - 实时数据提供器
- ✅ 管理 WebSocket 连接状态
- ✅ 连接指标监控（运行时间、重连次数、消息统计）
- ✅ 自动重连机制
- ✅ 数据更新动画触发
- ✅ 用户通知管理

### 2. WebSocketClient - WebSocket 客户端
- ✅ 自动重连功能
- ✅ 连接状态覆盖层
- ✅ 心跳检测
- ✅ 手动重连控制

### 3. DataUpdater - 数据更新器
- ✅ 多种动画效果（pulse, glow, shake, bounce, fade）
- ✅ 更新指示器
- ✅ 数据变化检测
- ✅ 性能优化

### 4. RealtimeDemo - 演示组件
- ✅ 完整功能演示
- ✅ 模拟数据生成
- ✅ 交互式界面

## 📦 组件使用

### 基本用法

```tsx
import { RealtimeProvider, DataUpdater, useRealtimeContext } from '@/components/dashboard/Realtime';

// 1. 包装应用
function App() {
  return (
    <RealtimeProvider
      enableAnimations={true}
      enableNotifications={true}
      notificationDuration={3000}
    >
      <Dashboard />
    </RealtimeProvider>
  );
}

// 2. 使用上下文
function Dashboard() {
  const { 
    isConnected, 
    connectionStatus, 
    realtimeData,
    retryConnection 
  } = useRealtimeContext();

  return (
    <div>
      <div>状态: {connectionStatus}</div>
      {!isConnected && (
        <button onClick={retryConnection}>重连</button>
      )}
    </div>
  );
}

// 3. 数据更新动画
function Widget({ widgetId }) {
  return (
    <DataUpdater
      widgetId={widgetId}
      animationType="pulse"
      showUpdateIndicator={true}
    >
      <div>Widget Content</div>
    </DataUpdater>
  );
}
```

### 高级用法

```tsx
// 使用 Hook
function MyWidget({ widgetId }) {
  const { 
    data, 
    isUpdating, 
    updateCount, 
    lastUpdateTime 
  } = useDataUpdater(widgetId);

  return (
    <div className={isUpdating ? 'updating' : ''}>
      <div>数据: {JSON.stringify(data)}</div>
      <div>更新次数: {updateCount}</div>
      <div>最后更新: {lastUpdateTime?.toLocaleTimeString()}</div>
    </div>
  );
}

// 高阶组件
const EnhancedWidget = withDataUpdater(MyWidget, {
  animationType: 'glow',
  showUpdateIndicator: true
});
```

## 🔧 配置选项

### RealtimeProvider 配置

```tsx
interface RealtimeProviderProps {
  enableAnimations?: boolean;        // 启用动画 (默认: true)
  enableNotifications?: boolean;     // 启用通知 (默认: true)
  notificationDuration?: number;     // 通知持续时间 (默认: 3000ms)
}
```

### DataUpdater 配置

```tsx
interface DataUpdaterProps {
  widgetId: string;                  // Widget ID (必需)
  animationType?: 'pulse' | 'glow' | 'shake' | 'bounce' | 'fade';
  animationDuration?: number;        // 动画持续时间 (默认: 1000ms)
  showUpdateIndicator?: boolean;     // 显示更新指示器 (默认: true)
  onDataUpdate?: (data: any) => void; // 数据更新回调
}
```

### WebSocketClient 配置

```tsx
interface WebSocketClientProps {
  autoReconnect?: boolean;           // 自动重连 (默认: true)
  reconnectInterval?: number;        // 重连间隔 (默认: 3000ms)
  maxReconnectAttempts?: number;     // 最大重连次数 (默认: 5)
  enableHeartbeat?: boolean;         // 启用心跳 (默认: true)
  heartbeatInterval?: number;        // 心跳间隔 (默认: 30000ms)
}
```

## 🎨 动画类型

1. **pulse** - 脉冲缩放效果
2. **glow** - 发光边框效果
3. **shake** - 左右摇摆效果
4. **bounce** - 上下弹跳效果
5. **fade** - 透明度变化效果

## 📊 连接指标

系统会自动跟踪以下连接指标：

- **uptime** - 连接运行时间（秒）
- **reconnectAttempts** - 重连尝试次数
- **messagesReceived** - 接收消息数量
- **messagesSent** - 发送消息数量
- **lastHeartbeat** - 最后心跳时间
- **averageLatency** - 平均延迟（毫秒）

## 🔄 集成说明

### 与现有系统集成

1. **Dashboard 集成**
   ```tsx
   // DashboardMain.tsx 已集成
   <RealtimeProvider>
     <DashboardMainContent />
   </RealtimeProvider>
   ```

2. **GridItem 集成**
   ```tsx
   // GridItem.tsx 已集成
   <DataUpdater widgetId={widget.id}>
     <Card>...</Card>
   </DataUpdater>
   ```

3. **Hook 集成**
   ```tsx
   // 使用现有的 useRealtime hook
   const realtimeHook = useRealtime();
   ```

## 🧪 测试

运行测试：
```bash
npm test -- src/components/dashboard/Realtime/__tests__/
```

测试覆盖：
- ✅ 基本组件渲染
- ✅ 上下文提供和使用
- ✅ 错误边界处理
- ✅ 配置选项验证

## 🚀 性能优化

1. **内存管理**
   - 自动清理定时器
   - 组件卸载时断开连接
   - 防止内存泄漏

2. **动画优化**
   - 使用 Framer Motion 进行硬件加速
   - 动画状态自动清理
   - 批量更新处理

3. **网络优化**
   - 指数退避重连策略
   - 心跳检测连接健康
   - 消息队列管理

## 📝 需求对应

此实现满足任务 6.7 的所有要求：

- ✅ **创建 RealtimeProvider 组件，管理实时连接** - 完成
- ✅ **实现 WebSocket 客户端和数据更新** - 完成  
- ✅ **支持连接状态监控和自动重连** - 完成
- ✅ **添加数据更新动画和用户提示** - 完成
- ✅ **需求 2.1.2** - 实时数据功能已实现

## 🎯 使用示例

查看 `RealtimeDemo.tsx` 获取完整的使用示例和功能演示。

## 🔗 相关文件

- `RealtimeProvider.tsx` - 主要提供器组件
- `WebSocketClient.tsx` - WebSocket 客户端
- `DataUpdater.tsx` - 数据更新器
- `RealtimeDemo.tsx` - 功能演示
- `index.ts` - 导出文件
- `__tests__/` - 测试文件