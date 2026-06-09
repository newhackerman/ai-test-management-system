import React, { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Activity,
  CheckCircle,
  Eye,
  Pause,
  Play,
  RotateCcw,
  Search,
  Square,
  TrendingUp,
} from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import {
  useCancelExecution,
  useExecutionStatistics,
  useExecutions,
  usePauseExecution,
  useResumeExecution,
} from '../../../hooks/testmanager/useExecution'
import { ExecutionStatus, ExecutionType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const statusLabels: Record<ExecutionStatus, string> = {
  [ExecutionStatus.NOT_EXECUTED]: '未执行',
  [ExecutionStatus.IN_PROGRESS]: '执行中',
  [ExecutionStatus.PASSED]: '通过',
  [ExecutionStatus.FAILED]: '失败',
  [ExecutionStatus.BLOCKED]: '暂停/阻塞',
  [ExecutionStatus.SKIPPED]: '已取消',
}

const statusVariants: Record<ExecutionStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  [ExecutionStatus.NOT_EXECUTED]: 'secondary',
  [ExecutionStatus.IN_PROGRESS]: 'default',
  [ExecutionStatus.PASSED]: 'default',
  [ExecutionStatus.FAILED]: 'destructive',
  [ExecutionStatus.BLOCKED]: 'secondary',
  [ExecutionStatus.SKIPPED]: 'outline',
}

const typeLabels: Record<ExecutionType, string> = {
  [ExecutionType.MANUAL]: '手工',
  [ExecutionType.AUTOMATED]: '自动化',
}

const formatDuration = (seconds?: number, startedAt?: string, status?: ExecutionStatus) => {
  let value = seconds
  if (!value && startedAt && status === ExecutionStatus.IN_PROGRESS) {
    value = Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000))
  }
  if (!value) return '-'
  if (value < 60) return `${value}秒`
  const minutes = Math.floor(value / 60)
  if (minutes < 60) return `${minutes}分钟`
  return `${Math.floor(minutes / 60)}小时${minutes % 60}分钟`
}

const ExecutionDashboard: React.FC = () => {
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string>(searchParams.get('status') || 'all')
  const [type, setType] = useState<string>(searchParams.get('type') || 'all')
  const planId = Number(searchParams.get('test_plan_id') || searchParams.get('plan_id') || 0) || undefined
  const pageSize = 12

  const filters = useMemo(() => ({
    page,
    size: pageSize,
    search,
    test_plan_id: planId,
    execution_status: status === 'all' ? undefined : status as ExecutionStatus,
    execution_type: type === 'all' ? undefined : type,
  }), [page, planId, search, status, type])

  const { data: executionsData, isLoading, refetch } = useExecutions(filters)
  const { data: statistics } = useExecutionStatistics()
  const pauseExecution = usePauseExecution()
  const resumeExecution = useResumeExecution()
  const cancelExecution = useCancelExecution()

  const executions = executionsData?.data || []
  const total = executionsData?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const stats = statistics || {
    total_executions: 0,
    in_progress: 0,
    completed_today: 0,
    pass_rate: 0,
    avg_duration: 0,
    active_executors: 0,
  }

  const resetFilters = () => {
    setSearch('')
    setStatus('all')
    setType('all')
    setPage(1)
  }

  const statusBadge = (value: ExecutionStatus) => (
    <Badge variant={statusVariants[value] || 'secondary'}>{statusLabels[value] || value}</Badge>
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">执行管理</h1>
          <p className="text-sm text-muted-foreground">管理手工执行、自动化执行和执行结果追踪</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RotateCcw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button asChild>
            <Link to="/test-manager/executions/manual">
              <Play className="mr-2 h-4 w-4" />
              手工执行
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/test-manager/executions/automation">
              <Activity className="mr-2 h-4 w-4" />
              自动化执行
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <Activity className="h-5 w-5 text-blue-600" />
            <div>
              <p className="text-sm text-muted-foreground">总执行数</p>
              <p className="text-2xl font-semibold">{stats.total_executions}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <Play className="h-5 w-5 text-emerald-600" />
            <div>
              <p className="text-sm text-muted-foreground">执行中</p>
              <p className="text-2xl font-semibold">{stats.in_progress}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <CheckCircle className="h-5 w-5 text-violet-600" />
            <div>
              <p className="text-sm text-muted-foreground">今日完成</p>
              <p className="text-2xl font-semibold">{stats.completed_today}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <TrendingUp className="h-5 w-5 text-amber-600" />
            <div>
              <p className="text-sm text-muted-foreground">通过率</p>
              <p className="text-2xl font-semibold">{stats.pass_rate}%</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
          <CardTitle className="text-lg">执行记录</CardTitle>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9 md:w-64"
                placeholder="搜索执行编号、用例编号或标题"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(1)
                }}
              />
            </div>
            <Select value={status} onValueChange={(value) => { setStatus(value); setPage(1) }}>
              <SelectTrigger className="md:w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value={ExecutionStatus.IN_PROGRESS}>执行中</SelectItem>
                <SelectItem value={ExecutionStatus.BLOCKED}>暂停/阻塞</SelectItem>
                <SelectItem value={ExecutionStatus.PASSED}>通过</SelectItem>
                <SelectItem value={ExecutionStatus.FAILED}>失败</SelectItem>
                <SelectItem value={ExecutionStatus.SKIPPED}>已取消</SelectItem>
              </SelectContent>
            </Select>
            <Select value={type} onValueChange={(value) => { setType(value); setPage(1) }}>
              <SelectTrigger className="md:w-32"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value={ExecutionType.MANUAL}>手工</SelectItem>
                <SelectItem value={ExecutionType.AUTOMATED}>自动化</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={resetFilters}>重置</Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[190px]">执行编号</TableHead>
                <TableHead>测试用例</TableHead>
                <TableHead className="w-[90px]">类型</TableHead>
                <TableHead className="w-[110px]">状态</TableHead>
                <TableHead className="w-[110px]">环境</TableHead>
                <TableHead className="w-[150px]">开始时间</TableHead>
                <TableHead className="w-[90px]">耗时</TableHead>
                <TableHead className="w-[170px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">加载中...</TableCell>
                </TableRow>
              ) : executions.length ? executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell>
                    <Link to={`/test-manager/executions/${execution.id}`} className="font-medium text-primary hover:underline">
                      {execution.execution_code}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{execution.test_case_title || `用例 #${execution.test_case_id}`}</p>
                      <p className="text-xs text-muted-foreground">{execution.test_case_code || `ID: ${execution.test_case_id}`}</p>
                    </div>
                  </TableCell>
                  <TableCell><Badge variant="outline">{typeLabels[execution.execution_type]}</Badge></TableCell>
                  <TableCell>{statusBadge(execution.execution_status)}</TableCell>
                  <TableCell>{execution.test_environment || '-'}</TableCell>
                  <TableCell>{execution.started_at ? formatDate(execution.started_at) : '-'}</TableCell>
                  <TableCell>{formatDuration(execution.duration, execution.started_at, execution.execution_status)}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button asChild variant="ghost" size="icon" title="查看详情">
                        <Link to={`/test-manager/executions/${execution.id}`}><Eye className="h-4 w-4" /></Link>
                      </Button>
                      {execution.execution_status === ExecutionStatus.IN_PROGRESS && (
                        <Button variant="ghost" size="icon" title="暂停" onClick={() => pauseExecution.mutate(execution.id)}>
                          <Pause className="h-4 w-4" />
                        </Button>
                      )}
                      {execution.execution_status === ExecutionStatus.BLOCKED && (
                        <Button variant="ghost" size="icon" title="恢复" onClick={() => resumeExecution.mutate(execution.id)}>
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                      {(execution.execution_status === ExecutionStatus.IN_PROGRESS || execution.execution_status === ExecutionStatus.BLOCKED) && (
                        <Button variant="ghost" size="icon" title="取消" onClick={() => cancelExecution.mutate(execution.id)}>
                          <Square className="h-4 w-4" />
                        </Button>
                      )}
                      {execution.execution_type === ExecutionType.MANUAL && (
                        <Button asChild variant="ghost" size="icon" title="执行该用例">
                          <Link to={`/test-manager/executions/manual/${execution.test_case_id}`}><CheckCircle className="h-4 w-4" /></Link>
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                    暂无执行记录
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="mt-4 flex flex-col gap-2 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
            <span>共 {total} 条记录，第 {page} / {totalPages} 页</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                上一页
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ExecutionDashboard
