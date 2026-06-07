import React from 'react'
import { useResponsive } from '@/hooks/useResponsive'
import RequirementForm from './RequirementForm'
import MobileRequirementForm from './mobile/MobileRequirementForm'
import { 
  Requirement, 
  CreateRequirementRequest, 
  UpdateRequirementRequest
} from '@/types/requirement'
import { User } from '@/types'

interface ResponsiveRequirementFormProps {
  requirement?: Requirement
  projectId?: number
  onSave?: (requirement: Requirement) => void
  onCancel?: () => void
  users?: User[]
  categories?: string[]
  availableTags?: string[]
}

/**
 * 响应式需求表单组件
 * 根据设备类型自动切换桌面版和移动版
 */
export const ResponsiveRequirementForm: React.FC<ResponsiveRequirementFormProps> = (props) => {
  const { isMobile } = useResponsive()

  // 移动端使用移动版组件
  if (isMobile) {
    return <MobileRequirementForm {...props} />
  }

  // 桌面端使用桌面版组件
  return <RequirementForm {...props} />
}

export default ResponsiveRequirementForm