// @ts-nocheck
import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Edit,
  Eye,
  Filter,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Trash2,
  UserCheck,
  X,
  Zap,
} from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Textarea } from '@/components/ui/Textarea'
import RiskMatrix from '@/components/projects/RiskMatrix'
import ProjectService from '@/services/projectService'
import userService from '@/services/user-service'
import {
  MitigationStrategy,
  Risk,
  RiskCategory,
  RiskLevel,
  RiskStatus,
  getMitigationStrategyText,
  getRiskCategoryText,
  getRiskLevelText,
  getRiskStatusText,
  riskService,
} from '@/services/riskService'

const categoryOptions = [
  { value: RiskCategory.SCHEDULE, label: '进度风险' },
  { value: RiskCategory.QUALITY, label: '质量风险' },
  { value: RiskCategory.RESOURCE, label: '资源风险' },
  { value: RiskCategory.TECHNICAL, label: '技术风险' },
  { value: RiskCategory.EXTERNAL, label: '外部风险' },
]

const levelOptions = [
  { value: RiskLevel.LOW, label: '低风险' },
  { value: RiskLevel.MEDIUM, label: '中风险' },
  { value: RiskLevel.HIGH, label: '高风险' },
  { value: RiskLevel.CRITICAL, label: '严重风险' },
]

const strategyOptions = [
  { value: MitigationStrategy.AVOID, label: '规避' },
  { value: MitigationStrategy.MITIGATE, label: '缓解' },
  { value: MitigationStrategy.TRANSFER, label: '转移' },
  { value: MitigationStrategy.ACCEPT, label: '接受' },
]

const statusOptions = [
  { value: RiskStatus.IDENTIFIED, label: '已识别' },
  { value: RiskStatus.ANALYZING, label: '分析中' },
  { value: RiskStatus.MITIGATING, label: '缓解中' },
  { value: RiskStatus.MONITORING, label: '监控中' },
  { value: RiskStatus.CLOSED, label: '已关闭' },
]

const statusTransitions = {
  [RiskStatus.IDENTIFIED]: [RiskStatus.ANALYZING, RiskStatus.MITIGATING, RiskStatus.MONITORING, RiskStatus.CLOSED],
  [RiskStatus.ANALYZING]: [RiskStatus.MITIGATING, RiskStatus.MONITORING, RiskStatus.CLOSED],
  [RiskStatus.MITIGATING]: [RiskStatus.MONITORING, RiskStatus.CLOSED],
  [RiskStatus.MONITORING]: [RiskStatus.MITIGATING, RiskStatus.CLOSED],
  [RiskStatus.CLOSED]: [RiskStatus.MONITORING],
}

const emptyForm = {
  project_id: '',
  risk_name: '',
  description: '',
  risk_category: RiskCategory.SCHEDULE,
  risk_level: RiskLevel.MEDIUM,
  probability: '0.50',
  impact_score: '5',
  mitigation_strategy: MitigationStrategy.MITIGATE,
  mitigation_plan: '',
  contingency_plan: '',
  owner_id: '',
  target_resolution_date: '',
}

const tomorrowInput = () => {
  const date = new Date()
  date.setDate(date.getDate() + 2)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const optionLabel = (options, value) => options.find((item) => item.value === value)?.label || value || '-'
const formatDate = (value) => (value ? new Date(value).toLocaleDateString('zh-CN') : '-')
const formatDateTime = (value) => (value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-')
const scoreValue = (risk) => Number(risk?.risk_score ?? Number(risk?.probability || 0) * Number(risk?.impact_score || 0))

function RiskManagement() {
  const [risks, setRisks] = useState<Risk[]>([])
  const [projects, setProjects] = useState([])
  const [users, setUsers] = useState([])
  const [selectedRisk, setSelectedRisk] = useState<Risk | null>(null)
  const [editingRisk, setEditingRisk] = useState<Risk | null>(null)
  const [statusRisk, setStatusRisk] = useState<Risk | null>(null)
  const [deleteRisk, setDeleteRisk] = useState<Risk | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [statusForm, setStatusForm] = useState({ status: '', actual_resolution_date: '' })
  const [filters, setFilters] = useState({
    search: '',
    project_id: '',
    owner_id: '',
    risk_category: '',
    risk_level: '',
    status: '',
  })
  const [analysisProjectId, setAnalysisProjectId] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [detection, setDetection] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [modalError, setModalError] = useState('')
  const [notice, setNotice] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const userNameById = useMemo(() => {
    return users.reduce((result, user) => {
      result[Number(user.id)] = user.real_name || user.nickname || user.username
      return result
    }, {})
  }, [users])

  const projectNameById = useMemo(() => {
    return projects.reduce((result, project) => {
      result[Number(project.id)] = project.project_name || project.name || `项目 #${project.id}`
      return result
    }, {})
  }, [projects])

  const statusCards = useMemo(() => {
    const openRisks = risks.filter((risk) => risk.status !== RiskStatus.CLOSED)
    const highRisks = risks.filter((risk) => [RiskLevel.HIGH, RiskLevel.CRITICAL].includes(risk.risk_level))
    const avgScore = risks.length ? risks.reduce((sum, risk) => sum + scoreValue(risk), 0) / risks.length : 0
    const overdue = risks.filter((risk) => (
      risk.status !== RiskStatus.CLOSED &&
      risk.target_resolution_date &&
      new Date(risk.target_resolution_date) < new Date(new Date().toDateString())
    )).length

    return [
      { label: '风险总数', value: total, hint: '当前筛选范围' },
      { label: '未关闭风险', value: openRisks.length, hint: '需要持续跟进' },
      { label: '高危风险', value: highRisks.length, hint: '高风险与严重风险' },
      { label: '平均评分', value: avgScore.toFixed(2), hint: overdue ? `${overdue} 条已逾期` : '概率 × 影响' },
    ]
  }, [risks, total])

  const loadReferences = async () => {
    const [projectResponse, userResponse] = await Promise.all([
      ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
      userService.getUsers({ page: 1, size: 100, status: 'active', sort_by: 'username', sort_order: 'asc' }),
    ])
    const nextProjects = projectResponse.data || []
    setProjects(nextProjects)
    setUsers(userResponse.users || [])
    setAnalysisProjectId((current) => current || String(nextProjects[0]?.id || ''))
  }

  const loadRisks = async (nextPage = page, overrideFilters = null) => {
    setLoading(true)
    setError('')
    try {
      const activeFilters = overrideFilters || filters
      const response = await riskService.listRisks({
        page: nextPage,
        page_size: pageSize,
        search: activeFilters.search.trim() || undefined,
        project_id: activeFilters.project_id ? Number(activeFilters.project_id) : undefined,
        owner_id: activeFilters.owner_id ? Number(activeFilters.owner_id) : undefined,
        risk_category: activeFilters.risk_category || undefined,
        risk_level: activeFilters.risk_level || undefined,
        status: activeFilters.status || undefined,
        sort_by: 'updated_at',
        sort_order: 'desc',
      })
      setRisks(response.risks || [])
      setTotal(response.total || 0)
      setPage(nextPage)
      if (selectedRisk && !response.risks?.some((risk) => risk.id === selectedRisk.id)) {
        setSelectedRisk(null)
      }
    } catch (err: any) {
      setError(err?.message || '加载风险列表失败')
      setRisks([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReferences().catch((err) => setError(err?.message || '加载项目和人员失败'))
  }, [])

  useEffect(() => {
    loadRisks(1)
  }, [])

  useEffect(() => {
    if (!formOpen || editingRisk) return
    setForm((current) => ({
      ...current,
      project_id: current.project_id || String(projects[0]?.id || ''),
      owner_id: current.owner_id || String(users[0]?.id || ''),
    }))
  }, [formOpen, editingRisk, projects, users])

  const openCreate = () => {
    setEditingRisk(null)
    setForm({
      ...emptyForm,
      project_id: filters.project_id || String(projects[0]?.id || ''),
      owner_id: filters.owner_id || String(users[0]?.id || ''),
      target_resolution_date: tomorrowInput(),
    })
    setFormOpen(true)
    setModalError('')
    setError('')
  }

  const openEdit = (risk) => {
    setEditingRisk(risk)
    setForm({
      project_id: String(risk.project_id || ''),
      risk_name: risk.risk_name || '',
      description: risk.description || '',
      risk_category: risk.risk_category || RiskCategory.SCHEDULE,
      risk_level: risk.risk_level || RiskLevel.MEDIUM,
      probability: String(risk.probability ?? '0.5'),
      impact_score: String(risk.impact_score ?? '5'),
      mitigation_strategy: risk.mitigation_strategy || MitigationStrategy.MITIGATE,
      mitigation_plan: risk.mitigation_plan || '',
      contingency_plan: risk.contingency_plan || '',
      owner_id: risk.owner_id ? String(risk.owner_id) : '',
      target_resolution_date: risk.target_resolution_date || '',
    })
    setFormOpen(true)
    setModalError('')
    setError('')
  }

  const closeForm = () => {
    if (saving) return
    setEditingRisk(null)
    setFormOpen(false)
    setForm(emptyForm)
    setModalError('')
  }

  const buildPayload = () => ({
    project_id: Number(form.project_id),
    risk_name: form.risk_name.trim(),
    description: form.description.trim(),
    risk_category: form.risk_category,
    risk_level: form.risk_level,
    probability: Number(form.probability),
    impact_score: Number(form.impact_score),
    mitigation_strategy: form.mitigation_strategy,
    mitigation_plan: form.mitigation_plan.trim() || undefined,
    contingency_plan: form.contingency_plan.trim() || undefined,
    owner_id: Number(form.owner_id),
    target_resolution_date: form.target_resolution_date || undefined,
  })

  const validateForm = () => {
    if (!form.project_id) return '请选择所属项目'
    if (!form.owner_id) return '请选择风险负责人'
    if (!form.risk_name.trim()) return '请填写风险名称'
    if (!form.description.trim()) return '请填写风险描述'
    const probability = Number(form.probability)
    const impact = Number(form.impact_score)
    if (!Number.isFinite(probability) || probability < 0 || probability > 1) return '发生概率必须在 0 到 1 之间'
    if (!Number.isInteger(impact) || impact < 1 || impact > 10) return '影响评分必须是 1 到 10 的整数'
    if (form.target_resolution_date) {
      const today = new Date(new Date().toDateString())
      if (new Date(form.target_resolution_date) <= today && !editingRisk) return '目标解决日期必须晚于今天'
    }
    return ''
  }

  const submitForm = async () => {
    const validationMessage = validateForm()
    if (validationMessage) {
      setModalError(validationMessage)
      return
    }

    setSaving(true)
    setModalError('')
    setError('')
    setNotice('')
    try {
      const payload = buildPayload()
      if (editingRisk) {
        const { project_id, ...updatePayload } = payload
        await riskService.updateRisk(editingRisk.id, updatePayload)
        setNotice('风险已更新')
      } else {
        await riskService.createRisk(payload)
        setNotice('风险已创建，并已通知负责人')
      }
      closeForm()
      await loadRisks(editingRisk ? page : 1)
    } catch (err: any) {
      setModalError(err?.message || (editingRisk ? '更新风险失败' : '创建风险失败'))
    } finally {
      setSaving(false)
    }
  }

  const openStatus = (risk) => {
    const nextStatuses = statusTransitions[risk.status] || []
    setStatusRisk(risk)
    setStatusForm({
      status: nextStatuses[0] || risk.status,
      actual_resolution_date: risk.actual_resolution_date || new Date().toISOString().slice(0, 10),
    })
    setError('')
  }

  const submitStatus = async () => {
    if (!statusRisk || !statusForm.status) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await riskService.updateRisk(statusRisk.id, {
        status: statusForm.status,
        actual_resolution_date: statusForm.status === RiskStatus.CLOSED ? statusForm.actual_resolution_date : undefined,
      })
      setNotice(`风险状态已更新为${getRiskStatusText(statusForm.status)}`)
      setStatusRisk(null)
      await loadRisks(page)
    } catch (err: any) {
      setError(err?.message || '更新风险状态失败')
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteRisk) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await riskService.deleteRisk(deleteRisk.id)
      setNotice('风险已删除')
      setDeleteRisk(null)
      setSelectedRisk(null)
      await loadRisks(page)
    } catch (err: any) {
      setError(err?.message || '删除风险失败')
    } finally {
      setSaving(false)
    }
  }

  const resetFilters = () => {
    const nextFilters = { search: '', project_id: '', owner_id: '', risk_category: '', risk_level: '', status: '' }
    setFilters(nextFilters)
    loadRisks(1, nextFilters)
  }

  const loadAnalysis = async () => {
    if (!analysisProjectId) {
      setError('请选择要分析的项目')
      return
    }
    setLoading(true)
    setError('')
    try {
      const result = await riskService.getRiskAnalysis(Number(analysisProjectId))
      setAnalysis(result)
    } catch (err: any) {
      setError(err?.message || '加载风险分析失败')
      setAnalysis(null)
    } finally {
      setLoading(false)
    }
  }

  const runAutoDetection = async () => {
    if (!analysisProjectId) {
      setError('请选择要识别风险的项目')
      return
    }
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const result = await riskService.autoDetectRisks(Number(analysisProjectId))
      setDetection(result)
      setNotice(`自动识别完成，发现 ${result.detected_risks?.length || 0} 条风险线索`)
      await loadRisks(1)
      await loadAnalysis()
    } catch (err: any) {
      setError(err?.message || '自动识别风险失败')
      setDetection(null)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-foreground">
            <ShieldAlert className="h-6 w-6" />
            风险管理
          </h1>
          <p className="text-sm text-muted-foreground">统一维护项目风险、负责人、应对计划、状态流转和风险矩阵。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => loadRisks(page)} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            新建风险
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      {notice && <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{notice}</div>}
      {projects.length === 0 && !loading && <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">请先创建项目，再登记风险。</div>}

      <Card>
        <CardContent className="space-y-3 p-4">
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {statusCards.map((item) => (
              <div key={item.label} className="rounded-md border bg-muted/20 px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-muted-foreground">{item.label}</span>
                  <span className="text-lg font-semibold leading-5 text-foreground">{item.value}</span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{item.hint}</div>
              </div>
            ))}
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-6">
            <div className="relative xl:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filters.search}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
                onKeyDown={(event) => event.key === 'Enter' && loadRisks(1)}
                placeholder="搜索风险名称、描述或应对计划"
                className="pl-10"
              />
            </div>
            <SelectField value={filters.project_id} onChange={(value) => setFilters((current) => ({ ...current, project_id: value }))}>
              <option value="">全部项目</option>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.project_name || project.name}</option>)}
            </SelectField>
            <SelectField value={filters.owner_id} onChange={(value) => setFilters((current) => ({ ...current, owner_id: value }))}>
              <option value="">全部负责人</option>
              {users.map((user) => <option key={user.id} value={user.id}>{user.real_name || user.nickname || user.username}</option>)}
            </SelectField>
            <SelectField value={filters.risk_category} onChange={(value) => setFilters((current) => ({ ...current, risk_category: value }))}>
              <option value="">全部类别</option>
              {categoryOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </SelectField>
            <SelectField value={filters.risk_level} onChange={(value) => setFilters((current) => ({ ...current, risk_level: value }))}>
              <option value="">全部等级</option>
              {levelOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </SelectField>
            <SelectField value={filters.status} onChange={(value) => setFilters((current) => ({ ...current, status: value }))}>
              <option value="">全部状态</option>
              {statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </SelectField>
            <div className="flex gap-2">
              <Button className="flex-1" variant="outline" onClick={() => loadRisks(1)} disabled={loading}>
                <Search className="mr-2 h-4 w-4" />
                查询
              </Button>
              <Button variant="ghost" onClick={resetFilters} disabled={loading}>清空</Button>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="h-4 w-4" />
            支持按项目、负责人、类别、等级和状态筛选风险台账
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="list">
        <TabsList className="h-9">
          <TabsTrigger value="list">风险台账</TabsTrigger>
          <TabsTrigger value="matrix">风险矩阵</TabsTrigger>
          <TabsTrigger value="analysis">风险分析</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1080px] text-sm">
                  <thead className="border-b bg-muted/40 text-left text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2.5 font-medium">风险</th>
                      <th className="px-3 py-2.5 font-medium">项目</th>
                      <th className="px-3 py-2.5 font-medium">负责人</th>
                      <th className="px-3 py-2.5 font-medium">类别</th>
                      <th className="px-3 py-2.5 font-medium">等级</th>
                      <th className="px-3 py-2.5 font-medium">概率/影响</th>
                      <th className="px-3 py-2.5 font-medium">状态</th>
                      <th className="px-3 py-2.5 font-medium">目标解决</th>
                      <th className="px-3 py-2.5 text-right font-medium">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading && risks.length === 0 ? (
                      <tr><td colSpan={9} className="px-4 py-10 text-center text-muted-foreground">加载中...</td></tr>
                    ) : risks.length === 0 ? (
                      <tr><td colSpan={9} className="px-4 py-10 text-center text-muted-foreground">暂无风险数据</td></tr>
                    ) : risks.map((risk) => (
                      <tr key={risk.id} className="border-b last:border-0">
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-foreground">{risk.risk_name}</div>
                          <div className="mt-1 line-clamp-1 max-w-md text-xs text-muted-foreground">{risk.description || '-'}</div>
                        </td>
                        <td className="px-3 py-2.5">{projectNameById[risk.project_id] || `项目 #${risk.project_id}`}</td>
                        <td className="px-3 py-2.5">{userNameById[risk.owner_id] || `用户 #${risk.owner_id}`}</td>
                        <td className="px-3 py-2.5">{getRiskCategoryText(risk.risk_category)}</td>
                        <td className="px-3 py-2.5"><RiskLevelBadge level={risk.risk_level} /></td>
                        <td className="px-3 py-2.5">
                          <div>{Number(risk.probability).toFixed(2)} / {risk.impact_score}</div>
                          <div className="text-xs text-muted-foreground">评分 {scoreValue(risk).toFixed(2)}</div>
                        </td>
                        <td className="px-3 py-2.5"><RiskStatusBadge status={risk.status} /></td>
                        <td className="px-3 py-2.5">{formatDate(risk.target_resolution_date)}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="outline" onClick={() => setSelectedRisk(risk)}>
                              <Eye className="mr-1 h-3 w-3" />
                              查看
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => openEdit(risk)}>
                              <Edit className="mr-1 h-3 w-3" />
                              编辑
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => openStatus(risk)}>状态</Button>
                            <Button size="sm" variant="destructive" onClick={() => setDeleteRisk(risk)}>
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-col gap-3 border-t px-4 py-3 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-muted-foreground">第 {page} / {totalPages} 页，共 {total} 条</div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1 || loading} onClick={() => loadRisks(page - 1)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    上一页
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages || loading} onClick={() => loadRisks(page + 1)}>
                    下一页
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="matrix">
          <RiskMatrix risks={risks} onRiskClick={setSelectedRisk} />
        </TabsContent>

        <TabsContent value="analysis">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <BarChart3 className="h-5 w-5" />
                项目风险分析
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <SelectField value={analysisProjectId} onChange={setAnalysisProjectId}>
                  <option value="">请选择项目</option>
                  {projects.map((project) => <option key={project.id} value={project.id}>{project.project_name || project.name}</option>)}
                </SelectField>
                <Button variant="outline" onClick={loadAnalysis} disabled={loading || !analysisProjectId}>
                  <BarChart3 className="mr-2 h-4 w-4" />
                  生成分析
                </Button>
                <Button onClick={runAutoDetection} disabled={saving || !analysisProjectId}>
                  <Zap className="mr-2 h-4 w-4" />
                  自动识别风险
                </Button>
              </div>

              {analysis ? (
                <div className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <Info label="风险总数" value={analysis.metrics?.total_risks ?? 0} />
                    <Info label="未关闭风险" value={analysis.metrics?.open_risks ?? 0} />
                    <Info label="严重/高风险" value={`${analysis.metrics?.critical_risks ?? 0} / ${analysis.metrics?.high_risks ?? 0}`} />
                    <Info label="平均评分" value={Number(analysis.metrics?.average_risk_score || 0).toFixed(2)} />
                  </div>
                  <div className="grid gap-5 lg:grid-cols-2">
                    <section>
                      <h3 className="mb-2 text-sm font-semibold text-foreground">类别分布</h3>
                      <div className="space-y-2">
                        {(analysis.category_analysis || []).map((item) => (
                          <div key={item.category} className="rounded-md border p-3 text-sm">
                            <div className="flex justify-between">
                              <span>{getRiskCategoryText(item.category)}</span>
                              <span>{item.count} 条，{Number(item.percentage || 0).toFixed(1)}%</span>
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">平均评分 {Number(item.average_score || 0).toFixed(2)}</div>
                          </div>
                        ))}
                        {analysis.category_analysis?.length === 0 && <div className="rounded-md border p-4 text-sm text-muted-foreground">暂无类别数据</div>}
                      </div>
                    </section>
                    <section>
                      <h3 className="mb-2 text-sm font-semibold text-foreground">处理建议</h3>
                      <div className="space-y-2">
                        {(analysis.recommendations || []).map((item, index) => (
                          <div key={index} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{item}</div>
                        ))}
                        {analysis.recommendations?.length === 0 && <div className="rounded-md border p-4 text-sm text-muted-foreground">暂无系统建议</div>}
                      </div>
                    </section>
                  </div>
                </div>
              ) : (
                <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">选择项目后生成分析，可查看风险分布、重点风险和处理建议。</div>
              )}

              {detection && (
                <div className="rounded-md border bg-muted/30 p-4">
                  <div className="font-medium text-foreground">自动识别结果</div>
                  <div className="mt-2 text-sm text-muted-foreground">发现 {detection.detected_risks?.length || 0} 条风险线索，建议 {detection.recommendations?.length || 0} 条。</div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {formOpen && (
        <RiskFormDialog
          title={editingRisk ? '编辑风险' : '新建风险'}
          form={form}
          setForm={setForm}
          projects={projects}
          users={users}
          modalError={modalError}
          onClose={closeForm}
          onSubmit={submitForm}
          saving={saving}
          editing={Boolean(editingRisk)}
        />
      )}

      {selectedRisk && (
        <RiskDetailDialog
          risk={selectedRisk}
          projectName={projectNameById[selectedRisk.project_id] || `项目 #${selectedRisk.project_id}`}
          ownerName={userNameById[selectedRisk.owner_id] || `用户 #${selectedRisk.owner_id}`}
          onClose={() => setSelectedRisk(null)}
          onEdit={() => {
            openEdit(selectedRisk)
            setSelectedRisk(null)
          }}
          onStatus={() => {
            openStatus(selectedRisk)
            setSelectedRisk(null)
          }}
        />
      )}

      {statusRisk && (
        <StatusDialog
          risk={statusRisk}
          form={statusForm}
          setForm={setStatusForm}
          onClose={() => setStatusRisk(null)}
          onSubmit={submitStatus}
          saving={saving}
        />
      )}

      {deleteRisk && (
        <ConfirmDialog
          title="删除风险"
          message={`确定删除风险“${deleteRisk.risk_name}”吗？删除后不可恢复。`}
          onClose={() => setDeleteRisk(null)}
          onConfirm={confirmDelete}
          saving={saving}
        />
      )}
    </div>
  )
}

function RiskFormDialog({ title, form, setForm, projects, users, modalError, onClose, onSubmit, saving, editing }) {
  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }))
  const computedScore = (Number(form.probability || 0) * Number(form.impact_score || 0)).toFixed(2)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <p className="mt-1 text-sm text-gray-500">填写风险来源、概率影响、负责人、应对计划和目标解决日期。</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          <div className="mb-4 space-y-2">
            {modalError && (
              <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <span>{modalError}</span>
              </div>
            )}
            {projects.length === 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                当前没有可选择的项目，请先创建或加入项目后再登记风险。
              </div>
            )}
            {users.length === 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                当前没有可选择的负责人，请先启用用户后再登记风险。
              </div>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="所属项目" required>
              <SelectField value={form.project_id} onChange={(value) => update('project_id', value)} disabled={editing}>
                <option value="">请选择项目</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.project_name || project.name}</option>)}
              </SelectField>
            </Field>
            <Field label="风险负责人" required>
              <SelectField value={form.owner_id} onChange={(value) => update('owner_id', value)}>
                <option value="">请选择负责人</option>
                {users.map((user) => <option key={user.id} value={user.id}>{user.real_name || user.nickname || user.username}</option>)}
              </SelectField>
            </Field>
            <Field label="风险名称" required className="md:col-span-2">
              <Input value={form.risk_name} onChange={(event) => update('risk_name', event.target.value)} placeholder="例如：核心接口联调延期影响验收" autoFocus />
            </Field>
            <Field label="风险类别">
              <SelectField value={form.risk_category} onChange={(value) => update('risk_category', value)}>
                {categoryOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </SelectField>
            </Field>
            <Field label="风险等级">
              <SelectField value={form.risk_level} onChange={(value) => update('risk_level', value)}>
                {levelOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </SelectField>
            </Field>
            <Field label="发生概率（0-1）">
              <Input type="number" min="0" max="1" step="0.01" value={form.probability} onChange={(event) => update('probability', event.target.value)} />
            </Field>
            <Field label="影响评分（1-10）">
              <Input type="number" min="1" max="10" step="1" value={form.impact_score} onChange={(event) => update('impact_score', event.target.value)} />
            </Field>
            <Field label="应对策略">
              <SelectField value={form.mitigation_strategy} onChange={(value) => update('mitigation_strategy', value)}>
                {strategyOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </SelectField>
            </Field>
            <Field label="目标解决日期">
              <Input type="date" value={form.target_resolution_date} onChange={(event) => update('target_resolution_date', event.target.value)} />
            </Field>
            <div className="rounded-md border bg-gray-50 p-3 text-sm md:col-span-2">
              <span className="text-gray-500">当前评分：</span>
              <span className="font-semibold text-gray-900">{computedScore}</span>
              <span className="ml-2 text-gray-500">评分由发生概率 × 影响评分得出。</span>
            </div>
            <Field label="风险描述" required className="md:col-span-2">
              <Textarea rows={4} value={form.description} onChange={(event) => update('description', event.target.value)} placeholder="说明风险背景、触发条件、影响范围和当前迹象" />
            </Field>
            <Field label="应对计划" className="md:col-span-2">
              <Textarea rows={4} value={form.mitigation_plan} onChange={(event) => update('mitigation_plan', event.target.value)} placeholder="列出降低概率或降低影响的具体动作、责任人和时间点" />
            </Field>
            <Field label="应急预案" className="md:col-span-2">
              <Textarea rows={3} value={form.contingency_plan} onChange={(event) => update('contingency_plan', event.target.value)} placeholder="风险发生后采用的兜底措施或替代方案" />
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

function RiskDetailDialog({ risk, projectName, ownerName, onClose, onEdit, onStatus }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between border-b px-6 py-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">{risk.risk_name}</h2>
              <RiskLevelBadge level={risk.risk_level} />
              <RiskStatusBadge status={risk.status} />
            </div>
            <p className="mt-1 text-sm text-gray-500">风险 #{risk.id} · 识别日期 {formatDate(risk.identified_date)}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-6">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard icon={<ShieldAlert className="h-4 w-4" />} label="所属项目" value={projectName} />
            <InfoCard icon={<UserCheck className="h-4 w-4" />} label="负责人" value={ownerName} />
            <InfoCard icon={<CalendarDays className="h-4 w-4" />} label="目标解决" value={formatDate(risk.target_resolution_date)} />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section>
              <h3 className="mb-2 text-sm font-semibold text-gray-900">风险描述</h3>
              <div className="min-h-[120px] whitespace-pre-wrap rounded-md border bg-gray-50 p-4 text-sm text-gray-700">{risk.description || '暂无描述'}</div>
            </section>
            <section>
              <h3 className="mb-2 text-sm font-semibold text-gray-900">应对计划</h3>
              <div className="min-h-[120px] whitespace-pre-wrap rounded-md border bg-gray-50 p-4 text-sm text-gray-700">{risk.mitigation_plan || '暂无应对计划'}</div>
            </section>
          </div>
          <div className="mt-6 grid gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
            <Info label="风险类别" value={getRiskCategoryText(risk.risk_category)} />
            <Info label="应对策略" value={getMitigationStrategyText(risk.mitigation_strategy)} />
            <Info label="发生概率" value={Number(risk.probability).toFixed(2)} />
            <Info label="影响评分" value={risk.impact_score} />
            <Info label="风险评分" value={scoreValue(risk).toFixed(2)} />
            <Info label="实际解决" value={formatDate(risk.actual_resolution_date)} />
            <Info label="创建时间" value={formatDateTime(risk.created_at)} />
            <Info label="更新时间" value={formatDateTime(risk.updated_at)} />
          </div>
          <section className="mt-6">
            <h3 className="mb-2 text-sm font-semibold text-gray-900">应急预案</h3>
            <div className="min-h-[80px] whitespace-pre-wrap rounded-md border bg-gray-50 p-4 text-sm text-gray-700">{risk.contingency_plan || '暂无应急预案'}</div>
          </section>
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

function StatusDialog({ risk, form, setForm, onClose, onSubmit, saving }) {
  const nextStatuses = statusTransitions[risk.status] || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">变更风险状态</h2>
            <p className="mt-1 text-sm text-gray-500">{risk.risk_name} · 当前：{getRiskStatusText(risk.status)}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="space-y-4 px-6 py-5">
          {nextStatuses.length === 0 ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">当前状态没有可执行的下一步。</div>
          ) : (
            <>
              <Field label="目标状态" required>
                <SelectField value={form.status} onChange={(value) => setForm((current) => ({ ...current, status: value }))}>
                  {nextStatuses.map((status) => <option key={status} value={status}>{getRiskStatusText(status)}</option>)}
                </SelectField>
              </Field>
              {form.status === RiskStatus.CLOSED && (
                <Field label="实际解决日期" required>
                  <Input type="date" value={form.actual_resolution_date} onChange={(event) => setForm((current) => ({ ...current, actual_resolution_date: event.target.value }))} />
                </Field>
              )}
            </>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={onSubmit} disabled={saving || nextStatuses.length === 0}>{saving ? '提交中...' : '确认变更'}</Button>
        </div>
      </div>
    </div>
  )
}

function ConfirmDialog({ title, message, onClose, onConfirm, saving }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="border-b px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        <div className="px-6 py-5 text-sm text-gray-700">{message}</div>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button variant="destructive" onClick={onConfirm} disabled={saving}>{saving ? '删除中...' : '确认删除'}</Button>
        </div>
      </div>
    </div>
  )
}

function SelectField({ value, onChange, children, disabled = false }) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </select>
  )
}

function Field({ label, required, className = '', children }) {
  return (
    <label className={`space-y-2 text-sm ${className}`}>
      <span className="font-medium text-gray-700">
        {label}
        {required && <span className="ml-1 text-red-500">*</span>}
      </span>
      {children}
    </label>
  )
}

function Info({ label, value }) {
  return (
    <div className="rounded-md border bg-white p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  )
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="flex gap-3 rounded-md border bg-gray-50 p-4">
      <div className="mt-0.5 text-red-600">{icon}</div>
      <div>
        <div className="text-xs text-gray-500">{label}</div>
        <div className="mt-1 text-sm font-medium text-gray-900">{value}</div>
      </div>
    </div>
  )
}

function RiskLevelBadge({ level }) {
  const className = {
    [RiskLevel.LOW]: 'bg-green-100 text-green-800',
    [RiskLevel.MEDIUM]: 'bg-yellow-100 text-yellow-800',
    [RiskLevel.HIGH]: 'bg-orange-100 text-orange-800',
    [RiskLevel.CRITICAL]: 'bg-red-100 text-red-800',
  }[level] || 'bg-gray-100 text-gray-700'
  return <Badge variant="secondary" className={`border-0 ${className}`}>{getRiskLevelText(level)}</Badge>
}

function RiskStatusBadge({ status }) {
  const className = {
    [RiskStatus.IDENTIFIED]: 'bg-gray-100 text-gray-700',
    [RiskStatus.ANALYZING]: 'bg-blue-100 text-blue-800',
    [RiskStatus.MITIGATING]: 'bg-orange-100 text-orange-800',
    [RiskStatus.MONITORING]: 'bg-indigo-100 text-indigo-800',
    [RiskStatus.CLOSED]: 'bg-green-100 text-green-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return <Badge variant="secondary" className={`border-0 ${className}`}>{getRiskStatusText(status)}</Badge>
}

export default RiskManagement
