// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Calendar, Download, Eye, Pencil, Plus, Search, User, UserCheck } from 'lucide-react'
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
import {
  useDefects,
  useDefectManagement,
  useCreateDefect,
  useUpdateDefect,
  useUpdateDefectStatus,
  useAssignDefect,
  useExportDefects,
} from '../../../hooks/testmanager/useDefect'
import userService from '../../../services/user-service'
import { DefectStatus, DefectSeverity, DefectType, Priority } from '../../../types/testmanager'
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
}

const labelOf = (options, value) => options.find((item) => item.value === value)?.label || value || '-'
const userName = (user) => user?.real_name || user?.nickname || user?.username || `用户 #${user?.id}`

const DefectList: React.FC = () => {
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
  const exportDefects = useExportDefects()

  const [users, setUsers] = useState([])
  const [referenceError, setReferenceError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editingDefect, setEditingDefect] = useState(null)
  const [detailDefect, setDetailDefect] = useState(null)
  const [assignDefectRow, setAssignDefectRow] = useState(null)
  const [assignUserId, setAssignUserId] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')

  const defects = defectsData?.data || []
  const totalCount = defectsData?.total || 0

  const userNameById = useMemo(() => {
    return users.reduce((result, user) => {
      result[Number(user.id)] = userName(user)
      return result
    }, {})
  }, [users])

  useEffect(() => {
    let cancelled = false
    userService
      .getUsers({ page: 1, size: 100, status: 'active', sort_by: 'username', sort_order: 'asc' })
      .then((response) => {
        if (!cancelled) setUsers(response.users || [])
      })
      .catch((err) => {
        if (!cancelled) setReferenceError(err?.message || '加载人员列表失败')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const openCreateForm = () => {
    setEditingDefect(null)
    setForm(emptyForm)
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
    })
    setFormError('')
    setFormOpen(true)
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

  const handleStatusChange = (id: number, status: DefectStatus) => {
    updateDefectStatus.mutate({ id, status })
  }

  const handleExport = (format: string) => {
    exportDefects.mutate({ filters, format })
  }

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
    return <div className="text-red-500 text-center">加载失败: {error.message}</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">缺陷管理</h1>
          <p className="text-gray-600">跟踪缺陷提交、分配、处理和关闭的完整流程</p>
        </div>
        <Button onClick={openCreateForm}>
          <Plus className="w-4 h-4 mr-2" />
          创建缺陷
        </Button>
      </div>

      {referenceError && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {referenceError}
        </div>
      )}

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 lg:flex-row">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="搜索缺陷标题、描述或编号"
                  value={searchTerm}
                  onChange={(event) => handleSearch(event.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleUpdateFilters({ status: value === 'all' ? undefined : value as DefectStatus })}
              >
                <SelectTrigger className="w-full sm:w-36">
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
                <SelectTrigger className="w-full sm:w-36">
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
                <SelectTrigger className="w-full sm:w-36">
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
        </CardContent>
      </Card>

      {selectedDefects.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <span className="text-sm text-gray-600">已选择 {selectedDefects.length} 个缺陷</span>
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
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" />
                  导出
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleExport('csv')}>导出为 CSV</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <div className="text-sm text-gray-600">共 {totalCount} 个缺陷</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>缺陷列表</CardTitle>
        </CardHeader>
        <CardContent>
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
                  <TableHead>缺陷标题</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>严重程度</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>报告人</TableHead>
                  <TableHead>负责人</TableHead>
                  <TableHead>报告时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
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
                        className="text-left font-medium text-blue-600 hover:text-blue-800"
                      >
                        {defect.title}
                      </button>
                      <div className="text-sm text-gray-500">{defect.defect_code}</div>
                      {defect.found_in_version && (
                        <div className="text-xs text-gray-400">发现版本：{defect.found_in_version}</div>
                      )}
                    </TableCell>
                    <TableCell><Badge variant="outline">{labelOf(defectTypeOptions, defect.defect_type)}</Badge></TableCell>
                    <TableCell>{getSeverityBadge(defect.severity)}</TableCell>
                    <TableCell><Badge variant="secondary">{labelOf(priorityOptions, defect.priority)}</Badge></TableCell>
                    <TableCell>{getStatusBadge(defect.status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span>{userNameById[Number(defect.reporter_id)] || `用户 #${defect.reporter_id}`}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span>{defect.assignee_id ? (userNameById[Number(defect.assignee_id)] || `用户 #${defect.assignee_id}`) : '未分配'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span>{formatDate(defect.reported_at)}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">操作</Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setDetailDefect(defect)}>
                            <Eye className="w-4 h-4 mr-2" />
                            查看详情
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => openEditForm(defect)}>
                            <Pencil className="w-4 h-4 mr-2" />
                            编辑
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => openAssignDialog(defect)}>
                            <UserCheck className="w-4 h-4 mr-2" />
                            分配负责人
                          </DropdownMenuItem>
                          {(statusTransitions[defect.status] || []).map((status) => (
                            <DropdownMenuItem key={status} onClick={() => handleStatusChange(defect.id, status)}>
                              设为{labelOf(statusOptions, status)}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {defects.length === 0 && (
            <div className="text-center py-8 text-gray-500">暂无缺陷数据</div>
          )}
        </CardContent>
      </Card>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-3xl">
          <form onSubmit={submitForm} className="space-y-4">
            <DialogHeader>
              <DialogTitle>{editingDefect ? '编辑缺陷' : '创建缺陷'}</DialogTitle>
            </DialogHeader>

            {formError && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</div>}

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
        <DialogContent className="max-w-2xl">
          {detailDefect && (
            <div className="space-y-4">
              <DialogHeader>
                <DialogTitle>{detailDefect.title}</DialogTitle>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-500">编号：</span>{detailDefect.defect_code}</div>
                <div><span className="text-gray-500">状态：</span>{labelOf(statusOptions, detailDefect.status)}</div>
                <div><span className="text-gray-500">类型：</span>{labelOf(defectTypeOptions, detailDefect.defect_type)}</div>
                <div><span className="text-gray-500">严重程度：</span>{labelOf(severityOptions, detailDefect.severity)}</div>
                <div><span className="text-gray-500">优先级：</span>{labelOf(priorityOptions, detailDefect.priority)}</div>
                <div><span className="text-gray-500">负责人：</span>{detailDefect.assignee_id ? (userNameById[Number(detailDefect.assignee_id)] || `用户 #${detailDefect.assignee_id}`) : '未分配'}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium">缺陷描述</div>
                <div className="rounded-md bg-gray-50 p-3 text-sm whitespace-pre-wrap">{detailDefect.description || '-'}</div>
              </div>
              <div>
                <div className="mb-1 text-sm font-medium">复现步骤</div>
                <div className="rounded-md bg-gray-50 p-3 text-sm whitespace-pre-wrap">{detailDefect.steps_to_reproduce || '-'}</div>
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
            <div className="text-sm text-gray-600">{assignDefectRow?.title}</div>
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
    </div>
  )
}

export default DefectList
