import React, { useState, useMemo } from 'react'
import { 
  Plus, 
  Search, 
  Filter,
  Grid3X3,
  List,
  SortAsc,
  SortDesc,
  Download,
  RefreshCw,
  Settings,
  FolderOpen
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Select'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuCheckboxItem } from '@/components/ui/DropdownMenu'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Skeleton } from '@/components/ui/Skeleton'
import ProjectCard from './ProjectCard'
import type { Project, ProjectFilters } from '@/types/project'
import { normalizeProjectType, projectTypeOptions } from '@/utils/projectType'

interface ProjectListProps {
  projects: Project[]
  loading?: boolean
  error?: string
  filters?: ProjectFilters
  onFiltersChange?: (filters: ProjectFilters) => void
  onCreateProject?: () => void
  onViewProject?: (project: Project) => void
  onEditProject?: (project: Project) => void
  onDeleteProject?: (project: Project) => void
  onExportProject?: (project: Project) => void
  onDuplicateProject?: (project: Project) => void
  onRefresh?: () => void
  className?: string
}

type ViewMode = 'grid' | 'list'
type SortField = 'created_at' | 'updated_at' | 'project_name' | 'progress_percentage' | 'priority' | 'planned_end_date'
type SortOrder = 'asc' | 'desc'

const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  loading = false,
  error,
  filters = {},
  onFiltersChange,
  onCreateProject,
  onViewProject,
  onEditProject,
  onDeleteProject,
  onExportProject,
  onDuplicateProject,
  onRefresh,
  className = ''
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [searchQuery, setSearchQuery] = useState(filters.search || '')
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([])
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>([])

  // Status options
  const statusOptions = [
    { value: 'PLANNING', label: '规划中', count: 0 },
    { value: 'IN_PROGRESS', label: '进行中', count: 0 },
    { value: 'ON_HOLD', label: '已暂停', count: 0 },
    { value: 'COMPLETED', label: '已完成', count: 0 },
    { value: 'CANCELLED', label: '已取消', count: 0 },
    { value: 'ARCHIVED', label: '已归档', count: 0 }
  ]

  const typeOptions = projectTypeOptions.map((option) => ({ ...option, count: 0 }))

  // Priority options
  const priorityOptions = [
    { value: 'LOW', label: '低', count: 0 },
    { value: 'MEDIUM', label: '中', count: 0 },
    { value: 'HIGH', label: '高', count: 0 },
    { value: 'URGENT', label: '紧急', count: 0 }
  ]

  // Calculate counts for filter options
  const optionsWithCounts = useMemo(() => {
    const statusCounts = statusOptions.map(option => ({
      ...option,
      count: projects.filter(p => p.status === option.value).length
    }))
    
    const typeCounts = typeOptions.map(option => ({
      ...option,
      count: projects.filter(p => normalizeProjectType(p.project_type) === option.value).length
    }))
    
    const priorityCounts = priorityOptions.map(option => ({
      ...option,
      count: projects.filter(p => p.priority === option.value).length
    }))

    return { statusCounts, typeCounts, priorityCounts }
  }, [projects])

  // Filter and sort projects
  const filteredAndSortedProjects = useMemo(() => {
    let filtered = projects.filter(project => {
      // Search filter
      const matchesSearch = !searchQuery || 
        project.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.project_code.toLowerCase().includes(searchQuery.toLowerCase())

      // Status filter
      const matchesStatus = selectedStatuses.length === 0 || selectedStatuses.includes(project.status)

      // Type filter
      const matchesType = selectedTypes.length === 0 || selectedTypes.includes(normalizeProjectType(project.project_type))

      // Priority filter
      const matchesPriority = selectedPriorities.length === 0 || selectedPriorities.includes(project.priority)

      return matchesSearch && matchesStatus && matchesType && matchesPriority
    })

    // Sort projects
    filtered.sort((a, b) => {
      let aValue: any = a[sortField]
      let bValue: any = b[sortField]

      // Handle different data types
      if (sortField === 'created_at' || sortField === 'updated_at' || sortField === 'planned_end_date') {
        aValue = new Date(aValue || 0).getTime()
        bValue = new Date(bValue || 0).getTime()
      } else if (sortField === 'project_name') {
        aValue = aValue?.toLowerCase() || ''
        bValue = bValue?.toLowerCase() || ''
      } else if (sortField === 'priority') {
        const priorityOrder = { 'URGENT': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 }
        aValue = priorityOrder[aValue as keyof typeof priorityOrder] || 0
        bValue = priorityOrder[bValue as keyof typeof priorityOrder] || 0
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

    return filtered
  }, [projects, searchQuery, selectedStatuses, selectedTypes, selectedPriorities, sortField, sortOrder])

  // Handle filter changes
  const handleFiltersChange = (newFilters: Partial<ProjectFilters>) => {
    const updatedFilters = { ...filters, ...newFilters }
    onFiltersChange?.(updatedFilters)
  }

  // Handle search
  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    handleFiltersChange({ search: value })
  }

  // Handle sort change
  const handleSortChange = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  // Get active filters count
  const activeFiltersCount = selectedStatuses.length + selectedTypes.length + selectedPriorities.length

  // Render loading skeleton
  const renderSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="p-6 border rounded-lg">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
              <Skeleton className="w-10 h-10 rounded-lg" />
              <div>
                <Skeleton className="w-32 h-4 mb-2" />
                <Skeleton className="w-20 h-3" />
              </div>
            </div>
            <Skeleton className="w-8 h-8 rounded" />
          </div>
          <Skeleton className="w-full h-3 mb-4" />
          <Skeleton className="w-full h-2 mb-4" />
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Skeleton className="w-full h-8" />
            <Skeleton className="w-full h-8" />
            <Skeleton className="w-full h-8" />
          </div>
          <div className="flex justify-between">
            <Skeleton className="w-20 h-3" />
            <Skeleton className="w-16 h-3" />
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-end">
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={onRefresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button onClick={onCreateProject} className="bg-gradient-to-r from-primary to-primary/90">
            <Plus className="w-4 h-4 mr-2" />
            新建项目
          </Button>
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 lg:space-x-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索项目名称、描述或编码..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Filters and View Controls */}
        <div className="flex items-center space-x-2">
          {/* Status Filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="relative">
                <Filter className="w-4 h-4 mr-2" />
                状态
                {selectedStatuses.length > 0 && (
                  <Badge variant="secondary" className="ml-2 px-1 py-0 text-xs">
                    {selectedStatuses.length}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-48">
              {optionsWithCounts.statusCounts.map((option) => (
                <DropdownMenuCheckboxItem
                  key={option.value}
                  checked={selectedStatuses.includes(option.value)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedStatuses([...selectedStatuses, option.value])
                    } else {
                      setSelectedStatuses(selectedStatuses.filter(s => s !== option.value))
                    }
                  }}
                >
                  <div className="flex items-center justify-between w-full">
                    <span>{option.label}</span>
                    <Badge variant="outline" className="text-xs">
                      {option.count}
                    </Badge>
                  </div>
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Type Filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="relative">
                类型
                {selectedTypes.length > 0 && (
                  <Badge variant="secondary" className="ml-2 px-1 py-0 text-xs">
                    {selectedTypes.length}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-48">
              {optionsWithCounts.typeCounts.map((option) => (
                <DropdownMenuCheckboxItem
                  key={option.value}
                  checked={selectedTypes.includes(option.value)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedTypes([...selectedTypes, option.value])
                    } else {
                      setSelectedTypes(selectedTypes.filter(t => t !== option.value))
                    }
                  }}
                >
                  <div className="flex items-center justify-between w-full">
                    <span>{option.label}</span>
                    <Badge variant="outline" className="text-xs">
                      {option.count}
                    </Badge>
                  </div>
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Priority Filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="relative">
                优先级
                {selectedPriorities.length > 0 && (
                  <Badge variant="secondary" className="ml-2 px-1 py-0 text-xs">
                    {selectedPriorities.length}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-48">
              {optionsWithCounts.priorityCounts.map((option) => (
                <DropdownMenuCheckboxItem
                  key={option.value}
                  checked={selectedPriorities.includes(option.value)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedPriorities([...selectedPriorities, option.value])
                    } else {
                      setSelectedPriorities(selectedPriorities.filter(p => p !== option.value))
                    }
                  }}
                >
                  <div className="flex items-center justify-between w-full">
                    <span>{option.label}</span>
                    <Badge variant="outline" className="text-xs">
                      {option.count}
                    </Badge>
                  </div>
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Sort */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                {sortOrder === 'asc' ? <SortAsc className="w-4 h-4 mr-2" /> : <SortDesc className="w-4 h-4 mr-2" />}
                排序
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => handleSortChange('updated_at')}>
                按更新时间
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleSortChange('created_at')}>
                按创建时间
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleSortChange('project_name')}>
                按项目名称
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleSortChange('progress_percentage')}>
                按进度
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleSortChange('priority')}>
                按优先级
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleSortChange('planned_end_date')}>
                按截止日期
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* View Mode Toggle */}
          <div className="flex items-center border rounded-md">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('grid')}
              className="rounded-r-none"
            >
              <Grid3X3 className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
              className="rounded-l-none"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Active Filters Summary */}
      {activeFiltersCount > 0 && (
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">活跃筛选:</span>
          {selectedStatuses.map(status => (
            <Badge key={status} variant="secondary" className="text-xs">
              状态: {statusOptions.find(s => s.value === status)?.label}
            </Badge>
          ))}
          {selectedTypes.map(type => (
            <Badge key={type} variant="secondary" className="text-xs">
              类型: {typeOptions.find(t => t.value === type)?.label}
            </Badge>
          ))}
          {selectedPriorities.map(priority => (
            <Badge key={priority} variant="secondary" className="text-xs">
              优先级: {priorityOptions.find(p => p.value === priority)?.label}
            </Badge>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedStatuses([])
              setSelectedTypes([])
              setSelectedPriorities([])
              setSearchQuery('')
              handleFiltersChange({ search: '' })
            }}
          >
            清除筛选
          </Button>
        </div>
      )}

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          显示 {filteredAndSortedProjects.length} 个项目，共 {projects.length} 个
        </span>
        {filteredAndSortedProjects.length > 0 && (
          <Button variant="ghost" size="sm">
            <Download className="w-4 h-4 mr-2" />
            导出列表
          </Button>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="text-center py-12">
          <div className="text-red-600 mb-4 dark:text-red-400">加载项目时出错</div>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={onRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            重试
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading && renderSkeleton()}

      {/* Projects Grid/List */}
      {!loading && !error && (
        <>
          {filteredAndSortedProjects.length > 0 ? (
            <div className={
              viewMode === 'grid' 
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                : "space-y-4"
            }>
              {filteredAndSortedProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onView={onViewProject}
                  onEdit={onEditProject}
                  onDelete={onDeleteProject}
                  onExport={onExportProject}
                  onDuplicate={onDuplicateProject}
                  className={viewMode === 'list' ? 'max-w-none' : ''}
                />
              ))}
            </div>
          ) : (
            /* Empty State */
            <div className="text-center py-12">
              <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {searchQuery || activeFiltersCount > 0 ? '没有找到匹配的项目' : '还没有项目'}
              </h3>
              <p className="text-muted-foreground mb-4">
                {searchQuery || activeFiltersCount > 0 
                  ? '尝试调整搜索条件或筛选器' 
                  : '开始创建您的第一个测试项目'}
              </p>
              <Button onClick={onCreateProject}>
                <Plus className="w-4 h-4 mr-2" />
                新建项目
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ProjectList
