/**
 * 离线存储管理器
 * 提供离线数据缓存、操作队列和数据同步功能
 */

export interface OfflineOperation {
  id: string
  type: 'CREATE' | 'UPDATE' | 'DELETE'
  resource: string
  data: any
  timestamp: number
  retryCount: number
  maxRetries: number
}

export interface CacheItem<T = any> {
  data: T
  timestamp: number
  expiry?: number
  version: string
}

export interface SyncStatus {
  isOnline: boolean
  lastSync: number
  pendingOperations: number
  syncInProgress: boolean
}

class OfflineStorageManager {
  private dbName = 'RequirementManagementOfflineDB'
  private dbVersion = 1
  private db: IDBDatabase | null = null
  private syncCallbacks: Set<(status: SyncStatus) => void> = new Set()
  private isOnline = navigator.onLine
  private syncInProgress = false

  constructor() {
    this.initDB()
    this.setupOnlineStatusListeners()
  }

  /**
   * 初始化 IndexedDB
   */
  private async initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // 缓存数据存储
        if (!db.objectStoreNames.contains('cache')) {
          const cacheStore = db.createObjectStore('cache', { keyPath: 'key' })
          cacheStore.createIndex('timestamp', 'timestamp')
          cacheStore.createIndex('expiry', 'expiry')
        }

        // 离线操作队列
        if (!db.objectStoreNames.contains('operations')) {
          const operationsStore = db.createObjectStore('operations', { keyPath: 'id' })
          operationsStore.createIndex('timestamp', 'timestamp')
          operationsStore.createIndex('type', 'type')
          operationsStore.createIndex('resource', 'resource')
        }

        // 同步状态
        if (!db.objectStoreNames.contains('sync_status')) {
          db.createObjectStore('sync_status', { keyPath: 'key' })
        }
      }
    })
  }

  /**
   * 设置在线状态监听器
   */
  private setupOnlineStatusListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true
      this.notifySyncStatus()
      this.processPendingOperations()
    })

    window.addEventListener('offline', () => {
      this.isOnline = false
      this.notifySyncStatus()
    })
  }

  /**
   * 缓存数据
   */
  async cacheData<T>(key: string, data: T, expiry?: number): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache'], 'readwrite')
    const store = transaction.objectStore('cache')

    const cacheItem: CacheItem<T> = {
      data,
      timestamp: Date.now(),
      expiry,
      version: '1.0'
    }

    await new Promise<void>((resolve, reject) => {
      const request = store.put({ key, ...cacheItem })
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 获取缓存数据
   */
  async getCachedData<T>(key: string): Promise<T | null> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache'], 'readonly')
    const store = transaction.objectStore('cache')

    return new Promise<T | null>((resolve, reject) => {
      const request = store.get(key)
      request.onsuccess = () => {
        const result = request.result
        if (!result) {
          resolve(null)
          return
        }

        // 检查是否过期
        if (result.expiry && Date.now() > result.expiry) {
          this.removeCachedData(key)
          resolve(null)
          return
        }

        resolve(result.data)
      }
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 删除缓存数据
   */
  async removeCachedData(key: string): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache'], 'readwrite')
    const store = transaction.objectStore('cache')

    await new Promise<void>((resolve, reject) => {
      const request = store.delete(key)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 清理过期缓存
   */
  async cleanExpiredCache(): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache'], 'readwrite')
    const store = transaction.objectStore('cache')
    const index = store.index('expiry')

    const now = Date.now()
    const range = IDBKeyRange.upperBound(now)

    await new Promise<void>((resolve, reject) => {
      const request = index.openCursor(range)
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result
        if (cursor) {
          cursor.delete()
          cursor.continue()
        } else {
          resolve()
        }
      }
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 添加离线操作到队列
   */
  async addOfflineOperation(operation: Omit<OfflineOperation, 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
    if (!this.db) await this.initDB()

    const id = `${operation.type}_${operation.resource}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const fullOperation: OfflineOperation = {
      id,
      timestamp: Date.now(),
      retryCount: 0,
      ...operation
    }

    const transaction = this.db!.transaction(['operations'], 'readwrite')
    const store = transaction.objectStore('operations')

    await new Promise<void>((resolve, reject) => {
      const request = store.add(fullOperation)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })

    this.notifySyncStatus()
    return id
  }

  /**
   * 获取待处理的离线操作
   */
  async getPendingOperations(): Promise<OfflineOperation[]> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['operations'], 'readonly')
    const store = transaction.objectStore('operations')

    return new Promise<OfflineOperation[]>((resolve, reject) => {
      const request = store.getAll()
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 删除离线操作
   */
  async removeOfflineOperation(id: string): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['operations'], 'readwrite')
    const store = transaction.objectStore('operations')

    await new Promise<void>((resolve, reject) => {
      const request = store.delete(id)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })

    this.notifySyncStatus()
  }

  /**
   * 更新离线操作重试次数
   */
  async updateOperationRetryCount(id: string, retryCount: number): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['operations'], 'readwrite')
    const store = transaction.objectStore('operations')

    const operation = await new Promise<OfflineOperation>((resolve, reject) => {
      const request = store.get(id)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })

    if (operation) {
      operation.retryCount = retryCount
      await new Promise<void>((resolve, reject) => {
        const request = store.put(operation)
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    }
  }

  /**
   * 处理待处理的离线操作
   */
  async processPendingOperations(): Promise<void> {
    if (!this.isOnline || this.syncInProgress) return

    this.syncInProgress = true
    this.notifySyncStatus()

    try {
      const operations = await this.getPendingOperations()
      
      for (const operation of operations) {
        try {
          await this.executeOperation(operation)
          await this.removeOfflineOperation(operation.id)
        } catch (error) {
          console.error('Failed to execute operation:', operation, error)
          
          // 增加重试次数
          const newRetryCount = operation.retryCount + 1
          
          if (newRetryCount >= operation.maxRetries) {
            // 达到最大重试次数，删除操作
            await this.removeOfflineOperation(operation.id)
            console.error('Operation failed after max retries:', operation)
          } else {
            // 更新重试次数
            await this.updateOperationRetryCount(operation.id, newRetryCount)
          }
        }
      }
    } finally {
      this.syncInProgress = false
      await this.updateSyncStatus()
      this.notifySyncStatus()
    }
  }

  /**
   * 执行离线操作
   */
  private async executeOperation(operation: OfflineOperation): Promise<void> {
    const { type, resource, data } = operation

    // 这里需要根据实际的API接口来实现
    const baseUrl = '/api/v1'
    let url = `${baseUrl}/${resource}`
    let method = 'GET'
    let body: string | undefined

    switch (type) {
      case 'CREATE':
        method = 'POST'
        body = JSON.stringify(data)
        break
      case 'UPDATE':
        method = 'PUT'
        url = `${url}/${data.id}`
        body = JSON.stringify(data)
        break
      case 'DELETE':
        method = 'DELETE'
        url = `${url}/${data.id}`
        break
    }

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        // 添加认证头等
      },
      body
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 更新同步状态
   */
  private async updateSyncStatus(): Promise<void> {
    if (!this.db) await this.initDB()

    const pendingOperations = await this.getPendingOperations()
    const syncStatus = {
      key: 'main',
      lastSync: Date.now(),
      pendingOperations: pendingOperations.length
    }

    const transaction = this.db!.transaction(['sync_status'], 'readwrite')
    const store = transaction.objectStore('sync_status')

    await new Promise<void>((resolve, reject) => {
      const request = store.put(syncStatus)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 获取同步状态
   */
  async getSyncStatus(): Promise<SyncStatus> {
    const pendingOperations = await this.getPendingOperations()
    
    let lastSync = 0
    if (this.db) {
      try {
        const transaction = this.db.transaction(['sync_status'], 'readonly')
        const store = transaction.objectStore('sync_status')
        
        const result = await new Promise<any>((resolve, reject) => {
          const request = store.get('main')
          request.onsuccess = () => resolve(request.result)
          request.onerror = () => reject(request.error)
        })
        
        if (result) {
          lastSync = result.lastSync
        }
      } catch (error) {
        console.error('Failed to get sync status:', error)
      }
    }

    return {
      isOnline: this.isOnline,
      lastSync,
      pendingOperations: pendingOperations.length,
      syncInProgress: this.syncInProgress
    }
  }

  /**
   * 订阅同步状态变化
   */
  onSyncStatusChange(callback: (status: SyncStatus) => void): () => void {
    this.syncCallbacks.add(callback)
    
    // 立即调用一次
    this.getSyncStatus().then(callback)
    
    // 返回取消订阅函数
    return () => {
      this.syncCallbacks.delete(callback)
    }
  }

  /**
   * 通知同步状态变化
   */
  private async notifySyncStatus(): Promise<void> {
    const status = await this.getSyncStatus()
    this.syncCallbacks.forEach(callback => callback(status))
  }

  /**
   * 强制同步
   */
  async forceSync(): Promise<void> {
    if (this.isOnline) {
      await this.processPendingOperations()
    }
  }

  /**
   * 清空所有离线数据
   */
  async clearAllOfflineData(): Promise<void> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache', 'operations', 'sync_status'], 'readwrite')
    
    await Promise.all([
      new Promise<void>((resolve, reject) => {
        const request = transaction.objectStore('cache').clear()
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      }),
      new Promise<void>((resolve, reject) => {
        const request = transaction.objectStore('operations').clear()
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      }),
      new Promise<void>((resolve, reject) => {
        const request = transaction.objectStore('sync_status').clear()
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    ])

    this.notifySyncStatus()
  }

  /**
   * 获取缓存大小统计
   */
  async getCacheStats(): Promise<{
    cacheCount: number
    operationsCount: number
    totalSize: number
  }> {
    if (!this.db) await this.initDB()

    const transaction = this.db!.transaction(['cache', 'operations'], 'readonly')
    
    const [cacheCount, operationsCount] = await Promise.all([
      new Promise<number>((resolve, reject) => {
        const request = transaction.objectStore('cache').count()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      }),
      new Promise<number>((resolve, reject) => {
        const request = transaction.objectStore('operations').count()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
    ])

    // 估算总大小（简单估算）
    const totalSize = (cacheCount + operationsCount) * 1024 // 假设每条记录平均1KB

    return {
      cacheCount,
      operationsCount,
      totalSize
    }
  }
}

// 创建全局实例
export const offlineStorage = new OfflineStorageManager()

// 导出类型和实例
export default offlineStorage