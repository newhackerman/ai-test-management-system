import { api } from './api'

// 配置类型定义
export interface ConfigItem {
  id: number
  config_key: string
  config_value: string
  config_type: 'STRING' | 'TEXT' | 'INTEGER' | 'FLOAT' | 'BOOLEAN' | 'JSON' | 'ARRAY' | 'EMAIL' | 'URL' | 'ENUM' | 'PASSWORD' | 'FILE' | 'COLOR' | 'DATE' | 'TIME'
  group_id?: number
  environment: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'
  description?: string
  default_value?: string
  example_value?: string
  validation_rule?: any
  is_core: boolean
  is_enabled: boolean
  is_encrypted: boolean
  is_required: boolean
  tags?: string[]
  sort_order: number
  created_at: string
  updated_at: string
  created_by?: number
  updated_by?: number
}

export interface ConfigGroup {
  id: number
  group_name: string
  group_code: string
  parent_id: number
  level: number
  path?: string
  sort_order: number
  description?: string
  icon?: string
  color?: string
  is_system: boolean
  is_enabled: boolean
  created_at: string
  updated_at: string
  created_by?: number
  updated_by?: number
}

export interface Environment {
  id: number
  env_name: string
  env_code: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'
  description?: string
  base_url?: string
  config_data?: any
  is_active: boolean
  is_default: boolean
  sort_order: number
  created_at: string
  updated_at: string
  created_by?: number
  updated_by?: number
}

export interface ConfigListResponse {
  items: ConfigItem[]
  total: number
  page: number
  size: number
  pages: number
}

export interface ConfigCreateRequest {
  config_key: string
  config_value: string
  config_type: 'STRING' | 'TEXT' | 'INTEGER' | 'FLOAT' | 'BOOLEAN' | 'JSON' | 'ARRAY' | 'EMAIL' | 'URL' | 'ENUM' | 'PASSWORD' | 'FILE' | 'COLOR' | 'DATE' | 'TIME'
  group_id?: number
  environment: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'
  description?: string
  default_value?: string
  example_value?: string
  validation_rule?: any
  is_core?: boolean
  is_enabled?: boolean
  is_encrypted?: boolean
  is_required?: boolean
  tags?: string[]
  sort_order?: number
}

export interface ConfigUpdateRequest {
  config_value?: string
  config_type?: 'STRING' | 'TEXT' | 'INTEGER' | 'FLOAT' | 'BOOLEAN' | 'JSON' | 'ARRAY' | 'EMAIL' | 'URL' | 'ENUM' | 'PASSWORD' | 'FILE' | 'COLOR' | 'DATE' | 'TIME'
  description?: string
  default_value?: string
  example_value?: string
  validation_rule?: any
  is_core?: boolean
  is_enabled?: boolean
  is_encrypted?: boolean
  is_required?: boolean
  tags?: string[]
  sort_order?: number
  change_reason?: string
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
}

const unwrapApiResponse = <T>(response: unknown): T => {
  const payload = response as ApiResponse<T> | { data?: ApiResponse<T> | T }

  if (payload && typeof payload === 'object' && 'success' in payload && 'data' in payload) {
    return (payload as ApiResponse<T>).data
  }

  const nested = (payload as { data?: ApiResponse<T> | T })?.data
  if (nested && typeof nested === 'object' && 'success' in nested && 'data' in nested) {
    return (nested as ApiResponse<T>).data
  }

  return nested as T
}

// 配置管理API服务
export class ConfigService {
  
  // === 配置管理 ===
  
  /**
   * 获取配置列表
   */
  static async getConfigs(params: {
    environment?: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'
    group_id?: number
    page?: number
    size?: number
    search?: string
    config_type?: string
    is_core?: boolean
  } = {}): Promise<ConfigListResponse> {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    
    const response = await api.get<ApiResponse<ConfigListResponse>>(`/configs/configs?${searchParams}`)
    return unwrapApiResponse<ConfigListResponse>(response)
  }

  /**
   * 获取单个配置
   */
  static async getConfig(configKey: string, environment: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf' = 'prod', decrypt: boolean = true): Promise<ConfigItem> {
    const response = await api.get<ApiResponse<ConfigItem>>(`/configs/configs/${configKey}?environment=${environment}&decrypt=${decrypt}`)
    return unwrapApiResponse<ConfigItem>(response)
  }

  /**
   * 创建配置
   */
  static async createConfig(data: ConfigCreateRequest): Promise<ConfigItem> {
    const response = await api.post<ApiResponse<ConfigItem>>('/configs/configs', data)
    return unwrapApiResponse<ConfigItem>(response)
  }

  /**
   * 更新配置
   */
  static async updateConfig(configKey: string, data: ConfigUpdateRequest, environment: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf' = 'prod'): Promise<ConfigItem> {
    const response = await api.put<ApiResponse<ConfigItem>>(`/configs/configs/${configKey}?environment=${environment}`, data)
    return unwrapApiResponse<ConfigItem>(response)
  }

  /**
   * 删除配置
   */
  static async deleteConfig(configKey: string, environment: 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf' = 'prod', hardDelete: boolean = false): Promise<void> {
    await api.delete(`/configs/configs/${configKey}?environment=${environment}&hard_delete=${hardDelete}`)
  }

  /**
   * 批量更新配置
   */
  static async batchUpdateConfigs(updates: any[]): Promise<any> {
    const response = await api.post<ApiResponse<any>>('/configs/configs/batch-update', updates)
    return unwrapApiResponse<any>(response)
  }

  // === 环境管理 ===

  /**
   * 获取环境列表
   */
  static async getEnvironments(): Promise<Environment[]> {
    const response = await api.get<ApiResponse<Environment[]>>('/configs/environments')
    return unwrapApiResponse<Environment[]>(response)
  }

  /**
   * 获取环境信息
   */
  static async getEnvironment(envCode: string): Promise<Environment> {
    const response = await api.get<ApiResponse<Environment>>(`/configs/environments/${envCode}`)
    return unwrapApiResponse<Environment>(response)
  }

  /**
   * 环境间配置同步
   */
  static async syncEnvironments(sourceEnv: string, targetEnv: string, configKeys?: string[]): Promise<any> {
    const params = new URLSearchParams()
    params.append('source_env', sourceEnv)
    params.append('target_env', targetEnv)
    if (configKeys) {
      configKeys.forEach(key => params.append('config_keys', key))
    }
    
    const response = await api.post<ApiResponse<any>>(`/configs/environments/sync?${params}`)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 比较环境配置差异
   */
  static async compareEnvironments(env1: string, env2: string): Promise<any> {
    const response = await api.get<ApiResponse<any>>(`/configs/environments/compare?env1=${env1}&env2=${env2}`)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 获取环境配置统计
   */
  static async getEnvironmentStatistics(environment: string): Promise<any> {
    const response = await api.get<ApiResponse<any>>(`/configs/environments/${environment}/statistics`)
    return unwrapApiResponse<any>(response)
  }

  // === 配置分组管理 ===

  /**
   * 获取配置分组列表
   */
  static async getConfigGroups(): Promise<ConfigGroup[]> {
    const response = await api.get<ApiResponse<ConfigGroup[]>>('/configs/groups')
    return unwrapApiResponse<ConfigGroup[]>(response) || []
  }

  /**
   * 创建配置分组
   */
  static async createConfigGroup(data: Partial<ConfigGroup>): Promise<ConfigGroup> {
    const response = await api.post<ApiResponse<ConfigGroup>>('/configs/groups', data)
    return unwrapApiResponse<ConfigGroup>(response)
  }

  /**
   * 更新配置分组
   */
  static async updateConfigGroup(id: number, data: Partial<ConfigGroup>): Promise<ConfigGroup> {
    const response = await api.put<ApiResponse<ConfigGroup>>(`/configs/groups/${id}`, data)
    return unwrapApiResponse<ConfigGroup>(response)
  }

  /**
   * 删除配置分组
   */
  static async deleteConfigGroup(id: number): Promise<void> {
    await api.delete(`/configs/groups/${id}`)
  }

  // === 权限管理 ===

  /**
   * 检查配置权限
   */
  static async checkConfigPermission(configKey: string, environment: string, action: string): Promise<boolean> {
    const response = await api.get<ApiResponse<{has_permission: boolean}>>(`/configs/permissions/check?config_key=${configKey}&environment=${environment}&action=${action}`)
    return unwrapApiResponse<{has_permission: boolean}>(response).has_permission
  }

  /**
   * 批量检查配置权限
   */
  static async batchCheckConfigPermission(configKeys: string[], environment: string, action: string): Promise<Record<string, boolean>> {
    const params = new URLSearchParams()
    configKeys.forEach(key => params.append('config_keys', key))
    params.append('environment', environment)
    params.append('action', action)
    
    const response = await api.post<ApiResponse<Record<string, boolean>>>(`/configs/permissions/batch-check?${params}`)
    return unwrapApiResponse<Record<string, boolean>>(response)
  }

  /**
   * 获取我的配置权限
   */
  static async getMyConfigPermissions(): Promise<any[]> {
    const response = await api.get<ApiResponse<any[]>>('/configs/permissions/my')
    return unwrapApiResponse<any[]>(response)
  }

  /**
   * 授予配置权限
   */
  static async grantConfigPermission(targetUserId: number, permissionData: any): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/configs/permissions/grant?target_user_id=${targetUserId}`, permissionData)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 撤销配置权限
   */
  static async revokeConfigPermission(permissionId: number): Promise<void> {
    await api.delete(`/configs/permissions/${permissionId}`)
  }

  /**
   * 获取权限统计
   */
  static async getPermissionStatistics(environment?: string): Promise<any> {
    const params = environment ? `?environment=${environment}` : ''
    const response = await api.get<ApiResponse<any>>(`/configs/permissions/statistics${params}`)
    return unwrapApiResponse<any>(response)
  }

  // === 审核管理 ===

  /**
   * 创建审核申请
   */
  static async createAuditRequest(requestData: any): Promise<any> {
    const response = await api.post<ApiResponse<any>>('/configs/audits', requestData)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 获取审核列表
   */
  static async getAuditList(params?: any): Promise<any> {
    const response = await api.get<ApiResponse<any>>('/configs/audits', { params })
    return unwrapApiResponse<any>(response)
  }

  /**
   * 获取待审核列表
   */
  static async getPendingAudits(): Promise<any[]> {
    const response = await api.get<ApiResponse<any[]>>('/configs/audits/pending')
    return unwrapApiResponse<any[]>(response)
  }

  /**
   * 获取审核详情
   */
  static async getAuditDetail(auditId: number): Promise<any> {
    const response = await api.get<ApiResponse<any>>(`/configs/audits/${auditId}`)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 审核通过
   */
  static async approveAudit(auditId: number, auditReason?: string): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/configs/audits/${auditId}/approve`, null, {
      params: auditReason ? { audit_reason: auditReason } : undefined
    })
    return unwrapApiResponse<any>(response)
  }

  /**
   * 审核驳回
   */
  static async rejectAudit(auditId: number, auditReason: string): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/configs/audits/${auditId}/reject`, null, {
      params: { audit_reason: auditReason }
    })
    return unwrapApiResponse<any>(response)
  }

  /**
   * 获取审核统计
   */
  static async getAuditStatistics(timeRange?: string): Promise<any> {
    const params = timeRange ? `?time_range=${timeRange}` : ''
    const response = await api.get<ApiResponse<any>>(`/configs/audits/statistics${params}`)
    return unwrapApiResponse<any>(response)
  }

  /**
   * 添加审核意见
   */
  static async addAuditComment(auditId: number, comment: string): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/configs/audits/${auditId}/comment`, null, {
      params: { comment }
    })
    return unwrapApiResponse<any>(response)
  }

  /**
   * 取消审核申请
   */
  static async cancelAudit(auditId: number, cancelReason: string): Promise<any> {
    const response = await api.post<ApiResponse<any>>(`/configs/audits/${auditId}/cancel`, null, {
      params: { cancel_reason: cancelReason }
    })
    return unwrapApiResponse<any>(response)
  }

  /**
   * 获取审核历史
   */
  static async getAuditHistory(auditId: number): Promise<any[]> {
    const response = await api.get<ApiResponse<any[]>>(`/configs/audits/${auditId}/history`)
    return unwrapApiResponse<any[]>(response)
  }
}
