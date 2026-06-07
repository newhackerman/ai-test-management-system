// 会议分析模块导出
export { default as AnalyticsDashboard } from './AnalyticsDashboard'
export { default as ParticipationAnalysis } from './ParticipationAnalysis'
export { default as MeetingSummary } from './MeetingSummary'
export { default as MeetingMinutes } from './MeetingMinutes'
export { default as ActionItems } from './ActionItems'
export { default as ReportGenerator } from './ReportGenerator'
export { default as MeetingComparison } from './MeetingComparison'

// 布局和导航组件
export { default as AnalyticsLayout } from './AnalyticsLayout'
export { default as AnalyticsNavigation } from './AnalyticsNavigation'

// 图表组件库
export * from './charts'

// 类型导出
export type {
  MeetingEffectivenessData,
  ParticipationAnalysisData,
  MeetingSummaryData,
  ChartConfig,
  ReportGenerationStatus
} from '@/stores/meeting/analyticsStore'