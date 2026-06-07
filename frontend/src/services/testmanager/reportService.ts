// @ts-nocheck
import { apiClient } from '../api/client'
import type {
  TestReport,
  ReportType,
  ReportFormat,
  PaginatedResponse
} from '../../types/testmanager'

export interface ReportFilters {
  search?: string
  test_plan_id?: number
  project_id?: number
  report_type?: ReportType
  report_format?: ReportFormat
  generated_by?: number
  created_after?: string
  created_before?: string
  page?: number
  size?: number
}

export interface GenerateReportRequest {
  test_plan_id?: number
  project_id: number
  report_name: string
  report_type: ReportType
  report_format: ReportFormat
  report_period_start?: string
  report_period_end?: string
  include_charts?: boolean
  include_details?: boolean
}

export class ReportService {
  private baseUrl = '/api/v1/test-reports'

  async getReports(filters?: ReportFilters): Promise<PaginatedResponse<TestReport>> {
    const params = new URLSearchParams()
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key === 'size' ? 'page_size' : key, String(value))
        }
      })
    }

    const response = await apiClient.get(`${this.baseUrl}?${params.toString()}`)
    return response.data
  }

  async getReport(id: number): Promise<TestReport> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)
    return response.data
  }

  async generateReport(data: GenerateReportRequest): Promise<TestReport> {
    const response = await apiClient.post(`${this.baseUrl}/generate`, data)
    return response.data
  }

  async downloadReport(id: number): Promise<Blob> {
    const response = await apiClient.get(`${this.baseUrl}/${id}/download`, {
      responseType: 'blob'
    })
    return response.data
  }

  async deleteReport(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async getReportTemplates(): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/templates`)
    return response.data
  }

  async previewReport(data: GenerateReportRequest): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/preview`, data)
    return response.data
  }

  async shareReport(id: number, emails: string[]): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${id}/share`, { emails })
  }

  async getReportStatistics(): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/statistics`)
    return response.data
  }
}

export const reportService = new ReportService()
