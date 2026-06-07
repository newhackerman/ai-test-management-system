// @ts-nocheck
import { apiClient } from '../api/client'
import type {
  Defect,
  CreateDefectRequest,
  UpdateDefectRequest,
  DefectFilters,
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

export class DefectService {
  private baseUrl = '/api/v1/defects'

  async getDefects(filters?: DefectFilters): Promise<PaginatedResponse<Defect>> {
    const params = normalizeParams(filters)

    const response = await apiClient.get(`${this.baseUrl}/?${params.toString()}`)
    return response.data
  }

  async getDefect(id: number): Promise<Defect> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)
    return unwrapData<Defect>(response.data)
  }

  async createDefect(data: CreateDefectRequest): Promise<Defect> {
    const response = await apiClient.post(`${this.baseUrl}/`, data)
    return unwrapData<Defect>(response.data)
  }

  async updateDefect(id: number, data: UpdateDefectRequest): Promise<Defect> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, data)
    return unwrapData<Defect>(response.data)
  }

  async deleteDefect(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  async updateDefectStatus(id: number, status: string, resolution?: string, notes?: string): Promise<Defect> {
    const response = await apiClient.patch(`${this.baseUrl}/${id}/status`, {
      status, 
      resolution, 
      notes 
    })
    return unwrapData<Defect>(response.data)
  }

  async assignDefect(id: number, assigneeId: number): Promise<Defect> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/assign`, { assignee_id: assigneeId })
    return unwrapData<Defect>(response.data)
  }

  async getDefectStatistics(filters?: DefectFilters): Promise<any> {
    const params = normalizeParams(filters)

    const response = await apiClient.get(`${this.baseUrl}/statistics?${params.toString()}`)
    return unwrapData<any>(response.data)
  }

  async getDefectTrends(timeRange: string = '30d'): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/trends?time_range=${timeRange}`)
    return unwrapData<any[]>(response.data) || []
  }

  async exportDefects(filters?: DefectFilters, format: string = 'excel'): Promise<Blob> {
    const params = normalizeParams(filters)
    params.append('format', format)

    const response = await apiClient.get(`${this.baseUrl}/export?${params.toString()}`, {
      responseType: 'blob'
    })
    return response.data
  }

  async uploadAttachment(id: number, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('attachment', file)

    const response = await apiClient.post(`${this.baseUrl}/${id}/attachments`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}

export const defectService = new DefectService()
