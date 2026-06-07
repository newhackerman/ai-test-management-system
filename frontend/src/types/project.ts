// Project Management Types

export interface Project {
  id: number
  project_code: string
  project_name: string
  description?: string
  project_type:
    | 'BUSINESS_SYSTEM'
    | 'MOBILE_APP'
    | 'API_SERVICE'
    | 'DATA_AI'
    | 'INFRASTRUCTURE'
    | 'INTERNAL_TOOL'
    | 'FUNCTIONAL'
    | 'PERFORMANCE'
    | 'SECURITY'
    | 'AUTOMATION'
    | 'INTEGRATION'
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
  status: 'PLANNING' | 'IN_PROGRESS' | 'ON_HOLD' | 'COMPLETED' | 'CANCELLED' | 'ARCHIVED'
  health_score: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  
  // Time management
  planned_start_date?: string
  planned_end_date?: string
  actual_start_date?: string
  actual_end_date?: string
  
  // Personnel management
  project_manager_id: number
  test_manager_id?: number
  client_contact?: string
  
  // Budget management
  budget?: number
  actual_cost: number
  
  // Progress management
  progress_percentage: number
  task_count: number
  completed_task_count: number
  
  // Quality management
  test_case_count: number
  passed_test_count: number
  defect_count: number
  
  // Metadata
  tags?: string[]
  custom_fields?: Record<string, any>
  
  // Audit fields
  created_by: number
  updated_by?: number
  created_at: string
  updated_at: string
  deleted_at?: string
  
  // Computed fields
  project_manager?: User
  test_manager?: User
  team_members?: ProjectMember[]
  recent_activity?: string
}

export interface ProjectMember {
  id: number
  project_id: number
  user_id: number
  role_in_project: 'ADMIN' | 'PROJECT_MANAGER' | 'REQUIREMENT_MANAGER' | 'DESIGNER' | 'ARCHITECT' | 'DEVELOPER' | 'TESTER' | 'DEVOPS' | 'THIRD_PARTY'
  allocation_percentage: number
  hourly_rate?: number
  join_date: string
  leave_date?: string
  status: 'ACTIVE' | 'INACTIVE' | 'ON_LEAVE'
  skills?: string[]
  responsibilities?: string
  created_at: string
  updated_at: string
  
  // Computed fields
  user?: User
}

export interface Task {
  id: number
  project_id: number
  task_code?: string
  task_name: string
  description?: string
  task_type: 'REQUIREMENT_ANALYSIS' | 'TEST_DESIGN' | 'TEST_EXECUTION' | 'AUTOMATION_DEVELOPMENT' | 'PERFORMANCE_TEST' | 'SECURITY_TEST' | 'ENVIRONMENT_SETUP' | 'DOCUMENTATION'
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
  status: 'TODO' | 'ASSIGNED' | 'IN_PROGRESS' | 'ON_HOLD' | 'BLOCKED' | 'PENDING_REVIEW' | 'COMPLETED' | 'CANCELLED'
  
  // Personnel assignment
  assignee_id?: number
  assignee_ids?: number[]
  reporter_id?: number
  reviewer_id?: number
  
  // Time management
  planned_start_date?: string
  planned_end_date?: string
  actual_start_date?: string
  actual_end_date?: string
  
  // Work hours management
  estimated_hours?: number
  actual_hours: number
  remaining_hours?: number
  
  // Dependencies
  parent_task_id?: number
  dependency_tasks?: number[]
  
  // Quality management
  acceptance_criteria?: string
  test_case_count: number
  defect_count: number
  
  // Metadata
  tags?: string[]
  attachments?: any[]
  
  // Audit fields
  created_by: number
  updated_by?: number
  created_at: string
  updated_at: string
  
  // Computed fields
  assignee?: User
  reporter?: User
  reviewer?: User
}

export interface ProjectFilters {
  search?: string
  status?: Project['status']
  project_type?: Project['project_type']
  priority?: Project['priority']
  risk_level?: Project['risk_level']
  project_manager_id?: number
  created_after?: string
  created_before?: string
  page?: number
  size?: number
  sort?: string
  order?: 'asc' | 'desc'
}

export interface CreateProjectRequest {
  project_name: string
  description?: string
  project_type: Project['project_type']
  priority?: Project['priority']
  planned_start_date?: string
  planned_end_date?: string
  project_manager_id: number
  test_manager_id?: number
  client_contact?: string
  budget?: number
  tags?: string[]
  custom_fields?: Record<string, any>
  team_members?: Array<{
    user_id: number
    role_in_project: ProjectMember['role_in_project']
    allocation_percentage?: number
    responsibilities?: string
  }>
}

export interface UpdateProjectRequest {
  project_name?: string
  description?: string
  project_type?: Project['project_type']
  priority?: Project['priority']
  status?: Project['status']
  planned_start_date?: string
  planned_end_date?: string
  project_manager_id?: number
  test_manager_id?: number
  client_contact?: string
  budget?: number
  tags?: string[]
  custom_fields?: Record<string, any>
}

export interface ProjectProgress {
  project_id: number
  time_progress: {
    progress_rate: number
    deviation: number
    days_elapsed: number
    days_remaining: number
  }
  task_progress: {
    progress_rate: number
    total_tasks: number
    completed_tasks: number
    in_progress_tasks: number
  }
  quality_progress: {
    progress_rate: number
    test_coverage: number
    defect_density: number
    pass_rate: number
  }
  milestone_progress: {
    progress_rate: number
    total_milestones: number
    completed_milestones: number
    overdue_milestones: number
  }
  overall_progress: number
  calculated_at: string
}

export interface ProjectStatistics {
  total_projects: number
  active_projects: number
  completed_projects: number
  overdue_projects: number
  high_risk_projects: number
  project_distribution: Array<{
    status: Project['status']
    count: number
  }>
  type_distribution: Array<{
    type: Project['project_type']
    count: number
  }>
}

// Team Collaboration Types
export interface WorkloadAnalysis {
  member: ProjectMember
  workload: number
  efficiency: number
  status: 'normal' | 'overloaded' | 'underloaded'
}

export interface TeamWorkloadAnalysis {
  project_id: number
  total_members: number
  total_capacity: number
  total_workload: number
  utilization_rate: number
  member_workloads: WorkloadAnalysis[]
  overloaded_members: WorkloadAnalysis[]
  underloaded_members: WorkloadAnalysis[]
  analyzed_at: string
}

export interface MemberRecommendation {
  user_id: number
  user_name: string
  skill_match_score: number
  workload_score: number
  performance_score: number
  overall_score: number
  recommended_role: ProjectMember['role_in_project']
}

// Communication and Collaboration Types
export interface ProjectMessage {
  id: number
  project_id: number
  user_id: number
  content: string
  message_type: 'text' | 'file' | 'image' | 'link'
  reply_to_id?: number
  is_pinned: boolean
  attachments?: Array<{
    id: number
    filename: string
    file_size: number
    file_type: string
    download_url: string
  }>
  mentions?: number[]
  created_at: string
  updated_at: string
  user?: User
  reply_to?: ProjectMessage
  replies?: ProjectMessage[]
}

export interface ProjectDocument {
  id: number
  project_id: number
  name: string
  description?: string
  file_type: string
  file_size: number
  version: string
  status: 'draft' | 'review' | 'approved' | 'archived'
  visibility: 'private' | 'team' | 'public'
  download_url: string
  preview_url?: string
  created_by: number
  updated_by: number
  created_at: string
  updated_at: string
  user?: User
  updater?: User
  versions?: DocumentVersion[]
  permissions?: DocumentPermission[]
}

export interface DocumentVersion {
  id: number
  document_id: number
  version: string
  file_size: number
  download_url: string
  change_log?: string
  created_by: number
  created_at: string
  user?: User
}

export interface DocumentPermission {
  id: number
  document_id: number
  user_id: number
  permission: 'read' | 'write' | 'admin'
  user?: User
}

export interface ProjectNotification {
  id: number
  project_id: number
  user_id: number
  type: 'message' | 'task' | 'document' | 'milestone' | 'member' | 'system'
  title: string
  content: string
  data?: any
  is_read: boolean
  priority: 'low' | 'medium' | 'high' | 'urgent'
  created_at: string
  sender?: User
}

export interface NotificationSettings {
  email_notifications: boolean
  push_notifications: boolean
  message_notifications: boolean
  task_notifications: boolean
  document_notifications: boolean
  milestone_notifications: boolean
  member_notifications: boolean
}

// Import User type from main types
import type { User } from './index'
