import type { Project } from '@/types/project'

export const projectTypeOptions: Array<{
  value: Project['project_type']
  label: string
  description: string
}> = [
  { value: 'BUSINESS_SYSTEM', label: '业务系统', description: '面向业务流程、运营管理或企业应用的项目' },
  { value: 'MOBILE_APP', label: '移动应用', description: 'App、小程序、移动端体验或跨端应用项目' },
  { value: 'API_SERVICE', label: '接口服务', description: '后端服务、开放接口、微服务或系统集成项目' },
  { value: 'DATA_AI', label: '数据/AI', description: '数据平台、算法模型、AI能力或分析类项目' },
  { value: 'INFRASTRUCTURE', label: '基础设施', description: '环境、平台、DevOps、稳定性或安全基础能力项目' },
  { value: 'INTERNAL_TOOL', label: '内部工具', description: '效率工具、管理后台、自动化支撑或内部系统项目' },
]

const projectTypeLabels: Record<Project['project_type'], string> = {
  BUSINESS_SYSTEM: '业务系统',
  MOBILE_APP: '移动应用',
  API_SERVICE: '接口服务',
  DATA_AI: '数据/AI',
  INFRASTRUCTURE: '基础设施',
  INTERNAL_TOOL: '内部工具',

  // Legacy values kept for old records and API compatibility.
  FUNCTIONAL: '业务系统',
  PERFORMANCE: '基础设施',
  SECURITY: '基础设施',
  AUTOMATION: '内部工具',
  INTEGRATION: '接口服务',
}

export const normalizeProjectType = (type?: Project['project_type'] | string): Project['project_type'] => {
  const legacyMap: Record<string, Project['project_type']> = {
    FUNCTIONAL: 'BUSINESS_SYSTEM',
    PERFORMANCE: 'INFRASTRUCTURE',
    SECURITY: 'INFRASTRUCTURE',
    AUTOMATION: 'INTERNAL_TOOL',
    INTEGRATION: 'API_SERVICE',
  }

  if (!type) return 'BUSINESS_SYSTEM'
  if (projectTypeOptions.some((option) => option.value === type)) return type as Project['project_type']
  return legacyMap[type] || 'BUSINESS_SYSTEM'
}

export const getProjectTypeLabel = (type?: Project['project_type'] | string) => {
  if (!type) return '-'
  return projectTypeLabels[type as Project['project_type']] || type
}

export const getProjectTypeDescription = (type?: Project['project_type'] | string) => {
  const option = projectTypeOptions.find((item) => item.value === type)
  return option?.description || ''
}
