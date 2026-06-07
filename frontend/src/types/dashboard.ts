// 仪表板相关类型定义

// 角色类型
export type RoleType = 
  | 'ADMIN'
  | 'PROJECT_MANAGER'
  | 'REQUIREMENT_MANAGER'
  | 'DESIGNER'
  | 'ARCHITECT'
  | 'DEVELOPER'
  | 'TESTER'
  | 'DEVOPS'
  | 'THIRD_PARTY'

// 布局项
export interface LayoutItem {
  i: string // 唯一标识
  x: number // x坐标
  y: number // y坐标
  w: number // 宽度
  h: number // 高度
  minW?: number // 最小宽度
  minH?: number // 最小高度
  maxW?: number // 最大宽度
  maxH?: number // 最大高度
  static?: boolean // 是否静态（不可拖拽）
  isDraggable?: boolean // 是否可拖拽
  isResizable?: boolean // 是否可调整大小
}

// 仪表板配置
export interface DashboardConfig {
  id: string
  userId: number
  roleType: RoleType
  dashboardName: string
  isDefault: boolean
  layoutConfig?: {
    items: LayoutItem[]
    cols?: number
    rowHeight?: number
    margin?: [number, number]
    containerPadding?: [number, number]
  }
  defaultLayoutConfig?: {
    items: LayoutItem[]
    cols?: number
    rowHeight?: number
    margin?: [number, number]
    containerPadding?: [number, number]
  }
  widgetConfigs?: WidgetConfig[]
  themeConfig?: ThemeConfig
  refreshInterval: number
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

// 组件定义
export interface WidgetDefinition {
  id: string
  widgetType: string
  widgetName: string
  description?: string
  category: WidgetCategory
  defaultConfig?: WidgetConfig
  dataSourceConfig?: DataSourceConfig
  supportedRoles: RoleType[]
  minWidth: number
  minHeight: number
  maxWidth: number
  maxHeight: number
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

// 组件分类
export type WidgetCategory = 
  | 'STATISTICS'
  | 'CHARTS'
  | 'PROGRESS'
  | 'STATUS'
  | 'RANKING'
  | 'CALENDAR'
  | 'MAP'
  | 'TABLE'

// 组件实例
export interface WidgetInstance {
  id: string
  type: string
  title: string
  config?: WidgetConfig
  position: {
    x: number
    y: number
    w: number
    h: number
  }
  isVisible: boolean
  createdAt: Date
  updatedAt: Date
}

// 组件配置
export interface WidgetConfig {
  title?: string
  showTitle?: boolean
  showBorder?: boolean
  backgroundColor?: string
  textColor?: string
  refreshInterval?: number
  dataSource?: DataSourceConfig
  chartConfig?: ChartConfig
  filterConfig?: FilterConfig
  [key: string]: any
}

// 数据源配置
export interface DataSourceConfig {
  type: 'api' | 'websocket' | 'static'
  url?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  headers?: Record<string, string>
  params?: Record<string, any>
  body?: any
  transform?: string // 数据转换函数
  cache?: {
    enabled: boolean
    ttl: number // 缓存时间（秒）
  }
}

// 图表配置
export interface ChartConfig {
  type: 'line' | 'bar' | 'pie' | 'area' | 'scatter' | 'gauge' | 'heatmap'
  xAxis?: AxisConfig
  yAxis?: AxisConfig
  series?: SeriesConfig[]
  legend?: LegendConfig
  tooltip?: TooltipConfig
  colors?: string[]
  animation?: boolean
}

// 轴配置
export interface AxisConfig {
  show: boolean
  type?: 'category' | 'value' | 'time'
  name?: string
  min?: number | string
  max?: number | string
  interval?: number
  formatter?: string
}

// 系列配置
export interface SeriesConfig {
  name: string
  type: string
  data: any[]
  color?: string
  smooth?: boolean
  stack?: string
}

// 图例配置
export interface LegendConfig {
  show: boolean
  position: 'top' | 'bottom' | 'left' | 'right'
  orient: 'horizontal' | 'vertical'
}

// 提示框配置
export interface TooltipConfig {
  show: boolean
  trigger: 'item' | 'axis'
  formatter?: string
}

// 过滤器配置
export interface FilterConfig {
  enabled: boolean
  filters: FilterItem[]
}

// 过滤项
export interface FilterItem {
  field: string
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'nin' | 'like'
  value: any
  label?: string
}

// 组件数据
export interface WidgetData {
  data: any
  timestamp: Date
  error?: string
  loading?: boolean
  metadata?: {
    total?: number
    page?: number
    pageSize?: number
    [key: string]: any
  }
}

// 配色方案
export interface ColorScheme {
  id: string
  schemeName: string
  schemeType: 'SYSTEM' | 'ENTERPRISE' | 'USER_CUSTOM'
  schemeCategory?: string
  colorPalette: string[]
  description?: string
  previewImage?: string
  isDefault: boolean
  isPublic: boolean
  isActive: boolean
  createdBy?: number
  organizationId?: number
  usageCount: number
  rating: number
  createdAt: Date
  updatedAt: Date
}

// 主题配置
export interface ThemeConfig {
  primaryColor: string
  borderRadius: number
  componentSize: 'small' | 'middle' | 'large'
  wireframe: boolean
}

// 布局偏好
export interface LayoutPreferences {
  gridSettings: {
    cols: number
    rowHeight: number
    margin: [number, number]
    containerPadding: [number, number]
  }
  compactMode: boolean
  showGridLines: boolean
  snapToGrid: boolean
}

// 通知设置
export interface NotificationSettings {
  dataUpdates: boolean
  systemAlerts: boolean
  projectNotifications: boolean
  emailNotifications: boolean
  pushNotifications: boolean
  soundEnabled: boolean
}

// 实时事件类型
export type RealtimeEventType = 
  | 'project_update'
  | 'requirement_update'
  | 'test_update'
  | 'system_alert'
  | 'user_activity'
  | 'data_refresh'

// 实时消息
export interface RealtimeMessage {
  id: string
  type: 'heartbeat' | 'data_update' | 'event' | 'error'
  eventType?: RealtimeEventType
  data: any
  timestamp: Date
  targetUsers?: number[]
  targetRoles?: RoleType[]
}

// WebSocket连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'

// 数据缓存项
export interface CacheItem<T = any> {
  data: T
  timestamp: Date
  ttl: number
  key: string
}

// 离线操作
export interface OfflineAction {
  id: string
  type: string
  data: any
  timestamp: Date
  retries: number
  maxRetries: number
}

// 性能指标
export interface PerformanceMetrics {
  latency: number
  messageCount: number
  errorCount: number
  uptime: number
  memoryUsage?: number
  renderTime?: number
}

// 用户活动
export interface UserActivity {
  userId: number
  action: string
  target: string
  timestamp: Date
  metadata?: Record<string, any>
}

// 导出/导入数据格式
export interface ExportData {
  version: string
  exportTime: Date
  preferences: any
  dashboards: DashboardConfig[]
  widgets: WidgetConfig[]
  colorSchemes: ColorScheme[]
}