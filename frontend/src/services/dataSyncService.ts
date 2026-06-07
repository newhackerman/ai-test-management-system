import { 
  useDashboardStore, 
  useWidgetStore, 
  useRealtimeStore, 
  useUserPreferencesStore 
} from '@/stores'
import type { DashboardConfig, WidgetConfig, OfflineAction } from '@/types/dashboard'

/**
 * 数据同步服务
 * 负责处理离线模式、数据缓存和同步机制
 */
export class DataSyncService {
  private syncInterval: NodeJS.Timeout | null = null
  private isOnline: boolean = navigator.onLine
  private syncQueue: OfflineAction[] = []
  private lastSyncTime: Date | null = null

  constructor() {
    this.initializeEventListeners()
    this.startPeriodicSync()
  }

  /**
   * 初始化事件监听器
   */
  private initializeEventListeners() {
    // 监听网络状态变化
    window.addEventListener('online', this.handleOnline.bind(this))
    window.addEventListener('offline', this.handleOffline.bind(this))
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this))
    
    // 监听页面卸载
    window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this))
  }

  /**
   * 处理网络连接恢复
   */
  private async handleOnline() {
    this.isOnline = true
    const realtimeStore = useRealtimeStore.getState()
    const userPreferencesStore = useUserPreferencesStore.getState()
    
    // 更新离线状态
    realtimeStore.setOffline(false)
    
    // 尝试重新连接WebSocket
    try {
      await realtimeStore.reconnect()
    } catch (error) {
      console.error('重连WebSocket失败:', error)
    }
    
    // 处理离线队列
    await this.processOfflineQueue()
    
    // 同步用户偏好
    if (userPreferencesStore.syncEnabled) {
      await userPreferencesStore.syncFromCloud()
    }
    
    // 刷新所有数据
    await this.refreshAllData()
  }

  /**
   * 处理网络断开
   */
  private handleOffline() {
    this.isOnline = false
    const realtimeStore = useRealtimeStore.getState()
    
    // 更新离线状态
    realtimeStore.setOffline(true)
    realtimeStore.disconnect()
  }

  /**
   * 处理页面可见性变化
   */
  private handleVisibilityChange() {
    if (document.hidden) {
      // 页面隐藏时暂停同步
      this.pauseSync()
    } else {
      // 页面显示时恢复同步
      this.resumeSync()
      
      // 检查数据是否需要刷新
      this.checkDataFreshness()
    }
  }

  /**
   * 处理页面卸载前
   */
  private handleBeforeUnload() {
    // 保存未保存的更改
    this.saveUnsavedChanges()
    
    // 清理资源
    this.cleanup()
  }

  /**
   * 开始定期同步
   */
  private startPeriodicSync() {
    this.syncInterval = setInterval(() => {
      if (this.isOnline && !document.hidden) {
        this.performPeriodicSync()
      }
    }, 30000) // 每30秒同步一次
  }

  /**
   * 暂停同步
   */
  private pauseSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
      this.syncInterval = null
    }
  }

  /**
   * 恢复同步
   */
  private resumeSync() {
    if (!this.syncInterval) {
      this.startPeriodicSync()
    }
  }

  /**
   * 执行定期同步
   */
  private async performPeriodicSync() {
    try {
      const dashboardStore = useDashboardStore.getState()
      const userPreferencesStore = useUserPreferencesStore.getState()
      
      // 同步仪表板配置
      if (dashboardStore.hasUnsavedChanges) {
        await this.saveDashboardConfig()
      }
      
      // 同步用户偏好
      if (userPreferencesStore.hasUnsavedChanges && userPreferencesStore.syncEnabled) {
        await userPreferencesStore.syncToCloud()
      }
      
      this.lastSyncTime = new Date()
    } catch (error) {
      console.error('定期同步失败:', error)
    }
  }

  /**
   * 检查数据新鲜度
   */
  private checkDataFreshness() {
    const now = new Date()
    const threshold = 5 * 60 * 1000 // 5分钟
    
    if (!this.lastSyncTime || (now.getTime() - this.lastSyncTime.getTime()) > threshold) {
      this.refreshAllData()
    }
  }

  /**
   * 刷新所有数据
   */
  private async refreshAllData() {
    try {
      const widgetStore = useWidgetStore.getState()
      const instances = widgetStore.instances
      
      // 刷新所有组件数据
      for (const [widgetId, instance] of Object.entries(instances)) {
        if (widgetStore.isWidgetVisible(widgetId)) {
          await this.refreshWidgetData(widgetId)
        }
      }
      
      widgetStore.refreshAllWidgets()
    } catch (error) {
      console.error('刷新数据失败:', error)
    }
  }

  /**
   * 刷新组件数据
   */
  private async refreshWidgetData(widgetId: string) {
    const widgetStore = useWidgetStore.getState()
    const instance = widgetStore.getInstance(widgetId)
    
    if (!instance || !instance.config?.dataSource) {
      return
    }

    widgetStore.setWidgetLoading(widgetId, true)
    widgetStore.clearWidgetError(widgetId)

    try {
      const data = await this.fetchWidgetData(instance.config.dataSource)
      widgetStore.setWidgetData(widgetId, {
        data,
        timestamp: new Date()
      })
    } catch (error) {
      widgetStore.setWidgetError(widgetId, error instanceof Error ? error.message : '数据加载失败')
    } finally {
      widgetStore.setWidgetLoading(widgetId, false)
    }
  }

  /**
   * 获取组件数据
   */
  private async fetchWidgetData(dataSource: any): Promise<any> {
    if (dataSource.type === 'api') {
      const response = await fetch(dataSource.url, {
        method: dataSource.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...dataSource.headers
        },
        body: dataSource.body ? JSON.stringify(dataSource.body) : undefined
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // 应用数据转换
      if (dataSource.transform) {
        try {
          const transformFn = new Function('data', dataSource.transform)
          return transformFn(data)
        } catch (error) {
          console.warn('数据转换失败:', error)
          return data
        }
      }
      
      return data
    }
    
    return null
  }

  /**
   * 处理离线队列
   */
  private async processOfflineQueue() {
    const realtimeStore = useRealtimeStore.getState()
    
    try {
      await realtimeStore.processOfflineQueue()
      this.syncQueue = []
    } catch (error) {
      console.error('处理离线队列失败:', error)
    }
  }

  /**
   * 保存仪表板配置
   */
  private async saveDashboardConfig() {
    const dashboardStore = useDashboardStore.getState()
    const { currentConfig, currentRole } = dashboardStore
    
    if (!currentConfig || !currentRole) {
      return
    }

    try {
      // 这里应该调用API保存配置
      const response = await fetch(`/api/v1/dashboards/config/${currentRole}/layout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          layout_config: currentConfig.layoutConfig,
          widget_configs: currentConfig.widgetConfigs,
          refresh_interval: currentConfig.refreshInterval
        })
      })
      
      if (response.ok) {
        dashboardStore.markSaved()
      } else {
        throw new Error('保存失败')
      }
    } catch (error) {
      if (!this.isOnline) {
        // 离线时添加到队列
        this.addToOfflineQueue('saveDashboardConfig', currentConfig)
      } else {
        throw error
      }
    }
  }

  /**
   * 添加到离线队列
   */
  private addToOfflineQueue(action: string, data: any) {
    const realtimeStore = useRealtimeStore.getState()
    realtimeStore.queueOfflineAction(action, data)
  }

  /**
   * 保存未保存的更改
   */
  private saveUnsavedChanges() {
    const dashboardStore = useDashboardStore.getState()
    const userPreferencesStore = useUserPreferencesStore.getState()
    
    // 保存仪表板更改到本地存储
    if (dashboardStore.hasUnsavedChanges) {
      const config = dashboardStore.currentConfig
      if (config) {
        localStorage.setItem(`dashboard_backup_${config.roleType}`, JSON.stringify(config))
      }
    }
    
    // 保存用户偏好更改到本地存储
    if (userPreferencesStore.hasUnsavedChanges) {
      const preferences = userPreferencesStore.exportPreferences()
      localStorage.setItem('preferences_backup', preferences)
    }
  }

  /**
   * 恢复备份数据
   */
  public async restoreFromBackup() {
    const dashboardStore = useDashboardStore.getState()
    const userPreferencesStore = useUserPreferencesStore.getState()
    
    try {
      // 恢复仪表板配置
      const currentRole = dashboardStore.currentRole
      if (currentRole) {
        const backupConfig = localStorage.getItem(`dashboard_backup_${currentRole}`)
        if (backupConfig) {
          const config = JSON.parse(backupConfig)
          dashboardStore.setCurrentConfig(config)
          localStorage.removeItem(`dashboard_backup_${currentRole}`)
        }
      }
      
      // 恢复用户偏好
      const backupPreferences = localStorage.getItem('preferences_backup')
      if (backupPreferences) {
        userPreferencesStore.importPreferences(backupPreferences)
        localStorage.removeItem('preferences_backup')
      }
    } catch (error) {
      console.error('恢复备份数据失败:', error)
    }
  }

  /**
   * 清理资源
   */
  private cleanup() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
      this.syncInterval = null
    }
    
    window.removeEventListener('online', this.handleOnline.bind(this))
    window.removeEventListener('offline', this.handleOffline.bind(this))
    document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this))
    window.removeEventListener('beforeunload', this.handleBeforeUnload.bind(this))
  }

  /**
   * 获取同步状态
   */
  public getSyncStatus() {
    return {
      isOnline: this.isOnline,
      lastSyncTime: this.lastSyncTime,
      queueLength: this.syncQueue.length,
      isActive: this.syncInterval !== null
    }
  }

  /**
   * 手动触发同步
   */
  public async manualSync() {
    if (!this.isOnline) {
      throw new Error('网络未连接，无法同步')
    }
    
    await this.performPeriodicSync()
  }

  /**
   * 销毁服务
   */
  public destroy() {
    this.cleanup()
  }
}

// 创建全局实例
export const dataSyncService = new DataSyncService()

// 导出便捷方法
export const useDataSync = () => {
  return {
    getSyncStatus: () => dataSyncService.getSyncStatus(),
    manualSync: () => dataSyncService.manualSync(),
    restoreFromBackup: () => dataSyncService.restoreFromBackup()
  }
}