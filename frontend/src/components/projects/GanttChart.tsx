import React from 'react'
import { CalendarDays } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import type { Task } from '@/types/project'

interface GanttChartProps {
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  className?: string
}

const statusText: Record<Task['status'], string> = {
  TODO: '待开始',
  ASSIGNED: '已分配',
  IN_PROGRESS: '进行中',
  ON_HOLD: '已暂停',
  BLOCKED: '阻塞',
  PENDING_REVIEW: '待评审',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

const statusProgress: Record<Task['status'], number> = {
  TODO: 5,
  ASSIGNED: 15,
  IN_PROGRESS: 55,
  ON_HOLD: 35,
  BLOCKED: 30,
  PENDING_REVIEW: 85,
  COMPLETED: 100,
  CANCELLED: 0,
}

export function GanttChart({ tasks, onTaskClick, className = '' }: GanttChartProps) {
  if (!tasks.length) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          暂无任务，创建任务后可查看时间计划。
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CalendarDays className="h-5 w-5" />
          任务甘特视图
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {tasks.map((task) => (
          <button
            key={task.id}
            type="button"
            onClick={() => onTaskClick?.(task)}
            className="w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/50"
          >
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate font-medium">{task.task_name}</div>
                <div className="text-xs text-muted-foreground">
                  {task.planned_start_date || '未设置'} - {task.planned_end_date || '未设置'}
                </div>
              </div>
              <Badge variant={task.status === 'BLOCKED' ? 'destructive' : 'outline'}>
                {statusText[task.status] || task.status}
              </Badge>
            </div>
            <Progress value={statusProgress[task.status] ?? 0} />
          </button>
        ))}
      </CardContent>
    </Card>
  )
}

export default GanttChart
