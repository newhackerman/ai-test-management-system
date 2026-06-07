import {
  AutomationLevel,
  Complexity,
  ExecutionStatus,
  Priority,
  TestCaseStatus,
  TestCaseType,
} from '../../../types/testmanager'

export const TEST_CASE_TYPE_LABELS: Record<TestCaseType, string> = {
  [TestCaseType.FUNCTIONAL]: '功能测试',
  [TestCaseType.NON_FUNCTIONAL]: '非功能测试',
  [TestCaseType.INTEGRATION]: '集成测试',
  [TestCaseType.SYSTEM]: '系统测试',
  [TestCaseType.ACCEPTANCE]: '验收测试',
  [TestCaseType.REGRESSION]: '回归测试',
  [TestCaseType.SMOKE]: '冒烟测试',
  [TestCaseType.PERFORMANCE]: '性能测试',
  [TestCaseType.SECURITY]: '安全测试',
  [TestCaseType.USABILITY]: '易用性测试',
}

export const PRIORITY_LABELS: Record<Priority, string> = {
  [Priority.CRITICAL]: '紧急',
  [Priority.HIGH]: '高',
  [Priority.MEDIUM]: '中',
  [Priority.LOW]: '低',
}

export const STATUS_LABELS: Record<TestCaseStatus, string> = {
  [TestCaseStatus.DRAFT]: '草稿',
  [TestCaseStatus.APPROVED]: '已批准',
  [TestCaseStatus.ACTIVE]: '活跃',
  [TestCaseStatus.DEPRECATED]: '已废弃',
  [TestCaseStatus.ARCHIVED]: '已归档',
}

export const COMPLEXITY_LABELS: Record<Complexity, string> = {
  [Complexity.SIMPLE]: '简单',
  [Complexity.MEDIUM]: '中等',
  [Complexity.COMPLEX]: '复杂',
}

export const AUTOMATION_LABELS: Record<AutomationLevel, string> = {
  [AutomationLevel.MANUAL]: '手动',
  [AutomationLevel.SEMI_AUTO]: '半自动',
  [AutomationLevel.FULL_AUTO]: '全自动',
}

export const EXECUTION_STATUS_LABELS: Record<ExecutionStatus, string> = {
  [ExecutionStatus.NOT_EXECUTED]: '未执行',
  [ExecutionStatus.IN_PROGRESS]: '执行中',
  [ExecutionStatus.PASSED]: '通过',
  [ExecutionStatus.FAILED]: '失败',
  [ExecutionStatus.BLOCKED]: '阻塞',
  [ExecutionStatus.SKIPPED]: '跳过',
}

export const getEnumLabel = <T extends string>(labels: Record<T, string>, value?: T | null) => (
  value ? labels[value] || value : '-'
)

