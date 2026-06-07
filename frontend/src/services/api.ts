import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'antd'

const API_PREFIX = '/api/v1'

const normalizeBaseURL = (url?: string) => {
  const baseURL = url || 'http://localhost:8000'
  return baseURL.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '')
}

const normalizeEndpoint = (url?: string) => {
  if (!url || /^https?:\/\//i.test(url)) return url
  const endpoint = url.startsWith('/') ? url : `/${url}`
  return endpoint.startsWith('/api/') ? endpoint : `${API_PREFIX}${endpoint}`
}

const getPersistedAuthToken = () => {
  const legacyToken =
    localStorage.getItem('auth-access-token') ||
    localStorage.getItem('auth_token') ||
    localStorage.getItem('auth-token') ||
    localStorage.getItem('token')
  if (legacyToken) return legacyToken

  const authStorage = localStorage.getItem('auth-storage')
  if (!authStorage) return null

  try {
    return JSON.parse(authStorage)?.state?.token || null
  } catch {
    return null
  }
}

const clearAuth = () => {
  localStorage.removeItem('auth-access-token')
  localStorage.removeItem('auth-refresh-token')
  localStorage.removeItem('auth-token-expiry')
  localStorage.removeItem('auth-user')
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth-token')
  localStorage.removeItem('token')
  localStorage.removeItem('refresh-token')
  localStorage.removeItem('auth-storage')
  localStorage.removeItem('persist:auth')
  localStorage.removeItem('persist:root')
  sessionStorage.clear()
  window.dispatchEvent(new Event('auth:logout'))
}

const api = axios.create({
  baseURL: normalizeBaseURL(import.meta.env.VITE_API_BASE_URL),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    config.url = normalizeEndpoint(config.url)
    const token = getPersistedAuthToken()

    if (token) {
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }

    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: AxiosError<any>) => {
    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        clearAuth()
        message.error('登录已过期，请重新登录')
        if (window.location.pathname !== '/login') window.location.href = '/login'
      } else if (status === 403) {
        message.error('没有权限访问该资源')
      } else if (status === 404) {
        message.error('请求的资源不存在')
      } else if (status >= 500) {
        message.error('服务器内部错误')
      } else {
        message.error(data?.message || data?.detail || '请求失败')
      }
    } else if (error.request) {
      message.error('网络错误，请检查网络连接')
    } else {
      message.error('请求配置错误')
    }

    return Promise.reject(error)
  },
)

export { api }
export const apiClient = api
export type { AxiosRequestConfig, AxiosResponse }
export default api
