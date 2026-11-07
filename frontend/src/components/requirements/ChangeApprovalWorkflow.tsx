import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Textarea } from '@/components/ui/Textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/Dialog'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  User, 
  MessageSquare,
  FileText,
  Calendar,
  ArrowRight,
  AlertTriangle
} from 'lucide-react'
import { RequirementChangeRequest, ChangeStatus } from '@/types/requirement'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/date'

interface ApprovalStep {
  id: string
  name: string
  approver: {
    id: number
    name: string
    role: string
  }
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'SKIPPED'
  approved_at?: string
  comments?: string
  required: boolean
}

interface ChangeApprovalWorkflowProps {
  changeRequest: RequirementChangeRequest
  onApprove: (changeId: number, notes?: string) => void
  onReject: (changeId: number, reason: string) => void
}

export function ChangeApprovalWorkflow({
  changeRequest,
  onApprove,
  onReject
}: ChangeApprovalWorkflowProps) {
  const [showApprovalDialog, setShowApprovalDialog] = useState(false)
  const [showRejectionDialog, setShowRejectionDialog] = useState(false)
  const [approvalNotes, setApprovalNotes] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')
  const [loading, setLoading] = useState(false)

  // 模拟审批流程数据
  const approvalSteps: ApprovalStep[] = [
    {
      id: 'technical_review',
      name: '技术评审',
      approver: {
        id: 1,
        name: '张技术',
        role: '技术负责人'
      },
      status: changeRequest.status === 'SUBMITTED' ? 'PENDING' : 'APPROVED',
      approved_at: changeRequest.status !== 'SUBMITTED' ? '2024-01-16T10:00:00Z' : undefined,
      comments: changeRequest.status !== 'SUBMITTED' ? '技术方案可行，建议实施' : undefined,
      required: true
    },
    {
      id: 'business_review',
      name: '业务评审',
      approver: {
        id: 2,
        name: '李产品',
        role: '产品经理'
      },
      status: changeRequest.status === 'UNDER_REVIEW' ? 'PENDING' : 
              changeRequest.status === 'APPROVED' ? 'APPROVED' : 'PENDING',
      approved_at: changeRequest.status === 'APPROVED' ? '2024-01-16T14:00:00Z' : undefined,
      comments: changeRequest.status === 'APPROVED' ? '符合业务需求，同意变更' : undefined,
      required: true
    },
    {
      id: 'project_manager_review',
      name: '项目经理审批',
      approver: {
        id: 3,
        name: '王项目',
        role: '项目经理'
      },
      status: changeRequest.status === 'APPROVED' ? 'APPROVED' : 'PENDING',
      approved_at: changeRequest.status === 'APPROVED' ? '2024-01-16T16:00:00Z' : undefined,
      comments: changeRequest.status === 'APPROVED' ? '项目计划已调整，批准实施' : undefined,
      required: true
    }
  ]

  const getStatusBadge = (status: ApprovalStep['status']) => {
    const statusConfig = {
      PENDING: { color: 'bg-yellow-100 text-yellow-800', icon: Clock, text: '待审批' },
      APPROVED: { color: 'bg-green-100 text-green-800', icon: CheckCircle, text: '已批准' },
      REJECTED: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', icon: XCircle, text: '已拒绝' },
      SKIPPED: { color: 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800', icon: ArrowRight, text: '已跳过' }
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

  const getCurrentStep = () => {
    return approvalSteps.find(step => step.status === 'PENDING')
  }

  // 当前登录用户取自认证 store；审批权限 = 当前步骤的指定审批人，超级管理员可代审任意步骤
  const currentUser = useAuthStore((state) => state.user)

  const canCurrentUserApprove = (step?: ApprovalStep) => {
    const target = step ?? getCurrentStep()
    if (!target) return false
    if (!['SUBMITTED', 'UNDER_REVIEW'].includes(changeRequest.status)) return false
    return currentUser?.id === target.approver.id || currentUser?.is_super_admin === true
  }

  const handleApprove = async () => {
    if (!canCurrentUserApprove()) return

    setLoading(true)
    try {
      await onApprove(changeRequest.id, approvalNotes)
      setShowApprovalDialog(false)
      setApprovalNotes('')
    } catch (error) {
      console.error('审批失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async () => {
    if (!canCurrentUserApprove() || !rejectionReason.trim()) return

    setLoading(true)
    try {
      await onReject(changeRequest.id, rejectionReason)
      setShowRejectionDialog(false)
      setRejectionReason('')
    } catch (error) {
      console.error('拒绝失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const getOverallProgress = () => {
    const completedSteps = approvalSteps.filter(step => 
      step.status === 'APPROVED' || step.status === 'SKIPPED'
    ).length
    return (completedSteps / approvalSteps.length) * 100
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center">
            <FileText className="w-5 h-5 mr-2" />
            审批工作流
          </span>
          <Badge variant="outline">
            {Math.round(getOverallProgress())}% 完成
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 变更请求基本信息 */}
        <div className="bg-gray-50 p-4 rounded-lg dark:bg-gray-800/50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">变更编号:</span>
              <div className="font-medium">{changeRequest.change_request_code}</div>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">申请人:</span>
              <div className="font-medium">申请人姓名</div>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">申请日期:</span>
              <div className="font-medium">{formatDate(changeRequest.requested_date)}</div>
            </div>
          </div>
        </div>

        {/* 审批流程步骤 */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 dark:text-gray-100">审批流程</h4>
          
          {approvalSteps.map((step, index) => (
            <div key={step.id} className="relative">
              {/* 连接线 */}
              {index < approvalSteps.length - 1 && (
                <div className="absolute left-6 top-12 w-0.5 h-8 bg-gray-200 dark:bg-gray-600"></div>
              )}
              
              <div className="flex items-start space-x-4">
                {/* 状态图标 */}
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  step.status === 'APPROVED' ? 'bg-green-100' :
                  step.status === 'REJECTED' ? 'bg-red-100 dark:bg-red-900/30' :
                  step.status === 'PENDING' ? 'bg-yellow-100' : 'bg-gray-100 dark:bg-gray-800'
                }`}>
                  {step.status === 'APPROVED' && <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />}
                  {step.status === 'REJECTED' && <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />}
                  {step.status === 'PENDING' && <Clock className="w-6 h-6 text-yellow-600" />}
                  {step.status === 'SKIPPED' && <ArrowRight className="w-6 h-6 text-gray-600 dark:text-gray-400" />}
                </div>

                {/* 步骤内容 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <h5 className="font-medium text-gray-900 dark:text-gray-100">{step.name}</h5>
                      <div className="flex items-center text-sm text-gray-600 mt-1 dark:text-gray-400">
                        <User className="w-4 h-4 mr-1" />
                        {step.approver.name} ({step.approver.role})
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusBadge(step.status)}
                      {step.required && (
                        <Badge variant="outline" className="text-xs">必需</Badge>
                      )}
                    </div>
                  </div>

                  {/* 审批时间和意见 */}
                  {step.approved_at && (
                    <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center">
                        <Calendar className="w-4 h-4 mr-1" />
                        {formatDate(step.approved_at)}
                      </div>
                    </div>
                  )}

                  {step.comments && (
                    <div className="mt-2 p-3 bg-gray-50 rounded-lg dark:bg-gray-800/50">
                      <div className="flex items-start">
                        <MessageSquare className="w-4 h-4 mr-2 mt-0.5 text-gray-500 dark:text-gray-400" />
                        <p className="text-sm text-gray-700 dark:text-gray-300">{step.comments}</p>
                      </div>
                    </div>
                  )}

                  {/* 当前步骤的操作按钮 */}
                  {step.status === 'PENDING' && canCurrentUserApprove(step) && (
                    <div className="mt-3 flex space-x-2">
                      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
                        <DialogTrigger asChild>
                          <Button size="sm" className="bg-green-600 hover:bg-green-700">
                            <CheckCircle className="w-4 h-4 mr-1" />
                            批准
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>批准变更请求</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <Alert>
                              <AlertTriangle className="h-4 w-4" />
                              <AlertDescription>
                                您即将批准变更请求 "{changeRequest.title}"，请确认您已仔细审查了变更内容和影响分析。
                              </AlertDescription>
                            </Alert>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                                审批意见 (可选)
                              </label>
                              <Textarea
                                value={approvalNotes}
                                onChange={(e) => setApprovalNotes(e.target.value)}
                                placeholder="请输入审批意见..."
                                rows={3}
                              />
                            </div>
                            <div className="flex justify-end space-x-2">
                              <Button
                                variant="outline"
                                onClick={() => setShowApprovalDialog(false)}
                                disabled={loading}
                              >
                                取消
                              </Button>
                              <Button
                                onClick={handleApprove}
                                disabled={loading}
                                className="bg-green-600 hover:bg-green-700"
                              >
                                {loading ? '处理中...' : '确认批准'}
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>

                      <Dialog open={showRejectionDialog} onOpenChange={setShowRejectionDialog}>
                        <DialogTrigger asChild>
                          <Button 
                            variant="outline" 
                            size="sm"
                            className="text-red-600 border-red-600 hover:bg-red-50 dark:text-red-400 dark:bg-red-900/20"
                          >
                            <XCircle className="w-4 h-4 mr-1" />
                            拒绝
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>拒绝变更请求</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <Alert>
                              <AlertTriangle className="h-4 w-4" />
                              <AlertDescription>
                                您即将拒绝变更请求 "{changeRequest.title}"，请说明拒绝原因。
                              </AlertDescription>
                            </Alert>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                                拒绝原因 *
                              </label>
                              <Textarea
                                value={rejectionReason}
                                onChange={(e) => setRejectionReason(e.target.value)}
                                placeholder="请详细说明拒绝原因..."
                                rows={4}
                                required
                              />
                            </div>
                            <div className="flex justify-end space-x-2">
                              <Button
                                variant="outline"
                                onClick={() => setShowRejectionDialog(false)}
                                disabled={loading}
                              >
                                取消
                              </Button>
                              <Button
                                onClick={handleReject}
                                disabled={loading || !rejectionReason.trim()}
                                className="bg-red-600 hover:bg-red-700"
                              >
                                {loading ? '处理中...' : '确认拒绝'}
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 审批历史 */}
        <div className="border-t pt-4">
          <h4 className="font-medium text-gray-900 mb-3 dark:text-gray-100">审批历史</h4>
          <div className="space-y-2">
            {approvalSteps
              .filter(step => step.status !== 'PENDING')
              .map((step) => (
                <div key={step.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center">
                    <span className="text-gray-600 dark:text-gray-400">{step.name}</span>
                    <span className="mx-2">·</span>
                    <span className="text-gray-900 dark:text-gray-100">{step.approver.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {step.approved_at && (
                      <span className="text-gray-500 dark:text-gray-400">{formatDate(step.approved_at)}</span>
                    )}
                    {getStatusBadge(step.status)}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default ChangeApprovalWorkflow