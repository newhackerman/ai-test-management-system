import { useState } from 'react'
import { AlertTriangle, Calendar, CheckCircle, Clock, FileText, MessageSquare, Send, Users, XCircle } from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Label } from '@/components/ui/Label'
import { Progress } from '@/components/ui/Progress'
import { Textarea } from '@/components/ui/Textarea'
import { RequirementReview, ReviewDecision, ReviewStatus } from '@/types/requirement'

interface ReviewDecisionPanelProps {
  review: RequirementReview
  currentUserId: number
  isModerator?: boolean
  onDecisionSubmit?: (decision: ReviewDecision, summary: string) => void
  onStatusUpdate?: (status: ReviewStatus) => void
}

interface ReviewProgress {
  total_reviewers: number
  completed_reviews: number
  pending_reviews: number
  reviewer_status: Array<{
    reviewer_id: number
    reviewer_name: string
    status: 'pending' | 'completed' | 'in_progress'
    completed_at?: string
    comment_count: number
  }>
}

const mockReviewProgress: ReviewProgress = {
  total_reviewers: 4,
  completed_reviews: 2,
  pending_reviews: 2,
  reviewer_status: [
    { reviewer_id: 2, reviewer_name: '张三', status: 'completed', completed_at: '2026-06-01T14:30:00+08:00', comment_count: 3 },
    { reviewer_id: 3, reviewer_name: '李四', status: 'completed', completed_at: '2026-06-01T15:20:00+08:00', comment_count: 1 },
    { reviewer_id: 4, reviewer_name: '王五', status: 'in_progress', comment_count: 2 },
    { reviewer_id: 5, reviewer_name: '赵六', status: 'pending', comment_count: 0 },
  ],
}

const decisionLabels: Record<ReviewDecision, string> = {
  APPROVED: '批准',
  APPROVED_WITH_MINOR_CHANGES: '有条件批准',
  NEEDS_MAJOR_REVISION: '需要重大修改',
  REJECTED: '拒绝',
}

const decisionDescriptions: Record<ReviewDecision, string> = {
  APPROVED: '需求评审通过，可以进入下一阶段。',
  APPROVED_WITH_MINOR_CHANGES: '需求基本符合要求，完成少量修改后通过。',
  NEEDS_MAJOR_REVISION: '需求存在重大问题，需要修改后重新评审。',
  REJECTED: '需求不符合要求，建议重新设计或取消。',
}

const statusLabels: Record<ReviewStatus, string> = {
  PENDING: '待开始',
  IN_PROGRESS: '进行中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

const getDecisionIcon = (decision: ReviewDecision) => {
  switch (decision) {
    case 'APPROVED':
    case 'APPROVED_WITH_MINOR_CHANGES':
      return <CheckCircle className="h-5 w-5 text-green-600" />
    case 'NEEDS_MAJOR_REVISION':
      return <AlertTriangle className="h-5 w-5 text-orange-600" />
    case 'REJECTED':
      return <XCircle className="h-5 w-5 text-red-600" />
    default:
      return <Clock className="h-5 w-5 text-gray-600" />
  }
}

const getDecisionColor = (decision: ReviewDecision) => {
  switch (decision) {
    case 'APPROVED':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'APPROVED_WITH_MINOR_CHANGES':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'NEEDS_MAJOR_REVISION':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'REJECTED':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const getStatusIcon = (status: 'pending' | 'completed' | 'in_progress') => {
  if (status === 'completed') return <CheckCircle className="h-4 w-4 text-green-600" />
  if (status === 'in_progress') return <Clock className="h-4 w-4 text-blue-600" />
  return <Clock className="h-4 w-4 text-gray-400" />
}

const formatDate = (value?: string) => {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未设置'
  return date.toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  })
}

const ReviewProgressCard: React.FC<{ progress: ReviewProgress }> = ({ progress }) => {
  const completionRate = progress.total_reviewers ? (progress.completed_reviews / progress.total_reviewers) * 100 : 0

  return (
    <Card className="p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold">评审进度</h4>
          <Badge variant="outline">
            {progress.completed_reviews}/{progress.total_reviewers} 已完成
          </Badge>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>完成进度</span>
            <span>{Math.round(completionRate)}%</span>
          </div>
          <Progress value={completionRate} className="h-2" />
        </div>

        <div className="space-y-3">
          {progress.reviewer_status.map((reviewer) => (
            <div key={reviewer.reviewer_id} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Avatar className="h-6 w-6">
                  <div className="flex h-full w-full items-center justify-center bg-primary/10">
                    <span className="text-xs">{reviewer.reviewer_name[0]}</span>
                  </div>
                </Avatar>
                <span className="text-sm font-medium">{reviewer.reviewer_name}</span>
                {getStatusIcon(reviewer.status)}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {reviewer.comment_count > 0 && (
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3 w-3" />
                    <span>{reviewer.comment_count}</span>
                  </span>
                )}
                {reviewer.completed_at && <span>{formatDate(reviewer.completed_at)}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

const DecisionForm: React.FC<{
  onSubmit: (decision: ReviewDecision, summary: string) => void
  onCancel: () => void
}> = ({ onSubmit, onCancel }) => {
  const [decision, setDecision] = useState<ReviewDecision>('APPROVED')
  const [summary, setSummary] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!summary.trim()) return
    setIsSubmitting(true)
    try {
      await onSubmit(decision, summary)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div>
          <h4 className="mb-4 font-semibold">评审决策</h4>

          <div className="space-y-4">
            <div>
              <Label htmlFor="decision">评审结论</Label>
              <select
                id="decision"
                value={decision}
                onChange={(event) => setDecision(event.target.value as ReviewDecision)}
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {Object.entries(decisionLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-sm text-muted-foreground">{decisionDescriptions[decision]}</p>
            </div>

            <div>
              <Label htmlFor="summary">评审总结 *</Label>
              <Textarea
                id="summary"
                placeholder="请说明评审结论、主要发现、决策依据和后续建议..."
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                rows={6}
                className="mt-1"
              />
              <p className="mt-1 text-sm text-muted-foreground">请包含主要发现、决策依据和后续建议。</p>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!summary.trim() || isSubmitting}>
            <Send className="mr-2 h-4 w-4" />
            {isSubmitting ? '提交中...' : '提交决策'}
          </Button>
        </div>
      </div>
    </Card>
  )
}

export const ReviewDecisionPanel: React.FC<ReviewDecisionPanelProps> = ({
  review,
  currentUserId: _currentUserId,
  isModerator = false,
  onDecisionSubmit,
  onStatusUpdate,
}) => {
  const [showDecisionForm, setShowDecisionForm] = useState(false)
  const [progress] = useState<ReviewProgress>(mockReviewProgress)

  const canMakeDecision = isModerator && review.review_status === 'IN_PROGRESS'
  const canStartReview = isModerator && review.review_status === 'PENDING'

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">评审状态</h3>
            <Badge
              className={
                review.review_status === 'PENDING'
                  ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                  : review.review_status === 'IN_PROGRESS'
                    ? 'bg-blue-100 text-blue-800 border-blue-200'
                    : review.review_status === 'COMPLETED'
                      ? 'bg-green-100 text-green-800 border-green-200'
                      : 'bg-gray-100 text-gray-800 border-gray-200'
              }
            >
              {statusLabels[review.review_status] || review.review_status}
            </Badge>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">计划时间：{formatDate(review.scheduled_date)}</span>
              </div>
              {review.started_at && (
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">开始时间：{formatDate(review.started_at)}</span>
                </div>
              )}
              {review.completed_at && (
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">完成时间：{formatDate(review.completed_at)}</span>
                </div>
              )}
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">评审人员：{review.reviewers.length} 人</span>
              </div>
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">评审类型：{review.review_type}</span>
              </div>
            </div>
          </div>

          {canStartReview && (
            <div className="border-t pt-4">
              <Button onClick={() => onStatusUpdate?.('IN_PROGRESS')}>
                <Clock className="mr-2 h-4 w-4" />
                开始评审
              </Button>
            </div>
          )}
        </div>
      </Card>

      {review.review_status === 'IN_PROGRESS' && <ReviewProgressCard progress={progress} />}

      {review.review_status === 'COMPLETED' && review.decision && (
        <Card className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">评审决策</h4>
              <Badge className={getDecisionColor(review.decision)}>
                {getDecisionIcon(review.decision)}
                <span className="ml-2">{decisionLabels[review.decision]}</span>
              </Badge>
            </div>

            {review.summary && (
              <div className="space-y-2">
                <Label>评审总结</Label>
                <div className="rounded-md bg-muted/50 p-4">
                  <p className="whitespace-pre-wrap text-sm">{review.summary}</p>
                </div>
              </div>
            )}

            <div className="text-sm text-muted-foreground">决策时间：{formatDate(review.completed_at)}</div>
          </div>
        </Card>
      )}

      {canMakeDecision && !showDecisionForm && (
        <Card className="p-6">
          <div className="space-y-4 text-center">
            <div>
              <h4 className="mb-2 font-semibold">准备做出评审决策</h4>
              <p className="text-sm text-muted-foreground">
                评审进度：{progress.completed_reviews}/{progress.total_reviewers} 人已完成评审
              </p>
            </div>

            {progress.completed_reviews < progress.total_reviewers && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  还有 {progress.pending_reviews} 位评审人员未完成评审。可以等待全部完成，也可以基于已收集意见做出决策。
                </AlertDescription>
              </Alert>
            )}

            <Button onClick={() => setShowDecisionForm(true)}>
              <FileText className="mr-2 h-4 w-4" />
              做出评审决策
            </Button>
          </div>
        </Card>
      )}

      {showDecisionForm && (
        <DecisionForm
          onSubmit={(decision, summary) => {
            onDecisionSubmit?.(decision, summary)
            setShowDecisionForm(false)
          }}
          onCancel={() => setShowDecisionForm(false)}
        />
      )}
    </div>
  )
}

export default ReviewDecisionPanel
