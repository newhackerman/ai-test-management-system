// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, Copy, Download, Play, Plus, Search, Trash2, Upload, Wand2 } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Checkbox } from '../../../components/ui/Checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/Dialog'
import {
  useBatchDeleteTestCases,
  useBatchUpdateTestCases,
  useDeleteTestCase,
  useDuplicateTestCase,
  useExportTestCases,
  useGenerateAutomationScript,
  useGenerateTestCases,
  useImportTestCases,
  useTestCaseManagement,
  useTestCases,
} from '../../../hooks/testmanager/useTestCase'
import { AutomationLevel, Priority, TestCaseStatus, TestCaseType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'
import requirementService from '../../../services/requirementService'
import { testPlanService } from '../../../services/testmanager/testPlanService'
import userService from '../../../services/user-service'
import type { Requirement } from '../../../types/requirement'
import type { TestPlan } from '../../../types/testmanager'
import type { User } from '../../../types'
import {
  AUTOMATION_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  TEST_CASE_TYPE_LABELS,
} from './testCaseLabels'

const statusVariant = {
  [TestCaseStatus.DRAFT]: 'secondary',
  [TestCaseStatus.APPROVED]: 'default',
  [TestCaseStatus.ACTIVE]: 'default',
  [TestCaseStatus.DEPRECATED]: 'secondary',
  [TestCaseStatus.ARCHIVED]: 'outline',
} as const

const priorityVariant = {
  [Priority.CRITICAL]: 'destructive',
  [Priority.HIGH]: 'destructive',
  [Priority.MEDIUM]: 'default',
  [Priority.LOW]: 'secondary',
} as const

const TestCaseList: React.FC = () => {
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPlanId, setImportPlanId] = useState('')
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [testPlans, setTestPlans] = useState<TestPlan[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [generateForm, setGenerateForm] = useState({
    requirement_id: '',
    test_plan_id: '',
  })

  const {
    selectedCases,
    filters,
    searchTerm,
    handleSelectCase,
    handleSelectAllCases,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
    handleChangePage,
    handleChangePageSize,
  } = useTestCaseManagement()

  const { data: testCasesData, isLoading, error } = useTestCases(filters)
  const deleteTestCase = useDeleteTestCase()
  const duplicateTestCase = useDuplicateTestCase()
  const batchDeleteTestCases = useBatchDeleteTestCases()
  const batchUpdateTestCases = useBatchUpdateTestCases()
  const exportTestCases = useExportTestCases()
  const importTestCases = useImportTestCases()
  const generateTestCases = useGenerateTestCases()
  const generateAutomationScript = useGenerateAutomationScript()

  const testCases = testCasesData?.data || []
  const totalCount = Number(testCasesData?.total || 0)
  const currentPage = Number(testCasesData?.page || filters.page || 1)
  const pageSize = Number(testCasesData?.size || filters.size || 20)
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))

  const requirementMap = useMemo(() => new Map(requirements.map((item) => [Number(item.id), item])), [requirements])
  const planMap = useMemo(() => new Map(testPlans.map((item) => [Number(item.id), item])), [testPlans])
  const userMap = useMemo(() => new Map(users.map((item) => [Number(item.id), item])), [users])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      requirementService.getRequirements({ page: 1, size: 100, sort_by: 'updated_at', sort_order: 'desc' }),
      testPlanService.getTestPlans({ page: 1, size: 100 }),
      userService.getUsers({ page: 1, size: 100, status: 'active' }),
    ]).then(([requirementsResult, plansResult, usersResult]) => {
      if (cancelled) return
      if (requirementsResult.status === 'fulfilled') setRequirements(requirementsResult.value.data || [])
      if (plansResult.status === 'fulfilled') setTestPlans(plansResult.value.data || [])
      if (usersResult.status === 'fulfilled') setUsers(usersResult.value.users || [])
    })
    return () => {
      cancelled = true
    }
  }, [])

  const getRequirementLabel = (requirementId?: number) => {
    if (!requirementId) return '未关联'
    const requirement = requirementMap.get(Number(requirementId))
    if (!requirement) return `需求 #${requirementId}`
    return requirement.requirement_code ? `${requirement.requirement_code} - ${requirement.title}` : requirement.title
  }

  const getPlanLabel = (planId?: number) => {
    if (!planId) return '未关联'
    const plan = planMap.get(Number(planId))
    if (!plan) return `计划 #${planId}`
    return plan.plan_code ? `${plan.plan_code} - ${plan.plan_name}` : plan.plan_name
  }

  const getUserName = (userId?: number) => {
    if (!userId) return '未分配'
    const user = userMap.get(Number(userId))
    return user?.real_name || user?.nickname || user?.username || `用户 #${userId}`
  }

  const handleDelete = (id: number) => {
    if (window.confirm('确定要删除这个测试用例吗？')) {
      deleteTestCase.mutate(id)
    }
  }

  const handleBatchDelete = () => {
    if (selectedCases.length && window.confirm(`确定要删除选中的 ${selectedCases.length} 个测试用例吗？`)) {
      batchDeleteTestCases.mutate(selectedCases, { onSuccess: handleClearSelection })
    }
  }

  const handleBatchStatus = (status: TestCaseStatus) => {
    if (!selectedCases.length) return
    batchUpdateTestCases.mutate(
      { ids: selectedCases, data: { status } },
      { onSuccess: handleClearSelection },
    )
  }

  const handleExportSelected = () => {
    const selectedRows = testCases.filter((item) => selectedCases.includes(item.id))
    if (!selectedRows.length) return
    const header = ['用例编号', '标题', '类型', '优先级', '状态', '关联需求', '负责人', '更新时间']
    const rows = selectedRows.map((item) => [
      item.case_code,
      item.case_title,
      TEST_CASE_TYPE_LABELS[item.case_type] || item.case_type,
      PRIORITY_LABELS[item.priority] || item.priority,
      STATUS_LABELS[item.status] || item.status,
      getRequirementLabel(item.requirement_id),
      getUserName(item.assignee_id),
      formatDate(item.updated_at),
    ])
    const csv = [header, ...rows]
      .map((row) => row.map((cell) => `"${String(cell || '').replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'selected-test-cases.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  const handleDuplicate = (id: number, title: string) => {
    const newTitle = window.prompt('请输入复制后的测试用例标题', `${title} - 副本`)
    if (newTitle?.trim()) duplicateTestCase.mutate({ id, newTitle: newTitle.trim() })
  }

  const handleImport = () => {
    if (!importFile) return
    importTestCases.mutate(
      { file: importFile, testPlanId: Number(importPlanId || 0) || undefined },
      {
        onSuccess: () => {
          setImportFile(null)
          setImportPlanId('')
          setShowImportDialog(false)
        },
      },
    )
  }

  const handleGenerate = () => {
    const requirementId = Number(generateForm.requirement_id)
    if (!Number.isFinite(requirementId) || requirementId <= 0) {
      window.alert('请选择一个需求后再生成测试用例')
      return
    }
    generateTestCases.mutate(
      {
        requirement_id: requirementId,
        test_plan_id: Number(generateForm.test_plan_id || 0) || undefined,
        generation_config: {
          include_negative_cases: true,
          include_boundary_cases: true,
          include_edge_cases: true,
        },
      },
      {
        onSuccess: () => {
          setShowGenerateDialog(false)
          setGenerateForm((current) => ({ ...current, requirement_id: '', test_plan_id: '' }))
        },
      },
    )
  }

  const handleGenerateScript = (id: number) => {
    generateAutomationScript.mutate({
      testCaseId: id,
      config: { framework: 'PLAYWRIGHT', language: 'PYTHON', browser: 'CHROME' },
    })
  }

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center">加载中...</div>
  }

  if (error) {
    return <div className="text-center text-red-500">加载失败：{error.message}</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">测试用例管理</h1>
          <p className="text-gray-600">维护测试用例、需求关联、执行入口和批量状态。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="mr-2 h-4 w-4" />
                导入用例
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>导入测试用例</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Field label="关联测试计划">
                  <Select value={importPlanId || 'none'} onValueChange={(value) => setImportPlanId(value === 'none' ? '' : value)}>
                    <SelectTrigger><SelectValue placeholder="可选" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">暂不关联测试计划</SelectItem>
                      {testPlans.map((plan) => (
                        <SelectItem key={plan.id} value={String(plan.id)}>
                          {plan.plan_code || `TP-${plan.id}`} - {plan.plan_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="文件">
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
                  />
                </Field>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowImportDialog(false)}>取消</Button>
                  <Button onClick={handleImport} disabled={!importFile || importTestCases.isPending}>
                    {importTestCases.isPending ? '导入中...' : '导入'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Download className="mr-2 h-4 w-4" />
                导出当前筛选
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => exportTestCases.mutate({ filters, format: 'csv' })}>
                导出 CSV
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => exportTestCases.mutate({ filters, format: 'txt' })}>
                导出 TXT
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Bot className="mr-2 h-4 w-4" />
                AI 从需求生成用例
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>AI 从需求生成测试用例</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Field label="选择需求来源">
                  <Select
                    value={generateForm.requirement_id || 'none'}
                    onValueChange={(value) => setGenerateForm((current) => ({ ...current, requirement_id: value === 'none' ? '' : value }))}
                  >
                    <SelectTrigger><SelectValue placeholder="选择要生成用例的需求" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">请选择要分析的需求</SelectItem>
                      {requirements.map((requirement) => (
                        <SelectItem key={requirement.id} value={String(requirement.id)}>
                          {requirement.requirement_code || `REQ-${requirement.id}`} - {requirement.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="保存到测试计划">
                  <Select
                    value={generateForm.test_plan_id || 'none'}
                    onValueChange={(value) => setGenerateForm((current) => ({ ...current, test_plan_id: value === 'none' ? '' : value }))}
                  >
                    <SelectTrigger><SelectValue placeholder="可选" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">暂不关联测试计划</SelectItem>
                      {testPlans.map((plan) => (
                        <SelectItem key={plan.id} value={String(plan.id)}>
                          {plan.plan_code || `TP-${plan.id}`} - {plan.plan_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowGenerateDialog(false)}>取消</Button>
                  <Button onClick={handleGenerate} disabled={generateTestCases.isPending}>
                    {generateTestCases.isPending ? '正在生成...' : '生成测试用例并保存'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          <Link to="/test-manager/test-cases/create">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              创建用例
            </Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(220px,1fr)_repeat(5,160px)]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="搜索标题、编号或模块"
                value={searchTerm}
                onChange={(event) => handleSearch(event.target.value)}
                className="pl-10"
              />
            </div>
            <FilterSelect value={filters.status || 'all'} placeholder="状态" allLabel="全部状态" options={STATUS_LABELS} onChange={(value) => handleUpdateFilters({ status: value === 'all' ? undefined : value })} />
            <FilterSelect value={filters.case_type || 'all'} placeholder="类型" allLabel="全部类型" options={TEST_CASE_TYPE_LABELS} onChange={(value) => handleUpdateFilters({ case_type: value === 'all' ? undefined : value })} />
            <FilterSelect value={filters.priority || 'all'} placeholder="优先级" allLabel="全部优先级" options={PRIORITY_LABELS} onChange={(value) => handleUpdateFilters({ priority: value === 'all' ? undefined : value })} />
            <Select
              value={filters.requirement_id ? String(filters.requirement_id) : 'all'}
              onValueChange={(value) => handleUpdateFilters({ requirement_id: value === 'all' ? undefined : Number(value) })}
            >
              <SelectTrigger><SelectValue placeholder="需求" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部需求</SelectItem>
                {requirements.map((requirement) => (
                  <SelectItem key={requirement.id} value={String(requirement.id)}>
                    {requirement.requirement_code || `REQ-${requirement.id}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={filters.assignee_id ? String(filters.assignee_id) : 'all'}
              onValueChange={(value) => handleUpdateFilters({ assignee_id: value === 'all' || value === 'unassigned' ? undefined : Number(value) })}
            >
              <SelectTrigger><SelectValue placeholder="负责人" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部负责人</SelectItem>
                <SelectItem value="unassigned">未分配</SelectItem>
                {users.map((user) => (
                  <SelectItem key={user.id} value={String(user.id)}>
                    {user.real_name || user.nickname || user.username}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {selectedCases.length > 0 && (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-6 md:flex-row md:items-center md:justify-between">
            <span className="text-sm text-gray-600">已选择 {selectedCases.length} 个测试用例</span>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={handleClearSelection}>取消选择</Button>
              <Button variant="outline" size="sm" onClick={handleExportSelected}>
                <Download className="mr-2 h-4 w-4" />
                导出选中
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">批量改状态</Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <DropdownMenuItem key={value} onClick={() => handleBatchStatus(value as TestCaseStatus)}>
                      设为{label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="outline" size="sm" className="text-red-600" onClick={handleBatchDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                批量删除
              </Button>
            </div>
          </CardContent>
        </Card>
      )}


      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>测试用例列表</CardTitle>
          <div className="text-sm text-gray-600">共 {totalCount} 个测试用例</div>
        </CardHeader>
        <CardContent>
          <Table className="min-w-[1385px] table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-11 px-3">
                  <Checkbox
                    checked={testCases.length > 0 && testCases.every((item) => selectedCases.includes(item.id))}
                    onCheckedChange={() => handleSelectAllCases(testCases.map((item) => item.id))}
                  />
                </TableHead>
                <TableHead className="w-[300px] px-3">用例</TableHead>
                <TableHead className="w-[92px] px-3">类型</TableHead>
                <TableHead className="w-20 px-3">优先级</TableHead>
                <TableHead className="w-[88px] px-3">状态</TableHead>
                <TableHead className="w-[210px] px-3">测试计划</TableHead>
                <TableHead className="w-[230px] px-3">关联需求</TableHead>
                <TableHead className="w-[110px] px-3">负责人</TableHead>
                <TableHead className="w-[155px] px-3">更新时间</TableHead>
                <TableHead className="w-[76px] px-3 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {testCases.map((testCase) => (
                <TableRow key={testCase.id}>
                  <TableCell className="px-3">
                    <Checkbox
                      checked={selectedCases.includes(testCase.id)}
                      onCheckedChange={() => handleSelectCase(testCase.id)}
                    />
                  </TableCell>
                  <TableCell className="max-w-0 px-3">
                    <Link
                      to={`/test-manager/test-cases/${testCase.id}`}
                      className="block truncate font-medium text-blue-600 hover:text-blue-800"
                      title={testCase.case_title}
                    >
                      {testCase.case_title}
                    </Link>
                    <div className="truncate text-sm text-gray-500" title={testCase.case_code}>{testCase.case_code}</div>
                    {testCase.module && <div className="truncate text-xs text-gray-400" title={testCase.module}>{testCase.module}</div>}
                  </TableCell>
                  <TableCell className="px-3"><Badge variant="outline">{TEST_CASE_TYPE_LABELS[testCase.case_type] || testCase.case_type}</Badge></TableCell>
                  <TableCell className="px-3"><Badge variant={priorityVariant[testCase.priority] || 'secondary'}>{PRIORITY_LABELS[testCase.priority] || testCase.priority}</Badge></TableCell>
                  <TableCell className="px-3"><Badge variant={statusVariant[testCase.status] || 'secondary'}>{STATUS_LABELS[testCase.status] || testCase.status}</Badge></TableCell>
                  <TableCell className="max-w-0 px-3">
                    <div className="truncate text-sm" title={getPlanLabel(testCase.test_plan_id)}>
                      {getPlanLabel(testCase.test_plan_id)}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-0 px-3">
                    <div className="truncate text-sm" title={getRequirementLabel(testCase.requirement_id)}>
                      {getRequirementLabel(testCase.requirement_id)}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-0 px-3">
                    <div className="truncate" title={getUserName(testCase.assignee_id)}>{getUserName(testCase.assignee_id)}</div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap px-3">{formatDate(testCase.updated_at)}</TableCell>
                  <TableCell className="px-3 text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">操作</Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild><Link to={`/test-manager/test-cases/${testCase.id}`}>查看详情</Link></DropdownMenuItem>
                        <DropdownMenuItem asChild><Link to={`/test-manager/test-cases/${testCase.id}/edit`}>编辑</Link></DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link to={`/test-manager/executions/manual/${testCase.id}`}>
                            <Play className="mr-2 h-4 w-4" />
                            执行测试
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDuplicate(testCase.id, testCase.case_title)}>
                          <Copy className="mr-2 h-4 w-4" />
                          复制
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleGenerateScript(testCase.id)}>
                          <Wand2 className="mr-2 h-4 w-4" />
                          生成自动化脚本
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-red-600" onClick={() => handleDelete(testCase.id)}>
                          <Trash2 className="mr-2 h-4 w-4" />
                          删除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {testCases.length === 0 && (
            <div className="py-10 text-center text-gray-500">暂无测试用例数据</div>
          )}

          <div className="mt-4 flex flex-col gap-3 border-t pt-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>每页</span>
              <Select value={String(pageSize)} onValueChange={(value) => handleChangePageSize(Number(value))}>
                <SelectTrigger className="h-8 w-20"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[10, 20, 50, 100].map((size) => <SelectItem key={size} value={String(size)}>{size}</SelectItem>)}
                </SelectContent>
              </Select>
              <span>条，第 {currentPage} / {totalPages} 页</span>
            </div>
            <div className="flex items-center justify-end gap-2">
              <Button variant="outline" size="sm" disabled={currentPage <= 1} onClick={() => handleChangePage(currentPage - 1)}>上一页</Button>
              <Button variant="outline" size="sm" disabled={currentPage >= totalPages} onClick={() => handleChangePage(currentPage + 1)}>下一页</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-2 text-sm font-medium">
    <span>{label}</span>
    {children}
  </label>
)

const EnumSelect = ({ value, options, onChange }: { value: string; options: Record<string, string>; onChange: (value: string) => void }) => (
  <select
    value={value}
    onChange={(event) => onChange(event.target.value)}
    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
  >
    {Object.entries(options).map(([optionValue, label]) => (
      <option key={optionValue} value={optionValue}>{label}</option>
    ))}
  </select>
)

const FilterSelect = ({ value, placeholder, allLabel, options, onChange }: {
  value: string
  placeholder: string
  allLabel: string
  options: Record<string, string>
  onChange: (value: string) => void
}) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent>
      <SelectItem value="all">{allLabel}</SelectItem>
      {Object.entries(options).map(([optionValue, label]) => (
        <SelectItem key={optionValue} value={optionValue}>{label}</SelectItem>
      ))}
    </SelectContent>
  </Select>
)

export default TestCaseList
