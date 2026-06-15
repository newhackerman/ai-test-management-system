import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  BarChart3,
  Bug,
  CheckCircle2,
  ClipboardList,
  FileText,
  PlayCircle,
  Plus,
  TestTube2,
  Timer,
} from 'lucide-react'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { Progress } from '../../components/ui/Progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table'
import { useDefectStatistics, useDefects } from '../../hooks/testmanager/useDefect'
import { useExecutionStatistics, useExecutions } from '../../hooks/testmanager/useExecution'
import { useTestCases } from '../../hooks/testmanager/useTestCase'
import { useTestPlans } from '../../hooks/testmanager/useTestPlan'
import { DefectSeverity, DefectStatus, ExecutionStatus, TestPlanStatus } from '../../types/testmanager'
import { formatDate } from '../../utils/date'

const planStatusLabels: Record<string, string> = {
  DRAFT: '草稿',
  APPROVED: '已批准',
  IN_PROGRESS: '进行中',
  PAUSED: '暂停',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

const executionStatusLabels: Record<string, string> = {
  NOT_EXECUTED: '未执行',
  IN_PROGRESS: '执行中',
  PASSED: '通过',
  FAILED: '失败',
  BLOCKED: '阻塞',
  SKIPPED: '跳过',
}

const defectStatusLabels: Record<string, string> = {
  NEW: '新建',
  ASSIGNED: '已分配',
  IN_PROGRESS: '处理中',
  RESOLVED: '已解决',
  VERIFIED: '已验证',
  CLOSED: '已关闭',
  REOPENED: '重新打开',
  REJECTED: '已拒绝',
  DEFERRED: '延期',
}

const pct = (value?: number) => Math.max(0, Math.min(100, Math.round(Number(value || 0))))
const num = (value: any) => Number(value || 0)

const TestManager: React.FC = () => {
  const { data: plansData, isLoading: plansLoading } = useTestPlans({ page: 1, size: 8 })
  const { data: activePlansData } = useTestPlans({ page: 1, size: 1, status: TestPlanStatus.IN_PROGRESS })
  const { data: pausedPlansData } = useTestPlans({ page: 1, size: 1, status: TestPlanStatus.PAUSED })
  const { data: casesData } = useTestCases({ page: 1, size: 1 })
  const { data: executionsData, isLoading: executionsLoading } = useExecutions({ page: 1, size: 8 })
  const { data: failedExecutionsData } = useExecutions({ page: 1, size: 1, execution_status: ExecutionStatus.FAILED })
  const { data: inProgressExecutionsData } = useExecutions({ page: 1, size: 1, execution_status: ExecutionStatus.IN_PROGRESS })
  const { data: defectsData, isLoading: defectsLoading } = useDefects({ page: 1, size: 8 })
  const { data: criticalDefectsData } = useDefects({ page: 1, size: 1, severity: DefectSeverity.CRITICAL })
  const { data: highDefectsData } = useDefects({ page: 1, size: 1, severity: DefectSeverity.HIGH })
  const { data: openDefectsData } = useDefects({ page: 1, size: 1, status: DefectStatus.NEW })
  const { data: defectStats } = useDefectStatistics()
  const { data: executionStats } = useExecutionStatistics()

  const plans = plansData?.data || []
  const executions = executionsData?.data || []
  const defects = defectsData?.data || []

  const openDefectTotal = useMemo(() => {
    const byStatus = defectStats?.defects_by_status || {}
    return ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'REOPENED'].reduce((sum, key) => sum + num(byStatus[key]), 0) || num(openDefectsData?.total)
  }, [defectStats, openDefectsData?.total])

  const metrics = useMemo(() => {
    const totalCases = num(casesData?.total)
    const totalExecutions = num(executionStats?.total_executions)
    const activePlans = num(activePlansData?.total)
    const pausedPlans = num(pausedPlansData?.total)
    const failedExecutions = num(failedExecutionsData?.total)
    const inProgressExecutions = num(inProgressExecutionsData?.total)
    const criticalDefects = num(criticalDefectsData?.total || defectStats?.critical_defects)
    const highDefects = num(highDefectsData?.total || defectStats?.high_defects)
    const passRate = pct(executionStats?.pass_rate)
    const executionCoverage = totalCases ? pct((totalExecutions / totalCases) * 100) : 0
    const planExecutionRate = plans.length
      ? pct(plans.reduce((sum, plan) => sum + num(plan.execution_rate), 0) / plans.length)
      : 0

    return {
      totalPlans: num(plansData?.total),
      activePlans,
      pausedPlans,
      totalCases,
      totalExecutions,
      inProgressExecutions,
      failedExecutions,
      totalDefects: num(defectsData?.total || defectStats?.total_defects),
      criticalDefects,
      highDefects,
      openDefectTotal,
      passRate,
      executionCoverage,
      planExecutionRate,
    }
  }, [
    activePlansData?.total,
    casesData?.total,
    criticalDefectsData?.total,
    defectStats,
    defectsData?.total,
    executionStats,
    failedExecutionsData?.total,
    highDefectsData?.total,
    inProgressExecutionsData?.total,
    openDefectTotal,
    pausedPlansData?.total,
    plans,
    plansData?.total,
  ])

  const metricCards = [
    {
      label: '测试计划',
      value: metrics.totalPlans,
      sub: `进行中 ${metrics.activePlans}`,
      icon: ClipboardList,
      link: '/test-manager/test-plans',
    },
    {
      label: '测试用例',
      value: metrics.totalCases,
      sub: `执行覆盖 ${metrics.executionCoverage}%`,
      icon: TestTube2,
      link: '/test-manager/test-cases',
    },
    {
      label: '执行记录',
      value: metrics.totalExecutions,
      sub: `执行中 ${metrics.inProgressExecutions}`,
      icon: PlayCircle,
      link: '/test-manager/executions',
    },
    {
      label: '未关闭缺陷',
      value: metrics.openDefectTotal,
      sub: `严重 ${metrics.criticalDefects} / 高 ${metrics.highDefects}`,
      icon: Bug,
      link: '/test-manager/defects',
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link to="/test-manager/test-cases/create">
              <Plus className="mr-2 h-4 w-4" />
              新建用例
            </Link>
          </Button>
          <Button asChild>
            <Link to="/test-manager/executions/manual">
              <PlayCircle className="mr-2 h-4 w-4" />
              开始执行
            </Link>
          </Button>
        </div>
      </div>

      <div>
        <Card>
          <CardContent className="grid gap-2 p-3 md:grid-cols-3 xl:grid-cols-5">
            {metricCards.map((item) => {
              const Icon = item.icon
              return (
                <Link key={item.label} to={item.link} className="rounded-md border px-3 py-2 transition-colors hover:bg-muted/40">
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4 text-primary" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <p className="truncate text-sm text-muted-foreground">{item.label}</p>
                        <p className="text-lg font-semibold leading-5">{item.value}</p>
                      </div>
                      <p className="truncate text-xs text-muted-foreground">{item.sub}</p>
                    </div>
                  </div>
                </Link>
              )
            })}
            <div className="rounded-md border px-3 py-2">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-4 w-4 text-primary" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="truncate text-sm text-muted-foreground">待处理风险</p>
                    <p className="text-lg font-semibold leading-5">{metrics.pausedPlans + metrics.failedExecutions + metrics.criticalDefects + metrics.highDefects}</p>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">失败 {metrics.failedExecutions} / 高危 {metrics.criticalDefects + metrics.highDefects}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-lg">测试计划进度</CardTitle>
            <Button asChild variant="outline" size="sm"><Link to="/test-manager/test-plans">全部计划</Link></Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>计划</TableHead>
                  <TableHead className="w-24">状态</TableHead>
                  <TableHead className="w-32">进度</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plansLoading ? (
                  <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">加载中...</TableCell></TableRow>
                ) : plans.length ? plans.map((plan) => (
                  <TableRow key={plan.id}>
                    <TableCell>
                      <Link to={`/test-manager/test-plans/${plan.id}`} className="font-medium text-primary hover:underline">
                        {plan.plan_name}
                      </Link>
                      <div className="text-xs text-muted-foreground">{plan.plan_code}</div>
                    </TableCell>
                    <TableCell><Badge variant="secondary">{planStatusLabels[plan.status] || plan.status}</Badge></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={pct(plan.execution_rate)} className="h-2" />
                        <span className="w-10 text-right text-xs text-muted-foreground">{pct(plan.execution_rate)}%</span>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">暂无测试计划</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-lg">最近执行</CardTitle>
            <Button asChild variant="outline" size="sm"><Link to="/test-manager/executions">执行管理</Link></Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用例</TableHead>
                  <TableHead className="w-24">状态</TableHead>
                  <TableHead className="w-36">开始时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executionsLoading ? (
                  <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">加载中...</TableCell></TableRow>
                ) : executions.length ? executions.map((execution) => (
                  <TableRow key={execution.id}>
                    <TableCell>
                      <Link to={`/test-manager/executions/${execution.id}`} className="font-medium text-primary hover:underline">
                        {execution.test_case_title || `用例 #${execution.test_case_id}`}
                      </Link>
                      <div className="text-xs text-muted-foreground">{execution.execution_code}</div>
                    </TableCell>
                    <TableCell><Badge variant={execution.execution_status === ExecutionStatus.FAILED ? 'destructive' : 'secondary'}>{executionStatusLabels[execution.execution_status] || execution.execution_status}</Badge></TableCell>
                    <TableCell className="text-sm">{execution.started_at ? formatDate(execution.started_at) : '-'}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow><TableCell colSpan={3} className="h-24 text-center text-muted-foreground">暂无执行记录</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <div>
        <Card>
          <CardHeader className="gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-lg">测试闭环</CardTitle>
            <Button asChild variant="outline" size="sm">
              <Link to="/test-manager/reports/generate">
                <FileText className="mr-2 h-4 w-4" />
                生成报告
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-md border p-3">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium">计划执行率</span>
                  <span>{metrics.planExecutionRate}%</span>
                </div>
                <Progress value={metrics.planExecutionRate} className="h-2" />
                <p className="mt-2 text-xs text-muted-foreground">按最近计划的执行率均值估算</p>
              </div>
              <div className="rounded-md border p-3">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium">执行通过率</span>
                  <span>{metrics.passRate}%</span>
                </div>
                <Progress value={metrics.passRate} className="h-2" />
                <p className="mt-2 text-xs text-muted-foreground">来自执行统计接口</p>
              </div>
              <div className="rounded-md border p-3">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium">用例执行覆盖</span>
                  <span>{metrics.executionCoverage}%</span>
                </div>
                <Progress value={metrics.executionCoverage} className="h-2" />
                <p className="mt-2 text-xs text-muted-foreground">执行记录数 / 用例总数</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-lg">缺陷态势</CardTitle>
            <Button asChild variant="outline" size="sm"><Link to="/test-manager/defects">缺陷管理</Link></Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>缺陷</TableHead>
                  <TableHead className="w-20">严重级别</TableHead>
                  <TableHead className="w-24">状态</TableHead>
                  <TableHead className="w-36">报告时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {defectsLoading ? (
                  <TableRow><TableCell colSpan={4} className="h-24 text-center text-muted-foreground">加载中...</TableCell></TableRow>
                ) : defects.length ? defects.map((defect) => (
                  <TableRow key={defect.id}>
                    <TableCell>
                      <Link to="/test-manager/defects" className="font-medium text-primary hover:underline">{defect.title}</Link>
                      <div className="text-xs text-muted-foreground">{defect.defect_code}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={defect.severity === DefectSeverity.CRITICAL || defect.severity === DefectSeverity.HIGH ? 'destructive' : 'secondary'}>
                        {defect.severity === DefectSeverity.CRITICAL ? '严重' : defect.severity === DefectSeverity.HIGH ? '高' : defect.severity === DefectSeverity.MEDIUM ? '中' : '低'}
                      </Badge>
                    </TableCell>
                    <TableCell><Badge variant="outline">{defectStatusLabels[defect.status] || defect.status}</Badge></TableCell>
                    <TableCell className="text-sm">{defect.reported_at ? formatDate(defect.reported_at) : '-'}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow><TableCell colSpan={4} className="h-24 text-center text-muted-foreground">暂无缺陷</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">常用操作</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/test-plans/create"><ClipboardList className="mr-2 h-4 w-4" />新建测试计划</Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/test-cases"><TestTube2 className="mr-2 h-4 w-4" />维护测试用例</Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/executions"><Timer className="mr-2 h-4 w-4" />查看执行队列</Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/defects"><AlertTriangle className="mr-2 h-4 w-4" />处理缺陷</Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/reports"><BarChart3 className="mr-2 h-4 w-4" />查看测试报告</Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to="/test-manager/reports/generate?type=execution"><CheckCircle2 className="mr-2 h-4 w-4" />生成执行报告</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default TestManager
