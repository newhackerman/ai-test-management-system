import type { Project } from '@/types/project'

export const projectPriorityOptions: Array<{
  value: Project['priority']
  label: string
}> = [
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
  { value: 'URGENT', label: '紧急' },
]

const projectPriorityLabels: Record<Project['priority'], string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  URGENT: '紧急',
}

export const getProjectPriorityLabel = (priority?: Project['priority'] | string) => {
  if (!priority) return '-'
  return projectPriorityLabels[priority as Project['priority']] || priority
}

// 优先级 Badge 配色（与 <Badge variant="outline"> 配合使用，沿用会议页
// statusBadgeClass 的浅底深字风格；配色与 ProjectDetail 的
// getPriorityConfig 一致：紧急红、高橙、中琥珀、低绿）。
// 紧急刻意用更深一档的红（bg-red-100 / text-red-800），在列表里更醒目。
const projectPriorityBadgeClasses: Record<Project['priority'], string> = {
  URGENT: 'border-red-300 bg-red-100 text-red-800 dark:border-red-700 dark:bg-red-900/40 dark:text-red-300',
  HIGH: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
  MEDIUM: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400',
  LOW: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400',
}

export const getProjectPriorityBadgeClass = (priority?: Project['priority'] | string) => {
  if (!priority) return ''
  return projectPriorityBadgeClasses[priority as Project['priority']] || ''
}
