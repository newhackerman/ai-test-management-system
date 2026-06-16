// @ts-nocheck
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Edit,
  Eye,
  FileText,
  Filter,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  UserCheck,
  X,
} from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import requirementService from '@/services/requirementService'
import ProjectService from '@/services/projectService'
import userService from '@/services/user-service'
import type { Requirement } from '@/types/requirement'

const requirementTypes = [
  { value: 'FUNCTIONAL', label: '功能需求' },
  { value: 'NON_FUNCTIONAL', label: '非功能需求' },
  { value: 'CONSTRAINT', label: '约束条件' },
  { value: 'INTERFACE', label: '接口需求' },
]

const priorities = [
  { value: 'CRITICAL', label: '紧急' },
  { value: 'HIGH', label: '高' },
  { value: 'MEDIUM', label: '中' },
  { value: 'LOW', label: '低' },
  { value: 'OPTIONAL', label: '可选' },
]

const businessValues = [
  { value: 'CORE', label: '核心' },
  { value: 'IMPORTANT', label: '重要' },
  { value: 'NORMAL', label: '普通' },
  { value: 'OPTIONAL', label: '可选' },
]

const complexities = [
  { value: 'SIMPLE', label: '简单' },
  { value: 'MEDIUM', label: '中等' },
  { value: 'COMPLEX', label: '复杂' },
  { value: 'VERY_COMPLEX', label: '非常复杂' },
]

const statuses = [
  { value: 'DRAFT', label: '草稿' },
  { value: 'PENDING_REVIEW', label: '待评审' },
  { value: 'REVIEWING', label: '评审中' },
  { value: 'NEEDS_REVISION', label: '需修改' },
  { value: 'APPROVED', label: '已批准' },
  { value: 'IN_DEVELOPMENT', label: '开发中' },
  { value: 'PAUSED', label: '已暂停' },
  { value: 'TESTING', label: '测试中' },
  { value: 'TEST_FAILED', label: '测试未通过' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'DEPLOYED', label: '已发布' },
  { value: 'CLOSED', label: '已关闭' },
  { value: 'CANCELLED', label: '已取消' },
]

const statusTransitions = {
  DRAFT: ['PENDING_REVIEW', 'CANCELLED'],
  PENDING_REVIEW: ['REVIEWING', 'DRAFT', 'CANCELLED'],
  REVIEWING: ['APPROVED', 'NEEDS_REVISION', 'CANCELLED'],
  NEEDS_REVISION: ['PENDING_REVIEW', 'CANCELLED'],
  APPROVED: ['IN_DEVELOPMENT', 'CANCELLED'],
  IN_DEVELOPMENT: ['TESTING', 'PAUSED', 'NEEDS_REVISION'],
  PAUSED: ['IN_DEVELOPMENT', 'CANCELLED'],
  TESTING: ['COMPLETED', 'TEST_FAILED'],
  TEST_FAILED: ['IN_DEVELOPMENT', 'CANCELLED'],
  COMPLETED: ['DEPLOYED', 'NEEDS_REVISION'],
  DEPLOYED: ['CLOSED'],
  CLOSED: ['DEPLOYED'],
  CANCELLED: ['DRAFT'],
}

const emptyForm = {
  project_id: '',
  title: '',
  description: '',
  acceptance_criteria: '',
  requirement_type: 'FUNCTIONAL',
  category: '',
  priority: 'MEDIUM',
  business_value: 'NORMAL',
  complexity: '',
  estimated_effort: '',
  assignee_id: '',
  reviewer_id: '',
  planned_start_date: '',
  planned_end_date: '',
  tags_text: '',
}

const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

const readAiDraft = (stateDraft, destination) => {
  if (stateDraft?.source === 'ai-assistant' && stateDraft.destination === destination) return stateDraft

  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_IMPORT_DRAFT_KEY) || 'null')
    return saved?.source === 'ai-assistant' && saved.destination === destination ? saved : null
  } catch {
    return null
  }
}

const firstReadableLine = (content = '', fallback = 'AI 导入需求') => {
  const line = content
    .split('\n')
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith('|') && !/^[-*_]{3,}$/.test(item))

  return (line || fallback)
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[\d一二三四五六七八九十]+[.、)]\s*/, '')
    .slice(0, 100)
}

const extractSection = (content = '', keywords = []) => {
  const lines = content.split('\n')
  const start = lines.findIndex((line) => keywords.some((keyword) => line.includes(keyword)))
  if (start < 0) return ''

  const collected = []
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index]
    if (/^#{1,6}\s+/.test(line) && collected.length) break
    collected.push(line)
  }

  return collected.join('\n').trim()
}

const buildRequirementDraftForm = (draft, projectId) => {
  const content = draft?.content || ''
  return {
    ...emptyForm,
    project_id: projectId || '',
    title: draft?.title || firstReadableLine(content),
    description: content,
    acceptance_criteria: extractSection(content, ['验收标准', '接受标准', '验收条件']) || '请根据 AI 分析内容补充可验证的验收标准。',
    requirement_type: 'FUNCTIONAL',
    priority: 'MEDIUM',
    business_value: 'NORMAL',
    category: 'AI 导入',
    tags_text: 'AI导入',
  }
}

const optionLabel = (options, value) => options.find((item) => item.value === value)?.label || value || '-'
const userLabel = (users, id) => {
  const user = users.find((item) => Number(item.id) === Number(id))
  return user ? user.real_name || user.nickname || user.username : '-'
}
const projectLabel = (projects, id) => {
  const project = projects.find((item) => Number(item.id) === Number(id))
  return project ? `${project.project_name || project.name} (${project.project_code || project.id})` : `项目 #${id}`
}
const formatDate = (value) => (value ? new Date(value).toLocaleDateString('zh-CN') : '-')
const compactDateTime = (value) => (value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-')

function RequirementsManagement() {
  const location = useLocation()
  const [aiDraft] = useState(() => readAiDraft((location.state as any)?.aiImport, 'requirement'))
  const [aiDraftConsumed, setAiDraftConsumed] = useState(false)
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [projects, setProjects] = useState([])
  const [users, setUsers] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [selectedIds, setSelectedIds] = useState([])
  const [selectedRequirement, setSelectedRequirement] = useState(null)
  const [editingRequirement, setEditingRequirement] = useState(null)
  const [statusRequirement, setStatusRequirement] = useState(null)
  const [deleteRequirement, setDeleteRequirement] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [statusForm, setStatusForm] = useState({ status: '', reason: '' })
  const [filters, setFilters] = useState({
    search: '',
    project_id: '',
    status: '',
    priority: '',
    requirement_type: '',
    assignee_id: '',
    category: '',
  })
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const categories = useMemo(() => {
    const values = new Set(requirements.map((item) => item.category).filter(Boolean))
    return Array.from(values)
  }, [requirements])

  const selectedRows = requirements.filter((item) => selectedIds.includes(item.id))
  const allCurrentSelected = requirements.length > 0 && requirements.every((item) => selectedIds.includes(item.id))

  const loadReferences = async () => {
    const [projectResponse, userResponse] = await Promise.all([
      ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
      userService.getUsers({ page: 1, size: 100, sort_by: 'created_at', sort_order: 'desc' }),
    ])
    setProjects(projectResponse.data || [])
    setUsers(userResponse.users || [])
  }

  const loadRequirements = async (nextPage = page, overrideFilters = null) => {
    setLoading(true)
    setError('')
    try {
      const activeFilters = overrideFilters || filters
      const requestFilters = {
        page: nextPage,
        size: pageSize,
        search: activeFilters.search.trim() || undefined,
        project_id: activeFilters.project_id ? Number(activeFilters.project_id) : undefined,
        status: activeFilters.status ? [activeFilters.status] : undefined,
        priority: activeFilters.priority ? [activeFilters.priority] : undefined,
        requirement_type: activeFilters.requirement_type ? activeFilters.requirement_type : undefined,
        assignee_id: activeFilters.assignee_id ? Number(activeFilters.assignee_id) : undefined,
        category: activeFilters.category || undefined,
        sort_by: 'updated_at',
        sort_order: 'desc',
      }
      const response = await requirementService.getRequirements(requestFilters)
      const list = response.data || []
      setRequirements(list)
      setTotal(response.total || list.length)
      setPage(nextPage)
      setSelectedIds((current) => current.filter((id) => list.some((item) => item.id === id)))
      if (selectedRequirement && !list.some((item) => item.id === selectedRequirement.id)) {
        setSelectedRequirement(null)
      }
    } catch (err: any) {
      setError(err?.message || '加载需求失败')
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async (overrideFilters = null) => {
    try {
      const activeFilters = overrideFilters || filters
      const data = await requirementService.getRequirementStatistics(activeFilters.project_id ? Number(activeFilters.project_id) : undefined)
      setStatistics(data)
    } catch {
      setStatistics(null)
    }
  }

  useEffect(() => {
    loadReferences().catch((err) => setError(err?.message || '加载项目和人员失败'))
  }, [])

  useEffect(() => {
    loadRequirements(1)
    loadStatistics()
  }, [])

  useEffect(() => {
    if (!aiDraft || aiDraftConsumed) return
    const projectId = filters.project_id || String(projects[0]?.id || '')
    if (!projectId) return

    setEditingRequirement(null)
    setForm(buildRequirementDraftForm(aiDraft, projectId))
    setNotice('已从 AI 助手导入需求草稿，请核对后保存。')
    sessionStorage.removeItem(AI_IMPORT_DRAFT_KEY)
    setAiDraftConsumed(true)
  }, [aiDraft, aiDraftConsumed, filters.project_id, projects])

  const openCreate = () => {
    setEditingRequirement(null)
    setForm({
      ...emptyForm,
      project_id: filters.project_id || String(projects[0]?.id || ''),
    })
  }

  const openEdit = (requirement) => {
    setEditingRequirement(requirement)
    setForm({
      project_id: String(requirement.project_id || ''),
      title: requirement.title || '',
      description: requirement.description || '',
      acceptance_criteria: requirement.acceptance_criteria || '',
      requirement_type: requirement.requirement_type || 'FUNCTIONAL',
      category: requirement.category || '',
      priority: requirement.priority || 'MEDIUM',
      business_value: requirement.business_value || 'NORMAL',
      complexity: requirement.complexity || '',
      estimated_effort: requirement.estimated_effort ? String(requirement.estimated_effort) : '',
      assignee_id: requirement.assignee_id ? String(requirement.assignee_id) : '',
      reviewer_id: requirement.reviewer_id ? String(requirement.reviewer_id) : '',
      planned_start_date: requirement.planned_start_date || '',
      planned_end_date: requirement.planned_end_date || '',
      tags_text: (requirement.tags || []).join(', '),
    })
  }

  const closeForm = () => {
    setEditingRequirement(null)
    setForm(emptyForm)
  }

  const buildPayload = () => {
    const tags = form.tags_text
      .split(/[,\n，]/)
      .map((item) => item.trim())
      .filter(Boolean)

    return {
      project_id: Number(form.project_id),
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      acceptance_criteria: form.acceptance_criteria.trim() || undefined,
      requirement_type: form.requirement_type,
      category: form.category.trim() || undefined,
      priority: form.priority,
      business_value: form.business_value,
      complexity: form.complexity || undefined,
      estimated_effort: form.estimated_effort === '' ? undefined : Number(form.estimated_effort),
      assignee_id: form.assignee_id ? Number(form.assignee_id) : undefined,
      reviewer_id: form.reviewer_id ? Number(form.reviewer_id) : undefined,
      planned_start_date: form.planned_start_date || undefined,
      planned_end_date: form.planned_end_date || undefined,
      tags,
      custom_fields: {},
    }
  }

  const validateForm = () => {
    if (!form.project_id) return '请选择所属项目'
    if (!form.title.trim()) return '请填写需求标题'
    if (form.planned_start_date && form.planned_end_date && form.planned_end_date < form.planned_start_date) {
      return '计划完成日期不能早于计划开始日期'
    }
    if (form.estimated_effort !== '' && Number(form.estimated_effort) < 0) return '预估工作量不能小于 0'
    return ''
  }

  const submitForm = async () => {
    const validationMessage = validateForm()
    if (validationMessage) {
      setError(validationMessage)
      return
    }

    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = buildPayload()
      if (editingRequirement) {
        await requirementService.updateRequirement(editingRequirement.id, payload)
        setNotice('需求已更新')
      } else {
        await requirementService.createRequirement(payload)
        setNotice('需求已创建')
      }
      closeForm()
      await loadRequirements(editingRequirement ? page : 1)
      await loadStatistics()
    } catch (err: any) {
      setError(err?.message || (editingRequirement ? '更新需求失败' : '创建需求失败'))
    } finally {
      setSaving(false)
    }
  }

  const openStatus = (requirement) => {
    const nextStatuses = statusTransitions[requirement.status] || []
    setStatusRequirement(requirement)
    setStatusForm({ status: nextStatuses[0] || requirement.status, reason: '' })
  }

  const submitStatus = async () => {
    if (!statusRequirement || !statusForm.status) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await requirementService.updateRequirementStatus(statusRequirement.id, {
        status: statusForm.status,
        reason: statusForm.reason.trim() || undefined,
      })
      setNotice(`需求状态已更新为${optionLabel(statuses, statusForm.status)}`)
      setStatusRequirement(null)
      await loadRequirements(page)
      await loadStatistics()
    } catch (err: any) {
      setError(err?.message || '更新需求状态失败')
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteRequirement) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await requirementService.deleteRequirement(deleteRequirement.id)
      setNotice('需求已删除')
      setDeleteRequirement(null)
      await loadRequirements(page)
      await loadStatistics()
    } catch (err: any) {
      setError(err?.message || '删除需求失败')
    } finally {
      setSaving(false)
    }
  }

  const batchToReview = async () => {
    const draftIds = selectedRows.filter((item) => item.status === 'DRAFT').map((item) => item.id)
    if (draftIds.length === 0) {
      setError('请选择草稿状态的需求')
      return
    }
    setSaving(true)
    setError('')
    try {
      await Promise.all(
        draftIds.map((id) => requirementService.updateRequirementStatus(id, { status: 'PENDING_REVIEW', reason: '批量提交评审' })),
      )
      setNotice(`已提交 ${draftIds.length} 条需求进入评审`)
      setSelectedIds([])
      await loadRequirements(page)
      await loadStatistics()
    } catch (err: any) {
      setError(err?.message || '批量提交评审失败')
    } finally {
      setSaving(false)
    }
  }

  const resetFilters = () => {
    const nextFilters = { search: '', project_id: '', status: '', priority: '', requirement_type: '', assignee_id: '', category: '' }
    setFilters(nextFilters)
    loadRequirements(1, nextFilters)
    loadStatistics(nextFilters)
  }

  const statusCards = useMemo(() => {
    const totalCount = statistics?.total_requirements || total
    const approved = Number(statistics?.status_distribution?.APPROVED || 0)
    const active = ['PENDING_REVIEW', 'REVIEWING', 'NEEDS_REVISION', 'APPROVED', 'IN_DEVELOPMENT', 'PAUSED', 'TESTING', 'TEST_FAILED']
      .reduce((sum, key) => sum + Number(statistics?.status_distribution?.[key] || 0), 0)
    const finished = ['COMPLETED', 'DEPLOYED', 'CLOSED'].reduce((sum, key) => sum + Number(statistics?.status_distribution?.[key] || 0), 0)
    return [
      { label: '需求总数', value: totalCount, hint: '当前筛选范围' },
      { label: '活跃需求', value: active, hint: '评审到测试阶段' },
      { label: '已批准', value: approved, hint: '可进入开发' },
      { label: '已交付', value: finished, hint: '完成、发布或关闭' },
    ]
  }, [statistics, total])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => { loadRequirements(page); loadStatistics() }} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            新建需求
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-2 p-3">
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {statusCards.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3 rounded-md border bg-muted/20 px-3 py-1.5">
                <span className="text-xs text-muted-foreground">{item.label}</span>
                <span className="text-base font-semibold leading-5 text-foreground">{item.value}</span>
              </div>
            ))}
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-6">
            <div className="relative xl:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filters.search}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
                onKeyDown={(event) => event.key === 'Enter' && loadRequirements(1)}
                placeholder="搜索标题、编号、描述或验收标准"
                className="pl-10"
              />
            </div>
            <SelectField value={filters.project_id} onChange={(value) => setFilters((current) => ({ ...current, project_id: value }))}>
              <option value="">全部项目</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.project_name || project.name}</option>
              ))}
            </SelectField>
            <SelectField value={filters.assignee_id} onChange={(value) => setFilters((current) => ({ ...current, assignee_id: value }))}>
              <option value="">全部负责人</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>{user.real_name || user.nickname || user.username}</option>
              ))}
            </SelectField>
            <SelectField value={filters.status} onChange={(value) => setFilters((current) => ({ ...current, status: value }))}>
              <option value="">全部状态</option>
              {statuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
            </SelectField>
            <SelectField value={filters.priority} onChange={(value) => setFilters((current) => ({ ...current, priority: value }))}>
              <option value="">全部优先级</option>
              {priorities.map((priority) => <option key={priority.value} value={priority.value}>{priority.label}</option>)}
            </SelectField>
            <SelectField value={filters.requirement_type} onChange={(value) => setFilters((current) => ({ ...current, requirement_type: value }))}>
              <option value="">全部类型</option>
              {requirementTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </SelectField>
            <SelectField value={filters.category} onChange={(value) => setFilters((current) => ({ ...current, category: value }))}>
              <option value="">全部分类</option>
              {categories.map((category) => <option key={category} value={category}>{category}</option>)}
            </SelectField>
            <div className="flex gap-2">
              <Button className="flex-1" variant="outline" onClick={() => { loadRequirements(1); loadStatistics() }} disabled={loading}>
                <Search className="mr-2 h-4 w-4" />
                查询
              </Button>
              <Button variant="ghost" onClick={resetFilters} disabled={loading}>清空</Button>
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={batchToReview} disabled={saving || selectedIds.length === 0}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              批量提交评审
            </Button>
          </div>
        </CardContent>
      </Card>

      {notice && <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{notice}</div>}
      {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800">{error}</div>}

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-y bg-muted/40 text-left text-muted-foreground">
                <tr>
                  <th className="w-12 px-3 py-2.5">
                    <Checkbox checked={allCurrentSelected} onCheckedChange={(checked) => {
                      setSelectedIds(checked ? Array.from(new Set([...selectedIds, ...requirements.map((item) => item.id)])) : selectedIds.filter((id) => !requirements.some((item) => item.id === id)))
                    }} />
                  </th>
                  <th className="min-w-[280px] px-3 py-2.5">需求</th>
                  <th className="min-w-[180px] px-3 py-2.5">项目</th>
                  <th className="px-3 py-2.5">类型</th>
                  <th className="px-3 py-2.5">状态</th>
                  <th className="px-3 py-2.5">优先级</th>
                  <th className="min-w-[120px] px-3 py-2.5">负责人</th>
                  <th className="min-w-[110px] px-3 py-2.5">计划完成</th>
                  <th className="min-w-[180px] px-3 py-2.5 text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-12 text-center text-muted-foreground">加载中...</td>
                  </tr>
                ) : requirements.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-12 text-center text-muted-foreground">暂无需求数据</td>
                  </tr>
                ) : (
                  requirements.map((requirement) => (
                    <tr key={requirement.id} className="border-b hover:bg-muted/30">
                      <td className="px-3 py-2.5">
                        <Checkbox
                          checked={selectedIds.includes(requirement.id)}
                          onCheckedChange={(checked) => {
                            setSelectedIds(checked ? [...selectedIds, requirement.id] : selectedIds.filter((id) => id !== requirement.id))
                          }}
                        />
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-start gap-3">
                          <div className="rounded-md bg-blue-50 p-2 text-blue-600 dark:text-blue-400 dark:bg-blue-900/20">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <button className="text-left font-medium text-foreground hover:text-blue-600 dark:text-blue-400" onClick={() => setSelectedRequirement(requirement)}>
                              {requirement.title}
                            </button>
                            <div className="mt-1 text-xs text-muted-foreground">{requirement.requirement_code || `REQ-${requirement.id}`}</div>
                            <div className="mt-1 line-clamp-1 max-w-xl text-xs text-muted-foreground">
                              {requirement.description || '暂无描述'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-muted-foreground">{projectLabel(projects, requirement.project_id)}</td>
                      <td className="px-3 py-2.5">{optionLabel(requirementTypes, requirement.requirement_type)}</td>
                      <td className="px-3 py-2.5"><StatusBadge status={requirement.status} /></td>
                      <td className="px-3 py-2.5"><PriorityBadge priority={requirement.priority} /></td>
                      <td className="px-3 py-2.5">{userLabel(users, requirement.assignee_id)}</td>
                      <td className="px-3 py-2.5">{formatDate(requirement.planned_end_date)}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="ghost" onClick={() => setSelectedRequirement(requirement)} title="查看详情">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => openEdit(requirement)}>
                            <Edit className="mr-1 h-3 w-3" />
                            编辑
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => openStatus(requirement)}>
                            状态
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => setDeleteRequirement(requirement)} disabled={requirement.status !== 'DRAFT'}>
                            <Trash2 className="mr-1 h-3 w-3" />
                            删除
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="flex flex-col gap-3 border-t px-4 py-3 md:flex-row md:items-center md:justify-between">
            <div className="text-sm text-muted-foreground">第 {page} / {totalPages} 页</div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1 || loading} onClick={() => loadRequirements(page - 1)}>
                <ChevronLeft className="mr-1 h-4 w-4" />
                上一页
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages || loading} onClick={() => loadRequirements(page + 1)}>
                下一页
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {(editingRequirement !== null || form !== emptyForm) && (
        <RequirementFormDialog
          title={editingRequirement ? '编辑需求' : '新建需求'}
          form={form}
          setForm={setForm}
          projects={projects}
          users={users}
          onClose={closeForm}
          onSubmit={submitForm}
          saving={saving}
        />
      )}

      {selectedRequirement && (
        <RequirementDetailDialog
          requirement={selectedRequirement}
          projects={projects}
          users={users}
          onClose={() => setSelectedRequirement(null)}
          onEdit={() => {
            openEdit(selectedRequirement)
            setSelectedRequirement(null)
          }}
          onStatus={() => {
            openStatus(selectedRequirement)
            setSelectedRequirement(null)
          }}
        />
      )}

      {statusRequirement && (
        <StatusDialog
          requirement={statusRequirement}
          form={statusForm}
          setForm={setStatusForm}
          onClose={() => setStatusRequirement(null)}
          onSubmit={submitStatus}
          saving={saving}
        />
      )}

      {deleteRequirement && (
        <ConfirmDialog
          title="删除需求"
          message={`确定删除需求“${deleteRequirement.title}”吗？只有草稿状态的需求允许删除，删除后不可恢复。`}
          onClose={() => setDeleteRequirement(null)}
          onConfirm={confirmDelete}
          saving={saving}
        />
      )}
    </div>
  )
}

function RequirementFormDialog({ title, form, setForm, projects, users, onClose, onSubmit, saving }) {
  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="所属项目" required>
              <SelectField value={form.project_id} onChange={(value) => update('project_id', value)}>
                <option value="">请选择项目</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.project_name || project.name}</option>
                ))}
              </SelectField>
            </Field>
            <Field label="需求类型">
              <SelectField value={form.requirement_type} onChange={(value) => update('requirement_type', value)}>
                {requirementTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
              </SelectField>
            </Field>
            <Field label="需求标题" required className="md:col-span-2">
              <Input value={form.title} onChange={(event) => update('title', event.target.value)} placeholder="例如：用户可以按项目筛选需求" />
            </Field>
            <Field label="优先级">
              <SelectField value={form.priority} onChange={(value) => update('priority', value)}>
                {priorities.map((priority) => <option key={priority.value} value={priority.value}>{priority.label}</option>)}
              </SelectField>
            </Field>
            <Field label="业务价值">
              <SelectField value={form.business_value} onChange={(value) => update('business_value', value)}>
                {businessValues.map((value) => <option key={value.value} value={value.value}>{value.label}</option>)}
              </SelectField>
            </Field>
            <Field label="分类">
              <Input value={form.category} onChange={(event) => update('category', event.target.value)} placeholder="例如：账号、报表、工作台" />
            </Field>
            <Field label="复杂度">
              <SelectField value={form.complexity} onChange={(value) => update('complexity', value)}>
                <option value="">暂不指定</option>
                {complexities.map((complexity) => <option key={complexity.value} value={complexity.value}>{complexity.label}</option>)}
              </SelectField>
            </Field>
            <Field label="负责人">
              <SelectField value={form.assignee_id} onChange={(value) => update('assignee_id', value)}>
                <option value="">暂不分配</option>
                {users.map((user) => <option key={user.id} value={user.id}>{user.real_name || user.nickname || user.username}</option>)}
              </SelectField>
            </Field>
            <Field label="评审人">
              <SelectField value={form.reviewer_id} onChange={(value) => update('reviewer_id', value)}>
                <option value="">暂不指定</option>
                {users.map((user) => <option key={user.id} value={user.id}>{user.real_name || user.nickname || user.username}</option>)}
              </SelectField>
            </Field>
            <Field label="计划开始">
              <Input type="date" value={form.planned_start_date} onChange={(event) => update('planned_start_date', event.target.value)} />
            </Field>
            <Field label="计划完成">
              <Input type="date" value={form.planned_end_date} onChange={(event) => update('planned_end_date', event.target.value)} />
            </Field>
            <Field label="预估工作量（人天）">
              <Input type="number" min="0" step="0.5" value={form.estimated_effort} onChange={(event) => update('estimated_effort', event.target.value)} />
            </Field>
            <Field label="标签">
              <Input value={form.tags_text} onChange={(event) => update('tags_text', event.target.value)} placeholder="多个标签用逗号分隔" />
            </Field>
            <Field label="需求描述" className="md:col-span-2">
              <Textarea rows={4} value={form.description} onChange={(event) => update('description', event.target.value)} placeholder="描述业务目标、用户场景和边界条件" />
            </Field>
            <Field label="验收标准" className="md:col-span-2">
              <Textarea rows={4} value={form.acceptance_criteria} onChange={(event) => update('acceptance_criteria', event.target.value)} placeholder="列出可验证的验收条件；批准需求前必须具备验收标准" />
            </Field>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={onSubmit} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function RequirementDetailDialog({ requirement, projects, users, onClose, onEdit, onStatus }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800">
        <div className="flex items-start justify-between border-b px-6 py-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{requirement.title}</h2>
              <StatusBadge status={requirement.status} />
              <PriorityBadge priority={requirement.priority} />
            </div>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{requirement.requirement_code} · 版本 {requirement.version}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-6">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard icon={<FileText className="h-4 w-4" />} label="所属项目" value={projectLabel(projects, requirement.project_id)} />
            <InfoCard icon={<UserCheck className="h-4 w-4" />} label="负责人" value={userLabel(users, requirement.assignee_id)} />
            <InfoCard icon={<CalendarDays className="h-4 w-4" />} label="计划完成" value={formatDate(requirement.planned_end_date)} />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section>
              <h3 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">需求描述</h3>
              <div className="min-h-[120px] whitespace-pre-wrap rounded-md border bg-gray-50 p-4 text-sm text-gray-700 dark:text-gray-300 dark:bg-gray-800/50">
                {requirement.description || '暂无描述'}
              </div>
            </section>
            <section>
              <h3 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">验收标准</h3>
              <div className="min-h-[120px] whitespace-pre-wrap rounded-md border bg-gray-50 p-4 text-sm text-gray-700 dark:text-gray-300 dark:bg-gray-800/50">
                {requirement.acceptance_criteria || '暂无验收标准'}
              </div>
            </section>
          </div>
          <div className="mt-6 grid gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
            <Info label="类型" value={optionLabel(requirementTypes, requirement.requirement_type)} />
            <Info label="分类" value={requirement.category || '-'} />
            <Info label="业务价值" value={optionLabel(businessValues, requirement.business_value)} />
            <Info label="复杂度" value={optionLabel(complexities, requirement.complexity)} />
            <Info label="预估工作量" value={requirement.estimated_effort ? `${requirement.estimated_effort} 人天` : '-'} />
            <Info label="质量分" value={requirement.quality_score ?? '-'} />
            <Info label="完整度" value={requirement.completeness_score ?? '-'} />
            <Info label="评审人" value={userLabel(users, requirement.reviewer_id)} />
            <Info label="计划开始" value={formatDate(requirement.planned_start_date)} />
            <Info label="实际开始" value={formatDate(requirement.actual_start_date)} />
            <Info label="实际完成" value={formatDate(requirement.actual_end_date)} />
            <Info label="更新时间" value={compactDateTime(requirement.updated_at)} />
          </div>
          {requirement.tags?.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {requirement.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onStatus}>变更状态</Button>
          <Button onClick={onEdit}>
            <Edit className="mr-2 h-4 w-4" />
            编辑
          </Button>
        </div>
      </div>
    </div>
  )
}

function StatusDialog({ requirement, form, setForm, onClose, onSubmit, saving }) {
  const nextStatuses = statusTransitions[requirement.status] || []
  const targetStatus = form.status
  const warning = getStatusWarning(requirement, targetStatus)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">变更需求状态</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{requirement.requirement_code} · 当前：{optionLabel(statuses, requirement.status)}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="space-y-4 px-6 py-5">
          {nextStatuses.length === 0 ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:text-amber-300 dark:bg-amber-900/20 dark:border-amber-800">当前状态没有可执行的下一步流转。</div>
          ) : (
            <>
              <Field label="目标状态" required>
                <SelectField value={form.status} onChange={(value) => setForm((current) => ({ ...current, status: value }))}>
                  {nextStatuses.map((status) => <option key={status} value={status}>{optionLabel(statuses, status)}</option>)}
                </SelectField>
              </Field>
              {warning && (
                <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:text-amber-300 dark:bg-amber-900/20 dark:border-amber-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
                  <span>{warning}</span>
                </div>
              )}
              <Field label="变更原因">
                <Textarea rows={4} value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="说明状态变更原因，便于后续追溯" />
              </Field>
            </>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={onSubmit} disabled={saving || nextStatuses.length === 0}>
            {saving ? '提交中...' : '确认变更'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function ConfirmDialog({ title, message, onClose, onConfirm, saving }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl dark:bg-gray-800">
        <div className="border-b px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
        </div>
        <div className="px-6 py-5 text-sm text-gray-700 dark:text-gray-300">{message}</div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button variant="destructive" onClick={onConfirm} disabled={saving}>{saving ? '删除中...' : '确认删除'}</Button>
        </div>
      </div>
    </div>
  )
}

function SelectField({ value, onChange, children }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
    >
      {children}
    </select>
  )
}

function Field({ label, required, className = '', children }) {
  return (
    <label className={`space-y-2 text-sm ${className}`}>
      <span className="font-medium text-gray-700 dark:text-gray-300">
        {label}
        {required && <span className="ml-1 text-red-500 dark:text-red-400">*</span>}
      </span>
      {children}
    </label>
  )
}

function Info({ label, value }) {
  return (
    <div className="rounded-md border bg-white p-3 dark:bg-gray-800">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  )
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="flex gap-3 rounded-md border bg-gray-50 p-4 dark:bg-gray-800/50">
      <div className="mt-0.5 text-blue-600 dark:text-blue-400">{icon}</div>
      <div>
        <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
        <div className="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{value}</div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const label = optionLabel(statuses, status)
  const className = {
    DRAFT: 'bg-gray-100 text-gray-700 dark:text-gray-300 dark:bg-gray-800',
    PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
    REVIEWING: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30',
    NEEDS_REVISION: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30',
    APPROVED: 'bg-green-100 text-green-800',
    IN_DEVELOPMENT: 'bg-purple-100 text-purple-800 dark:text-purple-300 dark:bg-purple-900/30',
    PAUSED: 'bg-slate-100 text-slate-700 dark:text-slate-300 dark:bg-slate-800',
    TESTING: 'bg-indigo-100 text-indigo-800 dark:text-indigo-300 dark:bg-indigo-900/30',
    TEST_FAILED: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30',
    COMPLETED: 'bg-emerald-100 text-emerald-800',
    DEPLOYED: 'bg-teal-100 text-teal-800',
    CLOSED: 'bg-zinc-100 text-zinc-700',
    CANCELLED: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30',
  }[status] || 'bg-gray-100 text-gray-700 dark:text-gray-300 dark:bg-gray-800'
  return <Badge variant="secondary" className={`border-0 ${className}`}>{label}</Badge>
}

function PriorityBadge({ priority }) {
  const label = optionLabel(priorities, priority)
  if (priority === 'CRITICAL') return <Badge variant="destructive">{label}</Badge>
  if (priority === 'HIGH') return <Badge className="border-0 bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30">{label}</Badge>
  if (priority === 'LOW' || priority === 'OPTIONAL') return <Badge variant="outline">{label}</Badge>
  return <Badge variant="secondary">{label}</Badge>
}

function getStatusWarning(requirement, status) {
  if (status === 'APPROVED' && !requirement.acceptance_criteria) return '批准前必须补充验收标准，否则后端会拒绝流转。'
  if (status === 'IN_DEVELOPMENT' && !requirement.assignee_id) return '进入开发前必须指定负责人。'
  if (status === 'TESTING' && !requirement.planned_end_date) return '进入测试前必须设置计划完成日期。'
  return ''
}

export default RequirementsManagement
