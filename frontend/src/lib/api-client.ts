import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

interface DataApiClient extends Omit<AxiosInstance, 'get' | 'post' | 'put' | 'patch' | 'delete'> {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  upload<T = any>(url: string, file: File | Blob | FormData, config?: AxiosRequestConfig): Promise<T>
  download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<void>
}

const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000,
  retries: 2,
  retryDelay: 1000,
}

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

const clearAuthAndRedirect = () => {
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

  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

const createApiClient = (): DataApiClient => {
  const client = axios.create({
    baseURL: API_CONFIG.baseURL,
    timeout: API_CONFIG.timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  client.interceptors.request.use((config) => {
    config.url = normalizeEndpoint(config.url)

    const token = getAuthToken()
    if (token) {
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }

    ;(config.headers as any)['X-Request-ID'] = generateRequestId()
    return config
  })

  client.interceptors.response.use(
    (response: AxiosResponse) => response.data,
    async (error: AxiosError) => {
      if (error.response?.status === 401) {
        clearAuthAndRedirect()
        return Promise.reject(new Error('登录已过期，请重新登录。'))
      }

      if (shouldRetry(error)) {
        return retryRequest(client, error)
      }

      return Promise.reject(handleApiError(error))
    },
  )

  const dataClient = client as unknown as DataApiClient

  dataClient.upload = async <T = any>(url: string, file: File | Blob | FormData, config?: AxiosRequestConfig): Promise<T> => {
    const formData = file instanceof FormData ? file : new FormData()
    if (!(file instanceof FormData)) {
      formData.append('file', file)
    }

    return dataClient.post<T>(url, formData, {
      ...config,
      headers: {
        ...(config?.headers || {}),
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  dataClient.download = async (url: string, filename = 'download', config?: AxiosRequestConfig): Promise<void> => {
    const blob = await dataClient.get<Blob>(url, {
      ...config,
      responseType: 'blob',
    })

    const objectUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(objectUrl)
  }

  return dataClient
}

function shouldRetry(error: AxiosError): boolean {
  if (!error.config) return false
  const config = error.config as any
  const currentRetries = config.__retries || 0
  if (currentRetries >= API_CONFIG.retries) return false
  return !error.response || (error.response.status >= 500 && error.response.status < 600)
}

async function retryRequest(client: AxiosInstance, error: AxiosError): Promise<any> {
  const config = error.config as any
  config.__retries = (config.__retries || 0) + 1
  const delay = API_CONFIG.retryDelay * Math.pow(2, config.__retries - 1)
  await new Promise((resolve) => setTimeout(resolve, delay))
  return client(config)
}

function handleApiError(error: AxiosError): Error {
  if (error.response) {
    const { status, data } = error.response
    if (status === 403) return new Error('权限不足，无法执行此操作。')
    if (status === 404) return new Error('请求的资源不存在。')
    if (status === 422) return new Error(extractValidationMessage(data) || '请求参数验证失败。')

    const detail = (data as any)?.message || (data as any)?.detail || (data as any)?.error
    if (typeof detail === 'string') return new Error(detail)
    if (Array.isArray(detail)) return new Error(detail.map((item: any) => item?.msg || String(item)).join('; '))
    return new Error('请求失败。')
  }

  if (error.request) return new Error('网络连接失败，请检查网络或后端服务。')
  return new Error(error.message || '未知错误。')
}

function extractValidationMessage(data: any): string | null {
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item: any) => `${item.loc?.join('.') || '字段'}: ${item.msg}`).join('; ')
  }
  return typeof data?.detail === 'string' ? data.detail : null
}

function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
}

export const apiClient = createApiClient()
export type { AxiosRequestConfig, AxiosResponse }
