import { useEffect, useCallback, useMemo } from 'react'
import { 
  useDashboardStore,
  useWidgetStore,
  useRealtimeStore,
  useUserPreferencesStore
} from '@/stores'
import { useDataSync } from '@/services/dataSyncService'
import type { RoleType, LayoutItem, WidgetConfig, ColorScheme } from '@/types/dashboard'

/**
 * 仪表板状态管理Hook
 * 提供统一的状态管理接口，整合所有仪表板相关的状态
 */
export const useDashboardState = (roleType?: RoleType) => {
  // 获取各个store的状态和方法
  const dashboardStore = useDashboardStore()
  const widgetStore = useWidgetStore()
  const realtimeStore = useRealtimeStore()
  const userPreferencesStore = useUserPreferencesStore()
  const dataSync = useDataSync()

  // 初始化仪表板
  const initializeDashboard = useCallback(async (role: RoleType) => {
    try {
      dashboardStore.setLoading(true)
      dashboardStore.clearError()

      // 切换角色
      await dashboardStore.switchRole(role)

      // 如果没有缓存的配置，从服务器加载
      if (!dashboardStore.currentConfig) {
        // 这里应该调用API加载配置
        // const config = await dashboardService.getRoleDashboard(role)
        // dashboardStore.setCurrentConfig(config)
      }

      // 加载组件定义
      // const definitions = await widgetService.getDefinitions()
      // widgetStore.setDefinitions(definitions)

      // 建立实时连接
      if (!realtimeStore.isConnected) {
        // await realtimeStore.connect(websocketUrl, token)
      }

      // 应用用户偏好
      userPreferencesStore.applyPreferences()

    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '初始化失败')
    } finally {
      dashboardStore.setLoading(false)
    }
  }, [dashboardStore, widgetStore, realtimeStore, userPreferencesStore])

  // 保存仪表板布局
  const saveDashboardLayout = useCallback(async (layout: LayoutItem[]) => {
    try {
      dashboardStore.setLayout(layout)
      
      if (realtimeStore.isConnected) {
        // 实时保存
        await dataSync.manualSync()
      } else {
        // 离线时标记为未保存
        dashboardStore.markUnsaved()
      }
    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '保存布局失败')
    }
  }, [dashboardStore, realtimeStore, dataSync])

  // 添加组件
  const addWidget = useCallback(async (widgetType: string, config: WidgetConfig) => {
    try {
      const widgetId = `widget_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      
      // 创建组件实例
      const instance = {
        id: widgetId,
        type: widgetType,
        title: config.title || widgetType,
        config,
        position: {
          x: 0,
          y: 0,
          w: config.defaultWidth || 4,
          h: config.defaultHeight || 3
        },
        isVisible: true,
        createdAt: new Date(),
        updatedAt: new Date()
      }

      widgetStore.addInstance(instance)

      // 添加到布局
      const layoutItem: LayoutItem = {
        i: widgetId,
        x: 0,
        y: 0,
        w: instance.position.w,
        h: instance.position.h
      }

      dashboardStore.addLayoutItem(layoutItem)

      // 加载组件数据
      await refreshWidgetData(widgetId)

    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '添加组件失败')
    }
  }, [dashboardStore, widgetStore])

  // 移除组件
  const removeWidget = useCallback((widgetId: string) => {
    try {
      widgetStore.removeInstance(widgetId)
      dashboardStore.removeLayoutItem(widgetId)
    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '移除组件失败')
    }
  }, [dashboardStore, widgetStore])

  // 更新组件配置
  const updateWidgetConfig = useCallback(async (widgetId: string, config: Partial<WidgetConfig>) => {
    try {
      widgetStore.updateWidgetConfig(widgetId, config)
      
      // 如果数据源配置发生变化，重新加载数据
      if (config.dataSource) {
        await refreshWidgetData(widgetId)
      }
    } catch (error) {
      widgetStore.setWidgetError(widgetId, error instanceof Error ? error.message : '更新配置失败')
    }
  }, [widgetStore])

  // 刷新组件数据
  const refreshWidgetData = useCallback(async (widgetId: string) => {
    const instance = widgetStore.getInstance(widgetId)
    if (!instance?.config?.dataSource) {
      return
    }

    widgetStore.setWidgetLoading(widgetId, true)
    widgetStore.clearWidgetError(widgetId)

    try {
      // 这里应该根据数据源配置获取数据
      // const data = await dataService.fetchWidgetData(instance.config.dataSource)
      const data = { mock: true, timestamp: new Date() } // 模拟数据

      widgetStore.setWidgetData(widgetId, {
        data,
        timestamp: new Date()
      })
    } catch (error) {
      widgetStore.setWidgetError(widgetId, error instanceof Error ? error.message : '数据加载失败')
    } finally {
      widgetStore.setWidgetLoading(widgetId, false)
    }
  }, [widgetStore])

  // 刷新所有组件数据
  const refreshAllWidgets = useCallback(async () => {
    const instances = Object.keys(widgetStore.instances)
    await Promise.all(instances.map(widgetId => refreshWidgetData(widgetId)))
  }, [widgetStore, refreshWidgetData])

  // 应用配色方案
  const applyColorScheme = useCallback((scheme: ColorScheme) => {
    userPreferencesStore.setColorScheme(scheme)
    
    // 更新所有图表的颜色
    const instances = Object.keys(widgetStore.instances)
    instances.forEach(widgetId => {
      const config = widgetStore.getWidgetConfig(widgetId)
      if (config?.chartConfig) {
        widgetStore.updateWidgetConfig(widgetId, {
          chartConfig: {
            ...config.chartConfig,
            colors: scheme.colorPalette
          }
        })
      }
    })
  }, [userPreferencesStore, widgetStore])

  // 切换编辑模式
  const toggleEditMode = useCallback(() => {
    dashboardStore.toggleEditMode()
  }, [dashboardStore])

  // 重置仪表板
  const resetDashboard = useCallback(async () => {
    try {
      dashboardStore.resetLayout()
      await dataSync.manualSync()
    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '重置失败')
    }
  }, [dashboardStore, dataSync])

  // 导出仪表板配置
  const exportDashboard = useCallback(() => {
    const config = dashboardStore.currentConfig
    const preferences = userPreferencesStore.exportPreferences()
    
    const exportData = {
      version: '1.0',
      exportTime: new Date(),
      dashboard: config,
      preferences: JSON.parse(preferences),
      widgets: Object.values(widgetStore.instances)
    }
    
    return JSON.stringify(exportData, null, 2)
  }, [dashboardStore, userPreferencesStore, widgetStore])

  // 导入仪表板配置
  const importDashboard = useCallback(async (data: string) => {
    try {
      const importData = JSON.parse(data)
      
      if (importData.dashboard) {
        dashboardStore.setCurrentConfig(importData.dashboard)
      }
      
      if (importData.preferences) {
        userPreferencesStore.importPreferences(JSON.stringify(importData.preferences))
      }
      
      if (importData.widgets) {
        importData.widgets.forEach((widget: any) => {
          widgetStore.addInstance(widget)
        })
      }
      
      await dataSync.manualSync()
    } catch (error) {
      dashboardStore.setError(error instanceof Error ? error.message : '导入失败')
    }
  }, [dashboardStore, userPreferencesStore, widgetStore, dataSync])

  // 计算派生状态
  const derivedState = useMemo(() => {
    const syncStatus = dataSync.getSyncStatus()
    
    return {
      // 连接状态
      isOnline: syncStatus.isOnline,
      isConnected: realtimeStore.isConnected,
      connectionStatus: realtimeStore.isConnecting ? 'connecting' : 
                      realtimeStore.isConnected ? 'connected' : 
                      realtimeStore.connectionError ? 'error' : 'disconnected',
      
      // 数据状态
      hasUnsavedChanges: dashboardStore.hasUnsavedChanges || userPreferencesStore.hasUnsavedChanges,
      lastSyncTime: syncStatus.lastSyncTime,
      
      // 组件统计
      totalWidgets: Object.keys(widgetStore.instances).length,
      visibleWidgets: Object.keys(widgetStore.instances).filter(id => widgetStore.isWidgetVisible(id)).length,
      loadingWidgets: widgetStore.loadingWidgets.size,
      errorWidgets: Object.keys(widgetStore.widgetErrors).length,
      
      // 性能指标
      performanceStats: realtimeStore.getPerformanceStats()
    }
  }, [
    dashboardStore.hasUnsavedChanges,
    userPreferencesStore.hasUnsavedChanges,
    realtimeStore.isConnected,
    realtimeStore.isConnecting,
    realtimeStore.connectionError,
    widgetStore.instances,
    widgetStore.loadingWidgets,
    widgetStore.widgetErrors,
    dataSync
  ])

  // 初始化效果
  useEffect(() => {
    if (roleType && roleType !== dashboardStore.currentRole) {
      initializeDashboard(roleType)
    }
  }, [roleType, dashboardStore.currentRole, initializeDashboard])

  // 自动保存效果
  useEffect(() => {
    if (dashboardStore.hasUnsavedChanges && realtimeStore.isConnected) {
      const timer = setTimeout(() => {
        dataSync.manualSync().catch(console.error)
      }, 5000) // 5秒后自动保存

      return () => clearTimeout(timer)
    }
  }, [dashboardStore.hasUnsavedChanges, realtimeStore.isConnected, dataSync])

  return {
    // 状态
    ...derivedState,
    currentConfig: dashboardStore.currentConfig,
    currentRole: dashboardStore.currentRole,
    layout: dashboardStore.layout,
    isEditMode: dashboardStore.isEditMode,
    isLoading: dashboardStore.isLoading,
    error: dashboardStore.error,
    
    // 组件相关
    widgets: widgetStore.instances,
    selectedWidget: widgetStore.selectedWidget,
    
    // 用户偏好
    colorScheme: userPreferencesStore.selectedColorScheme,
    themeConfig: userPreferencesStore.themeConfig,
    isDarkMode: userPreferencesStore.isDarkMode,
    
    // 方法
    initializeDashboard,
    saveDashboardLayout,
    addWidget,
    removeWidget,
    updateWidgetConfig,
    refreshWidgetData,
    refreshAllWidgets,
    applyColorScheme,
    toggleEditMode,
    resetDashboard,
    exportDashboard,
    importDashboard,
    
    // 同步方法
    manualSync: dataSync.manualSync,
    restoreFromBackup: dataSync.restoreFromBackup
  }
}

export default useDashboardState