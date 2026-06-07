import { 
  Requirement, 
  RequirementFilters, 
  CreateRequirementRequest, 
  UpdateRequirementRequest,
  RequirementStatusUpdate,
  RequirementListResponse,
  RequirementResponse,
  RequirementStatistics,
  RequirementStatisticsResponse
} from '@/types/requirement'
import { ApiResponse } from '@/types'
import api from './api'

const unwrap = <T>(response: unknown): T => {
  const payload = response as T | { data?: T }
  if (payload && typeof payload === 'object' && 'data' in payload && !('success' in payload)) {
    return (payload as { data?: T }).data as T
  }
  return payload as T
}

class RequirementService {
  private baseUrl = '/requirements'

  private buildListParams(filters?: RequirementFilters) {
    const params = new URLSearchParams()
    if (!filters) return params

    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return

      if (key === 'search') {
        params.append('keyword', String(value))
        return
      }

      if (key === 'page' || key === 'size') return

      if (key === 'requirement_type' && Array.isArray(value)) {
        if (value[0]) params.append('requirement_type', value[0].toString())
        return
      }

      if (key === 'category' && Array.isArray(value)) {
        if (value[0]) params.append('category', value[0].toString())
        return
      }

      if (key === 'created_after') {
        params.append('created_from', String(value))
        return
      }

      if (key === 'created_before') {
        params.append('created_to', String(value))
        return
      }

      if (Array.isArray(value)) {
        value.forEach((item) => params.append(key, item.toString()))
      } else {
        params.append(key, value.toString())
      }
    })

    const page = filters.page || 1
    const size = filters.size || 20
    params.append('skip', String((page - 1) * size))
    params.append('limit', String(size))

    return params
  }

  /**
   * 获取需求列表
   */
  async getRequirements(filters?: RequirementFilters): Promise<RequirementListResponse> {
    const params = this.buildListParams(filters)

    const queryString = params.toString()
    const response = await api.get<RequirementListResponse>(
      queryString ? `${this.baseUrl}/?${queryString}` : `${this.baseUrl}/`
    )
    const payload = unwrap<any>(response)
    const list = payload?.data || payload?.items || []
    return {
      ...payload,
      data: list,
      total: payload?.total || list.length,
      page: payload?.page || filters?.page || 1,
      size: payload?.page_size || payload?.size || filters?.size || 20,
      totalPages: Math.ceil((payload?.total || list.length) / (payload?.page_size || payload?.size || filters?.size || 20))
    }
  }

  /**
   * 根据ID获取需求详情
   */
  async getRequirement(id: number): Promise<Requirement> {
    const response = await api.get<RequirementResponse>(`${this.baseUrl}/${id}`)
    return unwrap<any>(response).data || unwrap<Requirement>(response)
  }

  /**
   * 创建需求
   */
  async createRequirement(data: CreateRequirementRequest): Promise<Requirement> {
    const response = await api.post<RequirementResponse>(`${this.baseUrl}/`, data)
    return unwrap<any>(response).data || unwrap<Requirement>(response)
  }

  /**
   * 更新需求
   */
  async updateRequirement(id: number, data: UpdateRequirementRequest): Promise<Requirement> {
    const response = await api.put<RequirementResponse>(`${this.baseUrl}/${id}`, data)
    return unwrap<any>(response).data || unwrap<Requirement>(response)
  }

  /**
   * 更新需求状态
   */
  async updateRequirementStatus(id: number, statusUpdate: RequirementStatusUpdate): Promise<Requirement> {
    const response = await api.put<RequirementResponse>(`${this.baseUrl}/${id}/status`, statusUpdate)
    return unwrap<any>(response).data || unwrap<Requirement>(response)
  }

  /**
   * 删除需求
   */
  async deleteRequirement(id: number): Promise<void> {
    await api.delete(`${this.baseUrl}/${id}`)
  }

  /**
   * 批量删除需求
   */
  async batchDeleteRequirements(ids: number[]): Promise<void> {
    await api.delete(`${this.baseUrl}/batch`, { data: { requirement_ids: ids } })
  }

  /**
   * 批量更新需求状态
   */
  async batchUpdateStatus(ids: number[], statusUpdate: RequirementStatusUpdate): Promise<void> {
    await api.put(`${this.baseUrl}/batch/status`, { requirement_ids: ids, ...statusUpdate })
  }

  /**
   * 复制需求
   */
  async duplicateRequirement(id: number, data?: Partial<CreateRequirementRequest>): Promise<Requirement> {
    const response = await api.post<RequirementResponse>(`${this.baseUrl}/${id}/duplicate`, data)
    return unwrap<any>(response).data || unwrap<Requirement>(response)
  }

  /**
   * 获取需求统计信息
   */
  async getRequirementStatistics(projectId?: number): Promise<RequirementStatistics> {
    const params = projectId ? `?project_id=${projectId}` : ''
    const response = await api.get<RequirementStatisticsResponse>(`${this.baseUrl}/statistics${params}`)
    return unwrap<any>(response).data || unwrap<RequirementStatistics>(response)
  }

  /**
   * 搜索需求
   */
  async searchRequirements(query: string, filters?: Partial<RequirementFilters>): Promise<RequirementListResponse> {
    const searchFilters: RequirementFilters = {
      search: query,
      ...filters
    }
    return this.getRequirements(searchFilters)
  }

  /**
   * 获取需求历史版本
   */
  async getRequirementHistory(id: number): Promise<Requirement[]> {
    const response = await api.get<{ data: Requirement[] }>(`${this.baseUrl}/${id}/history`)
    const payload = unwrap<any>(response)
    return payload?.status_history || payload?.data || []
  }

  /**
   * 导出需求
   */
  async exportRequirements(filters?: RequirementFilters, format: 'excel' | 'pdf' | 'csv' = 'excel'): Promise<Blob> {
    const params = new URLSearchParams()
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v.toString()))
          } else {
            params.append(key, value.toString())
          }
        }
      })
    }
    
    params.append('format', format)

    const response = await api.get(`${this.baseUrl}/export?${params}`, {
      responseType: 'blob'
    })
    return unwrap<Blob>(response)
  }

  /**
   * 导入需求
   */
  async importRequirements(file: File, projectId: number): Promise<{ success_count: number; failed_count: number; errors: string[] }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', projectId.toString())

    const response = await api.post<{ data: { success_count: number; failed_count: number; errors: string[] } }>(
      `${this.baseUrl}/import`, 
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return unwrap<any>(response).data
  }

  /**
   * 获取需求模板
   */
  async getRequirementTemplates(): Promise<Array<{ id: string; name: string; template: Partial<CreateRequirementRequest> }>> {
    const response = await api.get<{ data: Array<{ id: string; name: string; template: Partial<CreateRequirementRequest> }> }>(`${this.baseUrl}/templates`)
    return unwrap<any>(response).data || []
  }

  /**
   * 获取需求分类列表
   */
  async getRequirementCategories(projectId?: number): Promise<string[]> {
    const params = projectId ? `?project_id=${projectId}` : ''
    const response = await api.get<{ data: string[] }>(`${this.baseUrl}/categories${params}`)
    return unwrap<any>(response).data || []
  }

  /**
   * 获取需求标签列表
   */
  async getRequirementTags(projectId?: number): Promise<string[]> {
    const params = projectId ? `?project_id=${projectId}` : ''
    const response = await api.get<{ data: string[] }>(`${this.baseUrl}/tags${params}`)
    return unwrap<any>(response).data || []
  }
}

export const requirementService = new RequirementService()
export default requirementService
