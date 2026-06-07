import React, { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Calendar, Check, DollarSign, Tag, User, X } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Textarea } from '@/components/ui/Textarea'
import type { CreateProjectRequest, Project } from '@/types/project'
import { normalizeProjectType, projectTypeOptions } from '@/utils/projectType'

interface ProjectCreateModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: CreateProjectRequest) => Promise<void>
  editProject?: Project | null
  loading?: boolean
  currentUserId?: number
  currentUserName?: string
  submitError?: string
}

type FormErrors = Partial<Record<keyof CreateProjectRequest | 'date_range' | 'tags', string>>

const priorityOptions: Array<{ value: Project['priority']; label: string }> = [
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
  { value: 'URGENT', label: '紧急' },
]

const today = () => new Date().toISOString().slice(0, 10)

const addDays = (dateText: string, days: number) => {
  const date = new Date(dateText)
  if (Number.isNaN(date.getTime())) return today()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

const cleanOptional = (value?: string) => {
  const cleaned = value?.trim()
  return cleaned ? cleaned : undefined
}

const initialProjectData = (managerId: number): CreateProjectRequest => {
  const start = today()
  return {
    project_name: '',
    description: '',
    project_type: 'BUSINESS_SYSTEM',
    priority: 'MEDIUM',
    planned_start_date: start,
    planned_end_date: addDays(start, 14),
    project_manager_id: managerId,
    client_contact: '',
    budget: undefined,
    tags: [],
  }
}

const ProjectCreateModal: React.FC<ProjectCreateModalProps> = ({
  open,
  onClose,
  onSubmit,
  editProject,
  loading = false,
  currentUserId = 1,
  currentUserName = '当前用户',
  submitError = '',
}) => {
  const [formData, setFormData] = useState<CreateProjectRequest>(() => initialProjectData(currentUserId))
  const [tagInput, setTagInput] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})

  const selectedType = useMemo(
    () => projectTypeOptions.find((item) => item.value === formData.project_type) || projectTypeOptions[0],
    [formData.project_type]
  )

  useEffect(() => {
    if (!open) return

    if (editProject) {
      setFormData({
        project_name: editProject.project_name || '',
        description: editProject.description || '',
        project_type: normalizeProjectType(editProject.project_type),
        priority: editProject.priority || 'MEDIUM',
        planned_start_date: editProject.planned_start_date || today(),
        planned_end_date: editProject.planned_end_date || addDays(editProject.planned_start_date || today(), 14),
        project_manager_id: editProject.project_manager_id || currentUserId,
        test_manager_id: editProject.test_manager_id,
        client_contact: editProject.client_contact || '',
        budget: editProject.budget,
        tags: editProject.tags || [],
        custom_fields: editProject.custom_fields,
      })
    } else {
      setFormData(initialProjectData(currentUserId))
    }
    setErrors({})
    setTagInput('')
  }, [currentUserId, editProject, open])

  const updateField = <K extends keyof CreateProjectRequest>(field: K, value: CreateProjectRequest[K]) => {
    setFormData((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined, date_range: undefined }))
  }

  const validateForm = () => {
    const nextErrors: FormErrors = {}
    const name = formData.project_name.trim()
    const start = formData.planned_start_date
    const end = formData.planned_end_date

    if (!name) nextErrors.project_name = '请输入项目名称'
    if (name.length > 200) nextErrors.project_name = '项目名称不能超过 200 个字符'
    if (!start) nextErrors.planned_start_date = '请选择计划开始日期'
    if (!end) nextErrors.planned_end_date = '请选择计划结束日期'
    if (start && end && new Date(start) >= new Date(end)) {
      nextErrors.date_range = '计划结束日期必须晚于开始日期'
    }
    if (formData.budget !== undefined && Number(formData.budget) < 0) {
      nextErrors.budget = '预算不能小于 0'
    }
    if (!formData.project_manager_id) {
      nextErrors.project_manager_id = '缺少项目负责人'
    }

    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!validateForm()) return

    await onSubmit({
      ...formData,
      project_name: formData.project_name.trim(),
      description: cleanOptional(formData.description),
      client_contact: cleanOptional(formData.client_contact),
      budget: formData.budget === undefined || Number.isNaN(Number(formData.budget)) ? undefined : Number(formData.budget),
      tags: (formData.tags || []).map((tag) => tag.trim()).filter(Boolean),
    })
  }

  const handleStartDateChange = (value: string) => {
    setFormData((current) => {
      const currentEnd = current.planned_end_date
      const shouldMoveEnd = !currentEnd || new Date(currentEnd) <= new Date(value)
      return {
        ...current,
        planned_start_date: value,
        planned_end_date: shouldMoveEnd ? addDays(value, 14) : currentEnd,
      }
    })
    setErrors((current) => ({ ...current, planned_start_date: undefined, date_range: undefined }))
  }

  const addTag = (value = tagInput) => {
    const tag = value.trim()
    if (!tag) return
    setFormData((current) => {
      const tags = current.tags || []
      if (tags.includes(tag)) return current
      return { ...current, tags: [...tags, tag] }
    })
    setTagInput('')
  }

  const removeTag = (tagToRemove: string) => {
    setFormData((current) => ({
      ...current,
      tags: (current.tags || []).filter((tag) => tag !== tagToRemove),
    }))
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && !loading && onClose()}>
      <DialogContent className="max-h-[92vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editProject ? '编辑项目' : '新建项目'}</DialogTitle>
          <p className="mt-1 text-sm text-gray-600">
            填好名称和计划周期即可创建，其他信息可以之后补充。
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {(submitError || errors.date_range) && (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4" />
              <span>{submitError || errors.date_range}</span>
            </div>
          )}

          <section className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <Label htmlFor="project_name">项目名称 *</Label>
                <Input
                  id="project_name"
                  value={formData.project_name}
                  onChange={(event) => updateField('project_name', event.target.value)}
                  placeholder="例如：支付链路回归测试"
                  className={errors.project_name ? 'border-red-500' : ''}
                  autoFocus
                />
                {errors.project_name && <p className="mt-1 text-sm text-red-500">{errors.project_name}</p>}
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="description">项目说明</Label>
                <Textarea
                  id="description"
                  value={formData.description || ''}
                  onChange={(event) => updateField('description', event.target.value)}
                  placeholder="说明测试范围、交付目标或关键约束"
                  rows={3}
                />
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2 text-base font-semibold text-gray-900">
              <Check className="h-4 w-4" />
              类型与优先级
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <Label>项目类型</Label>
                <select
                  value={formData.project_type}
                  onChange={(event) => updateField('project_type', event.target.value as Project['project_type'])}
                  className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  {projectTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">{selectedType.description}</p>
              </div>

              <div>
                <Label>优先级</Label>
                <div className="mt-1 grid grid-cols-4 overflow-hidden rounded-md border">
                  {priorityOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => updateField('priority', option.value)}
                      className={`h-10 border-r text-sm last:border-r-0 ${
                        formData.priority === option.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2 text-base font-semibold text-gray-900">
              <Calendar className="h-4 w-4" />
              计划周期
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="planned_start_date">开始日期 *</Label>
                <Input
                  id="planned_start_date"
                  type="date"
                  value={formData.planned_start_date}
                  onChange={(event) => handleStartDateChange(event.target.value)}
                  className={errors.planned_start_date ? 'border-red-500' : ''}
                />
                {errors.planned_start_date && <p className="mt-1 text-sm text-red-500">{errors.planned_start_date}</p>}
              </div>

              <div>
                <Label htmlFor="planned_end_date">结束日期 *</Label>
                <Input
                  id="planned_end_date"
                  type="date"
                  value={formData.planned_end_date}
                  onChange={(event) => updateField('planned_end_date', event.target.value)}
                  className={errors.planned_end_date || errors.date_range ? 'border-red-500' : ''}
                />
                {errors.planned_end_date && <p className="mt-1 text-sm text-red-500">{errors.planned_end_date}</p>}
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2 text-base font-semibold text-gray-900">
              <User className="h-4 w-4" />
              负责人和补充信息
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <Label>项目负责人</Label>
                <div className="mt-1 flex h-10 items-center rounded-md border bg-gray-50 px-3 text-sm text-gray-700">
                  {currentUserName}
                </div>
              </div>
              <div>
                <Label htmlFor="client_contact">客户联系人</Label>
                <Input
                  id="client_contact"
                  value={formData.client_contact || ''}
                  onChange={(event) => updateField('client_contact', event.target.value)}
                  placeholder="姓名或团队"
                />
              </div>
              <div>
                <Label htmlFor="budget">预算</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    id="budget"
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.budget ?? ''}
                    onChange={(event) => updateField('budget', event.target.value ? Number(event.target.value) : undefined)}
                    placeholder="可选"
                    className={`pl-9 ${errors.budget ? 'border-red-500' : ''}`}
                  />
                </div>
                {errors.budget && <p className="mt-1 text-sm text-red-500">{errors.budget}</p>}
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2 text-base font-semibold text-gray-900">
              <Tag className="h-4 w-4" />
              标签
            </div>
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={(event) => setTagInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    addTag()
                  }
                }}
                placeholder="输入标签后回车"
              />
              <Button type="button" variant="outline" onClick={() => addTag()} disabled={!tagInput.trim()}>
                添加
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {(formData.tags || []).map((tag) => (
                <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} className="rounded-sm hover:text-red-600">
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </section>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '保存中...' : editProject ? '保存修改' : '创建项目'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default ProjectCreateModal
