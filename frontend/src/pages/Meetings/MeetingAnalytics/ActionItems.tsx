import React, { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import AnalyticsLayout from './AnalyticsLayout'
import {
  analyticsService,
  apiErrorMessage,
  isNotFoundError,
  type ActionItem,
  type ActionItemCreateInput,
  type ActionItemUpdateInput,
} from '@/services/meeting/analyticsService'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import EmptyState from '@/components/ui/EmptyState'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/Table'
import { AlertCircle, Loader2, Pencil, Plus, RefreshCw, Trash2, X } from 'lucide-react'

const PRIORITY_LABEL: Record<string, string> = { low: '低', medium: '中', high: '高', urgent: '紧急' }
const STATUS_LABEL: Record<string, string> = {
  pending: '待办',
  in_progress: '进行中',
  completed: '已完成',
}
const PRIORITIES = ['low', 'medium', 'high', 'urgent']
const STATUSES = ['pending', 'in_progress', 'completed']

const emptyForm: ActionItemCreateInput = {
  title: '',
  description: '',
  assignee: '',
  due_date: '',
  priority: 'medium',
  status: 'pending',
  estimated_hours: null,
  dependencies: [],
}

const toDateInput = (value?: string | null): string =>
  value ? value.slice(0, 10) : ''

/**
 * 行动项管理：接后端组新建的 CRUD（基于 meeting_tasks 表，
 * 响应沿用 ai_analysis_schemas.py 的 ActionItem 字段形状）。
 * 端点未就绪（404）时展示“接口尚未就绪”空态 + 重试，不编假数据顶上去。
 */
const ActionItems: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const [items, setItems] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [notReady, setNotReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [form, setForm] = useState<ActionItemCreateInput>(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(meetingId)) return
    setLoading(true)
    setError(null)
    setNotReady(false)
    try {
      setItems(await analyticsService.getActionItems(meetingId))
    } catch (err) {
      if (isNotFoundError(err)) {
        setNotReady(true)
        setItems([])
      } else {
        setError(apiErrorMessage(err, '获取行动项失败'))
      }
    } finally {
      setLoading(false)
    }
  }, [meetingId])

  useEffect(() => {
    load()
  }, [load])

  const resetForm = () => {
    setForm(emptyForm)
    setEditingId(null)
    setShowForm(false)
    setFormError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title.trim()) {
      setFormError('请填写行动项标题。')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      const payload: ActionItemCreateInput = {
        ...form,
        title: form.title.trim(),
        assignee: form.assignee?.trim() || undefined,
        due_date: form.due_date ? new Date(`${form.due_date}T00:00:00`).toISOString() : null,
        estimated_hours:
          form.estimated_hours === null || form.estimated_hours === undefined
            ? null
            : Number(form.estimated_hours),
      }
      if (editingId) {
        await analyticsService.updateActionItem(meetingId, editingId, payload)
      } else {
        await analyticsService.createActionItem(meetingId, payload)
      }
      resetForm()
      await load()
    } catch (err) {
      setFormError(apiErrorMessage(err, '保存行动项失败'))
    } finally {
      setSaving(false)
    }
  }

  const handleFieldChange = async (
    item: ActionItem,
    patch: Partial<ActionItem>,
  ) => {
    // 注意：后端 PATCH 本身是合并式更新（只改传了的字段，实测注册负责人
    // 在只传 status 的 PATCH 后仍保留）。之前观察到的“assignee 消失”是
    // 另一回事：未注册的人名创建时只做展示、不落 assignee_id，重读即无；
    // 所以行内改状态/优先级时仍带上整条记录的现有值，只改目标字段。
    const merged: ActionItemUpdateInput = {
      title: item.title,
      description: item.description ?? '',
      assignee: item.assignee ?? undefined,
      due_date: item.due_date ?? null,
      priority: item.priority,
      status: item.status,
      estimated_hours: item.estimated_hours ?? null,
      dependencies: item.dependencies ?? [],
      ...patch,
    }
    try {
      await analyticsService.updateActionItem(meetingId, item.action_id, merged)
      await load()
    } catch (err) {
      setError(apiErrorMessage(err, '更新行动项失败'))
    }
  }

  const handleDelete = async (actionId: string, title: string) => {
    if (!window.confirm(`确定删除行动项“${title}”吗？`)) return
    try {
      await analyticsService.deleteActionItem(meetingId, actionId)
      await load()
    } catch (err) {
      setError(apiErrorMessage(err, '删除行动项失败'))
    }
  }

  const startEdit = (item: ActionItem) => {
    setForm({
      title: item.title,
      description: item.description ?? '',
      assignee: item.assignee ?? '',
      due_date: toDateInput(item.due_date),
      priority: item.priority ?? 'medium',
      status: item.status ?? 'pending',
      estimated_hours: item.estimated_hours ?? null,
      dependencies: item.dependencies ?? [],
    })
    setEditingId(item.action_id)
    setShowForm(true)
    setFormError(null)
  }

  return (
    <AnalyticsLayout title="行动项目">
      <div data-testid="action-items">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">行动项目管理</h2>
            <p className="mt-1 text-sm text-gray-500">
              数据来源：GET/POST/PATCH/DELETE /api/v1/meetings/{meetingId}/action-items（基于 meeting_tasks 表）
            </p>
          </div>
          {!notReady && (
            <Button
              onClick={() => {
                resetForm()
                setShowForm(true)
              }}
              disabled={loading}
            >
              <Plus className="mr-1 h-4 w-4" />新建行动项
            </Button>
          )}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12 text-gray-600">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-3">正在加载行动项…</span>
          </div>
        )}

        {error && !loading && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
              <Button variant="outline" size="sm" className="ml-4" onClick={load}>
                <RefreshCw className="mr-1 h-4 w-4" />重试
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {!loading && notReady && (
          <div className="mt-6">
            <EmptyState
              title="行动项接口尚未就绪"
              description="后端组正在新建行动项 CRUD 端点（GET/POST/PATCH/DELETE /action-items），当前返回 404。端点就绪后本页自动可用，无需改前端。"
              actionLabel="重试"
              onAction={load}
            />
          </div>
        )}

        {!loading && !notReady && !error && showForm && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>{editingId ? '编辑行动项' : '新建行动项'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">标题 *</label>
                  <Input
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    placeholder="例如：完成数据库设计文档"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">描述</label>
                  <Textarea
                    value={form.description ?? ''}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="行动项的具体内容"
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-4">
                  <div>
                    <label className="text-sm font-medium">负责人</label>
                    <Input
                      value={form.assignee ?? ''}
                      onChange={(e) => setForm({ ...form, assignee: e.target.value })}
                      placeholder="负责人姓名"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">截止日期</label>
                    <Input
                      type="date"
                      value={form.due_date ?? ''}
                      onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">优先级</label>
                    <Select
                      value={form.priority ?? 'medium'}
                      onValueChange={(v) => setForm({ ...form, priority: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="选择优先级" />
                      </SelectTrigger>
                      <SelectContent>
                        {PRIORITIES.map((p) => (
                          <SelectItem key={p} value={p}>
                            {PRIORITY_LABEL[p]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">预估工时（小时）</label>
                    <Input
                      type="number"
                      min={0}
                      step={0.5}
                      value={form.estimated_hours ?? ''}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          estimated_hours: e.target.value === '' ? null : Number(e.target.value),
                        })
                      }
                    />
                  </div>
                </div>
                {formError && (
                  <Alert className="border-red-200 bg-red-50">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <AlertDescription className="text-red-800">{formError}</AlertDescription>
                  </Alert>
                )}
                <div className="flex gap-2">
                  <Button type="submit" disabled={saving}>
                    {saving ? '保存中…' : editingId ? '保存修改' : '创建行动项'}
                  </Button>
                  <Button type="button" variant="outline" onClick={resetForm}>
                    <X className="mr-1 h-4 w-4" />取消
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {!loading && !notReady && !error && items.length === 0 && !showForm && (
          <div className="mt-6">
            <EmptyState
              title="暂无行动项"
              description="该会议还没有行动项，点击“新建行动项”创建。"
              actionLabel="新建行动项"
              onAction={() => setShowForm(true)}
            />
          </div>
        )}

        {!loading && !notReady && items.length > 0 && (
          <Card className="mt-6">
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标题</TableHead>
                    <TableHead>负责人</TableHead>
                    <TableHead>截止日期</TableHead>
                    <TableHead>优先级</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>预估工时</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.action_id}>
                      <TableCell>
                        <div className="font-medium">{item.title}</div>
                        {item.description && (
                          <div className="text-xs text-muted-foreground">{item.description}</div>
                        )}
                      </TableCell>
                      <TableCell>{item.assignee ?? '暂无数据'}</TableCell>
                      <TableCell>
                        {item.due_date ? new Date(item.due_date).toLocaleDateString() : '暂无数据'}
                      </TableCell>
                      <TableCell>
                        <Select
                          value={item.priority ?? 'medium'}
                          onValueChange={(v) => handleFieldChange(item, { priority: v })}
                        >
                          <SelectTrigger className="w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PRIORITIES.map((p) => (
                              <SelectItem key={p} value={p}>
                                {PRIORITY_LABEL[p]}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Select
                          value={item.status ?? 'pending'}
                          onValueChange={(v) => handleFieldChange(item, { status: v })}
                        >
                          <SelectTrigger className="w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {STATUSES.map((s) => (
                              <SelectItem key={s} value={s}>
                                {STATUS_LABEL[s]}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        {item.estimated_hours === null || item.estimated_hours === undefined
                          ? '暂无数据'
                          : `${item.estimated_hours} 小时`}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => startEdit(item)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(item.action_id, item.title)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="mt-4 text-xs text-muted-foreground">
                状态流转：待办 → 进行中 → 已完成，在上方状态下拉中直接切换；优先级同理。
                <Badge variant="outline" className="ml-2">
                  共 {items.length} 项
                </Badge>
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </AnalyticsLayout>
  )
}

export default ActionItems
