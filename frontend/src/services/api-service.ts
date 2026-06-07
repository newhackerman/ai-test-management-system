// @ts-nocheck
/**
 * 缁熶竴API鏈嶅姟
 * 鎻愪緵甯﹁璇佺殑API璋冪敤鏂规硶
 */

import { useAuthStore } from '@/stores/auth'

class ApiService {
  private baseURL: string
  
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  }

  private getAuthHeaders(): HeadersInit {
    const authStorage = localStorage.getItem('auth-storage')
    const headers: HeadersInit = {
      'Content-Type': 'application/json'
    }

    if (authStorage) {
      try {
        const authData = JSON.parse(authStorage)
        const token = authData.state?.token
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }
      } catch (error) {
        console.error('瑙ｆ瀽璁よ瘉鏁版嵁澶辫触:', error)
      }
    }

    return headers
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      // 娓呴櫎璁よ瘉鐘舵€佸苟閲嶅畾鍚戝埌鐧诲綍椤?
      localStorage.removeItem('auth-storage')
      localStorage.removeItem('auth-token')
      localStorage.removeItem('refresh-token')
      sessionStorage.clear()
      window.location.href = '/login'
      throw new Error('登录已过期，请重新登录')
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`
      try {
        const errorData = await response.json()
        console.error('API閿欒璇︽儏:', errorData)
        
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // 澶勭悊楠岃瘉閿欒
            errorMessage = errorData.detail.map((item: any) => 
              `${item.loc?.join('.')}: ${item.msg}`
            ).join(', ')
          } else if (typeof errorData.detail === 'object' && errorData.detail.message) {
            // 澶勭悊缁撴瀯鍖栭敊璇?
            errorMessage = errorData.detail.message
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail
          } else {
            errorMessage = JSON.stringify(errorData.detail)
          }
        } else if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch (e) {
        console.error('瑙ｆ瀽閿欒鍝嶅簲澶辫触:', e)
      }
      
      throw new Error(errorMessage)
    }

    return response.json()
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    })

    return this.handleResponse<T>(response)
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: data ? JSON.stringify(data) : undefined
    })

    return this.handleResponse<T>(response)
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: data ? JSON.stringify(data) : undefined
    })

    return this.handleResponse<T>(response)
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    })

    return this.handleResponse<T>(response)
  }

  // 涓撻棬鐢ㄤ簬鑾峰彇鐢ㄦ埛鍒楄〃鐨勬柟娉?
  async getUsers(params: { skip?: number; limit?: number } = {}) {
    const queryParams = new URLSearchParams()
    if (params.skip !== undefined) queryParams.append('skip', String(params.skip))
    // 纭繚limit涓嶈秴杩?00
    const limit = Math.min(params.limit || 10, 100)
    queryParams.append('limit', String(limit))
    
    const endpoint = `/api/v1/users${queryParams.toString() ? '?' + queryParams.toString() : ''}`
    return this.get(endpoint)
  }

  // 鑾峰彇鎵€鏈夌敤鎴凤紙鍒嗛〉鑾峰彇锛?
  async getAllUsers() {
    const allUsers = []
    let skip = 0
    const limit = 100
    let hasMore = true

    while (hasMore) {
      const response = await this.getUsers({ skip, limit })
      allUsers.push(...response.users)
      
      skip += limit
      hasMore = response.users.length === limit && skip < response.total
    }

    return {
      users: allUsers,
      total: allUsers.length
    }
  }
}

export const apiService = new ApiService()
export default apiService
