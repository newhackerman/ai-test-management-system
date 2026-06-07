import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import type { Task } from '@/types/project'

interface TaskCreateModalProps {
  open: boolean
  onClose: () => void
  projectId: number
  task?: Task
  initialStatus?: Task['status']
  onSuccess?: (task: Task) => void
}

const defaultStatus: Task['status'] = 'TODO'

export function TaskCreateModal({
  open,
  onClose,
  projectId,
  task,
  initialStatus,
  onSuccess,
}: TaskCreateModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState<Task['status']>(initialStatus || defaultStatus)
  const [priority, setPriority] = useState<Task['priority']>('MEDIUM')

  useEffect(() => {
    if (!open) return
    setName(task?.task_name || '')
    setDescription(task?.description || '')
    setStatus(task?.status || initialStatus || defaultStatus)
    setPriority(task?.priority || 'MEDIUM')
  }, [initialStatus, open, task])

  const handleSubmit = () => {
    if (!name.trim()) return

    const now = new Date().toISOString()
    onSuccess?.({
      id: task?.id || Date.now(),
      project_id: projectId,
      task_name: name.trim(),
      description: description.trim(),
      task_type: task?.task_type || 'TEST_EXECUTION',
      priority,
      status,
      actual_hours: task?.actual_hours || 0,
      test_case_count: task?.test_case_count || 0,
      defect_count: task?.defect_count || 0,
      created_by: task?.created_by || 1,
      created_at: task?.created_at || now,
      updated_at: now,
    })
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{task ? '编辑任务' : '新建任务'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">任务名称</label>
            <Input value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">任务描述</label>
            <Textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">状态</label>
              <select value={status} onChange={(event) => setStatus(event.target.value as Task['status'])} className="h-10 w-full rounded-md border bg-background px-3 text-sm">
                <option value="TODO">待开始</option>
                <option value="ASSIGNED">已分配</option>
                <option value="IN_PROGRESS">进行中</option>
                <option value="ON_HOLD">已暂停</option>
                <option value="BLOCKED">阻塞</option>
                <option value="PENDING_REVIEW">待评审</option>
                <option value="COMPLETED">已完成</option>
                <option value="CANCELLED">已取消</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">优先级</label>
              <select value={priority} onChange={(event) => setPriority(event.target.value as Task['priority'])} className="h-10 w-full rounded-md border bg-background px-3 text-sm">
                <option value="LOW">低</option>
                <option value="MEDIUM">中</option>
                <option value="HIGH">高</option>
                <option value="URGENT">紧急</option>
              </select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>取消</Button>
          <Button type="button" onClick={handleSubmit} disabled={!name.trim()}>保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default TaskCreateModal
