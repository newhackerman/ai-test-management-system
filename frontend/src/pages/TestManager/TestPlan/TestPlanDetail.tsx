import React, { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Edit, Play, Pause, CheckCircle, Download, Users, Calendar, Target, Link2, Unlink, Search, Clock, Bug, FileText } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Progress } from '../../../components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import { Input } from '../../../components/ui/Input'
import { Checkbox } from '../../../components/ui/Checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { useBatchUpdateTestCases, useTestCases, useUpdateTestCase } from '../../../hooks/testmanager/useTestCase'
import { useDefects } from '../../../hooks/testmanager/useDefect'
import { useExecutions } from '../../../hooks/testmanager/useExecution'
import { useExportTestPlan, useTestPlan, useTestPlanProgress, useUpdateTestPlanStatus } from '../../../hooks/testmanager/useTestPlan'
import { reportService } from '../../../services/testmanager/reportService'
import { Priority, TestCaseStatus, TestPlanStatus, TestType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const TestPlanDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const planId = parseInt(id!, 10)
  const queryClient = useQueryClient()
  const [caseSearch, setCaseSearch] = useState('')
  const [selectedCaseIds, setSelectedCaseIds] = useState<number[]>([])
  const linkedCasesFilters = useMemo(() => ({ test_plan_id: planId, page: 1, size: 100 }), [planId])
  const candidateCasesFilters = useMemo(() => ({ search: caseSearch, page: 1, size: 100 }), [caseSearch])
  const executionFilters = useMemo(() => ({ test_plan_id: planId, page: 1, size: 20 }), [planId])
  const defectFilters = useMemo(() => ({ test_plan_id: planId, page: 1, size: 20 }), [planId])
  const reportFilters = useMemo(() => ({ test_plan_id: planId, page: 1, size: 20 }), [planId])

  const { data: testPlan, isLoading, error } = useTestPlan(planId)
  const { data: progress } = useTestPlanProgress(planId)
  const { data: linkedCasesData, isLoading: linkedCasesLoading } = useTestCases(linkedCasesFilters)
  const { data: candidateCasesData, isLoading: candidateCasesLoading } = useTestCases(candidateCasesFilters)
  const { data: executionsData, isLoading: executionsLoading } = useExecutions(executionFilters)
  const { data: defectsData, isLoading: defectsLoading } = useDefects(defectFilters)
  const { data: reportsData, isLoading: reportsLoading } = useQuery({
    queryKey: ['testReports', reportFilters],
    queryFn: () => reportService.getReports(reportFilters),
    enabled: Number.isFinite(planId) && planId > 0,
    staleTime: 30 * 1000,
  })
  const exportTestPlan = useExportTestPlan()
  const updateTestPlanStatus = useUpdateTestPlanStatus()
  const updateTestCase = useUpdateTestCase()
  const batchUpdateTestCases = useBatchUpdateTestCases()

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (error || !testPlan) {
    return <div className="text-red-500 text-center">加载失败</div>
  }

  const getStatusBadge = (status: TestPlanStatus) => {
    const statusConfig = {
      [TestPlanStatus.DRAFT]: { label: '草稿', variant: 'secondary' as const },
      [TestPlanStatus.APPROVED]: { label: '已批准', variant: 'default' as const },
      [TestPlanStatus.IN_PROGRESS]: { label: '进行中', variant: 'default' as const },
      [TestPlanStatus.PAUSED]: { label: '暂停', variant: 'secondary' as const },
      [TestPlanStatus.COMPLETED]: { label: '已完成', variant: 'default' as const },
      [TestPlanStatus.CANCELLED]: { label: '已取消', variant: 'destructive' as const },
    }
    
    const config = statusConfig[status]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getTypeLabel = (type: TestType) => {
    const typeLabels = {
      [TestType.FUNCTIONAL]: '功能测试',
      [TestType.PERFORMANCE]: '性能测试',
      [TestType.SECURITY]: '安全测试',
      [TestType.INTEGRATION]: '集成测试',
      [TestType.REGRESSION]: '回归测试',
      [TestType.ACCEPTANCE]: '验收测试',
    }
    return typeLabels[type] || type
  }

  const getCaseStatusBadge = (status: TestCaseStatus) => {
    const statusConfig = {
      [TestCaseStatus.DRAFT]: { label: '草稿', variant: 'secondary' as const },
      [TestCaseStatus.APPROVED]: { label: '已批准', variant: 'default' as const },
      [TestCaseStatus.ACTIVE]: { label: '活跃', variant: 'default' as const },
      [TestCaseStatus.DEPRECATED]: { label: '已废弃', variant: 'secondary' as const },
      [TestCaseStatus.ARCHIVED]: { label: '已归档', variant: 'outline' as const },
    }
    const config = statusConfig[status] || { label: status, variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getPriorityBadge = (priority: Priority) => {
    const priorityConfig = {
      [Priority.CRITICAL]: { label: '紧急', variant: 'destructive' as const },
      [Priority.HIGH]: { label: '高', variant: 'destructive' as const },
      [Priority.MEDIUM]: { label: '中', variant: 'default' as const },
      [Priority.LOW]: { label: '低', variant: 'secondary' as const },
    }
    const config = priorityConfig[priority] || { label: priority, variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getExecutionStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      NOT_EXECUTED: { label: '未执行', variant: 'secondary' },
      IN_PROGRESS: { label: '执行中', variant: 'default' },
      PASSED: { label: '通过', variant: 'default' },
      FAILED: { label: '失败', variant: 'destructive' },
      BLOCKED: { label: '阻塞', variant: 'destructive' },
      SKIPPED: { label: '跳过', variant: 'outline' },
    }
    const config = statusConfig[status] || { label: status || '-', variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getDefectStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      NEW: { label: '新建', variant: 'destructive' },
      ASSIGNED: { label: '已分配', variant: 'default' },
      IN_PROGRESS: { label: '处理中', variant: 'default' },
      RESOLVED: { label: '已解决', variant: 'secondary' },
      VERIFIED: { label: '已验证', variant: 'secondary' },
      CLOSED: { label: '已关闭', variant: 'outline' },
      REOPENED: { label: '重新打开', variant: 'destructive' },
      REJECTED: { label: '已拒绝', variant: 'outline' },
      DEFERRED: { label: '延期', variant: 'secondary' },
    }
    const config = statusConfig[status] || { label: status || '-', variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getReportStatusBadge = (status: string) => {
    const normalized = (status || '').toUpperCase()
    const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      PENDING: { label: '生成中', variant: 'secondary' },
      PROCESSING: { label: '生成中', variant: 'default' },
      COMPLETED: { label: '已完成', variant: 'default' },
      SUCCESS: { label: '已完成', variant: 'default' },
      FAILED: { label: '失败', variant: 'destructive' },
    }
    const config = statusConfig[normalized] || { label: status || '-', variant: 'secondary' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const executionTypeLabel = (type: string) => ({
    MANUAL: '手工执行',
    AUTOMATED: '自动执行',
  }[type] || type || '-')

  const reportTypeLabel = (type: string) => ({
    EXECUTION: '执行报告',
    DEFECT: '缺陷报告',
    COVERAGE: '覆盖率报告',
    QUALITY: '质量报告',
    PERFORMANCE: '性能报告',
    SECURITY: '安全报告',
  }[type] || type || '-')

  const formatDuration = (duration?: number) => {
    if (!duration && duration !== 0) return '-'
    if (duration < 60) return `${duration}s`
    return `${Math.floor(duration / 60)}m ${duration % 60}s`
  }

  const stats = progress || testPlan
  const executionRate = stats.total_cases > 0 ? (stats.executed_cases / stats.total_cases) * 100 : 0
  const passRate = stats.executed_cases > 0 ? (stats.passed_cases / stats.executed_cases) * 100 : 0
  const updatingStatus = updateTestPlanStatus.isPending
  const linkedCases = linkedCasesData?.data || []
  const executions = executionsData?.data || []
  const defects = defectsData?.data || []
  const reports = reportsData?.data || []
  const linkedCaseIdSet = new Set(linkedCases.map((testCase: any) => Number(testCase.id)))
  const latestExecutionByCaseId = new Map<number, any>()
  executions.forEach((execution: any) => {
    const caseId = Number(execution.test_case_id)
    if (caseId && !latestExecutionByCaseId.has(caseId)) latestExecutionByCaseId.set(caseId, execution)
  })
  const defectCountByCaseId = defects.reduce((result: Record<number, number>, defect: any) => {
    const caseId = Number(defect.test_case_id)
    if (caseId) result[caseId] = (result[caseId] || 0) + 1
    return result
  }, {})
  const candidateCases = (candidateCasesData?.data || []).filter((testCase: any) => Number(testCase.test_plan_id) !== planId)
  const selectableCandidateIds = candidateCases.map((testCase: any) => Number(testCase.id))
  const selectedCandidateIds = selectedCaseIds.filter((caseId) => selectableCandidateIds.includes(caseId))
  const linking = updateTestCase.isPending || batchUpdateTestCases.isPending

  const handleExport = (format: 'csv' | 'txt') => {
    exportTestPlan.mutate({ id: planId, format })
  }

  const handleStatusChange = (status: TestPlanStatus) => {
    updateTestPlanStatus.mutate({ id: planId, status })
  }

  const handleToggleCandidate = (caseId: number) => {
    setSelectedCaseIds((prev) => (
      prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev, caseId]
    ))
  }

  const handleToggleAllCandidates = () => {
    setSelectedCaseIds((prev) => {
      const allSelected = selectableCandidateIds.length > 0 && selectableCandidateIds.every((caseId) => prev.includes(caseId))
      if (allSelected) return prev.filter((caseId) => !selectableCandidateIds.includes(caseId))
      return Array.from(new Set([...prev, ...selectableCandidateIds]))
    })
  }

  const adjustPagedTotal = (oldData: any, delta: number) => {
    if (!oldData || typeof oldData !== 'object' || typeof oldData.total !== 'number') return oldData
    return { ...oldData, total: Math.max(0, oldData.total + delta) }
  }

  const caseMatchesCurrentSearch = (testCase: any) => {
    const keyword = caseSearch.trim().toLowerCase()
    if (!keyword) return true
    return [
      testCase.case_title,
      testCase.case_code,
      testCase.module,
    ].filter(Boolean).join(' ').toLowerCase().includes(keyword)
  }

  const syncCaseAssociationCache = (updatedCase: any, isLinkedToPlan: boolean) => {
    queryClient.setQueryData(['testCases', linkedCasesFilters], (oldData: any) => {
      if (!oldData?.data) return oldData
      const exists = oldData.data.some((testCase: any) => Number(testCase.id) === Number(updatedCase.id))
      if (isLinkedToPlan) {
        return exists
          ? { ...oldData, data: oldData.data.map((testCase: any) => Number(testCase.id) === Number(updatedCase.id) ? updatedCase : testCase) }
          : adjustPagedTotal({ ...oldData, data: [updatedCase, ...oldData.data] }, 1)
      }
      return exists
        ? adjustPagedTotal({ ...oldData, data: oldData.data.filter((testCase: any) => Number(testCase.id) !== Number(updatedCase.id)) }, -1)
        : oldData
    })

    queryClient.setQueryData(['testCases', candidateCasesFilters], (oldData: any) => {
      if (!oldData?.data) return oldData
      const exists = oldData.data.some((testCase: any) => Number(testCase.id) === Number(updatedCase.id))
      if (isLinkedToPlan) {
        return exists
          ? adjustPagedTotal({ ...oldData, data: oldData.data.filter((testCase: any) => Number(testCase.id) !== Number(updatedCase.id)) }, -1)
          : oldData
      }
      if (!caseMatchesCurrentSearch(updatedCase)) return oldData
      return exists
        ? { ...oldData, data: oldData.data.map((testCase: any) => Number(testCase.id) === Number(updatedCase.id) ? updatedCase : testCase) }
        : adjustPagedTotal({ ...oldData, data: [updatedCase, ...oldData.data] }, 1)
    })
  }

  const handleAttachCase = (caseId: number) => {
    updateTestCase.mutate(
      { id: caseId, data: { test_plan_id: planId } },
      { onSuccess: (updatedCase) => {
        syncCaseAssociationCache(updatedCase, true)
        setSelectedCaseIds((prev) => prev.filter((id) => id !== caseId))
      } },
    )
  }

  const handleAttachSelected = () => {
    if (!selectedCandidateIds.length) return
    batchUpdateTestCases.mutate(
      { ids: selectedCandidateIds, data: { test_plan_id: planId } },
      { onSuccess: () => setSelectedCaseIds([]) },
    )
  }

  const handleDetachCase = (caseId: number) => {
    if (!window.confirm('确定要将该测试用例从当前测试计划中移除吗？')) return
    updateTestCase.mutate(
      { id: caseId, data: { test_plan_id: null } },
      { onSuccess: (updatedCase) => syncCaseAssociationCache(updatedCase, false) },
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/test-plans">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{testPlan.plan_name}</h1>
            <p className="text-gray-600">{testPlan.plan_code}</p>
          </div>
          {getStatusBadge(testPlan.status)}
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {testPlan.status === TestPlanStatus.DRAFT && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.APPROVED)}>
              <CheckCircle className="w-4 h-4 mr-2" />
              批准
            </Button>
          )}
          {testPlan.status === TestPlanStatus.APPROVED && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.IN_PROGRESS)}>
              <Play className="w-4 h-4 mr-2" />
              开始执行
            </Button>
          )}
          {testPlan.status === TestPlanStatus.IN_PROGRESS && (
            <>
              <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.PAUSED)}>
                <Pause className="w-4 h-4 mr-2" />
                暂停
              </Button>
              <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.COMPLETED)}>
                <CheckCircle className="w-4 h-4 mr-2" />
                完成
              </Button>
            </>
          )}
          {testPlan.status === TestPlanStatus.PAUSED && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.IN_PROGRESS)}>
              <Play className="w-4 h-4 mr-2" />
              继续执行
            </Button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" disabled={exportTestPlan.isPending}>
                <Download className="w-4 h-4 mr-2" />
                {exportTestPlan.isPending ? '导出中...' : '导出'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleExport('csv')}>导出 CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('txt')}>导出 TXT</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Link to={`/test-manager/test-plans/${planId}/edit`}>
            <Button>
              <Edit className="w-4 h-4 mr-2" />
              编辑
            </Button>
          </Link>
        </div>
      </div>     
 {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Target className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">总用例数</p>
                <p className="text-2xl font-bold">{stats.total_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">已执行</p>
                <p className="text-2xl font-bold">{stats.executed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-green-500 rounded-full" />
              <div>
                <p className="text-sm font-medium text-gray-600">通过</p>
                <p className="text-2xl font-bold text-green-600">{stats.passed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-red-500 rounded-full" />
              <div>
                <p className="text-sm font-medium text-gray-600">失败</p>
                <p className="text-2xl font-bold text-red-600">{stats.failed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Section */}
      <Card>
        <CardHeader>
          <CardTitle>执行进度</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>执行进度</span>
                <span>{executionRate.toFixed(1)}%</span>
              </div>
              <Progress value={executionRate} className="h-3" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>通过率</span>
                <span>{passRate.toFixed(1)}%</span>
              </div>
              <Progress value={passRate} className="h-3" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Information */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="test-cases">测试用例</TabsTrigger>
          <TabsTrigger value="execution">执行记录</TabsTrigger>
          <TabsTrigger value="defects">缺陷</TabsTrigger>
          <TabsTrigger value="reports">报告</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-600">测试类型</label>
                  <p>{getTypeLabel(testPlan.test_type)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">描述</label>
                  <p>{testPlan.description || '暂无描述'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">测试范围</label>
                  <p>{testPlan.test_scope || '暂无定义'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">测试策略</label>
                  <p>{testPlan.test_strategy || '暂无定义'}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>时间安排</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">计划开始时间</label>
                    <p>{testPlan.planned_start_date ? formatDate(testPlan.planned_start_date) : '未设置'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">计划结束时间</label>
                    <p>{testPlan.planned_end_date ? formatDate(testPlan.planned_end_date) : '未设置'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">实际开始时间</label>
                    <p>{testPlan.actual_start_date ? formatDate(testPlan.actual_start_date) : '未开始'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">实际结束时间</label>
                    <p>{testPlan.actual_end_date ? formatDate(testPlan.actual_end_date) : '未完成'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="test-cases">
          <Card>
            <CardHeader>
              <CardTitle>已关联测试用例 ({linkedCases.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {linkedCasesLoading ? (
                <div className="py-8 text-center text-gray-500">正在加载已关联测试用例...</div>
              ) : linkedCases.length === 0 ? (
                <div className="py-8 text-center text-gray-500">当前测试计划还没有关联测试用例</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>用例标题</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>模块</TableHead>
                      <TableHead>最近执行</TableHead>
                      <TableHead>缺陷</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {linkedCases.map((testCase: any) => {
                      const latestExecution = latestExecutionByCaseId.get(Number(testCase.id))
                      const defectCount = defectCountByCaseId[Number(testCase.id)] || 0
                      return (
                        <TableRow key={testCase.id}>
                          <TableCell>
                            <Link to={`/test-manager/test-cases/${testCase.id}`} className="font-medium text-blue-600 hover:text-blue-800">
                              {testCase.case_title}
                            </Link>
                            <div className="text-xs text-gray-500">{testCase.case_code}</div>
                          </TableCell>
                          <TableCell>{getPriorityBadge(testCase.priority)}</TableCell>
                          <TableCell>{getCaseStatusBadge(testCase.status)}</TableCell>
                          <TableCell>{testCase.module || '-'}</TableCell>
                          <TableCell>
                            {latestExecution ? (
                              <Link to={`/test-manager/executions/${latestExecution.id}`}>
                                {getExecutionStatusBadge(latestExecution.execution_status)}
                              </Link>
                            ) : (
                              <Badge variant="secondary">未执行</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Link to={`/test-manager/defects?test_plan_id=${planId}&test_case_id=${testCase.id}`} className="text-blue-600 hover:text-blue-800">
                              {defectCount}
                            </Link>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button asChild size="sm">
                                <Link to={`/test-manager/executions/manual/${testCase.id}`}>
                                  <Play className="w-4 h-4 mr-2" />
                                  执行
                                </Link>
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={linking}
                                onClick={() => handleDetachCase(Number(testCase.id))}
                              >
                                <Unlink className="w-4 h-4 mr-2" />
                                移除
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <CardTitle>关联已有测试用例</CardTitle>
                <Button size="sm" disabled={!selectedCandidateIds.length || linking} onClick={handleAttachSelected}>
                  <Link2 className="w-4 h-4 mr-2" />
                  关联选中 ({selectedCandidateIds.length})
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  value={caseSearch}
                  onChange={(event) => setCaseSearch(event.target.value)}
                  placeholder="搜索用例标题或编号"
                  className="pl-10"
                />
              </div>

              {candidateCasesLoading ? (
                <div className="py-8 text-center text-gray-500">正在加载可关联测试用例...</div>
              ) : candidateCases.length === 0 ? (
                <div className="py-8 text-center text-gray-500">没有可关联的测试用例</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <Checkbox
                          checked={selectableCandidateIds.length > 0 && selectableCandidateIds.every((caseId) => selectedCaseIds.includes(caseId))}
                          onCheckedChange={handleToggleAllCandidates}
                        />
                      </TableHead>
                      <TableHead>用例标题</TableHead>
                      <TableHead>当前计划</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {candidateCases.map((testCase: any) => (
                      <TableRow key={testCase.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedCaseIds.includes(Number(testCase.id))}
                            onCheckedChange={() => handleToggleCandidate(Number(testCase.id))}
                          />
                        </TableCell>
                        <TableCell>
                          <Link to={`/test-manager/test-cases/${testCase.id}`} className="font-medium text-blue-600 hover:text-blue-800">
                            {testCase.case_title}
                          </Link>
                          <div className="text-xs text-gray-500">{testCase.case_code}</div>
                        </TableCell>
                        <TableCell>{testCase.test_plan_id ? `测试计划 #${testCase.test_plan_id}` : '未关联'}</TableCell>
                        <TableCell>{getPriorityBadge(testCase.priority)}</TableCell>
                        <TableCell>{getCaseStatusBadge(testCase.status)}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={linking || linkedCaseIdSet.has(Number(testCase.id))}
                            onClick={() => handleAttachCase(Number(testCase.id))}
                          >
                            <Link2 className="w-4 h-4 mr-2" />
                            关联
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="execution">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  执行记录 ({executionsData?.total ?? executions.length})
                </CardTitle>
                <Link to={`/test-manager/executions?test_plan_id=${planId}`}>
                  <Button variant="outline" size="sm">查看全部</Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {executionsLoading ? (
                <div className="text-center py-8 text-gray-500">正在加载执行记录...</div>
              ) : executions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">当前测试计划暂无执行记录</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>执行编号</TableHead>
                      <TableHead>用例ID</TableHead>
                      <TableHead>执行方式</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>环境</TableHead>
                      <TableHead>开始时间</TableHead>
                      <TableHead>耗时</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {executions.map((execution: any) => (
                      <TableRow key={execution.id}>
                        <TableCell className="font-medium">{execution.execution_code || `#${execution.id}`}</TableCell>
                        <TableCell>
                          {execution.test_case_id ? (
                            <Link to={`/test-manager/test-cases/${execution.test_case_id}`} className="text-blue-600 hover:text-blue-800">
                              #{execution.test_case_id}
                            </Link>
                          ) : '-'}
                        </TableCell>
                        <TableCell>{executionTypeLabel(execution.execution_type)}</TableCell>
                        <TableCell>{getExecutionStatusBadge(execution.execution_status)}</TableCell>
                        <TableCell>{execution.test_environment || '-'}</TableCell>
                        <TableCell>{execution.started_at ? formatDate(execution.started_at) : '-'}</TableCell>
                        <TableCell>{formatDuration(execution.duration)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="defects">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Bug className="w-5 h-5" />
                  相关缺陷 ({defectsData?.total ?? defects.length})
                </CardTitle>
                <Link to={`/test-manager/defects?test_plan_id=${planId}`}>
                  <Button variant="outline" size="sm">查看全部</Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {defectsLoading ? (
                <div className="text-center py-8 text-gray-500">正在加载缺陷...</div>
              ) : defects.length === 0 ? (
                <div className="text-center py-8 text-gray-500">当前测试计划暂无关联缺陷</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>缺陷</TableHead>
                      <TableHead>用例ID</TableHead>
                      <TableHead>严重程度</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>负责人</TableHead>
                      <TableHead>报告时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {defects.map((defect: any) => (
                      <TableRow key={defect.id}>
                        <TableCell>
                          <div className="font-medium">{defect.title}</div>
                          <div className="text-xs text-gray-500">{defect.defect_code}</div>
                        </TableCell>
                        <TableCell>
                          {defect.test_case_id ? (
                            <Link to={`/test-manager/test-cases/${defect.test_case_id}`} className="text-blue-600 hover:text-blue-800">
                              #{defect.test_case_id}
                            </Link>
                          ) : '-'}
                        </TableCell>
                        <TableCell>{getPriorityBadge(defect.severity)}</TableCell>
                        <TableCell>{getPriorityBadge(defect.priority)}</TableCell>
                        <TableCell>{getDefectStatusBadge(defect.status)}</TableCell>
                        <TableCell>{defect.assignee_id ? `用户 #${defect.assignee_id}` : '未分配'}</TableCell>
                        <TableCell>{defect.reported_at ? formatDate(defect.reported_at) : '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  测试报告 ({reportsData?.total ?? reports.length})
                </CardTitle>
                <div className="flex gap-2">
                  <Link to={`/test-manager/reports/generate?type=execution&test_plan_id=${planId}`}>
                    <Button variant="outline" size="sm">执行报告</Button>
                  </Link>
                  <Link to={`/test-manager/reports/generate?type=defect&test_plan_id=${planId}`}>
                    <Button variant="outline" size="sm">缺陷报告</Button>
                  </Link>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {reportsLoading ? (
                <div className="text-center py-8 text-gray-500">正在加载测试报告...</div>
              ) : reports.length === 0 ? (
                <div className="text-center py-8 text-gray-500">当前测试计划暂无测试报告</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>报告名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>格式</TableHead>
                      <TableHead>创建人</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>下载次数</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reports.map((report: any) => (
                      <TableRow key={report.id}>
                        <TableCell className="font-medium">{report.name || report.report_name || `报告 #${report.id}`}</TableCell>
                        <TableCell>{reportTypeLabel(report.report_type)}</TableCell>
                        <TableCell>{getReportStatusBadge(report.status)}</TableCell>
                        <TableCell>{(report.export_formats || [report.report_format]).filter(Boolean).join(', ') || '-'}</TableCell>
                        <TableCell>{report.created_by || report.generated_by ? `用户 #${report.created_by || report.generated_by}` : '-'}</TableCell>
                        <TableCell>{report.created_at ? formatDate(report.created_at) : '-'}</TableCell>
                        <TableCell>{report.download_count ?? 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TestPlanDetail
