// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Calendar, Download, Eye, MessageSquare, MoreHorizontal, Paperclip, Pencil, Plus, Search, Trash2, User, UserCheck } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Checkbox } from '../../../components/ui/Checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../../components/ui/Dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import ConfirmDialog from '../../../components/ui/ConfirmDialog'
import {
  useDefects,
  useDefectManagement,
  useCreateDefect,
  useUpdateDefect,
  useUpdateDefectStatus,
  useAssignDefect,
  useAddDefectComment,
  useDefectComments,
  useDeleteDefect,
  useExportDefects,
  useUploadAttachment,
} from '../../../hooks/testmanager/useDefect'
import userService from '../../../services/user-service'
import requirementService from '../../../services/requirementService'
import { testPlanService } from '../../../services/testmanager/testPlanService'
import { testCaseService } from '../../../services/testmanager/testCaseService'
import { executionService } from '../../../services/testmanager/executionService'
import { DefectResolution, DefectStatus, DefectSeverity, DefectType, Priority } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const defectTypeOptions = [
  { value: DefectType.FUNCTIONAL, label: '功能缺陷' },
  { value: DefectType.PERFORMANCE, label: '性能缺陷' },
  { value: DefectType.SECURITY, label: '安全缺陷' },
  { value: DefectType.USABILITY, label: '易用性缺陷' },
  { value: DefectType.COMPATIBILITY, label: '兼容性缺陷' },
  { value: DefectType.DATA, label: '数据缺陷' },
  { value: DefectType.INTERFACE, label: '接口缺陷' },
]

const severityOptions = [
  { value: DefectSeverity.CRITICAL, label: '严重' },
  { value: DefectSeverity.HIGH, label: '高' },
  { value: DefectSeverity.MEDIUM, label: '中' },
  { value: DefectSeverity.LOW, label: '低' },
]

const priorityOptions = [
  { value: Priority.CRITICAL, label: '紧急' },
  { value: Priority.HIGH, label: '高' },
  { value: Priority.MEDIUM, label: '中' },
  { value: Priority.LOW, label: '低' },
]

const statusOptions = [
  { value: DefectStatus.NEW, label: '新建' },
  { value: DefectStatus.ASSIGNED, label: '已分配' },
  { value: DefectStatus.IN_PROGRESS, label: '处理中' },
  { value: DefectStatus.RESOLVED, label: '已解决' },
  { value: DefectStatus.VERIFIED, label: '已验证' },
  { value: DefectStatus.CLOSED, label: '已关闭' },
  { value: DefectStatus.REOPENED, label: '重新打开' },
  { value: DefectStatus.REJECTED, label: '已拒绝' },
]

const resolutionOptions = [
  { value: DefectResolution.FIXED, label: '已修复' },
  { value: DefectResolution.DUPLICATE, label: '重复缺陷' },
  { value: DefectResolution.NOT_A_BUG, label: '非缺陷' },
  { value: DefectResolution.WONT_FIX, label: '不修复' },
  { value: DefectResolution.CANNOT_REPRODUCE, label: '无法复现' },
  { value: DefectResolution.DEFERRED, label: '延期处理' },
]

const statusTransitions = {
  [DefectStatus.NEW]: [DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS, DefectStatus.REJECTED],
  [DefectStatus.ASSIGNED]: [DefectStatus.IN_PROGRESS, DefectStatus.REJECTED],
  [DefectStatus.IN_PROGRESS]: [DefectStatus.RESOLVED, DefectStatus.REOPENED],
  [DefectStatus.RESOLVED]: [DefectStatus.VERIFIED, DefectStatus.REOPENED],
  [DefectStatus.VERIFIED]: [DefectStatus.CLOSED, DefectStatus.REOPENED],
  [DefectStatus.CLOSED]: [DefectStatus.REOPENED],
  [DefectStatus.REOPENED]: [DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS],
  [DefectStatus.REJECTED]: [DefectStatus.REOPENED],
}

const emptyForm = {
  title: '',
  description: '',
  steps_to_reproduce: '',
  defect_type: DefectType.FUNCTIONAL,
  severity: DefectSeverity.MEDIUM,
  priority: Priority.MEDIUM,
  found_in_version: '',
  test_environment: '',
  assignee_id: '',
  test_plan_id: '',
  test_case_id: '',
  test_execution_id: '',
  requirement_id: '',
}

const labelOf = (options, value) => options.find((item) => item.value === value)?.label || value || '-'
const userName = (user) => user?.real_name || user?.nickname || user?.username || `用户 #${user?.id}`

const DefectList: React.FC = () => {
  const [searchParams] = useSearchParams()
  const {
    selectedDefects,
    filters,
    searchTerm,
    handleSelectDefect,
    handleSelectAllDefects,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  } = useDefectManagement()

  const { data: defectsData, isLoading, error } = useDefects(filters)
  const createDefect = useCreateDefect()
  const updateDefect = useUpdateDefect()
  const updateDefectStatus = useUpdateDefectStatus()
  const assignDefect = useAssignDefect()
  const deleteDefect = useDeleteDefect()
  const exportDefects = useExportDefects()
  const addDefectComment = useAddDefectComment()
  const uploadAttachment = useUploadAttachment()

  const [users, setUsers] = useState([])
  const [testPlans, setTestPlans] = useState([])
  const [testCases, setTestCases] = useState([])
  const [executions, setExecutions] = useState([])
  const [requirements, setRequirements] = useState([])
  const [referenceError, setReferenceError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editingDefect, setEditingDefect] = useState(null)
  const [detailDefect, setDetailDefect] = useState(null)
  const [assignDefectRow, setAssignDefectRow] = useState(null)
  const [deleteDefectRow, setDeleteDefectRow] = useState(null)
  const [assignUserId, setAssignUserId] = useState('')
  const [statusDialog, setStatusDialog] = useState(null)
  const [statusNotes, setStatusNotes] = useState('')
  const [statusResolution, setStatusResolution] = useState(DefectResolution.FIXED)
  const [statusFixedVersion, setStatusFixedVersion] = useState('')
  const [statusError, setStatusError] = useState('')
  const [commentText, setCommentText] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const detailComments = useDefectComments(detailDefect?.id)

  useEffect(() => {
    const initialSearch = searchParams.get('search')?.trim()
    if (initialSearch) handleSearch(initialSearch)
    const testPlanId = Number(searchParams.get('test_plan_id') || searchParams.get('plan_id') || 0)
    const testCaseId = Number(searchParams.get('test_case_id') || 0)
    const testExecutionId = Number(searchParams.get('test_execution_id') || 0)
    const status = searchParams.get('status') as DefectStatus | null
    const severity = searchParams.get('severity') as DefectSeverity | null
    const defectType = searchParams.get('defect_type') as DefectType | null
    const nextFilters: any = {}
    if (testPlanId > 0) nextFilters.test_plan_id = testPlanId
    if (testCaseId > 0) nextFilters.test_case_id = testCaseId
    if (testExecutionId > 0) nextFilters.test_execution_id = testExecutionId
    if (status && Object.values(DefectStatus).includes(status)) nextFilters.status = status
    if (severity && Object.values(DefectSeverity).includes(severity)) nextFilters.severity = severity
    if (defectType && Object.values(DefectType).includes(defectType)) nextFilters.defect_type = defectType
    if (Object.keys(nextFilters).length) handleUpdateFilters(nextFilters)
  }, [handleSearch, handleUpdateFilters, searchParams])

  const defects = defectsData?.data || []
  const totalCount = defectsData?.total || 0
  const summary = useMemo(() => {
    const openStatuses = [DefectStatus.NEW, DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS, DefectStatus.REOPENED]
    return {
      open: defects.filter((defect) => openStatuses.includes(defect.status)).length,
      highRisk: defects.filter((defect) => [DefectSeverity.CRITICAL, DefectSeverity.HIGH].includes(defect.severity)).length,
      unassigned: defects.filter((defect) => !defect.assignee_id).length,
    }
  }, [defects])

  const userNameById = useMemo(() => {
    return users.reduce((result, user) => {
      result[Number(user.id)] = userName(user)
      return result
    }, {})
  }, [users])
  const planMap = useMemo(() => new Map(testPlans.map((item) => [Number(item.id), item])), [testPlans])
  const caseMap = useMemo(() => new Map(testCases.map((item) => [Number(item.id), item])), [testCases])
  const executionMap = useMemo(() => new Map(executions.map((item) => [Number(item.id), item])), [executions])
  const requirementMap = useMemo(() => new Map(requirements.map((item) => [Number(item.id), item])), [requirements])
  const filteredCases = useMemo(() => {
    const planId = Number(form.test_plan_id || 0)
    if (!planId) return testCases
    return testCases.filter((item) => Number(item.test_plan_id) === planId)
  }, [form.test_plan_id, testCases])
  const filteredExecutions = useMemo(() => {
    const planId = Number(form.test_plan_id || 0)
    const caseId = Number(form.test_case_id || 0)
    return executions.filter((item) => {
      if (planId && Number(item.test_plan_id) !== planId) return false
      if (caseId && Number(item.test_case_id) !== caseId) return false
      return true
    })
  }, [executions, form.test_case_id, form.test_plan_id])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      userService.getUsers({ page: 1, size: 100, status: 'active', sort_by: 'username', sort_order: 'asc' }),
      testPlanService.getTestPlans({ page: 1, size: 100 }),
      testCaseService.getTestCases({ page: 1, size: 100 }),
      executionService.getExecutions({ page: 1, size: 100 }),
      requirementService.getRequirements({ page: 1, size: 100 }),
    ]).then((results) => {
      if (cancelled) return
      const [usersResult, plansResult, casesResult, executionsResult, requirementsResult] = results
      if (usersResult.status === 'fulfilled') setUsers(usersResult.value.users || [])
      if (plansResult.status === 'fulfilled') setTestPlans(plansResult.value.data || [])
      if (casesResult.status === 'fulfilled') setTestCases(casesResult.value.data || [])
      if (executionsResult.status === 'fulfilled') setExecutions(executionsResult.value.data || [])
      if (requirementsResult.status === 'fulfilled') setRequirements(requirementsResult.value.data || [])
      const failed = results.find((result) => result.status === 'rejected')
      if (failed) setReferenceError(failed.reason?.message || '部分关联数据加载失败')
    })
    return () => {
      cancelled = true
    }
  }, [])

  const openCreateForm = () => {
    setEditingDefect(null)
    setForm({
      ...emptyForm,
      test_plan_id: searchParams.get('test_plan_id') || searchParams.get('plan_id') || '',
      test_case_id: searchParams.get('test_case_id') || '',
      test_execution_id: searchParams.get('test_execution_id') || '',
      requirement_id: searchParams.get('requirement_id') || '',
    })
    setFormError('')
    setFormOpen(true)
  }

  const openEditForm = (defect) => {
    setEditingDefect(defect)
    setForm({
      title: defect.title || '',
      description: defect.description || '',
      steps_to_reproduce: defect.steps_to_reproduce || '',
      defect_type: defect.defect_type || DefectType.FUNCTIONAL,
      severity: defect.severity || DefectSeverity.MEDIUM,
      priority: defect.priority || Priority.MEDIUM,
      found_in_version: defect.found_in_version || '',
      test_environment: defect.test_environment || '',
      assignee_id: defect.assignee_id ? String(defect.assignee_id) : '',
      test_plan_id: String(defect.test_plan_id || caseMap.get(Number(defect.test_case_id))?.test_plan_id || executionMap.get(Number(defect.test_execution_id))?.test_plan_id || ''),
      test_case_id: defect.test_case_id ? String(defect.test_case_id) : '',
      test_execution_id: defect.test_execution_id ? String(defect.test_execution_id) : '',
      requirement_id: defect.requirement_id ? String(defect.requirement_id) : '',
    })
    setFormError('')
    setFormOpen(true)
  }

  const updateForm = (patch) => setForm((current) => ({ ...current, ...patch }))

  const handlePlanChange = (value) => {
    const planId = Number(value || 0)
    updateForm({
      test_plan_id: value,
      test_case_id: form.test_case_id && Number(caseMap.get(Number(form.test_case_id))?.test_plan_id) === planId ? form.test_case_id : '',
      test_execution_id: '',
    })
  }

  const handleCaseChange = (value) => {
    const testCase = caseMap.get(Number(value))
    updateForm({
      test_case_id: value,
      test_plan_id: testCase?.test_plan_id ? String(testCase.test_plan_id) : form.test_plan_id,
      requirement_id: testCase?.requirement_id ? String(testCase.requirement_id) : form.requirement_id,
      test_execution_id: '',
    })
  }

  const handleExecutionChange = (value) => {
    const execution = executionMap.get(Number(value))
    const testCase = caseMap.get(Number(execution?.test_case_id))
    updateForm({
      test_execution_id: value,
      test_case_id: execution?.test_case_id ? String(execution.test_case_id) : form.test_case_id,
      test_plan_id: execution?.test_plan_id ? String(execution.test_plan_id) : (testCase?.test_plan_id ? String(testCase.test_plan_id) : form.test_plan_id),
      requirement_id: testCase?.requirement_id ? String(testCase.requirement_id) : form.requirement_id,
    })
  }

  const submitForm = async (event) => {
    event.preventDefault()
    const title = form.title.trim()
    const description = form.description.trim()
    if (!title) {
      setFormError('请输入缺陷标题')
      return
    }
    if (!description) {
      setFormError('请输入缺陷描述')
      return
    }
    if (form.test_plan_id && !form.test_case_id && !form.test_execution_id) {
      setFormError('已选择测试计划，请继续选择该计划下的测试用例或执行记录，缺陷才能归集到计划。')
      return
    }

    const payload = {
      title,
      description,
      steps_to_reproduce: form.steps_to_reproduce.trim() || undefined,
      defect_type: form.defect_type,
      severity: form.severity,
      priority: form.priority,
      found_in_version: form.found_in_version.trim() || undefined,
      test_environment: form.test_environment.trim() || undefined,
      assignee_id: form.assignee_id ? Number(form.assignee_id) : undefined,
      test_case_id: form.test_case_id ? Number(form.test_case_id) : null,
      test_execution_id: form.test_execution_id ? Number(form.test_execution_id) : null,
      requirement_id: form.requirement_id ? Number(form.requirement_id) : null,
    }

    try {
      if (editingDefect) {
        await updateDefect.mutateAsync({ id: editingDefect.id, data: payload })
      } else {
        await createDefect.mutateAsync(payload)
      }
      setFormOpen(false)
      setEditingDefect(null)
      setForm(emptyForm)
    } catch (err) {
      setFormError(err?.message || '保存缺陷失败')
    }
  }

  const openAssignDialog = (defect) => {
    setAssignDefectRow(defect)
    setAssignUserId(defect.assignee_id ? String(defect.assignee_id) : '')
  }

  const submitAssign = async () => {
    if (!assignDefectRow || !assignUserId) return
    await assignDefect.mutateAsync({ id: assignDefectRow.id, assigneeId: Number(assignUserId) })
    setAssignDefectRow(null)
    setAssignUserId('')
  }

  const batchAssign = async () => {
    if (!assignUserId || selectedDefects.length === 0) return
    await Promise.all(selectedDefects.map((id) => assignDefect.mutateAsync({ id, assigneeId: Number(assignUserId) })))
    handleClearSelection()
    setAssignDefectRow(null)
    setAssignUserId('')
  }

  const handleStatusChange = (defect, status: DefectStatus) => {
    setStatusDialog({ defect, status })
    setStatusNotes('')
    setStatusResolution(DefectResolution.FIXED)
    setStatusFixedVersion(defect.fixed_in_version || '')
    setStatusError('')
  }

  const submitStatusChange = async () => {
    if (!statusDialog) return
    const notes = statusNotes.trim()
    if ([DefectStatus.RESOLVED, DefectStatus.REOPENED, DefectStatus.REJECTED].includes(statusDialog.status) && !notes) {
      setStatusError('请填写处理说明，便于后续追踪原因和验证依据。')
      return
    }

    try {
      const updated = await updateDefectStatus.mutateAsync({
        id: statusDialog.defect.id,
        status: statusDialog.status,
        resolution: statusDialog.status === DefectStatus.RESOLVED ? statusResolution : undefined,
        notes: notes || undefined,
        fixed_in_version: statusDialog.status === DefectStatus.RESOLVED ? statusFixedVersion.trim() || undefined : undefined,
      })
      if (detailDefect?.id === updated.id) setDetailDefect(updated)
      setStatusDialog(null)
      setStatusNotes('')
      setStatusError('')
    } catch (err) {
      setStatusError(err?.response?.data?.detail || err?.message || '状态更新失败')
    }
  }

  const submitComment = async () => {
    if (!detailDefect || !commentText.trim()) return
    await addDefectComment.mutateAsync({ id: detailDefect.id, content: commentText.trim() })
    setCommentText('')
  }

  const handleAttachmentChange = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!detailDefect || !file) return
    const metadata = await uploadAttachment.mutateAsync({ id: detailDefect.id, file })
    setDetailDefect({
      ...detailDefect,
      attachments: [...(detailDefect.attachments || []), metadata],
    })
  }

  const confirmDelete = async () => {
    if (!deleteDefectRow) return
    await deleteDefect.mutateAsync(deleteDefectRow.id)
    setDeleteDefectRow(null)
  }

  const handleExport = (format: string) => {
    exportDefects.mutate({ filters, format })
  }

  const reportQuery = useMemo(() => {
    const params = new URLSearchParams({ type: 'defect' })
    if (filters.test_plan_id) params.set('test_plan_id', String(filters.test_plan_id))
    if (filters.status) params.set('status', String(filters.status))
    if (filters.severity) params.set('severity', String(filters.severity))
    if (filters.defect_type) params.set('defect_type', String(filters.defect_type))
    if (filters.search) params.set('search', String(filters.search))
    return params.toString()
  }, [filters])

  const formatFileSize = (size?: number) => {
    const value = Number(size || 0)
    if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)}MB`
    if (value >= 1024) return `${(value / 1024).toFixed(1)}KB`
    return `${value}B`
  }

  const getPlanLabel = (planId?: number) => {
    if (!planId) return ''
    const plan = planMap.get(Number(planId))
    return plan ? `${plan.plan_name} (${plan.plan_code || plan.id})` : `测试计划 #${planId}`
  }

  const getCaseLabel = (caseId?: number) => {
    if (!caseId) return ''
    const testCase = caseMap.get(Number(caseId))
    return testCase ? `${testCase.case_title} (${testCase.case_code || testCase.id})` : `测试用例 #${caseId}`
  }

  const getExecutionLabel = (executionId?: number) => {
    if (!executionId) return ''
    const execution = executionMap.get(Number(executionId))
    return execution ? `${execution.execution_code || `执行 #${execution.id}`} - ${execution.execution_status}` : `执行记录 #${executionId}`
  }

  const getRequirementLabel = (requirementId?: number) => {
    if (!requirementId) return ''
    const requirement = requirementMap.get(Number(requirementId))
    return requirement ? `${requirement.title} (${requirement.requirement_code || requirement.id})` : `需求 #${requirementId}`
  }

  const getRelatedPlanId = (defect) => (
    Number(defect.test_plan_id || 0) ||
    Number(caseMap.get(Number(defect.test_case_id))?.test_plan_id || 0) ||
    Number(executionMap.get(Number(defect.test_execution_id))?.test_plan_id || 0)
  )

  const getStatusBadge = (status: DefectStatus) => {
    const variants = {
      [DefectStatus.NEW]: 'secondary',
      [DefectStatus.ASSIGNED]: 'default',
      [DefectStatus.IN_PROGRESS]: 'default',
      [DefectStatus.RESOLVED]: 'default',
      [DefectStatus.VERIFIED]: 'default',
      [DefectStatus.CLOSED]: 'outline',
      [DefectStatus.REOPENED]: 'destructive',
      [DefectStatus.REJECTED]: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{labelOf(statusOptions, status)}</Badge>
  }

  const getSeverityBadge = (severity: DefectSeverity) => {
    const variants = {
      [DefectSeverity.CRITICAL]: 'destructive',
      [DefectSeverity.HIGH]: 'destructive',
      [DefectSeverity.MEDIUM]: 'default',
      [DefectSeverity.LOW]: 'secondary',
    }
    return <Badge variant={variants[severity] || 'secondary'}>{labelOf(severityOptions, severity)}</Badge>
  }

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (error) {
    return <div className="text-red-500 text-center dark:text-red-400">加载失败: {error.message}</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <div className="flex flex-wrap gap-2">
          <Button onClick={openCreateForm}>
            <Plus className="w-4 h-4 mr-2" />
            创建缺陷
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                导出
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => handleExport('csv')}>导出为 CSV</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Link to={`/test-manager/reports/generate?${reportQuery}`}>
            <Button variant="outline">生成缺陷报告</Button>
          </Link>
        </div>
      </div>

      {referenceError && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:text-amber-300 dark:bg-amber-900/20 dark:border-amber-800">
          {referenceError}
        </div>
      )}

      <Card>
        <CardHeader className="space-y-3 p-4 pb-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="mr-2 text-lg">缺陷列表</CardTitle>
              <Badge variant="outline">共 {totalCount} 个</Badge>
              <Badge variant={summary.open ? 'secondary' : 'outline'}>未关闭 {summary.open}</Badge>
              <Badge variant={summary.highRisk ? 'destructive' : 'outline'}>高风险 {summary.highRisk}</Badge>
              <Badge variant={summary.unassigned ? 'secondary' : 'outline'}>未分配 {summary.unassigned}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(220px,1fr)_160px_140px_140px_150px] xl:w-[860px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                <Input
                  placeholder="搜索缺陷标题、描述或编号"
                  value={searchTerm}
                  onChange={(event) => handleSearch(event.target.value)}
                  className="h-9 pl-10"
                />
              </div>
              <Select
                value={filters.test_plan_id ? String(filters.test_plan_id) : 'all'}
                onValueChange={(value) => handleUpdateFilters({ test_plan_id: value === 'all' ? undefined : Number(value) })}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="测试计划" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部计划</SelectItem>
                  {testPlans.map((plan) => (
                    <SelectItem key={plan.id} value={String(plan.id)}>{plan.plan_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleUpdateFilters({ status: value === 'all' ? undefined : value as DefectStatus })}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  {statusOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.severity || 'all'}
                onValueChange={(value) => handleUpdateFilters({ severity: value === 'all' ? undefined : value as DefectSeverity })}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="严重程度" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部程度</SelectItem>
                  {severityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.defect_type || 'all'}
                onValueChange={(value) => handleUpdateFilters({ defect_type: value === 'all' ? undefined : value as DefectType })}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="缺陷类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  {defectTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {selectedDefects.length > 0 && (
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <span className="text-sm text-muted-foreground">已选择 {selectedDefects.length} 个缺陷</span>
              <div className="flex flex-wrap gap-2">
                <select
                  value={assignUserId}
                  onChange={(event) => setAssignUserId(event.target.value)}
                  className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">选择负责人</option>
                  {users.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userName(user)}</option>
                  ))}
                </select>
                <Button variant="outline" size="sm" disabled={!assignUserId || assignDefect.isPending} onClick={batchAssign}>
                  <UserCheck className="w-4 h-4 mr-2" />
                  批量分配
                </Button>
                <Button variant="outline" size="sm" onClick={handleClearSelection}>取消选择</Button>
              </div>
            </div>
          )}
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedDefects.length === defects.length && defects.length > 0}
                      onCheckedChange={() => handleSelectAllDefects(defects.map((defect) => defect.id))}
                    />
                  </TableHead>
                  <TableHead className="min-w-[260px]">缺陷标题</TableHead>
                  <TableHead className="w-28">类型</TableHead>
                  <TableHead className="w-24">严重程度</TableHead>
                  <TableHead className="w-20">优先级</TableHead>
                  <TableHead className="w-24">状态</TableHead>
                  <TableHead className="min-w-[200px]">关联对象</TableHead>
                  <TableHead className="w-28">报告人</TableHead>
                  <TableHead className="w-28">负责人</TableHead>
                  <TableHead className="w-32">报告时间</TableHead>
                  <TableHead className="sticky right-0 z-10 w-32 bg-card text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {defects.map((defect) => (
                  <TableRow key={defect.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedDefects.includes(defect.id)}
                        onCheckedChange={() => handleSelectDefect(defect.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        onClick={() => setDetailDefect(defect)}
                        className="text-left font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400"
                      >
                        {defect.title}
                      </button>
                      <div className="text-sm text-gray-500 dark:text-gray-400">{defect.defect_code}</div>
                      {defect.found_in_version && (
                        <div className="text-xs text-gray-400 dark:text-gray-500">发现版本：{defect.found_in_version}</div>
                      )}
                    </TableCell>
                    <TableCell><Badge variant="outline">{labelOf(defectTypeOptions, defect.defect_type)}</Badge></TableCell>
                    <TableCell>{getSeverityBadge(defect.severity)}</TableCell>
                    <TableCell><Badge variant="secondary">{labelOf(priorityOptions, defect.priority)}</Badge></TableCell>
                    <TableCell>{getStatusBadge(defect.status)}</TableCell>
                    <TableCell>
                      <div className="max-w-[220px] space-y-1 text-xs">
                        {getRelatedPlanId(defect) ? (
                          <Link to={`/test-manager/test-plans/${getRelatedPlanId(defect)}`} className="block truncate text-blue-600 hover:text-blue-800 dark:text-blue-400">
                            {getPlanLabel(getRelatedPlanId(defect))}
                          </Link>
                        ) : null}
                        {defect.test_case_id ? (
                          <Link to={`/test-manager/test-cases/${defect.test_case_id}`} className="block truncate text-blue-600 hover:text-blue-800 dark:text-blue-400">
                            {getCaseLabel(defect.test_case_id)}
                          </Link>
                        ) : null}
                        {defect.test_execution_id ? (
                          <Link to={`/test-manager/executions/${defect.test_execution_id}`} className="block truncate text-blue-600 hover:text-blue-800 dark:text-blue-400">
                            {getExecutionLabel(defect.test_execution_id)}
                          </Link>
                        ) : null}
                        {defect.requirement_id ? (
                          <Link to={`/requirements?search=${encodeURIComponent(getRequirementLabel(defect.requirement_id))}`} className="block truncate text-blue-600 hover:text-blue-800 dark:text-blue-400">
                            {getRequirementLabel(defect.requirement_id)}
                          </Link>
                        ) : null}
                        {!getRelatedPlanId(defect) && !defect.test_case_id && !defect.test_execution_id && !defect.requirement_id && '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                        <span>{userNameById[Number(defect.reporter_id)] || `用户 #${defect.reporter_id}`}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                        <span>{defect.assignee_id ? (userNameById[Number(defect.assignee_id)] || `用户 #${defect.assignee_id}`) : '未分配'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                        <span>{formatDate(defect.reported_at)}</span>
                      </div>
                    </TableCell>
                    <TableCell className="sticky right-0 bg-card text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" title="查看详情" onClick={() => setDetailDefect(defect)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" title="编辑" onClick={() => openEditForm(defect)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" title="分配负责人" onClick={() => openAssignDialog(defect)}>
                          <UserCheck className="h-4 w-4" />
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8" title="更多操作">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {(statusTransitions[defect.status] || []).map((status) => (
                              <DropdownMenuItem key={status} onClick={() => handleStatusChange(defect, status)}>
                                <AlertTriangle className="w-4 h-4 mr-2" />
                                设为{labelOf(statusOptions, status)}
                              </DropdownMenuItem>
                            ))}
                            {[DefectStatus.NEW, DefectStatus.REJECTED].includes(defect.status) && (
                              <DropdownMenuItem onClick={() => setDeleteDefectRow(defect)}>
                                <Trash2 className="w-4 h-4 mr-2" />
                                删除
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {defects.length === 0 && (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">暂无缺陷数据</div>
          )}
        </CardContent>
      </Card>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-3xl">
          <form onSubmit={submitForm} className="space-y-4">
            <DialogHeader>
              <DialogTitle>{editingDefect ? '编辑缺陷' : '创建缺陷'}</DialogTitle>
            </DialogHeader>

            {formError && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20">{formError}</div>}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="space-y-1 md:col-span-2">
                <span className="text-sm font-medium">缺陷标题</span>
                <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="text-sm font-medium">缺陷描述</span>
                <Textarea
                  rows={4}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="text-sm font-medium">复现步骤</span>
                <Textarea
                  rows={3}
                  value={form.steps_to_reproduce}
                  onChange={(event) => setForm({ ...form, steps_to_reproduce: event.target.value })}
                />
              </label>

              <div className="space-y-3 rounded-md border bg-muted/20 p-3 md:col-span-2">
                <div>
                  <div className="text-sm font-medium">业务关联</div>
                  <p className="text-xs text-muted-foreground">把缺陷关联到用例、执行记录或需求。测试计划用于筛选用例，最终通过用例或执行记录归集到计划。</p>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <label className="space-y-1">
                    <span className="text-sm font-medium">测试计划</span>
                    <select
                      value={form.test_plan_id}
                      onChange={(event) => handlePlanChange(event.target.value)}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">暂不关联计划</option>
                      {testPlans.map((plan) => (
                        <option key={plan.id} value={String(plan.id)}>{plan.plan_name}</option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1">
                    <span className="text-sm font-medium">测试用例</span>
                    <select
                      value={form.test_case_id}
                      onChange={(event) => handleCaseChange(event.target.value)}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">暂不关联用例</option>
                      {filteredCases.map((testCase) => (
                        <option key={testCase.id} value={String(testCase.id)}>
                          {testCase.case_title} ({testCase.case_code})
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1">
                    <span className="text-sm font-medium">执行记录</span>
                    <select
                      value={form.test_execution_id}
                      onChange={(event) => handleExecutionChange(event.target.value)}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">暂不关联执行</option>
                      {filteredExecutions.map((execution) => (
                        <option key={execution.id} value={String(execution.id)}>
                          {execution.execution_code || `执行 #${execution.id}`} - {execution.execution_status}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1">
                    <span className="text-sm font-medium">关联需求</span>
                    <select
                      value={form.requirement_id}
                      onChange={(event) => updateForm({ requirement_id: event.target.value })}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">暂不关联需求</option>
                      {requirements.map((requirement) => (
                        <option key={requirement.id} value={String(requirement.id)}>
                          {requirement.title} ({requirement.requirement_code || requirement.id})
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>

              <label className="space-y-1">
                <span className="text-sm font-medium">缺陷类型</span>
                <select
                  value={form.defect_type}
                  onChange={(event) => setForm({ ...form, defect_type: event.target.value })}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {defectTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">负责人</span>
                <select
                  value={form.assignee_id}
                  onChange={(event) => setForm({ ...form, assignee_id: event.target.value })}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">暂不分配</option>
                  {users.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userName(user)}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">严重程度</span>
                <select
                  value={form.severity}
                  onChange={(event) => setForm({ ...form, severity: event.target.value })}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {severityOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">优先级</span>
                <select
                  value={form.priority}
                  onChange={(event) => setForm({ ...form, priority: event.target.value })}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {priorityOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">发现版本</span>
                <Input value={form.found_in_version} onChange={(event) => setForm({ ...form, found_in_version: event.target.value })} />
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium">测试环境</span>
                <Input value={form.test_environment} onChange={(event) => setForm({ ...form, test_environment: event.target.value })} />
              </label>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button>
              <Button type="submit" disabled={createDefect.isPending || updateDefect.isPending}>
                {editingDefect ? '保存修改' : '保存缺陷'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(detailDefect)} onOpenChange={(open) => !open && setDetailDefect(null)}>
        <DialogContent className="max-w-4xl">
          {detailDefect && (
            <div className="space-y-4">
              <DialogHeader>
                <DialogTitle>{detailDefect.title}</DialogTitle>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-500 dark:text-gray-400">编号：</span>{detailDefect.defect_code}</div>
                <div><span className="text-gray-500 dark:text-gray-400">状态：</span>{labelOf(statusOptions, detailDefect.status)}</div>
                <div><span className="text-gray-500 dark:text-gray-400">类型：</span>{labelOf(defectTypeOptions, detailDefect.defect_type)}</div>
                <div><span className="text-gray-500 dark:text-gray-400">严重程度：</span>{labelOf(severityOptions, detailDefect.severity)}</div>
                <div><span className="text-gray-500 dark:text-gray-400">优先级：</span>{labelOf(priorityOptions, detailDefect.priority)}</div>
                <div><span className="text-gray-500 dark:text-gray-400">负责人：</span>{detailDefect.assignee_id ? (userNameById[Number(detailDefect.assignee_id)] || `用户 #${detailDefect.assignee_id}`) : '未分配'}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium">关联对象</div>
                <div className="grid grid-cols-1 gap-2 rounded-md bg-gray-50 p-3 text-sm md:grid-cols-2 dark:bg-gray-800/50">
                  {getRelatedPlanId(detailDefect) ? (
                    <Link to={`/test-manager/test-plans/${getRelatedPlanId(detailDefect)}`} className="text-blue-600 hover:text-blue-800 dark:text-blue-400">
                      计划：{getPlanLabel(getRelatedPlanId(detailDefect))}
                    </Link>
                  ) : <span className="text-gray-500 dark:text-gray-400">计划：未关联</span>}
                  {detailDefect.test_case_id ? (
                    <Link to={`/test-manager/test-cases/${detailDefect.test_case_id}`} className="text-blue-600 hover:text-blue-800 dark:text-blue-400">
                      用例：{getCaseLabel(detailDefect.test_case_id)}
                    </Link>
                  ) : <span className="text-gray-500 dark:text-gray-400">用例：未关联</span>}
                  {detailDefect.test_execution_id ? (
                    <Link to={`/test-manager/executions/${detailDefect.test_execution_id}`} className="text-blue-600 hover:text-blue-800 dark:text-blue-400">
                      执行：{getExecutionLabel(detailDefect.test_execution_id)}
                    </Link>
                  ) : <span className="text-gray-500 dark:text-gray-400">执行：未关联</span>}
                  {detailDefect.requirement_id ? (
                    <Link to={`/requirements?search=${encodeURIComponent(getRequirementLabel(detailDefect.requirement_id))}`} className="text-blue-600 hover:text-blue-800 dark:text-blue-400">
                      需求：{getRequirementLabel(detailDefect.requirement_id)}
                    </Link>
                  ) : <span className="text-gray-500 dark:text-gray-400">需求：未关联</span>}
                </div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium">缺陷描述</div>
                <div className="rounded-md bg-gray-50 p-3 text-sm whitespace-pre-wrap dark:bg-gray-800/50">{detailDefect.description || '-'}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium">复现步骤</div>
                <div className="rounded-md bg-gray-50 p-3 text-sm whitespace-pre-wrap dark:bg-gray-800/50">{detailDefect.steps_to_reproduce || '-'}</div>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-3 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">状态处理</div>
                    {getStatusBadge(detailDefect.status)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(statusTransitions[detailDefect.status] || []).map((status) => (
                      <Button key={status} variant="outline" size="sm" onClick={() => handleStatusChange(detailDefect, status)}>
                        设为{labelOf(statusOptions, status)}
                      </Button>
                    ))}
                    {(statusTransitions[detailDefect.status] || []).length === 0 && (
                      <span className="text-sm text-gray-500 dark:text-gray-400">当前状态暂无后续流转</span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <span>报告：{formatDate(detailDefect.reported_at)}</span>
                    <span>解决：{detailDefect.resolved_at ? formatDate(detailDefect.resolved_at) : '-'}</span>
                    <span>验证：{detailDefect.verified_at ? formatDate(detailDefect.verified_at) : '-'}</span>
                    <span>修复版本：{detailDefect.fixed_in_version || '-'}</span>
                  </div>
                </div>

                <div className="space-y-3 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center text-sm font-medium">
                      <Paperclip className="mr-2 h-4 w-4" />
                      附件
                    </div>
                    <label className="inline-flex h-8 cursor-pointer items-center rounded-md border px-3 text-sm hover:bg-accent">
                      上传
                      <input type="file" className="hidden" onChange={handleAttachmentChange} />
                    </label>
                  </div>
                  <div className="max-h-32 space-y-2 overflow-y-auto">
                    {(detailDefect.attachments || []).length ? detailDefect.attachments.map((file, index) => (
                      <div key={`${file.file_path || file.filename}-${index}`} className="flex items-center justify-between rounded bg-gray-50 px-2 py-1 text-xs dark:bg-gray-800/50">
                        <span className="truncate">{file.filename || `附件 ${index + 1}`}</span>
                        <span className="ml-2 text-gray-500 dark:text-gray-400">{formatFileSize(file.file_size)}</span>
                      </div>
                    )) : (
                      <div className="text-sm text-gray-500 dark:text-gray-400">暂无附件</div>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-3 rounded-md border p-3">
                <div className="flex items-center text-sm font-medium">
                  <MessageSquare className="mr-2 h-4 w-4" />
                  处理评论
                </div>
                <div className="max-h-40 space-y-2 overflow-y-auto">
                  {detailComments.isLoading ? (
                    <div className="text-sm text-gray-500 dark:text-gray-400">评论加载中...</div>
                  ) : (detailComments.data?.data || []).length ? (
                    (detailComments.data?.data || []).map((comment) => (
                      <div key={comment.id} className="rounded bg-gray-50 p-2 text-sm dark:bg-gray-800/50">
                        <div className="mb-1 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                          <span>{userNameById[Number(comment.user_id)] || `用户 #${comment.user_id}`}</span>
                          <span>{formatDate(comment.created_at)}</span>
                        </div>
                        <div className="whitespace-pre-wrap">{comment.content}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-gray-500 dark:text-gray-400">暂无评论</div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Textarea
                    rows={2}
                    value={commentText}
                    onChange={(event) => setCommentText(event.target.value)}
                    placeholder="补充处理说明、验证结论或沟通记录"
                  />
                  <Button className="self-end" disabled={!commentText.trim() || addDefectComment.isPending} onClick={submitComment}>
                    发送
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDetailDefect(null)}>关闭</Button>
                <Button onClick={() => { setDetailDefect(null); openEditForm(detailDefect) }}>编辑</Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(assignDefectRow)} onOpenChange={(open) => !open && setAssignDefectRow(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>分配缺陷负责人</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-sm text-gray-600 dark:text-gray-400">{assignDefectRow?.title}</div>
            <select
              value={assignUserId}
              onChange={(event) => setAssignUserId(event.target.value)}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">请选择负责人</option>
              {users.map((user) => (
                <option key={user.id} value={String(user.id)}>{userName(user)}</option>
              ))}
            </select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDefectRow(null)}>取消</Button>
            <Button disabled={!assignUserId || assignDefect.isPending} onClick={submitAssign}>确认分配</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(statusDialog)} onOpenChange={(open) => !open && setStatusDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>流转缺陷状态</DialogTitle>
          </DialogHeader>
          {statusDialog && (
            <div className="space-y-4">
              <div className="rounded-md bg-gray-50 p-3 text-sm dark:bg-gray-800/50">
                <div className="font-medium">{statusDialog.defect.title}</div>
                <div className="mt-1 text-gray-600 dark:text-gray-400">
                  {labelOf(statusOptions, statusDialog.defect.status)} → {labelOf(statusOptions, statusDialog.status)}
                </div>
              </div>

              {statusDialog.status === DefectStatus.RESOLVED && (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <label className="space-y-1">
                    <span className="text-sm font-medium">解决方案</span>
                    <select
                      value={statusResolution}
                      onChange={(event) => setStatusResolution(event.target.value)}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      {resolutionOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="text-sm font-medium">修复版本</span>
                    <Input value={statusFixedVersion} onChange={(event) => setStatusFixedVersion(event.target.value)} />
                  </label>
                </div>
              )}

              <label className="space-y-1">
                <span className="text-sm font-medium">处理说明</span>
                <Textarea
                  rows={4}
                  value={statusNotes}
                  onChange={(event) => setStatusNotes(event.target.value)}
                  placeholder="说明处理原因、修复范围、验证依据或重开原因"
                />
              </label>
              {statusError && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20">{statusError}</div>}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusDialog(null)}>取消</Button>
            <Button disabled={updateDefectStatus.isPending} onClick={submitStatusChange}>确认流转</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteDefectRow)}
        title="删除缺陷"
        description={`确认删除缺陷“${deleteDefectRow?.title || ''}”？删除后无法恢复。`}
        confirmText="删除"
        cancelText="取消"
        variant="destructive"
        onCancel={() => setDeleteDefectRow(null)}
        onConfirm={confirmDelete}
      />
    </div>
  )
}

export default DefectList
