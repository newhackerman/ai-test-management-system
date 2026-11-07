import api from './api'

export type MatrixType = 'requirement_to_test' | 'requirement_to_task' | 'requirement_to_design'

export interface TraceabilityMatrixResponse {
  project_id: number
  matrix_type: string
  requirements: Array<Record<string, any>>
  targets: Array<Record<string, any>>
  matrix_data: Record<string, Record<string, boolean>>
  coverage_stats: Record<string, any>
  generated_at: string
}

export interface ImpactItem {
  object_type: string
  object_id: number
  object_title: string
  impact_type: string
  impact_level: string
  impact_description: string
}

export interface ChangeImpactAnalysisResponse {
  requirement_id: number
  change_description: string
  direct_impacts: ImpactItem[]
  indirect_impacts: ImpactItem[]
  affected_requirements: number[]
  affected_test_cases: number[]
  affected_tasks: number[]
  risk_level: string
  recommendations: string[]
  analyzed_at: string
}

export interface TraceabilityCoverageResponse {
  project_id: number
  coverage_type: string
  coverage_stats: {
    project_id: number
    coverage_type: string
    total_requirements: number
    covered_requirements: number
    uncovered_requirements: number[]
    coverage_rate: number
  }
  generated_at: string
}

class TraceabilityService {
  private baseUrl = '/requirement-traceability'

  /** 生成追溯矩阵：需求行 × 目标列，matrix_data[需求 id][目标 id] 为是否关联 */
  async getTraceabilityMatrix(projectId: number, matrixType: MatrixType): Promise<TraceabilityMatrixResponse> {
    return api.post(`${this.baseUrl}/matrix`, {
      project_id: projectId,
      matrix_type: matrixType,
      include_indirect: false,
    })
  }

  /** 分析一次需求变更的影响：直接影响 + 间接影响 + 风险等级 + 建议 */
  async analyzeChangeImpact(
    requirementId: number,
    changeDescription: string,
    analysisDepth = 3,
  ): Promise<ChangeImpactAnalysisResponse> {
    return api.post(`${this.baseUrl}/impact-analysis`, {
      requirement_id: requirementId,
      change_description: changeDescription,
      analysis_depth: analysisDepth,
    })
  }

  /** 项目追溯覆盖率统计 */
  async getTraceabilityCoverage(projectId: number): Promise<TraceabilityCoverageResponse> {
    return api.get(`${this.baseUrl}/coverage/${projectId}`)
  }

  /** 搜索追溯链接 */
  async searchTraceabilityLinks(params: Record<string, any>): Promise<{ links: any[]; total: number }> {
    return api.get(`${this.baseUrl}/links`, { params })
  }
}

export const traceabilityService = new TraceabilityService()
export default traceabilityService

/** 把分析对象下载为 JSON 文件（影响分析 / 覆盖率报告的导出都用它） */
export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
