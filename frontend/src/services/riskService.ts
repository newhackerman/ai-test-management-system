// @ts-nocheck
/**
 * 椋庨櫓绠＄悊鏈嶅姟
 * 
 * 鎻愪緵椤圭洰椋庨櫓绠＄悊鐨凙PI璋冪敤鍔熻兘锛屽寘鎷細
 * - 椋庨櫓CRUD鎿嶄綔
 * - 鏅鸿兘椋庨櫓璇嗗埆
 * - 椋庨櫓鐩戞帶鍜岄璀?
 * - 椋庨櫓鍒嗘瀽鍜屾姤鍛?
 */

import { apiClient } from '@/lib/api-client'

const unwrap = <T>(response: any): T => {
  if (response && typeof response === 'object' && 'data' in response) {
    return response.data as T
  }
  return response as T
}

// 椋庨櫓鐩稿叧绫诲瀷瀹氫箟
export enum RiskCategory {
  SCHEDULE = 'SCHEDULE',
  QUALITY = 'QUALITY',
  RESOURCE = 'RESOURCE',
  TECHNICAL = 'TECHNICAL',
  EXTERNAL = 'EXTERNAL'
}

export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum MitigationStrategy {
  AVOID = 'AVOID',
  MITIGATE = 'MITIGATE',
  TRANSFER = 'TRANSFER',
  ACCEPT = 'ACCEPT'
}

export enum RiskStatus {
  IDENTIFIED = 'IDENTIFIED',
  ANALYZING = 'ANALYZING',
  MITIGATING = 'MITIGATING',
  MONITORING = 'MONITORING',
  CLOSED = 'CLOSED'
}

export interface Risk {
  id: number
  project_id: number
  risk_name: string
  description: string
  risk_category: RiskCategory
  risk_level: RiskLevel
  probability: number
  impact_score: number
  risk_score?: number
  mitigation_strategy: MitigationStrategy
  mitigation_plan?: string
  contingency_plan?: string
  status: RiskStatus
  owner_id: number
  identified_date: string
  target_resolution_date?: string
  actual_resolution_date?: string
  created_by: number
  updated_by?: number
  created_at: string
  updated_at: string
}

export interface CreateRiskRequest {
  project_id: number
  risk_name: string
  description: string
  risk_category: RiskCategory
  risk_level: RiskLevel
  probability: number
  impact_score: number
  mitigation_strategy: MitigationStrategy
  mitigation_plan?: string
  contingency_plan?: string
  owner_id: number
  target_resolution_date?: string
}

export interface UpdateRiskRequest {
  risk_name?: string
  description?: string
  risk_category?: RiskCategory
  risk_level?: RiskLevel
  probability?: number
  impact_score?: number
  mitigation_strategy?: MitigationStrategy
  mitigation_plan?: string
  contingency_plan?: string
  status?: RiskStatus
  owner_id?: number
  target_resolution_date?: string
  actual_resolution_date?: string
}

export interface RiskListQuery {
  project_id?: number
  search?: string
  risk_category?: RiskCategory
  risk_level?: RiskLevel
  status?: RiskStatus
  owner_id?: number
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface RiskListResponse {
  risks: Risk[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface RiskMetrics {
  total_risks: number
  open_risks: number
  critical_risks: number
  high_risks: number
  medium_risks: number
  low_risks: number
  average_risk_score: number
  risk_trend: string
}

export interface RiskCategoryAnalysis {
  category: RiskCategory
  count: number
  percentage: number
  average_score: number
}

export interface RiskAnalysisResponse {
  project_id: number
  analysis_date: string
  metrics: RiskMetrics
  category_analysis: RiskCategoryAnalysis[]
  top_risks: Risk[]
  recommendations: string[]
}

export interface RiskAlert {
  risk_id: number
  alert_type: string
  severity: string
  message: string
  recommendation?: string
  created_at: string
}

export interface AutoRiskDetectionResult {
  project_id: number
  detection_time: string
  detected_risks: any[]
  risk_indicators: Record<string, any>
  recommendations: string[]
}

export interface RiskTrendData {
  trend_date: string
  total_risks: number
  new_risks: number
  closed_risks: number
  average_score: number
  critical_count: number
}

export interface RiskTrendResponse {
  project_id: number
  start_date: string
  end_date: string
  trend_data: RiskTrendData[]
  summary: Record<string, any>
}

export class RiskService {
  private baseUrl = '/api/v1/risks'

  /**
   * 鍒涘缓椤圭洰椋庨櫓
   */
  async createRisk(riskData: CreateRiskRequest): Promise<Risk> {
    const response = await apiClient.post<Risk>(`${this.baseUrl}/`, riskData)
    return unwrap<Risk>(response)
  }

  /**
   * 鑾峰彇椋庨櫓璇︽儏
   */
  async getRisk(riskId: number): Promise<Risk> {
    const response = await apiClient.get<Risk>(`${this.baseUrl}/${riskId}`)
    return unwrap<Risk>(response)
  }

  /**
   * 鏇存柊椤圭洰椋庨櫓
   */
  async updateRisk(riskId: number, riskData: UpdateRiskRequest): Promise<Risk> {
    const response = await apiClient.put<Risk>(`${this.baseUrl}/${riskId}`, riskData)
    return unwrap<Risk>(response)
  }

  /**
   * 鍒犻櫎椤圭洰椋庨櫓
   */
  async deleteRisk(riskId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${riskId}`)
  }

  /**
   * 鑾峰彇椋庨櫓鍒楄〃
   */
  async listRisks(query: RiskListQuery = {}): Promise<RiskListResponse> {
    const params = new URLSearchParams()
    
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString())
      }
    })

    const queryString = params.toString()
    const response = await apiClient.get<RiskListResponse>(
      queryString ? `${this.baseUrl}/?${queryString}` : `${this.baseUrl}/`
    )
    const payload = unwrap<any>(response)
    const risks = payload?.risks || payload?.data || payload?.items || []
    return {
      risks,
      total: payload?.total || risks.length,
      page: payload?.page || query.page || 1,
      page_size: payload?.page_size || query.page_size || 20,
      total_pages: payload?.total_pages || 1,
    }
  }

  /**
   * 鑷姩妫€娴嬮」鐩闄?
   */
  async autoDetectRisks(projectId: number): Promise<AutoRiskDetectionResult> {
    const response = await apiClient.post<AutoRiskDetectionResult>(
      `${this.baseUrl}/auto-detect?project_id=${projectId}`
    )
    return unwrap<AutoRiskDetectionResult>(response)
  }

  /**
   * 鑾峰彇椋庨櫓鍒嗘瀽鎶ュ憡
   */
  async getRiskAnalysis(projectId: number): Promise<RiskAnalysisResponse> {
    const response = await apiClient.get<RiskAnalysisResponse>(`${this.baseUrl}/analysis/${projectId}`)
    return unwrap<RiskAnalysisResponse>(response)
  }

  /**
   * 鑾峰彇椋庨櫓瓒嬪娍鍒嗘瀽
   */
  async getRiskTrend(projectId: number, days: number = 30): Promise<RiskTrendResponse> {
    const response = await apiClient.get<RiskTrendResponse>(
      `${this.baseUrl}/trend/${projectId}?days=${days}`
    )
    return unwrap<RiskTrendResponse>(response)
  }

  /**
   * 鍚姩椋庨櫓鐩戞帶
   */
  async startRiskMonitoring(projectId: number, intervalHours: number = 24): Promise<any> {
    const response = await apiClient.post(
      `${this.baseUrl}/monitor/start?project_id=${projectId}&interval_hours=${intervalHours}`
    )
    return unwrap<any>(response)
  }

  /**
   * 鍋滄椋庨櫓鐩戞帶
   */
  async stopRiskMonitoring(projectId: number): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/monitor/stop?project_id=${projectId}`)
    return unwrap<any>(response)
  }

  /**
   * 鑾峰彇椋庨櫓棰勮
   */
  async getRiskAlerts(projectId: number, days: number = 7): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/alerts/${projectId}?days=${days}`
    )
    return unwrap<any>(response)
  }

  /**
   * 鑾峰彇鐩戞帶鐘舵€?
   */
  async getMonitoringStatus(projectId: number): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/monitor/status/${projectId}`)
    return unwrap<any>(response)
  }

  /**
   * 鏇存柊鐩戞帶閰嶇疆
   */
  async updateMonitoringConfig(projectId: number, config: Record<string, any>): Promise<any> {
    const response = await apiClient.put(`${this.baseUrl}/monitor/config/${projectId}`, config)
    return unwrap<any>(response)
  }

  /**
   * 鐢熸垚椋庨櫓鎶ュ憡
   */
  async generateRiskReport(reportRequest: {
    project_id: number
    report_type: 'summary' | 'detailed' | 'trend'
    start_date?: string
    end_date?: string
    include_charts?: boolean
    format?: 'pdf' | 'excel' | 'json'
  }): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/report`, reportRequest)
    return unwrap<any>(response)
  }
}

// 瀵煎嚭鍗曚緥瀹炰緥
export const riskService = new RiskService()

// 宸ュ叿鍑芥暟
export const getRiskLevelColor = (level: RiskLevel): string => {
  const colorMap = {
    [RiskLevel.LOW]: 'green',
    [RiskLevel.MEDIUM]: 'yellow',
    [RiskLevel.HIGH]: 'orange',
    [RiskLevel.CRITICAL]: 'red'
  }
  return colorMap[level] || 'gray'
}

export const getRiskLevelText = (level: RiskLevel): string => {
  const textMap = {
    [RiskLevel.LOW]: '低风险',
    [RiskLevel.MEDIUM]: '中风险',
    [RiskLevel.HIGH]: '高风险',
    [RiskLevel.CRITICAL]: '严重风险'
  }
  return textMap[level] || level
}

export const getRiskCategoryText = (category: RiskCategory): string => {
  const textMap = {
    [RiskCategory.SCHEDULE]: '进度风险',
    [RiskCategory.QUALITY]: '质量风险',
    [RiskCategory.RESOURCE]: '资源风险',
    [RiskCategory.TECHNICAL]: '技术风险',
    [RiskCategory.EXTERNAL]: '外部风险'
  }
  return textMap[category] || category
}

export const getRiskStatusText = (status: RiskStatus): string => {
  const textMap = {
    [RiskStatus.IDENTIFIED]: '已识别',
    [RiskStatus.ANALYZING]: '分析中',
    [RiskStatus.MITIGATING]: '缓解中',
    [RiskStatus.MONITORING]: '监控中',
    [RiskStatus.CLOSED]: '已关闭'
  }
  return textMap[status] || status
}

export const getMitigationStrategyText = (strategy: MitigationStrategy): string => {
  const textMap = {
    [MitigationStrategy.AVOID]: '规避',
    [MitigationStrategy.MITIGATE]: '缓解',
    [MitigationStrategy.TRANSFER]: '转移',
    [MitigationStrategy.ACCEPT]: '接受'
  }
  return textMap[strategy] || strategy
}
