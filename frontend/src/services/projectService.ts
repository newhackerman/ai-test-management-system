// @ts-nocheck
import { apiClient } from '@/lib/api-client'
import type { 
  Project, 
  ProjectFilters, 
  CreateProjectRequest, 
  UpdateProjectRequest,
  ProjectProgress,
  ProjectStatistics
} from '@/types/project'
import type { PaginatedResponse, ApiResponse } from '@/types'

export class ProjectService {
  private static readonly BASE_URL = '/api/v1/projects'

  private static unwrapProjectResponse(response: any): Project {
    return response?.data || response?.project || response
  }

  private static unwrapResponse(response: any): any {
    return response?.data ?? response
  }

  /**
   * Get projects with filters and pagination
   */
  static async getProjects(filters?: ProjectFilters): Promise<PaginatedResponse<Project>> {
    const params = new URLSearchParams()
    
    if (filters?.search) params.append('search', filters.search)
    if (filters?.status) params.append('status', filters.status)
    if (filters?.project_type) params.append('project_type', filters.project_type)
    if (filters?.priority) params.append('priority', filters.priority)
    if (filters?.risk_level) params.append('risk_level', filters.risk_level)
    if (filters?.project_manager_id) params.append('project_manager_id', filters.project_manager_id.toString())
    if (filters?.created_after) params.append('created_after', filters.created_after)
    if (filters?.created_before) params.append('created_before', filters.created_before)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('size', filters.size.toString())
    if (filters?.sort) params.append('sort_by', filters.sort)
    if (filters?.order) params.append('sort_order', filters.order)

    const queryString = params.toString()
    const url = queryString ? `${this.BASE_URL}?${queryString}` : this.BASE_URL

    const response: any = await apiClient.get(url)
    const payload = response?.data ?? response
    if (Array.isArray(payload)) {
      return {
        data: payload,
        total: payload.length,
        page: filters?.page || 1,
        size: filters?.size || payload.length,
        totalPages: 1,
      }
    }

    return {
      data: payload.projects || payload.data || [],
      total: payload.total || 0,
      page: payload.page || 1,
      size: payload.size || filters?.size || 20,
      totalPages: payload.totalPages || payload.total_pages || 1
    }
  }

  /**
   * Get project by ID
   */
  static async getProject(id: number): Promise<Project> {
    const response: any = await apiClient.get(`${this.BASE_URL}/${id}`)
    return this.unwrapProjectResponse(response)
  }

  /**
   * Create new project
   */
  static async createProject(data: CreateProjectRequest): Promise<Project> {
    const response: any = await apiClient.post(this.BASE_URL, data)
    return this.unwrapProjectResponse(response)
  }

  /**
   * Update project
   */
  static async updateProject(id: number, data: UpdateProjectRequest): Promise<Project> {
    const response: any = await apiClient.put(`${this.BASE_URL}/${id}`, data)
    return this.unwrapProjectResponse(response)
  }

  /**
   * Delete project (soft delete)
   */
  static async deleteProject(id: number): Promise<void> {
    await apiClient.delete(`${this.BASE_URL}/${id}`)
  }

  /**
   * Update project status
   */
  static async updateProjectStatus(id: number, status: Project['status'], reason?: string): Promise<Project> {
    const response: any = await apiClient.post(`${this.BASE_URL}/${id}/status`, null, {
      params: { new_status: status, reason }
    })
    return this.unwrapProjectResponse(response)
  }

  /**
   * Get project progress
   */
  static async getProjectProgress(id: number): Promise<ProjectProgress> {
    const response: any = await apiClient.get(`${this.BASE_URL}/${id}/progress`)
    return response?.data || response
  }

  /**
   * Get project statistics
   */
  static async getProjectStatistics(): Promise<ProjectStatistics> {
    const response: any = await apiClient.get(`${this.BASE_URL}/statistics`)
    return response?.data || response
  }

  /**
   * Export project report
   */
  static async exportProject(id: number, format: 'pdf' | 'excel' | 'csv' = 'pdf'): Promise<Blob> {
    return await apiClient.get(`${this.BASE_URL}/${id}/export`, {
      params: { format },
      responseType: 'blob'
    })
  }

  /**
   * Duplicate project
   */
  static async duplicateProject(id: number, newName?: string): Promise<Project> {
    const response: any = await apiClient.post<ApiResponse<Project>>(`${this.BASE_URL}/${id}/duplicate`, {
      project_name: newName
    })
    return response?.data || response?.project || response
  }

  /**
   * Archive project
   */
  static async archiveProject(id: number): Promise<Project> {
    const response: any = await apiClient.patch<ApiResponse<Project>>(`${this.BASE_URL}/${id}/archive`)
    return response?.data || response?.project || response
  }

  /**
   * Restore archived project
   */
  static async restoreProject(id: number): Promise<Project> {
    const response: any = await apiClient.patch<ApiResponse<Project>>(`${this.BASE_URL}/${id}/restore`)
    return response?.data || response?.project || response
  }

  /**
   * Get project team members
   */
  static async getProjectMembers(id: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${id}/members`)
    return this.unwrapResponse(response)
  }

  /**
   * Add team member to project
   */
  static async addProjectMember(id: number, memberData: {
    user_id: number
    role_in_project: string
    allocation_percentage?: number
    responsibilities?: string
  }) {
    const response = await apiClient.post(`${this.BASE_URL}/${id}/members`, memberData)
    return this.unwrapResponse(response)
  }

  /**
   * Remove team member from project
   */
  static async removeProjectMember(projectId: number, memberId: number) {
    await apiClient.delete(`${this.BASE_URL}/${projectId}/members/${memberId}`)
  }

  /**
   * Update team member role or allocation
   */
  static async updateProjectMember(projectId: number, memberId: number, data: {
    role_in_project?: string
    allocation_percentage?: number
    responsibilities?: string
  }) {
    const response = await apiClient.put(`${this.BASE_URL}/${projectId}/members/${memberId}`, data)
    return this.unwrapResponse(response)
  }

  /**
   * Get project tasks
   */
  static async getProjectTasks(id: number, filters?: {
    status?: string
    assignee_id?: number
    task_type?: string
    page?: number
    size?: number
  }) {
    const params = new URLSearchParams()
    if (filters?.status) params.append('status', filters.status)
    if (filters?.assignee_id) params.append('assignee_id', filters.assignee_id.toString())
    if (filters?.task_type) params.append('task_type', filters.task_type)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('size', filters.size.toString())

    const queryString = params.toString()
    const url = queryString ? `${this.BASE_URL}/${id}/tasks?${queryString}` : `${this.BASE_URL}/${id}/tasks`

    const response = await apiClient.get(url)
    return this.unwrapResponse(response)
  }

  /**
   * Get project milestones
   */
  static async getProjectMilestones(id: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${id}/milestones`)
    return this.unwrapResponse(response)
  }

  /**
   * Get project risks
   */
  static async getProjectRisks(id: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${id}/risks`)
    return this.unwrapResponse(response)
  }

  /**
   * Get project activity log
   */
  static async getProjectActivity(id: number, page = 1, size = 20) {
    const response = await apiClient.get(`${this.BASE_URL}/${id}/activity`, {
      params: { page, size }
    })
    return this.unwrapResponse(response)
  }

  /**
   * Invite member by email
   */
  static async inviteMemberByEmail(projectId: number, inviteData: {
    email: string
    role_in_project: string
    allocation_percentage?: number
    responsibilities?: string
    welcome_message?: string
  }) {
    const response = await apiClient.post(`${this.BASE_URL}/${projectId}/members/invite`, inviteData)
    return this.unwrapResponse(response)
  }

  /**
   * Get team workload analysis
   */
  static async getTeamWorkloadAnalysis(projectId: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/members/workload`)
    return this.unwrapResponse(response)
  }

  /**
   * Get team statistics
   */
  static async getTeamStatistics(projectId: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/members/statistics`)
    return this.unwrapResponse(response)
  }

  /**
   * Recommend team members
   */
  static async recommendTeamMembers(projectId: number, skillRequirements: {
    required_skills: string[]
    project_type?: string
    experience_level?: string
  }) {
    const response = await apiClient.post(`${this.BASE_URL}/${projectId}/members/recommend`, skillRequirements)
    return this.unwrapResponse(response)
  }

  /**
   * Get project messages/discussions
   */
  static async getProjectMessages(projectId: number, page = 1, size = 20) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/messages`, {
      params: { page, size }
    })
    return this.unwrapResponse(response)
  }

  /**
   * Send project message
   */
  static async sendProjectMessage(projectId: number, messageData: {
    content: string
    message_type?: string
    reply_to_id?: number
    attachments?: any[]
  }) {
    const response = await apiClient.post(`${this.BASE_URL}/${projectId}/messages`, messageData)
    return this.unwrapResponse(response)
  }

  /**
   * Update project message
   */
  static async updateProjectMessage(projectId: number, messageId: number, data: {
    content: string
  }) {
    const response = await apiClient.put(`${this.BASE_URL}/${projectId}/messages/${messageId}`, data)
    return this.unwrapResponse(response)
  }

  /**
   * Delete project message
   */
  static async deleteProjectMessage(projectId: number, messageId: number) {
    await apiClient.delete(`${this.BASE_URL}/${projectId}/messages/${messageId}`)
  }

  /**
   * Pin/unpin project message
   */
  static async toggleMessagePin(projectId: number, messageId: number) {
    const response = await apiClient.patch(`${this.BASE_URL}/${projectId}/messages/${messageId}/pin`)
    return this.unwrapResponse(response)
  }

  /**
   * Get project documents
   */
  static async getProjectDocuments(projectId: number, page = 1, size = 20) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/documents`, {
      params: { page, size }
    })
    return this.unwrapResponse(response)
  }

  /**
   * Upload project document
   */
  static async uploadProjectDocument(projectId: number, documentData: {
    name: string
    description?: string
    visibility: string
    file: File
  }) {
    const formData = new FormData()
    formData.append('name', documentData.name)
    if (documentData.description) {
      formData.append('description', documentData.description)
    }
    formData.append('visibility', documentData.visibility)
    formData.append('file', documentData.file)

    const response = await apiClient.post(`${this.BASE_URL}/${projectId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return this.unwrapResponse(response)
  }

  /**
   * Delete project document
   */
  static async deleteProjectDocument(projectId: number, documentId: number) {
    await apiClient.delete(`${this.BASE_URL}/${projectId}/documents/${documentId}`)
  }

  /**
   * Get project notifications
   */
  static async getProjectNotifications(projectId: number, page = 1, size = 20) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/notifications`, {
      params: { page, size }
    })
    return this.unwrapResponse(response)
  }

  /**
   * Get project notification settings for current user
   */
  static async getProjectNotificationSettings(projectId: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/notifications/settings`)
    return this.unwrapResponse(response)
  }

  /**
   * Update project notification settings for current user
   */
  static async updateProjectNotificationSettings(projectId: number, settings: Record<string, any>) {
    const response = await apiClient.put(`${this.BASE_URL}/${projectId}/notifications/settings`, settings)
    return this.unwrapResponse(response)
  }

  /**
   * Mark notification as read
   */
  static async markNotificationAsRead(projectId: number, notificationIds: number[]) {
    const response = await apiClient.patch(`${this.BASE_URL}/${projectId}/notifications/read`, {
      notification_ids: notificationIds
    })
    return this.unwrapResponse(response)
  }

  /**
   * Delete project notification
   */
  static async deleteProjectNotification(projectId: number, notificationId: number) {
    await apiClient.delete(`${this.BASE_URL}/${projectId}/notifications/${notificationId}`)
  }

  /**
   * Get unread notification count
   */
  static async getUnreadNotificationCount(projectId: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/notifications/unread-count`)
    return this.unwrapResponse(response)
  }

  /**
   * Get unread message count
   */
  static async getUnreadMessageCount(projectId: number) {
    const response = await apiClient.get(`${this.BASE_URL}/${projectId}/messages/unread-count`)
    return this.unwrapResponse(response)
  }
}

export default ProjectService
