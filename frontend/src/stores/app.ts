import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AppConfig {
  apiBaseUrl: string
  version: string
  environment: 'development' | 'staging' | 'production'
  features: Record<string, boolean>
  limits: {
    maxFileSize: number
    maxFiles: number
    requestTimeout: number
  }
}

export interface SystemStatus {
  api: 'online' | 'offline' | 'maintenance'
  database: 'online' | 'offline' | 'maintenance'
  storage: 'online' | 'offline' | 'maintenance'
  lastCheck: number
}

export interface AppState {
  // 应用配置
  config: AppConfig
  
  // 系统状态
  systemStatus: SystemStatus
  
  // 连接状态
  isOnline: boolean
  
  // 应用初始化状态
  isInitialized: boolean
  initializationError: string | null
  
  // 全局设置
  settings: Record<string, any>
  
  // 缓存数据
  cache: Record<string, { data: any; timestamp: number; ttl: number }>
}

export interface AppActions {
  // 初始化应用
  initialize: () => Promise<void>
  
  // 配置管理
  updateConfig: (config: Partial<AppConfig>) => void
  
  // 系统状态
  updateSystemStatus: (status: Partial<SystemStatus>) => void
  checkSystemStatus: () => Promise<void>
  
  // 连接状态
  setOnlineStatus: (isOnline: boolean) => void
  
  // 设置管理
  updateSettings: (settings: Record<string, any>) => void
  getSetting: (key: string, defaultValue?: any) => any
  setSetting: (key: string, value: any) => void
  
  // 缓存管理
  setCache: (key: string, data: any, ttl?: number) => void
  getCache: (key: string) => any | null
  clearCache: (key?: string) => void
  
  // 功能开关
  isFeatureEnabled: (feature: string) => boolean
  toggleFeature: (feature: string) => void
}

export type AppStore = AppState & AppActions

// 默认配置
const defaultConfig: AppConfig = {
  apiBaseUrl: '/api',
  version: '1.0.0',
  environment: 'development',
  features: {
    aiAssistant: true,
    aiProgramming: true,
    performanceMonitoring: true,
    realTimeNotifications: true,
    advancedReporting: true,
    videoMeeting: false,
    darkMode: true
  },
  limits: {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    maxFiles: 5,
    requestTimeout: 30000 // 30秒
  }
}

// 模拟API调用
const mockCheckSystemStatus = async (): Promise<SystemStatus> => {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  return {
    api: 'online',
    database: 'online',
    storage: 'online',
    lastCheck: Date.now()
  }
}

const mockInitializeApp = async (): Promise<{ config: AppConfig; settings: Record<string, any> }> => {
  // 模拟初始化延迟
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  return {
    config: defaultConfig,
    settings: {
      autoSave: true,
      notifications: true,
      theme: 'system',
      language: 'zh',
      timezone: 'Asia/Shanghai'
    }
  }
}

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // 初始状态
      config: defaultConfig,
      systemStatus: {
        api: 'offline',
        database: 'offline',
        storage: 'offline',
        lastCheck: 0
      },
      isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
      isInitialized: false,
      initializationError: null,
      settings: {},
      cache: {},

      // 初始化应用
      initialize: async () => {
        try {
          set({ initializationError: null })
          
          const { config, settings } = await mockInitializeApp()
          const systemStatus = await mockCheckSystemStatus()
          
          set({
            config,
            settings,
            systemStatus,
            isInitialized: true
          })
        } catch (error) {
          set({
            initializationError: error instanceof Error ? error.message : '应用初始化失败',
            isInitialized: false
          })
          throw error
        }
      },

      // 配置管理
      updateConfig: (configUpdate) => {
        set(state => ({
          config: { ...state.config, ...configUpdate }
        }))
      },

      // 系统状态
      updateSystemStatus: (statusUpdate) => {
        set(state => ({
          systemStatus: { ...state.systemStatus, ...statusUpdate, lastCheck: Date.now() }
        }))
      },

      checkSystemStatus: async () => {
        try {
          const status = await mockCheckSystemStatus()
          set({ systemStatus: status })
        } catch (error) {
          set(state => ({
            systemStatus: {
              ...state.systemStatus,
              api: 'offline',
              database: 'offline',
              storage: 'offline',
              lastCheck: Date.now()
            }
          }))
        }
      },

      // 连接状态
      setOnlineStatus: (isOnline) => {
        set({ isOnline })
      },

      // 设置管理
      updateSettings: (settingsUpdate) => {
        set(state => ({
          settings: { ...state.settings, ...settingsUpdate }
        }))
      },

      getSetting: (key, defaultValue = null) => {
        const { settings } = get()
        return settings[key] !== undefined ? settings[key] : defaultValue
      },

      setSetting: (key, value) => {
        set(state => ({
          settings: { ...state.settings, [key]: value }
        }))
      },

      // 缓存管理
      setCache: (key, data, ttl = 5 * 60 * 1000) => { // 默认5分钟TTL
        set(state => ({
          cache: {
            ...state.cache,
            [key]: {
              data,
              timestamp: Date.now(),
              ttl
            }
          }
        }))
      },

      getCache: (key) => {
        const { cache } = get()
        const item = cache[key]
        
        if (!item) return null
        
        // 检查是否过期
        if (Date.now() - item.timestamp > item.ttl) {
          // 清除过期缓存
          get().clearCache(key)
          return null
        }
        
        return item.data
      },

      clearCache: (key) => {
        if (key) {
          set(state => {
            const newCache = { ...state.cache }
            delete newCache[key]
            return { cache: newCache }
          })
        } else {
          set({ cache: {} })
        }
      },

      // 功能开关
      isFeatureEnabled: (feature) => {
        const { config } = get()
        return config.features[feature] || false
      },

      toggleFeature: (feature) => {
        set(state => ({
          config: {
            ...state.config,
            features: {
              ...state.config.features,
              [feature]: !state.config.features[feature]
            }
          }
        }))
      }
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        config: state.config,
        settings: state.settings,
        isInitialized: state.isInitialized
      })
    }
  )
)

// 监听网络状态变化
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    useAppStore.getState().setOnlineStatus(true)
  })

  window.addEventListener('offline', () => {
    useAppStore.getState().setOnlineStatus(false)
  })
}

// 工具函数
export const useAppConfig = () => {
  const config = useAppStore(state => state.config)
  const updateConfig = useAppStore(state => state.updateConfig)
  const isFeatureEnabled = useAppStore(state => state.isFeatureEnabled)
  const toggleFeature = useAppStore(state => state.toggleFeature)

  return {
    config,
    updateConfig,
    isFeatureEnabled,
    toggleFeature
  }
}

export const useAppSettings = () => {
  const settings = useAppStore(state => state.settings)
  const updateSettings = useAppStore(state => state.updateSettings)
  const getSetting = useAppStore(state => state.getSetting)
  const setSetting = useAppStore(state => state.setSetting)

  return {
    settings,
    updateSettings,
    getSetting,
    setSetting
  }
}

export const useSystemStatus = () => {
  const systemStatus = useAppStore(state => state.systemStatus)
  const updateSystemStatus = useAppStore(state => state.updateSystemStatus)
  const checkSystemStatus = useAppStore(state => state.checkSystemStatus)
  const isOnline = useAppStore(state => state.isOnline)

  return {
    systemStatus,
    updateSystemStatus,
    checkSystemStatus,
    isOnline
  }
}