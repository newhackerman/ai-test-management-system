// @ts-nocheck
import { apiClient } from '../api/client'
import type {
  TestExecution,
  ExecutionStatus,
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
    const paramKey = key === 'size'
      ? 'page_size'
      : key === 'started_after'
        ? 'start_date'
        : key === 'started_before'
          ? 'end_date'
          : key
    params.append(paramKey, String(value))
  })
  return params
}

export interface ExecutionFilters {
  search?: string
  test_plan_id?: number
  test_case_id?: number
  execution_type?: string
  execution_status?: ExecutionStatus
  executor_id?: number
  started_after?: string
  started_before?: string
  page?: number
  size?: number
}

export interface StartExecutionRequest {
  test_case_id: number
  test_environment?: string
  browser_info?: string
  os_info?: string
}

export interface CompleteExecutionRequest {
  execution_status: ExecutionStatus
  actual_result?: string
  failure_reason?: string
  execution_notes?: string
  screenshots?: any[]
  logs?: any[]
  videos?: any[]
}

export interface AutomationExecutionRequest {
  test_case_ids: number[]
  framework: string
  test_environment: string
  browser?: string
  parallel_count?: number
  retry_count?: number
  timeout?: number
  execution_config?: Record<string, any>
}

export interface AutomationExecutionResponse {
  execution_id: string
  framework: string
  test_environment: string
  status: string
  total_cases: number
  completed_cases: number
  passed_cases: number
  failed_cases: number
  progress_percentage: number
  started_at: string
  estimated_completion?: string
  execution_logs?: Array<Record<string, any>>
  test_results?: Array<Record<string, any>>
}

export class ExecutionService {
  private baseUrl = '/api/v1/test-executions'

  async getExecutions(filters?: ExecutionFilters): Promise<PaginatedResponse<TestExecution>> {
    const params = normalizeParams(filters)

    const response = await apiClient.get(`${this.baseUrl}?${params.toString()}`)
    return response.data
  }

  async getExecution(id: number): Promise<TestExecution> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)
    return unwrapData<TestExecution>(response.data)
  }

  async startManualExecution(data: StartExecutionRequest): Promise<TestExecution> {
    const response = await apiClient.post(`${this.baseUrl}/manual/start`, data)
    return unwrapData<TestExecution>(response.data)
  }

  async completeExecution(id: number, data: CompleteExecutionRequest): Promise<TestExecution> {
    const response = await apiClient.post(`${this.baseUrl}/manual/complete`, {
      execution_id: id,
      ...data,
    })
    return unwrapData<TestExecution>(response.data)
  }

  async pauseExecution(id: number): Promise<TestExecution> {
    const response = await apiClient.post(`${this.baseUrl}/manual/pause`, { execution_id: id })
    return unwrapData<TestExecution>(response.data)
  }

  async resumeExecution(id: number): Promise<TestExecution> {
    const response = await apiClient.post(`${this.baseUrl}/manual/resume`, { execution_id: id })
    return unwrapData<TestExecution>(response.data)
  }

  async startAutomationExecution(data: AutomationExecutionRequest): Promise<AutomationExecutionResponse> {
    const response = await apiClient.post(`${this.baseUrl}/automation/start`, data)
    return unwrapData<AutomationExecutionResponse>(response.data)
  }

  async getAutomationExecutionStatus(executionId: string): Promise<AutomationExecutionResponse> {
    const response = await apiClient.get(`${this.baseUrl}/automation/${executionId}/status`)
    return unwrapData<AutomationExecutionResponse>(response.data)
  }

  async cancelAutomationExecution(executionId: string): Promise<AutomationExecutionResponse> {
    const response = await apiClient.post(`${this.baseUrl}/automation/${executionId}/cancel`)
    return unwrapData<AutomationExecutionResponse>(response.data)
  }

  async cancelExecution(id: number): Promise<TestExecution> {
    const response = await apiClient.post(`${this.baseUrl}/manual/complete`, {
      execution_id: id,
      execution_status: 'SKIPPED',
      execution_notes: '用户取消执行',
    })
    return unwrapData<TestExecution>(response.data)
  }

  async getExecutionLogs(id: number): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/${id}/logs`)
    return unwrapData<any[]>(response.data)
  }

  async uploadScreenshot(id: number, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('screenshot', file)

    const response = await apiClient.post(`${this.baseUrl}/${id}/screenshots`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return unwrapData<any>(response.data)
  }

  async uploadVideo(id: number, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('video', file)

    const response = await apiClient.post(`${this.baseUrl}/${id}/videos`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return unwrapData<any>(response.data)
  }

  async getExecutionStatistics(filters?: ExecutionFilters): Promise<any> {
    const params = normalizeParams(filters)

    const response = await apiClient.get(`${this.baseUrl}/statistics?${params.toString()}`)
    return unwrapData<any>(response.data)
  }
}

export const executionService = new ExecutionService()
