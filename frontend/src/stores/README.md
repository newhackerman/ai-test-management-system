# 仪表板状态管理系统

本文档描述了仪表板管理模块的状态管理架构和实现。

## 概述

仪表板状态管理系统基于 Zustand 构建，提供了完整的状态管理解决方案，包括：

- 仪表板配置管理
- 组件状态管理  
- 实时数据管理
- 用户偏好管理
- 数据同步和离线支持

## 架构设计

```
状态管理层
├── dashboard.ts          # 仪表板核心状态
├── widget.ts            # 组件状态管理
├── realtime.ts          # 实时数据状态
├── userPreferences.ts   # 用户偏好状态
└── index.ts            # 统一导出

服务层
├── dataSyncService.ts   # 数据同步服务
└── hooks/
    └── useDashboardState.ts  # 综合状态Hook

类型定义
└── types/dashboard.ts   # 类型定义
```

## 核心Store

### 1. Dashboard Store (dashboard.ts)

管理仪表板的核心状态，包括配置、布局、角色等。

**主要功能：**
- 仪表板配置管理
- 布局状态管理
- 角色切换
- 编辑模式控制
- 配置缓存

**关键方法：**
```typescript
// 配置管理
setCurrentConfig(config: DashboardConfig)
updateConfig(updates: Partial<DashboardConfig>)
cacheConfig(roleKey: string, config: DashboardConfig)

// 角色管理
setCurrentRole(role: RoleType)
switchRole(role: RoleType): Promise<void>

// 布局管理
setLayout(layout: LayoutItem[])
addLayoutItem(item: LayoutItem)
removeLayoutItem(itemId: string)
resetLayout()

// 编辑模式
setEditMode(enabled: boolean)
toggleEditMode()
```

### 2. Widget Store (widget.ts)

管理组件的定义、实例、数据和配置。

**主要功能：**
- 组件定义管理
- 组件实例管理
- 组件数据缓存
- 组件配置管理
- 加载状态和错误处理

**关键方法：**
```typescript
// 组件定义
setDefinitions(definitions: WidgetDefinition[])
addDefinition(definition: WidgetDefinition)

// 组件实例
addInstance(instance: WidgetInstance)
removeInstance(id: string)
updateInstance(id: string, updates: Partial<WidgetInstance>)

// 组件数据
setWidgetData(widgetId: string, data: WidgetData)
getWidgetData(widgetId: string): WidgetData | null

// 组件配置
setWidgetConfig(widgetId: string, config: WidgetConfig)
updateWidgetConfig(widgetId: string, updates: Partial<WidgetConfig>)
```

### 3. Realtime Store (realtime.ts)

管理WebSocket连接和实时数据推送。

**主要功能：**
- WebSocket连接管理
- 实时数据接收和分发
- 连接状态监控
- 离线队列管理
- 性能监控

**关键方法：**
```typescript
// 连接管理
connect(url: string, token: string): Promise<void>
disconnect()
reconnect(): Promise<void>

// 订阅管理
subscribe(eventTypes: string[])
unsubscribe(eventTypes: string[])
addEventHandler(eventType: string, handler: Function)

// 数据管理
updateRealtimeData(key: string, data: any)
handleMessage(message: any)

// 离线模式
setOffline(offline: boolean)
queueOfflineAction(action: string, data: any)
processOfflineQueue()
```

### 4. User Preferences Store (userPreferences.ts)

管理用户的个人偏好设置。

**主要功能：**
- 配色方案管理
- 主题配置
- 布局偏好
- 通知设置
- 可访问性设置
- 云端同步

**关键方法：**
```typescript
// 配色方案
setColorScheme(scheme: ColorScheme)
addCustomColorScheme(scheme: ColorScheme)

// 主题管理
setThemeConfig(config: Partial<ThemeConfig>)
toggleDarkMode()

// 同步管理
syncToCloud(): Promise<void>
syncFromCloud(): Promise<void>

// 导入导出
exportPreferences(): string
importPreferences(data: string)
```

## 数据同步服务

### DataSyncService

提供数据同步、离线支持和数据恢复功能。

**主要功能：**
- 网络状态监控
- 自动数据同步
- 离线队列管理
- 数据备份和恢复
- 性能优化

**使用方式：**
```typescript
import { dataSyncService, useDataSync } from '@/services/dataSyncService'

// 在组件中使用
const { getSyncStatus, manualSync, restoreFromBackup } = useDataSync()

// 获取同步状态
const status = getSyncStatus()

// 手动同步
await manualSync()

// 恢复备份
await restoreFromBackup()
```

## 综合状态Hook

### useDashboardState

提供统一的仪表板状态管理接口。

**使用方式：**
```typescript
import { useDashboardState } from '@/hooks/dashboard/useDashboardState'

function DashboardComponent() {
  const {
    // 状态
    currentConfig,
    layout,
    isEditMode,
    widgets,
    isOnline,
    
    // 方法
    initializeDashboard,
    saveDashboardLayout,
    addWidget,
    removeWidget,
    toggleEditMode,
    refreshAllWidgets
  } = useDashboardState('ADMIN')

  // 使用状态和方法...
}
```

## 状态持久化

使用 Zustand 的 persist 中间件实现状态持久化：

```typescript
persist(
  (set, get) => ({
    // store implementation
  }),
  {
    name: 'store-name',
    partialize: (state) => ({
      // 选择需要持久化的状态
    })
  }
)
```

**持久化策略：**
- Dashboard Store: 缓存配置和当前角色
- Widget Store: 持久化组件定义和配置
- User Preferences Store: 持久化所有用户偏好
- Realtime Store: 不持久化（运行时状态）

## 状态订阅

使用 subscribeWithSelector 中间件实现精确的状态订阅：

```typescript
// 订阅布局变更
const unsubscribe = subscribeToLayoutChanges((layout) => {
  console.log('Layout changed:', layout)
})

// 订阅连接状态
const unsubscribe = subscribeToConnectionStatus((isConnected) => {
  console.log('Connection status:', isConnected)
})

// 清理订阅
unsubscribe()
```

## 错误处理

每个 Store 都包含完整的错误处理机制：

```typescript
// 设置错误
setError(error: string | null)

// 清除错误
clearError()

// 获取错误
const error = store.error
```

## 性能优化

1. **选择器模式**：使用选择器函数避免不必要的重渲染
2. **数据缓存**：智能缓存组件数据和配置
3. **懒加载**：按需加载组件定义和数据
4. **批量更新**：合并多个状态更新
5. **内存管理**：及时清理不需要的数据

## 测试

每个 Store 都包含完整的单元测试：

```bash
# 运行所有状态管理测试
npm test stores/

# 运行特定Store测试
npm test stores/__tests__/dashboard.test.ts
```

## 最佳实践

1. **单一职责**：每个 Store 只管理相关的状态
2. **不可变更新**：使用不可变的方式更新状态
3. **类型安全**：使用 TypeScript 确保类型安全
4. **错误边界**：合理处理错误和异常情况
5. **性能监控**：监控状态更新的性能影响

## 扩展指南

### 添加新的Store

1. 创建新的Store文件
2. 定义状态接口和操作接口
3. 实现Store逻辑
4. 添加到index.ts导出
5. 编写单元测试

### 添加新的状态订阅

1. 在相应Store中添加订阅函数
2. 使用subscribeWithSelector中间件
3. 提供取消订阅机制

### 集成新的数据源

1. 在DataSyncService中添加数据源处理
2. 更新相应Store的数据获取逻辑
3. 添加错误处理和缓存策略

## 故障排除

### 常见问题

1. **状态不更新**：检查是否正确使用了不可变更新
2. **内存泄漏**：确保及时取消订阅和清理资源
3. **性能问题**：使用选择器避免不必要的重渲染
4. **同步失败**：检查网络状态和API接口

### 调试工具

1. **Zustand DevTools**：使用浏览器扩展调试状态
2. **React DevTools**：检查组件重渲染
3. **Network Tab**：监控API调用和WebSocket连接
4. **Console Logs**：查看详细的错误信息

## 更新日志

- v1.0.0: 初始实现，包含四个核心Store
- v1.1.0: 添加数据同步服务和离线支持
- v1.2.0: 添加综合状态Hook和性能优化