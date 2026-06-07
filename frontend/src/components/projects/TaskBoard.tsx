import React from 'react'
import { Plus } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import type { Task } from '@/types/project'

interface TaskBoardProps {
  projectId?: number
  tasks?: Task[]
  onTaskClick?: (task: Task) => void
  onCreateTask?: (status?: Task['status']) => void
}

const columns: Array<{ id: Task['status']; title: string }> = [
  { id: 'TODO', title: '待开始' },
  { id: 'ASSIGNED', title: '已分配' },
  { id: 'IN_PROGRESS', title: '进行中' },
  { id: 'PENDING_REVIEW', title: '待评审' },
  { id: 'COMPLETED', title: '已完成' },
  { id: 'BLOCKED', title: '阻塞' },
]

const priorityText: Record<Task['priority'], string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  URGENT: '紧急',
}

export function TaskBoard({ projectId, tasks = [], onTaskClick, onCreateTask }: TaskBoardProps) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3 2xl:grid-cols-6">
      {columns.map((column) => {
        const columnTasks = tasks.filter((task) => task.status === column.id)
        return (
          <div key={column.id} className="rounded-md border bg-muted/30 p-3">
            <div className="mb-3 flex items-center justify-between">
              <div className="font-medium">{column.title}</div>
              <Badge variant="outline">{columnTasks.length}</Badge>
            </div>
            <div className="space-y-2">
              {columnTasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  className="w-full text-left"
                  onClick={() => onTaskClick?.(task)}
                >
                  <Card className="p-3 hover:shadow-sm">
                    <div className="font-medium">{task.task_name}</div>
                    {task.description && (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{task.description}</p>
                    )}
                    <div className="mt-3 flex items-center justify-between text-xs">
                      <Badge variant="outline">{priorityText[task.priority] || task.priority}</Badge>
                      <span className="text-muted-foreground">{task.planned_end_date || '未排期'}</span>
                    </div>
                  </Card>
                </button>
              ))}
              <Button type="button" variant="ghost" className="w-full" onClick={() => onCreateTask?.(column.id)}>
                <Plus className="mr-2 h-4 w-4" />
                新建任务
              </Button>
            </div>
          </div>
        )
      })}
      {tasks.length === 0 && (
        <div className="col-span-full rounded-md border p-8 text-center text-sm text-muted-foreground">
          项目 {projectId ? `#${projectId}` : ''} 暂无任务。
        </div>
      )}
    </div>
  )
}

export default TaskBoard
