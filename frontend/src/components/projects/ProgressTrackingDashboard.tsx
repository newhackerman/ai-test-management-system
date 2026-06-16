// @ts-nocheck
import { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Calendar,
  CheckCircle,
  Target,
  TrendingUp,
} from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import type { ProjectProgress } from '@/types/project'

import { MilestoneTimeline } from './MilestoneTimeline'
import { ProgressChart } from './ProgressChart'
import { RiskMatrix } from './RiskMatrix'

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

interface Risk {
  id: number
  risk_name: string
  description: string
  risk_category: 'SCHEDULE' | 'QUALITY' | 'RESOURCE' | 'TECHNICAL' | 'EXTERNAL'
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  probability: number
  impact_score: number
  risk_score: number
  mitigation_strategy: 'AVOID' | 'MITIGATE' | 'TRANSFER' | 'ACCEPT'
  mitigation_plan?: string
  status: 'IDENTIFIED' | 'ANALYZING' | 'MITIGATING' | 'MONITORING' | 'CLOSED'
  owner_id: number
  owner?: {
    id: number
    full_name: string
    avatar_url?: string
  }
  identified_date: string
  target_resolution_date?: string
  actual_resolution_date?: string
}

interface Alert {
  id: number
  type: 'PROGRESS' | 'QUALITY' | 'RISK' | 'MILESTONE' | 'RESOURCE'
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  title: string
  message: string
  created_at: string
  is_read: boolean
  action_required: boolean
  related_entity_id?: number
  related_entity_type?: string
}

interface ProgressTrackingDashboardProps {
  projectId: number
  progress?: ProjectProgress
  milestones?: Milestone[]
  risks?: Risk[]
  alerts?: Alert[]
  onMilestoneClick?: (milestone: Milestone) => void
  onRiskClick?: (risk: Risk) => void
  onAlertClick?: (alert: Alert) => void
  className?: string
}

const toPercent = (value?: number) => {
  const safeValue = Number.isFinite(value) ? Number(value) : 0
  return Math.max(0, Math.min(100, safeValue <= 1 ? safeValue * 100 : safeValue))
}

const formatDateTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'

  return date.toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  })
}

function DashboardOverview({
  progress,
  milestones = [],
  risks = [],
  alerts = [],
}: {
  progress?: ProjectProgress
  milestones: Milestone[]
  risks: Risk[]
  alerts: Alert[]
}) {
  const overallProgress = progress ? Math.round(toPercent(progress.overall_progress)) : 0
  const completedMilestones = milestones.filter((m) => m.status === 'COMPLETED').length
  const overdueMilestones = milestones.filter((m) => m.status === 'OVERDUE').length
  const criticalRisks = risks.filter((r) => r.risk_level === 'CRITICAL').length
  const unreadAlerts = alerts.filter((a) => !a.is_read).length

  const progressColor =
    overallProgress >= 90
      ? 'text-green-600'
      : overallProgress >= 70
        ? 'text-blue-600'
        : overallProgress >= 50
          ? 'text-yellow-600'
          : 'text-red-600 dark:text-red-400'

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">总体进度</p>
            <p className={`text-3xl font-bold ${progressColor}`}>{overallProgress}%</p>
          </div>
          <TrendingUp className={`h-8 w-8 ${progressColor}`} />
        </div>
        {progress && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-xs">
              <span>时间：{Math.round(toPercent(progress.time_progress.progress_rate))}%</span>
              <span>任务：{Math.round(toPercent(progress.task_progress.progress_rate))}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span>质量：{Math.round(toPercent(progress.quality_progress.progress_rate))}%</span>
              <span>里程碑：{Math.round(toPercent(progress.milestone_progress.progress_rate))}%</span>
            </div>
          </div>
        )}
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">里程碑</p>
            <p className="text-3xl font-bold">
              {completedMilestones}/{milestones.length}
            </p>
          </div>
          <Target className="h-8 w-8 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="mt-4 space-y-2 text-xs">
          <div className="flex justify-between">
            <span>已完成：{completedMilestones}</span>
            <span>总计：{milestones.length}</span>
          </div>
          {overdueMilestones > 0 && <Badge variant="destructive">{overdueMilestones} 个逾期</Badge>}
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">风险管理</p>
            <p className="text-3xl font-bold text-orange-600">{risks.length}</p>
          </div>
          <AlertTriangle className="h-8 w-8 text-orange-600" />
        </div>
        <div className="mt-4 space-y-2 text-xs">
          <div className="flex justify-between">
            <span>总风险：{risks.length}</span>
            <span>严重：{criticalRisks}</span>
          </div>
          {criticalRisks > 0 && <Badge variant="destructive">{criticalRisks} 个严重风险</Badge>}
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">预警中心</p>
            <p className="text-3xl font-bold text-red-600 dark:text-red-400">{unreadAlerts}</p>
          </div>
          <Bell className="h-8 w-8 text-red-600 dark:text-red-400" />
        </div>
        <div className="mt-4 space-y-2 text-xs">
          <div className="flex justify-between">
            <span>未读：{unreadAlerts}</span>
            <span>总计：{alerts.length}</span>
          </div>
          {unreadAlerts > 0 && <Badge variant="destructive">需要关注</Badge>}
        </div>
      </Card>
    </div>
  )
}

function AlertDashboard({
  alerts,
  onAlertClick,
}: {
  alerts: Alert[]
  onAlertClick?: (alert: Alert) => void
}) {
  const alertTypeConfig = {
    PROGRESS: { label: '进度预警', icon: TrendingUp, color: 'bg-orange-100 text-orange-800' },
    QUALITY: { label: '质量预警', icon: Target, color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30' },
    RISK: { label: '风险预警', icon: AlertTriangle, color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30' },
    MILESTONE: { label: '里程碑预警', icon: Calendar, color: 'bg-yellow-100 text-yellow-800' },
    RESOURCE: { label: '资源预警', icon: Activity, color: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30' },
  }

  const alertSeverityConfig = {
    LOW: { label: '低', color: 'bg-green-100 text-green-800' },
    MEDIUM: { label: '中', color: 'bg-yellow-100 text-yellow-800' },
    HIGH: { label: '高', color: 'bg-orange-100 text-orange-800' },
    CRITICAL: { label: '严重', color: 'bg-red-100 text-red-800' },
  }

  const sortedAlerts = [...alerts]
    .filter((alert) => !alert.is_read)
    .sort((a, b) => {
      const severityOrder = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
      const severityDiff = severityOrder[b.severity] - severityOrder[a.severity]
      if (severityDiff !== 0) return severityDiff
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-semibold">
          <Bell className="h-5 w-5" />
          <span>预警中心</span>
          {sortedAlerts.length > 0 && <Badge variant="destructive">{sortedAlerts.length}</Badge>}
        </h3>

        {sortedAlerts.length > 0 && (
          <Button variant="outline" size="sm">
            全部标记已读
          </Button>
        )}
      </div>

      <div className="max-h-96 space-y-3 overflow-y-auto">
        {sortedAlerts.slice(0, 10).map((alert) => {
          const typeConfig = alertTypeConfig[alert.type]
          const severityConfig = alertSeverityConfig[alert.severity]
          const TypeIcon = typeConfig.icon

          return (
            <button
              key={alert.id}
              type="button"
              className={`w-full rounded-lg border p-3 text-left transition-all hover:shadow-md ${
                alert.severity === 'CRITICAL'
                  ? 'border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800'
                  : alert.severity === 'HIGH'
                    ? 'border-orange-200 bg-orange-50 dark:bg-orange-900/20'
                    : 'border-gray-200 bg-gray-50 dark:bg-gray-800/50 dark:border-gray-700'
              }`}
              onClick={() => onAlertClick?.(alert)}
            >
              <div className="flex items-start gap-3">
                <TypeIcon className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <h5 className="font-medium">{alert.title}</h5>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className={typeConfig.color}>
                        {typeConfig.label}
                      </Badge>
                      <Badge variant="outline" className={severityConfig.color}>
                        {severityConfig.label}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">{alert.message}</p>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{formatDateTime(alert.created_at)}</span>
                    {alert.action_required && <Badge variant="destructive">需要处理</Badge>}
                  </div>
                </div>
              </div>
            </button>
          )
        })}

        {sortedAlerts.length === 0 && (
          <div className="py-8 text-center">
            <CheckCircle className="mx-auto mb-4 h-12 w-12 text-green-500" />
            <h4 className="mb-2 text-lg font-semibold text-foreground">暂无预警</h4>
            <p className="text-muted-foreground">项目运行正常，没有需要关注的预警信息。</p>
          </div>
        )}

        {sortedAlerts.length > 10 && (
          <div className="pt-4 text-center">
            <Button variant="outline">查看全部 {sortedAlerts.length} 个预警</Button>
          </div>
        )}
      </div>
    </Card>
  )
}

export function ProgressTrackingDashboard({
  progress,
  milestones = [],
  risks = [],
  alerts = [],
  onMilestoneClick,
  onRiskClick,
  onAlertClick,
  className = '',
}: ProgressTrackingDashboardProps) {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className={`space-y-6 ${className}`}>
      <DashboardOverview progress={progress} milestones={milestones} risks={risks} alerts={alerts} />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            <span>进度分析</span>
          </TabsTrigger>
          <TabsTrigger value="milestones" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            <span>里程碑</span>
          </TabsTrigger>
          <TabsTrigger value="risks" className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span>风险矩阵</span>
          </TabsTrigger>
          <TabsTrigger value="alerts" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            <span>预警中心</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          {progress ? (
            <ProgressChart progress={progress} />
          ) : (
            <Card className="p-8 text-center">
              <BarChart3 className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-2 text-lg font-semibold text-foreground">暂无进度数据</h3>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="milestones" className="mt-6">
          <MilestoneTimeline milestones={milestones} onMilestoneClick={onMilestoneClick} />
        </TabsContent>

        <TabsContent value="risks" className="mt-6">
          <RiskMatrix risks={risks} onRiskClick={onRiskClick} />
        </TabsContent>

        <TabsContent value="alerts" className="mt-6">
          <AlertDashboard alerts={alerts} onAlertClick={onAlertClick} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ProgressTrackingDashboard
