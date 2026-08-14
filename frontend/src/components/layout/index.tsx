import React, { useEffect, useMemo, useState } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileSpreadsheet,
  FolderOpen,
  Home,
  LogOut,
  Menu,
  Moon,
  PlayCircle,
  Settings,
  Shield,
  Sun,
  TestTube,
  Trash2,
  User,
  Users,
  X,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { apiClient } from '@/services/api/client'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

const navGroups = [
  {
    title: '工作台',
    items: [
      { label: '仪表盘', path: '/', icon: Home },
      { label: '项目管理', path: '/projects', icon: FolderOpen, module: 'projects' },
      { label: '任务管理', path: '/tasks', icon: ClipboardList, module: 'tasks' },
      { label: '需求管理', path: '/requirements', icon: ClipboardList, module: 'requirements' },
      { label: '风险管理', path: '/risks', icon: AlertTriangle, module: 'projects' },
      { label: 'AI 助手', path: '/ai-assistant', icon: Bot },
    ],
  },
  {
    title: '测试管理',
    items: [
      { label: '测试概览', path: '/test-manager', icon: TestTube, module: 'testing' },
      { label: '测试计划', path: '/test-manager/test-plans', icon: ClipboardList, module: 'testing' },
      { label: '测试用例', path: '/test-manager/test-cases', icon: ClipboardList, module: 'testing' },
      { label: '执行管理', path: '/test-manager/executions', icon: PlayCircle, module: 'testing' },
      { label: '缺陷管理', path: '/test-manager/defects', icon: AlertTriangle, module: 'defects' },
      { label: '测试报告', path: '/test-manager/reports', icon: FileSpreadsheet, module: 'reports' },
      { label: '性能测试', path: '/test-manager/performance', icon: BarChart3, module: 'testing' },
      { label: '安全测试', path: '/test-manager/security', icon: Shield, module: 'testing' },
    ],
  },
  {
    title: '系统管理',
    items: [
      { label: '用户管理', path: '/users', icon: Users, module: 'users' },
      { label: '角色管理', path: '/roles', icon: Shield, module: 'roles' },
      { label: '系统设置', path: '/settings', icon: Settings, module: 'settings' },
      { label: '配置项', path: '/config', icon: Settings, module: 'settings' },
      { label: '配置分组', path: '/config/groups', icon: FolderOpen, module: 'settings' },
      { label: '审计日志', path: '/config/audits', icon: ClipboardList, module: 'settings' },
      { label: '自动恢复', path: '/auto-recovery', icon: PlayCircle, module: 'testing' },
      { label: '数据统计', path: '/statistics', icon: BarChart3, module: 'reports' },
    ],
  },
]

const pageTitles: Record<string, string> = {
  '/': '仪表盘',
  '/projects': '项目管理',
  '/tasks': '任务管理',
  '/requirements': '需求管理',
  '/risks': '风险管理',
  '/ai-assistant': 'AI 助手',
  '/test-manager': '测试概览',
  '/test-manager/test-plans': '测试计划',
  '/test-manager/test-plans/create': '创建测试计划',
  '/test-manager/test-cases': '测试用例',
  '/test-manager/test-cases/create': '创建测试用例',
  '/test-manager/executions': '执行管理',
  '/test-manager/executions/manual': '手工执行',
  '/test-manager/executions/automation': '自动化执行',
  '/test-manager/defects': '缺陷管理',
  '/test-manager/defects/analytics': '缺陷分析',
  '/test-manager/reports': '测试报告',
  '/test-manager/reports/generate': '生成测试报告',
  '/test-manager/performance': '性能测试',
  '/test-manager/security': '安全测试',
  '/allure-reports': 'Allure 报告',
  '/reports': '报告管理',
  '/auto-recovery': '自动恢复',
  '/statistics': '数据统计',
  '/users': '用户管理',
  '/roles': '角色管理',
  '/settings': '系统设置',
  '/config': '配置项',
  '/config/groups': '配置分组',
  '/config/audits': '审计日志',
  '/meetings': '会议管理',
  '/meetings/create': '新建会议',
  '/profile': '个人资料',
}

const dynamicPageTitleRules: Array<[RegExp, string]> = [
  [/^\/projects\/\d+$/, '项目详情'],
  [/^\/meetings\/create$/, '新建会议'],
  [/^\/meetings\/[^/]+\/edit$/, '编辑会议'],
  [/^\/meetings\/room\/[^/]+$/, '会议室'],
  [/^\/meetings\/join\/[^/]+$/, '加入会议'],
  [/^\/meetings\/recordings\/[^/]+\/player$/, '录制播放'],
  [/^\/meetings\/recordings\/[^/]+$/, '录制详情'],
  [/^\/meetings\/recordings$/, '会议录制'],
  [/^\/meetings\/analytics\/comparison$/, '会议对比'],
  [/^\/meetings\/[^/]+\/analytics\/participation$/, '参与度分析'],
  [/^\/meetings\/[^/]+\/analytics\/summary$/, '会议摘要'],
  [/^\/meetings\/[^/]+\/analytics\/minutes$/, '会议纪要'],
  [/^\/meetings\/[^/]+\/analytics\/actions$/, '行动项'],
  [/^\/meetings\/[^/]+\/analytics\/reports$/, '会议报告'],
  [/^\/meetings\/[^/]+\/analytics$/, '会议分析'],
  [/^\/meetings\/[^/]+\/recordings$/, '会议录制'],
  [/^\/meetings\/[^/]+$/, '会议详情'],
  [/^\/test-manager\/test-plans\/\d+\/edit$/, '编辑测试计划'],
  [/^\/test-manager\/test-plans\/\d+$/, '测试计划详情'],
  [/^\/test-manager\/test-cases\/\d+\/edit$/, '编辑测试用例'],
  [/^\/test-manager\/test-cases\/\d+$/, '测试用例详情'],
  [/^\/test-manager\/executions\/manual\/\d+$/, '手工执行'],
  [/^\/test-manager\/executions\/[^/]+$/, '执行详情'],
]

const defaultCollapsedSidebarPaths = ['/ai-assistant', '/test-manager/test-cases/create']

interface SystemNotification {
  id: number
  title: string
  content?: string
  category: string
  is_read: boolean
  created_at?: string
}

const notificationCategoryLabels: Record<string, string> = {
  system: '系统通知',
  task: '任务通知',
  defect: '缺陷通知',
  requirement: '需求通知',
  meeting: '会议通知',
  report: '报告通知',
}

const AppLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAuthenticated, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { resolvedTheme, toggleTheme } = useTheme()
  const darkMode = resolvedTheme === 'dark'
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [messagePanelOpen, setMessagePanelOpen] = useState(false)
  const [notifications, setNotifications] = useState<SystemNotification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [selectedNotification, setSelectedNotification] = useState<SystemNotification | null>(null)
  const [deletingNotification, setDeletingNotification] = useState<SystemNotification | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'unread' | 'read'>('unread')
  const [accessModules, setAccessModules] = useState<Record<string, boolean> | null>(null)

  const currentTitle = useMemo(() => {
    const exact = pageTitles[location.pathname]
    if (exact) return exact
    const dynamicMatch = dynamicPageTitleRules.find(([pattern]) => pattern.test(location.pathname))
    if (dynamicMatch) return dynamicMatch[1]
    const match = Object.keys(pageTitles)
      .filter((path) => path !== '/' && location.pathname.startsWith(path))
      .sort((a, b) => b.length - a.length)[0]
    return match ? pageTitles[match] : '工作台'
  }, [location.pathname])

  // theme managed by useTheme hook

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [isAuthenticated, navigate])

  useEffect(() => {
    if (defaultCollapsedSidebarPaths.some((path) => location.pathname.startsWith(path))) {
      setSidebarCollapsed(true)
    }
  }, [location.pathname])

  useEffect(() => {
    if (!isAuthenticated) {
      setAccessModules(null)
      return
    }

    let cancelled = false
    apiClient
      .get('/dashboard/access')
      .then((response) => {
        if (cancelled) return
        const payload = response.data?.data || response.data
        setAccessModules(payload?.modules || {})
      })
      .catch(() => {
        if (!cancelled) setAccessModules({})
      })

    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  const loadNotifications = async () => {
    if (!isAuthenticated) {
      setNotifications([])
      setUnreadCount(0)
      return
    }

    try {
      const response = await apiClient.get('/notifications', { params: { limit: 100 } })
      const payload = response.data || {}
      setNotifications(payload.notifications || [])
      setUnreadCount(Number(payload.unread_count || 0))
    } catch {
      setNotifications([])
      setUnreadCount(0)
    }
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([])
      setUnreadCount(0)
      return
    }

    let cancelled = false
    const refresh = async () => {
      if (!cancelled) await loadNotifications()
    }

    refresh()
    const timer = window.setInterval(refresh, 30000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (notificationOpen || messagePanelOpen) {
      loadNotifications()
    }
  }, [notificationOpen, messagePanelOpen])

  const markAllNotificationsRead = async () => {
    try {
      await apiClient.patch('/notifications/read-all')
      await loadNotifications()
    } catch {
      // Request interceptor already shows the user-facing error.
    }
  }

  const openNotificationDetail = (notification: SystemNotification) => {
    setSelectedNotification(notification)
    setNotificationOpen(false)
    if (!notification.is_read) {
      setNotifications((previous) => previous.map((item) => (item.id === notification.id ? { ...item, is_read: true } : item)))
      setUnreadCount((count) => Math.max(0, count - 1))
      apiClient
        .patch(`/notifications/${notification.id}/read`)
        .then(loadNotifications)
        .catch(() => {
          // Request interceptor already shows the user-facing error.
        })
    }
  }

  const deleteNotification = async (notification: SystemNotification) => {
    try {
      await apiClient.delete(`/notifications/${notification.id}`)
      setDeletingNotification(null)
      if (selectedNotification?.id === notification.id) {
        setSelectedNotification(null)
      }
      await loadNotifications()
    } catch {
      // Request interceptor already shows the user-facing error.
    }
  }

  const filteredNotifications = useMemo(() => {
    if (activeTab === 'unread') return notifications.filter((item) => !item.is_read)
    if (activeTab === 'read') return notifications.filter((item) => item.is_read)
    return notifications
  }, [notifications, activeTab])

  const visibleNavGroups = useMemo(() => {
    const canViewItem = (item: { module?: string }) => {
      if (!item.module) return true
      if (!accessModules) return false
      return Boolean(accessModules[item.module])
    }

    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter(canViewItem),
      }))
      .filter((group) => group.items.length > 0)
  }, [accessModules])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white text-slate-700 shadow-sm transition-[width,transform] dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200 lg:translate-x-0 ${
          sidebarCollapsed ? 'lg:w-16' : 'lg:w-48'
        } ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <button
          type="button"
          className="absolute -right-3 top-5 z-50 hidden h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white lg:flex"
          onClick={() => setSidebarCollapsed((value) => !value)}
          aria-label={sidebarCollapsed ? '展开菜单' : '收起菜单'}
          title={sidebarCollapsed ? '展开菜单' : '收起菜单'}
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
        <div className={`flex h-14 items-center justify-between border-b border-slate-200 px-3 dark:border-slate-800 ${sidebarCollapsed ? 'lg:justify-center lg:px-2' : ''}`}>
          <Link to="/" className={`truncate text-sm font-semibold text-slate-900 dark:text-slate-100 ${sidebarCollapsed ? 'lg:hidden' : ''}`}>
            AI 测试
          </Link>
          <Link
            to="/"
            className={`hidden h-10 w-10 items-center justify-center rounded-md bg-blue-600 text-sm font-semibold text-white ${
              sidebarCollapsed ? 'lg:flex' : 'lg:hidden'
            }`}
            aria-label="AI 测试管理系统"
          >
            AI
          </Link>
          <button className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="关闭菜单">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className={`h-[calc(100vh-3.5rem)] overflow-y-auto ${sidebarCollapsed ? 'space-y-3 p-2 lg:px-2' : 'space-y-3 p-2'}`}>
          {visibleNavGroups.map((group) => (
            <div key={group.title}>
              <div className={`mb-1 px-2 text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-500 ${sidebarCollapsed ? 'lg:hidden' : ''}`}>{group.title}</div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/' || item.path === '/test-manager'}
                      onClick={() => setSidebarOpen(false)}
                      title={sidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `flex items-center rounded-md px-2 py-1.5 text-sm transition-colors ${
                          sidebarCollapsed ? 'lg:justify-center lg:px-0 lg:py-2.5' : ''
                        } ${
                          isActive
                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-200'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
                        }`
                      }
                    >
                      <Icon className={`mr-2 h-4 w-4 shrink-0 ${sidebarCollapsed ? 'lg:mr-0' : ''}`} />
                      <span className={`truncate ${sidebarCollapsed ? 'lg:hidden' : ''}`}>{item.label}</span>
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {sidebarOpen && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setSidebarOpen(false)} />}

      <div className={`transition-[padding] ${sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-48'}`}>
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/95 px-4 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
          <div className="flex min-w-0 items-center gap-3">
            <button className="rounded-md p-2 hover:bg-gray-100 dark:hover:bg-slate-800 lg:hidden dark:bg-gray-800" onClick={() => setSidebarOpen(true)} aria-label="打开菜单">
              <Menu className="h-5 w-5" />
            </button>
            <button
              className="hidden rounded-md p-2 hover:bg-gray-100 dark:hover:bg-slate-800 lg:inline-flex dark:bg-gray-800"
              onClick={() => setSidebarCollapsed((value) => !value)}
              aria-label={sidebarCollapsed ? '展开菜单' : '收起菜单'}
              title={sidebarCollapsed ? '展开菜单' : '收起菜单'}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-base font-semibold">{currentTitle}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800 dark:bg-gray-800/50 dark:hover:bg-gray-800"
              title={darkMode ? '切换到浅色主题' : '切换到深色主题'}
            >
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              <span className="hidden sm:inline">{darkMode ? '浅色' : '深色'}</span>
            </button>

            <div className="relative">
              <button
                className="relative inline-flex h-9 w-9 items-center justify-center rounded-md border hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800 dark:bg-gray-800/50 dark:hover:bg-gray-800"
                title="消息通知"
                onClick={() => setNotificationOpen((value) => !value)}
              >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 px-1 text-[10px] leading-none text-white shadow-sm">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </button>
              {notificationOpen && (
                <div className="absolute right-0 mt-2 w-72 rounded-md border bg-white p-4 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-medium">消息通知</span>
                    <div className="flex items-center gap-2">
                      {unreadCount > 0 && (
                        <button className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400" onClick={markAllNotificationsRead}>
                          全部已读
                        </button>
                      )}
                      <button
                        className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                        onClick={() => {
                          setNotificationOpen(false)
                          setActiveTab('unread')
                          setMessagePanelOpen(true)
                        }}
                      >
                        管理
                      </button>
                      <button className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:text-gray-300" onClick={() => setNotificationOpen(false)}>
                        关闭
                      </button>
                    </div>
                  </div>
                  <div className={`${notifications.length === 0 ? '' : 'hidden'} rounded-md bg-gray-50 px-3 py-6 text-center text-sm text-gray-500 dark:bg-slate-800 dark:text-gray-400`}>
                    暂无新的通知
                  </div>
                  {notifications.length > 0 && (
                    <div className="max-h-80 space-y-2 overflow-y-auto">
                      {notifications.map((notification) => (
                        <button
                          key={notification.id}
                          type="button"
                          className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:hover:border-blue-500/50 dark:hover:bg-slate-700 ${
                            notification.is_read ? 'bg-white dark:bg-slate-900' : 'bg-blue-50 dark:bg-slate-800'
                          }`}
                          onClick={() => openNotificationDetail(notification)}
                          title="点击查看消息详情"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="font-medium">{notification.title}</div>
                            {!notification.is_read && <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[11px] text-blue-700 dark:bg-blue-500/15 dark:text-blue-200">未读</span>}
                          </div>
                          {notification.content && (
                            <div className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">{notification.content}</div>
                          )}
                          {notification.created_at && (
                            <div className="mt-1 text-[11px] text-gray-400 dark:text-gray-500">{new Date(notification.created_at).toLocaleString()}</div>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <Link
              to="/profile"
              className="hidden h-9 items-center gap-2 rounded-md border px-3 hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800 sm:flex dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <User className="h-4 w-4" />
              <span className="max-w-32 truncate text-sm">{user?.real_name || user?.nickname || user?.username || '用户'}</span>
              <ChevronDown className="h-4 w-4 text-gray-400 dark:text-gray-500" />
            </Link>

            <button
              onClick={handleLogout}
              className="inline-flex h-9 items-center gap-1 rounded-md border px-3 text-sm hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800 dark:bg-gray-800/50 dark:hover:bg-gray-800"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">退出</span>
            </button>
          </div>
        </header>

        <main className="p-3 sm:p-4">
          <Outlet />
        </main>
      </div>

      <Dialog open={messagePanelOpen} onOpenChange={(open) => !open && setMessagePanelOpen(false)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                消息管理
                {unreadCount > 0 && (
                  <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-normal text-white">{unreadCount} 条未读</span>
                )}
              </DialogTitle>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400" onClick={markAllNotificationsRead}>
                    全部已读
                  </button>
                )}
                <button
                  type="button"
                  className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  onClick={() => setMessagePanelOpen(false)}
                  aria-label="关闭"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          </DialogHeader>

          <div className="mb-3 flex space-x-1 border-b border-slate-200 dark:border-slate-700">
            {(([['all', '全部'], ['unread', '未读'], ['read', '已读']] as const).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={`-mb-px border-b-2 px-3 py-1.5 text-sm transition-colors ${
                  activeTab === value
                    ? 'border-blue-600 font-medium text-blue-600 dark:border-blue-400 dark:text-blue-300'
                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
                onClick={() => setActiveTab(value)}
              >
                {label}
                {value === 'unread' && unreadCount > 0 ? ` (${unreadCount})` : ''}
              </button>
            )))}
          </div>

          <div className="max-h-[60vh] space-y-2 overflow-y-auto">
            {filteredNotifications.length === 0 ? (
              <div className="rounded-md bg-gray-50 px-3 py-8 text-center text-sm text-gray-500 dark:bg-slate-800 dark:text-gray-400">
                {activeTab === 'unread' ? '暂无未读消息' : activeTab === 'read' ? '暂无已读消息' : '暂无消息'}
              </div>
            ) : (
              filteredNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex items-start gap-2 rounded-md border px-3 py-2 dark:border-slate-700 ${
                    notification.is_read ? 'bg-white dark:bg-slate-900' : 'bg-blue-50 dark:bg-slate-800'
                  }`}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => openNotificationDetail(notification)}
                    title="点击查看消息详情"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate text-sm font-medium">{notification.title}</div>
                      {!notification.is_read && <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[11px] text-blue-700 dark:bg-blue-500/15 dark:text-blue-200">未读</span>}
                    </div>
                    {notification.content && (
                      <div className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">{notification.content}</div>
                    )}
                    {notification.created_at && (
                      <div className="mt-1 text-[11px] text-gray-400 dark:text-gray-500">{new Date(notification.created_at).toLocaleString()}</div>
                    )}
                  </button>
                  <button
                    type="button"
                    className="rounded-md p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                    title="删除消息"
                    onClick={() => setDeletingNotification(notification)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deletingNotification !== null}
        title="删除消息"
        description={deletingNotification ? `确定要删除消息「${deletingNotification.title}」吗？删除后将不再显示。` : ''}
        confirmText="删除"
        cancelText="取消"
        variant="destructive"
        onConfirm={() => {
          if (deletingNotification) deleteNotification(deletingNotification)
        }}
        onCancel={() => setDeletingNotification(null)}
      />

      <Dialog open={selectedNotification !== null} onOpenChange={(open) => !open && setSelectedNotification(null)}>
        <DialogContent className="max-w-lg">
          {selectedNotification && (
            <>
              <DialogHeader>
                <div className="flex items-start justify-between gap-3">
                  <DialogTitle>{selectedNotification.title}</DialogTitle>
                  <button
                    type="button"
                    className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                    onClick={() => setSelectedNotification(null)}
                    aria-label="关闭"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">{notificationCategoryLabels[selectedNotification.category] || selectedNotification.category}</span>
                  {selectedNotification.created_at && <span>{new Date(selectedNotification.created_at).toLocaleString()}</span>}
                  <span className={selectedNotification.is_read ? 'text-slate-400 dark:text-slate-500' : 'text-blue-600 dark:text-blue-300'}>
                    {selectedNotification.is_read ? '已读' : '未读'}
                  </span>
                </div>
                <div className="whitespace-pre-wrap break-words text-slate-700 dark:text-slate-200">
                  {selectedNotification.content || '该消息没有更多内容。'}
                </div>
              </div>
              <DialogFooter>
                <button
                  type="button"
                  className="rounded-md border px-3 py-1.5 text-sm transition hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  onClick={() => setSelectedNotification(null)}
                >
                  关闭
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default AppLayout
