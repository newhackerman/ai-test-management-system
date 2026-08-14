// 全局状态管理入口文件

// 基础状态管理
export { useAuthStore } from './auth'
export { useUIStore } from './ui'
export { useAppStore } from './app'

// 查询状态管理
export { useQueryStore, useQuery, useMutation } from './query'

// 仪表板状态管理
export { 
  useDashboardStore, 
  dashboardSelectors,
  subscribeToDashboardChanges,
  subscribeToLayoutChanges,
  subscribeToEditModeChanges
} from './dashboard'

export { 
  useWidgetStore,
  widgetSelectors,
  subscribeToWidgetData,
  subscribeToWidgetConfig,
  subscribeToWidgetSelection,
  subscribeToWidgetErrors
} from './widget'

export { 
  useRealtimeStore,
  realtimeSelectors,
  subscribeToConnectionStatus,
  subscribeToRealtimeData,
  subscribeToConnectionErrors
} from './realtime'

export { 
  useUserPreferencesStore,
  userPreferencesSelectors,
  subscribeToThemeChanges,
  subscribeToColorSchemeChanges,
  subscribeToLayoutPreferencesChanges
} from './userPreferences'

// 会议状态管理
export { 
  useMeetingRoomStore,
  selectConnectionStatus,
  selectIsConnected,
  selectParticipants,
  selectLocalParticipant,
  selectMessages,
  selectUnreadCount,
  selectSharedFiles,
  selectIsRecording,
  selectNetworkQuality,
  selectMediaDevices,
  selectPermissions,
  selectConfig,
  subscribeToConnectionStatus as subscribeToMeetingConnectionStatus,
  subscribeToParticipants,
  subscribeToMessages,
  subscribeToRecordingState,
  meetingRoomUtils
} from './meeting/meetingRoomStore'

// 会议分析状态管理
export {
  useAnalyticsStore,
  type MeetingEffectivenessData,
  type ParticipationAnalysisData,
  type MeetingSummaryData,
  type ChartConfig,
  type ReportGenerationStatus
} from './meeting/analyticsStore'

// 查询客户端和工具
export { queryClient, queryKeys } from '@/lib/query-client'

// 查询hooks
export * from '@/hooks/use-queries'

// 查询服务
export { queryServices } from '@/services/query-services'

// 开发工具
export { QueryDevtools, QueryDevtoolsProvider } from '@/components/dev/QueryDevtools'

// 类型定义
export type * from './query'
export type * from './meeting/meetingRoomStore'