import React from 'react'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Table } from '@/components/ui/Table'
import { Loading } from '@/components/ui/Loading'
import { 
  Eye, 
  Edit, 
  Check, 
  X, 
  Clock, 
  AlertTriangle, 
  FileText,
  TrendingUp,
  Calendar,
  User
} from 'lucide-react'
import { RequirementChangeRequest, ChangeStatus, ChangePriority, ChangeType } from '@/types/requirement'
import { formatDate } from '@/utils/date'

interface ChangeRequestListProps {
  changes: RequirementChangeRequest[]
  loading: boolean
  onViewChange: (change: RequirementChangeRequest) => void
  onApprove: (changeId: number, notes?: string) => void
  onReject: (changeId: number, reason: string) => void
  onShowImpactAnalysis: (change: RequirementChangeRequest) => void
}

export function ChangeRequestList({
  changes,
  loading,
  onViewChange,
  onApprove,
  onReject,
  onShowImpactAnalysis
}: ChangeRequestListProps) {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loading />
      </div>
    )
  }

  if (changes.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无变更请求</h3>
        <p className="text-gray-500">当前没有符合条件的变更请求</p>
      </div>
    )
  }

  const getStatusBadge = (status: ChangeStatus) => {
    const statusConfig = {
      SUBMITTED: { color: 'bg-blue-100 text-blue-800', icon: Clock, text: '已提交' },
      UNDER_REVIEW: { color: 'bg-yellow-100 text-yellow-800', icon: Eye, text: '审核中' },
      APPROVED: { color: 'bg-green-100 text-green-800', icon: Check, text: '已批准' },
      REJECTED: { color: 'bg-red-100 text-red-800', icon: X, text: '已拒绝' },
      IMPLEMENTED: { color: 'bg-purple-100 text-purple-800', icon: Check, text: '已实施' },
      CLOSED: { color: 'bg-gray-100 text-gray-800', icon: Check, text: '已关闭' }
    }

    const config = statusConfig[status]
    const Icon = config.icon

    return (
      <Badge className={config.color}>
        <Icon className="w-3 h-3 mr-1" />
        {config.text}
      </Badge>
    )
  }

  const getPriorityBadge = (priority: ChangePriority) => {
    const priorityConfig = {
      EMERGENCY: { color: 'bg-red-100 text-red-800', text: '紧急' },
      HIGH: { color: 'bg-orange-100 text-orange-800', text: '高' },
      MEDIUM: { color: 'bg-yellow-100 text-yellow-800', text: '中' },
      LOW: { color: 'bg-green-100 text-green-800', text: '低' }
    }

    const config = priorityConfig[priority]

    return (
      <Badge className={config.color}>
        {config.text}
      </Badge>
    )
  }

  const getChangeTypeBadge = (type: ChangeType) => {
    const typeConfig = {
      ADDITION: { color: 'bg-blue-100 text-blue-800', text: '新增' },
      MODIFICATION: { color: 'bg-yellow-100 text-yellow-800', text: '修改' },
      DELETION: { color: 'bg-red-100 text-red-800', text: '删除' },
      CLARIFICATION: { color: 'bg-gray-100 text-gray-800', text: '澄清' }
    }

    const config = typeConfig[type]

    return (
      <Badge variant="outline" className={config.color}>
        {config.text}
      </Badge>
    )
  }

  const canApprove = (change: RequirementChangeRequest) => {
    return ['SUBMITTED', 'UNDER_REVIEW'].includes(change.status)
  }

  const canReject = (change: RequirementChangeRequest) => {
    return ['SUBMITTED', 'UNDER_REVIEW'].includes(change.status)
  }

  return (
    <div className="space-y-4">
      {/* 桌面端表格视图 */}
      <div className="hidden md:block">
        <Table>
          <thead>
            <tr>
              <th className="text-left">变更请求</th>
              <th className="text-left">类型</th>
              <th className="text-left">状态</th>
              <th className="text-left">优先级</th>
              <th className="text-left">工作量</th>
              <th className="text-left">申请日期</th>
              <th className="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {changes.map((change) => (
              <tr key={change.id} className="hover:bg-gray-50">
                <td>
                  <div>
                    <div className="font-medium text-gray-900">{change.title}</div>
                    <div className="text-sm text-gray-500">{change.change_request_code}</div>
                    <div className="text-sm text-gray-600 mt-1 line-clamp-2">
                      {change.description}
                    </div>
                  </div>
                </td>
                <td>
                  {getChangeTypeBadge(change.change_type)}
                </td>
                <td>
                  {getStatusBadge(change.status)}
                </td>
                <td>
                  {getPriorityBadge(change.priority)}
                </td>
                <td>
                  <div className="text-sm">
                    {change.effort_estimate ? `${change.effort_estimate} 人天` : '-'}
                  </div>
                  {change.cost_estimate && (
                    <div className="text-xs text-gray-500">
                      ¥{change.cost_estimate.toLocaleString()}
                    </div>
                  )}
                </td>
                <td>
                  <div className="text-sm text-gray-900">
                    {formatDate(change.requested_date)}
                  </div>
                  {change.target_date && (
                    <div className="text-xs text-gray-500">
                      目标: {formatDate(change.target_date)}
                    </div>
                  )}
                </td>
                <td>
                  <div className="flex justify-end space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onViewChange(change)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onShowImpactAnalysis(change)}
                    >
                      <TrendingUp className="w-4 h-4" />
                    </Button>
                    {canApprove(change) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-green-600 hover:text-green-700"
                        onClick={() => onApprove(change.id)}
                      >
                        <Check className="w-4 h-4" />
                      </Button>
                    )}
                    {canReject(change) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-600 hover:text-red-700"
                        onClick={() => onReject(change.id, '需要提供拒绝原因')}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>

      {/* 移动端卡片视图 */}
      <div className="md:hidden space-y-4">
        {changes.map((change) => (
          <Card key={change.id} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardContent className="p-4">
              <div className="space-y-3">
                {/* 标题和编号 */}
                <div>
                  <h3 className="font-medium text-gray-900">{change.title}</h3>
                  <p className="text-sm text-gray-500">{change.change_request_code}</p>
                </div>

                {/* 描述 */}
                <p className="text-sm text-gray-600 line-clamp-2">
                  {change.description}
                </p>

                {/* 标签行 */}
                <div className="flex flex-wrap gap-2">
                  {getChangeTypeBadge(change.change_type)}
                  {getStatusBadge(change.status)}
                  {getPriorityBadge(change.priority)}
                </div>

                {/* 详细信息 */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="flex items-center text-gray-500">
                      <Calendar className="w-4 h-4 mr-1" />
                      申请日期
                    </div>
                    <div className="text-gray-900">
                      {formatDate(change.requested_date)}
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center text-gray-500">
                      <Clock className="w-4 h-4 mr-1" />
                      工作量
                    </div>
                    <div className="text-gray-900">
                      {change.effort_estimate ? `${change.effort_estimate} 人天` : '-'}
                    </div>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex justify-between items-center pt-2 border-t">
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onViewChange(change)}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      查看
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onShowImpactAnalysis(change)}
                    >
                      <TrendingUp className="w-4 h-4 mr-1" />
                      影响分析
                    </Button>
                  </div>
                  <div className="flex space-x-2">
                    {canApprove(change) && (
                      <Button
                        size="sm"
                        className="bg-green-600 hover:bg-green-700"
                        onClick={() => onApprove(change.id)}
                      >
                        <Check className="w-4 h-4 mr-1" />
                        批准
                      </Button>
                    )}
                    {canReject(change) && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-600 border-red-600 hover:bg-red-50"
                        onClick={() => onReject(change.id, '需要提供拒绝原因')}
                      >
                        <X className="w-4 h-4 mr-1" />
                        拒绝
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default ChangeRequestList