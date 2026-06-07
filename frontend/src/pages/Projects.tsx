// @ts-nocheck
import React, { useState } from 'react'
import { Calendar, Copy, Download, Edit, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">项目管理</h1>
          <p className="mt-2 text-gray-600">查看项目列表，执行刷新、复制、导出和删除操作。</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="mr-2 h-4 w-4" />
          新建项目
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
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

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {loading && projects.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-gray-500">加载中...</CardContent>
          </Card>
        ) : projects.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-gray-500">暂无项目数据</CardContent>
          </Card>
        ) : (
          projects.map((project) => (
            <Card key={project.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg">{project.project_name}</CardTitle>
                    <p className="mt-1 text-sm text-gray-500">{project.project_code || `#${project.id}`}</p>
                  </div>
                  <Badge>{statusLabels[project.status] || project.status}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-gray-600">{project.description || '暂无描述'}</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Info label="类型" value={getProjectTypeLabel(project.project_type)} />
                  <Info label="优先级" value={getProjectPriorityLabel(project.priority)} />
                  <Info label="进度" value={`${project.progress_percentage || 0}%`} />
                  <Info label="预算" value={project.budget ? `¥${project.budget}` : '-'} />
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Calendar className="h-4 w-4" />
                  <span>{project.planned_start_date || '-'} 至 {project.planned_end_date || '-'}</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button size="sm" variant="outline" onClick={() => openEditModal(project)}>
                    <Edit className="mr-1 h-3 w-3" />
                    编辑
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => duplicateProject(project.id, `${project.project_name} - 副本`)}>
                    <Copy className="mr-1 h-3 w-3" />
                    复制
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => exportProject(project.id, 'csv')}>
                    <Download className="mr-1 h-3 w-3" />
                    导出
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => handleDelete(project)}>
                    <Trash2 className="mr-1 h-3 w-3" />
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

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

const Info = ({ label, value }: { label: string; value: string }) => (
  <div>
    <div className="text-gray-500">{label}</div>
    <div className="font-medium text-gray-900">{value}</div>
  </div>
)

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
