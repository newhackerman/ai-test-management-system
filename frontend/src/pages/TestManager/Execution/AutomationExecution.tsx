import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, FileText, Monitor, Play, RefreshCw, Search, Settings, Square } from 'lucide-react'
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
import {
  EXECUTION_ENVIRONMENTS,
  RESULT_COLLECTION_OPTIONS,
  RUNNER_TYPE_OPTIONS,
  TestExecutionConfigService,
  type TestExecutionConfig,
  type TestExecutionEnvironment,
} from '../../../services/testExecutionConfigService'
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
  const [executionConfigs, setExecutionConfigs] = useState<TestExecutionConfig[]>([])
  const [executionConfigLoading, setExecutionConfigLoading] = useState(false)
  const [executionConfigError, setExecutionConfigError] = useState('')
  const [executionEnvironment, setExecutionEnvironment] = useState<TestExecutionEnvironment>('test')
  const [selectedConfigId, setSelectedConfigId] = useState('')

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
  const enabledExecutionConfigs = useMemo(() => executionConfigs.filter((item) => item.enabled), [executionConfigs])
  const availableEnvironments = useMemo(() => (
    EXECUTION_ENVIRONMENTS.filter((environment) => enabledExecutionConfigs.some((item) => item.environment === environment.value))
  ), [enabledExecutionConfigs])
  const environmentConfigs = useMemo(() => (
    enabledExecutionConfigs.filter((item) => item.environment === executionEnvironment)
  ), [enabledExecutionConfigs, executionEnvironment])
  const selectedExecutionConfig = useMemo(() => (
    environmentConfigs.find((item) => item.id === selectedConfigId) || environmentConfigs[0]
  ), [environmentConfigs, selectedConfigId])

  const loadExecutionConfigs = async () => {
    setExecutionConfigLoading(true)
    setExecutionConfigError('')
    try {
      const list = await TestExecutionConfigService.listAll()
      setExecutionConfigs(list)
    } catch (error) {
      setExecutionConfigError('测试执行配置加载失败，请检查配置项页面中的测试执行配置。')
      setExecutionConfigs([])
    } finally {
      setExecutionConfigLoading(false)
    }
  }

  useEffect(() => {
    loadExecutionConfigs()
  }, [])

  useEffect(() => {
    if (!enabledExecutionConfigs.length) {
      setSelectedConfigId('')
      return
    }

    if (!enabledExecutionConfigs.some((item) => item.environment === executionEnvironment)) {
      setExecutionEnvironment(enabledExecutionConfigs[0].environment)
      return
    }

    if (!environmentConfigs.some((item) => item.id === selectedConfigId)) {
      setSelectedConfigId(environmentConfigs[0]?.id || '')
    }
  }, [enabledExecutionConfigs, environmentConfigs, executionEnvironment, selectedConfigId])

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
    if (!selectedExecutionConfig) return
    const response = await startAutomation.mutateAsync({
      test_case_ids: selectedCases,
      framework: selectedExecutionConfig.framework,
      test_environment: selectedExecutionConfig.environment,
      browser: selectedExecutionConfig.browser || 'chrome',
      parallel_count: selectedExecutionConfig.parallel_count,
      retry_count: selectedExecutionConfig.retry_count,
      timeout: selectedExecutionConfig.timeout,
      execution_config: {
        source: 'test_execution_config',
        config_id: selectedExecutionConfig.id,
        config_name: selectedExecutionConfig.name,
        framework_label: selectedExecutionConfig.framework_label,
        framework: selectedExecutionConfig.framework,
        browser: selectedExecutionConfig.browser,
        environment: selectedExecutionConfig.environment,
        parallel_count: selectedExecutionConfig.parallel_count,
        retry_count: selectedExecutionConfig.retry_count,
        timeout: selectedExecutionConfig.timeout,
        headless: selectedExecutionConfig.headless,
        runner_type: selectedExecutionConfig.runner_type,
        runner_name: selectedExecutionConfig.runner_name,
        runner_host: selectedExecutionConfig.runner_host,
        runner_port: selectedExecutionConfig.runner_port,
        runner_user: selectedExecutionConfig.runner_user,
        runner_os: selectedExecutionConfig.runner_os,
        runner_workdir: selectedExecutionConfig.runner_workdir,
        credential_ref: selectedExecutionConfig.credential_ref,
        agent_id: selectedExecutionConfig.agent_id,
        agent_callback_url: selectedExecutionConfig.agent_callback_url,
        docker_image: selectedExecutionConfig.docker_image,
        docker_network: selectedExecutionConfig.docker_network,
        docker_volumes: selectedExecutionConfig.docker_volumes,
        docker_args: selectedExecutionConfig.docker_args,
        kubernetes_context: selectedExecutionConfig.kubernetes_context,
        kubernetes_namespace: selectedExecutionConfig.kubernetes_namespace,
        kubernetes_image: selectedExecutionConfig.kubernetes_image,
        kubernetes_job_template: selectedExecutionConfig.kubernetes_job_template,
        ci_provider: selectedExecutionConfig.ci_provider,
        ci_pipeline_url: selectedExecutionConfig.ci_pipeline_url,
        ci_project: selectedExecutionConfig.ci_project,
        ci_branch: selectedExecutionConfig.ci_branch,
        ci_token_ref: selectedExecutionConfig.ci_token_ref,
        ci_variables: selectedExecutionConfig.ci_variables,
        tool_home: selectedExecutionConfig.tool_home,
        executable_path: selectedExecutionConfig.executable_path,
        working_directory: selectedExecutionConfig.working_directory,
        command: selectedExecutionConfig.command,
        command_template: selectedExecutionConfig.command_template,
        pre_command: selectedExecutionConfig.pre_command,
        post_command: selectedExecutionConfig.post_command,
        result_collection: selectedExecutionConfig.result_collection,
        result_directory: selectedExecutionConfig.result_directory,
        result_file_pattern: selectedExecutionConfig.result_file_pattern,
        report_directory: selectedExecutionConfig.report_directory,
        result_format: selectedExecutionConfig.result_format,
        artifact_patterns: selectedExecutionConfig.artifact_patterns,
        jmeter_properties: selectedExecutionConfig.jmeter_properties,
        distributed_hosts: selectedExecutionConfig.distributed_hosts,
        environment_variables: selectedExecutionConfig.environment_variables,
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
          <Button onClick={startExecution} disabled={selectedCases.length === 0 || !selectedExecutionConfig || startAutomation.isPending}>
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
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Settings className="h-5 w-5" />
              执行配置
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={loadExecutionConfigs} disabled={executionConfigLoading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                {executionConfigLoading ? '刷新中' : '刷新配置'}
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link to="/config">去配置项维护</Link>
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {executionConfigError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
              {executionConfigError}
            </div>
          )}
          {!executionConfigLoading && enabledExecutionConfigs.length === 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              当前没有启用的测试执行配置，请先在“配置项 - 测试执行配置”中创建或初始化配置。
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-[180px_minmax(260px,1fr)]">
            <div>
              <label className="mb-2 block text-sm font-medium">环境</label>
              <Select value={executionEnvironment} onValueChange={(value) => setExecutionEnvironment(value as TestExecutionEnvironment)} disabled={executionConfigLoading || !availableEnvironments.length}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {availableEnvironments.map((environment) => (
                    <SelectItem key={environment.value} value={environment.value}>{environment.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">执行方式</label>
              <Select value={selectedExecutionConfig?.id || ''} onValueChange={setSelectedConfigId} disabled={executionConfigLoading || !environmentConfigs.length}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {environmentConfigs.map((config) => (
                    <SelectItem key={config.id} value={config.id}>
                      {config.name}（{config.framework_label || config.framework}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {selectedExecutionConfig && (
            <div className="grid gap-3 rounded-md border bg-muted/20 p-3 text-sm md:grid-cols-6">
              <div>
                <div className="text-xs text-muted-foreground">执行方式</div>
                <div className="font-medium">{selectedExecutionConfig.framework_label || selectedExecutionConfig.framework}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">执行节点</div>
                <div className="font-medium">
                  {selectedExecutionConfig.runner_name || RUNNER_TYPE_OPTIONS.find((item) => item.value === selectedExecutionConfig.runner_type)?.label || selectedExecutionConfig.runner_type || '本机执行'}
                </div>
                {selectedExecutionConfig.runner_host && (
                  <div className="truncate text-xs text-muted-foreground">
                    {selectedExecutionConfig.runner_user ? `${selectedExecutionConfig.runner_user}@` : ''}{selectedExecutionConfig.runner_host}
                    {selectedExecutionConfig.runner_port ? `:${selectedExecutionConfig.runner_port}` : ''}
                  </div>
                )}
                {selectedExecutionConfig.docker_image && <div className="truncate text-xs text-muted-foreground">{selectedExecutionConfig.docker_image}</div>}
                {selectedExecutionConfig.agent_id && <div className="truncate text-xs text-muted-foreground">{selectedExecutionConfig.agent_id}</div>}
                {selectedExecutionConfig.kubernetes_namespace && <div className="truncate text-xs text-muted-foreground">{selectedExecutionConfig.kubernetes_namespace}</div>}
                {selectedExecutionConfig.ci_provider && <div className="truncate text-xs text-muted-foreground">{selectedExecutionConfig.ci_provider}</div>}
              </div>
              <div>
                <div className="text-xs text-muted-foreground">并发 / 重试</div>
                <div className="font-medium">{selectedExecutionConfig.parallel_count} / {selectedExecutionConfig.retry_count}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">超时</div>
                <div className="font-medium">{selectedExecutionConfig.timeout}s</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">结果采集</div>
                <div className="font-medium">
                  {RESULT_COLLECTION_OPTIONS.find((item) => item.value === selectedExecutionConfig.result_collection)?.label || selectedExecutionConfig.result_collection || '-'}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">命令/模板</div>
                <div className="font-medium">{selectedExecutionConfig.command ? '固定命令' : selectedExecutionConfig.command_template ? '命令模板' : '按脚本类型执行'}</div>
              </div>
            </div>
          )}
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
              <div><p className="text-2xl font-semibold text-blue-600 dark:text-blue-400">{executionStatus.total_cases}</p><p className="text-sm text-muted-foreground">总数</p></div>
              <div><p className="text-2xl font-semibold text-emerald-600 dark:text-emerald-400">{executionStatus.completed_cases}</p><p className="text-sm text-muted-foreground">已完成</p></div>
              <div><p className="text-2xl font-semibold text-green-600 dark:text-green-400">{executionStatus.passed_cases}</p><p className="text-sm text-muted-foreground">通过</p></div>
              <div><p className="text-2xl font-semibold text-red-600 dark:text-red-400">{executionStatus.failed_cases}</p><p className="text-sm text-muted-foreground">失败</p></div>
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
                          <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-red-600 dark:text-red-400">{result.failure_reason}</p>
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
