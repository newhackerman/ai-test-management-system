// @ts-nocheck
import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'
import type { WidgetDefinition, WidgetInstance, WidgetData, WidgetConfig } from '@/types/dashboard'

interface WidgetState {
  // 缁勪欢瀹氫箟
  definitions: Record<string, WidgetDefinition>
  // 缁勪欢瀹炰緥
  instances: Record<string, WidgetInstance>
  // 缁勪欢鏁版嵁缂撳瓨
  dataCache: Record<string, WidgetData>
  // 缁勪欢閰嶇疆
  configs: Record<string, WidgetConfig>
  // 閫変腑鐨勭粍浠?
  selectedWidget: string | null
  // 鍔犺浇鐘舵€?
  loadingWidgets: Set<string>
  // 閿欒鐘舵€?
  widgetErrors: Record<string, string>
  // 鏁版嵁鍒锋柊鏃堕棿鎴?
  lastRefresh: Record<string, Date>
  // 缁勪欢鍙鎬?
  widgetVisibility: Record<string, boolean>
}

interface WidgetActions {
  // 缁勪欢瀹氫箟绠＄悊
  setDefinitions: (definitions: WidgetDefinition[]) => void
  addDefinition: (definition: WidgetDefinition) => void
  updateDefinition: (id: string, updates: Partial<WidgetDefinition>) => void
  removeDefinition: (id: string) => void
  getDefinition: (type: string) => WidgetDefinition | null
  
  // 缁勪欢瀹炰緥绠＄悊
  addInstance: (instance: WidgetInstance) => void
  updateInstance: (id: string, updates: Partial<WidgetInstance>) => void
  removeInstance: (id: string) => void
  getInstance: (id: string) => WidgetInstance | null
  getInstancesByType: (type: string) => WidgetInstance[]
  
  // 缁勪欢鏁版嵁绠＄悊
  setWidgetData: (widgetId: string, data: WidgetData) => void
  updateWidgetData: (widgetId: string, updates: Partial<WidgetData>) => void
  clearWidgetData: (widgetId: string) => void
  getWidgetData: (widgetId: string) => WidgetData | null
  
  // 缁勪欢閰嶇疆绠＄悊
  setWidgetConfig: (widgetId: string, config: WidgetConfig) => void
  updateWidgetConfig: (widgetId: string, updates: Partial<WidgetConfig>) => void
  getWidgetConfig: (widgetId: string) => WidgetConfig | null
  
  // 閫夋嫨绠＄悊
  selectWidget: (widgetId: string | null) => void
  
  // 鍔犺浇鐘舵€佺鐞?
  setWidgetLoading: (widgetId: string, loading: boolean) => void
  isWidgetLoading: (widgetId: string) => boolean
  
  // 閿欒绠＄悊
  setWidgetError: (widgetId: string, error: string | null) => void
  clearWidgetError: (widgetId: string) => void
  getWidgetError: (widgetId: string) => string | null
  
  // 鍒锋柊绠＄悊
  markWidgetRefreshed: (widgetId: string) => void
  getLastRefresh: (widgetId: string) => Date | null
  
  // 鍙鎬х鐞?
  setWidgetVisibility: (widgetId: string, visible: boolean) => void
  toggleWidgetVisibility: (widgetId: string) => void
  isWidgetVisible: (widgetId: string) => boolean
  
  // 鎵归噺鎿嶄綔
  refreshAllWidgets: () => void
  clearAllErrors: () => void
  hideAllWidgets: () => void
  showAllWidgets: () => void
  
  // 閲嶇疆
  reset: () => void
}

const initialState: WidgetState = {
  definitions: {},
  instances: {},
  dataCache: {},
  configs: {},
  selectedWidget: null,
  loadingWidgets: new Set(),
  widgetErrors: {},
  lastRefresh: {},
  widgetVisibility: {}
}

export const useWidgetStore = create<WidgetState & WidgetActions>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        ...initialState,

        // 缁勪欢瀹氫箟绠＄悊
        setDefinitions: (definitions) => {
          set((state) => {
            const newDefinitions: Record<string, WidgetDefinition> = {}
            definitions.forEach(def => {
              newDefinitions[def.widgetType] = def
            })
            return { ...state, definitions: newDefinitions }
          })
        },

        addDefinition: (definition) => {
          set((state) => ({
            ...state,
            definitions: {
              ...state.definitions,
              [definition.widgetType]: definition
            }
          }))
        },

        updateDefinition: (id, updates) => {
          set((state) => {
            if (state.definitions[id]) {
              return {
                ...state,
                definitions: {
                  ...state.definitions,
                  [id]: { ...state.definitions[id], ...updates }
                }
              }
            }
            return state
          })
        },

        removeDefinition: (id) => {
          set((state) => {
            const { [id]: removed, ...rest } = state.definitions
            return { ...state, definitions: rest }
          })
        },

        getDefinition: (type) => {
          return get().definitions[type] || null
        },

        // 缁勪欢瀹炰緥绠＄悊
        addInstance: (instance) => {
          set((state) => {
            state.instances[instance.id] = instance
            // 鍒濆鍖栫浉鍏崇姸鎬?
            state.widgetVisibility[instance.id] = true
            state.configs[instance.id] = instance.config || {}
          })
        },

        updateInstance: (id, updates) => {
          set((state) => {
            if (state.instances[id]) {
              Object.assign(state.instances[id], updates)
              // 濡傛灉鏇存柊浜嗛厤缃紝鍚屾鍒癱onfigs
              if (updates.config) {
                state.configs[id] = updates.config
              }
            }
          })
        },

        removeInstance: (id) => {
          set((state) => {
            delete state.instances[id]
            delete state.dataCache[id]
            delete state.configs[id]
            delete state.widgetErrors[id]
            delete state.lastRefresh[id]
            delete state.widgetVisibility[id]
            state.loadingWidgets.delete(id)
            
            if (state.selectedWidget === id) {
              state.selectedWidget = null
            }
          })
        },

        getInstance: (id) => {
          return get().instances[id] || null
        },

        getInstancesByType: (type) => {
          const instances = get().instances
          return Object.values(instances).filter(instance => instance.type === type)
        },

        // 缁勪欢鏁版嵁绠＄悊
        setWidgetData: (widgetId, data) => {
          set((state) => {
            state.dataCache[widgetId] = data
            state.lastRefresh[widgetId] = new Date()
          })
        },

        updateWidgetData: (widgetId, updates) => {
          set((state) => {
            if (state.dataCache[widgetId]) {
              Object.assign(state.dataCache[widgetId], updates)
              state.lastRefresh[widgetId] = new Date()
            }
          })
        },

        clearWidgetData: (widgetId) => {
          set((state) => {
            delete state.dataCache[widgetId]
            delete state.lastRefresh[widgetId]
          })
        },

        getWidgetData: (widgetId) => {
          return get().dataCache[widgetId] || null
        },

        // 缁勪欢閰嶇疆绠＄悊
        setWidgetConfig: (widgetId, config) => {
          set((state) => {
            state.configs[widgetId] = config
            // 鍚屾鍒板疄渚?
            if (state.instances[widgetId]) {
              state.instances[widgetId].config = config
            }
          })
        },

        updateWidgetConfig: (widgetId, updates) => {
          set((state) => {
            if (state.configs[widgetId]) {
              Object.assign(state.configs[widgetId], updates)
              // 鍚屾鍒板疄渚?
              if (state.instances[widgetId]) {
                state.instances[widgetId].config = state.configs[widgetId]
              }
            }
          })
        },

        getWidgetConfig: (widgetId) => {
          return get().configs[widgetId] || null
        },

        // 閫夋嫨绠＄悊
        selectWidget: (widgetId) => {
          set((state) => {
            state.selectedWidget = widgetId
          })
        },

        // 鍔犺浇鐘舵€佺鐞?
        setWidgetLoading: (widgetId, loading) => {
          set((state) => {
            if (loading) {
              state.loadingWidgets.add(widgetId)
            } else {
              state.loadingWidgets.delete(widgetId)
            }
          })
        },

        isWidgetLoading: (widgetId) => {
          return get().loadingWidgets.has(widgetId)
        },

        // 閿欒绠＄悊
        setWidgetError: (widgetId, error) => {
          set((state) => {
            if (error) {
              state.widgetErrors[widgetId] = error
            } else {
              delete state.widgetErrors[widgetId]
            }
          })
        },

        clearWidgetError: (widgetId) => {
          set((state) => {
            delete state.widgetErrors[widgetId]
          })
        },

        getWidgetError: (widgetId) => {
          return get().widgetErrors[widgetId] || null
        },

        // 鍒锋柊绠＄悊
        markWidgetRefreshed: (widgetId) => {
          set((state) => {
            state.lastRefresh[widgetId] = new Date()
          })
        },

        getLastRefresh: (widgetId) => {
          return get().lastRefresh[widgetId] || null
        },

        // 鍙鎬х鐞?
        setWidgetVisibility: (widgetId, visible) => {
          set((state) => {
            state.widgetVisibility[widgetId] = visible
          })
        },

        toggleWidgetVisibility: (widgetId) => {
          set((state) => {
            state.widgetVisibility[widgetId] = !state.widgetVisibility[widgetId]
          })
        },

        isWidgetVisible: (widgetId) => {
          return get().widgetVisibility[widgetId] ?? true
        },

        // 鎵归噺鎿嶄綔
        refreshAllWidgets: () => {
          const instances = get().instances
          const now = new Date()
          set((state) => {
            Object.keys(instances).forEach(widgetId => {
              state.lastRefresh[widgetId] = now
            })
          })
        },

        clearAllErrors: () => {
          set((state) => {
            state.widgetErrors = {}
          })
        },

        hideAllWidgets: () => {
          const instances = get().instances
          set((state) => {
            Object.keys(instances).forEach(widgetId => {
              state.widgetVisibility[widgetId] = false
            })
          })
        },

        showAllWidgets: () => {
          const instances = get().instances
          set((state) => {
            Object.keys(instances).forEach(widgetId => {
              state.widgetVisibility[widgetId] = true
            })
          })
        },

        // 閲嶇疆
        reset: () => {
          set(() => ({ 
            ...initialState,
            loadingWidgets: new Set()
          }))
        }
      }),
      {
        name: 'widget-storage',
        partialize: (state) => ({
          definitions: state.definitions,
          configs: state.configs,
          widgetVisibility: state.widgetVisibility,
          // 涓嶆寔涔呭寲瀹炰緥銆佹暟鎹紦瀛樼瓑杩愯鏃剁姸鎬?
        })
      }
    )
  )
)

// 閫夋嫨鍣ㄥ嚱鏁?
export const widgetSelectors = {
  definitions: (state: WidgetState & WidgetActions) => state.definitions,
  instances: (state: WidgetState & WidgetActions) => state.instances,
  selectedWidget: (state: WidgetState & WidgetActions) => state.selectedWidget,
  loadingWidgets: (state: WidgetState & WidgetActions) => state.loadingWidgets,
  widgetErrors: (state: WidgetState & WidgetActions) => state.widgetErrors,
  dataCache: (state: WidgetState & WidgetActions) => state.dataCache,
  configs: (state: WidgetState & WidgetActions) => state.configs,
  widgetVisibility: (state: WidgetState & WidgetActions) => state.widgetVisibility
}

// 缁勪欢鏁版嵁鍙樻洿鐩戝惉鍣?
export const subscribeToWidgetData = (widgetId: string, callback: (data: WidgetData | null) => void) => {
  return useWidgetStore.subscribe(
    (state) => state.dataCache[widgetId] || null,
    callback
  )
}

// 缁勪欢閰嶇疆鍙樻洿鐩戝惉鍣?
export const subscribeToWidgetConfig = (widgetId: string, callback: (config: WidgetConfig | null) => void) => {
  return useWidgetStore.subscribe(
    (state) => state.configs[widgetId] || null,
    callback
  )
}

// 缁勪欢閫夋嫨鍙樻洿鐩戝惉鍣?
export const subscribeToWidgetSelection = (callback: (selectedWidget: string | null) => void) => {
  return useWidgetStore.subscribe(
    (state) => state.selectedWidget,
    callback
  )
}

// 缁勪欢閿欒鐩戝惉鍣?
export const subscribeToWidgetErrors = (callback: (errors: Record<string, string>) => void) => {
  return useWidgetStore.subscribe(
    (state) => state.widgetErrors,
    callback
  )
}
