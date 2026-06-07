// @ts-nocheck
// API缂撳瓨绯荤粺 - 瀹屾暣瀹炵幇

import { QueryClient } from '@tanstack/react-query'

export interface CacheConfig {
  defaultStaleTime: number
  defaultGcTime: number
  maxRetries: number
  retryDelay: (attemptIndex: number) => number
  networkMode: 'online' | 'always' | 'offlineFirst'
}

export interface RequestOptimizationConfig {
  enableDeduplication: boolean
  enableBatching: boolean
  batchInterval: number
  maxBatchSize: number
  enableCompression: boolean
  enableEtag: boolean
}

/**
 * 璇锋眰浼樺寲鍣ㄧ被
 * 鎻愪緵璇锋眰鍘婚噸銆佹壒澶勭悊銆佸帇缂╃瓑浼樺寲鍔熻兘
 */
export class RequestOptimizer {
  private config: RequestOptimizationConfig
  private pendingRequests = new Map<string, Promise<any>>()
  private batchQueue: Array<{
    key: string
    request: () => Promise<any>
    resolve: (value: any) => void
    reject: (error: any) => void
  }> = []
  private batchTimer: NodeJS.Timeout | null = null

  constructor(config: Partial<RequestOptimizationConfig> = {}) {
    this.config = {
      enableDeduplication: true,
      enableBatching: false,
      batchInterval: 50,
      maxBatchSize: 10,
      enableCompression: true,
      enableEtag: true,
      ...config
    }
  }

  /**
   * 浼樺寲璇锋眰
   */
  async optimize<T>(
    key: string,
    requestFn: () => Promise<T>,
    options: {
      enableDeduplication?: boolean
      enableBatching?: boolean
      priority?: 'low' | 'normal' | 'high'
    } = {}
  ): Promise<T> {
    const {
      enableDeduplication = this.config.enableDeduplication,
      enableBatching = this.config.enableBatching,
      priority = 'normal'
    } = options

    // 璇锋眰鍘婚噸
    if (enableDeduplication && this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key)!
    }

    // 鎵瑰鐞?
    if (enableBatching) {
      return this.addToBatch(key, requestFn)
    }

    // 鏅€氳姹?
    const promise = this.executeRequest(key, requestFn)
    
    if (enableDeduplication) {
      this.pendingRequests.set(key, promise)
      promise.finally(() => {
        this.pendingRequests.delete(key)
      })
    }

    return promise
  }

  /**
   * 甯︾紦瀛樼殑浼樺寲璇锋眰
   */
  async optimizeWithCache<T>(
    key: string,
    requestFn: () => Promise<{ data: T; headers: Record<string, string> }>,
    options: {
      params?: any
      ttl?: number
      skipCache?: boolean
      skipDeduplication?: boolean
    } = {}
  ): Promise<T> {
    const cacheKey = this.generateCacheKey(key, options.params)
    
    // 妫€鏌ョ紦瀛?
    if (!options.skipCache) {
      const cached = this.getFromCache<T>(cacheKey)
      if (cached) {
        return cached
      }
    }

    // 鎵ц浼樺寲璇锋眰
    const result = await this.optimize(
      cacheKey,
      requestFn,
      {
        enableDeduplication: !options.skipDeduplication,
        enableBatching: false
      }
    )

    // 缂撳瓨缁撴灉
    if (!options.skipCache && result.data) {
      this.setCache(cacheKey, result.data, options.ttl)
    }

    return result.data
  }

  /**
   * 鐢熸垚缂撳瓨閿?
   */
  private generateCacheKey(key: string, params?: any): string {
    if (!params) return key
    
    const paramStr = JSON.stringify(params, Object.keys(params).sort())
    return `${key}:${btoa(paramStr)}`
  }

  /**
   * 浠庣紦瀛樿幏鍙栨暟鎹?
   */
  private getFromCache<T>(key: string): T | null {
    const cached = localStorage.getItem(`cache:${key}`)
    if (!cached) return null

    try {
      const { data, expiry } = JSON.parse(cached)
      if (Date.now() > expiry) {
        localStorage.removeItem(`cache:${key}`)
        return null
      }
      return data
    } catch {
      localStorage.removeItem(`cache:${key}`)
      return null
    }
  }

  /**
   * 璁剧疆缂撳瓨
   */
  private setCache<T>(key: string, data: T, ttl: number = 5 * 60 * 1000): void {
    const expiry = Date.now() + ttl
    const cacheData = { data, expiry }
    
    try {
      localStorage.setItem(`cache:${key}`, JSON.stringify(cacheData))
    } catch (error) {
      // 缂撳瓨绌洪棿涓嶈冻锛屾竻鐞嗚繃鏈熺紦瀛?
      this.cleanExpiredCache()
    }
  }

  /**
   * 娓呯悊杩囨湡缂撳瓨
   */
  private cleanExpiredCache(): void {
    const keys = Object.keys(localStorage)
    const now = Date.now()

    keys.forEach(key => {
      if (key.startsWith('cache:')) {
        try {
          const cached = JSON.parse(localStorage.getItem(key) || '{}')
          if (cached.expiry && now > cached.expiry) {
            localStorage.removeItem(key)
          }
        } catch {
          localStorage.removeItem(key)
        }
      }
    })
  }

  /**
   * 鎵ц璇锋眰
   */
  private async executeRequest<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    try {
      const startTime = performance.now()
      const result = await requestFn()
      const endTime = performance.now()
      
      // 璁板綍鎬ц兘鎸囨爣
      this.recordMetrics(key, endTime - startTime, 'success')
      
      return result
    } catch (error) {
      this.recordMetrics(key, 0, 'error')
      throw error
    }
  }

  /**
   * 娣诲姞鍒版壒澶勭悊闃熷垪
   */
  private addToBatch<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.batchQueue.push({
        key,
        request: requestFn,
        resolve,
        reject
      })

      if (this.batchQueue.length >= this.config.maxBatchSize) {
        this.processBatch()
      } else if (!this.batchTimer) {
        this.batchTimer = setTimeout(() => {
          this.processBatch()
        }, this.config.batchInterval)
      }
    })
  }

  /**
   * 澶勭悊鎵瑰鐞嗛槦鍒?
   */
  private async processBatch(): void {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer)
      this.batchTimer = null
    }

    const batch = this.batchQueue.splice(0, this.config.maxBatchSize)
    if (batch.length === 0) return

    // 骞惰鎵ц鎵瑰鐞嗚姹?
    const promises = batch.map(async (item) => {
      try {
        const result = await item.request()
        item.resolve(result)
      } catch (error) {
        item.reject(error)
      }
    })

    await Promise.allSettled(promises)
  }

  /**
   * 璁板綍鎬ц兘鎸囨爣
   */
  private recordMetrics(key: string, duration: number, status: 'success' | 'error'): void {
    // 杩欓噷鍙互闆嗘垚鎬ц兘鐩戞帶鏈嶅姟
    if (import.meta.env.DEV) {
      console.log(`[RequestOptimizer] ${key}: ${duration.toFixed(2)}ms (${status})`)
    }
  }

  /**
   * 娓呯悊璧勬簮
   */
  cleanup(): void {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer)
      this.batchTimer = null
    }
    this.pendingRequests.clear()
    this.batchQueue = []
  }
}

/**
 * 缂撳瓨绛栫暐绠＄悊鍣?
 */
export class CacheStrategyManager {
  private strategies = new Map<string, CacheStrategy>()

  /**
   * 娉ㄥ唽缂撳瓨绛栫暐
   */
  registerStrategy(name: string, strategy: CacheStrategy): void {
    this.strategies.set(name, strategy)
  }

  /**
   * 鑾峰彇缂撳瓨绛栫暐
   */
  getStrategy(name: string): CacheStrategy | undefined {
    return this.strategies.get(name)
  }

  /**
   * 搴旂敤缂撳瓨绛栫暐
   */
  applyStrategy(name: string, queryKey: string[], data: any): CacheOptions {
    const strategy = this.strategies.get(name)
    if (!strategy) {
      throw new Error(`缓存策略 "${name}" 不存在`)
    }

    return strategy.getCacheOptions(queryKey, data)
  }
}

/**
 * 缂撳瓨绛栫暐鎺ュ彛
 */
export interface CacheStrategy {
  getCacheOptions(queryKey: string[], data: any): CacheOptions
}

/**
 * 缂撳瓨閫夐」
 */
export interface CacheOptions {
  staleTime: number
  gcTime: number
  refetchOnMount: boolean
  refetchOnWindowFocus: boolean
  refetchOnReconnect: boolean
  refetchInterval: number | false
}

/**
 * 榛樿缂撳瓨绛栫暐
 */
export class DefaultCacheStrategy implements CacheStrategy {
  getCacheOptions(queryKey: string[], data: any): CacheOptions {
    return {
      staleTime: 5 * 60 * 1000, // 5鍒嗛挓
      gcTime: 10 * 60 * 1000, // 10鍒嗛挓
      refetchOnMount: true,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchInterval: false
    }
  }
}

/**
 * 闈欐€佹暟鎹紦瀛樼瓥鐣?
 */
export class StaticDataCacheStrategy implements CacheStrategy {
  getCacheOptions(queryKey: string[], data: any): CacheOptions {
    return {
      staleTime: 60 * 60 * 1000, // 1灏忔椂
      gcTime: 24 * 60 * 60 * 1000, // 24灏忔椂
      refetchOnMount: false,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      refetchInterval: false
    }
  }
}

/**
 * 瀹炴椂鏁版嵁缂撳瓨绛栫暐
 */
export class RealtimeDataCacheStrategy implements CacheStrategy {
  getCacheOptions(queryKey: string[], data: any): CacheOptions {
    return {
      staleTime: 0, // 绔嬪嵆杩囨湡
      gcTime: 1 * 60 * 1000, // 1鍒嗛挓
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      refetchInterval: 30 * 1000 // 30绉?
    }
  }
}

/**
 * 鐢ㄦ埛鏁版嵁缂撳瓨绛栫暐
 */
export class UserDataCacheStrategy implements CacheStrategy {
  getCacheOptions(queryKey: string[], data: any): CacheOptions {
    return {
      staleTime: 10 * 60 * 1000, // 10鍒嗛挓
      gcTime: 30 * 60 * 1000, // 30鍒嗛挓
      refetchOnMount: false,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchInterval: false
    }
  }
}

/**
 * 缂撳瓨澶辨晥绠＄悊鍣?
 */
export class CacheInvalidationManager {
  private queryClient: QueryClient

  constructor(queryClient: QueryClient) {
    this.queryClient = queryClient
  }

  /**
   * 鎸夋爣绛惧け鏁堢紦瀛?
   */
  invalidateByTags(tags: string[]): void {
    tags.forEach(tag => {
      this.queryClient.invalidateQueries({
        predicate: (query) => {
          const queryTags = (query.meta as any)?.tags || []
          return queryTags.includes(tag)
        }
      })
    })
  }

  /**
   * 鎸夋ā寮忓け鏁堢紦瀛?
   */
  invalidateByPattern(pattern: RegExp): void {
    this.queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey.join('.')
        return pattern.test(queryKey)
      }
    })
  }

  /**
   * 澶辨晥鐩稿叧缂撳瓨
   */
  invalidateRelated(resource: string, action: 'create' | 'update' | 'delete'): void {
    const patterns = this.getInvalidationPatterns(resource, action)
    
    patterns.forEach(pattern => {
      if (typeof pattern === 'string') {
        this.queryClient.invalidateQueries({ queryKey: [pattern] })
      } else {
        this.invalidateByPattern(pattern)
      }
    })
  }

  /**
   * 鑾峰彇澶辨晥妯″紡
   */
  private getInvalidationPatterns(resource: string, action: string): Array<string | RegExp> {
    const patterns: Array<string | RegExp> = []

    switch (resource) {
      case 'project':
        patterns.push('projects', /^project\./, /^test-cases\..*project/)
        if (action === 'delete') {
          patterns.push(/^requirements\..*project/, /^tasks\..*project/)
        }
        break
      
      case 'test-case':
        patterns.push('test-cases', /^test-case\./, /^test-results\..*test-case/)
        break
      
      case 'user':
        patterns.push('users', /^user\./, /^projects\..*user/)
        break
      
      default:
        patterns.push(resource)
    }

    return patterns
  }
}

/**
 * 棰勫姞杞界鐞嗗櫒
 */
export class PreloadManager {
  private queryClient: QueryClient
  private preloadQueue: Array<{
    queryKey: string[]
    queryFn: () => Promise<any>
    priority: number
  }> = []

  constructor(queryClient: QueryClient) {
    this.queryClient = queryClient
  }

  /**
   * 娣诲姞棰勫姞杞戒换鍔?
   */
  addPreloadTask(
    queryKey: string[],
    queryFn: () => Promise<any>,
    priority: number = 0
  ): void {
    this.preloadQueue.push({ queryKey, queryFn, priority })
    this.preloadQueue.sort((a, b) => b.priority - a.priority)
  }

  /**
   * 鎵ц棰勫姞杞?
   */
  async executePreload(maxConcurrent: number = 3): Promise<void> {
    const executing: Promise<any>[] = []

    while (this.preloadQueue.length > 0 || executing.length > 0) {
      // 鍚姩鏂扮殑棰勫姞杞戒换鍔?
      while (executing.length < maxConcurrent && this.preloadQueue.length > 0) {
        const task = this.preloadQueue.shift()!
        const promise = this.queryClient.prefetchQuery({
          queryKey: task.queryKey,
          queryFn: task.queryFn,
          staleTime: 5 * 60 * 1000
        }).catch(error => {
          console.warn('棰勫姞杞藉け璐?', task.queryKey, error)
        })

        executing.push(promise)
      }

      // 绛夊緟鑷冲皯涓€涓换鍔″畬鎴?
      if (executing.length > 0) {
        await Promise.race(executing)
        // 绉婚櫎宸插畬鎴愮殑浠诲姟
        for (let i = executing.length - 1; i >= 0; i--) {
          const promise = executing[i]
          if (await Promise.race([promise, Promise.resolve('pending')]) !== 'pending') {
            executing.splice(i, 1)
          }
        }
      }
    }
  }

  /**
   * 棰勫姞杞藉叧閿矾寰?
   */
  async preloadCriticalPath(routes: string[]): Promise<void> {
    const criticalQueries = this.getCriticalQueries(routes)
    
    for (const query of criticalQueries) {
      this.addPreloadTask(query.queryKey, query.queryFn, query.priority)
    }

    await this.executePreload()
  }

  /**
   * 鑾峰彇鍏抽敭鏌ヨ
   */
  private getCriticalQueries(routes: string[]): Array<{
    queryKey: string[]
    queryFn: () => Promise<any>
    priority: number
  }> {
    const queries: Array<{
      queryKey: string[]
      queryFn: () => Promise<any>
      priority: number
    }> = []

    routes.forEach(route => {
      switch (route) {
        case '/':
        case '/dashboard':
          queries.push({
            queryKey: ['dashboard'],
            queryFn: () => fetch('/api/dashboard').then(r => r.json()),
            priority: 10
          })
          break
        
        case '/projects':
          queries.push({
            queryKey: ['projects'],
            queryFn: () => fetch('/api/projects').then(r => r.json()),
            priority: 8
          })
          break
        
        case '/test-cases':
          queries.push({
            queryKey: ['test-cases'],
            queryFn: () => fetch('/api/test-cases').then(r => r.json()),
            priority: 7
          })
          break
      }
    })

    return queries
  }
}

// 鍒涘缓鍏ㄥ眬瀹炰緥
export const requestOptimizer = new RequestOptimizer()
export const cacheStrategyManager = new CacheStrategyManager()

// 娉ㄥ唽榛樿缂撳瓨绛栫暐
cacheStrategyManager.registerStrategy('default', new DefaultCacheStrategy())
cacheStrategyManager.registerStrategy('static', new StaticDataCacheStrategy())
cacheStrategyManager.registerStrategy('realtime', new RealtimeDataCacheStrategy())
cacheStrategyManager.registerStrategy('user', new UserDataCacheStrategy())

/**
 * 缂撳瓨宸ュ叿鍑芥暟
 */
export const cacheUtils = {
  /**
   * 鐢熸垚鏌ヨ閿?
   */
  generateQueryKey: (resource: string, params?: Record<string, any>): string[] => {
    const key = [resource]
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) {
          key.push(`${k}:${v}`)
        }
      })
    }
    return key
  },

  /**
   * 妫€鏌ョ紦瀛樻槸鍚﹀瓨鍦?
   */
  isCached: (queryClient: QueryClient, queryKey: string[]): boolean => {
    const query = queryClient.getQueryCache().find({ queryKey })
    return !!query && query.state.data !== undefined
  },

  /**
   * 鑾峰彇缂撳瓨鏁版嵁
   */
  getCachedData: <T>(queryClient: QueryClient, queryKey: string[]): T | undefined => {
    return queryClient.getQueryData<T>(queryKey)
  },

  /**
   * 璁剧疆缂撳瓨鏁版嵁
   */
  setCachedData: <T>(queryClient: QueryClient, queryKey: string[], data: T): void => {
    queryClient.setQueryData(queryKey, data)
  },

  /**
   * 绉婚櫎缂撳瓨
   */
  removeCache: (queryClient: QueryClient, queryKey: string[]): void => {
    queryClient.removeQueries({ queryKey })
  }
}
