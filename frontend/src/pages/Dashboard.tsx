import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  BarChart3,
  Briefcase,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  FileText,
  ListChecks,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { apiClient } from '@/services/api/client'
import { cn } from '@/lib/utils'

type DistributionItem = {
  name: string
  count: number
}

type DataSource = {
  table: string
  available: boolean
  note?: string | null
}

type RecentActivity = {
  type: 'project' | 'requirement' | 'test_case' | 'defect' | 'meeting'
  title?: string | null
  status?: string | null
  occurred_at?: string | null
  link?: string | null
}

type DashboardSummary = {
  generated_at: string
  user: {
    display_name?: string
  }
  access?: {
    is_superuser: boolean
    permissions: string[]
    roles: string[]
    modules: Record<string, boolean>
  }
  users: {
    total: number
    active: number
    locked: number
    today_logins: number
    roles: number
  }
  projects: {
    total: number
    active: number
    completed: number
    overdue: number
    high_risk: number
    avg_progress: number
    status_distribution: DistributionItem[]
  }
  requirements: {
    total: number
    active: number
    completed: number
    overdue: number
    completion_rate: number
    status_distribution: DistributionItem[]
  }
  tasks: {
    total: number
    open: number
    completed: number
    overdue: number
    completion_rate: number
    status_distribution: DistributionItem[]
  }
  testing: {
    plans_total: number
    plans_active: number
    cases_total: number
    cases_active: number
    executions_total: number
    executions_today: number
    passed_executions: number
    pass_rate: number
    case_status_distribution: DistributionItem[]
    execution_status_distribution: DistributionItem[]
  }
  defects: {
    total: number
    open: number
    high_priority_open: number
    resolved: number
    resolution_rate: number
    status_distribution: DistributionItem[]
  }
  meetings: {
    total: number
    today: number
    upcoming: number
    running: number
    status_distribution: DistributionItem[]
  }
  reports: {
    total: number
    completed: number
    failed: number
  }
  recent_activity: RecentActivity[]
  data_sources: DataSource[]
}

const statusLabels: Record<string, string> = {
  PLANNING: '规划中',
  IN_PROGRESS: '进行中',
  ON_HOLD: '暂停',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  ARCHIVED: '已归档',
  DRAFT: '草稿',
  PENDING_REVIEW: '待评审',
  REVIEWING: '评审中',
  NEEDS_REVISION: '需修改',
  APPROVED: '已批准',
  IN_DEVELOPMENT: '开发中',
  TESTING: '测试中',
  TEST_FAILED: '测试未通过',
  DEPLOYED: '已部署',
  CLOSED: '已关闭',
  ACTIVE: '启用',
  TODO: '待办',
  ASSIGNED: '已分配',
  REVIEW: '评审',
  DEPRECATED: '已废弃',
  NOT_EXECUTED: '未执行',
  PASSED: '通过',
  FAILED: '失败',
  BLOCKED: '阻塞',
  SKIPPED: '跳过',
  NEW: '新建',
  RESOLVED: '已解决',
  VERIFIED: '已验证',
  REOPENED: '重新打开',
  REJECTED: '已拒绝',
  SCHEDULED: '已安排',
  POSTPONED: '已延期',
  todo: '待处理',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
  on_hold: '暂停',
}

const typeLabels: Record<RecentActivity['type'], string> = {
  project: '项目',
  requirement: '需求',
  test_case: '用例',
  defect: '缺陷',
  meeting: '会议',
}

const formatNumber = (value?: number) => Number(value || 0).toLocaleString('zh-CN')

const clampPercent = (value?: number) => Math.max(0, Math.min(100, Number(value || 0)))

const formatPercent = (value?: number) => `${clampPercent(value).toFixed(clampPercent(value) % 1 === 0 ? 0 : 1)}%`

const formatTime = (value?: string | null) => {
  if (!value) return '暂无时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '暂无时间'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const Dashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadSummary = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const response = await apiClient.get('/dashboard/summary')
      const payload = response.data?.data || response.data
      setSummary(payload)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '仪表盘数据加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSummary()
  }, [loadSummary])

  const canView = useCallback(
    (module: string) => {
      if (!summary?.access?.modules) return true
      return Boolean(summary.access.modules[module])
    },
    [summary],
  )

  const keyMetrics = useMemo(
    () => [
      {
        module: 'projects',
        title: '进行中项目',
        value: summary?.projects.active,
        helper: `总项目 ${formatNumber(summary?.projects.total)}，逾期 ${formatNumber(summary?.projects.overdue)}`,
        icon: Briefcase,
        tone: 'bg-blue-50 text-blue-700',
        link: '/projects',
      },
      {
        module: 'defects',
        title: '未关闭缺陷',
        value: summary?.defects.open,
        helper: `高优先级 ${formatNumber(summary?.defects.high_priority_open)}，总缺陷 ${formatNumber(summary?.defects.total)}`,
        icon: AlertTriangle,
        tone: 'bg-red-50 text-red-700',
        link: '/test-manager/defects',
      },
      {
        module: 'testing',
        title: '测试通过率',
        value: summary ? formatPercent(summary.testing.pass_rate) : undefined,
        helper: `执行总数 ${formatNumber(summary?.testing.executions_total)}，今日执行 ${formatNumber(summary?.testing.executions_today)}`,
        icon: ClipboardCheck,
        tone: 'bg-emerald-50 text-emerald-700',
        link: '/test-manager/executions',
      },
      {
        module: 'tasks',
        title: '待办任务',
        value: summary?.tasks.open,
        helper: `逾期 ${formatNumber(summary?.tasks.overdue)}，完成率 ${formatPercent(summary?.tasks.completion_rate)}`,
        icon: ListChecks,
        tone: 'bg-amber-50 text-amber-700',
        link: '/tasks',
      },
      {
        module: 'requirements',
        title: '活跃需求',
        value: summary?.requirements.active,
        helper: `总需求 ${formatNumber(summary?.requirements.total)}，完成率 ${formatPercent(summary?.requirements.completion_rate)}`,
        icon: FileText,
        tone: 'bg-indigo-50 text-indigo-700',
        link: '/requirements',
      },
      {
        module: 'meetings',
        title: '今日会议',
        value: summary?.meetings.today,
        helper: `待开始 ${formatNumber(summary?.meetings.upcoming)}，进行中 ${formatNumber(summary?.meetings.running)}`,
        icon: CalendarDays,
        tone: 'bg-cyan-50 text-cyan-700',
        link: '/meetings?date=today',
      },
    ].filter((metric) => canView(metric.module)),
    [summary, canView],
  )


  const hasBusinessPanel = canView('projects') || canView('requirements') || canView('tasks')
  const hasQualityPanel = canView('testing') || canView('defects') || canView('reports')
  const hasTeamPanel = canView('users') || canView('roles') || canView('meetings') || canView('reports')
  const hasAnyModule = !summary?.access?.modules || Object.values(summary.access.modules).some(Boolean)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">仪表盘</h1>
          {summary?.generated_at && (
            <p className="mt-1 text-sm text-gray-500">更新时间：{formatTime(summary.generated_at)}</p>
          )}
        </div>
        <Button type="button" variant="outline" onClick={loadSummary} disabled={loading} className="w-fit">
          <RefreshCw className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
          刷新
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !hasAnyModule && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          当前账号没有可展示的业务模块权限，请联系管理员分配角色或权限。
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-4">
        {keyMetrics.map((metric) => (
          <Link key={metric.title} to={metric.link} className="block">
            <Card className="h-full transition-colors hover:bg-gray-50">
              <CardContent className="flex h-full items-start justify-between gap-4 p-5">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-600">{metric.title}</p>
                  <p className="mt-2 text-3xl font-bold text-gray-900">
                    {loading ? '...' : typeof metric.value === 'number' ? formatNumber(metric.value) : metric.value || '0'}
                  </p>
                  <p className="mt-2 text-sm text-gray-500">{metric.helper}</p>
                </div>
                <div className={cn('rounded-lg p-3', metric.tone)}>
                  <metric.icon className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {canView('projects') && (
        <Card className={cn(hasTeamPanel ? 'xl:col-span-8' : 'xl:col-span-12')}>
          <CardHeader>
            <CardTitle className="text-lg">项目与交付</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <CompactMetric label="项目总数" value={summary?.projects.total} loading={loading} />
              <CompactMetric label="进行中" value={summary?.projects.active} loading={loading} />
              <CompactMetric label="已完成" value={summary?.projects.completed} loading={loading} />
              <CompactMetric label="已逾期" value={summary?.projects.overdue} loading={loading} emphasis={Boolean(summary?.projects.overdue)} />
              <CompactMetric label="高风险" value={summary?.projects.high_risk} loading={loading} emphasis={Boolean(summary?.projects.high_risk)} />
            </div>
            <ProgressBlock label="平均项目进度" value={summary?.projects.avg_progress} />
            <DistributionList items={summary?.projects.status_distribution || []} total={summary?.projects.total || 0} emptyText="暂无项目状态数据" />
          </CardContent>
        </Card>
        )}

        {hasTeamPanel && (
        <Card className={cn(canView('projects') ? 'xl:col-span-4' : 'xl:col-span-12')}>
          <CardHeader>
            <CardTitle className="text-lg">人员与会议</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(canView('users') || canView('roles')) && (
              <div className="grid grid-cols-2 gap-3">
                {canView('users') && <CompactMetric label="用户总数" value={summary?.users.total} loading={loading} />}
                {canView('users') && <CompactMetric label="活跃用户" value={summary?.users.active} loading={loading} />}
                {canView('roles') && <CompactMetric label="角色数量" value={summary?.users.roles} loading={loading} />}
                {canView('users') && <CompactMetric label="今日登录" value={summary?.users.today_logins} loading={loading} />}
              </div>
            )}
            {canView('meetings') && (
            <div className="rounded-lg border p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700">
                <CalendarDays className="h-4 w-4" />
                会议
              </div>
              <div className="grid grid-cols-3 gap-3">
                <CompactMetric label="今日" value={summary?.meetings.today} loading={loading} />
                <CompactMetric label="待开始" value={summary?.meetings.upcoming} loading={loading} />
                <CompactMetric label="进行中" value={summary?.meetings.running} loading={loading} />
              </div>
            </div>
            )}
            {canView('reports') && (
            <div className="rounded-lg border p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700">
                <FileText className="h-4 w-4" />
                测试报告
              </div>
              <div className="grid grid-cols-3 gap-3">
                <CompactMetric label="总数" value={summary?.reports.total} loading={loading} />
                <CompactMetric label="完成" value={summary?.reports.completed} loading={loading} />
                <CompactMetric label="失败" value={summary?.reports.failed} loading={loading} emphasis={Boolean(summary?.reports.failed)} />
              </div>
            </div>
            )}
          </CardContent>
        </Card>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {hasBusinessPanel && (canView('requirements') || canView('tasks')) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">需求与任务</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {canView('requirements') && <CompactMetric label="需求总数" value={summary?.requirements.total} loading={loading} />}
              {canView('requirements') && <CompactMetric label="活跃需求" value={summary?.requirements.active} loading={loading} />}
              {canView('requirements') && <CompactMetric label="完成需求" value={summary?.requirements.completed} loading={loading} />}
              {canView('requirements') && <CompactMetric label="逾期需求" value={summary?.requirements.overdue} loading={loading} emphasis={Boolean(summary?.requirements.overdue)} />}
              {canView('tasks') && <CompactMetric label="待办任务" value={summary?.tasks.open} loading={loading} emphasis={Boolean(summary?.tasks.overdue)} />}
              {canView('tasks') && <CompactMetric label="逾期任务" value={summary?.tasks.overdue} loading={loading} emphasis={Boolean(summary?.tasks.overdue)} />}
            </div>
            {canView('requirements') && <ProgressBlock label="需求完成率" value={summary?.requirements.completion_rate} />}
            {canView('tasks') && <ProgressBlock label="任务完成率" value={summary?.tasks.completion_rate} />}
            {canView('requirements') && <DistributionList items={summary?.requirements.status_distribution || []} total={summary?.requirements.total || 0} emptyText="暂无需求状态数据" />}
          </CardContent>
        </Card>
        )}

        {hasQualityPanel && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">测试与质量</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {canView('testing') && <CompactMetric label="测试计划" value={summary?.testing.plans_total} loading={loading} />}
              {canView('testing') && <CompactMetric label="活跃计划" value={summary?.testing.plans_active} loading={loading} />}
              {canView('testing') && <CompactMetric label="测试用例" value={summary?.testing.cases_total} loading={loading} />}
              {canView('testing') && <CompactMetric label="活跃用例" value={summary?.testing.cases_active} loading={loading} />}
              {canView('defects') && <CompactMetric label="未关缺陷" value={summary?.defects.open} loading={loading} emphasis={Boolean(summary?.defects.open)} />}
              {canView('defects') && <CompactMetric label="高优先级" value={summary?.defects.high_priority_open} loading={loading} emphasis={Boolean(summary?.defects.high_priority_open)} />}
            </div>
            {canView('testing') && <ProgressBlock label="测试通过率" value={summary?.testing.pass_rate} />}
            {canView('defects') && <ProgressBlock label="缺陷解决率" value={summary?.defects.resolution_rate} />}
            {canView('defects') && <DistributionList items={summary?.defects.status_distribution || []} total={summary?.defects.total || 0} emptyText="暂无缺陷状态数据" />}
          </CardContent>
        </Card>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">最近动态</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="h-12 animate-pulse rounded bg-gray-100" />
                ))}
              </div>
            ) : summary?.recent_activity?.length ? (
              <div className="divide-y">
                {summary.recent_activity.map((item, index) => (
                  <Link
                    key={`${item.type}-${item.title}-${index}`}
                    to={item.link || '/'}
                    className="flex items-center justify-between gap-4 py-3 hover:bg-gray-50"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{typeLabels[item.type]}</Badge>
                        <p className="truncate text-sm font-medium text-gray-900">{item.title || '未命名记录'}</p>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">{formatTime(item.occurred_at)}</p>
                    </div>
                    <StatusBadge value={item.status} />
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState icon={Clock} text="暂无最近动态" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">数据来源</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="h-8 animate-pulse rounded bg-gray-100" />
                ))}
              </div>
            ) : summary?.data_sources?.length ? (
              <div className="space-y-2">
                {summary.data_sources.map((source) => (
                  <div key={source.table} className="flex items-center justify-between gap-3 rounded border px-3 py-2 text-sm">
                    <span className="font-mono text-xs text-gray-700">{source.table}</span>
                    <Badge variant={source.available ? 'secondary' : 'outline'} className={source.available ? 'text-emerald-700' : 'text-gray-500'}>
                      {source.available ? '已读取' : '无数据表'}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={CheckCircle2} text="暂无数据来源信息" />
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  )
}

const CompactMetric = ({
  label,
  value,
  loading,
  emphasis,
}: {
  label: string
  value?: number
  loading: boolean
  emphasis?: boolean
}) => (
  <div>
    <p className="text-xs text-gray-500">{label}</p>
    <p className={cn('mt-1 text-xl font-semibold', emphasis ? 'text-red-700' : 'text-gray-900')}>{loading ? '...' : formatNumber(value)}</p>
  </div>
)

const ProgressBlock = ({ label, value }: { label: string; value?: number }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between text-sm">
      <span className="font-medium text-gray-700">{label}</span>
      <span className="text-gray-600">{formatPercent(value)}</span>
    </div>
    <Progress value={clampPercent(value)} className="h-3" />
  </div>
)

const DistributionList = ({ items, total, emptyText }: { items: DistributionItem[]; total: number; emptyText: string }) => {
  if (!items.length || total <= 0) {
    return <EmptyState icon={BarChart3} text={emptyText} />
  }

  return (
    <div className="space-y-3">
      {items.slice(0, 6).map((item) => {
        const percent = _distributionPercent(item.count, total)
        return (
          <div key={item.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-700">{statusLabels[item.name] || item.name}</span>
              <span className="text-gray-500">
                {formatNumber(item.count)} / {formatPercent(percent)}
              </span>
            </div>
            <Progress value={percent} className="h-2" />
          </div>
        )
      })}
    </div>
  )
}

const _distributionPercent = (value: number, total: number) => {
  if (!total) return 0
  return Math.round((value * 10000) / total) / 100
}

const StatusBadge = ({ value }: { value?: string | null }) => {
  if (!value) return <Badge variant="outline">无状态</Badge>
  const isWarning = ['FAILED', 'BLOCKED', 'NEW', 'REOPENED', 'TEST_FAILED'].includes(value)
  const isDone = ['COMPLETED', 'CLOSED', 'PASSED', 'VERIFIED', 'RESOLVED', 'completed'].includes(value)
  return (
    <Badge
      variant={isWarning ? 'destructive' : isDone ? 'secondary' : 'outline'}
      className={isDone ? 'text-emerald-700' : undefined}
    >
      {statusLabels[value] || value}
    </Badge>
  )
}

const EmptyState = ({ icon: Icon, text }: { icon: React.ElementType; text: string }) => (
  <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed p-5 text-sm text-gray-500">
    <Icon className="h-4 w-4" />
    {text}
  </div>
)

export default Dashboard
