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
