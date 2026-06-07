import { useMemo } from 'react'
import { AlertTriangle, Calendar, CheckCircle, Clock, FileText, Flag, Target, TrendingUp, Users } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'

interface Milestone {
  id: number
  milestone_name: string
  description?: string
  milestone_type: 'REQUIREMENT' | 'DESIGN' | 'EXECUTION' | 'DELIVERY'
  planned_date: string
  actual_date?: string
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'OVERDUE' | 'CANCELLED'
  deliverables?: string[]
  acceptance_criteria?: string
  owner_id: number
  owner?: {
    id: number
    full_name: string
    avatar_url?: string
  }
  dependency_milestones?: number[]
  progress_percentage?: number
}

interface MilestoneTimelineProps {
  milestones: Milestone[]
  onMilestoneClick?: (milestone: Milestone) => void
  className?: string
}

const milestoneTypeConfig = {
  REQUIREMENT: { label: '需求', color: 'bg-blue-100 text-blue-800', icon: FileText, bgColor: 'bg-blue-50' },
  DESIGN: { label: '设计', color: 'bg-purple-100 text-purple-800', icon: Target, bgColor: 'bg-purple-50' },
  EXECUTION: { label: '执行', color: 'bg-orange-100 text-orange-800', icon: TrendingUp, bgColor: 'bg-orange-50' },
  DELIVERY: { label: '交付', color: 'bg-green-100 text-green-800', icon: Flag, bgColor: 'bg-green-50' },
}

const statusConfig = {
  PENDING: { label: '待开始', color: 'bg-gray-100 text-gray-800', icon: Clock, dotColor: 'bg-gray-400' },
  IN_PROGRESS: { label: '进行中', color: 'bg-blue-100 text-blue-800', icon: TrendingUp, dotColor: 'bg-blue-500' },
  COMPLETED: { label: '已完成', color: 'bg-green-100 text-green-800', icon: CheckCircle, dotColor: 'bg-green-500' },
  OVERDUE: { label: '已逾期', color: 'bg-red-100 text-red-800', icon: AlertTriangle, dotColor: 'bg-red-500' },
  CANCELLED: { label: '已取消', color: 'bg-gray-100 text-gray-800', icon: Clock, dotColor: 'bg-gray-400' },
}

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '日期未知'

  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    timeZone: 'Asia/Shanghai',
  })
}

const getDaysUntilDue = (value: string) => {
  const target = new Date(value)
  if (Number.isNaN(target.getTime())) return 0
  const today = new Date()
  const diff = target.getTime() - today.getTime()
  return Math.ceil(diff / (24 * 60 * 60 * 1000))
}

function MilestoneCard({
  milestone,
  isFirst,
  isLast,
  onClick,
}: {
  milestone: Milestone
  isFirst: boolean
  isLast: boolean
  onClick?: (milestone: Milestone) => void
}) {
  const typeConfig = milestoneTypeConfig[milestone.milestone_type]
  const statusConf = statusConfig[milestone.status]
  const TypeIcon = typeConfig.icon
  const StatusIcon = statusConf.icon
  const daysUntilDue = getDaysUntilDue(milestone.planned_date)
  const isOverdue = milestone.status !== 'COMPLETED' && milestone.status !== 'CANCELLED' && daysUntilDue < 0

  return (
    <div className="flex items-start gap-4">
      <div className="flex flex-col items-center">
        {!isFirst && <div className="h-6 w-0.5 bg-border" />}
        <div className={`z-10 h-4 w-4 rounded-full border-2 border-background ${statusConf.dotColor}`} />
        {!isLast && <div className="h-6 w-0.5 bg-border" />}
      </div>

      <Card
        className={`flex-1 cursor-pointer p-4 transition-all hover:shadow-md ${typeConfig.bgColor}`}
        onClick={() => onClick?.(milestone)}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <TypeIcon className="h-4 w-4" />
              <h4 className="font-semibold text-foreground">{milestone.milestone_name}</h4>
              <Badge variant="outline" className={typeConfig.color}>
                {typeConfig.label}
              </Badge>
              <Badge variant="outline" className={statusConf.color}>
                <StatusIcon className="mr-1 h-3 w-3" />
                {statusConf.label}
              </Badge>
            </div>

            {milestone.description && (
              <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{milestone.description}</p>
            )}
          </div>
        </div>

        {milestone.progress_percentage !== undefined && milestone.status === 'IN_PROGRESS' && (
          <div className="mb-3">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">完成进度</span>
              <span className="font-medium">{milestone.progress_percentage}%</span>
            </div>
            <Progress value={milestone.progress_percentage} className="h-1" />
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Calendar className="h-3 w-3" />
              <span>计划：{formatDate(milestone.planned_date)}</span>
            </div>

            {milestone.actual_date && (
              <div className="flex items-center gap-1 text-muted-foreground">
                <CheckCircle className="h-3 w-3" />
                <span>完成：{formatDate(milestone.actual_date)}</span>
              </div>
            )}

            {milestone.owner && (
              <div className="flex items-center gap-1 text-muted-foreground">
                <Users className="h-3 w-3" />
                <span>{milestone.owner.full_name}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isOverdue && <Badge variant="destructive">逾期 {Math.abs(daysUntilDue)} 天</Badge>}
            {!isOverdue && milestone.status !== 'COMPLETED' && daysUntilDue <= 7 && daysUntilDue >= 0 && (
              <Badge variant="outline" className="bg-yellow-100 text-yellow-800">
                {daysUntilDue === 0 ? '今天到期' : `${daysUntilDue} 天后到期`}
              </Badge>
            )}
          </div>
        </div>

        {milestone.deliverables && milestone.deliverables.length > 0 && (
          <div className="mt-3 border-t pt-3">
            <div className="mb-2 text-xs text-muted-foreground">交付物</div>
            <div className="flex flex-wrap gap-1">
              {milestone.deliverables.slice(0, 3).map((deliverable) => (
                <Badge key={deliverable} variant="secondary">
                  {deliverable}
                </Badge>
              ))}
              {milestone.deliverables.length > 3 && (
                <Badge variant="secondary">+{milestone.deliverables.length - 3}</Badge>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

function MilestoneStats({ milestones }: { milestones: Milestone[] }) {
  const stats = useMemo(() => {
    const total = milestones.length
    const completed = milestones.filter((milestone) => milestone.status === 'COMPLETED').length
    const inProgress = milestones.filter((milestone) => milestone.status === 'IN_PROGRESS').length
    const overdue = milestones.filter((milestone) => milestone.status === 'OVERDUE').length
    const upcoming = milestones.filter((milestone) => {
      const daysUntil = getDaysUntilDue(milestone.planned_date)
      return milestone.status === 'PENDING' && daysUntil <= 7 && daysUntil >= 0
    }).length

    return { total, completed, inProgress, overdue, upcoming }
  }, [milestones])

  return (
    <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
      <Card className="p-4 text-center">
        <div className="text-2xl font-bold text-foreground">{stats.total}</div>
        <div className="text-sm text-muted-foreground">总里程碑</div>
      </Card>
      <Card className="p-4 text-center">
        <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
        <div className="text-sm text-muted-foreground">已完成</div>
      </Card>
      <Card className="p-4 text-center">
        <div className="text-2xl font-bold text-blue-600">{stats.inProgress}</div>
        <div className="text-sm text-muted-foreground">进行中</div>
      </Card>
      <Card className="p-4 text-center">
        <div className="text-2xl font-bold text-red-600">{stats.overdue}</div>
        <div className="text-sm text-muted-foreground">已逾期</div>
      </Card>
      <Card className="p-4 text-center">
        <div className="text-2xl font-bold text-orange-600">{stats.upcoming}</div>
        <div className="text-sm text-muted-foreground">即将到期</div>
      </Card>
    </div>
  )
}

export function MilestoneTimeline({ milestones, onMilestoneClick, className = '' }: MilestoneTimelineProps) {
  const sortedMilestones = useMemo(
    () => [...milestones].sort((a, b) => new Date(a.planned_date).getTime() - new Date(b.planned_date).getTime()),
    [milestones],
  )

  if (milestones.length === 0) {
    return (
      <Card className={`p-8 text-center ${className}`}>
        <Target className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="mb-2 text-lg font-semibold text-foreground">暂无里程碑</h3>
        <p className="mb-4 text-muted-foreground">项目还没有设置里程碑，建议添加关键节点来跟踪项目进展。</p>
        <Button>
          <Target className="mr-2 h-4 w-4" />
          添加里程碑
        </Button>
      </Card>
    )
  }

  return (
    <div className={className}>
      <MilestoneStats milestones={milestones} />

      <Card className="p-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h3 className="flex items-center gap-2 text-lg font-semibold">
            <Target className="h-5 w-5" />
            <span>里程碑时间线</span>
          </h3>

          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            {[
              ['bg-green-500', '已完成'],
              ['bg-blue-500', '进行中'],
              ['bg-red-500', '逾期'],
              ['bg-gray-400', '待开始'],
            ].map(([colorClass, label]) => (
              <div key={label} className="flex items-center gap-1">
                <div className={`h-3 w-3 rounded-full ${colorClass}`} />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          {sortedMilestones.map((milestone, index) => (
            <MilestoneCard
              key={milestone.id}
              milestone={milestone}
              isFirst={index === 0}
              isLast={index === sortedMilestones.length - 1}
              onClick={onMilestoneClick}
            />
          ))}
        </div>
      </Card>
    </div>
  )
}

export default MilestoneTimeline
