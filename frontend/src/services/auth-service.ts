// @ts-nocheck
import { apiClient } from '@/lib/api-client'
import { createApiError } from '@/lib/api-error-handler'
import type { User } from '@/types'

export interface LoginCredentials {
  username: string
  password: string
  rememberMe?: boolean
}

export interface RegisterData {
  username: string
  email: string
  password: string
  first_name?: string
  last_name?: string
}

export interface AuthResponse {
  user: User
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
}

export interface TokenRefreshResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface PasswordChangeData {
  old_password?: string
  current_password?: string
  new_password: string
}

export interface PasswordResetData {
  email: string
}

export interface PasswordResetConfirmData {
  token: string
  newPassword: string
  confirmPassword: string
}

const ACCESS_TOKEN_KEY = 'auth-access-token'
const REFRESH_TOKEN_KEY = 'auth-refresh-token'
const TOKEN_EXPIRY_KEY = 'auth-token-expiry'
const USER_KEY = 'auth-user'

const clearPersistedAuth = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(TOKEN_EXPIRY_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem('auth-storage')
  localStorage.removeItem('auth_token')
  localStorage.removeItem('token')
  localStorage.removeItem('persist:auth')
  localStorage.removeItem('persist:root')
  sessionStorage.clear()
}

const unwrap = (response: any) => {
  if (response?.success && response?.data) return response.data
  if (response?.data && !response?.access_token && !response?.token) return response.data
  return response
}

const normalizeUser = (rawUser: any = {}): User => ({
  id: Number(rawUser.id ?? rawUser.user_id ?? 0),
  username: String(rawUser.username || ''),
  email: String(rawUser.email || ''),
  real_name: rawUser.real_name || rawUser.full_name || rawUser.nickname || rawUser.username || '',
  nickname: rawUser.nickname || '',
  phone: rawUser.phone || '',
  avatar: rawUser.avatar || rawUser.avatar_url || '',
  role: rawUser.role || rawUser.roles?.[0]?.code || 'USER',
  status: rawUser.status || (rawUser.is_active === false ? 'disabled' : 'active'),
  is_active: rawUser.is_active !== false,
  is_super_admin: Boolean(rawUser.is_super_admin || rawUser.is_superuser),
  last_login_at: rawUser.last_login_at,
  created_at: rawUser.created_at || new Date().toISOString(),
  updated_at: rawUser.updated_at || new Date().toISOString(),
  roles: rawUser.roles || [],
  permissions: rawUser.permissions || [],
})

class TokenManager {
  setTokens(accessToken: string, refreshToken = '', expiresIn = 3600) {
    const expiryTime = Date.now() + expiresIn * 1000
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    localStorage.setItem(TOKEN_EXPIRY_KEY, String(expiryTime))

    try {
      apiClient.defaults.headers.common.Authorization = `Bearer ${accessToken}`
    } catch {
      // Some test doubles do not expose axios defaults.
    }
  }

  getAccessToken() {
    const directToken = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (directToken) return directToken

    try {
      const persisted = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      return persisted?.state?.token || null
    } catch {
      return null
    }
  }

  getRefreshToken() {
    const directToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (directToken) return directToken

    try {
      const persisted = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      return persisted?.state?.refreshToken || null
    } catch {
      return null
    }
  }

  isTokenExpired() {
    const expiryTime = Number(localStorage.getItem(TOKEN_EXPIRY_KEY) || 0)
    if (!expiryTime) return false
    return Date.now() >= expiryTime
  }

  isTokenExpiringSoon() {
    const expiryTime = Number(localStorage.getItem(TOKEN_EXPIRY_KEY) || 0)
    if (!expiryTime) return false
    return Date.now() + 5 * 60 * 1000 >= expiryTime
  }

  clearTokens() {
    clearPersistedAuth()
    try {
      delete apiClient.defaults.headers.common.Authorization
    } catch {
      // Ignore non-axios compatible clients.
    }
  }

  setUser(user: User) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }

  getUser(): User | null {
    try {
      const localUser = localStorage.getItem(USER_KEY)
      if (localUser) return JSON.parse(localUser)

      const persisted = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      return persisted?.state?.user || null
    } catch {
      return null
    }
  }

  isAuthenticated() {
    return Boolean(this.getAccessToken()) && !this.isTokenExpired()
  }
}

export class AuthService {
  private tokenManager = new TokenManager()
  private refreshPromise: Promise<TokenRefreshResponse> | null = null
  private refreshTimer: ReturnType<typeof setInterval> | null = null

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = unwrap(await apiClient.post('/auth/login', credentials))
      const accessToken = response.access_token || response.accessToken || response.token
      const refreshToken = response.refresh_token || response.refreshToken || ''
      const expiresIn = Number(response.expires_in || response.expiresIn || 3600)

      if (!accessToken) {
        throw new Error('登录响应缺少访问令牌')
      }

      const user = normalizeUser(response.user || response)
      const authResponse: AuthResponse = {
        user,
        accessToken,
        refreshToken,
        tokenType: response.token_type || response.tokenType || 'Bearer',
        expiresIn,
      }

      this.tokenManager.setTokens(accessToken, refreshToken, expiresIn)
      this.tokenManager.setUser(user)
      this.startTokenRefreshTimer()
      window.dispatchEvent(new CustomEvent('auth:login', { detail: user }))

      return authResponse
    } catch (error) {
      throw createApiError('登录失败，请检查用户名和密码', 'LOGIN_FAILED', 401, error)
    }
  }

  async register(userData: RegisterData): Promise<User> {
    try {
      const response = unwrap(await apiClient.post('/auth/register', userData))
      return normalizeUser(response.user || response)
    } catch (error) {
      throw createApiError('注册失败，请检查输入信息', 'REGISTER_FAILED', 400, error)
    }
  }

  async logout(skipApiCall = false): Promise<void> {
    try {
      if (!skipApiCall && this.getAccessToken()) {
        await apiClient.post('/auth/logout')
      }
    } catch {
      // Local logout must still happen even when the API is unavailable.
    } finally {
      this.logoutLocally()
    }
  }

  logoutLocally(): void {
    this.stopTokenRefreshTimer()
    this.tokenManager.clearTokens()
    window.dispatchEvent(new CustomEvent('auth:logout'))
  }

  async refreshToken(): Promise<TokenRefreshResponse> {
    if (this.refreshPromise) return this.refreshPromise

    const refreshToken = this.tokenManager.getRefreshToken()
    if (!refreshToken) {
      this.logoutLocally()
      throw createApiError('没有刷新令牌', 'NO_REFRESH_TOKEN', 401)
    }

    this.refreshPromise = this.performTokenRefresh(refreshToken)

    try {
      const response = await this.refreshPromise
      this.tokenManager.setTokens(response.accessToken, response.refreshToken, response.expiresIn)
      return response
    } catch (error) {
      this.logoutLocally()
      throw error
    } finally {
      this.refreshPromise = null
    }
  }

  private async performTokenRefresh(refreshToken: string): Promise<TokenRefreshResponse> {
    const response = unwrap(await apiClient.post('/auth/refresh', { refresh_token: refreshToken }))
    return {
      accessToken: response.access_token || response.accessToken || response.token,
      refreshToken: response.refresh_token || response.refreshToken || refreshToken,
      expiresIn: Number(response.expires_in || response.expiresIn || 3600),
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = unwrap(await apiClient.get('/auth/me'))
      const user = normalizeUser(response.user || response)
      this.tokenManager.setUser(user)
      return user
    } catch (error) {
      throw createApiError('获取用户信息失败', 'GET_USER_FAILED', undefined, error)
    }
  }

  async updateProfile(updates: Partial<User>): Promise<User> {
    const currentUser = this.getCurrentUserFromStorage()
    if (!currentUser) throw createApiError('用户未登录', 'NOT_AUTHENTICATED', 401)

    await apiClient.put(`/users/${currentUser.id}`, updates)
    const updatedUser = await this.getCurrentUser()
    window.dispatchEvent(new CustomEvent('auth:profile-updated', { detail: updatedUser }))
    return updatedUser
  }

  async changePassword(data: PasswordChangeData): Promise<void> {
    await apiClient.put('/auth/change-password', {
      current_password: data.current_password || data.old_password,
      old_password: data.old_password || data.current_password,
      new_password: data.new_password,
    })
  }

  async requestPasswordReset(data: PasswordResetData): Promise<void> {
    await apiClient.post('/auth/forgot-password', data)
  }

  async confirmPasswordReset(data: PasswordResetConfirmData): Promise<void> {
    if (data.newPassword !== data.confirmPassword) {
      throw createApiError('两次输入的密码不一致', 'PASSWORD_MISMATCH', 400)
    }

    await apiClient.post('/auth/reset-password', {
      token: data.token,
      new_password: data.newPassword,
      confirm_password: data.confirmPassword,
    })
  }

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/auth/verify-email', { token })
  }

  async resendVerificationEmail(): Promise<void> {
    await apiClient.post('/auth/resend-verification-email')
  }

  async getUserPermissions(): Promise<{ roles: any[]; permissions: string[] }> {
    const response = unwrap(await apiClient.get('/auth/permissions'))
    return {
      roles: response.roles || [],
      permissions: response.permissions || response.all_permissions || [],
    }
  }

  isAuthenticated(): boolean {
    return this.tokenManager.isAuthenticated()
  }

  getCurrentUserFromStorage(): User | null {
    return this.tokenManager.getUser()
  }

  getAccessToken(): string | null {
    return this.tokenManager.getAccessToken()
  }

  async checkAndRefreshToken(): Promise<void> {
    if (!this.isAuthenticated()) return
    if (this.tokenManager.isTokenExpiringSoon()) {
      await this.refreshToken()
    }
  }

  startTokenRefreshTimer(): void {
    this.stopTokenRefreshTimer()
    this.refreshTimer = setInterval(() => {
      this.checkAndRefreshToken().catch(() => undefined)
    }, 60 * 1000)
  }

  stopTokenRefreshTimer(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer)
      this.refreshTimer = null
    }
  }

  hasPermission(permission: string): boolean {
    const user = this.getCurrentUserFromStorage()
    if (!user) return false
    if (user.is_super_admin || user.role === 'admin' || user.role === 'ADMIN') return true
    return (user.permissions || []).some((item: any) => item === permission || item.code === permission)
  }

  hasRole(role: string): boolean {
    const user = this.getCurrentUserFromStorage()
    if (!user) return false
    return user.role === role || (user.roles || []).some((item: any) => item.code === role || item.name === role)
  }
}

export const authService = new AuthService()

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && authService.isAuthenticated()) {
    authService.checkAndRefreshToken().catch(() => undefined)
  }
})

export default authService
