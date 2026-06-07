// @ts-nocheck
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { AlertCircle, AlertTriangle, CheckCircle, CheckSquare, Clock, Filter, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Textarea } from '@/components/ui/Textarea'
import ProjectService from '@/services/projectService'
import TaskService, { CreateTaskRequest } from '@/services/taskService'
import userService from '@/services/user-service'
import type { User } from '@/types'
import type { Project, Task } from '@/types/project'
import {
  getTaskPriorityLabel,
  getTaskStatusLabel,
  getTaskTypeLabel,
  taskPriorityOptions,
  taskStatusOptions,
  taskTypeOptions,
} from '@/utils/taskLabels'

const statusConfig = {
  TODO: { icon: Clock, variant: 'secondary' },
  ASSIGNED: { icon: CheckSquare, variant: 'secondary' },
  IN_PROGRESS: { icon: CheckSquare, variant: 'default' },
  ON_HOLD: { icon: Clock, variant: 'secondary' },
  BLOCKED: { icon: AlertTriangle, variant: 'destructive' },
  PENDING_REVIEW: { icon: Clock, variant: 'secondary' },
  COMPLETED: { icon: CheckCircle, variant: 'success' },
  CANCELLED: { icon: AlertTriangle, variant: 'secondary' },
}

const initialForm: CreateTaskRequest & { status: Task['status'] } = {
  project_id: 0,
  task_name: '',
  description: '',
  task_type: 'TEST_EXECUTION',
  priority: 'MEDIUM',
  status: 'TODO',
  assignee_ids: [],
  planned_start_date: '',
  planned_end_date: '',
}

function TaskManagement() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalError, setModalError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState<Task['status'] | 'all'>('all')
  const [createOpen, setCreateOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [assigningTask, setAssigningTask] = useState<Task | null>(null)
  const [assigningIds, setAssigningIds] = useState<number[]>([])
  const [form, setForm] = useState(initialForm)

  const projectNameById = useMemo(() => {
    return projects.reduce<Record<number, string>>((result, project) => {
      result[project.id] = project.project_name
      return result
    }, {})
  }, [projects])

  const userNameById = useMemo(() => {
    return users.reduce<Record<number, string>>((result, user) => {
      result[user.id] = user.real_name || user.nickname || user.username
      return result
    }, {})
  }, [users])

  const getAssigneeIds = (task: Task) => {
    if (Array.isArray(task.assignee_ids) && task.assignee_ids.length > 0) return task.assignee_ids
    return task.assignee_id ? [task.assignee_id] : []
  }

  const getAssigneeText = (task: Task) => {
    const assigneeIds = getAssigneeIds(task)
    if (assigneeIds.length === 0) return '未分配'
    return assigneeIds.map((id) => userNameById[id] || `#${id}`).join('、')
  }

  const loadProjects = async () => {
    setProjectsLoading(true)
    try {
      const response = await ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' })
      const nextProjects = response.data || []
      setProjects(nextProjects)
      setForm((current) => ({
        ...current,
        project_id: current.project_id || nextProjects[0]?.id || 0,
      }))
    } catch (err: any) {
      setError(err?.message || '加载项目列表失败')
    } finally {
      setProjectsLoading(false)
    }
  }

  const loadUsers = async () => {
    try {
      const response = await userService.getUsers({ page: 1, size: 100, status: 'active', sort_by: 'username', sort_order: 'asc' })
      setUsers(response.users || [])
    } catch (err: any) {
      setError(err?.message || '加载用户列表失败')
    }
  }

  const loadTasks = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await TaskService.getTasks({
        page: 1,
        size: 100,
        search: searchQuery || undefined,
        status: selectedFilter === 'all' ? undefined : [selectedFilter],
        sort_by: 'updated_at',
        sort_order: 'desc',
      })
      setTasks(response.data || [])
    } catch (err: any) {
      setError(err?.message || '加载任务失败')
      setTasks([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
    loadUsers()
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadTasks()
    }, 250)

    return () => window.clearTimeout(timer)
  }, [searchQuery, selectedFilter])

  const filteredTasks = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return tasks.filter((task) => {
      const matchesSearch =
        !query ||
        String(task.task_name || '').toLowerCase().includes(query) ||
        String(task.description || '').toLowerCase().includes(query) ||
        String(task.task_code || '').toLowerCase().includes(query)
      const matchesFilter = selectedFilter === 'all' || task.status === selectedFilter
      return matchesSearch && matchesFilter
    })
  }, [searchQuery, selectedFilter, tasks])

  const openCreateModal = () => {
    setModalError('')
    setForm({
      ...initialForm,
      project_id: projects[0]?.id || 0,
    })
    setCreateOpen(true)
  }

  const closeCreateModal = () => {
    if (saving) return
    setCreateOpen(false)
    setModalError('')
  }

  const updateForm = <K extends keyof typeof form>(field: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
    setModalError('')
  }

  const createTask = async (event: FormEvent) => {
    event.preventDefault()
    const taskName = form.task_name.trim()
    if (!form.project_id) {
      setModalError('请选择所属项目')
      return
    }
    if (!taskName) {
      setModalError('请输入任务名称')
      return
    }
    if (form.planned_start_date && form.planned_end_date && new Date(form.planned_start_date) >= new Date(form.planned_end_date)) {
      setModalError('计划结束日期必须晚于开始日期')
      return
    }

    setSaving(true)
    setModalError('')
    try {
      await TaskService.createTask({
        ...form,
        task_name: taskName,
        description: form.description?.trim() || undefined,
        assignee_id: form.assignee_ids?.[0],
        assignee_ids: form.assignee_ids?.length ? form.assignee_ids : undefined,
        planned_start_date: form.planned_start_date || undefined,
        planned_end_date: form.planned_end_date || undefined,
      })
      setCreateOpen(false)
      await loadTasks()
    } catch (err: any) {
      setModalError(err?.message || '创建任务失败')
    } finally {
      setSaving(false)
    }
  }

  const updateStatus = async (task: Task, nextStatus: Task['status']) => {
    if (nextStatus === task.status) return
    setError('')
    try {
      await TaskService.updateTaskStatus(task.id, { status: nextStatus })
      await loadTasks()
    } catch (err: any) {
      setError(err?.message || '更新任务状态失败')
    }
  }

  const toggleCreateAssignee = (userId: number) => {
    setForm((current) => {
      const selected = current.assignee_ids || []
      const nextSelected = selected.includes(userId)
        ? selected.filter((id) => id !== userId)
        : [...selected, userId]
      return { ...current, assignee_ids: nextSelected }
    })
  }

  const openAssignModal = (task: Task) => {
    setAssigningTask(task)
    setAssigningIds(getAssigneeIds(task))
    setModalError('')
    setAssignOpen(true)
  }

  const closeAssignModal = () => {
    if (saving) return
    setAssignOpen(false)
    setAssigningTask(null)
    setAssigningIds([])
    setModalError('')
  }

  const toggleAssigningUser = (userId: number) => {
    setAssigningIds((current) => (
      current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId]
    ))
  }

  const submitAssignment = async (event: FormEvent) => {
    event.preventDefault()
    if (!assigningTask) return
    if (assigningIds.length === 0) {
      setModalError('请至少选择一个执行人')
      return
    }

    setSaving(true)
    setModalError('')
    try {
      await TaskService.assignTask(assigningTask.id, {
        assignee_id: assigningIds[0],
        assignee_ids: assigningIds,
      })
      setAssignOpen(false)
      setAssigningTask(null)
      setAssigningIds([])
      await loadTasks()
    } catch (err: any) {
      setModalError(err?.message || '分配任务失败')
    } finally {
      setSaving(false)
    }
  }

  const deleteTask = async (task: Task) => {
    if (!window.confirm(`确定要删除任务“${task.task_name}”吗？`)) return
    try {
      await TaskService.deleteTask(task.id)
      await loadTasks()
    } catch (err: any) {
      setError(err?.message || '删除任务失败')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">任务管理</h1>
          <p className="mt-1 text-muted-foreground">跟踪项目中的开发、测试和修复任务。</p>
        </div>
        <Button onClick={openCreateModal} disabled={projectsLoading || projects.length === 0}>
          <Plus className="mr-2 h-4 w-4" />
          新建任务
        </Button>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索任务名称、描述或编号"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            className="pl-10"
          />
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              {selectedFilter === 'all' ? '全部状态' : getTaskStatusLabel(selectedFilter)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="z-[100] bg-white text-gray-900">
            <DropdownMenuItem onClick={() => setSelectedFilter('all')}>全部状态</DropdownMenuItem>
            {taskStatusOptions.map((status) => (
              <DropdownMenuItem key={status.value} onClick={() => setSelectedFilter(status.value)}>
                {status.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="outline" onClick={loadTasks} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
      {!projectsLoading && projects.length === 0 && (
        <div className="rounded-md bg-yellow-50 px-4 py-3 text-sm text-yellow-800">请先创建项目，再新建任务。</div>
      )}

      <div className="space-y-4">
        {loading && filteredTasks.length === 0 && (
          <Card><CardContent className="p-8 text-center text-muted-foreground">加载中...</CardContent></Card>
        )}
        {!loading && filteredTasks.length === 0 && (
          <Card><CardContent className="p-8 text-center text-muted-foreground">暂无任务数据</CardContent></Card>
        )}
        {filteredTasks.map((task) => {
          const config = statusConfig[task.status] || statusConfig.TODO
          const Icon = config.icon
          const progress = task.status === 'COMPLETED' ? 100 : task.status === 'IN_PROGRESS' ? 50 : 0
          return (
            <Card key={task.id}>
              <CardContent className="p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="font-semibold text-foreground">{task.task_name}</h3>
                      <Badge variant={config.variant}>
                        <Icon className="mr-1 inline h-3 w-3" />
                        {getTaskStatusLabel(task.status)}
                      </Badge>
                      <Badge variant={task.priority === 'HIGH' || task.priority === 'URGENT' ? 'destructive' : 'secondary'}>
                        优先级：{getTaskPriorityLabel(task.priority)}
                      </Badge>
                      <Badge variant="outline">{getTaskTypeLabel(task.task_type)}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{task.description || '暂无描述'}</p>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>编号：{task.task_code || `#${task.id}`}</span>
                      <span>项目：{projectNameById[task.project_id] || `#${task.project_id}`}</span>
                      <span>执行人：{getAssigneeText(task)}</span>
                      <span>截止：{task.planned_end_date || '-'}</span>
                    </div>
                  </div>
                  <div className="min-w-36">
                    <div className="mb-1 flex justify-between text-sm">
                      <span>进度</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-200">
                      <div className="h-2 rounded-full bg-blue-600" style={{ width: `${progress}%` }} />
                    </div>
                    <div className="mt-3 flex justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => openAssignModal(task)}>分配</Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button size="sm" variant="outline">改状态</Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="z-[100] bg-white text-gray-900">
                          {taskStatusOptions.map((status) => (
                            <DropdownMenuItem
                              key={status.value}
                              disabled={status.value === task.status}
                              onClick={() => updateStatus(task, status.value)}
                            >
                              {status.label}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <Button size="sm" variant="destructive" onClick={() => deleteTask(task)} aria-label={`删除${task.task_name}`}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Dialog open={assignOpen} onOpenChange={(nextOpen) => !nextOpen && closeAssignModal()}>
        <DialogContent className="max-h-[80vh] max-w-xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>分配任务</DialogTitle>
            <p className="mt-1 text-sm text-gray-600">{assigningTask?.task_name || ''}</p>
          </DialogHeader>

          <form onSubmit={submitAssignment} className="space-y-4">
            {modalError && (
              <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <span>{modalError}</span>
              </div>
            )}

            <div>
              <Label>执行人 *</Label>
              <div className="mt-2 grid max-h-56 grid-cols-1 gap-2 overflow-y-auto rounded-md border p-3 md:grid-cols-2">
                {users.length === 0 ? (
                  <div className="text-sm text-gray-500">暂无可分配用户</div>
                ) : users.map((user) => (
                  <label key={user.id} className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={assigningIds.includes(user.id)}
                      onChange={() => toggleAssigningUser(user.id)}
                    />
                    <span>{user.real_name || user.nickname || user.username}</span>
                  </label>
                ))}
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeAssignModal} disabled={saving}>取消</Button>
              <Button type="submit" disabled={saving || users.length === 0}>{saving ? '保存中...' : '保存分配'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={createOpen} onOpenChange={(nextOpen) => !nextOpen && closeCreateModal()}>
        <DialogContent className="max-h-[92vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新建任务</DialogTitle>
            <p className="mt-1 text-sm text-gray-600">填写任务名称、所属项目和初始状态后即可创建。</p>
          </DialogHeader>

          <form onSubmit={createTask} className="space-y-5">
            {modalError && (
              <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <span>{modalError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <Label htmlFor="task_project_id">所属项目 *</Label>
                <select
                  id="task_project_id"
                  value={form.project_id || ''}
                  onChange={(event) => updateForm('project_id', Number(event.target.value))}
                  className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  required
                >
                  <option value="" disabled>请选择项目</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.project_name}</option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="task_name">任务名称 *</Label>
                <Input
                  id="task_name"
                  value={form.task_name}
                  onChange={(event) => updateForm('task_name', event.target.value)}
                  placeholder="例如：补充登录流程回归测试"
                  autoFocus
                  required
                />
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="task_description">任务描述</Label>
                <Textarea
                  id="task_description"
                  value={form.description || ''}
                  onChange={(event) => updateForm('description', event.target.value)}
                  placeholder="说明任务背景、验收要求或注意事项"
                  rows={3}
                />
              </div>

              <div className="md:col-span-2">
                <Label>执行人</Label>
                <div className="mt-2 grid max-h-40 grid-cols-1 gap-2 overflow-y-auto rounded-md border p-3 md:grid-cols-2">
                  {users.length === 0 ? (
                    <div className="text-sm text-gray-500">暂无可分配用户</div>
                  ) : users.map((user) => (
                    <label key={user.id} className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={(form.assignee_ids || []).includes(user.id)}
                        onChange={() => toggleCreateAssignee(user.id)}
                      />
                      <span>{user.real_name || user.nickname || user.username}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="task_type">任务类型</Label>
                <select
                  id="task_type"
                  value={form.task_type}
                  onChange={(event) => updateForm('task_type', event.target.value as Task['task_type'])}
                  className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {taskTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="task_priority">优先级</Label>
                <select
                  id="task_priority"
                  value={form.priority}
                  onChange={(event) => updateForm('priority', event.target.value as Task['priority'])}
                  className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {taskPriorityOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="task_status">初始状态</Label>
                <select
                  id="task_status"
                  value={form.status}
                  onChange={(event) => updateForm('status', event.target.value as Task['status'])}
                  className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {taskStatusOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="planned_start_date">开始日期</Label>
                <Input
                  id="planned_start_date"
                  type="date"
                  value={form.planned_start_date || ''}
                  onChange={(event) => updateForm('planned_start_date', event.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="planned_end_date">截止日期</Label>
                <Input
                  id="planned_end_date"
                  type="date"
                  value={form.planned_end_date || ''}
                  onChange={(event) => updateForm('planned_end_date', event.target.value)}
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeCreateModal} disabled={saving}>取消</Button>
              <Button type="submit" disabled={saving || projects.length === 0}>{saving ? '创建中...' : '创建任务'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default TaskManagement
