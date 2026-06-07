import React, { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/services/api/client'

type RecentActivity = {
  type?: string
  title?: string | null
  status?: string | null
  occurred_at?: string | null
}

type StatisticsState = {
  users: {
    total: number
    active: number
    inactive: number
    locked: number
    newThisMonth: number
  }
  roles: {
    total: number
    system: number
    custom: number
    active: number
  }
  sessions: {
    online: number
    todayLogins: number
    weeklyLogins: number
    monthlyLogins: number
  }
  security: {
    failedLogins: number
    lockedAccounts: number
    securityEvents: number
    lastSecurityEvent: string | null
  }
}

const defaultStats: StatisticsState = {
  users: {
    total: 0,
    active: 0,
    inactive: 0,
    locked: 0,
    newThisMonth: 0
  },
  roles: {
    total: 0,
    system: 0,
    custom: 0,
    active: 0
  },
  sessions: {
    online: 0,
    todayLogins: 0,
    weeklyLogins: 0,
    monthlyLogins: 0
  },
  security: {
    failedLogins: 0,
    lockedAccounts: 0,
    securityEvents: 0,
    lastSecurityEvent: null
  }
}

const typeLabels: Record<string, string> = {
  project: '项目',
  requirement: '需求',
  test_case: '测试用例',
  defect: '缺陷',
  meeting: '会议'
}

const statusLabels: Record<string, string> = {
  PLANNING: '规划中',
  IN_PROGRESS: '进行中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  ACTIVE: '启用',
  PASSED: '通过',
  FAILED: '失败',
  NEW: '新建',
  RESOLVED: '已解决',
  CLOSED: '已关闭',
  SCHEDULED: '已安排',
  todo: '待处理',
  in_progress: '进行中',
  completed: '已完成'
}

const percent = (value: number, total: number) => {
  if (total <= 0) return '0.0%'
  return `${((value / total) * 100).toFixed(1)}%`
}

const Statistics: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<StatisticsState>(defaultStats)
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([])
  const [error, setError] = useState('')
  const [timeRange, setTimeRange] = useState('7d')

  const loadStats = useCallback(async () => {
    setIsLoading(true)
    setError('')

    try {
      const [summaryResponse, roleStatsResult] = await Promise.allSettled([
        apiClient.get('/dashboard/summary'),
        apiClient.get('/roles/stats')
      ])

      if (summaryResponse.status === 'rejected') {
        throw summaryResponse.reason
      }

      const summary = summaryResponse.value.data?.data || summaryResponse.value.data || {}
      const roleStats = roleStatsResult.status === 'fulfilled'
        ? roleStatsResult.value.data?.data || roleStatsResult.value.data || {}
        : {}
      const userTotal = Number(summary.users?.total || 0)
      const userActive = Number(summary.users?.active || 0)
      const userLocked = Number(summary.users?.locked || 0)

      setStats({
        users: {
          total: userTotal,
          active: userActive,
          inactive: Math.max(userTotal - userActive - userLocked, 0),
          locked: userLocked,
          newThisMonth: 0
        },
        roles: {
          total: Number(roleStats.total_roles ?? summary.users?.roles ?? 0),
          system: Number(roleStats.system_roles || 0),
          custom: Number(roleStats.custom_roles || 0),
          active: Number(roleStats.active_roles || 0)
        },
        sessions: {
          online: 0,
          todayLogins: Number(summary.users?.today_logins || 0),
          weeklyLogins: 0,
          monthlyLogins: 0
        },
        security: {
          failedLogins: 0,
          lockedAccounts: userLocked,
          securityEvents: 0,
          lastSecurityEvent: null
        }
      })
      setRecentActivities(summary.recent_activity || [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '统计数据加载失败')
      setStats(defaultStats)
      setRecentActivities([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats, timeRange])

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '无'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  const StatCard = ({ title, value, subtitle, color = 'blue', icon }: {
    title: string
    value: string | number
    subtitle?: string
    color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
    icon?: string
  }) => {
    const colorClasses = {
      blue: 'bg-blue-50 border-blue-200 text-blue-800',
      green: 'bg-green-50 border-green-200 text-green-800',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      red: 'bg-red-50 border-red-200 text-red-800',
      purple: 'bg-purple-50 border-purple-200 text-purple-800'
    }

    return (
      <div className={`p-6 rounded-lg border ${colorClasses[color]}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium opacity-75">{title}</p>
            <p className="text-3xl font-bold mt-2">{value}</p>
            {subtitle && <p className="text-sm opacity-75 mt-1">{subtitle}</p>}
          </div>
          {icon && <div className="text-3xl opacity-50">{icon}</div>}
        </div>
      </div>
    )
  }

  const ChartPlaceholder = ({ title, height = 300 }: { title: string; height?: number }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">{title}</h3>
      <div 
        className="bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center"
        style={{ height: `${height}px` }}
      >
        <div className="text-center text-gray-500 dark:text-gray-400">
          <div className="text-4xl mb-2">📊</div>
          <p>图表数据加载中...</p>
          <p className="text-sm mt-1">时间范围: {timeRange === '7d' ? '最近7天' : timeRange === '30d' ? '最近30天' : '最近90天'}</p>
        </div>
      </div>
    </div>
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            数据统计
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            系统运行状态和用户活动统计
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <select 
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
          </select>
          <button 
            onClick={loadStats}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
          >
            {isLoading ? '刷新中...' : '刷新数据'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 用户统计卡片 */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">用户统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <StatCard
            title="总用户数"
            value={stats.users.total}
            icon="👥"
            color="blue"
          />
          <StatCard
            title="活跃用户"
            value={stats.users.active}
            subtitle={percent(stats.users.active, stats.users.total)}
            icon="✅"
            color="green"
          />
          <StatCard
            title="非活跃用户"
            value={stats.users.inactive}
            subtitle={percent(stats.users.inactive, stats.users.total)}
            icon="⏸️"
            color="yellow"
          />
          <StatCard
            title="锁定用户"
            value={stats.users.locked}
            subtitle={percent(stats.users.locked, stats.users.total)}
            icon="🔒"
            color="red"
          />
          <StatCard
            title="本月新增"
            value={stats.users.newThisMonth}
            subtitle="后端暂未提供"
            icon="🆕"
            color="purple"
          />
        </div>
      </div>

      {/* 角色统计卡片 */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">角色统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="总角色数"
            value={stats.roles.total}
            icon="🎭"
            color="blue"
          />
          <StatCard
            title="系统角色"
            value={stats.roles.system}
            subtitle="内置角色"
            icon="⚙️"
            color="green"
          />
          <StatCard
            title="自定义角色"
            value={stats.roles.custom}
            subtitle="用户创建"
            icon="🎨"
            color="purple"
          />
          <StatCard
            title="启用角色"
            value={stats.roles.active}
            subtitle={percent(stats.roles.active, stats.roles.total)}
            icon="✅"
            color="green"
          />
        </div>
      </div>

      {/* 会话统计卡片 */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">会话统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="在线用户"
            value={stats.sessions.online}
            subtitle="后端暂未提供"
            icon="🟢"
            color="green"
          />
          <StatCard
            title="今日登录"
            value={stats.sessions.todayLogins}
            subtitle="登录次数"
            icon="📅"
            color="blue"
          />
          <StatCard
            title="本周登录"
            value={stats.sessions.weeklyLogins}
            subtitle="后端暂未提供"
            icon="📊"
            color="purple"
          />
          <StatCard
            title="本月登录"
            value={stats.sessions.monthlyLogins}
            subtitle="后端暂未提供"
            icon="📈"
            color="green"
          />
        </div>
      </div>

      {/* 安全统计卡片 */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">安全统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="登录失败"
            value={stats.security.failedLogins}
            subtitle="后端暂未提供"
            icon="❌"
            color="red"
          />
          <StatCard
            title="锁定账户"
            value={stats.security.lockedAccounts}
            subtitle="当前锁定"
            icon="🔐"
            color="red"
          />
          <StatCard
            title="安全事件"
            value={stats.security.securityEvents}
            subtitle="后端暂未提供"
            icon="⚠️"
            color="yellow"
          />
          <StatCard
            title="最后事件"
            value={formatDate(stats.security.lastSecurityEvent)}
            subtitle="安全事件时间"
            icon="🕐"
            color="blue"
          />
        </div>
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPlaceholder title="用户活动趋势" />
        <ChartPlaceholder title="登录统计" />
        <ChartPlaceholder title="角色分布" />
        <ChartPlaceholder title="安全事件趋势" />
      </div>

      {/* 详细数据表格 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">最近活动</h3>
        </div>
        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">时间</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">用户</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">操作</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">状态</th>
                </tr>
              </thead>
              <tbody>
                {(recentActivities.length ? recentActivities : []).map((activity, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{formatDate(activity.occurred_at || null)}</td>
                    <td className="py-3 px-4 font-medium">{typeLabels[activity.type || ''] || activity.type || '-'}</td>
                    <td className="py-3 px-4">{activity.title || '未命名记录'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        ['COMPLETED', 'PASSED', 'RESOLVED', 'CLOSED', 'completed'].includes(activity.status || '')
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {statusLabels[activity.status || ''] || activity.status || '无状态'}
                      </span>
                    </td>
                  </tr>
                ))}
                {!recentActivities.length && (
                  <tr>
                    <td className="py-8 px-4 text-center text-gray-500" colSpan={4}>
                      暂无最近活动
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Statistics
