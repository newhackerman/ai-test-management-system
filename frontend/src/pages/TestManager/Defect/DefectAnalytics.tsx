import React from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, BarChart3, Calendar, PieChart, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Progress } from '../../../components/ui/Progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { useDefectStatistics, useDefectTrendsWithFilters } from '../../../hooks/testmanager/useDefect'
import { testPlanService } from '../../../services/testmanager/testPlanService'

const severityLabels: Record<string, string> = {
  CRITICAL: '严重',
  HIGH: '高',
  MEDIUM: '中',
  LOW: '低',
  TRIVIAL: '轻微',
}

const statusLabels: Record<string, string> = {
  NEW: '新建',
  ASSIGNED: '已分配',
  IN_PROGRESS: '处理中',
  RESOLVED: '已解决',
  VERIFIED: '已验证',
  CLOSED: '已关闭',
  REOPENED: '重新打开',
  REJECTED: '已拒绝',
}

const typeLabels: Record<string, string> = {
  FUNCTIONAL: '功能',
  PERFORMANCE: '性能',
  SECURITY: '安全',
  USABILITY: '易用性',
  COMPATIBILITY: '兼容性',
  DATA: '数据',
  INTERFACE: '接口',
}

const defaultStats = {
  total_defects: 0,
  new_defects: 0,
  resolved_defects: 0,
  critical_defects: 0,
  high_defects: 0,
  medium_defects: 0,
  low_defects: 0,
  trivial_defects: 0,
  resolution_rate: 0,
  avg_resolution_time: 0,
  defect_density: 0,
  reopen_rate: 0,
  defects_by_status: {},
  defects_by_severity: {},
  defects_by_type: {},
}

const percent = (value: number, total: number) => (total > 0 ? Math.round((value / total) * 100) : 0)
const formatDate = (value: string) => {
  const date = new Date(value)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

const DefectAnalytics: React.FC = () => {
  const [timeRange, setTimeRange] = React.useState('30d')
  const [testPlanId, setTestPlanId] = React.useState('all')
  const [testPlans, setTestPlans] = React.useState<any[]>([])

  const filters = React.useMemo(() => ({
    test_plan_id: testPlanId === 'all' ? undefined : Number(testPlanId),
  }), [testPlanId])
  const { data: statistics, isLoading: statsLoading, error: statsError } = useDefectStatistics(filters)
  const { data: trends, isLoading: trendsLoading, error: trendsError } = useDefectTrendsWithFilters(timeRange, filters)

  React.useEffect(() => {
    let cancelled = false
    testPlanService.getTestPlans({ page: 1, size: 100 })
      .then((result: any) => {
        if (!cancelled) setTestPlans(result.data || [])
      })
      .catch(() => {
        if (!cancelled) setTestPlans([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const stats = { ...defaultStats, ...(statistics || {}) }
  const trendData = (trends || []).filter((item: any) => item.new_defects || item.resolved_defects || item.total_defects).slice(-14)
  const maxDaily = Math.max(1, ...trendData.map((item: any) => Math.max(item.new_defects || 0, item.resolved_defects || 0)))
  const total = Number(stats.total_defects || 0)

  const severityRows = Object.entries(stats.defects_by_severity || {})
    .filter(([key]) => key in severityLabels)
    .map(([key, value]) => ({ key, label: severityLabels[key], value: Number(value || 0) }))

  const statusRows = Object.entries(stats.defects_by_status || {})
    .filter(([key]) => key in statusLabels)
    .map(([key, value]) => ({ key, label: statusLabels[key], value: Number(value || 0) }))
    .filter((item) => item.value > 0)

  const typeRows = Object.entries(stats.defects_by_type || {})
    .filter(([key]) => key in typeLabels)
    .map(([key, value]) => ({ key, label: typeLabels[key], value: Number(value || 0) }))
    .filter((item) => item.value > 0)

  const openDefects = total - Number(stats.resolved_defects || 0)
  const loading = statsLoading || trendsLoading
  const error = statsError || trendsError
  const listQueryPrefix = testPlanId === 'all' ? '' : `test_plan_id=${testPlanId}&`

  if (error) {
    return <div className="text-center text-red-500">加载缺陷分析失败：{(error as Error).message}</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">缺陷分析</h1>
          <p className="text-gray-600">基于缺陷库的实时统计、分布和趋势</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Select value={testPlanId} onValueChange={setTestPlanId}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="测试计划" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部测试计划</SelectItem>
              {testPlans.map((plan) => (
                <SelectItem key={plan.id} value={String(plan.id)}>{plan.plan_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">最近7天</SelectItem>
              <SelectItem value="30d">最近30天</SelectItem>
              <SelectItem value="90d">最近90天</SelectItem>
              <SelectItem value="1y">最近1年</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <BarChart3 className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">缺陷总数</p>
                <Link to={`/test-manager/defects?${listQueryPrefix}`} className="text-2xl font-bold hover:text-blue-700">{loading ? '-' : total}</Link>
                <p className="mt-1 text-xs text-gray-500">当前库内全部缺陷</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">高危缺陷</p>
                <Link to={`/test-manager/defects?${listQueryPrefix}`} className="block text-2xl font-bold text-red-600 hover:text-red-700">
                  {loading ? '-' : Number(stats.critical_defects || 0) + Number(stats.high_defects || 0)}
                </Link>
                <p className="mt-1 text-xs text-gray-500">严重 + 高优先处理</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <TrendingUp className="h-5 w-5 text-green-500" />
              <div className="w-full">
                <p className="text-sm font-medium text-gray-600">解决率</p>
                <p className="text-2xl font-bold">{loading ? '-' : `${stats.resolution_rate}%`}</p>
                <Progress value={Number(stats.resolution_rate || 0)} className="mt-2 h-2" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <Calendar className="h-5 w-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">平均解决时间</p>
                <p className="text-2xl font-bold">{loading ? '-' : `${stats.avg_resolution_time || 0}天`}</p>
                <p className="mt-1 text-xs text-gray-500">按已解决缺陷计算</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>缺陷趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trendData.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-gray-500">当前时间范围内暂无趋势数据</div>
            ) : (
              <div className="h-64 space-y-3 overflow-y-auto pr-2">
                {trendData.map((item: any) => (
                  <div key={item.date} className="grid grid-cols-[56px_1fr_72px] items-center gap-3 text-sm">
                    <span className="text-gray-500">{formatDate(item.date)}</span>
                    <div className="space-y-1">
                      <div className="h-2 rounded bg-gray-100">
                        <div className="h-2 rounded bg-blue-500" style={{ width: `${percent(item.new_defects || 0, maxDaily)}%` }} />
                      </div>
                      <div className="h-2 rounded bg-gray-100">
                        <div className="h-2 rounded bg-green-500" style={{ width: `${percent(item.resolved_defects || 0, maxDaily)}%` }} />
                      </div>
                    </div>
                    <span className="text-right text-gray-600">新{item.new_defects || 0} / 解{item.resolved_defects || 0}</span>
                  </div>
                ))}
                <div className="flex gap-4 pt-2 text-xs text-gray-500">
                  <span><span className="mr-1 inline-block h-2 w-4 rounded bg-blue-500" />新增</span>
                  <span><span className="mr-1 inline-block h-2 w-4 rounded bg-green-500" />解决</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <PieChart className="h-5 w-5" />
              <span>严重程度分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {severityRows.map((item) => (
                <div key={item.key} className="flex items-center justify-between gap-4">
                  <span className="w-16 text-sm">{item.label}</span>
                  <div className="h-2 flex-1 rounded-full bg-gray-200">
                    <div className="h-2 rounded-full bg-red-500" style={{ width: `${percent(item.value, total)}%` }} />
                  </div>
                  <Link to={`/test-manager/defects?${listQueryPrefix}severity=${item.key}`}>
                    <Badge variant={item.key === 'CRITICAL' || item.key === 'HIGH' ? 'destructive' : 'secondary'}>{item.value}</Badge>
                  </Link>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>解决情况</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="mb-2 flex justify-between text-sm">
                  <span>已解决/验证/关闭</span>
                  <span>{stats.resolved_defects} / {total}</span>
                </div>
                <Progress value={Number(stats.resolution_rate || 0)} className="h-3" />
              </div>
              <div className="grid grid-cols-3 gap-4 pt-2 text-center">
                <div>
                  <p className="text-lg font-bold text-blue-600">{openDefects}</p>
                  <p className="text-sm text-gray-600">未完成</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-green-600">{stats.resolved_defects}</p>
                  <p className="text-sm text-gray-600">已完成</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-orange-600">{stats.reopen_rate || 0}%</p>
                  <p className="text-sm text-gray-600">重开率</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>状态与类型</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              <div>
                <div className="mb-2 text-sm font-medium">状态分布</div>
                <div className="flex flex-wrap gap-2">
                  {statusRows.length ? statusRows.map((item) => (
                    <Link key={item.key} to={`/test-manager/defects?${listQueryPrefix}status=${item.key}`}>
                      <Badge variant="outline">{item.label} {item.value}</Badge>
                    </Link>
                  )) : <span className="text-sm text-gray-500">暂无状态数据</span>}
                </div>
              </div>
              <div>
                <div className="mb-2 text-sm font-medium">类型分布</div>
                <div className="flex flex-wrap gap-2">
                  {typeRows.length ? typeRows.map((item) => (
                    <Link key={item.key} to={`/test-manager/defects?${listQueryPrefix}defect_type=${item.key}`}>
                      <Badge variant="secondary">{item.label} {item.value}</Badge>
                    </Link>
                  )) : <span className="text-sm text-gray-500">暂无类型数据</span>}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>处理建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Number(stats.critical_defects || 0) + Number(stats.high_defects || 0) > 0 && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
                当前存在高危缺陷，建议优先安排负责人处理严重和高等级问题。
              </div>
            )}
            {openDefects > 0 && (
              <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
                仍有 {openDefects} 个缺陷未完成，建议按负责人和状态持续跟进。
              </div>
            )}
            {total === 0 && (
              <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
                暂无缺陷数据，创建缺陷后这里会展示真实统计。
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default DefectAnalytics
