import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import {
  analyticsService,
  apiErrorMessage,
  isNotFoundError,
  triggerBlobDownload,
  type ActionItem,
  type MeetingAnalyticsResponse,
  type MeetingMinutesResponse,
  type MeetingSummaryResponse,
  type ParticipationMetric,
} from '@/services/meeting/analyticsService'

/**
 * 会议分析状态层：只存后端接口直接返回的数据，不编造任何数值。
 *
 * 数据来源：
 * - 效果分析 / 参与度：GET /api/v1/meetings/{id}/analytics（参与度复用同一返回体的
 *   participation_metrics 列表；接口未返回逐人数据时为空列表，页面展示“暂无数据”）。
 * - 摘要：GET /api/v1/meetings/{id}/summary；未生成时后端返回 generation_method='pending'
 *   的空摘要，store 记为 null（未生成），页面展示空态 + 生成入口。
 * - 报告：POST /api/v1/meetings/{id}/analytics/reports/generate，进度按真实请求阶段推进，
 *   不再用 setTimeout 假进度；端点未就绪（404）时进入错误态。
 *
 * 注意：后端当前返回的部分指标（如情感评分）仍为固定值，属后端待改造项；
 * 前端只原样展示接口返回值，不在本地改写或“修正”数字。
 */

/** 效果分析 = 后端 MeetingAnalyticsResponse 原样 */
export type MeetingEffectivenessData = MeetingAnalyticsResponse

export interface ParticipationAnalysisData {
  meetingId: number
  participants: ParticipationMetric[]
  /** 接口是否返回了逐人参与数据 */
  hasData: boolean
  averageEngagement: number | null
  averageSpeakingTime: number | null
  totalInteractions: number | null
}

/** 会议摘要 = 后端 MeetingSummaryResponse 原样 */
export type MeetingSummaryData = MeetingSummaryResponse

export type MeetingMinutesData = MeetingMinutesResponse
export type MeetingActionItemData = ActionItem

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
  /** 生成完成后可下载的地址（后端返回的 download_url，或本地 Blob URL） */
  downloadUrl?: string | null
  fileName?: string | null
}

interface AnalyticsState {
  effectivenessData: Record<number, MeetingEffectivenessData>
  participationData: Record<number, ParticipationAnalysisData>
  summaryData: Record<number, MeetingSummaryData | null>
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
  generateSummary: (meetingId: number) => Promise<boolean>
  fetchAllAnalyticsData: (meetingId: number) => Promise<void>
  updateChartConfig: (chartId: string, config: ChartConfig) => void
  resetChartConfigs: () => void
  generateReport: (meetingId: number, reportType: string, options?: any) => Promise<boolean>
  resetReportGeneration: () => void
  updateEffectivenessData: (meetingId: number, data: MeetingEffectivenessData) => void
  updateParticipationData: (meetingId: number, data: ParticipationAnalysisData) => void
  updateSummaryData: (meetingId: number, data: MeetingSummaryData | null) => void
  clearAnalyticsData: () => void
  clearMeetingData: (meetingId: number) => void
  setError: (error: string | null) => void
}

const deriveParticipation = (
  meetingId: number,
  analytics: MeetingEffectivenessData,
): ParticipationAnalysisData => {
  const participants = Array.isArray(analytics.participation_metrics)
    ? analytics.participation_metrics
    : []
  const average = (values: number[]): number | null =>
    values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : null
  return {
    meetingId,
    participants,
    hasData: participants.length > 0,
    averageEngagement: average(participants.map((p) => p.engagement_score)),
    averageSpeakingTime: average(participants.map((p) => p.speaking_time_minutes)),
    totalInteractions:
      participants.length > 0
        ? participants.reduce((sum, p) => sum + (p.interaction_count || 0), 0)
        : null,
  }
}

/** 未生成摘要的判定：后端以 generation_method='pending' + 空 overview 表示尚未生成。 */
const isSummaryGenerated = (summary: MeetingSummaryResponse | null | undefined): boolean => {
  if (!summary) return false
  if (summary.generation_method === 'pending') return false
  return Boolean(summary.overview && summary.overview.trim().length > 0)
}

const formatNumber = (value: number | null | undefined): string =>
  value === null || value === undefined || Number.isNaN(value) ? '暂无数据' : value.toFixed(2)

export { formatNumber }

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
          const data = await analyticsService.getAnalytics(meetingId)
          set((state) => ({
            effectivenessData: { ...state.effectivenessData, [meetingId]: data },
            participationData: {
              ...state.participationData,
              [meetingId]: deriveParticipation(meetingId, data),
            },
            isLoadingEffectiveness: false,
            isLoadingParticipation: false,
          }))
        } catch (error) {
          set({
            error: apiErrorMessage(error, '获取效果分析数据失败'),
            isLoadingEffectiveness: false,
          })
        }
      },

      fetchParticipationData: async (meetingId) => {
        set({ isLoadingParticipation: true, error: null })
        try {
          const cached = get().effectivenessData[meetingId]
          const data = cached ?? (await analyticsService.getAnalytics(meetingId))
          set((state) => ({
            effectivenessData: { ...state.effectivenessData, [meetingId]: data },
            participationData: {
              ...state.participationData,
              [meetingId]: deriveParticipation(meetingId, data),
            },
            isLoadingParticipation: false,
            isLoadingEffectiveness: false,
          }))
        } catch (error) {
          set({
            error: apiErrorMessage(error, '获取参与度分析数据失败'),
            isLoadingParticipation: false,
          })
        }
      },

      fetchSummaryData: async (meetingId) => {
        set({ isLoadingSummary: true, error: null })
        try {
          const data = await analyticsService.getSummary(meetingId)
          set((state) => ({
            summaryData: {
              ...state.summaryData,
              [meetingId]: isSummaryGenerated(data) ? data : null,
            },
            isLoadingSummary: false,
          }))
        } catch (error) {
          if (isNotFoundError(error)) {
            // 摘要尚未生成：不是错误，是空态。
            set((state) => ({
              summaryData: { ...state.summaryData, [meetingId]: null },
              isLoadingSummary: false,
            }))
          } else {
            set({
              error: apiErrorMessage(error, '获取会议摘要数据失败'),
              isLoadingSummary: false,
            })
          }
        }
      },

      generateSummary: async (meetingId) => {
        set({ isLoadingSummary: true, error: null })
        try {
          const data = await analyticsService.generateSummary(meetingId)
          set((state) => ({
            summaryData: {
              ...state.summaryData,
              [meetingId]: isSummaryGenerated(data) ? data : null,
            },
            isLoadingSummary: false,
          }))
          return isSummaryGenerated(data)
        } catch (error) {
          set({
            error: apiErrorMessage(error, '生成会议摘要失败'),
            isLoadingSummary: false,
          })
          return false
        }
      },

      fetchAllAnalyticsData: async (meetingId) => {
        set({ isLoading: true })
        try {
          await Promise.all([
            get().fetchEffectivenessData(meetingId),
            get().fetchSummaryData(meetingId),
          ])
        } finally {
          set({ isLoading: false })
        }
      },

      updateChartConfig: (chartId, config) =>
        set((state) => ({ chartConfigs: { ...state.chartConfigs, [chartId]: config } })),
      resetChartConfigs: () => set({ chartConfigs: {} }),

      generateReport: async (meetingId, reportType, options = {}) => {
        const format: 'html' | 'markdown' =
          reportType === 'html' || options?.format === 'html' ? 'html' : 'markdown'
        const fileName =
          options?.fileName ?? `meeting-${meetingId}-report.${format === 'html' ? 'html' : 'md'}`
        set({
          reportGeneration: {
            isGenerating: true,
            progress: 10,
            currentStep: '正在请求后端生成报告…',
            error: undefined,
            downloadUrl: null,
            fileName,
          },
        })
        try {
          const result = await analyticsService.generateReport(meetingId, format)
          set((state) => ({
            reportGeneration: { ...state.reportGeneration, progress: 60, currentStep: '后端已返回，正在准备下载…' },
          }))

          let downloadUrl: string | null = result.downloadUrl ?? null
          if (!downloadUrl && result.content) {
            const mime = format === 'html' ? 'text/html;charset=utf-8' : 'text/markdown;charset=utf-8'
            downloadUrl = triggerBlobDownload(new Blob([result.content], { type: mime }), fileName)
          } else if (!downloadUrl && result.reportId !== null && result.reportId !== undefined) {
            const blob = await analyticsService.downloadReport(meetingId, format)
            downloadUrl = triggerBlobDownload(blob, result.fileName ?? fileName)
          }

          set({
            reportGeneration: {
              isGenerating: false,
              progress: 100,
              currentStep: downloadUrl ? '报告生成完成，可下载' : '报告生成完成',
              downloadUrl,
              fileName: result.fileName ?? fileName,
            },
          })
          return true
        } catch (error) {
          const message = isNotFoundError(error)
            ? '报告生成接口尚未就绪（后端未提供该端点，404），请等待后端组提供端点后重试。'
            : apiErrorMessage(error, '报告生成失败')
          set({
            reportGeneration: {
              isGenerating: false,
              progress: 0,
              currentStep: '报告生成失败',
              error: message,
              downloadUrl: null,
              fileName,
            },
          })
          return false
        }
      },

      resetReportGeneration: () =>
        set({ reportGeneration: { isGenerating: false, progress: 0, currentStep: '' } }),
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
