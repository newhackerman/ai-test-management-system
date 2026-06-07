import { useState } from 'react'
import { Activity, AlertTriangle, Archive, CheckCircle, Clock, Pause, Play, X } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Textarea } from '@/components/ui/Textarea'
import type { Project } from '@/types/project'

interface ProjectStatusManagerProps {
  project: Project
  onStatusChange: (status: Project['status'], reason?: string) => Promise<void>
  disabled?: boolean
}

const statusConfig: Record<
  Project['status'],
  {
    label: string
    icon: typeof Clock
    color: string
    bgColor: string
    description: string
  }
> = {
  PLANNING: {
    label: '规划中',
    icon: Clock,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    description: '项目正在规划阶段，正在制定计划和准备资源。',
  },
  IN_PROGRESS: {
    label: '进行中',
    icon: Activity,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    description: '项目正在执行中，团队可以继续推进任务。',
  },
  ON_HOLD: {
    label: '已暂停',
    icon: Pause,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    description: '项目暂时停止，等待条件满足后继续。',
  },
  COMPLETED: {
    label: '已完成',
    icon: CheckCircle,
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    description: '项目已完成，后续可归档保留。',
  },
  CANCELLED: {
    label: '已取消',
    icon: X,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    description: '项目已取消，不再继续执行。',
  },
  ARCHIVED: {
    label: '已归档',
    icon: Archive,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    description: '项目已归档，仅保留查看和审计记录。',
  },
}

const transitions: Record<Project['status'], Project['status'][]> = {
  PLANNING: ['IN_PROGRESS', 'ON_HOLD', 'CANCELLED'],
  IN_PROGRESS: ['ON_HOLD', 'COMPLETED', 'CANCELLED'],
  ON_HOLD: ['IN_PROGRESS', 'CANCELLED'],
  COMPLETED: ['ARCHIVED'],
  CANCELLED: ['ARCHIVED'],
  ARCHIVED: [],
}

const quickActionMap: Partial<Record<Project['status'], { label: string; icon: typeof Clock; variant: 'default' | 'outline' }>> = {
  IN_PROGRESS: { label: '开始项目', icon: Play, variant: 'default' },
  ON_HOLD: { label: '暂停项目', icon: Pause, variant: 'outline' },
  COMPLETED: { label: '完成项目', icon: CheckCircle, variant: 'outline' },
}

const ProjectStatusManager: React.FC<ProjectStatusManagerProps> = ({ project, onStatusChange, disabled = false }) => {
  const [showDialog, setShowDialog] = useState(false)
  const [selectedStatus, setSelectedStatus] = useState<Project['status']>(project.status)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const currentConfig = statusConfig[project.status]
  const selectedConfig = statusConfig[selectedStatus]
  const availableTransitions = transitions[project.status] || []
  const CurrentIcon = currentConfig.icon

  const quickActions = availableTransitions
    .filter((status) => quickActionMap[status])
    .map((status) => ({ status, ...quickActionMap[status]! }))

  const openStatusDialog = (status = project.status) => {
    setSelectedStatus(status)
    setReason('')
    setShowDialog(true)
  }

  const handleConfirmStatusChange = async () => {
    if (selectedStatus === project.status) {
      setShowDialog(false)
      return
    }

    try {
      setLoading(true)
      await onStatusChange(selectedStatus, reason.trim() || undefined)
      setShowDialog(false)
      setReason('')
    } finally {
      setLoading(false)
    }
  }

  const reasonRequired = selectedStatus === 'ON_HOLD' || selectedStatus === 'CANCELLED'

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div className={`flex items-center gap-2 rounded-lg px-3 py-2 ${currentConfig.bgColor}`}>
          <CurrentIcon className={`h-4 w-4 ${currentConfig.color}`} />
          <span className={`font-medium ${currentConfig.color}`}>{currentConfig.label}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {quickActions.map((action) => {
            const ActionIcon = action.icon
            return (
              <Button
                key={action.status}
                size="sm"
                variant={action.variant}
                onClick={() => openStatusDialog(action.status)}
                disabled={disabled}
              >
                <ActionIcon className="mr-2 h-4 w-4" />
                {action.label}
              </Button>
            )
          })}

          {availableTransitions.length > quickActions.length && (
            <Button size="sm" variant="ghost" onClick={() => openStatusDialog()} disabled={disabled}>
              更多状态...
            </Button>
          )}
        </div>
      </div>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>更改项目状态</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">当前状态</label>
              <div className={`mt-1 flex items-center gap-2 rounded-lg px-3 py-2 ${currentConfig.bgColor}`}>
                <CurrentIcon className={`h-4 w-4 ${currentConfig.color}`} />
                <span className={`font-medium ${currentConfig.color}`}>{currentConfig.label}</span>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground" htmlFor="project-status-select">
                新状态
              </label>
              <select
                id="project-status-select"
                value={selectedStatus}
                onChange={(event) => setSelectedStatus(event.target.value as Project['status'])}
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value={project.status}>{currentConfig.label}（当前）</option>
                {availableTransitions.map((status) => (
                  <option key={status} value={status}>
                    {statusConfig[status].label}
                  </option>
                ))}
              </select>

              {selectedStatus !== project.status && (
                <p className="mt-1 text-sm text-muted-foreground">{selectedConfig.description}</p>
              )}
            </div>

            {selectedStatus !== project.status && (
              <div>
                <label className="text-sm font-medium text-muted-foreground" htmlFor="status-change-reason">
                  变更原因 {reasonRequired && '*'}
                </label>
                <Textarea
                  id="status-change-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="请输入状态变更原因..."
                  rows={3}
                  className="mt-1"
                />
                {reasonRequired && !reason.trim() && (
                  <p className="mt-1 text-sm text-red-500">暂停或取消项目时必须填写原因。</p>
                )}
              </div>
            )}

            {(selectedStatus === 'CANCELLED' || selectedStatus === 'ARCHIVED') && (
              <div className="flex items-start gap-2 rounded-lg bg-yellow-50 p-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
                <div className="text-sm">
                  <p className="font-medium text-yellow-800">注意</p>
                  <p className="text-yellow-700">
                    {selectedStatus === 'CANCELLED'
                      ? '取消项目后通常不能恢复到进行中状态，请谨慎操作。'
                      : '归档项目后将限制编辑权限，仅保留查看权限。'}
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)} disabled={loading}>
              取消
            </Button>
            <Button
              onClick={handleConfirmStatusChange}
              disabled={loading || selectedStatus === project.status || (reasonRequired && !reason.trim())}
            >
              {loading ? '更新中...' : '确认更改'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default ProjectStatusManager
