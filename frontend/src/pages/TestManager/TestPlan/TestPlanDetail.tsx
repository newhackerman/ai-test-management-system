import React, { useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Edit, Play, Pause, CheckCircle, Download, Users, Calendar, Target, Link2, Unlink, Search } from 'lucide-react'
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
import { useExportTestPlan, useTestPlan, useTestPlanProgress, useUpdateTestPlanStatus } from '../../../hooks/testmanager/useTestPlan'
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

  const { data: testPlan, isLoading, error } = useTestPlan(planId)
  const { data: progress } = useTestPlanProgress(planId)
  const { data: linkedCasesData, isLoading: linkedCasesLoading } = useTestCases(linkedCasesFilters)
  const { data: candidateCasesData, isLoading: candidateCasesLoading } = useTestCases(candidateCasesFilters)
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

  const stats = progress || testPlan
  const executionRate = stats.total_cases > 0 ? (stats.executed_cases / stats.total_cases) * 100 : 0
  const passRate = stats.executed_cases > 0 ? (stats.passed_cases / stats.executed_cases) * 100 : 0
  const updatingStatus = updateTestPlanStatus.isPending
  const linkedCases = linkedCasesData?.data || []
  const linkedCaseIdSet = new Set(linkedCases.map((testCase: any) => Number(testCase.id)))
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
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {linkedCases.map((testCase: any) => (
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
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={linking}
                            onClick={() => handleDetachCase(Number(testCase.id))}
                          >
                            <Unlink className="w-4 h-4 mr-2" />
                            移除关联
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
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
              <CardTitle>执行记录</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                执行记录将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="defects">
          <Card>
            <CardHeader>
              <CardTitle>相关缺陷</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                缺陷列表将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports">
          <Card>
            <CardHeader>
              <CardTitle>测试报告</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                测试报告将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TestPlanDetail
