// 测试管理模块类型定义

export interface TestPlan {
  id: number
  plan_code: string
  project_id: number
  plan_name: string
  description?: string
  test_type: TestType
  test_strategy?: string
  test_scope?: string
  status: TestPlanStatus
  planned_start_date?: string
  planned_end_date?: string
  actual_start_date?: string
  actual_end_date?: string
  test_manager_id: number
  created_by: number
  total_cases: number
  executed_cases: number
  passed_cases: number
  failed_cases: number
  pass_rate?: number
  execution_rate?: number
  created_at: string
  updated_at: string
}

export enum TestType {
  FUNCTIONAL = 'FUNCTIONAL',
  PERFORMANCE = 'PERFORMANCE',
  SECURITY = 'SECURITY',
  INTEGRATION = 'INTEGRATION',
  REGRESSION = 'REGRESSION',
  ACCEPTANCE = 'ACCEPTANCE'
}

export enum TestPlanStatus {
  DRAFT = 'DRAFT',
  APPROVED = 'APPROVED',
  IN_PROGRESS = 'IN_PROGRESS',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  CANCELLED = 'CANCELLED'
}

export interface TestCase {
  id: number
  case_code: string
  test_plan_id?: number
  requirement_id?: number
  case_title: string
  case_description?: string
  case_type: TestCaseType
  module?: string
  priority: Priority
  complexity: Complexity
  automation_level: AutomationLevel
  preconditions?: string
  test_steps: TestStep[]
  expected_result?: string
  test_data?: any
  status: TestCaseStatus
  creator_id: number
  assignee_id?: number
  reviewer_id?: number
  tags?: string[]
  attachments?: any[]
  created_at: string
  updated_at: string
  version: number
}

export enum TestCaseType {
  FUNCTIONAL = 'FUNCTIONAL',
  NON_FUNCTIONAL = 'NON_FUNCTIONAL',
  INTEGRATION = 'INTEGRATION',
  SYSTEM = 'SYSTEM',
  ACCEPTANCE = 'ACCEPTANCE',
  REGRESSION = 'REGRESSION',
  SMOKE = 'SMOKE',
  PERFORMANCE = 'PERFORMANCE',
  SECURITY = 'SECURITY',
  USABILITY = 'USABILITY'
}

export enum TestCaseStatus {
  DRAFT = 'DRAFT',
  APPROVED = 'APPROVED',
  ACTIVE = 'ACTIVE',
  DEPRECATED = 'DEPRECATED',
  ARCHIVED = 'ARCHIVED'
}

export enum Priority {
  CRITICAL = 'CRITICAL',
  HIGH = 'HIGH',
  MEDIUM = 'MEDIUM',
  LOW = 'LOW'
}

export enum Complexity {
  SIMPLE = 'SIMPLE',
  MEDIUM = 'MEDIUM',
  COMPLEX = 'COMPLEX'
}

export enum AutomationLevel {
  MANUAL = 'MANUAL',
  SEMI_AUTO = 'SEMI_AUTO',
  FULL_AUTO = 'FULL_AUTO'
}

export interface TestStep {
  id?: number
  step_number: number
  action: string
  expected_result: string
  test_data?: any
}

export interface TestExecution {
  id: number
  execution_code: string
  test_case_id: number
  test_plan_id?: number
  execution_type: ExecutionType
  execution_status: ExecutionStatus
  actual_result?: string
  failure_reason?: string
  execution_notes?: string
  test_environment?: string
  browser_info?: string
  os_info?: string
  started_at?: string
  completed_at?: string
  duration?: number
  executor_id: number
  screenshots?: any[]
  logs?: any[]
  videos?: any[]
  created_at: string
  updated_at: string
}

export enum ExecutionType {
  MANUAL = 'MANUAL',
  AUTOMATED = 'AUTOMATED'
}

export enum ExecutionStatus {
  NOT_EXECUTED = 'NOT_EXECUTED',
  IN_PROGRESS = 'IN_PROGRESS',
  PASSED = 'PASSED',
  FAILED = 'FAILED',
  BLOCKED = 'BLOCKED',
  SKIPPED = 'SKIPPED'
}

export interface Defect {
  id: number
  defect_code: string
  test_execution_id?: number
  test_case_id?: number
  requirement_id?: number
  title: string
  description: string
  steps_to_reproduce?: string
  defect_type: DefectType
  severity: DefectSeverity
  priority: Priority
  status: DefectStatus
  resolution?: DefectResolution
  found_in_version?: string
  fixed_in_version?: string
  test_environment?: string
  reporter_id: number
  assignee_id?: number
  resolver_id?: number
  reported_at: string
  assigned_at?: string
  resolved_at?: string
  verified_at?: string
  attachments?: any[]
  created_at: string
  updated_at: string
}

export enum DefectType {
  FUNCTIONAL = 'FUNCTIONAL',
  PERFORMANCE = 'PERFORMANCE',
  SECURITY = 'SECURITY',
  USABILITY = 'USABILITY',
  COMPATIBILITY = 'COMPATIBILITY',
  DATA = 'DATA',
  INTERFACE = 'INTERFACE'
}

export enum DefectSeverity {
  CRITICAL = 'CRITICAL',
  HIGH = 'HIGH',
  MEDIUM = 'MEDIUM',
  LOW = 'LOW'
}

export enum DefectStatus {
  NEW = 'NEW',
  ASSIGNED = 'ASSIGNED',
  IN_PROGRESS = 'IN_PROGRESS',
  RESOLVED = 'RESOLVED',
  VERIFIED = 'VERIFIED',
  CLOSED = 'CLOSED',
  REOPENED = 'REOPENED',
  REJECTED = 'REJECTED',
  DEFERRED = 'DEFERRED'
}

export enum DefectResolution {
  FIXED = 'FIXED',
  DUPLICATE = 'DUPLICATE',
  NOT_A_BUG = 'NOT_A_BUG',
  WONT_FIX = 'WONT_FIX',
  CANNOT_REPRODUCE = 'CANNOT_REPRODUCE',
  DEFERRED = 'DEFERRED'
}

export interface TestReport {
  id: number
  report_code: string
  test_plan_id?: number
  project_id: number
  report_name: string
  report_type: ReportType
  report_format: ReportFormat
  report_content?: string
  report_summary?: string
  file_path?: string
  file_size?: number
  total_cases: number
  executed_cases: number
  passed_cases: number
  failed_cases: number
  blocked_cases: number
  skipped_cases: number
  pass_rate?: number
  coverage_rate?: number
  defect_density?: number
  report_period_start?: string
  report_period_end?: string
  generated_by: number
  created_at: string
  updated_at: string
}

export enum ReportType {
  EXECUTION = 'EXECUTION',
  DEFECT = 'DEFECT',
  COVERAGE = 'COVERAGE',
  QUALITY = 'QUALITY',
  PERFORMANCE = 'PERFORMANCE',
  SECURITY = 'SECURITY'
}

export enum ReportFormat {
  HTML = 'HTML',
  PDF = 'PDF',
  WORD = 'WORD',
  EXCEL = 'EXCEL',
  JSON = 'JSON'
}

// 请求类型
export interface CreateTestPlanRequest {
  project_id: number
  plan_name: string
  description?: string
  test_type: TestType
  test_strategy?: string
  test_scope?: string
  planned_start_date?: string
  planned_end_date?: string
  test_manager_id: number
}

export interface UpdateTestPlanRequest {
  plan_name?: string
  description?: string
  test_strategy?: string
  test_scope?: string
  planned_start_date?: string
  planned_end_date?: string
  test_manager_id?: number
  status?: TestPlanStatus
}

export interface CreateTestCaseRequest {
  test_plan_id?: number
  requirement_id?: number
  case_title: string
  case_description?: string
  case_type: TestCaseType
  module?: string
  priority: Priority
  complexity?: Complexity
  automation_level?: AutomationLevel
  preconditions?: string
  test_steps: TestStep[]
  expected_result?: string
  test_data?: any
  assignee_id?: number
  tags?: string[]
}

export interface UpdateTestCaseRequest {
  test_plan_id?: number | null
  requirement_id?: number | null
  case_title?: string
  case_description?: string
  case_type?: TestCaseType
  module?: string
  priority?: Priority
  complexity?: Complexity
  automation_level?: AutomationLevel
  preconditions?: string
  test_steps?: TestStep[]
  expected_result?: string
  test_data?: any
  assignee_id?: number
  tags?: string[]
  status?: TestCaseStatus
}

export interface CreateDefectRequest {
  test_execution_id?: number
  test_case_id?: number
  requirement_id?: number
  title: string
  description: string
  steps_to_reproduce?: string
  defect_type: DefectType
  severity: DefectSeverity
  priority: Priority
  found_in_version?: string
  test_environment?: string
  assignee_id?: number
  attachments?: any[]
}

export interface UpdateDefectRequest {
  title?: string
  description?: string
  steps_to_reproduce?: string
  defect_type?: DefectType
  severity?: DefectSeverity
  priority?: Priority
  status?: DefectStatus
  resolution?: DefectResolution
  fixed_in_version?: string
  assignee_id?: number
  attachments?: any[]
}

// 查询参数
export interface TestPlanFilters {
  search?: string
  project_id?: number
  test_type?: TestType
  status?: TestPlanStatus
  test_manager_id?: number
  created_after?: string
  created_before?: string
  page?: number
  size?: number
}

export interface TestCaseFilters {
  search?: string
  test_plan_id?: number
  requirement_id?: number
  case_type?: TestCaseType
  module?: string
  priority?: Priority
  complexity?: Complexity
  automation_level?: AutomationLevel
  status?: TestCaseStatus
  assignee_id?: number
  creator_id?: number
  tags?: string[]
  page?: number
  size?: number
}

export interface DefectFilters {
  search?: string
  test_plan_id?: number
  test_case_id?: number
  requirement_id?: number
  defect_type?: DefectType
  severity?: DefectSeverity
  priority?: Priority
  status?: DefectStatus
  reporter_id?: number
  assignee_id?: number
  found_in_version?: string
  created_after?: string
  created_before?: string
  page?: number
  size?: number
}

// 统计类型
export interface TestPlanProgress {
  plan_id: number
  total_cases: number
  executed_cases: number
  passed_cases: number
  failed_cases: number
  blocked_cases: number
  skipped_cases: number
  execution_rate: number
  pass_rate: number
  updated_at: string
}

export interface TestMetrics {
  total_plans: number
  active_plans: number
  completed_plans: number
  total_cases: number
  executed_cases: number
  passed_cases: number
  failed_cases: number
  pass_rate: number
  execution_rate: number
  defect_count: number
  critical_defects: number
  high_defects: number
}

export interface DefectTrendData {
  date: string
  new_defects: number
  resolved_defects: number
  total_defects: number
}

export interface TestCoverageData {
  module: string
  total_requirements: number
  covered_requirements: number
  coverage_rate: number
}

// AI 生成相关
export interface TestCaseGenerationConfig {
  requirement_id: number
  case_type: TestCaseType
  priority: Priority
  test_plan_id?: number
  complexity?: Complexity
  framework?: string
  template_type?: string
  generation_config?: Record<string, any>
}

export interface AutomationConfig {
  framework: string
  language: string
  browser: string
  creator_id?: number
}

export interface AutomationScript {
  id: number
  test_case_id: number
  framework: string
  language: string
  script_content: string
  script_path?: string
  dependencies?: string[]
  created_by: number
  created_at: string
  updated_at: string
}
