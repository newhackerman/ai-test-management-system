import React, { useMemo, useState } from 'react'
import { BarChart3, Download, LayoutGrid, Plus, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import type { Task } from '@/types/project'
import { GanttChart } from './GanttChart'
import { TaskBoard } from './TaskBoard'
import { TaskCreateModal } from './TaskCreateModal'

interface TaskManagementProps {
  projectId?: number
  className?: string
}

export function TaskManagement({ projectId = 0, className = '' }: TaskManagementProps) {
  const [activeTab, setActiveTab] = useState('board')
  const [keyword, setKeyword] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createTaskStatus, setCreateTaskStatus] = useState<Task['status'] | undefined>()
  const [tasks, setTasks] = useState<Task[]>([])

  const filteredTasks = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return tasks
    return tasks.filter((task) =>
      [task.task_name, task.description, task.task_code]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized)),
    )
  }, [keyword, tasks])

  const completedCount = tasks.filter((task) => task.status === 'COMPLETED').length
  const blockedCount = tasks.filter((task) => task.status === 'BLOCKED').length
  const activeCount = tasks.filter((task) => task.status === 'IN_PROGRESS').length

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">任务管理</h1>
          <p className="text-sm text-muted-foreground">管理项目任务、进度和执行状态。</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline">
            <Download className="mr-2 h-4 w-4" />
            导出
          </Button>
          <Button type="button" variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button type="button" onClick={() => setShowCreateModal(true)}>
            <Plus className="mr-2 h-4 w-4" />
            新建任务
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card className="p-4"><div className="text-sm text-muted-foreground">总任务</div><div className="text-2xl font-semibold">{tasks.length}</div></Card>
        <Card className="p-4"><div className="text-sm text-muted-foreground">进行中</div><div className="text-2xl font-semibold">{activeCount}</div></Card>
        <Card className="p-4"><div className="text-sm text-muted-foreground">已完成</div><div className="text-2xl font-semibold">{completedCount}</div></Card>
        <Card className="p-4"><div className="text-sm text-muted-foreground">阻塞</div><div className="text-2xl font-semibold">{blockedCount}</div></Card>
      </div>

      <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索任务" />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="board" className="flex items-center gap-2">
            <LayoutGrid className="h-4 w-4" />
            看板视图
          </TabsTrigger>
          <TabsTrigger value="gantt" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            甘特视图
          </TabsTrigger>
        </TabsList>
        <TabsContent value="board" className="mt-6">
          <TaskBoard
            projectId={projectId}
            tasks={filteredTasks}
            onCreateTask={(status) => {
              setCreateTaskStatus(status)
              setShowCreateModal(true)
            }}
          />
        </TabsContent>
        <TabsContent value="gantt" className="mt-6">
          <GanttChart tasks={filteredTasks} />
        </TabsContent>
      </Tabs>

      <TaskCreateModal
        open={showCreateModal}
        onClose={() => {
          setShowCreateModal(false)
          setCreateTaskStatus(undefined)
        }}
        projectId={projectId}
        initialStatus={createTaskStatus}
        onSuccess={(task) => setTasks((current) => [task, ...current])}
      />
    </div>
  )
}

export default TaskManagement
