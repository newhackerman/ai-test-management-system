import React from 'react'
import { useResponsive } from '@/hooks/useResponsive'
import RequirementList from './RequirementList'
import MobileRequirementList from './mobile/MobileRequirementList'
import { 
  Requirement, 
  RequirementFilters
} from '@/types/requirement'

interface ResponsiveRequirementListProps {
  projectId?: number
  onRequirementSelect?: (requirement: Requirement) => void
  onRequirementEdit?: (requirement: Requirement) => void
  onRequirementCreate?: () => void
  selectedRequirements?: number[]
  onSelectionChange?: (selectedIds: number[]) => void
}

/**
 * 响应式需求列表组件
 * 根据设备类型自动切换桌面版和移动版
 */
export const ResponsiveRequirementList: React.FC<ResponsiveRequirementListProps> = (props) => {
  const { isMobile } = useResponsive()

  // 移动端使用移动版组件
  if (isMobile) {
    return <MobileRequirementList {...props} />
  }

  // 桌面端使用桌面版组件
  return <RequirementList {...props} />
}

export default ResponsiveRequirementList