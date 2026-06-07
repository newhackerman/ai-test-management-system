import { apiClient } from '@/lib/api-client'
import type { Role, User } from '@/types'

export interface CreateUserData {
  username: string
  email: string
  password: string
  nickname?: string | null
  phone?: string | null
  is_active?: boolean
  role_ids?: number[]
}

export interface UpdateUserData {
  username?: string
  email?: string
  nickname?: string | null
  phone?: string | null
  is_active?: boolean
  role_ids?: number[]
}

export interface UserListParams {
  page?: number
  size?: number
  pageSize?: number
  search?: string
  status?: string
  role?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface UserListResponse {
  users: User[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface UserPermissionsResponse {
  user_id: string
  username: string
  roles: Role[]
  all_permissions: string[]
}

export interface BatchUserResult {
  success_count: number
  failed_count: number
  total_count: number
  failed_users: Array<{ user_id: string; username?: string; error: string }>
  message: string
}

export interface ImportUserResult {
  success_count: number
  failed_count: number
  total_count: number
  failed_users: Array<{ row: number; username?: string; email?: string; error: string }>
  message: string
}

const statusValues: User['status'][] = ['active', 'disabled', 'locked', 'pending', 'deleted']

export const ROLE_NAME_MAP: Record<string, string> = {
  admin: '系统管理员',
  user: '普通用户',
  SUPER_ADMIN: '超级管理员',
  SYSTEM_ADMIN: '系统管理员',
  CONFIG_ADMIN: '配置管理员',
  PROJECT_MANAGER: '项目管理员',
  DEVELOPER: '开发人员',
  TESTER: '测试人员',
  DEVOPS: '运维人员',
  READONLY_USER: '只读用户',
  ADMIN: '系统管理员',
  USER: '普通用户',
  PROJECT_MANAGER_LEGACY: '项目管理员',
  DESIGNER: '设计人员',
  ARCHITECT: '架构师',
  OPS: '运维人员',
  REQUIREMENT_MANAGER: '需求管理员',
  THIRD_PARTY: '第三方人员',
  GUEST: '访客',
}

const LEGACY_ROLE_CODE_MAP: Record<string, string> = {
  admin: 'ADMIN',
  user: 'USER',
  project_manager: 'PROJECT_MANAGER',
  developer: 'DEVELOPER',
  tester: 'TESTER',
  designer: 'DESIGNER',
  architect: 'ARCHITECT',
  ops: 'OPS',
  requirement_manager: 'REQUIREMENT_MANAGER',
  third_party: 'THIRD_PARTY',
  guest: 'GUEST',
}

function normalizeRoleCode(value: unknown) {
  const code = String(value || '').trim()
  return LEGACY_ROLE_CODE_MAP[code] || code.toUpperCase()
}

export function getRoleDisplayName(role?: Pick<Role, 'code' | 'name'> | string | null) {
  if (!role) return '未分配'
  const rawCode = typeof role === 'string' ? role : role.code
  const rawName = typeof role === 'string' ? '' : role.name
  const normalizedCode = normalizeRoleCode(rawCode || rawName)
  return ROLE_NAME_MAP[rawCode || ''] || ROLE_NAME_MAP[normalizedCode] || rawName || rawCode || '未分配'
}

function normalizeStatus(value: unknown): User['status'] {
  const normalized = String(value || 'active').toLowerCase()
  if (normalized === 'inactive') return 'disabled'
  return statusValues.includes(normalized as User['status']) ? (normalized as User['status']) : 'active'
}

function normalizeRole(rawRole: any): Role {
  const code = String(rawRole.code || rawRole.name || rawRole.id || '')
  return {
    id: Number(rawRole.id),
    code,
    name: getRoleDisplayName({ code, name: String(rawRole.name || rawRole.code || rawRole.id || '') }),
    description: rawRole.description || '',
    is_system_role: Boolean(rawRole.is_system_role || rawRole.is_system),
    is_active: rawRole.is_active !== false,
    priority: Number(rawRole.priority || rawRole.sort || rawRole.sort_order || 0),
    created_at: rawRole.created_at || '',
    updated_at: rawRole.updated_at || '',
    color: rawRole.color,
    icon: rawRole.icon,
    sort_order: rawRole.sort_order ?? rawRole.sort,
  }
}

function normalizeUser(rawUser: any): User {
  const roles = Array.isArray(rawUser.roles) ? rawUser.roles.map(normalizeRole) : []
  const primaryRole = roles[0]?.code || rawUser.role || 'READONLY_USER'

  return {
    id: Number(rawUser.id),
    username: String(rawUser.username || ''),
    email: String(rawUser.email || ''),
    real_name: rawUser.real_name || rawUser.full_name || rawUser.nickname || rawUser.username || '',
    nickname: rawUser.nickname || '',
    phone: rawUser.phone || '',
    avatar: rawUser.avatar || rawUser.avatar_url || '',
    role: primaryRole,
    status: normalizeStatus(rawUser.status),
    is_active: rawUser.is_active !== false,
    is_super_admin: Boolean(rawUser.is_superuser || rawUser.is_super_admin),
    last_login_at: rawUser.last_login_at || undefined,
    created_at: rawUser.created_at || '',
    updated_at: rawUser.updated_at || '',
    roles,
    permissions: rawUser.permissions || [],
    bio: rawUser.bio || '',
    gender: rawUser.gender,
    birthday: rawUser.birthday,
    location: rawUser.location || '',
    website: rawUser.website || '',
    language: rawUser.language || 'zh-CN',
    timezone: rawUser.timezone || 'Asia/Shanghai',
    theme: rawUser.theme || 'light',
    email_notifications: rawUser.email_notifications ?? true,
    sms_notifications: rawUser.sms_notifications ?? false,
    push_notifications: rawUser.push_notifications ?? true,
    is_email_verified: rawUser.is_email_verified ?? false,
    is_phone_verified: rawUser.is_phone_verified ?? false,
    mfa_enabled: rawUser.mfa_enabled ?? false,
    failed_login_attempts: rawUser.failed_login_attempts,
    locked_until: rawUser.locked_until,
  }
}

function appendParam(params: URLSearchParams, key: string, value: unknown) {
  if (value !== undefined && value !== null && value !== '') {
    params.append(key, String(value))
  }
}

export class UserService {
  async getUsers(params: UserListParams = {}): Promise<UserListResponse> {
    const page = params.page || 1
    const size = params.size || params.pageSize || 10
    const queryParams = new URLSearchParams()

    appendParam(queryParams, 'skip', (page - 1) * size)
    appendParam(queryParams, 'limit', size)
    appendParam(queryParams, 'search', params.search)
    appendParam(queryParams, 'status', params.status)
    appendParam(queryParams, 'role', params.role)
    appendParam(queryParams, 'sort_by', params.sort_by || 'created_at')
    appendParam(queryParams, 'sort_order', params.sort_order || 'desc')

    const response = await apiClient.get<any>(`/api/v1/users?${queryParams.toString()}`)

    return {
      users: (response.users || []).map(normalizeUser),
      total: Number(response.total || 0),
      page: Number(response.page || page),
      page_size: Number(response.page_size || size),
      total_pages: Number(response.total_pages || 0),
    }
  }

  async getUserById(userId: string): Promise<User> {
    const response = await apiClient.get<any>(`/api/v1/users/${userId}`)
    return normalizeUser(response)
  }

  async createUser(userData: CreateUserData): Promise<User> {
    const response = await apiClient.post<any>('/api/v1/users', userData)
    return normalizeUser(response)
  }

  async updateUser(userId: string, userData: UpdateUserData): Promise<User> {
    const response = await apiClient.put<any>(`/api/v1/users/${userId}`, userData)
    return normalizeUser(response)
  }

  async deleteUser(userId: string): Promise<void> {
    await apiClient.delete(`/api/v1/users/${userId}`)
  }

  async lockUser(userId: string, reason?: string): Promise<void> {
    await apiClient.post(`/api/v1/users/${userId}/lock`, { reason })
  }

  async unlockUser(userId: string): Promise<void> {
    await apiClient.post(`/api/v1/users/${userId}/unlock`)
  }

  async resetUserPassword(userId: string, newPassword: string, forceChange = true): Promise<void> {
    await apiClient.post(`/api/v1/users/${userId}/reset-password`, {
      new_password: newPassword,
      force_change: forceChange,
    })
  }

  async getUserPermissions(userId: string): Promise<UserPermissionsResponse> {
    const response = await apiClient.get<any>(`/api/v1/users/${userId}/permissions`)
    return {
      user_id: String(response.user_id),
      username: response.username,
      roles: (response.roles || []).map(normalizeRole),
      all_permissions: response.all_permissions || [],
    }
  }

  async getRoles(): Promise<Role[]> {
    const response = await apiClient.get<any>('/api/v1/roles?size=100')
    const roles = response.data || response.roles || []
    return roles.map(normalizeRole)
  }

  async batchUpdateUsers(
    userIds: string[],
    action: 'activate' | 'deactivate' | 'delete' | 'assign_role' | 'remove_role',
    data?: { role_id?: number; reason?: string },
  ): Promise<BatchUserResult> {
    return await apiClient.post<any>('/api/v1/users/batch', {
      action,
      user_ids: userIds.map((id) => Number(id)),
      role_id: data?.role_id,
      reason: data?.reason,
    })
  }

  async exportUsers(params: UserListParams = {}): Promise<Blob> {
    const queryParams = new URLSearchParams()
    appendParam(queryParams, 'search', params.search)
    appendParam(queryParams, 'status', params.status)
    appendParam(queryParams, 'role', params.role)

    return await apiClient.get<Blob>(`/api/v1/users/export?${queryParams.toString()}`, {
      responseType: 'blob',
    })
  }

  async importUsers(file: File): Promise<ImportUserResult> {
    const formData = new FormData()
    formData.append('file', file)

    return await apiClient.post<any>('/api/v1/users/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }
}

export const userService = new UserService()
export default userService
