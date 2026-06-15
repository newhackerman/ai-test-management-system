import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, FileText, Monitor, Play, Search, Settings, Square } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Checkbox } from '../../../components/ui/Checkbox'
import { Input } from '../../../components/ui/Input'
import { Progress } from '../../../components/ui/Progress'
import { ScrollArea } from '../../../components/ui/ScrollArea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import {
  useAutomationExecutionStatus,
  useCancelAutomationExecution,
  useStartAutomationExecution,
} from '../../../hooks/testmanager/useExecution'
import { useTestCases } from '../../../hooks/testmanager/useTestCase'
import { AutomationLevel, ExecutionStatus, Priority } from '../../../types/testmanager'

const statusLabels: Record<string, string> = {
  PENDING: '待执行',
  RUNNING: '执行中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  FAILED: '失败',
  [ExecutionStatus.NOT_EXECUTED]: '未执行',
  [ExecutionStatus.IN_PROGRESS]: '执行中',
  [ExecutionStatus.PASSED]: '通过',
  [ExecutionStatus.BLOCKED]: '阻塞',
  [ExecutionStatus.SKIPPED]: '跳过',
}

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  PENDING: 'secondary',
  RUNNING: 'default',
  COMPLETED: 'default',
  CANCELLED: 'outline',
  FAILED: 'destructive',
  [ExecutionStatus.NOT_EXECUTED]: 'secondary',
  [ExecutionStatus.IN_PROGRESS]: 'default',
  [ExecutionStatus.PASSED]: 'default',
  [ExecutionStatus.BLOCKED]: 'secondary',
  [ExecutionStatus.SKIPPED]: 'outline',
}

const automationLabels: Record<string, string> = {
  [AutomationLevel.SEMI_AUTO]: '半自动',
  [AutomationLevel.FULL_AUTO]: '全自动',
}

const priorityLabels: Record<string, string> = {
  [Priority.CRITICAL]: '紧急',
  [Priority.HIGH]: '高',
  [Priority.MEDIUM]: '中',
  [Priority.LOW]: '低',
}

const AutomationExecution: React.FC = () => {
  const [selectedCases, setSelectedCases] = useState<number[]>([])
  const [activeExecutionId, setActiveExecutionId] = useState('')
  const [search, setSearch] = useState('')
  const [automationFilter, setAutomationFilter] = useState('all')
  const [executionConfig, setExecutionConfig] = useState({
    framework: 'auto',
    browser: 'chrome',
    environment: 'test',
    parallel: 1,
    retry: 1,
    headless: true,
  })

  const { data: testCasesData, isLoading } = useTestCases({ page: 1, size: 100 })
  const startAutomation = useStartAutomationExecution()
  const cancelAutomation = useCancelAutomationExecution()
  const statusQuery = useAutomationExecutionStatus(activeExecutionId)

  const testCases = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    return (testCasesData?.data || [])
      .filter((item) => item.automation_level === AutomationLevel.SEMI_AUTO || item.automation_level === AutomationLevel.FULL_AUTO)
      .filter((item) => automationFilter === 'all' || item.automation_level === automationFilter)
      .filter((item) => {
        if (!keyword) return true
        return `${item.case_code} ${item.case_title} ${item.module || ''}`.toLowerCase().includes(keyword)
      })
  }, [automationFilter, search, testCasesData?.data])

  const executionStatus = statusQuery.data
  const isRunning = executionStatus?.status === 'RUNNING' || executionStatus?.status === 'PENDING'
  const logs = executionStatus?.execution_logs || []
  const results = executionStatus?.test_results || []
  const selectedCaseSet = useMemo(() => new Set(selectedCases), [selectedCases])
  const progressValue = executionStatus?.progress_percentage || 0

  const visibleCaseIds = testCases.map((item) => item.id)
  const allVisibleSelected = visibleCaseIds.length > 0 && visibleCaseIds.every((id) => selectedCaseSet.has(id))

  const toggleCase = (caseId: number) => {
    setSelectedCases((prev) => prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev, caseId])
  }

  const toggleAllVisible = () => {
    if (!visibleCaseIds.length) return
    setSelectedCases((prev) => {
      if (visibleCaseIds.every((id) => prev.includes(id))) {
        return prev.filter((id) => !visibleCaseIds.includes(id))
      }
      return Array.from(new Set([...prev, ...visibleCaseIds]))
    })
  }

  const startExecution = async () => {
    const response = await startAutomation.mutateAsync({
      test_case_ids: selectedCases,
      framework: executionConfig.framework,
      test_environment: executionConfig.environment,
      browser: executionConfig.browser,
      parallel_count: executionConfig.parallel,
      retry_count: executionConfig.retry,
      execution_config: {
        headless: executionConfig.headless,
      },
    })
    setActiveExecutionId(response.execution_id)
  }

  const cancelExecution = async () => {
    if (!activeExecutionId) return
    await cancelAutomation.mutateAsync(activeExecutionId)
  }

  const statusBadge = (status?: string) => {
    const value = status || 'PENDING'
    return <Badge variant={statusVariants[value] || 'secondary'}>{statusLabels[value] || value}</Badge>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/test-manager/executions">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回执行管理
            </Link>
          </Button>
        </div>
        {!isRunning ? (
          <Button onClick={startExecution} disabled={selectedCases.length === 0 || startAutomation.isPending}>
            <Play className="mr-2 h-4 w-4" />
            {startAutomation.isPending ? '启动中...' : `开始执行 ${selectedCases.length} 条`}
          </Button>
        ) : (
          <Button variant="outline" onClick={cancelExecution} disabled={cancelAutomation.isPending}>
            <Square className="mr-2 h-4 w-4" />
            {cancelAutomation.isPending ? '取消中...' : '取消批次'}
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Settings className="h-5 w-5" />
            执行配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-5">
            <div>
              <label className="mb-2 block text-sm font-medium">执行方式</label>
              <Select value={executionConfig.framework} onValueChange={(value) => setExecutionConfig((prev) => ({ ...prev, framework: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">自动识别导入脚本</SelectItem>
                  <SelectItem value="playwright">Playwright</SelectItem>
                  <SelectItem value="selenium">Selenium</SelectItem>
                  <SelectItem value="pytest">Pytest / Python</SelectItem>
                  <SelectItem value="jest">Node.js / JavaScript</SelectItem>
                  <SelectItem value="jmeter">JMeter</SelectItem>
                  <SelectItem value="har">HAR 回放</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">浏览器</label>
              <Select value={executionConfig.browser} onValueChange={(value) => setExecutionConfig((prev) => ({ ...prev, browser: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="chrome">Chrome</SelectItem>
                  <SelectItem value="firefox">Firefox</SelectItem>
                  <SelectItem value="edge">Edge</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">环境</label>
              <Select value={executionConfig.environment} onValueChange={(value) => setExecutionConfig((prev) => ({ ...prev, environment: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="test">测试环境</SelectItem>
                  <SelectItem value="staging">预发环境</SelectItem>
                  <SelectItem value="dev">开发环境</SelectItem>
                  <SelectItem value="local">本地环境</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">并发数</label>
              <Input type="number" min="1" max="20" value={executionConfig.parallel} onChange={(event) => setExecutionConfig((prev) => ({ ...prev, parallel: Number(event.target.value) || 1 }))} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">重试次数</label>
              <Input type="number" min="0" max="10" value={executionConfig.retry} onChange={(event) => setExecutionConfig((prev) => ({ ...prev, retry: Number(event.target.value) || 0 }))} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="headless"
              checked={executionConfig.headless}
              onCheckedChange={(checked) => setExecutionConfig((prev) => ({ ...prev, headless: Boolean(checked) }))}
            />
            <label htmlFor="headless" className="text-sm">无头模式</label>
          </div>
        </CardContent>
      </Card>

      {executionStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Monitor className="h-5 w-5" />
              执行进度
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">批次号：{executionStatus.execution_id}</span>
              {statusBadge(executionStatus.status)}
            </div>
            <div>
              <div className="mb-2 flex justify-between text-sm">
                <span>整体进度</span>
                <span>{progressValue.toFixed(1)}%</span>
              </div>
              <Progress value={progressValue} className="h-3" />
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div><p className="text-2xl font-semibold text-blue-600">{executionStatus.total_cases}</p><p className="text-sm text-muted-foreground">总数</p></div>
              <div><p className="text-2xl font-semibold text-emerald-600">{executionStatus.completed_cases}</p><p className="text-sm text-muted-foreground">已完成</p></div>
              <div><p className="text-2xl font-semibold text-green-600">{executionStatus.passed_cases}</p><p className="text-sm text-muted-foreground">通过</p></div>
              <div><p className="text-2xl font-semibold text-red-600">{executionStatus.failed_cases}</p><p className="text-sm text-muted-foreground">失败</p></div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
              <CardTitle className="text-lg">选择测试用例</CardTitle>
              <div className="flex flex-col gap-2 md:flex-row md:items-center">
                <div className="relative md:w-64">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input className="pl-9" placeholder="搜索用例" value={search} onChange={(event) => setSearch(event.target.value)} />
                </div>
                <Select value={automationFilter} onValueChange={setAutomationFilter}>
                  <SelectTrigger className="md:w-32"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    <SelectItem value={AutomationLevel.SEMI_AUTO}>半自动</SelectItem>
                    <SelectItem value={AutomationLevel.FULL_AUTO}>全自动</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={toggleAllVisible} disabled={!testCases.length || isRunning}>
                  {allVisibleSelected ? '取消本页' : '选择本页'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox checked={allVisibleSelected} onCheckedChange={toggleAllVisible} disabled={!testCases.length || isRunning} />
                    </TableHead>
                    <TableHead>测试用例</TableHead>
                    <TableHead className="w-[120px]">模块</TableHead>
                    <TableHead className="w-[90px]">优先级</TableHead>
                    <TableHead className="w-[100px]">自动化</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow><TableCell colSpan={5} className="h-24 text-center text-muted-foreground">加载中...</TableCell></TableRow>
                  ) : testCases.length ? testCases.map((testCase) => (
                    <TableRow key={testCase.id}>
                      <TableCell>
                        <Checkbox checked={selectedCaseSet.has(testCase.id)} onCheckedChange={() => toggleCase(testCase.id)} disabled={isRunning} />
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{testCase.case_title}</p>
                        <p className="text-xs text-muted-foreground">{testCase.case_code}</p>
                      </TableCell>
                      <TableCell>{testCase.module || '-'}</TableCell>
                      <TableCell><Badge variant="outline">{priorityLabels[testCase.priority] || testCase.priority}</Badge></TableCell>
                      <TableCell><Badge variant="secondary">{automationLabels[testCase.automation_level] || testCase.automation_level}</Badge></TableCell>
                    </TableRow>
                  )) : (
                    <TableRow><TableCell colSpan={5} className="h-24 text-center text-muted-foreground">暂无可自动化执行的用例</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
              <div className="mt-4 text-sm text-muted-foreground">已选择 {selectedCases.length} 条</div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="logs" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="logs">日志</TabsTrigger>
            <TabsTrigger value="results">结果</TabsTrigger>
          </TabsList>
          <TabsContent value="logs">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="h-5 w-5" />
                  执行日志
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-72 rounded border bg-muted/30 p-3">
                  {logs.length ? logs.map((log, index) => (
                    <div key={index} className="mb-2 text-sm">
                      <span className="text-muted-foreground">{log.time ? new Date(log.time).toLocaleTimeString() : '-'}</span>
                      <span className="ml-2">[{log.level || 'INFO'}] {log.message || JSON.stringify(log)}</span>
                    </div>
                  )) : <div className="text-sm text-muted-foreground">暂无执行日志</div>}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="results">
            <Card>
              <CardHeader><CardTitle className="text-lg">执行结果</CardTitle></CardHeader>
              <CardContent>
                {results.length ? (
                  <div className="space-y-3">
                    {results.map((result) => (
                      <div key={result.execution_id || result.test_case_id} className="rounded border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate font-medium">{result.case_title || result.case_code}</p>
                            <p className="text-xs text-muted-foreground">{result.case_code || result.execution_code}</p>
                          </div>
                          {statusBadge(result.status)}
                        </div>
                        {result.failure_reason && (
                          <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-red-600">{result.failure_reason}</p>
                        )}
                        {!result.failure_reason && result.actual_result && (
                          <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground">{result.actual_result}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <div className="text-sm text-muted-foreground">暂无执行结果</div>}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default AutomationExecution
