// 基础类型定义

export interface User {
  id: number
  username: string
  email: string
  real_name?: string
  nickname?: string
  phone?: string
  avatar?: string
  role: string
  status: 'active' | 'locked' | 'pending' | 'disabled' | 'deleted'
  is_active: boolean
  is_super_admin?: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
  roles?: Role[]
  permissions?: Permission[]
  // 扩展字段
  bio?: string
  gender?: 'male' | 'female' | 'other' | 'unknown'
  birthday?: string
  location?: string
  website?: string
  language?: string
  timezone?: string
  theme?: string
  email_notifications?: boolean
  sms_notifications?: boolean
  push_notifications?: boolean
  is_email_verified?: boolean
  is_phone_verified?: boolean
  mfa_enabled?: boolean
  failed_login_attempts?: number
  locked_until?: string
}

export interface Role {
  id: number
  code: string
  name: string
  description?: string
  is_system_role: boolean
  is_active: boolean
  priority: number
  created_at: string
  updated_at: string
  permissions?: Permission[]
  // 扩展字段
  color?: string
  icon?: string
  sort_order?: number
  parent_id?: number
  level?: number
  path?: string
}

export interface Permission {
  id: number
  code: string
  name: string
  module: string
  action: string
  resource?: string
  description?: string
  created_at: string
  updated_at?: string
  // 扩展字段
  is_system_permission?: boolean
  parent_id?: number
  level?: number
  sort_order?: number
  conditions?: any
  effect?: 'allow' | 'deny'
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface PaginatedResponse<T = any> {
  data: T[]
  total: number
  page: number
  size: number
  totalPages: number
}

export interface LoginRequest {
  username: string
  password: string
  rememberMe?: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface CreateUserRequest {
  username: string
  email: string
  password: string
  nickname?: string
  phone?: string
  role_ids?: number[]
}

export interface UpdateUserRequest {
  nickname?: string
  phone?: string
  avatar?: string
  bio?: string
  gender?: string
  birthday?: string
  location?: string
  website?: string
  language?: string
  timezone?: string
  theme?: string
  email_notifications?: boolean
  sms_notifications?: boolean
  push_notifications?: boolean
  role_ids?: number[]
}

export interface CreateRoleRequest {
  code: string
  name: string
  description?: string
  permission_ids?: number[]
}

export interface UpdateRoleRequest {
  name?: string
  description?: string
  permission_ids?: number[]
}

export interface CreatePermissionRequest {
  code: string
  name: string
  module: string
  action: string
  resource?: string
  description?: string
}

export interface UpdatePermissionRequest {
  name?: string
  module?: string
  action?: string
  resource?: string
  description?: string
}

export interface UserFilters {
  search?: string
  status?: string
  role?: string
  page?: number
  size?: number
  pageSize?: number
}

export interface RoleFilters {
  search?: string
  isActive?: boolean
  type?: string
  status?: string
  page?: number
  size?: number
  pageSize?: number
}

export interface PermissionMatrix {
  roles: Role[]
  permissions: Permission[]
  matrix: Record<string, Record<string, boolean>>
}

export interface Theme {
  mode: 'light' | 'dark'
  primaryColor: string
}

export interface ApiError {
  code: string
  message: string
  details?: any
}

export interface AppError {
  type: 'validation' | 'network' | 'auth' | 'server' | 'unknown'
  message: string
  code?: string
  details?: any
}

export interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

// 用户相关类型
export interface UserSearchParams {
  keyword?: string
  status?: string
  role_id?: number
  page?: number
  size?: number
}

export interface UserCreateParams {
  username: string
  email: string
  password: string
  nickname?: string
  phone?: string
  role_ids?: number[]
}

export interface UserUpdateParams {
  nickname?: string
  phone?: string
  avatar?: string
  role_ids?: number[]
}

export interface PasswordChangeParams {
  current_password: string
  new_password: string
  confirm_password: string
}

// 角色相关类型
export interface RoleSearchParams {
  keyword?: string
  is_active?: boolean
  page?: number
  size?: number
}

export interface RoleCreateParams {
  code: string
  name: string
  description?: string
  permission_ids?: number[]
}

export interface RoleUpdateParams {
  name?: string
  description?: string
  permission_ids?: number[]
}

// 权限相关类型
export interface PermissionSearchParams {
  keyword?: string
  module?: string
  page?: number
  size?: number
}

export interface PermissionCreateParams {
  code: string
  name: string
  module: string
  action: string
  resource?: string
  description?: string
}

export interface PermissionUpdateParams {
  name?: string
  module?: string
  action?: string
  resource?: string
  description?: string
}

// 审计日志相关
export interface AuditLog {
  id: number
  user_id?: number
  action: string
  resource_type: string
  resource_id?: string
  old_values?: any
  new_values?: any
  ip_address?: string
  user_agent?: string
  result: 'success' | 'failure' | 'partial_success'
  error_message?: string
  created_at: string
}

// 统计相关
export interface UserStats {
  total_users: number
  active_users: number
  inactive_users: number
  locked_users: number
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
}

// 批量操作
export interface BatchOperationRequest {
  action: 'activate' | 'deactivate' | 'delete' | 'assign_role' | 'remove_role'
  user_ids: number[]
  role_id?: number
  reason?: string
}

export interface BatchOperationResponse {
  success_count: number
  failed_count: number
  total_count: number
  failed_users: Array<{
    user_id: number
    username?: string
    error: string
  }>
  message: string
}

// 导入导出
export interface ImportUsersResponse {
  success_count: number
  failed_count: number
  total_count: number
  failed_users: Array<{
    row: number
    username: string
    email: string
    error: string
  }>
  message: string
}

// 高级用户管理类型
export interface UserStatistics {
  total_users: number
  status_statistics: Record<string, number>
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
  recent_active_users: number
  inactive_users: number
}

export interface AdvancedUserFilters {
  search?: string
  status?: string
  created_after?: string
  created_before?: string
  last_login_after?: string
  last_login_before?: string
  is_active?: boolean
  is_superuser?: boolean
  is_email_verified?: boolean
  is_phone_verified?: boolean
  mfa_enabled?: boolean
}

export interface UserActivityLog {
  id: number
  action: string
  resource_type: string
  resource_id?: string
  ip_address?: string
  user_agent?: string
  result: string
  error_message?: string
  created_at: string
}

export interface UserSession {
  id: number
  device_info?: string
  ip_address?: string
  user_agent?: string
  is_active: boolean
  created_at: string
  last_activity?: string
  expires_at?: string
}

export interface MFASetupData {
  secret: string
  qr_code: string
  backup_codes: string[]
  provisioning_uri: string
}

export interface PasswordChangeData {
  current_password: string
  new_password: string
}

export interface MFAVerificationData {
  verification_code: string
}

// 权限管理类型
export interface PermissionTree {
  id: number
  code: string
  name: string
  description?: string
  module: string
  action: string
  resource?: string
  permission_type: 'menu' | 'button' | 'api' | 'data' | 'field'
  level: number
  parent_id?: number
  sort_order: number
  is_active: boolean
  children: PermissionTree[]
}

export interface UserPermissions {
  user_id: number
  username: string
  roles: Array<{
    code: string
    name: string
  }>
  role_permissions: Record<string, Permission[]>
  direct_permissions: Permission[]
  all_permissions: string[]
}

export interface PermissionAssignment {
  permission_id: number
  effect: 'allow' | 'deny'
  expires_at?: string
  reason?: string
}

export interface PermissionCheck {
  permissions: Record<string, boolean>
}

// 角色管理扩展类型
export interface RoleStatistics {
  total_roles: number
  active_roles: number
  inactive_roles: number
  system_roles: number
  custom_roles: number
  user_distribution: Array<{
    role_name: string
    user_count: number
  }>
}

export interface RoleTree {
  id: number
  code: string
  name: string
  description?: string
  color?: string
  icon?: string
  level: number
  parent_id?: number
  is_active: boolean
  is_system_role: boolean
  user_count: number
  permission_count: number
  children: RoleTree[]
}

export interface RoleAssignment {
  user_ids: number[]
  role_id: number
}

export interface RolePermissionAssignment {
  permission_ids: number[]
  effect: 'allow' | 'deny'
  conditions?: any
}

// 其他请求响应类型
export interface UserUnlockRequest {
  reason?: string
}

export interface UserProfileResponse extends User {
  // 扩展字段
}

export interface ResendVerificationEmailRequest {
  email: string
}

export interface ResendVerificationEmailResponse {
  message: string
}

export interface SearchParams {
  q?: string
  page?: number
  size?: number
  sort?: string
  order?: 'asc' | 'desc'
}
