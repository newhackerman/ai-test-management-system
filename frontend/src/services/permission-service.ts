/**
 * 权限管理服务
 * 提供权限CRUD操作、权限检查、权限分配等功能
 */

import { apiClient } from '@/lib/api-client'
import { createApiError } from '@/lib/api-error-handler'
import type { Permission, PermissionTree, UserPermissions, PermissionAssignment, PermissionCheck } from '@/types'

export interface CreatePermissionData {
  code: string
  name: string
  description?: string
  module: string
  action: string
  resource?: string
  permission_type?: 'menu' | 'button' | 'api' | 'data' | 'field'
  parent_id?: number
  level?: number
  sort_order?: number
  effect?: 'allow' | 'deny'
  conditions?: any
  is_system_permission?: boolean
}

export interface UpdatePermissionData {
  name?: string
  description?: string
  module?: string
  action?: string
  resource?: string
  permission_type?: 'menu' | 'button' | 'api' | 'data' | 'field'
  sort_order?: number
  effect?: 'allow' | 'deny'
  conditions?: any
  is_active?: boolean
}

export interface PermissionListParams {
  page?: number
  size?: number
  module?: string
  permission_type?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PermissionListResponse {
  permissions: Permission[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PermissionStatistics {
  total_permissions: number
  module_statistics: Record<string, number>
  type_statistics: Record<string, number>
}

/**
 * 权限管理服务类
 */
export class PermissionService {
  /**
   * 获取权限列表
   */
  async getPermissions(params: PermissionListParams = {}): Promise<PermissionListResponse> {
    try {
      const queryParams = new URLSearchParams()
      
      if (params.page) queryParams.append('skip', String((params.page - 1) * (params.size || 10)))
      if (params.size) queryParams.append('limit', String(params.size))
      if (params.module) queryParams.append('module', params.module)
      if (params.permission_type) queryParams.append('permission_type', params.permission_type)

      const response = await apiClient.get<PermissionListResponse>(`/api/v1/permissions?${queryParams.toString()}`)
      return response
    } catch (error) {
      throw createApiError(
        '获取权限列表失败',
        'GET_PERMISSIONS_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 获取权限树结构
   */
  async getPermissionTree(): Promise<PermissionTree[]> {
    try {
      const response = await apiClient.get<{
        permission_tree: PermissionTree[]
      }>('/api/v1/permissions/tree')
      
      return response.permission_tree
    } catch (error) {
      throw createApiError(
        '获取权限树失败',
        'GET_PERMISSION_TREE_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 获取权限统计信息
   */
  async getPermissionStatistics(): Promise<PermissionStatistics> {
    try {
      const response = await apiClient.get<PermissionStatistics>('/api/v1/permissions/statistics')
      return response
    } catch (error) {
      throw createApiError(
        '获取权限统计失败',
        'GET_PERMISSION_STATISTICS_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 创建权限
   */
  async createPermission(permissionData: CreatePermissionData): Promise<Permission> {
    try {
      const response = await apiClient.post<Permission>('/api/v1/permissions', permissionData)
      return response
    } catch (error) {
      throw createApiError(
        '创建权限失败',
        'CREATE_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 获取权限详情
   */
  async getPermissionById(permissionId: string): Promise<Permission> {
    try {
      const response = await apiClient.get<Permission>(`/api/v1/permissions/${permissionId}`)
      return response
    } catch (error) {
      throw createApiError(
        '获取权限详情失败',
        'GET_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 更新权限
   */
  async updatePermission(permissionId: string, permissionData: UpdatePermissionData): Promise<Permission> {
    try {
      const response = await apiClient.put<Permission>(`/api/v1/permissions/${permissionId}`, permissionData)
      return response
    } catch (error) {
      throw createApiError(
        '更新权限失败',
        'UPDATE_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 删除权限
   */
  async deletePermission(permissionId: string): Promise<void> {
    try {
      await apiClient.delete(`/api/v1/permissions/${permissionId}`)
    } catch (error) {
      throw createApiError(
        '删除权限失败',
        'DELETE_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 获取用户权限
   */
  async getUserPermissions(userId: string): Promise<UserPermissions> {
    try {
      const response = await apiClient.get<UserPermissions>(`/api/v1/permissions/users/${userId}`)
      return response
    } catch (error) {
      throw createApiError(
        '获取用户权限失败',
        'GET_USER_PERMISSIONS_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 授予用户权限
   */
  async grantPermissionToUser(userId: string, assignment: PermissionAssignment): Promise<void> {
    try {
      await apiClient.post(`/api/v1/permissions/users/${userId}/grant`, assignment)
    } catch (error) {
      throw createApiError(
        '授予用户权限失败',
        'GRANT_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 撤销用户权限
   */
  async revokePermissionFromUser(userId: string, permissionId: string): Promise<void> {
    try {
      await apiClient.delete(`/api/v1/permissions/users/${userId}/permissions/${permissionId}`)
    } catch (error) {
      throw createApiError(
        '撤销用户权限失败',
        'REVOKE_PERMISSION_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 批量检查权限
   */
  async checkPermissions(permissionCodes: string[], userId?: string): Promise<PermissionCheck> {
    try {
      const requestData: any = { permission_codes: permissionCodes }
      if (userId) {
        requestData.user_id = parseInt(userId)
      }

      const response = await apiClient.post<PermissionCheck>('/api/v1/permissions/check', requestData)
      return response
    } catch (error) {
      throw createApiError(
        '检查权限失败',
        'CHECK_PERMISSIONS_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 获取角色权限
   */
  async getRolePermissions(roleId: string): Promise<Permission[]> {
    try {
      const response = await apiClient.get<{
        permissions: Permission[]
      }>(`/api/v1/permissions/roles/${roleId}`)
      
      return response.permissions
    } catch (error) {
      throw createApiError(
        '获取角色权限失败',
        'GET_ROLE_PERMISSIONS_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 为角色分配权限
   */
  async assignPermissionsToRole(roleId: string, permissionIds: number[]): Promise<{
    message: string
    success_count: number
    failed_count: number
    failed_permissions: any[]
  }> {
    try {
      const response = await apiClient.post<{
        message: string
        success_count: number
        failed_count: number
        failed_permissions: any[]
      }>(`/api/v1/permissions/roles/${roleId}/assign`, permissionIds)
      
      return response
    } catch (error) {
      throw createApiError(
        '为角色分配权限失败',
        'ASSIGN_PERMISSIONS_TO_ROLE_FAILED',
        undefined,
        error
      )
    }
  }

  /**
   * 检查单个权限
   */
  async hasPermission(permissionCode: string, userId?: string): Promise<boolean> {
    try {
      const result = await this.checkPermissions([permissionCode], userId)
      return result.permissions[permissionCode] || false
    } catch (error) {
      // 权限检查失败时默认返回false
      return false
    }
  }

  /**
   * 获取模块权限列表
   */
  async getPermissionsByModule(module: string): Promise<Permission[]> {
    try {
      const response = await this.getPermissions({ module })
      return response.permissions
    } catch (error) {
      throw createApiError(
        '获取模块权限失败',
        'GET_MODULE_PERMISSIONS_FAILED',
        undefined,
        error
      )
    }
  }
}

// 创建权限服务实例
export const permissionService = new PermissionService()

export default permissionService