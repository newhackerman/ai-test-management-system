import React from 'react'
import { useResponsive } from '@/hooks/useResponsive'
import RequirementDetail from './RequirementDetail'
import MobileRequirementDetail from './mobile/MobileRequirementDetail'
import { Requirement } from '@/types/requirement'

interface ResponsiveRequirementDetailProps {
  requirementId: number
  onBack?: () => void
  onEdit?: (requirement: Requirement) => void
}

/**
 * 响应式需求详情组件
 * 根据设备类型自动切换桌面版和移动版
 */
export const ResponsiveRequirementDetail: React.FC<ResponsiveRequirementDetailProps> = (props) => {
  const { isMobile } = useResponsive()

  // 移动端使用移动版组件
  if (isMobile) {
    return <MobileRequirementDetail {...props} />
  }

  // 桌面端使用桌面版组件
  return <RequirementDetail {...props} />
}

export default ResponsiveRequirementDetail