// @ts-nocheck
import { apiClient } from '../api/client'
import type {
  TestCase,
  CreateTestCaseRequest,
  UpdateTestCaseRequest,
  TestCaseFilters,
  TestCaseGenerationConfig,
  AutomationConfig,
  AutomationScript,
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
    if (Array.isArray(value)) {
      value.forEach(v => params.append(key === 'size' ? 'page_size' : key, String(v)))
    } else {
      params.append(key === 'size' ? 'page_size' : key, String(value))
    }
  })
  return params
}

export class TestCaseService {
  private baseUrl = '/api/v1/test-cases/'
  private path = (suffix = '') => `${this.baseUrl}${suffix}`

  async getTestCases(filters?: TestCaseFilters): Promise<PaginatedResponse<TestCase>> {
    const params = normalizeParams(filters)

    const response = await apiClient.get(`${this.path()}?${params.toString()}`)
    return response.data
  }

  async getTestCase(id: number): Promise<TestCase> {
    const response = await apiClient.get(this.path(String(id)))
    return unwrapData<TestCase>(response.data)
  }

  async createTestCase(data: CreateTestCaseRequest): Promise<TestCase> {
    const response = await apiClient.post(this.baseUrl, data)
    return unwrapData<TestCase>(response.data)
  }

  async updateTestCase(id: number, data: UpdateTestCaseRequest): Promise<TestCase> {
    const response = await apiClient.put(this.path(String(id)), data)
    return unwrapData<TestCase>(response.data)
  }

  async deleteTestCase(id: number): Promise<void> {
    await apiClient.delete(this.path(String(id)))
  }

  async duplicateTestCase(id: number, newTitle: string): Promise<TestCase> {
    const response = await apiClient.post(this.path('copy'), { source_case_id: id, case_title: newTitle })
    return unwrapData<TestCase>(response.data)
  }

  async generateTestCases(config: TestCaseGenerationConfig): Promise<TestCase[]> {
    const response = await apiClient.post(this.path('generate'), config, { timeout: 240000 })
    return unwrapData<TestCase[]>(response.data)
  }

  async generateAutomationScript(testCaseId: number, config: AutomationConfig): Promise<AutomationScript> {
    const response = await apiClient.post(this.path('generate-script'), {
      test_case_id: testCaseId,
      framework: config.framework,
      language: config.language || 'python',
      browser: config.browser || 'chrome',
      automation_config: config,
    })
    return unwrapData<AutomationScript>(response.data)
  }

  async batchUpdateTestCases(ids: number[], data: Partial<UpdateTestCaseRequest>): Promise<void> {
    await apiClient.post(this.path('batch-update'), { case_ids: ids, update_data: data })
  }

  async batchDeleteTestCases(ids: number[]): Promise<void> {
    await apiClient.delete(this.path('batch'), { data: { ids } })
  }

  async exportTestCases(filters?: TestCaseFilters, format: string = 'excel'): Promise<Blob> {
    const params = normalizeParams(filters)
    params.append('format', format)

    const response = await apiClient.get(`${this.path('export')}?${params.toString()}`, {
      responseType: 'blob'
    })
    return response.data
  }

  async importTestCases(file: File, testPlanId?: number): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    if (testPlanId) {
      formData.append('test_plan_id', String(testPlanId))
    }

    const response = await apiClient.post(this.path('import'), formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}

export const testCaseService = new TestCaseService()
