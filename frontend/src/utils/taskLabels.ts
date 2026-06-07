import type { Task } from '@/types/project'

export const taskStatusOptions: Array<{ value: Task['status']; label: string }> = [
  { value: 'TODO', label: '待开始' },
  { value: 'ASSIGNED', label: '已分配' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'ON_HOLD', label: '暂停' },
  { value: 'BLOCKED', label: '已阻塞' },
  { value: 'PENDING_REVIEW', label: '待评审' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'CANCELLED', label: '已取消' },
]

export const taskTypeOptions: Array<{ value: Task['task_type']; label: string }> = [
  { value: 'REQUIREMENT_ANALYSIS', label: '需求分析' },
  { value: 'TEST_DESIGN', label: '测试设计' },
  { value: 'TEST_EXECUTION', label: '测试执行' },
  { value: 'AUTOMATION_DEVELOPMENT', label: '自动化开发' },
  { value: 'PERFORMANCE_TEST', label: '性能测试' },
  { value: 'SECURITY_TEST', label: '安全测试' },
  { value: 'ENVIRONMENT_SETUP', label: '环境搭建' },
  { value: 'DOCUMENTATION', label: '文档工作' },
]

export const taskPriorityOptions: Array<{ value: Task['priority']; label: string }> = [
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
  { value: 'URGENT', label: '紧急' },
]

export const getTaskStatusLabel = (status?: Task['status'] | string) => {
  if (!status) return '-'
  return taskStatusOptions.find((option) => option.value === status)?.label || status
}

export const getTaskTypeLabel = (type?: Task['task_type'] | string) => {
  if (!type) return '-'
  return taskTypeOptions.find((option) => option.value === type)?.label || type
}

export const getTaskPriorityLabel = (priority?: Task['priority'] | string) => {
  if (!priority) return '-'
  return taskPriorityOptions.find((option) => option.value === priority)?.label || priority
}
