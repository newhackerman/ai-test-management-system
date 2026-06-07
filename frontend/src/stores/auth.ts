// @ts-nocheck
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Role } from '@/types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  permissions: string[]
  roles: Role[]
}

interface AuthActions {
  login: (user: User, token: string, refreshToken?: string) => void
  logout: () => Promise<void>
  updateUser: (user: User) => void
  setPermissions: (permissions: string[]) => void
  setRoles: (roles: Role[]) => void
  clearAuth: () => void
  checkAuth: () => Promise<void>
  getCurrentUser: () => Promise<User | null>
}

const clearPersistedAuth = () => {
  localStorage.removeItem('auth-storage')
  localStorage.removeItem('auth_token')
  localStorage.removeItem('token')
  localStorage.removeItem('persist:auth')
  localStorage.removeItem('persist:root')
  localStorage.removeItem('auth-access-token')
  localStorage.removeItem('auth-refresh-token')
  localStorage.removeItem('auth-token-expiry')
  localStorage.removeItem('auth-user')
  sessionStorage.clear()
}

const permissionCodes = (permissions: any[] = []) =>
  permissions.map((item) => (typeof item === 'string' ? item : item?.code)).filter(Boolean)

const normalizeUser = (payload: any, fallback?: User | null): User => {
  const source = payload?.user_info || payload?.user || payload || {}
  const roles = payload?.roles || source.roles || fallback?.roles || []
  const permissions = payload?.permissions || source.permissions || fallback?.permissions || []
  const username = source.username || fallback?.username || ''
  const isSuperAdmin = Boolean(source.is_super_admin || source.is_superuser || source.isSuperAdmin)

  return {
    ...(fallback || {}),
    id: Number(source.id ?? source.user_id ?? fallback?.id ?? 0),
    username,
    email: source.email ?? fallback?.email ?? '',
    real_name: source.real_name || source.full_name || source.nickname || fallback?.real_name || username,
    nickname: source.nickname ?? fallback?.nickname ?? '',
    phone: source.phone ?? fallback?.phone ?? '',
    avatar: source.avatar ?? source.avatar_url ?? fallback?.avatar ?? '',
    role: source.role || roles?.[0]?.code || fallback?.role || (isSuperAdmin ? 'admin' : 'USER'),
    status: source.status || (source.is_active === false ? 'disabled' : fallback?.status || 'active'),
    is_active: source.is_active !== false,
    is_super_admin: isSuperAdmin,
    isSuperAdmin,
    last_login_at: source.last_login_at ?? fallback?.last_login_at,
    created_at: source.created_at || fallback?.created_at || new Date().toISOString(),
    updated_at: source.updated_at || fallback?.updated_at || new Date().toISOString(),
    roles,
    permissions,
    bio: source.bio ?? fallback?.bio,
    gender: source.gender ?? fallback?.gender,
    birthday: source.birthday ?? fallback?.birthday,
    location: source.location ?? fallback?.location,
    website: source.website ?? fallback?.website,
    language: source.language ?? fallback?.language,
    timezone: source.timezone ?? fallback?.timezone,
    theme: source.theme ?? fallback?.theme,
    email_notifications: source.email_notifications ?? fallback?.email_notifications,
    sms_notifications: source.sms_notifications ?? fallback?.sms_notifications,
    push_notifications: source.push_notifications ?? fallback?.push_notifications,
    mfa_enabled: source.mfa_enabled ?? fallback?.mfa_enabled,
    failed_login_attempts: source.failed_login_attempts ?? fallback?.failed_login_attempts,
  } as User
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
      permissions: [],
      roles: [],

      login: (user, token, refreshToken = '') => {
        const normalizedUser = normalizeUser(user)
        set({
          user: normalizedUser,
          token,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
          permissions: permissionCodes(normalizedUser.permissions),
          roles: normalizedUser.roles || [],
        })
      },

      logout: async () => {
        const { token } = get()
        if (token) {
          try {
            await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            })
          } catch (error) {
            console.warn('退出登录接口调用失败，已执行本地退出。', error)
          }
        }

        clearPersistedAuth()
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          permissions: [],
          roles: [],
        })
      },

      updateUser: (user) => {
        const normalizedUser = normalizeUser(user, get().user)
        set({
          user: normalizedUser,
          permissions: permissionCodes(normalizedUser.permissions),
          roles: normalizedUser.roles || [],
        })
      },

      setPermissions: (permissions) => set({ permissions }),

      setRoles: (roles) => set({ roles }),

      clearAuth: () => {
        clearPersistedAuth()
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          permissions: [],
          roles: [],
        })
      },

      checkAuth: async () => {
        const { token, user } = get()
        if (!token) {
          set({ isAuthenticated: false, isLoading: false })
          return
        }

        set({ isLoading: true })
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/profile`, {
            headers: { Authorization: `Bearer ${token}` },
          })

          if (!response.ok) {
            get().clearAuth()
            return
          }

          const data = await response.json()
          const normalizedUser = normalizeUser(data, user)
          set({
            user: normalizedUser,
            isAuthenticated: true,
            isLoading: false,
            permissions: permissionCodes(normalizedUser.permissions),
            roles: normalizedUser.roles || [],
          })
        } catch (error) {
          console.warn('认证检查失败，已清理本地登录状态。', error)
          get().clearAuth()
        }
      },

      getCurrentUser: async () => {
        const { token, user } = get()
        if (!token) return null

        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/profile`, {
            headers: { Authorization: `Bearer ${token}` },
          })
          if (!response.ok) {
            get().clearAuth()
            return null
          }

          const data = await response.json()
          const normalizedUser = normalizeUser(data, user)
          set({
            user: normalizedUser,
            isAuthenticated: true,
            isLoading: false,
            permissions: permissionCodes(normalizedUser.permissions),
            roles: normalizedUser.roles || [],
          })
          return normalizedUser
        } catch (error) {
          console.warn('获取当前用户失败。', error)
          set({ isLoading: false })
          return user
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        permissions: state.permissions,
        roles: state.roles,
      }),
    },
  ),
)

export const usePermissions = () => {
  const { user, permissions, roles } = useAuthStore()

  const hasPermission = (permission: string): boolean => {
    if (!user) return false
    if (user.is_super_admin || user.isSuperAdmin) return true
    return permissions.includes(permission)
  }

  const hasRole = (roleCode: string): boolean => {
    if (!user) return false
    return roles.some((role) => role.code === roleCode)
  }

  const hasAnyRole = (roleCodes: string[]): boolean => roleCodes.some((roleCode) => hasRole(roleCode))
  const hasAllRoles = (roleCodes: string[]): boolean => roleCodes.every((roleCode) => hasRole(roleCode))
  const hasAnyPermission = (permissionCodes: string[]): boolean => permissionCodes.some((code) => hasPermission(code))
  const hasAllPermissions = (permissionCodes: string[]): boolean => permissionCodes.every((code) => hasPermission(code))

  return {
    user,
    permissions,
    roles,
    hasPermission,
    hasRole,
    hasAnyRole,
    hasAllRoles,
    hasAnyPermission,
    hasAllPermissions,
  }
}

export const useAuth = () => {
  const store = useAuthStore()
  return {
    user: store.user,
    token: store.token,
    refreshToken: store.refreshToken,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    login: store.login,
    logout: store.logout,
    updateUser: store.updateUser,
    clearAuth: store.clearAuth,
  }
}
