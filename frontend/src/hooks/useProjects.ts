import { useState, useEffect, useCallback } from 'react'
import { useToast } from '@/hooks/useToast'
import ProjectService from '@/services/projectService'
import type { 
  Project, 
  ProjectFilters, 
  CreateProjectRequest, 
  UpdateProjectRequest,
  ProjectProgress,
  ProjectStatistics
} from '@/types/project'
import type { PaginatedResponse } from '@/types'

interface UseProjectsOptions {
  initialFilters?: ProjectFilters
  autoLoad?: boolean
}

interface UseProjectsReturn {
  // Data
  projects: Project[]
  totalProjects: number
  currentPage: number
  totalPages: number
  statistics: ProjectStatistics | null
  
  // Loading states
  loading: boolean
  creating: boolean
  updating: boolean
  deleting: boolean
  
  // Error states
  error: string | null
  
  // Actions
  loadProjects: (filters?: ProjectFilters) => Promise<void>
  createProject: (data: CreateProjectRequest) => Promise<Project | null>
  updateProject: (id: number, data: UpdateProjectRequest) => Promise<Project | null>
  deleteProject: (id: number) => Promise<boolean>
  duplicateProject: (id: number, newName?: string) => Promise<Project | null>
  updateProjectStatus: (id: number, status: Project['status'], reason?: string) => Promise<Project | null>
  exportProject: (id: number, format?: 'pdf' | 'excel' | 'csv') => Promise<boolean>
  refreshProjects: () => Promise<void>
  loadStatistics: () => Promise<void>
  
  // Filter management
  filters: ProjectFilters
  setFilters: (filters: ProjectFilters) => void
  clearFilters: () => void
}

export const useProjects = (options: UseProjectsOptions = {}): UseProjectsReturn => {
  const { initialFilters = {}, autoLoad = true } = options
  const { toast } = useToast()

  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [totalProjects, setTotalProjects] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statistics, setStatistics] = useState<ProjectStatistics | null>(null)
  const [filters, setFilters] = useState<ProjectFilters>(initialFilters)
  
  // Loading states
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  
  // Error state
  const [error, setError] = useState<string | null>(null)

  // Load projects
  const loadProjects = useCallback(async (newFilters?: ProjectFilters) => {
    try {
      setLoading(true)
      setError(null)
      
      const filtersToUse = newFilters || filters
      const response: PaginatedResponse<Project> = await ProjectService.getProjects(filtersToUse)
      
      setProjects(response.data)
      setTotalProjects(response.total)
      setCurrentPage(response.page)
      setTotalPages(response.totalPages)
      
      if (newFilters) {
        setFilters(newFilters)
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '加载项目失败'
      setError(errorMessage)
      toast({
        title: '加载失败',
        description: errorMessage,
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }, [filters, toast])

  // Create project
  const createProject = useCallback(async (data: CreateProjectRequest): Promise<Project | null> => {
    try {
      setCreating(true)
      setError(null)
      
      const newProject = await ProjectService.createProject(data)
      
      // Add to local state
      setProjects(prev => [newProject, ...prev])
      setTotalProjects(prev => prev + 1)
      
      toast({
        title: '创建成功',
        description: `项目 "${newProject.project_name}" 已创建`
      })
      
      return newProject
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '创建项目失败'
      setError(errorMessage)
      toast({
        title: '创建失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return null
    } finally {
      setCreating(false)
    }
  }, [toast])

  // Update project
  const updateProject = useCallback(async (id: number, data: UpdateProjectRequest): Promise<Project | null> => {
    try {
      setUpdating(true)
      setError(null)
      
      const updatedProject = await ProjectService.updateProject(id, data)
      
      // Update local state
      setProjects(prev => prev.map(p => p.id === id ? updatedProject : p))
      
      toast({
        title: '更新成功',
        description: `项目 "${updatedProject.project_name}" 已更新`
      })
      
      return updatedProject
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '更新项目失败'
      setError(errorMessage)
      toast({
        title: '更新失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return null
    } finally {
      setUpdating(false)
    }
  }, [toast])

  // Delete project
  const deleteProject = useCallback(async (id: number): Promise<boolean> => {
    try {
      setDeleting(true)
      setError(null)
      
      const project = projects.find(p => p.id === id)
      await ProjectService.deleteProject(id)
      
      // Remove from local state
      setProjects(prev => prev.filter(p => p.id !== id))
      setTotalProjects(prev => prev - 1)
      
      toast({
        title: '删除成功',
        description: `项目 "${project?.project_name}" 已删除`
      })
      
      return true
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '删除项目失败'
      setError(errorMessage)
      toast({
        title: '删除失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return false
    } finally {
      setDeleting(false)
    }
  }, [projects, toast])

  // Duplicate project
  const duplicateProject = useCallback(async (id: number, newName?: string): Promise<Project | null> => {
    try {
      setCreating(true)
      setError(null)
      
      const duplicatedProject = await ProjectService.duplicateProject(id, newName)
      
      // Add to local state
      setProjects(prev => [duplicatedProject, ...prev])
      setTotalProjects(prev => prev + 1)
      
      toast({
        title: '复制成功',
        description: `项目 "${duplicatedProject.project_name}" 已创建`
      })
      
      return duplicatedProject
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '复制项目失败'
      setError(errorMessage)
      toast({
        title: '复制失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return null
    } finally {
      setCreating(false)
    }
  }, [toast])

  // Update project status
  const updateProjectStatus = useCallback(async (id: number, status: Project['status'], reason?: string): Promise<Project | null> => {
    try {
      setUpdating(true)
      setError(null)
      
      const updatedProject = await ProjectService.updateProjectStatus(id, status, reason)
      
      // Update local state
      setProjects(prev => prev.map(p => p.id === id ? updatedProject : p))
      
      toast({
        title: '状态更新成功',
        description: `项目状态已更新为 "${status}"`
      })
      
      return updatedProject
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '更新状态失败'
      setError(errorMessage)
      toast({
        title: '状态更新失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return null
    } finally {
      setUpdating(false)
    }
  }, [toast])

  // Export project
  const exportProject = useCallback(async (id: number, format: 'pdf' | 'excel' | 'csv' = 'pdf'): Promise<boolean> => {
    try {
      setError(null)
      
      const project = projects.find(p => p.id === id)
      const blob = await ProjectService.exportProject(id, format)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${project?.project_name || 'project'}_report.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      toast({
        title: '导出成功',
        description: `项目报告已导出为 ${format.toUpperCase()} 格式`
      })
      
      return true
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || '导出失败'
      setError(errorMessage)
      toast({
        title: '导出失败',
        description: errorMessage,
        variant: 'destructive'
      })
      return false
    }
  }, [projects, toast])

  // Load statistics
  const loadStatistics = useCallback(async () => {
    try {
      const stats = await ProjectService.getProjectStatistics()
      setStatistics(stats)
    } catch (err: any) {
      console.error('Failed to load project statistics:', err)
    }
  }, [])

  // Refresh projects
  const refreshProjects = useCallback(async () => {
    await loadProjects()
  }, [loadProjects])

  // Clear filters
  const clearFilters = useCallback(() => {
    const clearedFilters: ProjectFilters = {}
    setFilters(clearedFilters)
    loadProjects(clearedFilters)
  }, [loadProjects])

  // Auto load on mount
  useEffect(() => {
    if (autoLoad) {
      loadProjects()
      loadStatistics()
    }
  }, [autoLoad, loadProjects, loadStatistics])

  return {
    // Data
    projects,
    totalProjects,
    currentPage,
    totalPages,
    statistics,
    
    // Loading states
    loading,
    creating,
    updating,
    deleting,
    
    // Error state
    error,
    
    // Actions
    loadProjects,
    createProject,
    updateProject,
    deleteProject,
    duplicateProject,
    updateProjectStatus,
    exportProject,
    refreshProjects,
    loadStatistics,
    
    // Filter management
    filters,
    setFilters,
    clearFilters
  }
}

export default useProjects