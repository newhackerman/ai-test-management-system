import React, { useMemo, useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import type { Project } from '@/types/project'
import { ProjectCard } from '../ProjectCard'

interface VirtualizedProjectListProps {
  projects: Project[]
  loading?: boolean
  onProjectClick?: (project: Project) => void
  onProjectEdit?: (project: Project) => void
  onProjectDelete?: (project: Project) => void
  onRefresh?: () => void
  height?: number
  itemHeight?: number
  className?: string
}

export const VirtualizedProjectList: React.FC<VirtualizedProjectListProps> = ({
  projects,
  loading = false,
  onProjectClick,
  onProjectEdit,
  onProjectDelete,
  onRefresh,
  className = '',
}) => {
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState('')

  const filteredProjects = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    return projects.filter((project) => {
      const matchesKeyword =
        !normalized ||
        project.project_name.toLowerCase().includes(normalized) ||
        project.project_code.toLowerCase().includes(normalized) ||
        project.description?.toLowerCase().includes(normalized)
      const matchesStatus = !status || project.status === status
      return matchesKeyword && matchesStatus
    })
  }, [keyword, projects, status])

  return (
    <div className={className}>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative md:w-96">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索项目名称、编号或描述"
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="h-10 rounded-md border bg-background px-3 text-sm"
          >
            <option value="">全部状态</option>
            <option value="PLANNING">规划中</option>
            <option value="IN_PROGRESS">进行中</option>
            <option value="ON_HOLD">已暂停</option>
            <option value="COMPLETED">已完成</option>
            <option value="CANCELLED">已取消</option>
            <option value="ARCHIVED">已归档</option>
          </select>
          <Button type="button" variant="outline" onClick={onRefresh} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">项目加载中...</div>
      ) : filteredProjects.length === 0 ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">暂无匹配项目</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onView={onProjectClick}
              onEdit={onProjectEdit}
              onDelete={onProjectDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default React.memo(VirtualizedProjectList)
