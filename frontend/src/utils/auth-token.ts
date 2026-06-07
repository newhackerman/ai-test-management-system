/**
 * 认证token工具函数
 */

/**
 * 获取当前用户的认证token
 * @returns token字符串或null
 */
export const getAuthToken = (): string | null => {
  const authStorage = localStorage.getItem('auth-storage')
  
  if (!authStorage) {
    return null
  }

  try {
    const authData = JSON.parse(authStorage)
    return authData.state?.token || null
  } catch (error) {
    console.error('解析认证数据失败:', error)
    return null
  }
}

/**
 * 获取认证请求头
 * @returns 包含Authorization头的对象
 */
export const getAuthHeaders = (): HeadersInit => {
  const token = getAuthToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

/**
 * 检查是否有有效的认证token
 * @returns boolean
 */
export const hasValidToken = (): boolean => {
  const token = getAuthToken()
  return !!token && token.length > 0
}

/**
 * 清除认证数据
 */
export const clearAuthData = (): void => {
  localStorage.removeItem('auth-storage')
}