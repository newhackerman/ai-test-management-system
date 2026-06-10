// @ts-nocheck
import React, { useState } from 'react'
import { Calendar, Copy, Download, Edit, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import ProjectCreateModal from '@/components/projects/ProjectCreateModal'
import { useProjects } from '@/hooks/useProjects'
import type { CreateProjectRequest, Project, UpdateProjectRequest } from '@/types/project'
import { getProjectPriorityLabel } from '@/utils/projectPriority'
import { getProjectTypeLabel } from '@/utils/projectType'

const statusLabels: Record<string, string> = {
  PLANNING: '规划中',
  IN_PROGRESS: '进行中',
  ON_HOLD: '已暂停',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  ARCHIVED: '已归档',
}

const Projects: React.FC = () => {
  const {
    projects,
    loading,
    error,
    filters,
    setFilters,
    createProject,
    updateProject,
    deleteProject,
    duplicateProject,
    exportProject,
    refreshProjects,
    creating,
    updating,
  } = useProjects()
  const [search, setSearch] = useState(filters.search || '')
  const [projectModalOpen, setProjectModalOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [modalError, setModalError] = useState('')

  const handleSearch = () => {
    setFilters({ ...filters, search })
  }

  const handleDelete = async (project: Project) => {
    if (window.confirm(`确定要删除项目“${project.project_name}”吗？`)) {
      await deleteProject(project.id)
    }
  }

  const openCreateModal = () => {
    setEditingProject(null)
    setModalError('')
    setProjectModalOpen(true)
  }

  const openEditModal = (project: Project) => {
    setEditingProject(project)
    setModalError('')
    setProjectModalOpen(true)
  }

  const handleModalClose = () => {
    setProjectModalOpen(false)
    setEditingProject(null)
    setModalError('')
  }

  const handleProjectSubmit = async (data: CreateProjectRequest) => {
    setModalError('')
    if (editingProject) {
      const updateData: UpdateProjectRequest = {
        project_name: data.project_name,
        description: data.description,
        project_type: data.project_type,
        priority: data.priority,
        planned_start_date: data.planned_start_date,
        planned_end_date: data.planned_end_date,
        project_manager_id: data.project_manager_id,
        test_manager_id: data.test_manager_id,
        client_contact: data.client_contact,
        budget: data.budget,
        tags: data.tags,
        custom_fields: data.custom_fields,
      }
      const updated = await updateProject(editingProject.id, updateData)
      if (!updated) {
        setModalError('项目更新失败，请检查必填项和日期设置。')
        throw new Error('update failed')
      }
    } else {
      const created = await createProject({
        ...data,
        project_manager_id: data.project_manager_id || Number(userIdFromStorage() || 1),
      })
      if (!created) {
        setModalError('项目创建失败，请检查必填项和日期设置。')
        throw new Error('create failed')
      }
    }
    handleModalClose()
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">项目管理</h1>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="mr-2 h-4 w-4" />
          新建项目
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && handleSearch()}
                placeholder="搜索项目名称、描述或标签"
                className="pl-10"
              />
            </div>
            <Button variant="outline" onClick={handleSearch}>搜索</Button>
            <Button variant="outline" onClick={refreshProjects} disabled={loading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              刷新
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[260px]">项目</TableHead>
                <TableHead className="w-24">状态</TableHead>
                <TableHead className="w-32">类型</TableHead>
                <TableHead className="w-24">优先级</TableHead>
                <TableHead className="w-28">进度</TableHead>
                <TableHead className="w-28">预算</TableHead>
                <TableHead className="w-52">周期</TableHead>
                <TableHead className="w-56 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && projects.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">加载中...</TableCell>
                </TableRow>
              ) : projects.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">暂无项目数据</TableCell>
                </TableRow>
              ) : (
                projects.map((project) => (
                  <TableRow key={project.id}>
                    <TableCell>
                      <div className="font-medium text-foreground">{project.project_name}</div>
                      <div className="text-xs text-muted-foreground">{project.project_code || `#${project.id}`}</div>
                      <div className="mt-1 line-clamp-1 max-w-xl text-xs text-muted-foreground">{project.description || '暂无描述'}</div>
                    </TableCell>
                    <TableCell><Badge>{statusLabels[project.status] || project.status}</Badge></TableCell>
                    <TableCell>{getProjectTypeLabel(project.project_type)}</TableCell>
                    <TableCell>{getProjectPriorityLabel(project.priority)}</TableCell>
                    <TableCell>{project.progress_percentage || 0}%</TableCell>
                    <TableCell>{project.budget ? `¥${project.budget}` : '-'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        <span>{project.planned_start_date || '-'} 至 {project.planned_end_date || '-'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="outline" onClick={() => openEditModal(project)}>
                          <Edit className="mr-1 h-3 w-3" />
                          编辑
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => duplicateProject(project.id, `${project.project_name} - 副本`)}>
                          <Copy className="mr-1 h-3 w-3" />
                          复制
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => exportProject(project.id, 'csv')} title="导出">
                          <Download className="h-3 w-3" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(project)} title="删除">
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <ProjectCreateModal
        open={projectModalOpen}
        onClose={handleModalClose}
        onSubmit={handleProjectSubmit}
        editProject={editingProject}
        loading={creating || updating}
        currentUserId={Number(userIdFromStorage() || 1)}
        currentUserName={userNameFromStorage()}
        submitError={modalError}
      />
    </div>
  )
}

const userIdFromStorage = () => {
  try {
    return JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.user?.id ||
      JSON.parse(localStorage.getItem('auth-user') || '{}')?.id
  } catch {
    return 1
  }
}

const userNameFromStorage = () => {
  try {
    const persisted = JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.user
    const direct = JSON.parse(localStorage.getItem('auth-user') || '{}')
    return persisted?.real_name || persisted?.username || direct?.real_name || direct?.username || '当前用户'
  } catch {
    return '当前用户'
  }
}

export default Projects
