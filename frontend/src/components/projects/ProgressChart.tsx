import React from 'react'
import { CheckCircle2, Clock, ShieldCheck, Target } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import type { ProjectProgress } from '@/types/project'

interface ProgressChartProps {
  progress: ProjectProgress
  className?: string
}

const toPercent = (value?: number) => {
  const safeValue = Number.isFinite(value) ? Number(value) : 0
  return Math.max(0, Math.min(100, safeValue <= 1 ? safeValue * 100 : safeValue))
}

const formatDateTime = (value?: string) => {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未记录'

  return date.toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  })
}

const Metric = ({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  detail?: string
}) => {
  const percent = toPercent(value)

  return (
    <div className="rounded-md border p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {label}
        </div>
        <span className="text-sm font-semibold">{Math.round(percent)}%</span>
      </div>
      <Progress value={percent} />
      {detail && <p className="mt-2 text-xs text-muted-foreground">{detail}</p>}
    </div>
  )
}

export function ProgressChart({ progress, className = '' }: ProgressChartProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">项目进度</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Metric
          icon={Target}
          label="总体进度"
          value={progress.overall_progress}
          detail={`计算时间：${formatDateTime(progress.calculated_at)}`}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Metric
            icon={Clock}
            label="时间进度"
            value={progress.time_progress.progress_rate}
            detail={`已过 ${progress.time_progress.days_elapsed} 天，剩余 ${progress.time_progress.days_remaining} 天`}
          />
          <Metric
            icon={CheckCircle2}
            label="任务进度"
            value={progress.task_progress.progress_rate}
            detail={`${progress.task_progress.completed_tasks}/${progress.task_progress.total_tasks} 已完成`}
          />
          <Metric
            icon={ShieldCheck}
            label="质量进度"
            value={progress.quality_progress.progress_rate}
            detail={`测试覆盖率 ${Math.round(toPercent(progress.quality_progress.test_coverage))}%，通过率 ${Math.round(toPercent(progress.quality_progress.pass_rate))}%`}
          />
        </div>
      </CardContent>
    </Card>
  )
}

export default ProgressChart
