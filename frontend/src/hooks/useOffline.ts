import { useState, useEffect, useCallback } from 'react'
import offlineStorage, { SyncStatus, OfflineOperation } from '@/lib/offline-storage'

/**
 * 离线功能 Hook
 * 提供离线状态管理、数据缓存和操作队列功能
 */
export const useOffline = () => {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isOnline: navigator.onLine,
    lastSync: 0,
    pendingOperations: 0,
    syncInProgress: false
  })

  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    // 订阅同步状态变化
    const unsubscribe = offlineStorage.onSyncStatusChange((status) => {
      setSyncStatus(status)
      setIsInitialized(true)
    })

    return unsubscribe
  }, [])

  /**
   * 缓存数据
   */
  const cacheData = useCallback(async <T>(key: string, data: T, expiry?: number) => {
    try {
      await offlineStorage.cacheData(key, data, expiry)
      return true
    } catch (error) {
      console.error('Failed to cache data:', error)
      return false
    }
  }, [])

  /**
   * 获取缓存数据
   */
  const getCachedData = useCallback(async <T>(key: string): Promise<T | null> => {
    try {
      return await offlineStorage.getCachedData<T>(key)
    } catch (error) {
      console.error('Failed to get cached data:', error)
      return null
    }
  }, [])

  /**
   * 添加离线操作
   */
  const addOfflineOperation = useCallback(async (
    type: 'CREATE' | 'UPDATE' | 'DELETE',
    resource: string,
    data: any,
    maxRetries: number = 3
  ) => {
    try {
      const id = await offlineStorage.addOfflineOperation({
        type,
        resource,
        data,
        maxRetries
      })
      return id
    } catch (error) {
      console.error('Failed to add offline operation:', error)
      return null
    }
  }, [])

  /**
   * 强制同步
   */
  const forceSync = useCallback(async () => {
    try {
      await offlineStorage.forceSync()
      return true
    } catch (error) {
      console.error('Failed to force sync:', error)
      return false
    }
  }, [])

  /**
   * 清空离线数据
   */
  const clearOfflineData = useCallback(async () => {
    try {
      await offlineStorage.clearAllOfflineData()
      return true
    } catch (error) {
      console.error('Failed to clear offline data:', error)
      return false
    }
  }, [])

  /**
   * 获取缓存统计
   */
  const getCacheStats = useCallback(async () => {
    try {
      return await offlineStorage.getCacheStats()
    } catch (error) {
      console.error('Failed to get cache stats:', error)
      return null
    }
  }, [])

  return {
    // 状态
    syncStatus,
    isInitialized,
    isOnline: syncStatus.isOnline,
    hasPendingOperations: syncStatus.pendingOperations > 0,
    isSyncing: syncStatus.syncInProgress,

    // 方法
    cacheData,
    getCachedData,
    addOfflineOperation,
    forceSync,
    clearOfflineData,
    getCacheStats
  }
}

/**
 * 离线优先的数据获取 Hook
 */
export const useOfflineFirst = <T>(
  key: string,
  fetcher: () => Promise<T>,
  options: {
    cacheExpiry?: number
    fallbackToCache?: boolean
    syncInBackground?: boolean
  } = {}
) => {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [fromCache, setFromCache] = useState(false)

  const { isOnline, cacheData, getCachedData } = useOffline()

  const {
    cacheExpiry,
    fallbackToCache = true,
    syncInBackground = true
  } = options

  const fetchData = useCallback(async (useCache = true) => {
    try {
      setLoading(true)
      setError(null)

      // 首先尝试从缓存获取数据
      if (useCache) {
        const cachedData = await getCachedData<T>(key)
        if (cachedData) {
          setData(cachedData)
          setFromCache(true)
          setLoading(false)

          // 如果在线且启用后台同步，则在后台更新数据
          if (isOnline && syncInBackground) {
            try {
              const freshData = await fetcher()
              await cacheData(key, freshData, cacheExpiry)
              setData(freshData)
              setFromCache(false)
            } catch (error) {
              // 后台同步失败不影响用户体验
              console.warn('Background sync failed:', error)
            }
          }
          return
        }
      }

      // 如果在线，尝试获取新数据
      if (isOnline) {
        const freshData = await fetcher()
        await cacheData(key, freshData, cacheExpiry)
        setData(freshData)
        setFromCache(false)
      } else if (fallbackToCache) {
        // 离线时回退到缓存
        const cachedData = await getCachedData<T>(key)
        if (cachedData) {
          setData(cachedData)
          setFromCache(true)
        } else {
          throw new Error('No cached data available offline')
        }
      } else {
        throw new Error('Network unavailable and cache fallback disabled')
      }
    } catch (err) {
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }, [key, fetcher, isOnline, cacheData, getCachedData, cacheExpiry, fallbackToCache, syncInBackground])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const refetch = useCallback(() => {
    return fetchData(false) // 强制从网络获取
  }, [fetchData])

  return {
    data,
    loading,
    error,
    fromCache,
    refetch
  }
}

/**
 * 离线操作 Hook
 */
export const useOfflineOperation = () => {
  const { isOnline, addOfflineOperation } = useOffline()

  /**
   * 执行可离线的操作
   */
  const executeOperation = useCallback(async <T>(
    operation: () => Promise<T>,
    offlineConfig: {
      type: 'CREATE' | 'UPDATE' | 'DELETE'
      resource: string
      data: any
      maxRetries?: number
    }
  ): Promise<{ success: boolean; data?: T; queued?: boolean }> => {
    if (isOnline) {
      try {
        const result = await operation()
        return { success: true, data: result }
      } catch (error) {
        // 在线操作失败，添加到离线队列
        const operationId = await addOfflineOperation(
          offlineConfig.type,
          offlineConfig.resource,
          offlineConfig.data,
          offlineConfig.maxRetries
        )
        
        if (operationId) {
          return { success: true, queued: true }
        } else {
          throw error
        }
      }
    } else {
      // 离线时直接添加到队列
      const operationId = await addOfflineOperation(
        offlineConfig.type,
        offlineConfig.resource,
        offlineConfig.data,
        offlineConfig.maxRetries
      )
      
      if (operationId) {
        return { success: true, queued: true }
      } else {
        throw new Error('Failed to queue offline operation')
      }
    }
  }, [isOnline, addOfflineOperation])

  return {
    executeOperation
  }
}

/**
 * 网络状态 Hook
 */
export const useNetworkStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [connectionType, setConnectionType] = useState<string>('unknown')

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // 检测连接类型（如果支持）
    if ('connection' in navigator) {
      const connection = (navigator as any).connection
      setConnectionType(connection.effectiveType || 'unknown')

      const handleConnectionChange = () => {
        setConnectionType(connection.effectiveType || 'unknown')
      }

      connection.addEventListener('change', handleConnectionChange)

      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
        connection.removeEventListener('change', handleConnectionChange)
      }
    }

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return {
    isOnline,
    connectionType,
    isSlowConnection: connectionType === 'slow-2g' || connectionType === '2g'
  }
}

export default useOffline