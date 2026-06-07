/**
 * API错误处理工具
 */

export interface ApiError extends Error {
  code?: string
  status?: number
  details?: any
}

/**
 * 创建API错误
 */
export function createApiError(
  message: string,
  code?: string,
  status?: number,
  originalError?: any
): ApiError {
  const error = new Error(message) as ApiError
  error.code = code
  error.status = status
  error.details = originalError

  // 如果原始错误有更详细的信息，使用它
  if (originalError?.message) {
    error.message = originalError.message
  }

  return error
}

/**
 * 处理API错误响应
 */
export function handleApiError(error: any): ApiError {
  if (error.response) {
    // 服务器返回错误状态码
    const { status, data } = error.response
    const message = data?.message || data?.detail || `请求失败 (${status})`
    return createApiError(message, data?.code, status, error)
  }

  if (error.request) {
    // 请求发送但没有收到响应
    return createApiError('网络连接失败', 'NETWORK_ERROR', undefined, error)
  }

  // 其他错误
  return createApiError(error.message || '未知错误', 'UNKNOWN_ERROR', undefined, error)
}