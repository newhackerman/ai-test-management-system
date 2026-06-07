import React, { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Camera, CheckCircle, Clock, Play, XCircle } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/Dialog'
import { Input } from '../../../components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Textarea } from '../../../components/ui/Textarea'
import { useTestCase, useTestCases } from '../../../hooks/testmanager/useTestCase'
import { useCompleteExecution, useStartManualExecution, useUploadScreenshot } from '../../../hooks/testmanager/useExecution'
import { ExecutionStatus, TestCaseStatus } from '../../../types/testmanager'

const ManualExecution: React.FC = () => {
  const { testCaseId } = useParams<{ testCaseId?: string }>()
  const navigate = useNavigate()
  const caseId = Number(testCaseId || 0)

  const [currentExecution, setCurrentExecution] = useState<any>(null)
  const [stepResults, setStepResults] = useState<Record<number, { status: ExecutionStatus; actualResult: string; notes: string }>>({})
  const [environment, setEnvironment] = useState('test')
  const [browserInfo, setBrowserInfo] = useState('')
  const [actualResult, setActualResult] = useState('')
  const [executionNotes, setExecutionNotes] = useState('')
  const [showScreenshotDialog, setShowScreenshotDialog] = useState(false)

  const { data: testCasesData, isLoading: isCaseListLoading } = useTestCases({
    status: TestCaseStatus.ACTIVE,
    page: 1,
    size: 50,
  })
  const { data: testCase, isLoading } = useTestCase(caseId)
  const startExecution = useStartManualExecution()
  const completeExecution = useCompleteExecution()
  const uploadScreenshot = useUploadScreenshot()

  const testCases = testCasesData?.data || []

  const handleStartExecution = async () => {
    const execution = await startExecution.mutateAsync({
      test_case_id: caseId,
      test_environment: environment,
      browser_info: browserInfo,
      os_info: navigator.userAgent,
    })
    setCurrentExecution(execution)
  }

  const handleStepResult = (stepIndex: number, status: ExecutionStatus, stepActualResult: string, notes: string) => {
    setStepResults((prev) => ({
      ...prev,
      [stepIndex]: { status, actualResult: stepActualResult, notes },
    }))
  }

  const handleCompleteExecution = async () => {
    if (!currentExecution) return

    const stepCount = testCase?.test_steps?.length || 0
    const completedStepResults = Object.values(stepResults)
    const hasFailedSteps = completedStepResults.some((result) => result.status === ExecutionStatus.FAILED)
    const allStepsPassed = stepCount > 0 && completedStepResults.length === stepCount &&
      completedStepResults.every((result) => result.status === ExecutionStatus.PASSED)
    const finalStatus = hasFailedSteps ? ExecutionStatus.FAILED : allStepsPassed ? ExecutionStatus.PASSED : ExecutionStatus.BLOCKED

    await completeExecution.mutateAsync({
      id: currentExecution.id,
      data: {
        execution_status: finalStatus,
        actual_result: actualResult,
        execution_notes: executionNotes,
      },
    })
    navigate('/test-manager/executions')
  }

  const handleScreenshotUpload = async (file: File) => {
    if (!currentExecution) return
    await uploadScreenshot.mutateAsync({ id: currentExecution.id, file })
    setShowScreenshotDialog(false)
  }

  const getStepStatusBadge = (status?: ExecutionStatus) => {
    if (!status) return <Badge variant="secondary">待执行</Badge>
    const statusConfig = {
      [ExecutionStatus.PASSED]: { label: '通过', variant: 'default' as const },
      [ExecutionStatus.FAILED]: { label: '失败', variant: 'destructive' as const },
      [ExecutionStatus.BLOCKED]: { label: '阻塞', variant: 'secondary' as const },
      [ExecutionStatus.SKIPPED]: { label: '跳过', variant: 'outline' as const },
    }
    const config = statusConfig[status as keyof typeof statusConfig] || { label: status, variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  if (!caseId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/executions">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回执行列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">选择手动执行用例</h1>
            <p className="text-gray-600">从已激活的测试用例中选择一条开始执行</p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>可执行测试用例</CardTitle>
          </CardHeader>
          <CardContent>
            {isCaseListLoading ? (
              <div className="py-8 text-center text-gray-500">加载中...</div>
            ) : testCases.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>用例编号</TableHead>
                    <TableHead>用例名称</TableHead>
                    <TableHead>模块</TableHead>
                    <TableHead>优先级</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {testCases.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.case_code}</TableCell>
                      <TableCell className="font-medium">{item.case_title}</TableCell>
                      <TableCell>{item.module || '-'}</TableCell>
                      <TableCell><Badge variant="outline">{item.priority}</Badge></TableCell>
                      <TableCell className="text-right">
                        <Link to={`/test-manager/executions/manual/${item.id}`}>
                          <Button size="sm">
                            <Play className="w-4 h-4 mr-2" />
                            开始执行
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="py-8 text-center text-gray-500">暂无已激活的测试用例</div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (!testCase) {
    return <div className="text-red-500 text-center">测试用例不存在</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/executions/manual">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回用例选择
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">手动测试执行</h1>
            <p className="text-gray-600">{testCase.case_title}</p>
          </div>
        </div>
        <div className="flex space-x-2">
          {!currentExecution ? (
            <Button onClick={handleStartExecution} disabled={startExecution.isPending}>
              <Play className="w-4 h-4 mr-2" />
              {startExecution.isPending ? '启动中...' : '开始执行'}
            </Button>
          ) : (
            <>
              <Dialog open={showScreenshotDialog} onOpenChange={setShowScreenshotDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Camera className="w-4 h-4 mr-2" />
                    截图
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>上传截图</DialogTitle>
                  </DialogHeader>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) handleScreenshotUpload(file)
                    }}
                    className="block w-full text-sm text-gray-500"
                  />
                </DialogContent>
              </Dialog>

              <Button onClick={handleCompleteExecution} disabled={completeExecution.isPending}>
                <CheckCircle className="w-4 h-4 mr-2" />
                {completeExecution.isPending ? '完成中...' : '完成执行'}
              </Button>
            </>
          )}
        </div>
      </div>

      {!currentExecution && (
        <Card>
          <CardHeader>
            <CardTitle>执行环境配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-2">测试环境</label>
                <Select value={environment} onValueChange={setEnvironment}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="test">测试环境</SelectItem>
                    <SelectItem value="staging">预生产环境</SelectItem>
                    <SelectItem value="dev">开发环境</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">浏览器信息</label>
                <Input
                  placeholder="请输入浏览器信息"
                  value={browserInfo}
                  onChange={(event) => setBrowserInfo(event.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>测试步骤</CardTitle>
            </CardHeader>
            <CardContent>
              {testCase.test_steps?.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">步骤</TableHead>
                      <TableHead>操作</TableHead>
                      <TableHead>预期结果</TableHead>
                      <TableHead>实际结果</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {testCase.test_steps.map((step, index) => {
                      const stepResult = stepResults[index]
                      return (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{step.step_number || index + 1}</TableCell>
                          <TableCell>{step.action}</TableCell>
                          <TableCell>{step.expected_result}</TableCell>
                          <TableCell>
                            {currentExecution && (
                              <Textarea
                                placeholder="输入实际结果"
                                value={stepResult?.actualResult || ''}
                                onChange={(event) =>
                                  handleStepResult(index, stepResult?.status || ExecutionStatus.PASSED, event.target.value, stepResult?.notes || '')
                                }
                                rows={2}
                                className="min-w-[200px]"
                              />
                            )}
                          </TableCell>
                          <TableCell>{getStepStatusBadge(stepResult?.status)}</TableCell>
                          <TableCell>
                            {currentExecution && (
                              <div className="flex space-x-1">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleStepResult(index, ExecutionStatus.PASSED, stepResult?.actualResult || '', stepResult?.notes || '')}
                                >
                                  <CheckCircle className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleStepResult(index, ExecutionStatus.FAILED, stepResult?.actualResult || '', stepResult?.notes || '')}
                                >
                                  <XCircle className="w-4 h-4" />
                                </Button>
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-gray-500">暂无测试步骤</div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>用例信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-600">用例编号</label>
                <p>{testCase.case_code}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600">用例描述</label>
                <p>{testCase.case_description || '暂无描述'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600">前置条件</label>
                <p>{testCase.preconditions || '无特殊前置条件'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600">预期结果</label>
                <p>{testCase.expected_result || '暂无定义'}</p>
              </div>
            </CardContent>
          </Card>

          {currentExecution && (
            <Card>
              <CardHeader>
                <CardTitle>执行记录</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">总体实际结果</label>
                  <Textarea
                    placeholder="输入总体实际结果"
                    value={actualResult}
                    onChange={(event) => setActualResult(event.target.value)}
                    rows={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">执行备注</label>
                  <Textarea
                    placeholder="输入执行备注"
                    value={executionNotes}
                    onChange={(event) => setExecutionNotes(event.target.value)}
                    rows={3}
                  />
                </div>
                <div className="pt-4 border-t">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Clock className="w-4 h-4" />
                    <span>执行时间: {currentExecution.started_at ? new Date(currentExecution.started_at).toLocaleString() : '-'}</span>
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
