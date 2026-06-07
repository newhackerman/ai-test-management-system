import React from 'react'
import { Calendar, Copy, Edit, Eye, MoreHorizontal, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import type { Project } from '@/types/project'
import { cn } from '@/lib/utils'
import { getProjectTypeLabel } from '@/utils/projectType'

interface ProjectCardProps {
  project: Project
  onView?: (project: Project) => void
  onClick?: (project: Project) => void
  onEdit?: (project: Project) => void
  onDelete?: (project: Project) => void
  onExport?: (project: Project) => void
  onDuplicate?: (project: Project) => void
  className?: string
}

const statusText: Record<Project['status'], string> = {
  PLANNING: '规划中',
  IN_PROGRESS: '进行中',
  ON_HOLD: '已暂停',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  ARCHIVED: '已归档',
}

const priorityText: Record<Project['priority'], string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  URGENT: '紧急',
}

const riskText: Record<Project['risk_level'], string> = {
  LOW: '低风险',
  MEDIUM: '中风险',
  HIGH: '高风险',
  CRITICAL: '严重风险',
}

const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onView,
  onClick,
  onEdit,
  onDelete,
  onExport,
  onDuplicate,
  className,
}) => {
  const openProject = () => (onView || onClick)?.(project)

  return (
    <Card className={cn('overflow-hidden transition-shadow hover:shadow-md', className)}>
      <CardHeader className="space-y-3 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate text-lg">{project.project_name}</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">{project.project_code}</p>
          </div>
          <Badge variant={project.status === 'COMPLETED' ? 'secondary' : 'default'}>
            {statusText[project.status] || project.status}
          </Badge>
        </div>
        {project.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{project.description}</p>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{getProjectTypeLabel(project.project_type)}</Badge>
          <Badge variant="outline">优先级：{priorityText[project.priority] || project.priority}</Badge>
          <Badge variant={project.risk_level === 'CRITICAL' ? 'destructive' : 'outline'}>
            {riskText[project.risk_level] || project.risk_level}
          </Badge>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">项目进度</span>
            <span className="font-medium">{project.progress_percentage || 0}%</span>
          </div>
          <Progress value={project.progress_percentage || 0} />
        </div>

        <div className="grid grid-cols-3 gap-3 text-center text-sm">
          <div>
            <div className="font-semibold">{project.task_count || 0}</div>
            <div className="text-xs text-muted-foreground">任务</div>
          </div>
          <div>
            <div className="font-semibold">{project.test_case_count || 0}</div>
            <div className="text-xs text-muted-foreground">用例</div>
          </div>
          <div>
            <div className="font-semibold">{project.defect_count || 0}</div>
            <div className="text-xs text-muted-foreground">缺陷</div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 border-t pt-3">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" />
            <span>{project.planned_end_date || project.updated_at?.slice(0, 10) || '未设置'}</span>
          </div>
          <div className="flex items-center gap-1">
            <Button type="button" variant="ghost" size="sm" onClick={openProject} title="查看">
              <Eye className="h-4 w-4" />
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => onEdit?.(project)} title="编辑">
              <Edit className="h-4 w-4" />
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => onDuplicate?.(project)} title="复制">
              <Copy className="h-4 w-4" />
            </Button>
            {onExport && (
              <Button type="button" variant="ghost" size="sm" onClick={() => onExport(project)} title="导出">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            )}
            <Button type="button" variant="ghost" size="sm" onClick={() => onDelete?.(project)} title="删除">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export { ProjectCard }
export default ProjectCard
