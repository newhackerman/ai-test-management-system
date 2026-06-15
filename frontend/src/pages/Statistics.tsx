import React, { useCallback, useEffect, useState } from 'react'
import { Activity, RefreshCw, ShieldAlert, UserCog, Users } from 'lucide-react'
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

  const StatCard = ({ title, value, subtitle, tone = 'blue', icon: Icon }: {
    title: string
    value: string | number
    subtitle?: string
    tone?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
    icon: React.ElementType
  }) => {
    const colorClasses = {
      blue: 'text-blue-600',
      green: 'text-green-600',
      yellow: 'text-amber-600',
      red: 'text-red-600',
      purple: 'text-purple-600'
    }

    return (
      <div className="rounded-lg border bg-card p-3 text-card-foreground">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs text-muted-foreground">{title}</p>
            <p className={`mt-1 text-2xl font-bold leading-7 ${colorClasses[tone]}`}>{value}</p>
            {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <Icon className={`h-4 w-4 ${colorClasses[tone]}`} />
        </div>
      </div>
    )
  }

  const DetailPanel = ({ title, items }: { title: string; items: Array<{ label: string; value: number | string; hint?: string; percent?: string }> }) => (
    <div className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 text-base font-semibold">{title}</div>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="text-muted-foreground">{item.label}</span>
              <span className="font-medium">{item.value}</span>
            </div>
            {item.percent && (
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary" style={{ width: item.percent }} />
              </div>
            )}
            {item.hint && <div className="mt-1 text-xs text-muted-foreground">{item.hint}</div>}
          </div>
        ))}
      </div>
    </div>
  )

  if (isLoading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select 
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm focus:ring-2 focus:ring-ring"
          >
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
          </select>
          <button 
            onClick={loadStats}
            disabled={isLoading}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <RefreshCw className="h-4 w-4" />
            {isLoading ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <StatCard title="总用户数" value={stats.users.total} icon={Users} />
        <StatCard title="活跃用户" value={stats.users.active} subtitle={percent(stats.users.active, stats.users.total)} icon={Activity} tone="green" />
        <StatCard title="锁定用户" value={stats.users.locked} subtitle={percent(stats.users.locked, stats.users.total)} icon={ShieldAlert} tone="red" />
        <StatCard title="总角色数" value={stats.roles.total} icon={UserCog} tone="purple" />
        <StatCard title="今日登录" value={stats.sessions.todayLogins} subtitle="登录次数" icon={Activity} tone="blue" />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
        <DetailPanel
          title="用户状态"
          items={[
            { label: '活跃用户', value: stats.users.active, percent: percent(stats.users.active, stats.users.total) },
            { label: '非活跃用户', value: stats.users.inactive, percent: percent(stats.users.inactive, stats.users.total) },
            { label: '锁定用户', value: stats.users.locked, percent: percent(stats.users.locked, stats.users.total) },
            { label: '本月新增', value: stats.users.newThisMonth, hint: '后端暂未提供该统计' }
          ]}
        />
        <DetailPanel
          title="角色状态"
          items={[
            { label: '系统角色', value: stats.roles.system, hint: '内置角色' },
            { label: '自定义角色', value: stats.roles.custom, hint: '用户创建' },
            { label: '启用角色', value: stats.roles.active, percent: percent(stats.roles.active, stats.roles.total) }
          ]}
        />
        <DetailPanel
          title="登录与会话"
          items={[
            { label: '在线用户', value: stats.sessions.online, hint: '后端暂未提供该统计' },
            { label: '今日登录', value: stats.sessions.todayLogins },
            { label: '本周登录', value: stats.sessions.weeklyLogins, hint: '后端暂未提供该统计' },
            { label: '本月登录', value: stats.sessions.monthlyLogins, hint: '后端暂未提供该统计' }
          ]}
        />
        <DetailPanel
          title="安全概览"
          items={[
            { label: '登录失败', value: stats.security.failedLogins, hint: '后端暂未提供该统计' },
            { label: '锁定账户', value: stats.security.lockedAccounts },
            { label: '安全事件', value: stats.security.securityEvents, hint: '后端暂未提供该统计' },
            { label: '最后事件', value: formatDate(stats.security.lastSecurityEvent) }
          ]}
        />
      </div>

      <div className="rounded-lg border bg-card text-card-foreground">
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div>
            <h3 className="text-base font-semibold">最近活动</h3>
            <p className="text-xs text-muted-foreground">展示项目、需求、用例、缺陷和会议相关动态</p>
          </div>
          <span className="text-xs text-muted-foreground">共 {recentActivities.length} 条</span>
        </div>
        <div className="p-4">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-3 py-2 text-left text-sm font-medium text-foreground">时间</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-foreground">类型</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-foreground">内容</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-foreground">状态</th>
                </tr>
              </thead>
              <tbody>
                {(recentActivities.length ? recentActivities : []).map((activity, index) => (
                  <tr key={index} className="border-b hover:bg-muted/50">
                    <td className="px-3 py-2 text-sm text-muted-foreground">{formatDate(activity.occurred_at || null)}</td>
                    <td className="px-3 py-2 text-sm font-medium">{typeLabels[activity.type || ''] || activity.type || '-'}</td>
                    <td className="px-3 py-2 text-sm">{activity.title || '未命名记录'}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-1 text-xs ${
                        ['COMPLETED', 'PASSED', 'RESOLVED', 'CLOSED', 'completed'].includes(activity.status || '')
                          ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                      }`}>
                        {statusLabels[activity.status || ''] || activity.status || '无状态'}
                      </span>
                    </td>
                  </tr>
                ))}
                {!recentActivities.length && (
                  <tr>
                    <td className="px-4 py-8 text-center text-sm text-muted-foreground" colSpan={4}>
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
