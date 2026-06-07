import React from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { 
  BarChart3, 
  Users, 
  FileText, 
  ClipboardList, 
  CheckSquare,
  TrendingUp
} from 'lucide-react'

interface AnalyticsNavigationProps {
  className?: string
}

const AnalyticsNavigation: React.FC<AnalyticsNavigationProps> = ({ className }) => {
  const location = useLocation()
  const { id: meetingId } = useParams<{ id: string }>()
  
  const navigationItems = [
    {
      key: 'dashboard',
      label: '分析概览',
      icon: BarChart3,
      path: `/meetings/${meetingId}/analytics`,
      description: '会议效果综合分析'
    },
    {
      key: 'participation',
      label: '参与度分析',
      icon: Users,
      path: `/meetings/${meetingId}/analytics/participation`,
      description: '参与者表现分析'
    },
    {
      key: 'summary',
      label: '会议摘要',
      icon: FileText,
      path: `/meetings/${meetingId}/analytics/summary`,
      description: 'AI生成的会议摘要'
    },
    {
      key: 'minutes',
      label: '会议纪要',
      icon: ClipboardList,
      path: `/meetings/${meetingId}/analytics/minutes`,
      description: '结构化会议纪要'
    },
    {
      key: 'actions',
      label: '行动项目',
      icon: CheckSquare,
      path: `/meetings/${meetingId}/analytics/actions`,
      description: '待办事项管理'
    },
    {
      key: 'reports',
      label: '报告生成',
      icon: FileText,
      path: `/meetings/${meetingId}/analytics/reports`,
      description: '生成分析报告'
    }
  ]
  
  return (
    <nav className={cn('bg-white border-b border-gray-200', className)}>
      <div className="px-6">
        <div className="flex items-center space-x-8">
          {/* 返回会议详情 */}
          <Link
            to={`/meetings/${meetingId}`}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 py-4"
          >
            <TrendingUp className="h-5 w-5" />
            <span className="font-medium">返回会议</span>
          </Link>
          
          <div className="h-6 w-px bg-gray-300" />
          
          {/* 分析导航项 */}
          {navigationItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            
            return (
              <Link
                key={item.key}
                to={item.path}
                className={cn(
                  'flex items-center space-x-2 py-4 border-b-2 transition-colors',
                  isActive
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                )}
              >
                <Icon className="h-5 w-5" />
                <div className="flex flex-col">
                  <span className="font-medium">{item.label}</span>
                  <span className="text-xs text-gray-500">{item.description}</span>
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

export default AnalyticsNavigation