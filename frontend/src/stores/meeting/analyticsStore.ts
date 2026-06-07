import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface MeetingEffectivenessData {
  meetingId: number
  overallScore: number
  participationMetrics: {
    averageParticipation: number
    speakingDistribution: Array<{
      userId: number
      userName: string
      speakingTime: number
      percentage: number
    }>
    interactionCount: number
    engagementScore: number
  }
  agendaCompletion: {
    totalItems: number
    completedItems: number
    completionRate: number
    timeUtilization: number
  }
  decisionEfficiency: {
    decisionsCount: number
    averageDecisionTime: number
    consensusRate: number
  }
  timeUtilization: {
    scheduledDuration: number
    actualDuration: number
    productiveTime: number
    utilizationRate: number
  }
  sentimentAnalysis: {
    overallSentiment: 'positive' | 'neutral' | 'negative'
    sentimentScore: number
    emotionalTrends: Array<{ timestamp: string; sentiment: number }>
  }
  improvementSuggestions: string[]
}

export interface ParticipationAnalysisData {
  meetingId: number
  participants: Array<{
    userId: number
    userName: string
    joinTime: string
    leaveTime?: string
    totalDuration: number
    speakingTime: number
    interactionCount: number
    attentionScore: number
    contributionScore: number
  }>
  overallMetrics: {
    averageAttendance: number
    averageSpeakingTime: number
    totalInteractions: number
    engagementTrend: Array<{ timeSlot: string; engagementLevel: number }>
  }
}

export interface MeetingSummaryData {
  meetingId: number
  title: string
  overview: string
  keyPoints: string[]
  decisions: Array<{
    id: string
    description: string
    decisionMaker: string
    timestamp: string
    impact: 'high' | 'medium' | 'low'
  }>
  actionItems: Array<{
    id: string
    task: string
    assignee: string
    deadline: string
    priority: 'high' | 'medium' | 'low'
    status: 'pending' | 'in_progress' | 'completed'
  }>
  nextSteps: string[]
  generatedAt: string
}

export interface ChartConfig {
  type: 'bar' | 'pie' | 'line' | 'heatmap' | 'area'
  title: string
  data: any[]
  options: Record<string, any>
  colors?: string[]
}

export interface ReportGenerationStatus {
  isGenerating: boolean
  progress: number
  currentStep: string
  error?: string
}

interface AnalyticsState {
  effectivenessData: Record<number, MeetingEffectivenessData>
  participationData: Record<number, ParticipationAnalysisData>
  summaryData: Record<number, MeetingSummaryData>
  selectedMeetingId: number | null
  activeTab: 'overview' | 'participation' | 'summary' | 'comparison'
  chartConfigs: Record<string, ChartConfig>
  isLoading: boolean
  isLoadingEffectiveness: boolean
  isLoadingParticipation: boolean
  isLoadingSummary: boolean
  reportGeneration: ReportGenerationStatus
  error: string | null
  setSelectedMeetingId: (meetingId: number | null) => void
  setActiveTab: (tab: AnalyticsState['activeTab']) => void
  fetchEffectivenessData: (meetingId: number) => Promise<void>
  fetchParticipationData: (meetingId: number) => Promise<void>
  fetchSummaryData: (meetingId: number) => Promise<void>
  fetchAllAnalyticsData: (meetingId: number) => Promise<void>
  updateChartConfig: (chartId: string, config: ChartConfig) => void
  resetChartConfigs: () => void
  generateReport: (meetingId: number, reportType: string, options?: any) => Promise<void>
  resetReportGeneration: () => void
  updateEffectivenessData: (meetingId: number, data: MeetingEffectivenessData) => void
  updateParticipationData: (meetingId: number, data: ParticipationAnalysisData) => void
  updateSummaryData: (meetingId: number, data: MeetingSummaryData) => void
  clearAnalyticsData: () => void
  clearMeetingData: (meetingId: number) => void
  setError: (error: string | null) => void
}

const createEffectivenessData = (meetingId: number): MeetingEffectivenessData => ({
  meetingId,
  overallScore: 85,
  participationMetrics: {
    averageParticipation: 78,
    speakingDistribution: [
      { userId: 1, userName: '张三', speakingTime: 15, percentage: 25 },
      { userId: 2, userName: '李四', speakingTime: 12, percentage: 20 },
      { userId: 3, userName: '王五', speakingTime: 18, percentage: 30 },
      { userId: 4, userName: '赵六', speakingTime: 15, percentage: 25 },
    ],
    interactionCount: 45,
    engagementScore: 82,
  },
  agendaCompletion: { totalItems: 5, completedItems: 4, completionRate: 80, timeUtilization: 85 },
  decisionEfficiency: { decisionsCount: 3, averageDecisionTime: 8, consensusRate: 90 },
  timeUtilization: { scheduledDuration: 60, actualDuration: 65, productiveTime: 55, utilizationRate: 85 },
  sentimentAnalysis: {
    overallSentiment: 'positive',
    sentimentScore: 0.7,
    emotionalTrends: [
      { timestamp: '09:00', sentiment: 0.6 },
      { timestamp: '09:15', sentiment: 0.8 },
      { timestamp: '09:30', sentiment: 0.7 },
      { timestamp: '09:45', sentiment: 0.9 },
    ],
  },
  improvementSuggestions: ['建议控制会议时长，避免超时', '鼓励更多参与者发言', '提前准备议程材料'],
})

const createParticipationData = (meetingId: number): ParticipationAnalysisData => ({
  meetingId,
  participants: [
    { userId: 1, userName: '张三', joinTime: '09:00:00', leaveTime: '10:05:00', totalDuration: 65, speakingTime: 15, interactionCount: 12, attentionScore: 85, contributionScore: 88 },
    { userId: 2, userName: '李四', joinTime: '09:02:00', leaveTime: '10:05:00', totalDuration: 63, speakingTime: 12, interactionCount: 8, attentionScore: 78, contributionScore: 75 },
    { userId: 3, userName: '王五', joinTime: '09:00:00', leaveTime: '10:05:00', totalDuration: 65, speakingTime: 18, interactionCount: 15, attentionScore: 92, contributionScore: 95 },
    { userId: 4, userName: '赵六', joinTime: '09:05:00', leaveTime: '10:00:00', totalDuration: 55, speakingTime: 15, interactionCount: 10, attentionScore: 80, contributionScore: 82 },
  ],
  overallMetrics: {
    averageAttendance: 95,
    averageSpeakingTime: 15,
    totalInteractions: 45,
    engagementTrend: [
      { timeSlot: '09:00-09:15', engagementLevel: 75 },
      { timeSlot: '09:15-09:30', engagementLevel: 85 },
      { timeSlot: '09:30-09:45', engagementLevel: 90 },
      { timeSlot: '09:45-10:00', engagementLevel: 88 },
    ],
  },
})

const createSummaryData = (meetingId: number): MeetingSummaryData => ({
  meetingId,
  title: '项目需求评审会议',
  overview: '本次会议讨论了项目需求规格，明确核心功能模块并分配后续任务。',
  keyPoints: ['确认用户管理模块核心功能', '讨论数据库设计方案', '评估技术风险和解决方案', '制定开发时间计划'],
  decisions: [
    { id: 'decision-1', description: '采用 React + TypeScript 技术栈', decisionMaker: '张三', timestamp: '09:15:00', impact: 'high' },
    { id: 'decision-2', description: '使用 MySQL 作为主数据库', decisionMaker: '李四', timestamp: '09:30:00', impact: 'medium' },
    { id: 'decision-3', description: '采用敏捷开发模式', decisionMaker: '王五', timestamp: '09:45:00', impact: 'high' },
  ],
  actionItems: [
    { id: 'action-1', task: '完成数据库设计文档', assignee: '张三', deadline: '2026-06-08', priority: 'high', status: 'pending' },
    { id: 'action-2', task: '搭建开发环境', assignee: '李四', deadline: '2026-06-05', priority: 'medium', status: 'in_progress' },
    { id: 'action-3', task: '准备 UI 设计稿', assignee: '王五', deadline: '2026-06-10', priority: 'medium', status: 'pending' },
  ],
  nextSteps: ['下周进行技术方案评审', '开始详细设计阶段', '准备开发环境和工具'],
  generatedAt: new Date().toISOString(),
})

export const useAnalyticsStore = create<AnalyticsState>()(
  devtools(
    (set, get) => ({
      effectivenessData: {},
      participationData: {},
      summaryData: {},
      selectedMeetingId: null,
      activeTab: 'overview',
      chartConfigs: {},
      isLoading: false,
      isLoadingEffectiveness: false,
      isLoadingParticipation: false,
      isLoadingSummary: false,
      reportGeneration: { isGenerating: false, progress: 0, currentStep: '' },
      error: null,

      setSelectedMeetingId: (meetingId) => set({ selectedMeetingId: meetingId }),
      setActiveTab: (tab) => set({ activeTab: tab }),

      fetchEffectivenessData: async (meetingId) => {
        set({ isLoadingEffectiveness: true, error: null })
        try {
          set((state) => ({
            effectivenessData: { ...state.effectivenessData, [meetingId]: createEffectivenessData(meetingId) },
            isLoadingEffectiveness: false,
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '获取效果分析数据失败', isLoadingEffectiveness: false })
        }
      },

      fetchParticipationData: async (meetingId) => {
        set({ isLoadingParticipation: true, error: null })
        try {
          set((state) => ({
            participationData: { ...state.participationData, [meetingId]: createParticipationData(meetingId) },
            isLoadingParticipation: false,
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '获取参与度分析数据失败', isLoadingParticipation: false })
        }
      },

      fetchSummaryData: async (meetingId) => {
        set({ isLoadingSummary: true, error: null })
        try {
          set((state) => ({
            summaryData: { ...state.summaryData, [meetingId]: createSummaryData(meetingId) },
            isLoadingSummary: false,
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '获取会议摘要数据失败', isLoadingSummary: false })
        }
      },

      fetchAllAnalyticsData: async (meetingId) => {
        set({ isLoading: true })
        try {
          await Promise.all([
            get().fetchEffectivenessData(meetingId),
            get().fetchParticipationData(meetingId),
            get().fetchSummaryData(meetingId),
          ])
        } finally {
          set({ isLoading: false })
        }
      },

      updateChartConfig: (chartId, config) =>
        set((state) => ({ chartConfigs: { ...state.chartConfigs, [chartId]: config } })),
      resetChartConfigs: () => set({ chartConfigs: {} }),

      generateReport: async (_meetingId, _reportType, _options = {}) => {
        const steps = ['准备生成报告...', '收集会议数据...', '分析参与度指标...', '生成效果评估...', '导出报告文件...']
        set({ reportGeneration: { isGenerating: true, progress: 0, currentStep: steps[0] } })

        for (let index = 0; index < steps.length; index += 1) {
          set((state) => ({
            reportGeneration: {
              ...state.reportGeneration,
              progress: Math.round(((index + 1) / steps.length) * 100),
              currentStep: steps[index],
            },
          }))
          await new Promise((resolve) => setTimeout(resolve, 200))
        }

        set({ reportGeneration: { isGenerating: false, progress: 100, currentStep: '报告生成完成' } })
      },

      resetReportGeneration: () => set({ reportGeneration: { isGenerating: false, progress: 0, currentStep: '' } }),
      updateEffectivenessData: (meetingId, data) =>
        set((state) => ({ effectivenessData: { ...state.effectivenessData, [meetingId]: data } })),
      updateParticipationData: (meetingId, data) =>
        set((state) => ({ participationData: { ...state.participationData, [meetingId]: data } })),
      updateSummaryData: (meetingId, data) =>
        set((state) => ({ summaryData: { ...state.summaryData, [meetingId]: data } })),

      clearAnalyticsData: () =>
        set({
          effectivenessData: {},
          participationData: {},
          summaryData: {},
          selectedMeetingId: null,
          activeTab: 'overview',
          chartConfigs: {},
          error: null,
        }),

      clearMeetingData: (meetingId) =>
        set((state) => {
          const effectivenessData = { ...state.effectivenessData }
          const participationData = { ...state.participationData }
          const summaryData = { ...state.summaryData }
          delete effectivenessData[meetingId]
          delete participationData[meetingId]
          delete summaryData[meetingId]
          return { effectivenessData, participationData, summaryData }
        }),

      setError: (error) => set({ error }),
    }),
    { name: 'analytics-store' },
  ),
)
