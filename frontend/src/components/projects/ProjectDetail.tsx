import React, { useState, useEffect } from 'react'
import { 
  ArrowLeft,
  Edit,
  Save,
  X,
  Users,
  Calendar,
  Target,
  AlertTriangle,
  BarChart3,
  FileText,
  Settings,
  MoreHorizontal,
  Download,
  Copy,
  Archive,
  Trash2,
  Play,
  Pause,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Activity
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Progress } from '@/components/ui/Progress'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/DropdownMenu'
import { Tooltip } from '@/components/ui/Tooltip'
import ProjectStatusManager from './ProjectStatusManager'
import type { Project, UpdateProjectRequest } from '@/types/project'
import { getProjectTypeLabel, normalizeProjectType, projectTypeOptions } from '@/utils/projectType'

interface ProjectDetailProps {
  project: Project
  loading?: boolean
  onBack?: () => void
  onUpdate?: (id: number, data: UpdateProjectRequest) => Promise<void>
  onDelete?: (project: Project) => Promise<void>
  onExport?: (project: Project) => Promise<void>
  onDuplicate?: (project: Project) => Promise<void>
  onStatusChange?: (id: number, status: Project['status']) => Promise<void>
  className?: string
}

const ProjectDetail: React.FC<ProjectDetailProps> = ({
  project,
  loading = false,
  onBack,
  onUpdate,
  onDelete,
  onExport,
  onDuplicate,
  onStatusChange,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState<UpdateProjectRequest>({})
  const [saving, setSaving] = useState(false)

  // Initialize edit data when project changes
  useEffect(() => {
    setEditData({
      project_name: project.project_name,
      description: project.description,
      project_type: project.project_type,
      priority: project.priority,
      planned_start_date: project.planned_start_date,
      planned_end_date: project.planned_end_date,
      budget: project.budget,
      client_contact: project.client_contact,
      tags: project.tags
    })
  }, [project])

  // Status configuration
  const getStatusConfig = (status: Project['status']) => {
    const configs = {
      PLANNING: { 
        label: '规划中', 
        variant: 'outline' as const, 
        icon: Clock,
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-50 dark:bg-blue-900/20'
      },
      IN_PROGRESS: { 
        label: '进行中', 
        variant: 'default' as const, 
        icon: Activity,
        color: 'text-green-600 dark:text-green-400',
        bgColor: 'bg-green-50'
      },
      ON_HOLD: { 
        label: '已暂停', 
        variant: 'secondary' as const, 
        icon: Pause,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50'
      },
      COMPLETED: { 
        label: '已完成', 
        variant: 'success' as const, 
        icon: CheckCircle,
        color: 'text-green-700',
        bgColor: 'bg-green-50'
      },
      CANCELLED: { 
        label: '已取消', 
        variant: 'destructive' as const, 
        icon: X,
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-50 dark:bg-red-900/20'
      },
      ARCHIVED: { 
        label: '已归档', 
        variant: 'secondary' as const, 
        icon: Archive,
        color: 'text-gray-600 dark:text-gray-400',
        bgColor: 'bg-gray-50 dark:bg-gray-800/50'
      }
    }
    return configs[status]
  }

  // Priority configuration
  const getPriorityConfig = (priority: Project['priority']) => {
    const configs = {
      LOW: { label: '低', color: 'text-green-600', bgColor: 'bg-green-100' },
      MEDIUM: { label: '中', color: 'text-yellow-600', bgColor: 'bg-yellow-100' },
      HIGH: { label: '高', color: 'text-orange-600', bgColor: 'bg-orange-100' },
      URGENT: { label: '紧急', color: 'text-red-600', bgColor: 'bg-red-100' }
    }
    return configs[priority]
  }

  // Project type configuration
  const getTypeConfig = (type: Project['project_type']) => {
    const configs = {
      BUSINESS_SYSTEM: { label: '业务系统', color: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30' },
      MOBILE_APP: { label: '移动应用', color: 'bg-cyan-100 text-cyan-800' },
      API_SERVICE: { label: '接口服务', color: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30' },
      DATA_AI: { label: '数据/AI', color: 'bg-purple-100 text-purple-800 dark:text-purple-300 dark:bg-purple-900/30' },
      INFRASTRUCTURE: { label: '基础设施', color: 'bg-slate-100 text-slate-800 dark:bg-slate-800' },
      INTERNAL_TOOL: { label: '内部工具', color: 'bg-green-100 text-green-800' },
      FUNCTIONAL: { label: '业务系统', color: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30' },
      PERFORMANCE: { label: '基础设施', color: 'bg-slate-100 text-slate-800 dark:bg-slate-800' },
      SECURITY: { label: '基础设施', color: 'bg-slate-100 text-slate-800 dark:bg-slate-800' },
      AUTOMATION: { label: '内部工具', color: 'bg-green-100 text-green-800' },
      INTEGRATION: { label: '接口服务', color: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30' }
    }
    return configs[type] || { label: getProjectTypeLabel(type), color: 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800' }
  }

  // Handle save
  const handleSave = async () => {
    if (!onUpdate) return
    
    try {
      setSaving(true)
      await onUpdate(project.id, editData)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update project:', error)
    } finally {
      setSaving(false)
    }
  }

  // Handle cancel edit
  const handleCancelEdit = () => {
    setEditData({
      project_name: project.project_name,
      description: project.description,
      project_type: project.project_type,
      priority: project.priority,
      planned_start_date: project.planned_start_date,
      planned_end_date: project.planned_end_date,
      budget: project.budget,
      client_contact: project.client_contact,
      tags: project.tags
    })
    setIsEditing(false)
  }

  // Handle status change
  const handleStatusChange = async (newStatus: Project['status']) => {
    if (!onStatusChange) return
    await onStatusChange(project.id, newStatus)
  }

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return '未设置'
    return new Date(dateString).toLocaleDateString('zh-CN')
  }

  // Calculate progress trend
  const getProgressTrend = () => {
    const timeElapsed = project.actual_start_date ? 
      Math.floor((new Date().getTime() - new Date(project.actual_start_date).getTime()) / (1000 * 60 * 60 * 24)) : 0
    const totalDays = project.planned_start_date && project.planned_end_date ?
      Math.floor((new Date(project.planned_end_date).getTime() - new Date(project.planned_start_date).getTime()) / (1000 * 60 * 60 * 24)) : 100
    
    const expectedProgress = totalDays > 0 ? (timeElapsed / totalDays) * 100 : 0
    const actualProgress = Number(project.progress_percentage) || 0
    
    if (actualProgress > expectedProgress + 10) {
      return { icon: TrendingUp, color: 'text-green-600 dark:text-green-400', label: '进度超前' }
    } else if (actualProgress < expectedProgress - 10) {
      return { icon: TrendingDown, color: 'text-red-600 dark:text-red-400', label: '进度滞后' }
    } else {
      return { icon: Activity, color: 'text-gray-600 dark:text-gray-400', label: '进度正常' }
    }
  }

  const statusConfig = getStatusConfig(project.status)
  const priorityConfig = getPriorityConfig(project.priority)
  const typeConfig = getTypeConfig(project.project_type)
  const progressTrend = getProgressTrend()
  const progressPercentage = Number(project.progress_percentage) || 0
  const StatusIcon = statusConfig.icon
  const TrendIcon = progressTrend.icon

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center space-x-3 mb-2">
              {isEditing ? (
                <Input
                  value={editData.project_name || ''}
                  onChange={(e) => setEditData({ ...editData, project_name: e.target.value })}
                  className="text-2xl font-bold border-none p-0 h-auto"
                />
              ) : (
                <h1 className="text-2xl font-bold text-foreground">{project.project_name}</h1>
              )}
              <Badge className={`${typeConfig.color}`}>
                {typeConfig.label}
              </Badge>
            </div>
            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
              <span>项目编码: {project.project_code}</span>
              <span>创建于: {formatDate(project.created_at)}</span>
              <span>更新于: {formatDate(project.updated_at)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {isEditing ? (
            <>
              <Button variant="outline" onClick={handleCancelEdit} disabled={saving}>
                <X className="w-4 h-4 mr-2" />
                取消
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? '保存中...' : '保存'}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Edit className="w-4 h-4 mr-2" />
                编辑
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    <MoreHorizontal className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onExport?.(project)}>
                    <Download className="w-4 h-4 mr-2" />
                    导出报告
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDuplicate?.(project)}>
                    <Copy className="w-4 h-4 mr-2" />
                    复制项目
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    className="text-destructive"
                    onClick={() => onDelete?.(project)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    删除项目
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>
      </div>

      {/* Status and Quick Actions */}
      <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center space-x-4">
          <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${priorityConfig.bgColor}`}>
            <span className={`text-sm ${priorityConfig.color}`}>优先级: {priorityConfig.label}</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground">健康度:</span>
            <div className={`w-3 h-3 rounded-full ${
              project.health_score >= 80 ? 'bg-green-500' :
              project.health_score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
            }`} />
            <span className="text-sm font-medium">{project.health_score}</span>
          </div>
        </div>

        <ProjectStatusManager
          project={project}
          onStatusChange={handleStatusChange}
          disabled={loading}
        />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview" className="flex items-center space-x-2">
            <BarChart3 className="w-4 h-4" />
            <span>概览</span>
          </TabsTrigger>
          <TabsTrigger value="team" className="flex items-center space-x-2">
            <Users className="w-4 h-4" />
            <span>团队</span>
          </TabsTrigger>
          <TabsTrigger value="tasks" className="flex items-center space-x-2">
            <Target className="w-4 h-4" />
            <span>任务</span>
          </TabsTrigger>
          <TabsTrigger value="milestones" className="flex items-center space-x-2">
            <Calendar className="w-4 h-4" />
            <span>里程碑</span>
          </TabsTrigger>
          <TabsTrigger value="risks" className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4" />
            <span>风险</span>
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center space-x-2">
            <Settings className="w-4 h-4" />
            <span>设置</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Project Info */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">项目信息</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">项目描述</label>
                    {isEditing ? (
                      <Textarea
                        value={editData.description || ''}
                        onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                        placeholder="请输入项目描述..."
                        className="mt-1"
                        rows={3}
                      />
                    ) : (
                      <p className="mt-1 text-sm">{project.description || '暂无描述'}</p>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">项目类型</label>
                      {isEditing ? (
                        <select
                          value={normalizeProjectType(editData.project_type || project.project_type)}
                          onChange={(event) => setEditData({ ...editData, project_type: event.target.value as Project['project_type'] })}
                          className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        >
                          {projectTypeOptions.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      ) : (
                        <p className="mt-1 text-sm">{typeConfig.label}</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">优先级</label>
                      {isEditing ? (
                        <select
                          value={editData.priority || project.priority}
                          onChange={(event) => setEditData({ ...editData, priority: event.target.value as Project['priority'] })}
                          className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        >
                          <option value="LOW">低</option>
                          <option value="MEDIUM">中</option>
                          <option value="HIGH">高</option>
                          <option value="URGENT">紧急</option>
                        </select>
                      ) : (
                        <p className="mt-1 text-sm">{priorityConfig.label}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">计划开始时间</label>
                      {isEditing ? (
                        <Input
                          type="date"
                          value={editData.planned_start_date || ''}
                          onChange={(e) => setEditData({ ...editData, planned_start_date: e.target.value })}
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">{formatDate(project.planned_start_date)}</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">计划结束时间</label>
                      {isEditing ? (
                        <Input
                          type="date"
                          value={editData.planned_end_date || ''}
                          onChange={(e) => setEditData({ ...editData, planned_end_date: e.target.value })}
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">{formatDate(project.planned_end_date)}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">项目预算</label>
                      {isEditing ? (
                        <Input
                          type="number"
                          value={editData.budget || ''}
                          onChange={(e) => setEditData({ ...editData, budget: parseFloat(e.target.value) })}
                          placeholder="请输入预算金额"
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">
                          {project.budget ? `¥${project.budget.toLocaleString()}` : '未设置'}
                        </p>
                      )}
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">客户联系人</label>
                      {isEditing ? (
                        <Input
                          value={editData.client_contact || ''}
                          onChange={(e) => setEditData({ ...editData, client_contact: e.target.value })}
                          placeholder="请输入客户联系人"
                          className="mt-1"
                        />
                      ) : (
                        <p className="mt-1 text-sm">{project.client_contact || '未设置'}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-muted-foreground">项目标签</label>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {project.tags?.map((tag, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      {(!project.tags || project.tags.length === 0) && (
                        <span className="text-sm text-muted-foreground">暂无标签</span>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Progress and Stats */}
            <div className="space-y-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">项目进度</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-muted-foreground">整体进度</span>
                      <Tooltip content={progressTrend.label}>
                        <TrendIcon className={`w-4 h-4 ${progressTrend.color}`} />
                      </Tooltip>
                    </div>
                    <span className="text-lg font-semibold">{progressPercentage.toFixed(1)}%</span>
                  </div>
                  <Progress value={progressPercentage} className="h-3" />
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">项目统计</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">总任务数</span>
                    <span className="font-semibold">{project.task_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">已完成任务</span>
                    <span className="font-semibold text-green-600 dark:text-green-400">{project.completed_task_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">测试用例数</span>
                    <span className="font-semibold">{project.test_case_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">通过用例数</span>
                    <span className="font-semibold text-green-600 dark:text-green-400">{project.passed_test_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">发现缺陷数</span>
                    <span className="font-semibold text-red-600 dark:text-red-400">{project.defect_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">团队成员数</span>
                    <span className="font-semibold">{project.team_members?.length || 0}</span>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">成本统计</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">项目预算</span>
                    <span className="font-semibold">
                      {project.budget ? `¥${project.budget.toLocaleString()}` : '未设置'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">实际成本</span>
                    <span className="font-semibold">¥{project.actual_cost.toLocaleString()}</span>
                  </div>
                  {project.budget && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">成本使用率</span>
                      <span className={`font-semibold ${
                        (project.actual_cost / project.budget) > 0.9 ? 'text-red-600 dark:text-red-400' : 
                        (project.actual_cost / project.budget) > 0.7 ? 'text-yellow-600' : 'text-green-600 dark:text-green-400'
                      }`}>
                        {((project.actual_cost / project.budget) * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">团队成员</h3>
              <Button>
                <Users className="w-4 h-4 mr-2" />
                添加成员
              </Button>
            </div>
            <div className="text-center py-12 text-muted-foreground">
              团队管理功能开发中...
            </div>
          </Card>
        </TabsContent>

        {/* Tasks Tab */}
        <TabsContent value="tasks">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">项目任务</h3>
              <Button>
                <Target className="w-4 h-4 mr-2" />
                创建任务
              </Button>
            </div>
            <div className="text-center py-12 text-muted-foreground">
              任务管理功能开发中...
            </div>
          </Card>
        </TabsContent>

        {/* Milestones Tab */}
        <TabsContent value="milestones">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">项目里程碑</h3>
              <Button>
                <Calendar className="w-4 h-4 mr-2" />
                添加里程碑
              </Button>
            </div>
            <div className="text-center py-12 text-muted-foreground">
              里程碑管理功能开发中...
            </div>
          </Card>
        </TabsContent>

        {/* Risks Tab */}
        <TabsContent value="risks">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">项目风险</h3>
              <Button>
                <AlertTriangle className="w-4 h-4 mr-2" />
                添加风险
              </Button>
            </div>
            <div className="text-center py-12 text-muted-foreground">
              风险管理功能开发中...
            </div>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6">项目设置</h3>
            <div className="space-y-6">
              <div>
                <h4 className="font-medium mb-2">危险操作</h4>
                <div className="space-y-2">
                  <Button variant="outline" onClick={() => handleStatusChange('ARCHIVED')}>
                    <Archive className="w-4 h-4 mr-2" />
                    归档项目
                  </Button>
                  <Button variant="destructive" onClick={() => onDelete?.(project)}>
                    <Trash2 className="w-4 h-4 mr-2" />
                    删除项目
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ProjectDetail
