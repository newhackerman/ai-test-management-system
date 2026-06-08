// @ts-nocheck
import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { message } from 'antd'

const normalizeEndpoint = (url?: string) => {
  if (!url || /^https?:\/\//i.test(url)) return url
  const endpoint = url.startsWith('/') ? url : `/${url}`
  return endpoint.startsWith('/api/') ? endpoint : `/api/v1${endpoint}`
}

const getAuthToken = () => {
  const directToken = localStorage.getItem('auth-access-token') || localStorage.getItem('auth_token') || localStorage.getItem('token')
  if (directToken) return directToken

  try {
    return JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token || null
  } catch {
    return null
  }
}

const getErrorMessage = (data: any, fallback = '请求失败。') => {
  const detail = data?.message ?? data?.detail ?? data?.error ?? fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item))).join('; ')
  }
  if (detail && typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return String(detail)
}

const clearAuthAndRedirect = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('token')
  localStorage.removeItem('auth-storage')
  localStorage.removeItem('persist:auth')
  localStorage.removeItem('persist:root')
  localStorage.removeItem('auth-access-token')
  localStorage.removeItem('auth-refresh-token')
  localStorage.removeItem('auth-token-expiry')
  localStorage.removeItem('auth-user')
  sessionStorage.clear()

  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    config.url = normalizeEndpoint(config.url)
    const token = getAuthToken()

    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        message.error('登录已过期，请重新登录。')
        clearAuthAndRedirect()
      } else if (status === 403) {
        message.error('没有权限访问该资源。')
      } else if (status === 404) {
        message.error('请求的资源不存在。')
      } else if (status >= 500) {
        message.error(getErrorMessage(data, '服务器内部错误。'))
      } else {
        message.error(getErrorMessage(data))
      }
    } else if (error.request) {
      message.error('网络错误，请检查连接或后端服务。')
    } else {
      message.error('请求配置错误。')
    }

    return Promise.reject(error)
  },
)

export default apiClient
