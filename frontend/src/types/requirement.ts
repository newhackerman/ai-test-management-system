// 需求管理相关类型定义

export type RequirementType = 'FUNCTIONAL' | 'NON_FUNCTIONAL' | 'CONSTRAINT' | 'INTERFACE'

export type RequirementStatus = 
  | 'DRAFT' 
  | 'PENDING_REVIEW' 
  | 'REVIEWING' 
  | 'NEEDS_REVISION' 
  | 'APPROVED' 
  | 'IN_DEVELOPMENT' 
  | 'PAUSED' 
  | 'TESTING' 
  | 'TEST_FAILED' 
  | 'COMPLETED' 
  | 'DEPLOYED' 
  | 'CLOSED' 
  | 'CANCELLED'

export type Priority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'OPTIONAL'

export type BusinessValue = 'CORE' | 'IMPORTANT' | 'NORMAL' | 'OPTIONAL'

export type Complexity = 'SIMPLE' | 'MEDIUM' | 'COMPLEX' | 'VERY_COMPLEX'

export interface Requirement {
  id: number
  requirement_code: string
  project_id: number
  parent_id?: number
  title: string
  description?: string
  acceptance_criteria?: string
  
  // 分类和属性
  requirement_type: RequirementType
  category?: string
  priority: Priority
  business_value: BusinessValue
  
  // 状态管理
  status: RequirementStatus
  
  // 复杂度和工作量
  complexity?: Complexity
  estimated_effort?: number
  actual_effort?: number
  
  // 人员管理
  creator_id: number
  assignee_id?: number
  reviewer_id?: number
  
  // 时间管理
  planned_start_date?: string
  planned_end_date?: string
  actual_start_date?: string
  actual_end_date?: string
  
  // 质量管理
  quality_score?: number
  completeness_score?: number
  
  // 元数据
  tags?: string[]
  custom_fields?: Record<string, any>
  attachments?: AttachmentInfo[]
  
  // 审计字段
  created_at: string
  updated_at: string
  updated_by?: number
  version: number
  
  // 关联信息
  creator?: {
    id: number
    username: string
    real_name?: string
  }
  assignee?: {
    id: number
    username: string
    real_name?: string
  }
  reviewer?: {
    id: number
    username: string
    real_name?: string
  }
  project?: {
    id: number
    name: string
    project_code: string
  }
}

export interface AttachmentInfo {
  id: string
  name: string
  size: number
  type: string
  url: string
  uploaded_at: string
}

export interface RequirementFilters {
  search?: string
  project_id?: number
  status?: RequirementStatus[]
  priority?: Priority[]
  requirement_type?: RequirementType[]
  category?: string[]
  assignee_id?: number[]
  creator_id?: number[]
  created_after?: string
  created_before?: string
  updated_after?: string
  updated_before?: string
  tags?: string[]
  page?: number
  size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface CreateRequirementRequest {
  project_id: number
  parent_id?: number
  title: string
  description?: string
  acceptance_criteria?: string
  requirement_type: RequirementType
  category?: string
  priority: Priority
  business_value: BusinessValue
  complexity?: Complexity
  estimated_effort?: number
  assignee_id?: number
  reviewer_id?: number
  planned_start_date?: string
  planned_end_date?: string
  tags?: string[]
  custom_fields?: Record<string, any>
}

export interface UpdateRequirementRequest {
  title?: string
  description?: string
  acceptance_criteria?: string
  requirement_type?: RequirementType
  category?: string
  priority?: Priority
  business_value?: BusinessValue
  complexity?: Complexity
  estimated_effort?: number
  assignee_id?: number
  reviewer_id?: number
  planned_start_date?: string
  planned_end_date?: string
  tags?: string[]
  custom_fields?: Record<string, any>
}

export interface RequirementStatusUpdate {
  status: RequirementStatus
  reason?: string
}

export interface RequirementStatistics {
  total_requirements: number
  status_distribution: Record<RequirementStatus, number>
  priority_distribution: Record<Priority, number>
  type_distribution: Record<RequirementType, number>
  completion_rate: number
  average_quality_score: number
  overdue_requirements: number
}

// 需求依赖相关类型
export type DependencyType = 'DEPENDS_ON' | 'BLOCKS' | 'RELATES_TO' | 'CONFLICTS_WITH' | 'DUPLICATES' | 'REPLACES'

export interface RequirementDependency {
  id: number
  source_requirement_id: number
  target_requirement_id: number
  dependency_type: DependencyType
  description?: string
  created_by: number
  created_at: string
  source_requirement?: Requirement
  target_requirement?: Requirement
}

// 需求评审相关类型
export type ReviewType = 'FORMAL' | 'INFORMAL' | 'WALKTHROUGH' | 'INSPECTION'
export type ReviewStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type ReviewDecision = 'APPROVED' | 'APPROVED_WITH_MINOR_CHANGES' | 'NEEDS_MAJOR_REVISION' | 'REJECTED'

export interface RequirementReview {
  id: number
  requirement_id: number
  review_type: ReviewType
  review_status: ReviewStatus
  title: string
  description?: string
  review_criteria?: string
  moderator_id: number
  reviewers: number[]
  scheduled_date?: string
  started_at?: string
  completed_at?: string
  decision?: ReviewDecision
  summary?: string
  created_by: number
  created_at: string
  updated_at: string
}

// 需求变更相关类型
export type ChangeType = 'ADDITION' | 'MODIFICATION' | 'DELETION' | 'CLARIFICATION'
export type ChangeStatus = 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'IMPLEMENTED' | 'CLOSED'
export type ChangePriority = 'EMERGENCY' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface RequirementChangeRequest {
  id: number
  requirement_id: number
  change_request_code: string
  title: string
  description: string
  reason: string
  change_type: ChangeType
  impact_analysis?: string
  effort_estimate?: number
  cost_estimate?: number
  risk_assessment?: string
  status: ChangeStatus
  priority: ChangePriority
  requestor_id: number
  approver_id?: number
  implementer_id?: number
  requested_date: string
  target_date?: string
  approved_date?: string
  implemented_date?: string
  created_at: string
  updated_at: string
}

// API 响应类型
export interface RequirementListResponse {
  data: Requirement[]
  total: number
  page: number
  size: number
  totalPages: number
}

export interface RequirementResponse {
  data: Requirement
}

export interface RequirementStatisticsResponse {
  data: RequirementStatistics
}