// @ts-nocheck
import { apiClient } from '../api/client'
import type {
  TestPlan,
  CreateTestPlanRequest,
  UpdateTestPlanRequest,
  TestPlanFilters,
  TestPlanProgress,
  PaginatedResponse
} from '../../types/testmanager'

const unwrapData = <T>(payload: any): T => (
  payload && typeof payload === 'object' && 'success' in payload && 'data' in payload
    ? payload.data
    : payload
)

const normalizeParams = (filters?: Record<string, any>) => {
  const params = new URLSearchParams()
  if (!filters) return params

  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'all') return
    params.append(key === 'size' ? 'page_size' : key, String(value))
  })
  return params
}

const parseDownloadFileName = (contentDisposition?: string) => {
  if (!contentDisposition) return ''

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ''))

  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || ''
}

export class TestPlanService {
  private baseUrl = '/api/v1/test-plans/'

  private path(suffix = '') {
    return suffix ? `${this.baseUrl}${suffix}` : this.baseUrl
  }

  async getTestPlans(filters?: TestPlanFilters): Promise<PaginatedResponse<TestPlan>> {
    const params = normalizeParams(filters)

    const query = params.toString()
    const response = await apiClient.get(query ? `${this.baseUrl}?${query}` : this.baseUrl)
    return response.data
  }

  async getTestPlan(id: number): Promise<TestPlan> {
    const response = await apiClient.get(this.path(String(id)))
    return unwrapData<TestPlan>(response.data)
  }

  async createTestPlan(data: CreateTestPlanRequest): Promise<TestPlan> {
    const response = await apiClient.post(this.baseUrl, data)
    return unwrapData<TestPlan>(response.data)
  }

  async updateTestPlan(id: number, data: UpdateTestPlanRequest): Promise<TestPlan> {
    const response = await apiClient.put(this.path(String(id)), data)
    return unwrapData<TestPlan>(response.data)
  }

  async deleteTestPlan(id: number): Promise<void> {
    await apiClient.delete(this.path(String(id)))
  }

  async getTestPlanProgress(id: number): Promise<TestPlanProgress> {
    const response = await apiClient.get(this.path(`${id}/progress`))
    return unwrapData<TestPlanProgress>(response.data)
  }

  async updateTestPlanStatus(id: number, status: string): Promise<TestPlan> {
    const response = await apiClient.patch(this.path(`${id}/status`), { status })
    return unwrapData<TestPlan>(response.data)
  }

  async duplicateTestPlan(id: number, newName: string): Promise<TestPlan> {
    const response = await apiClient.post(this.path(`${id}/duplicate`), { plan_name: newName })
    return unwrapData<TestPlan>(response.data)
  }

  async getTestPlanTemplates(): Promise<any[]> {
    const response = await apiClient.get(this.path('templates'))
    return unwrapData<any[]>(response.data) || []
  }

  async exportTestPlan(id: number, format: string): Promise<{ blob: Blob; filename: string }> {
    const response = await apiClient.get(this.path(`${id}/export`), {
      params: { format },
      responseType: 'blob'
    })
    return {
      blob: response.data,
      filename: parseDownloadFileName(response.headers?.['content-disposition']) || `test-plan-${id}.${format}`
    }
  }
}

export const testPlanService = new TestPlanService()
