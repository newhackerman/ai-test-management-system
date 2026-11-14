import { apiClient } from '@/services/api/client'

/**
 * 会议分析前端服务层。
 *
 * 对接后端 ai_analysis_routes.py 已有端点与后端组在建端点：
 * - GET  /api/v1/meetings/{id}/analytics          已有，返回 { success, data }
 * - GET  /api/v1/meetings/{id}/summary            已有；未生成时返回 generation_method='pending' 的空摘要（200）
 * - POST /api/v1/meetings/{id}/summary/generate   已有
 * - GET  /api/v1/meetings/{id}/minutes            已有，返回数组（未生成时为空数组）
 * - POST /api/v1/meetings/{id}/minutes/generate   已有
 * - GET/POST/PATCH/DELETE /api/v1/meetings/{id}/action-items
 *   后端组在建（基于 meeting_tasks 表，响应沿用 ai_analysis_schemas.py 的 ActionItem 字段）；
 *   未就绪时返回 404，前端以空态/错误态顶住，不编假数据。
 * - POST /api/v1/meetings/{id}/analytics/reports/generate（body { format: 'html' | 'markdown' }）
 *   + GET  /api/v1/meetings/{id}/analytics/reports/download?format=...
 *   后端组在建；下载路径为约定路径（以后端真实返回的 download_url 为准）。
 *
 * 本文件只做透传与必要的信封拆包，不加工、不编造任何业务数值。
 */

export interface ParticipationMetric {
  user_id: number
  user_name: string
  speaking_time_minutes: number
  speaking_percentage: number
  interaction_count: number
  engagement_score: number
  attention_score: number
  contribution_quality: number
}

export interface MeetingAnalyticsResponse {
  meeting_id: number
  overall_effectiveness: number
  participation_metrics: ParticipationMetric[]
  agenda_completion_rate: number
  decision_efficiency: number
  time_utilization: number
  sentiment_analysis: Record<string, unknown>
  improvement_suggestions: string[]
  meeting_quality_score: number
  network_quality_avg: number
  technical_issues_count: number
  analyzed_at: string
}

export interface SummaryKeyPoint {
  title: string
  content: string
  importance: number
  timestamp?: string | null
  participants?: string[] | null
}

export interface SummaryDecision {
  decision_id: string
  title: string
  description: string
  decision_maker?: string | null
  impact_level: string
  implementation_date?: string | null
  status: string
  related_requirements?: string[] | null
}

export interface ActionItem {
  action_id: string
  title: string
  description: string
  assignee?: string | null
  due_date?: string | null
  priority: string
  status: string
  estimated_hours?: number | null
  dependencies?: string[] | null
}

export interface MeetingSummaryResponse {
  meeting_id: number
  overview: string
  key_points: SummaryKeyPoint[]
  decisions: SummaryDecision[]
  action_items: ActionItem[]
  next_steps: string[]
  participants_summary: Record<string, unknown>
  meeting_effectiveness: Record<string, unknown>
  generated_at: string
  generation_method: string
  language: string
}

export interface MeetingMinutesResponse {
  id: number
  meeting_id: number
  title: string
  content: string
  summary?: string | null
  minute_type: string
  generation_method: string
  agenda_items?: Array<Record<string, unknown>> | null
  decisions?: Array<Record<string, unknown>> | null
  action_items?: Array<Record<string, unknown>> | null
  attendees?: string[] | null
  key_points?: Array<Record<string, unknown>> | null
  status: string
  approval_required: boolean
  version: string
  parent_minute_id?: number | null
  approved_by?: number | null
  approved_at?: string | null
  created_at: string
  updated_at: string
  created_by?: number | null
}

export interface ActionItemCreateInput {
  title: string
  description?: string
  assignee?: string
  due_date?: string | null
  priority?: string
  status?: string
  estimated_hours?: number | null
  dependencies?: string[]
}

export type ActionItemUpdateInput = Partial<ActionItemCreateInput>

export interface ReportGenerateResult {
  /** 后端返回的下载地址（若有，以它为准） */
  downloadUrl?: string | null
  reportId?: string | number | null
  fileName?: string | null
  /** 后端直接以文本/文件体返回时，携带内容 */
  content?: string | null
  contentType?: string | null
}

const unwrap = <T,>(payload: unknown): T => {
  const body = payload as { data?: T } | null
  if (body && typeof body === 'object' && 'data' in body && body.data !== undefined) {
    return body.data as T
  }
  return payload as T
}

const unwrapList = <T,>(payload: unknown): T[] => {
  const body = payload as { data?: T[] } | null
  if (Array.isArray(payload)) return payload as T[]
  if (body && typeof body === 'object' && Array.isArray(body.data)) return body.data as T[]
  return []
}

export const isNotFoundError = (error: unknown): boolean => {
  const status = (error as { response?: { status?: number } })?.response?.status
  return status === 404
}

export const apiErrorMessage = (error: unknown, fallback: string): string => {
  const data = (error as { response?: { data?: unknown } })?.response?.data as
    | { detail?: unknown; message?: unknown }
    | undefined
  const detail = data?.detail ?? data?.message
  if (typeof detail === 'string' && detail) return detail
  if (error instanceof Error && error.message) return error.message
  return fallback
}

/** 404 是预期状态（端点/数据尚未就绪）时，压住 apiClient 的全局错误提示，页面自己展示空态/错误态。 */
const silent404 = { silent404: true } as unknown as import('axios').AxiosRequestConfig

export const analyticsService = {
  async getAnalytics(meetingId: number): Promise<MeetingAnalyticsResponse> {
    const response = await apiClient.get(`/meetings/${meetingId}/analytics`)
    return unwrap<MeetingAnalyticsResponse>(response.data)
  },

  async getSummary(meetingId: number): Promise<MeetingSummaryResponse> {
    const response = await apiClient.get(`/meetings/${meetingId}/summary`, silent404)
    return unwrap<MeetingSummaryResponse>(response.data)
  },

  async generateSummary(
    meetingId: number,
    request: { summary_length?: string; language?: string } = {},
  ): Promise<MeetingSummaryResponse> {
    const response = await apiClient.post(`/meetings/${meetingId}/summary/generate`, {
      include_transcript: true,
      include_chat: true,
      include_files: false,
      summary_length: request.summary_length ?? 'medium',
      language: request.language ?? 'zh-CN',
    })
    return unwrap<MeetingSummaryResponse>(response.data)
  },

  async getMinutes(meetingId: number): Promise<MeetingMinutesResponse[]> {
    const response = await apiClient.get(`/meetings/${meetingId}/minutes`, silent404)
    return unwrapList<MeetingMinutesResponse>(response.data)
  },

  async generateMinutes(
    meetingId: number,
    request: { template_type?: string; format_style?: string } = {},
  ): Promise<MeetingMinutesResponse> {
    const response = await apiClient.post(`/meetings/${meetingId}/minutes/generate`, {
      template_type: request.template_type ?? 'standard',
      include_summary: true,
      include_transcript: false,
      include_attachments: true,
      format_style: request.format_style ?? 'formal',
      language: 'zh-CN',
      auto_structure: true,
    })
    return unwrap<MeetingMinutesResponse>(response.data)
  },

  async getActionItems(meetingId: number): Promise<ActionItem[]> {
    const response = await apiClient.get(`/meetings/${meetingId}/action-items`, silent404)
    return unwrapList<ActionItem>(response.data)
  },

  async createActionItem(meetingId: number, input: ActionItemCreateInput): Promise<ActionItem> {
    const response = await apiClient.post(`/meetings/${meetingId}/action-items`, input)
    return unwrap<ActionItem>(response.data)
  },

  async updateActionItem(
    meetingId: number,
    actionId: string | number,
    input: ActionItemUpdateInput,
  ): Promise<ActionItem> {
    const response = await apiClient.patch(
      `/meetings/${meetingId}/action-items/${actionId}`,
      input,
    )
    return unwrap<ActionItem>(response.data)
  },

  async deleteActionItem(meetingId: number, actionId: string | number): Promise<void> {
    await apiClient.delete(`/meetings/${meetingId}/action-items/${actionId}`)
  },

  /**
   * 生成分析报告。约定：POST 返回 JSON 信封，内含 download_url（优先）、
   * 或 report_id（再用 GET 下载端点取文件）、或直接返回文件内容。
   * 若后端直接以文件体响应（Content-Type 非 JSON），按内容处理。
   */
  async generateReport(
    meetingId: number,
    format: 'html' | 'markdown',
  ): Promise<ReportGenerateResult> {
    const response = await apiClient.post(
      `/meetings/${meetingId}/analytics/reports/generate`,
      { format },
      silent404,
    )
    const contentType: string = response.headers?.['content-type'] ?? ''
    const payload = response.data
    if (typeof payload === 'string') {
      return { content: payload, contentType, fileName: `meeting-${meetingId}-report.${format === 'html' ? 'html' : 'md'}` }
    }
    const data = unwrap<Record<string, unknown>>(payload)
    if (data && typeof data === 'object') {
      return {
        downloadUrl:
          (data.download_url as string | undefined) ??
          (data.downloadUrl as string | undefined) ??
          null,
        reportId: (data.report_id as string | number | undefined) ?? (data.id as string | number | undefined) ?? null,
        fileName: (data.file_name as string | undefined) ?? (data.filename as string | undefined) ?? null,
        content: typeof data.content === 'string' ? (data.content as string) : null,
        contentType,
      }
    }
    return {}
  },

  /** 按约定下载端点取报告文件，返回 Blob。以后端返回的 download_url 为准时调用方直接用该 URL。 */
  async downloadReport(meetingId: number, format: 'html' | 'markdown'): Promise<Blob> {
    const response = await apiClient.get(
      `/meetings/${meetingId}/analytics/reports/download`,
      { params: { format }, responseType: 'blob', ...silent404 },
    )
    return response.data as Blob
  },
}

/** 把 Blob/文本内容触发为浏览器下载。 */
export const triggerBlobDownload = (blob: Blob, fileName: string): string => {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  return url
}
