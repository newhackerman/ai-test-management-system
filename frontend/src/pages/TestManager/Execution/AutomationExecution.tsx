import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, FileText, Monitor, Play, Settings, Square } from 'lucide-react'
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
import { AutomationLevel, ExecutionStatus } from '../../../types/testmanager'

const statusLabels: Record<string, string> = {
  PENDING: '待执行',
  RUNNING: '执行中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  [ExecutionStatus.NOT_EXECUTED]: '未执行',
  [ExecutionStatus.IN_PROGRESS]: '执行中',
  [ExecutionStatus.PASSED]: '通过',
  [ExecutionStatus.FAILED]: '失败',
  [ExecutionStatus.BLOCKED]: '阻塞',
  [ExecutionStatus.SKIPPED]: '跳过',
}

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  PENDING: 'secondary',
  RUNNING: 'default',
  COMPLETED: 'default',
  CANCELLED: 'outline',
  [ExecutionStatus.NOT_EXECUTED]: 'secondary',
  [ExecutionStatus.IN_PROGRESS]: 'default',
  [ExecutionStatus.PASSED]: 'default',
  [ExecutionStatus.FAILED]: 'destructive',
  [ExecutionStatus.BLOCKED]: 'secondary',
  [ExecutionStatus.SKIPPED]: 'outline',
}

const AutomationExecution: React.FC = () => {
  const [selectedCases, setSelectedCases] = useState<number[]>([])
  const [activeExecutionId, setActiveExecutionId] = useState<string>('')
  const [executionConfig, setExecutionConfig] = useState({
    framework: 'playwright',
    browser: 'chrome',
    environment: 'test',
    parallel: 1,
    retry: 1,
    headless: true,
  })

  const { data: testCasesData } = useTestCases({
    automation_level: AutomationLevel.FULL_AUTO,
    page: 1,
    size: 50,
  })
  const startAutomation = useStartAutomationExecution()
  const cancelAutomation = useCancelAutomationExecution()
  const statusQuery = useAutomationExecutionStatus(activeExecutionId)

  const testCases = testCasesData?.data || []
  const executionStatus = statusQuery.data
  const isRunning = executionStatus?.status === 'RUNNING' || executionStatus?.status === 'PENDING'
  const logs = executionStatus?.execution_logs || []
  const results = executionStatus?.test_results || []

  const progressValue = executionStatus?.progress_percentage || 0
  const selectedCaseSet = useMemo(() => new Set(selectedCases), [selectedCases])

  const handleCaseSelection = (caseId: number) => {
    setSelectedCases((prev) =>
      prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev, caseId]
    )
  }

  const handleSelectAll = () => {
    if (!testCases.length) return
    setSelectedCases((prev) => (prev.length === testCases.length ? [] : testCases.map((item) => item.id)))
  }

  const handleStartExecution = async () => {
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

  const handleStopExecution = async () => {
    if (!activeExecutionId) return
    await cancelAutomation.mutateAsync(activeExecutionId)
  }

  const getStatusBadge = (status?: string) => {
    const value = status || 'PENDING'
    return <Badge variant={statusVariants[value] || 'secondary'}>{statusLabels[value] || value}</Badge>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/executions">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回执行列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">自动化测试执行</h1>
            <p className="text-gray-600">配置和运行自动化测试用例</p>
          </div>
        </div>
        <div className="flex space-x-2">
          {!isRunning ? (
            <Button onClick={handleStartExecution} disabled={selectedCases.length === 0 || startAutomation.isPending}>
              <Play className="w-4 h-4 mr-2" />
              {startAutomation.isPending ? '启动中...' : '开始执行'}
            </Button>
          ) : (
            <Button variant="outline" onClick={handleStopExecution} disabled={cancelAutomation.isPending}>
              <Square className="w-4 h-4 mr-2" />
              {cancelAutomation.isPending ? '停止中...' : '停止执行'}
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>执行配置</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            <div>
              <label className="block text-sm font-medium mb-2">自动化框架</label>
              <Select value={executionConfig.framework} onValueChange={(value) => setExecutionConfig((prev) => ({ ...prev, framework: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="playwright">Playwright</SelectItem>
                  <SelectItem value="selenium">Selenium</SelectItem>
                  <SelectItem value="cypress">Cypress</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">浏览器</label>
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
              <label className="block text-sm font-medium mb-2">测试环境</label>
              <Select value={executionConfig.environment} onValueChange={(value) => setExecutionConfig((prev) => ({ ...prev, environment: value }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="test">测试环境</SelectItem>
                  <SelectItem value="staging">预生产环境</SelectItem>
                  <SelectItem value="dev">开发环境</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">并发数</label>
              <Input
                type="number"
                min="1"
                max="10"
                value={executionConfig.parallel}
                onChange={(event) => setExecutionConfig((prev) => ({ ...prev, parallel: Number(event.target.value) || 1 }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">重试次数</label>
              <Input
                type="number"
                min="0"
                max="5"
                value={executionConfig.retry}
                onChange={(event) => setExecutionConfig((prev) => ({ ...prev, retry: Number(event.target.value) || 0 }))}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2 mt-4">
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
            <CardTitle className="flex items-center space-x-2">
              <Monitor className="w-5 h-5" />
              <span>执行进度</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">批次号: {executionStatus.execution_id}</div>
                {getStatusBadge(executionStatus.status)}
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>总体进度</span>
                  <span>{progressValue.toFixed(1)}%</span>
                </div>
                <Progress value={progressValue} className="h-3" />
              </div>
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-blue-600">{executionStatus.total_cases}</p>
                  <p className="text-sm text-gray-600">总用例数</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">{executionStatus.completed_cases}</p>
                  <p className="text-sm text-gray-600">已完成</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-emerald-600">{executionStatus.passed_cases}</p>
                  <p className="text-sm text-gray-600">通过</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-red-600">{executionStatus.failed_cases}</p>
                  <p className="text-sm text-gray-600">失败</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>选择测试用例</CardTitle>
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm" onClick={handleSelectAll} disabled={!testCases.length || isRunning}>
                  {selectedCases.length === testCases.length && testCases.length > 0 ? '取消全选' : '全选'}
                </Button>
                <span className="text-sm text-gray-600">已选择 {selectedCases.length} / {testCases.length}</span>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedCases.length === testCases.length && testCases.length > 0}
                        onCheckedChange={handleSelectAll}
                        disabled={!testCases.length || isRunning}
                      />
                    </TableHead>
                    <TableHead>用例名称</TableHead>
                    <TableHead>模块</TableHead>
                    <TableHead>优先级</TableHead>
                    <TableHead>自动化程度</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {testCases.map((testCase) => (
                    <TableRow key={testCase.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedCaseSet.has(testCase.id)}
                          onCheckedChange={() => handleCaseSelection(testCase.id)}
                          disabled={isRunning}
                        />
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{testCase.case_title}</p>
                          <p className="text-sm text-gray-500">{testCase.case_code}</p>
                        </div>
                      </TableCell>
                      <TableCell>{testCase.module || '未分类'}</TableCell>
                      <TableCell><Badge variant="outline">{testCase.priority}</Badge></TableCell>
                      <TableCell><Badge variant="secondary">{testCase.automation_level}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {testCases.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无可用的自动化测试用例</div>
              )}
            </CardContent>
          </Card>
        </div>

        <div>
          <Tabs defaultValue="logs" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="logs">执行日志</TabsTrigger>
              <TabsTrigger value="results">执行结果</TabsTrigger>
            </TabsList>

            <TabsContent value="logs">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-5 h-5" />
                    <span>实时日志</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-64 w-full border rounded p-3 bg-gray-50">
                    {logs.length ? (
                      <div className="space-y-1">
                        {logs.map((log, index) => (
                          <div key={index} className="text-sm font-mono">
                            <span className="text-gray-500">{log.time ? new Date(log.time).toLocaleTimeString() : '-'}</span>
                            <span className="ml-2">[{log.level || 'INFO'}] {log.message || JSON.stringify(log)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500">暂无执行日志</div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="results">
              <Card>
                <CardHeader>
                  <CardTitle>执行结果</CardTitle>
                </CardHeader>
                <CardContent>
                  {results.length ? (
                    <div className="space-y-3">
                      {results.map((result) => (
                        <div key={result.execution_id || result.test_case_id} className="flex items-center justify-between p-3 border rounded">
                          <div>
                            <p className="font-medium">{result.case_title || result.case_code}</p>
                            <p className="text-sm text-gray-500">{result.execution_code}</p>
                          </div>
                          {getStatusBadge(result.status)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500">暂无执行结果</div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default AutomationExecution
