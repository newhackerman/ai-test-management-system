import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'system'
export type Language = 'zh' | 'en'

export interface UIState {
  // 主题相关
  theme: Theme
  isDarkMode: boolean
  
  // 布局相关
  sidebarCollapsed: boolean
  sidebarWidth: number
  
  // 语言相关
  language: Language
  
  // 加载状态
  globalLoading: boolean
  loadingMessage: string
  
  // 通知相关
  notifications: Notification[]
  
  // 模态框状态
  modals: Record<string, boolean>
  
  // 页面状态
  pageTitle: string
  breadcrumbs: Breadcrumb[]
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  duration?: number
  timestamp: number
  read: boolean
}

export interface Breadcrumb {
  label: string
  href?: string
  icon?: string
}

export interface UIActions {
  // 主题相关
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  setDarkMode: (isDark: boolean) => void
  
  // 布局相关
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setSidebarWidth: (width: number) => void
  
  // 语言相关
  setLanguage: (language: Language) => void
  
  // 加载状态
  setGlobalLoading: (loading: boolean, message?: string) => void
  
  // 通知相关
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  removeNotification: (id: string) => void
  markNotificationAsRead: (id: string) => void
  clearAllNotifications: () => void
  
  // 模态框状态
  openModal: (modalId: string) => void
  closeModal: (modalId: string) => void
  toggleModal: (modalId: string) => void
  
  // 页面状态
  setPageTitle: (title: string) => void
  setBreadcrumbs: (breadcrumbs: Breadcrumb[]) => void
}

export type UIStore = UIState & UIActions

// 检测系统主题偏好
const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light'
}

// 应用主题到DOM
const applyTheme = (theme: Theme, isDarkMode: boolean) => {
  if (typeof document !== 'undefined') {
    const root = document.documentElement
    
    if (theme === 'system') {
      const systemTheme = getSystemTheme()
      root.classList.toggle('dark', systemTheme === 'dark')
    } else {
      root.classList.toggle('dark', isDarkMode)
    }
  }
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      // 初始状态
      theme: 'system',
      isDarkMode: false,
      sidebarCollapsed: false,
      sidebarWidth: 256,
      language: 'zh',
      globalLoading: false,
      loadingMessage: '',
      notifications: [],
      modals: {},
      pageTitle: '',
      breadcrumbs: [],

      // 主题相关
      setTheme: (theme) => {
        const isDarkMode = theme === 'dark' || (theme === 'system' && getSystemTheme() === 'dark')
        set({ theme, isDarkMode })
        applyTheme(theme, isDarkMode)
      },

      toggleTheme: () => {
        const { theme } = get()
        const newTheme = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
        get().setTheme(newTheme)
      },

      setDarkMode: (isDarkMode) => {
        set({ isDarkMode })
        applyTheme(get().theme, isDarkMode)
      },

      // 布局相关
      setSidebarCollapsed: (collapsed) => {
        set({ sidebarCollapsed: collapsed })
      },

      toggleSidebar: () => {
        set(state => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setSidebarWidth: (width) => {
        set({ sidebarWidth: Math.max(200, Math.min(400, width)) })
      },

      // 语言相关
      setLanguage: (language) => {
        set({ language })
        if (typeof document !== 'undefined') {
          document.documentElement.lang = language
        }
      },

      // 加载状态
      setGlobalLoading: (loading, message = '') => {
        set({ globalLoading: loading, loadingMessage: message })
      },

      // 通知相关
      addNotification: (notification) => {
        const id = Math.random().toString(36).substr(2, 9)
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: Date.now(),
          read: false
        }

        set(state => ({
          notifications: [newNotification, ...state.notifications]
        }))

        // 自动移除通知
        if (notification.duration !== 0) {
          const duration = notification.duration || 5000
          setTimeout(() => {
            get().removeNotification(id)
          }, duration)
        }
      },

      removeNotification: (id) => {
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== id)
        }))
      },

      markNotificationAsRead: (id) => {
        set(state => ({
          notifications: state.notifications.map(n =>
            n.id === id ? { ...n, read: true } : n
          )
        }))
      },

      clearAllNotifications: () => {
        set({ notifications: [] })
      },

      // 模态框状态
      openModal: (modalId) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: true }
        }))
      },

      closeModal: (modalId) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: false }
        }))
      },

      toggleModal: (modalId) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: !state.modals[modalId] }
        }))
      },

      // 页面状态
      setPageTitle: (title) => {
        set({ pageTitle: title })
        if (typeof document !== 'undefined') {
          document.title = title ? `${title} - AI测试平台` : 'AI测试平台'
        }
      },

      setBreadcrumbs: (breadcrumbs) => {
        set({ breadcrumbs })
      }
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth,
        language: state.language
      })
    }
  )
)

// 监听系统主题变化
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  
  mediaQuery.addEventListener('change', (e) => {
    const { theme, setDarkMode } = useUIStore.getState()
    if (theme === 'system') {
      setDarkMode(e.matches)
    }
  })
}

// 通知工具函数
export const useNotifications = () => {
  const { addNotification, removeNotification, markNotificationAsRead, clearAllNotifications } = useUIStore()
  
  const showSuccess = (title: string, message?: string, duration?: number) => {
    addNotification({ type: 'success', title, message, duration })
  }

  const showError = (title: string, message?: string, duration?: number) => {
    addNotification({ type: 'error', title, message, duration })
  }

  const showWarning = (title: string, message?: string, duration?: number) => {
    addNotification({ type: 'warning', title, message, duration })
  }

  const showInfo = (title: string, message?: string, duration?: number) => {
    addNotification({ type: 'info', title, message, duration })
  }

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeNotification,
    markAsRead: markNotificationAsRead,
    clearAll: clearAllNotifications
  }
}

// 模态框工具函数
export const useModal = (modalId: string) => {
  const isOpen = useUIStore(state => state.modals[modalId] || false)
  const { openModal, closeModal, toggleModal } = useUIStore()

  return {
    isOpen,
    open: () => openModal(modalId),
    close: () => closeModal(modalId),
    toggle: () => toggleModal(modalId)
  }
}