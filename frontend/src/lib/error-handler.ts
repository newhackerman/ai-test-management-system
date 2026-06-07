// @ts-nocheck
import toast from 'react-hot-toast'

import type { AppError } from '@/types'
import { ERROR_CODES } from './constants'
import { getErrorMessage } from './utils'

export class AppException extends Error {
  public code: string
  public details?: Record<string, any>
  public timestamp: string

  constructor(message: string, code: string = ERROR_CODES.INTERNAL_ERROR, details?: Record<string, any>) {
    super(message)
    this.name = 'AppException'
    this.code = code
    this.details = details
    this.timestamp = new Date().toISOString()
  }
}

export class ValidationException extends AppException {
  constructor(message: string, details?: Record<string, any>) {
    super(message, ERROR_CODES.VALIDATION_ERROR, details)
    this.name = 'ValidationException'
  }
}

export class NetworkException extends AppException {
  constructor(message: string, details?: Record<string, any>) {
    super(message, ERROR_CODES.NETWORK_ERROR, details)
    this.name = 'NetworkException'
  }
}

export class AuthException extends AppException {
  constructor(message: string, code: string = ERROR_CODES.UNAUTHORIZED, details?: Record<string, any>) {
    super(message, code, details)
    this.name = 'AuthException'
  }
}

export class ErrorHandler {
  private static instance: ErrorHandler
  private errorListeners: Array<(error: AppError) => void> = []
  private retryHandlers: Map<string, () => Promise<void>> = new Map()

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler()
    }
    return ErrorHandler.instance
  }

  addErrorListener(listener: (error: AppError) => void) {
    this.errorListeners.push(listener)
  }

  removeErrorListener(listener: (error: AppError) => void) {
    this.errorListeners = this.errorListeners.filter((item) => item !== listener)
  }

  handle(error: unknown, context?: string): AppError {
    const appError = this.normalizeError(error)
    this.logError(appError, context)
    this.errorListeners.forEach((listener) => {
      try {
        listener(appError)
      } catch (listenerError) {
        console.error('Error in error listener:', listenerError)
      }
    })
    this.showUserError(appError)
    return appError
  }

  private normalizeError(error: unknown): AppError {
    if (error instanceof AppException) {
      return {
        type: this.getTypeFromCode(error.code),
        code: error.code,
        message: error.message,
        details: error.details,
      }
    }

    if (error instanceof Error) {
      if (error.name === 'TypeError' && error.message.toLowerCase().includes('fetch')) {
        return { type: 'network', code: ERROR_CODES.NETWORK_ERROR, message: '网络连接失败，请检查网络连接' }
      }
      if (error.message.toLowerCase().includes('timeout')) {
        return { type: 'network', code: ERROR_CODES.TIMEOUT, message: '请求超时，请稍后重试' }
      }
      return { type: 'unknown', code: ERROR_CODES.INTERNAL_ERROR, message: error.message }
    }

    const anyError = error as any
    if (anyError?.code || anyError?.message) {
      return {
        type: this.getTypeFromCode(anyError.code),
        code: anyError.code || ERROR_CODES.INTERNAL_ERROR,
        message: anyError.message || getErrorMessage(error),
        details: anyError.details,
      }
    }

    return { type: 'unknown', code: ERROR_CODES.INTERNAL_ERROR, message: getErrorMessage(error) }
  }

  private getTypeFromCode(code?: string): AppError['type'] {
    if (code === ERROR_CODES.NETWORK_ERROR || code === ERROR_CODES.TIMEOUT) return 'network'
    if (code === ERROR_CODES.UNAUTHORIZED || code === ERROR_CODES.TOKEN_EXPIRED) return 'auth'
    if (code === ERROR_CODES.VALIDATION_ERROR) return 'validation'
    if (code === ERROR_CODES.INTERNAL_ERROR) return 'server'
    return 'unknown'
  }

  private logError(error: AppError, context?: string) {
    if (import.meta.env.DEV) {
      console.group(`Error: ${error.code || error.type}`)
      console.error('Message:', error.message)
      console.error('Details:', error.details)
      console.error('Context:', context)
      console.groupEnd()
    }
  }

  private showUserError(error: AppError) {
    const message = this.getUserFriendlyMessage(error)
    toast.error(message, {
      duration: error.type === 'auth' ? 3000 : 4000,
      id: `${error.type || 'general'}-error`,
    })

    if (error.type === 'auth') {
      this.handleAuthError()
    }
  }

  private getUserFriendlyMessage(error: AppError): string {
    const messageMap: Record<string, string> = {
      [ERROR_CODES.NETWORK_ERROR]: '网络连接失败，请检查网络连接后重试',
      [ERROR_CODES.TIMEOUT]: '请求超时，请稍后重试',
      [ERROR_CODES.UNAUTHORIZED]: '登录已过期，请重新登录',
      [ERROR_CODES.FORBIDDEN]: '没有权限执行此操作',
      [ERROR_CODES.TOKEN_EXPIRED]: '登录已过期，请重新登录',
      [ERROR_CODES.VALIDATION_ERROR]: '输入信息有误，请检查后重试',
      [ERROR_CODES.RESOURCE_NOT_FOUND]: '请求的资源不存在',
      [ERROR_CODES.RESOURCE_CONFLICT]: '操作冲突，请刷新页面后重试',
      [ERROR_CODES.SERVICE_UNAVAILABLE]: '服务暂时不可用，请稍后重试',
      [ERROR_CODES.INTERNAL_ERROR]: '系统内部错误，请联系管理员',
    }

    return messageMap[error.code || ''] || error.message || '发生未知错误'
  }

  private handleAuthError() {
    localStorage.removeItem('auth-storage')
    localStorage.removeItem('auth-access-token')
    localStorage.removeItem('auth-refresh-token')
    localStorage.removeItem('auth-token-expiry')
    localStorage.removeItem('auth-user')
    window.dispatchEvent(new CustomEvent('auth:logout'))

    setTimeout(() => {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }, 1000)
  }

  addRetryHandler(errorId: string, handler: () => Promise<void>) {
    this.retryHandlers.set(errorId, handler)
  }

  async retry(errorId: string): Promise<boolean> {
    const handler = this.retryHandlers.get(errorId)
    if (!handler) return false

    try {
      await handler()
      this.retryHandlers.delete(errorId)
      toast.success('操作重试成功')
      return true
    } catch (error) {
      this.handle(error, 'retry')
      return false
    }
  }

  clearRetryHandlers() {
    this.retryHandlers.clear()
  }
}

export const errorHandler = ErrorHandler.getInstance()

window.addEventListener('error', (event) => {
  errorHandler.handle(event.error, 'global-error')
})

window.addEventListener('unhandledrejection', (event) => {
  errorHandler.handle(event.reason, 'unhandled-promise-rejection')
})

export const handleError = (error: unknown, context?: string) => errorHandler.handle(error, context)
export const handleApiError = (error: unknown, context?: string) => errorHandler.handle(error, `api-${context}`)
export const handleValidationError = (errors: Record<string, string>) =>
  errorHandler.handle(new ValidationException('表单验证失败', { fields: errors }), 'form-validation')
export const handleNetworkError = (message?: string) =>
  errorHandler.handle(new NetworkException(message || '网络连接失败'), 'network')
export const handleAuthError = (message?: string, code?: string) =>
  errorHandler.handle(new AuthException(message || '认证失败', code), 'authentication')
export const handleReactError = (error: Error, errorInfo: any) =>
  errorHandler.handle(new AppException(error.message, ERROR_CODES.INTERNAL_ERROR, { stack: error.stack, componentStack: errorInfo.componentStack }), 'react-error-boundary')

export default errorHandler
