// @ts-nocheck
// 璇锋眰鎷︽埅鍣ㄧ郴缁?

import { apiClient } from './api-client'
import { authService } from '@/services/auth-service'
import { apiErrorHandler, createApiError } from './api-error-handler'
import { toast } from 'sonner'

/**
 * 璇锋眰鎷︽埅鍣ㄧ被鍨?
 */
export interface RequestInterceptor {
  name: string
  priority: number
  onRequest?: (config: RequestInit & { url: string }) => Promise<RequestInit & { url: string }> | RequestInit & { url: string }
  onResponse?: (response: Response) => Promise<Response> | Response
  onError?: (error: any) => Promise<any> | any
}

/**
 * 鎷︽埅鍣ㄧ鐞嗗櫒
 */
class InterceptorManager {
  private requestInterceptors: RequestInterceptor[] = []
  private responseInterceptors: RequestInterceptor[] = []
  private errorInterceptors: RequestInterceptor[] = []

  /**
   * 娣诲姞鎷︽埅鍣?
   */
  add(interceptor: RequestInterceptor): void {
    if (interceptor.onRequest) {
      this.requestInterceptors.push(interceptor)
      this.requestInterceptors.sort((a, b) => b.priority - a.priority)
    }

    if (interceptor.onResponse) {
      this.responseInterceptors.push(interceptor)
      this.responseInterceptors.sort((a, b) => b.priority - a.priority)
    }

    if (interceptor.onError) {
      this.errorInterceptors.push(interceptor)
      this.errorInterceptors.sort((a, b) => b.priority - a.priority)
    }
  }

  /**
   * 绉婚櫎鎷︽埅鍣?
   */
  remove(name: string): void {
    this.requestInterceptors = this.requestInterceptors.filter(i => i.name !== name)
    this.responseInterceptors = this.responseInterceptors.filter(i => i.name !== name)
    this.errorInterceptors = this.errorInterceptors.filter(i => i.name !== name)
  }

  /**
   * 搴旂敤璇锋眰鎷︽埅鍣?
   */
  async applyRequestInterceptors(config: RequestInit & { url: string }): Promise<RequestInit & { url: string }> {
    let currentConfig = config

    for (const interceptor of this.requestInterceptors) {
      if (interceptor.onRequest) {
        currentConfig = await interceptor.onRequest(currentConfig)
      }
    }

    return currentConfig
  }

  /**
   * 搴旂敤鍝嶅簲鎷︽埅鍣?
   */
  async applyResponseInterceptors(response: Response): Promise<Response> {
    let currentResponse = response

    for (const interceptor of this.responseInterceptors) {
      if (interceptor.onResponse) {
        currentResponse = await interceptor.onResponse(currentResponse)
      }
    }

    return currentResponse
  }

  /**
   * 搴旂敤閿欒鎷︽埅鍣?
   */
  async applyErrorInterceptors(error: any): Promise<any> {
    let currentError = error

    for (const interceptor of this.errorInterceptors) {
      if (interceptor.onError) {
        try {
          currentError = await interceptor.onError(currentError)
        } catch (interceptorError) {
          // 濡傛灉鎷︽埅鍣ㄦ湰韬嚭閿欙紝缁х画浣跨敤鍘熼敊璇?
          console.warn(`错误拦截器 ${interceptor.name} 执行失败:`, interceptorError)
        }
      }
    }

    return currentError
  }
}

// 鍒涘缓鎷︽埅鍣ㄧ鐞嗗櫒瀹炰緥
export const interceptorManager = new InterceptorManager()

/**
 * 璁よ瘉鎷︽埅鍣?
 */
export const authInterceptor: RequestInterceptor = {
  name: 'auth',
  priority: 100,
  
  onRequest: async (config) => {
    // 璺宠繃璁よ瘉鐨勮姹?
    if (config.url.includes('/auth/login') || 
        config.url.includes('/auth/register') || 
        config.url.includes('/auth/refresh')) {
      return config
    }

    // 妫€鏌ュ苟鍒锋柊token
    await authService.checkAndRefreshToken()

    // 娣诲姞璁よ瘉澶?
    const token = authService.getAccessToken()
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`
      }
    }

    return config
  },

  onResponse: async (response) => {
    // 澶勭悊401鏈巿鏉冨搷搴?
    if (response.status === 401) {
      const url = new URL(response.url)
      
      // 濡傛灉涓嶆槸鍒锋柊token鐨勮姹傦紝灏濊瘯鍒锋柊token
      if (!url.pathname.includes('/auth/refresh')) {
        try {
          await authService.refreshToken()
          // 鍙互鍦ㄨ繖閲岄噸鏂板彂璧峰師璇锋眰锛屼絾闇€瑕佹洿澶嶆潅鐨勯€昏緫
        } catch (error) {
          // 鍒锋柊澶辫触锛屼娇鐢ㄦ湰鍦扮櫥鍑洪伩鍏岮PI寰幆
          authService.logoutLocally()
        }
      }
    }

    return response
  }
}

/**
 * 璇锋眰鏃ュ織鎷︽埅鍣?
 */
export const loggingInterceptor: RequestInterceptor = {
  name: 'logging',
  priority: 90,
  
  onRequest: async (config) => {
    if (import.meta.env.DEV) {
      console.group(`API Request: ${config.method || 'GET'} ${config.url}`)
      console.log('Headers:', config.headers)
      if (config.body) {
        console.log('Body:', config.body)
      }
      console.groupEnd()
    }
    return config
  },

  onResponse: async (response) => {
    if (import.meta.env.DEV) {
      const url = new URL(response.url)
      console.group(`API Response: ${response.status} ${url.pathname}`)
      console.log('Status:', response.status, response.statusText)
      console.log('Headers:', Object.fromEntries(response.headers.entries()))
      console.groupEnd()
    }
    return response
  },

  onError: async (error) => {
    if (import.meta.env.DEV) {
      console.group('API Error')
      console.error(error)
      console.groupEnd()
    }
    return error
  }
}

/**
 * 缂撳瓨鎷︽埅鍣?
 */
export const cacheInterceptor: RequestInterceptor = {
  name: 'cache',
  priority: 80,
  
  onRequest: async (config) => {
    // 鍙GET璇锋眰娣诲姞缂撳瓨澶?
    if (config.method === 'GET' || !config.method) {
      config.headers = {
        ...config.headers,
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    }
    return config
  },

  onResponse: async (response) => {
    // 澶勭悊304 Not Modified鍝嶅簲
    if (response.status === 304) {
      // 鍙互浠庢湰鍦扮紦瀛樿繑鍥炴暟鎹?
    }
    return response
  }
}

/**
 * 閲嶈瘯鎷︽埅鍣?
 */
export const retryInterceptor: RequestInterceptor = {
  name: 'retry',
  priority: 70,
  
  onError: async (error) => {
    // 妫€鏌ユ槸鍚﹀簲璇ラ噸璇?
    if (shouldRetry(error)) {
      const retryCount = (error.retryCount || 0) + 1
      const maxRetries = 3

      if (retryCount <= maxRetries) {
        // 璁＄畻寤惰繜鏃堕棿锛堟寚鏁伴€€閬匡級
        const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 10000)
        
        await new Promise(resolve => setTimeout(resolve, delay))
        
        // 鏍囪閲嶈瘯娆℃暟
        error.retryCount = retryCount
        
        // 閲嶆柊鍙戣捣璇锋眰锛堣繖閲岄渶瑕佹洿澶嶆潅鐨勯€昏緫鏉ラ噸鏂板彂璧疯姹傦級
        console.log(`重试请求 (${retryCount}/${maxRetries})`)
      }
    }
    
    return error
  }
}

/**
 * 鍒ゆ柇鏄惁搴旇閲嶈瘯
 */
function shouldRetry(error: any): boolean {
  // 缃戠粶閿欒
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    return true
  }

  // 鏈嶅姟鍣ㄩ敊璇?
  if (error.status >= 500) {
    return true
  }

  // 瓒呮椂閿欒
  if (error.name === 'AbortError') {
    return true
  }

  return false
}

/**
 * 璇锋眰ID鎷︽埅鍣?
 */
export const requestIdInterceptor: RequestInterceptor = {
  name: 'requestId',
  priority: 95,
  
  onRequest: async (config) => {
    // 涓烘瘡涓姹傛坊鍔犲敮涓€ID
    const requestId = generateRequestId()
    config.headers = {
      ...config.headers,
      'X-Request-ID': requestId
    }
    return config
  }
}

/**
 * 鐢熸垚璇锋眰ID
 */
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 鐢ㄦ埛浠ｇ悊鎷︽埅鍣?
 */
export const userAgentInterceptor: RequestInterceptor = {
  name: 'userAgent',
  priority: 85,
  
  onRequest: async (config) => {
    config.headers = {
      ...config.headers,
      'X-Client-Version': import.meta.env.VITE_APP_VERSION || '1.0.0',
      'X-Client-Platform': navigator.platform,
      'X-Client-Language': navigator.language
    }
    return config
  }
}

/**
 * 閿欒澶勭悊鎷︽埅鍣?
 */
export const errorHandlingInterceptor: RequestInterceptor = {
  name: 'errorHandling',
  priority: 60,
  
  onError: async (error) => {
    // 缁熶竴閿欒澶勭悊
    const apiError = createApiError(
      error.message || '请求失败',
      error.code,
      error.status,
      error
    )

    // 鏍规嵁閿欒绫诲瀷鏄剧ず涓嶅悓鐨勬彁绀?
    if (error.status === 401) {
      toast.error('登录已过期，请重新登录')
    } else if (error.status === 403) {
      toast.error('权限不足，无法访问')
    } else if (error.status === 404) {
      toast.error('请求的资源不存在')
    } else if (error.status >= 500) {
      toast.error('服务器错误，请稍后重试')
    } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
      toast.error('网络连接失败，请检查网络')
    }

    return apiError
  }
}

/**
 * 鎬ц兘鐩戞帶鎷︽埅鍣?
 */
export const performanceInterceptor: RequestInterceptor = {
  name: 'performance',
  priority: 50,
  
  onRequest: async (config) => {
    // 璁板綍璇锋眰寮€濮嬫椂闂?
    (config as any).startTime = performance.now()
    return config
  },

  onResponse: async (response) => {
    // 璁＄畻璇锋眰鑰楁椂
    const startTime = (response as any).startTime
    if (startTime) {
      const duration = performance.now() - startTime
      
      // 璁板綍鎬ц兘鎸囨爣
      if (import.meta.env.DEV) {
        console.log(`Request duration: ${duration.toFixed(2)}ms`)
      }

      // 鍙互鍙戦€佸埌鎬ц兘鐩戞帶鏈嶅姟
      recordPerformanceMetric(response.url, duration)
    }
    
    return response
  }
}

/**
 * 璁板綍鎬ц兘鎸囨爣
 */
function recordPerformanceMetric(url: string, duration: number): void {
  // 杩欓噷鍙互闆嗘垚鎬ц兘鐩戞帶鏈嶅姟锛屽 Sentry銆丏ataDog 绛?
  if (duration > 5000) { // 瓒呰繃5绉掔殑璇锋眰
    console.warn(`慢请求警告：${url} 耗时 ${duration.toFixed(2)}ms`)
  }
}

/**
 * 鍒濆鍖栨墍鏈夋嫤鎴櫒
 */
export function initializeInterceptors(): void {
  // 鎸変紭鍏堢骇椤哄簭娣诲姞鎷︽埅鍣?
  interceptorManager.add(authInterceptor)
  interceptorManager.add(requestIdInterceptor)
  interceptorManager.add(loggingInterceptor)
  interceptorManager.add(userAgentInterceptor)
  interceptorManager.add(cacheInterceptor)
  interceptorManager.add(retryInterceptor)
  interceptorManager.add(errorHandlingInterceptor)
  interceptorManager.add(performanceInterceptor)

  // 灏嗘嫤鎴櫒闆嗘垚鍒癆PI瀹㈡埛绔?
  apiClient.addRequestInterceptor(async (config) => {
    const configWithUrl = { ...config, url: config.url || '' }
    return await interceptorManager.applyRequestInterceptors(configWithUrl)
  })

  apiClient.addResponseInterceptor(async (response) => {
    return await interceptorManager.applyResponseInterceptors(response)
  })
}

// 鑷姩鍒濆鍖栨嫤鎴櫒
initializeInterceptors()

export default interceptorManager
