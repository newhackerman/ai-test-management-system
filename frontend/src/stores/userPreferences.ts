// @ts-nocheck
import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'
import type { ColorScheme, ThemeConfig, LayoutPreferences, NotificationSettings } from '@/types/dashboard'

interface UserPreferencesState {
  // 閰嶈壊鏂规
  selectedColorScheme: ColorScheme | null
  customColorSchemes: ColorScheme[]
  
  // 涓婚閰嶇疆
  themeConfig: ThemeConfig
  isDarkMode: boolean
  autoSwitchDarkMode: boolean
  
  // 甯冨眬鍋忓ソ
  layoutPreferences: LayoutPreferences
  
  // 閫氱煡璁剧疆
  notificationSettings: NotificationSettings
  
  // 璇█璁剧疆
  language: string
  timezone: string
  
  // 鏁版嵁鍒锋柊璁剧疆
  autoRefresh: boolean
  refreshInterval: number
  
  // 鍙闂€ц缃?
  accessibilityMode: boolean
  highContrast: boolean
  fontSize: 'small' | 'medium' | 'large'
  
  // 涓汉鍖栬缃?
  favoriteWidgets: string[]
  hiddenWidgets: string[]
  widgetOrder: string[]
  
  // 鍚屾鐘舵€?
  lastSyncTime: Date | null
  syncEnabled: boolean
  syncError: string | null
  
  // 鏈湴瀛樺偍鐘舵€?
  isLoading: boolean
  hasUnsavedChanges: boolean
}

interface UserPreferencesActions {
  // 閰嶈壊鏂规绠＄悊
  setColorScheme: (scheme: ColorScheme) => void
  addCustomColorScheme: (scheme: ColorScheme) => void
  updateCustomColorScheme: (id: string, updates: Partial<ColorScheme>) => void
  removeCustomColorScheme: (id: string) => void
  
  // 涓婚绠＄悊
  setThemeConfig: (config: Partial<ThemeConfig>) => void
  toggleDarkMode: () => void
  setAutoSwitchDarkMode: (enabled: boolean) => void
  
  // 甯冨眬鍋忓ソ
  setLayoutPreferences: (preferences: Partial<LayoutPreferences>) => void
  updateGridSettings: (settings: Partial<LayoutPreferences['gridSettings']>) => void
  
  // 閫氱煡璁剧疆
  setNotificationSettings: (settings: Partial<NotificationSettings>) => void
  toggleNotification: (type: keyof NotificationSettings) => void
  
  // 璇█鍜屽湴鍖?
  setLanguage: (language: string) => void
  setTimezone: (timezone: string) => void
  
  // 鏁版嵁鍒锋柊
  setAutoRefresh: (enabled: boolean) => void
  setRefreshInterval: (interval: number) => void
  
  // 鍙闂€?
  setAccessibilityMode: (enabled: boolean) => void
  setHighContrast: (enabled: boolean) => void
  setFontSize: (size: 'small' | 'medium' | 'large') => void
  
  // 涓汉鍖?
  addFavoriteWidget: (widgetId: string) => void
  removeFavoriteWidget: (widgetId: string) => void
  hideWidget: (widgetId: string) => void
  showWidget: (widgetId: string) => void
  setWidgetOrder: (order: string[]) => void
  
  // 鍚屾绠＄悊
  syncToCloud: () => Promise<void>
  syncFromCloud: () => Promise<void>
  setSyncEnabled: (enabled: boolean) => void
  clearSyncError: () => void
  
  // 鐘舵€佺鐞?
  setLoading: (loading: boolean) => void
  markUnsaved: () => void
  markSaved: () => void
  
  // 閲嶇疆鍜屽鍏ュ鍑?
  resetToDefaults: () => void
  exportPreferences: () => string
  importPreferences: (data: string) => void
  
  // 搴旂敤鍋忓ソ
  applyPreferences: () => void
}

const defaultThemeConfig: ThemeConfig = {
  primaryColor: '#2563eb',
  borderRadius: 6,
  componentSize: 'middle',
  wireframe: false
}

const defaultLayoutPreferences: LayoutPreferences = {
  gridSettings: {
    cols: 12,
    rowHeight: 60,
    margin: [10, 10],
    containerPadding: [10, 10]
  },
  compactMode: false,
  showGridLines: false,
  snapToGrid: true
}

const defaultNotificationSettings: NotificationSettings = {
  dataUpdates: true,
  systemAlerts: true,
  projectNotifications: true,
  emailNotifications: false,
  pushNotifications: true,
  soundEnabled: false
}

const initialState: UserPreferencesState = {
  selectedColorScheme: null,
  customColorSchemes: [],
  
  themeConfig: defaultThemeConfig,
  isDarkMode: false,
  autoSwitchDarkMode: false,
  
  layoutPreferences: defaultLayoutPreferences,
  
  notificationSettings: defaultNotificationSettings,
  
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  
  autoRefresh: true,
  refreshInterval: 30,
  
  accessibilityMode: false,
  highContrast: false,
  fontSize: 'medium',
  
  favoriteWidgets: [],
  hiddenWidgets: [],
  widgetOrder: [],
  
  lastSyncTime: null,
  syncEnabled: false,
  syncError: null,
  
  isLoading: false,
  hasUnsavedChanges: false
}

export const useUserPreferencesStore = create<UserPreferencesState & UserPreferencesActions>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        ...initialState,

        // 閰嶈壊鏂规绠＄悊
        setColorScheme: (scheme) => {
          set((state) => {
            state.selectedColorScheme = scheme
            state.hasUnsavedChanges = true
          })
        },

        addCustomColorScheme: (scheme) => {
          set((state) => {
            state.customColorSchemes.push(scheme)
            state.hasUnsavedChanges = true
          })
        },

        updateCustomColorScheme: (id, updates) => {
          set((state) => {
            const index = state.customColorSchemes.findIndex(s => s.id === id)
            if (index !== -1) {
              Object.assign(state.customColorSchemes[index], updates)
              state.hasUnsavedChanges = true
            }
          })
        },

        removeCustomColorScheme: (id) => {
          set((state) => {
            state.customColorSchemes = state.customColorSchemes.filter(s => s.id !== id)
            if (state.selectedColorScheme?.id === id) {
              state.selectedColorScheme = null
            }
            state.hasUnsavedChanges = true
          })
        },

        // 涓婚绠＄悊
        setThemeConfig: (config) => {
          set((state) => {
            Object.assign(state.themeConfig, config)
            state.hasUnsavedChanges = true
          })
        },

        toggleDarkMode: () => {
          set((state) => {
            state.isDarkMode = !state.isDarkMode
            state.hasUnsavedChanges = true
          })
        },

        setAutoSwitchDarkMode: (enabled) => {
          set((state) => {
            state.autoSwitchDarkMode = enabled
            state.hasUnsavedChanges = true
          })
        },

        // 甯冨眬鍋忓ソ
        setLayoutPreferences: (preferences) => {
          set((state) => {
            Object.assign(state.layoutPreferences, preferences)
            state.hasUnsavedChanges = true
          })
        },

        updateGridSettings: (settings) => {
          set((state) => {
            Object.assign(state.layoutPreferences.gridSettings, settings)
            state.hasUnsavedChanges = true
          })
        },

        // 閫氱煡璁剧疆
        setNotificationSettings: (settings) => {
          set((state) => {
            Object.assign(state.notificationSettings, settings)
            state.hasUnsavedChanges = true
          })
        },

        toggleNotification: (type) => {
          set((state) => {
            state.notificationSettings[type] = !state.notificationSettings[type]
            state.hasUnsavedChanges = true
          })
        },

        // 璇█鍜屽湴鍖?
        setLanguage: (language) => {
          set((state) => {
            state.language = language
            state.hasUnsavedChanges = true
          })
        },

        setTimezone: (timezone) => {
          set((state) => {
            state.timezone = timezone
            state.hasUnsavedChanges = true
          })
        },

        // 鏁版嵁鍒锋柊
        setAutoRefresh: (enabled) => {
          set((state) => {
            state.autoRefresh = enabled
            state.hasUnsavedChanges = true
          })
        },

        setRefreshInterval: (interval) => {
          set((state) => {
            state.refreshInterval = Math.max(5, Math.min(300, interval)) // 5绉掑埌5鍒嗛挓
            state.hasUnsavedChanges = true
          })
        },

        // 鍙闂€?
        setAccessibilityMode: (enabled) => {
          set((state) => {
            state.accessibilityMode = enabled
            state.hasUnsavedChanges = true
          })
        },

        setHighContrast: (enabled) => {
          set((state) => {
            state.highContrast = enabled
            state.hasUnsavedChanges = true
          })
        },

        setFontSize: (size) => {
          set((state) => {
            state.fontSize = size
            state.hasUnsavedChanges = true
          })
        },

        // 涓汉鍖?
        addFavoriteWidget: (widgetId) => {
          set((state) => {
            if (!state.favoriteWidgets.includes(widgetId)) {
              state.favoriteWidgets.push(widgetId)
              state.hasUnsavedChanges = true
            }
          })
        },

        removeFavoriteWidget: (widgetId) => {
          set((state) => {
            state.favoriteWidgets = state.favoriteWidgets.filter(id => id !== widgetId)
            state.hasUnsavedChanges = true
          })
        },

        hideWidget: (widgetId) => {
          set((state) => {
            if (!state.hiddenWidgets.includes(widgetId)) {
              state.hiddenWidgets.push(widgetId)
              state.hasUnsavedChanges = true
            }
          })
        },

        showWidget: (widgetId) => {
          set((state) => {
            state.hiddenWidgets = state.hiddenWidgets.filter(id => id !== widgetId)
            state.hasUnsavedChanges = true
          })
        },

        setWidgetOrder: (order) => {
          set((state) => {
            state.widgetOrder = order
            state.hasUnsavedChanges = true
          })
        },

        // 鍚屾绠＄悊
        syncToCloud: async () => {
          const state = get()
          
          if (!state.syncEnabled) {
            return
          }

          set((draft) => {
            draft.isLoading = true
            draft.syncError = null
          })

          try {
            // 杩欓噷搴旇璋冪敤API鍚屾鍒颁簯绔?
            const preferences = {
              selectedColorScheme: state.selectedColorScheme,
              customColorSchemes: state.customColorSchemes,
              themeConfig: state.themeConfig,
              isDarkMode: state.isDarkMode,
              autoSwitchDarkMode: state.autoSwitchDarkMode,
              layoutPreferences: state.layoutPreferences,
              notificationSettings: state.notificationSettings,
              language: state.language,
              timezone: state.timezone,
              autoRefresh: state.autoRefresh,
              refreshInterval: state.refreshInterval,
              accessibilityMode: state.accessibilityMode,
              highContrast: state.highContrast,
              fontSize: state.fontSize,
              favoriteWidgets: state.favoriteWidgets,
              hiddenWidgets: state.hiddenWidgets,
              widgetOrder: state.widgetOrder
            }

            // 妯℃嫙API璋冪敤
            await new Promise(resolve => setTimeout(resolve, 1000))
            console.log('鍚屾鍋忓ソ璁剧疆鍒颁簯绔?', preferences)

            set((draft) => {
              draft.lastSyncTime = new Date()
              draft.hasUnsavedChanges = false
              draft.isLoading = false
            })
          } catch (error) {
            set((draft) => {
              draft.syncError = error instanceof Error ? error.message : '鍚屾澶辫触'
              draft.isLoading = false
            })
          }
        },

        syncFromCloud: async () => {
          const state = get()
          
          if (!state.syncEnabled) {
            return
          }

          set((draft) => {
            draft.isLoading = true
            draft.syncError = null
          })

          try {
            // 杩欓噷搴旇璋冪敤API浠庝簯绔幏鍙栧亸濂借缃?
            await new Promise(resolve => setTimeout(resolve, 1000))
            
            // 妯℃嫙浠庝簯绔幏鍙栫殑鏁版嵁
            const cloudPreferences = {
              // ... 浜戠鍋忓ソ璁剧疆
            }

            set((draft) => {
              // 搴旂敤浜戠鍋忓ソ璁剧疆
              Object.assign(draft, cloudPreferences)
              draft.lastSyncTime = new Date()
              draft.hasUnsavedChanges = false
              draft.isLoading = false
            })
          } catch (error) {
            set((draft) => {
              draft.syncError = error instanceof Error ? error.message : '鍚屾澶辫触'
              draft.isLoading = false
            })
          }
        },

        setSyncEnabled: (enabled) => {
          set((state) => {
            state.syncEnabled = enabled
            state.hasUnsavedChanges = true
          })
        },

        clearSyncError: () => {
          set((state) => {
            state.syncError = null
          })
        },

        // 鐘舵€佺鐞?
        setLoading: (loading) => {
          set((state) => {
            state.isLoading = loading
          })
        },

        markUnsaved: () => {
          set((state) => {
            state.hasUnsavedChanges = true
          })
        },

        markSaved: () => {
          set((state) => {
            state.hasUnsavedChanges = false
          })
        },

        // 閲嶇疆鍜屽鍏ュ鍑?
        resetToDefaults: () => {
          set(() => ({
            ...initialState,
            hasUnsavedChanges: true
          }))
        },

        exportPreferences: () => {
          const state = get()
          const exportData = {
            selectedColorScheme: state.selectedColorScheme,
            customColorSchemes: state.customColorSchemes,
            themeConfig: state.themeConfig,
            isDarkMode: state.isDarkMode,
            autoSwitchDarkMode: state.autoSwitchDarkMode,
            layoutPreferences: state.layoutPreferences,
            notificationSettings: state.notificationSettings,
            language: state.language,
            timezone: state.timezone,
            autoRefresh: state.autoRefresh,
            refreshInterval: state.refreshInterval,
            accessibilityMode: state.accessibilityMode,
            highContrast: state.highContrast,
            fontSize: state.fontSize,
            favoriteWidgets: state.favoriteWidgets,
            hiddenWidgets: state.hiddenWidgets,
            widgetOrder: state.widgetOrder,
            exportTime: new Date().toISOString()
          }
          
          return JSON.stringify(exportData, null, 2)
        },

        importPreferences: (data) => {
          try {
            const importData = JSON.parse(data)
            
            set((state) => {
              // 楠岃瘉骞跺簲鐢ㄥ鍏ョ殑鏁版嵁
              if (importData.selectedColorScheme) {
                state.selectedColorScheme = importData.selectedColorScheme
              }
              if (importData.customColorSchemes) {
                state.customColorSchemes = importData.customColorSchemes
              }
              if (importData.themeConfig) {
                state.themeConfig = { ...defaultThemeConfig, ...importData.themeConfig }
              }
              if (typeof importData.isDarkMode === 'boolean') {
                state.isDarkMode = importData.isDarkMode
              }
              if (typeof importData.autoSwitchDarkMode === 'boolean') {
                state.autoSwitchDarkMode = importData.autoSwitchDarkMode
              }
              if (importData.layoutPreferences) {
                state.layoutPreferences = { ...defaultLayoutPreferences, ...importData.layoutPreferences }
              }
              if (importData.notificationSettings) {
                state.notificationSettings = { ...defaultNotificationSettings, ...importData.notificationSettings }
              }
              if (importData.language) {
                state.language = importData.language
              }
              if (importData.timezone) {
                state.timezone = importData.timezone
              }
              if (typeof importData.autoRefresh === 'boolean') {
                state.autoRefresh = importData.autoRefresh
              }
              if (typeof importData.refreshInterval === 'number') {
                state.refreshInterval = importData.refreshInterval
              }
              if (typeof importData.accessibilityMode === 'boolean') {
                state.accessibilityMode = importData.accessibilityMode
              }
              if (typeof importData.highContrast === 'boolean') {
                state.highContrast = importData.highContrast
              }
              if (importData.fontSize) {
                state.fontSize = importData.fontSize
              }
              if (Array.isArray(importData.favoriteWidgets)) {
                state.favoriteWidgets = importData.favoriteWidgets
              }
              if (Array.isArray(importData.hiddenWidgets)) {
                state.hiddenWidgets = importData.hiddenWidgets
              }
              if (Array.isArray(importData.widgetOrder)) {
                state.widgetOrder = importData.widgetOrder
              }
              
              state.hasUnsavedChanges = true
            })
          } catch (error) {
            throw new Error('瀵煎叆鏁版嵁鏍煎紡閿欒')
          }
        },

        // 搴旂敤鍋忓ソ
        applyPreferences: () => {
          const state = get()
          
          // 搴旂敤涓婚
          if (state.isDarkMode) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
          
          // 搴旂敤瀛椾綋澶у皬
          document.documentElement.setAttribute('data-font-size', state.fontSize)
          
          // 搴旂敤楂樺姣斿害
          if (state.highContrast) {
            document.documentElement.classList.add('high-contrast')
          } else {
            document.documentElement.classList.remove('high-contrast')
          }
          
          // 搴旂敤鍙闂€фā寮?
          if (state.accessibilityMode) {
            document.documentElement.classList.add('accessibility-mode')
          } else {
            document.documentElement.classList.remove('accessibility-mode')
          }
        }
      }),
      {
        name: 'user-preferences-storage',
        partialize: (state) => ({
          selectedColorScheme: state.selectedColorScheme,
          customColorSchemes: state.customColorSchemes,
          themeConfig: state.themeConfig,
          isDarkMode: state.isDarkMode,
          autoSwitchDarkMode: state.autoSwitchDarkMode,
          layoutPreferences: state.layoutPreferences,
          notificationSettings: state.notificationSettings,
          language: state.language,
          timezone: state.timezone,
          autoRefresh: state.autoRefresh,
          refreshInterval: state.refreshInterval,
          accessibilityMode: state.accessibilityMode,
          highContrast: state.highContrast,
          fontSize: state.fontSize,
          favoriteWidgets: state.favoriteWidgets,
          hiddenWidgets: state.hiddenWidgets,
          widgetOrder: state.widgetOrder,
          syncEnabled: state.syncEnabled,
          lastSyncTime: state.lastSyncTime
        })
      }
    )
  )
)

// 閫夋嫨鍣ㄥ嚱鏁?
export const userPreferencesSelectors = {
  selectedColorScheme: (state: UserPreferencesState & UserPreferencesActions) => state.selectedColorScheme,
  themeConfig: (state: UserPreferencesState & UserPreferencesActions) => state.themeConfig,
  isDarkMode: (state: UserPreferencesState & UserPreferencesActions) => state.isDarkMode,
  layoutPreferences: (state: UserPreferencesState & UserPreferencesActions) => state.layoutPreferences,
  notificationSettings: (state: UserPreferencesState & UserPreferencesActions) => state.notificationSettings,
  favoriteWidgets: (state: UserPreferencesState & UserPreferencesActions) => state.favoriteWidgets,
  hiddenWidgets: (state: UserPreferencesState & UserPreferencesActions) => state.hiddenWidgets,
  hasUnsavedChanges: (state: UserPreferencesState & UserPreferencesActions) => state.hasUnsavedChanges
}

// 涓婚鍙樻洿鐩戝惉鍣?
export const subscribeToThemeChanges = (callback: (isDarkMode: boolean) => void) => {
  return useUserPreferencesStore.subscribe(
    (state) => state.isDarkMode,
    callback
  )
}

// 閰嶈壊鏂规鍙樻洿鐩戝惉鍣?
export const subscribeToColorSchemeChanges = (callback: (scheme: ColorScheme | null) => void) => {
  return useUserPreferencesStore.subscribe(
    (state) => state.selectedColorScheme,
    callback
  )
}

// 甯冨眬鍋忓ソ鍙樻洿鐩戝惉鍣?
export const subscribeToLayoutPreferencesChanges = (callback: (preferences: LayoutPreferences) => void) => {
  return useUserPreferencesStore.subscribe(
    (state) => state.layoutPreferences,
    callback
  )
}
