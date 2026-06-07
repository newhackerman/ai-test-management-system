import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'
import type { DashboardConfig, LayoutItem, RoleType } from '@/types/dashboard'

interface DashboardState {
  // 当前仪表板配置
  currentConfig: DashboardConfig | null
  // 多仪表板配置缓存
  configCache: Record<string, DashboardConfig>
  // 当前角色
  currentRole: RoleType | null
  // 布局状态
  layout: LayoutItem[]
  // 编辑模式
  isEditMode: boolean
  // 加载状态
  isLoading: boolean
  // 错误状态
  error: string | null
  // 最后保存时间
  lastSaved: Date | null
  // 是否有未保存的更改
  hasUnsavedChanges: boolean
}

interface DashboardActions {
  // 配置管理
  setCurrentConfig: (config: DashboardConfig) => void
  updateConfig: (updates: Partial<DashboardConfig>) => void
  cacheConfig: (roleKey: string, config: DashboardConfig) => void
  getCachedConfig: (roleKey: string) => DashboardConfig | null
  clearConfigCache: () => void
  
  // 角色管理
  setCurrentRole: (role: RoleType) => void
  switchRole: (role: RoleType) => Promise<void>
  
  // 布局管理
  setLayout: (layout: LayoutItem[]) => void
  updateLayoutItem: (itemId: string, updates: Partial<LayoutItem>) => void
  addLayoutItem: (item: LayoutItem) => void
  removeLayoutItem: (itemId: string) => void
  resetLayout: () => void
  
  // 编辑模式
  setEditMode: (enabled: boolean) => void
  toggleEditMode: () => void
  
  // 状态管理
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
  
  // 保存管理
  markSaved: () => void
  markUnsaved: () => void
  
  // 重置状态
  reset: () => void
}

const initialState: DashboardState = {
  currentConfig: null,
  configCache: {},
  currentRole: null,
  layout: [],
  isEditMode: false,
  isLoading: false,
  error: null,
  lastSaved: null,
  hasUnsavedChanges: false
}

export const useDashboardStore = create<DashboardState & DashboardActions>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        ...initialState,

        // 配置管理
        setCurrentConfig: (config) => {
          set((state) => ({
            ...state,
            currentConfig: config,
            layout: config.layoutConfig?.items || [],
            error: null
          }))
        },

        updateConfig: (updates) => {
          set((state) => {
            if (state.currentConfig) {
              return {
                ...state,
                currentConfig: { ...state.currentConfig, ...updates },
                hasUnsavedChanges: true
              }
            }
            return state
          })
        },

        cacheConfig: (roleKey, config) => {
          set((state) => ({
            ...state,
            configCache: { ...state.configCache, [roleKey]: config }
          }))
        },

        getCachedConfig: (roleKey) => {
          return get().configCache[roleKey] || null
        },

        clearConfigCache: () => {
          set((state) => ({
            ...state,
            configCache: {}
          }))
        },

        // 角色管理
        setCurrentRole: (role) => {
          set((state) => ({
            ...state,
            currentRole: role
          }))
        },

        switchRole: async (role) => {
          const { currentRole, currentConfig, cacheConfig } = get()
          
          set((state) => ({
            ...state,
            isLoading: true,
            error: null
          }))

          try {
            // 缓存当前配置
            if (currentRole && currentConfig) {
              cacheConfig(`${currentRole}`, currentConfig)
            }

            // 检查缓存中是否有新角色的配置
            const cachedConfig = get().getCachedConfig(`${role}`)
            
            if (cachedConfig) {
              // 使用缓存的配置
              set((state) => ({
                ...state,
                currentRole: role,
                currentConfig: cachedConfig,
                layout: cachedConfig.layoutConfig?.items || [],
                isLoading: false
              }))
            } else {
              // 需要从服务器加载配置
              set((state) => ({
                ...state,
                currentRole: role,
                currentConfig: null,
                layout: [],
                isLoading: false
              }))
            }
          } catch (error) {
            set((state) => ({
              ...state,
              error: error instanceof Error ? error.message : '切换角色失败',
              isLoading: false
            }))
          }
        },

        // 布局管理
        setLayout: (layout) => {
          set((state) => {
            const newState = { ...state, layout }
            if (state.currentConfig) {
              newState.currentConfig = {
                ...state.currentConfig,
                layoutConfig: {
                  ...state.currentConfig.layoutConfig,
                  items: layout
                }
              }
              newState.hasUnsavedChanges = true
            }
            return newState
          })
        },

        updateLayoutItem: (itemId, updates) => {
          set((state) => {
            const itemIndex = state.layout.findIndex(item => item.i === itemId)
            if (itemIndex !== -1) {
              const newLayout = [...state.layout]
              newLayout[itemIndex] = { ...newLayout[itemIndex], ...updates }
              
              const newState = { ...state, layout: newLayout }
              if (state.currentConfig) {
                newState.currentConfig = {
                  ...state.currentConfig,
                  layoutConfig: {
                    ...state.currentConfig.layoutConfig,
                    items: newLayout
                  }
                }
                newState.hasUnsavedChanges = true
              }
              return newState
            }
            return state
          })
        },

        addLayoutItem: (item) => {
          set((state) => {
            const newLayout = [...state.layout, item]
            const newState = { ...state, layout: newLayout }
            if (state.currentConfig) {
              newState.currentConfig = {
                ...state.currentConfig,
                layoutConfig: {
                  ...state.currentConfig.layoutConfig,
                  items: newLayout
                }
              }
              newState.hasUnsavedChanges = true
            }
            return newState
          })
        },

        removeLayoutItem: (itemId) => {
          set((state) => {
            const newLayout = state.layout.filter(item => item.i !== itemId)
            const newState = { ...state, layout: newLayout }
            if (state.currentConfig) {
              newState.currentConfig = {
                ...state.currentConfig,
                layoutConfig: {
                  ...state.currentConfig.layoutConfig,
                  items: newLayout
                }
              }
              newState.hasUnsavedChanges = true
            }
            return newState
          })
        },

        resetLayout: () => {
          set((state) => {
            if (state.currentConfig?.defaultLayoutConfig) {
              const newLayout = state.currentConfig.defaultLayoutConfig.items || []
              return {
                ...state,
                layout: newLayout,
                currentConfig: {
                  ...state.currentConfig,
                  layoutConfig: state.currentConfig.defaultLayoutConfig
                },
                hasUnsavedChanges: true
              }
            }
            return state
          })
        },

        // 编辑模式
        setEditMode: (enabled) => {
          set((state) => ({
            ...state,
            isEditMode: enabled
          }))
        },

        toggleEditMode: () => {
          set((state) => ({
            ...state,
            isEditMode: !state.isEditMode
          }))
        },

        // 状态管理
        setLoading: (loading) => {
          set((state) => ({
            ...state,
            isLoading: loading
          }))
        },

        setError: (error) => {
          set((state) => ({
            ...state,
            error
          }))
        },

        clearError: () => {
          set((state) => ({
            ...state,
            error: null
          }))
        },

        // 保存管理
        markSaved: () => {
          set((state) => ({
            ...state,
            hasUnsavedChanges: false,
            lastSaved: new Date()
          }))
        },

        markUnsaved: () => {
          set((state) => ({
            ...state,
            hasUnsavedChanges: true
          }))
        },

        // 重置状态
        reset: () => {
          set(() => ({ ...initialState }))
        }
      }),
      {
        name: 'dashboard-storage',
        partialize: (state) => ({
          configCache: state.configCache,
          currentRole: state.currentRole,
          // 不持久化当前配置和布局，每次重新加载
        })
      }
    )
  )
)

// 选择器函数
export const dashboardSelectors = {
  currentConfig: (state: DashboardState & DashboardActions) => state.currentConfig,
  layout: (state: DashboardState & DashboardActions) => state.layout,
  isEditMode: (state: DashboardState & DashboardActions) => state.isEditMode,
  isLoading: (state: DashboardState & DashboardActions) => state.isLoading,
  error: (state: DashboardState & DashboardActions) => state.error,
  hasUnsavedChanges: (state: DashboardState & DashboardActions) => state.hasUnsavedChanges,
  currentRole: (state: DashboardState & DashboardActions) => state.currentRole
}

// 状态变更监听器
export const subscribeToDashboardChanges = (callback: (state: DashboardState & DashboardActions) => void) => {
  return useDashboardStore.subscribe(callback)
}

// 布局变更监听器
export const subscribeToLayoutChanges = (callback: (layout: LayoutItem[]) => void) => {
  return useDashboardStore.subscribe(
    (state) => state.layout,
    callback
  )
}

// 编辑模式变更监听器
export const subscribeToEditModeChanges = (callback: (isEditMode: boolean) => void) => {
  return useDashboardStore.subscribe(
    (state) => state.isEditMode,
    callback
  )
}