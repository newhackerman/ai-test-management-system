import React, { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Camera, CheckCircle, Clock, Play, Search, XCircle } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/Dialog'
import { Input } from '../../../components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Textarea } from '../../../components/ui/Textarea'
import { useCompleteExecution, useStartManualExecution, useUploadScreenshot } from '../../../hooks/testmanager/useExecution'
import { useTestCase, useTestCases } from '../../../hooks/testmanager/useTestCase'
import { ExecutionStatus, Priority, TestCaseStatus } from '../../../types/testmanager'

type StepResult = {
  status: ExecutionStatus
  actualResult: string
  notes: string
}

const priorityLabels: Record<string, string> = {
  [Priority.CRITICAL]: '紧急',
  [Priority.HIGH]: '高',
  [Priority.MEDIUM]: '中',
  [Priority.LOW]: '低',
}

const statusLabels: Record<string, string> = {
  [ExecutionStatus.PASSED]: '通过',
  [ExecutionStatus.FAILED]: '失败',
  [ExecutionStatus.BLOCKED]: '阻塞',
  [ExecutionStatus.SKIPPED]: '跳过',
}

const getStepNumber = (step: any, index: number) => step?.step_number ?? step?.step ?? step?.index ?? index + 1
const getStepAction = (step: any) => step?.action ?? step?.description ?? step?.step_description ?? step?.operation ?? '-'
const getStepExpected = (step: any) => step?.expected_result ?? step?.expected ?? step?.expectedResult ?? '-'

const ManualExecution: React.FC = () => {
  const { testCaseId } = useParams<{ testCaseId?: string }>()
  const navigate = useNavigate()
  const caseId = Number(testCaseId || 0)

  const [currentExecution, setCurrentExecution] = useState<any>(null)
  const [stepResults, setStepResults] = useState<Record<number, StepResult>>({})
  const [environment, setEnvironment] = useState('test')
  const [browserInfo, setBrowserInfo] = useState('')
  const [actualResult, setActualResult] = useState('')
  const [failureReason, setFailureReason] = useState('')
  const [executionNotes, setExecutionNotes] = useState('')
  const [search, setSearch] = useState('')
  const [showScreenshotDialog, setShowScreenshotDialog] = useState(false)

  const { data: testCasesData, isLoading: isCaseListLoading } = useTestCases({
    page: 1,
    size: 100,
  })
  const { data: testCase, isLoading } = useTestCase(caseId)
  const startExecution = useStartManualExecution()
  const completeExecution = useCompleteExecution()
  const uploadScreenshot = useUploadScreenshot()

  const executableCases = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    return (testCasesData?.data || [])
      .filter((item) => item.status !== TestCaseStatus.ARCHIVED && item.status !== TestCaseStatus.DEPRECATED)
      .filter((item) => {
        if (!keyword) return true
        return `${item.case_code} ${item.case_title} ${item.module || ''}`.toLowerCase().includes(keyword)
      })
  }, [search, testCasesData?.data])

  const steps = testCase?.test_steps || []
  const completedSteps = Object.values(stepResults)
  const failedCount = completedSteps.filter((item) => item.status === ExecutionStatus.FAILED).length
  const passedCount = completedSteps.filter((item) => item.status === ExecutionStatus.PASSED).length
  const blockedCount = completedSteps.filter((item) => item.status === ExecutionStatus.BLOCKED).length

  const updateStepResult = (stepIndex: number, patch: Partial<StepResult>) => {
    setStepResults((prev) => ({
      ...prev,
      [stepIndex]: {
        status: prev[stepIndex]?.status || ExecutionStatus.PASSED,
        actualResult: prev[stepIndex]?.actualResult || '',
        notes: prev[stepIndex]?.notes || '',
        ...patch,
      },
    }))
  }

  const handleStartExecution = async () => {
    const execution = await startExecution.mutateAsync({
      test_case_id: caseId,
      test_environment: environment,
      browser_info: browserInfo,
      os_info: navigator.userAgent,
    })
    setCurrentExecution(execution)
  }

  const inferFinalStatus = () => {
    if (failedCount > 0) return ExecutionStatus.FAILED
    if (blockedCount > 0) return ExecutionStatus.BLOCKED
    if (steps.length > 0 && passedCount === steps.length) return ExecutionStatus.PASSED
    if (steps.length === 0 && actualResult.trim()) return ExecutionStatus.PASSED
    return ExecutionStatus.BLOCKED
  }

  const buildStepLogs = () => steps.map((step: any, index: number) => {
    const result = stepResults[index]
    return {
      type: 'step',
      step_index: index,
      step_number: getStepNumber(step, index),
      action: getStepAction(step),
      expected_result: getStepExpected(step),
      status: result?.status || ExecutionStatus.BLOCKED,
      actual_result: result?.actualResult || '',
      notes: result?.notes || '',
      recorded_at: new Date().toISOString(),
    }
  })

  const handleCompleteExecution = async () => {
    if (!currentExecution) return
    const finalStatus = inferFinalStatus()
    const defaultActualResult = [
      `步骤总数：${steps.length}`,
      `通过：${passedCount}`,
      `失败：${failedCount}`,
      `阻塞：${blockedCount}`,
    ].join('；')

    const completed = await completeExecution.mutateAsync({
      id: currentExecution.id,
      data: {
        execution_status: finalStatus,
        actual_result: actualResult.trim() || defaultActualResult,
        failure_reason: finalStatus === ExecutionStatus.FAILED ? failureReason : undefined,
        execution_notes: executionNotes,
        logs: [
          ...buildStepLogs(),
          {
            type: 'summary',
            status: finalStatus,
            actual_result: actualResult.trim() || defaultActualResult,
            notes: executionNotes,
            recorded_at: new Date().toISOString(),
          },
        ],
      },
    })
    navigate(`/test-manager/executions/${completed.id}`)
  }

  const handleScreenshotUpload = async (file: File) => {
    if (!currentExecution) return
    await uploadScreenshot.mutateAsync({ id: currentExecution.id, file })
    setShowScreenshotDialog(false)
  }

  const stepStatusBadge = (status?: ExecutionStatus) => {
    if (!status) return <Badge variant="secondary">待执行</Badge>
    const variant = status === ExecutionStatus.FAILED
      ? 'destructive'
      : status === ExecutionStatus.PASSED
        ? 'default'
        : 'secondary'
    return <Badge variant={variant}>{statusLabels[status] || status}</Badge>
  }

  if (!caseId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/test-manager/executions">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回执行管理
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">选择手工执行用例</h1>
            <p className="text-sm text-muted-foreground">草稿、已审批和启用状态的用例都可以执行</p>
          </div>
        </div>

        <Card>
          <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-lg">可执行测试用例</CardTitle>
            <div className="relative md:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="搜索用例编号、标题或模块" value={search} onChange={(event) => setSearch(event.target.value)} />
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[150px]">用例编号</TableHead>
                  <TableHead>用例标题</TableHead>
                  <TableHead className="w-[120px]">模块</TableHead>
                  <TableHead className="w-[90px]">优先级</TableHead>
                  <TableHead className="w-[90px]">状态</TableHead>
                  <TableHead className="w-[100px] text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isCaseListLoading ? (
                  <TableRow><TableCell colSpan={6} className="h-24 text-center text-muted-foreground">加载中...</TableCell></TableRow>
                ) : executableCases.length ? executableCases.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.case_code}</TableCell>
                    <TableCell className="font-medium">{item.case_title}</TableCell>
                    <TableCell>{item.module || '-'}</TableCell>
                    <TableCell><Badge variant="outline">{priorityLabels[item.priority] || item.priority}</Badge></TableCell>
                    <TableCell><Badge variant="secondary">{item.status}</Badge></TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm">
                        <Link to={`/test-manager/executions/manual/${item.id}`}>
                          <Play className="mr-2 h-4 w-4" />
                          执行
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow><TableCell colSpan={6} className="h-24 text-center text-muted-foreground">暂无可执行测试用例</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center text-muted-foreground">加载中...</div>
  }

  if (!testCase) {
    return <div className="py-16 text-center text-destructive">测试用例不存在</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/test-manager/executions/manual">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回用例选择
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">手工执行</h1>
            <p className="text-sm text-muted-foreground">{testCase.case_code} · {testCase.case_title}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!currentExecution ? (
            <Button onClick={handleStartExecution} disabled={startExecution.isPending}>
              <Play className="mr-2 h-4 w-4" />
              {startExecution.isPending ? '启动中...' : '开始执行'}
            </Button>
          ) : (
            <>
              <Dialog open={showScreenshotDialog} onOpenChange={setShowScreenshotDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Camera className="mr-2 h-4 w-4" />
                    截图
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>上传截图</DialogTitle></DialogHeader>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) handleScreenshotUpload(file)
                    }}
                    className="block w-full text-sm text-muted-foreground"
                  />
                </DialogContent>
              </Dialog>
              <Button onClick={handleCompleteExecution} disabled={completeExecution.isPending}>
                <CheckCircle className="mr-2 h-4 w-4" />
                {completeExecution.isPending ? '保存中...' : '完成并保存'}
              </Button>
            </>
          )}
        </div>
      </div>

      {!currentExecution && (
        <Card>
          <CardHeader><CardTitle className="text-lg">执行环境</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">测试环境</label>
              <Select value={environment} onValueChange={setEnvironment}>
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
              <label className="mb-2 block text-sm font-medium">浏览器/客户端</label>
              <Input placeholder="例如 Chrome 125 / iOS App" value={browserInfo} onChange={(event) => setBrowserInfo(event.target.value)} />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="gap-2 md:flex-row md:items-center md:justify-between">
              <CardTitle className="text-lg">执行步骤</CardTitle>
              <div className="text-sm text-muted-foreground">
                已记录 {completedSteps.length} / {steps.length}，通过 {passedCount}，失败 {failedCount}
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">步骤</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>预期结果</TableHead>
                    <TableHead className="w-[230px]">实际结果</TableHead>
                    <TableHead className="w-[90px]">状态</TableHead>
                    <TableHead className="w-[120px] text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {steps.length ? steps.map((step: any, index: number) => {
                    const result = stepResults[index]
                    return (
                      <TableRow key={index}>
                        <TableCell>{getStepNumber(step, index)}</TableCell>
                        <TableCell className="min-w-[180px]">{getStepAction(step)}</TableCell>
                        <TableCell className="min-w-[180px]">{getStepExpected(step)}</TableCell>
                        <TableCell>
                          <Textarea
                            disabled={!currentExecution}
                            rows={2}
                            placeholder="记录实际结果"
                            value={result?.actualResult || ''}
                            onChange={(event) => updateStepResult(index, { actualResult: event.target.value })}
                          />
                        </TableCell>
                        <TableCell>{stepStatusBadge(result?.status)}</TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button disabled={!currentExecution} variant="outline" size="icon" title="通过" onClick={() => updateStepResult(index, { status: ExecutionStatus.PASSED })}>
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button disabled={!currentExecution} variant="outline" size="icon" title="失败" onClick={() => updateStepResult(index, { status: ExecutionStatus.FAILED })}>
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  }) : (
                    <TableRow><TableCell colSpan={6} className="h-24 text-center text-muted-foreground">该用例暂无步骤，可在右侧填写整体结果后保存</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">用例信息</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div><p className="text-muted-foreground">描述</p><p className="mt-1 whitespace-pre-wrap">{testCase.case_description || '-'}</p></div>
              <div><p className="text-muted-foreground">前置条件</p><p className="mt-1 whitespace-pre-wrap">{testCase.preconditions || '-'}</p></div>
              <div><p className="text-muted-foreground">预期结果</p><p className="mt-1 whitespace-pre-wrap">{testCase.expected_result || '-'}</p></div>
            </CardContent>
          </Card>

          {currentExecution && (
            <Card>
              <CardHeader><CardTitle className="text-lg">执行结论</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium">整体实际结果</label>
                  <Textarea rows={3} value={actualResult} onChange={(event) => setActualResult(event.target.value)} placeholder="概述本次执行观察到的结果" />
                </div>
                {failedCount > 0 && (
                  <div>
                    <label className="mb-2 block text-sm font-medium">失败原因</label>
                    <Textarea rows={3} value={failureReason} onChange={(event) => setFailureReason(event.target.value)} placeholder="失败步骤、错误现象、初步原因" />
                  </div>
                )}
                <div>
                  <label className="mb-2 block text-sm font-medium">执行备注</label>
                  <Textarea rows={3} value={executionNotes} onChange={(event) => setExecutionNotes(event.target.value)} placeholder="环境差异、数据准备、风险说明等" />
                </div>
                <div className="border-t pt-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    <span>开始时间：{currentExecution.started_at ? new Date(currentExecution.started_at).toLocaleString() : '-'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default ManualExecution
