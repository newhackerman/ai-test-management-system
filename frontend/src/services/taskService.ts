// @ts-nocheck
import { apiClient } from '@/lib/api-client'
import type { Task } from '@/types/project'
import type { PaginatedResponse, ApiResponse } from '@/types'

export interface TaskFilters {
  search?: string
  project_id?: number
  status?: Task['status'][]
  task_type?: Task['task_type'][]
  priority?: Task['priority'][]
  assignee_id?: number
  reporter_id?: number
  parent_task_id?: number
  planned_start_date_from?: string
  planned_start_date_to?: string
  planned_end_date_from?: string
  planned_end_date_to?: string
  page?: number
  size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface CreateTaskRequest {
  project_id: number
  task_name: string
  description?: string
  task_type: Task['task_type']
  priority?: Task['priority']
  status?: Task['status']
  assignee_id?: number
  assignee_ids?: number[]
  reporter_id?: number
  reviewer_id?: number
  planned_start_date?: string
  planned_end_date?: string
  estimated_hours?: number
  parent_task_id?: number
  dependency_tasks?: number[]
  acceptance_criteria?: string
  tags?: string[]
  attachments?: any[]
}

export interface UpdateTaskRequest {
  task_name?: string
  description?: string
  task_type?: Task['task_type']
  priority?: Task['priority']
  status?: Task['status']
  assignee_id?: number
  assignee_ids?: number[]
  reporter_id?: number
  reviewer_id?: number
  planned_start_date?: string
  planned_end_date?: string
  actual_start_date?: string
  actual_end_date?: string
  estimated_hours?: number
  actual_hours?: number
  remaining_hours?: number
  parent_task_id?: number
  dependency_tasks?: number[]
  acceptance_criteria?: string
  tags?: string[]
  attachments?: any[]
}

export interface TaskStatusUpdateRequest {
  status: Task['status']
  reason?: string
}

export interface TaskAssignmentRequest {
  assignee_id?: number
  assignee_ids?: number[]
  reason?: string
  comment?: string
}

export interface TaskProgressUpdateRequest {
  actual_hours?: number
  remaining_hours?: number
  progress_notes?: string
  issues_encountered?: string
}

export interface TaskDependencyRequest {
  dependency_tasks: number[]
}

export interface TaskStatistics {
  total_tasks: number
  status_distribution: Array<{
    status: Task['status']
    count: number
  }>
  type_distribution: Array<{
    type: Task['task_type']
    count: number
  }>
  priority_distribution: Array<{
    priority: Task['priority']
    count: number
  }>
  overdue_tasks: number
  completed_on_time: number
  average_completion_time: number
}

export class TaskService {
  private static readonly BASE_URL = '/api/v1/tasks'

  private static unwrapTask(response: any): Task {
    return response?.data || response?.task || response
  }

  /**
   * Get tasks with filters and pagination
   */
  static async getTasks(filters?: TaskFilters): Promise<PaginatedResponse<Task>> {
    const params = new URLSearchParams()
    
    if (filters?.search) params.append('search', filters.search)
    if (filters?.project_id) params.append('project_id', filters.project_id.toString())
    if (filters?.status) {
      filters.status.forEach(status => params.append('status', status))
    }
    if (filters?.task_type) {
      filters.task_type.forEach(type => params.append('task_type', type))
    }
    if (filters?.priority) {
      filters.priority.forEach(priority => params.append('priority', priority))
    }
    if (filters?.assignee_id) params.append('assignee_id', filters.assignee_id.toString())
    if (filters?.reporter_id) params.append('reporter_id', filters.reporter_id.toString())
    if (filters?.parent_task_id) params.append('parent_task_id', filters.parent_task_id.toString())
    if (filters?.planned_start_date_from) params.append('planned_start_date_from', filters.planned_start_date_from)
    if (filters?.planned_start_date_to) params.append('planned_start_date_to', filters.planned_start_date_to)
    if (filters?.planned_end_date_from) params.append('planned_end_date_from', filters.planned_end_date_from)
    if (filters?.planned_end_date_to) params.append('planned_end_date_to', filters.planned_end_date_to)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('size', filters.size.toString())
    if (filters?.sort_by) params.append('sort_by', filters.sort_by)
    if (filters?.sort_order) params.append('sort_order', filters.sort_order)

    const queryString = params.toString()
    const url = queryString ? `${this.BASE_URL}?${queryString}` : this.BASE_URL

    const response: any = await apiClient.get<PaginatedResponse<Task>>(url)
    if (Array.isArray(response?.data)) return response

    const tasks = response?.tasks || response?.items || []
    return {
      data: tasks,
      total: response?.total || tasks.length,
      page: response?.page || filters?.page || 1,
      size: response?.size || filters?.size || 20,
      totalPages: response?.totalPages || response?.total_pages || 1,
    }
  }

  /**
   * Get task by ID
   */
  static async getTask(id: number): Promise<Task> {
    const response = await apiClient.get<ApiResponse<Task>>(`${this.BASE_URL}/${id}`)
    return this.unwrapTask(response)
  }

  /**
   * Create new task
   */
  static async createTask(data: CreateTaskRequest): Promise<Task> {
    const response = await apiClient.post<ApiResponse<Task>>(this.BASE_URL, data)
    return this.unwrapTask(response)
  }

  /**
   * Update task
   */
  static async updateTask(id: number, data: UpdateTaskRequest): Promise<Task> {
    const response = await apiClient.put<ApiResponse<Task>>(`${this.BASE_URL}/${id}`, data)
    return this.unwrapTask(response)
  }

  /**
   * Delete task
   */
  static async deleteTask(id: number): Promise<void> {
    await apiClient.delete(`${this.BASE_URL}/${id}`)
  }

  /**
   * Update task status
   */
  static async updateTaskStatus(id: number, data: TaskStatusUpdateRequest): Promise<Task> {
    const response = await apiClient.post<ApiResponse<Task>>(`${this.BASE_URL}/${id}/status`, data)
    return this.unwrapTask(response)
  }

  /**
   * Assign task
   */
  static async assignTask(id: number, data: TaskAssignmentRequest): Promise<Task> {
    const response = await apiClient.post<ApiResponse<Task>>(`${this.BASE_URL}/${id}/assign`, data)
    return this.unwrapTask(response)
  }

  /**
   * Update task progress
   */
  static async updateTaskProgress(id: number, data: TaskProgressUpdateRequest): Promise<Task> {
    const response = await apiClient.post<ApiResponse<Task>>(`${this.BASE_URL}/${id}/progress`, data)
    return this.unwrapTask(response)
  }

  /**
   * Set task dependencies
   */
  static async setTaskDependencies(id: number, data: TaskDependencyRequest): Promise<Task> {
    const response = await apiClient.post<ApiResponse<Task>>(`${this.BASE_URL}/${id}/dependencies`, data)
    return this.unwrapTask(response)
  }

  /**
   * Get task dependencies
   */
  static async getTaskDependencies(id: number): Promise<any> {
    const response = await apiClient.get(`${this.BASE_URL}/${id}/dependencies`)
    return response.data
  }

  /**
   * Validate task dependencies
   */
  static async validateTaskDependencies(id: number, data: TaskDependencyRequest): Promise<{
    valid: boolean
    has_circular_dependency: boolean
    message: string
  }> {
    const response = await apiClient.post(`${this.BASE_URL}/${id}/dependencies/validate`, data)
    return response.data
  }

  /**
   * Get project task statistics
   */
  static async getTaskStatistics(projectId: number): Promise<TaskStatistics> {
    const response: any = await apiClient.get<ApiResponse<TaskStatistics>>(`/api/v1/projects/${projectId}/tasks/statistics`)
    return response?.data || response
  }

  /**
   * Get project critical path
   */
  static async getProjectCriticalPath(projectId: number): Promise<any> {
    const response = await apiClient.get(`/api/v1/projects/${projectId}/critical-path`)
    return response.data
  }

  /**
   * Activate ready tasks
   */
  static async activateReadyTasks(projectId: number): Promise<{
    success: boolean
    message: string
    activated_tasks: any[]
    activated_at: string
  }> {
    const response = await apiClient.post(`/api/v1/projects/${projectId}/tasks/activate`)
    return response.data
  }
}

export default TaskService
