import { apiClient } from '@/lib/api-client'
import { createApiError } from '@/lib/api-error-handler'
import type { Role } from '@/types'

export interface CreateRoleData {
  name: string
  code: string
  description?: string
  is_active?: boolean
  priority?: number
  sort_order?: number
  permission_ids?: number[]
}

export interface UpdateRoleData {
  name?: string
  description?: string
  is_active?: boolean
  priority?: number
  sort_order?: number
  permission_ids?: number[]
}

export interface RoleListParams {
  page?: number
  size?: number
  search?: string
  type?: string
  status?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface RoleListResponse {
  roles: Role[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

function normalizeRole(role: any): Role {
  return {
    id: role.id,
    name: role.name,
    code: role.code,
    description: role.description,
    is_system_role: Boolean(role.is_system_role),
    is_active: role.is_active !== false,
    priority: role.priority || 0,
    sort_order: role.sort_order ?? role.sort ?? 0,
    created_at: role.created_at,
    updated_at: role.updated_at,
    permissions: role.permissions || [],
  } as Role
}

export class RoleService {
  async getAllRoles(): Promise<Role[]> {
    try {
      const response = (await apiClient.get<any>('/roles/all')) as any
      const roles = Array.isArray(response) ? response : response.data || response.roles || []
      return roles.map(normalizeRole)
    } catch (error) {
      throw createApiError('获取角色列表失败', 'GET_ALL_ROLES_FAILED', undefined, error)
    }
  }

  async getRoles(params: RoleListParams = {}): Promise<RoleListResponse> {
    try {
      const queryParams = new URLSearchParams()
      if (params.page) queryParams.append('page', String(params.page))
      if (params.size) queryParams.append('size', String(params.size))
      if (params.search) queryParams.append('search', params.search)
      if (params.type) queryParams.append('type', params.type)
      if (params.status) queryParams.append('status', params.status)
      if (params.sort_by) queryParams.append('sort_by', params.sort_by)
      if (params.sort_order) queryParams.append('sort_order', params.sort_order)

      const response = (await apiClient.get<any>(`/roles?${queryParams.toString()}`)) as any
      const roles = (response.data || response.roles || []).map(normalizeRole)

      return {
        roles,
        total: response.total || roles.length,
        page: response.page || params.page || 1,
        page_size: response.page_size || response.size || params.size || 10,
        total_pages: response.total_pages || 1,
      }
    } catch (error) {
      throw createApiError('获取角色列表失败', 'GET_ROLES_FAILED', undefined, error)
    }
  }

  async getRoleById(roleId: string): Promise<Role> {
    try {
      const response = (await apiClient.get<any>(`/roles/${roleId}`)) as any
      return normalizeRole(response.data || response)
    } catch (error) {
      throw createApiError('获取角色详情失败', 'GET_ROLE_FAILED', undefined, error)
    }
  }

  async createRole(roleData: CreateRoleData): Promise<Role> {
    try {
      const response = (await apiClient.post<any>('/roles', roleData)) as any
      return normalizeRole(response.data || response)
    } catch (error) {
      throw createApiError('创建角色失败', 'CREATE_ROLE_FAILED', undefined, error)
    }
  }

  async updateRole(roleId: string, roleData: UpdateRoleData): Promise<Role> {
    try {
      const response = (await apiClient.put<any>(`/roles/${roleId}`, roleData)) as any
      return normalizeRole(response.data || response)
    } catch (error) {
      throw createApiError('更新角色失败', 'UPDATE_ROLE_FAILED', undefined, error)
    }
  }

  async deleteRole(roleId: string): Promise<void> {
    try {
      await apiClient.delete(`/roles/${roleId}`)
    } catch (error) {
      throw createApiError('删除角色失败', 'DELETE_ROLE_FAILED', undefined, error)
    }
  }
}

export const roleService = new RoleService()

export default roleService
