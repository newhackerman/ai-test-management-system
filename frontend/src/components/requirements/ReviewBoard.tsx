import React, { useState, useEffect } from 'react'
import { 
  Calendar, 
  Clock, 
  Users, 
  MessageSquare, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Eye,
  Edit,
  Plus,
  Filter
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Avatar } from '@/components/ui/Avatar'
import { Tooltip } from '@/components/ui/Tooltip'
import { RequirementReview, ReviewStatus, ReviewType, ReviewDecision } from '@/types/requirement'

interface ReviewBoardProps {
  projectId?: number
  onCreateReview?: () => void
  onViewReview?: (review: RequirementReview) => void
  onEditReview?: (review: RequirementReview) => void
}

// Mock data for demonstration
const mockReviews: RequirementReview[] = [
  {
    id: 1,
    requirement_id: 1,
    review_type: 'FORMAL',
    review_status: 'PENDING',
    title: '用户登录功能需求评审',
    description: '对用户登录功能的详细需求进行正式评审',
    review_criteria: '功能完整性、安全性、用户体验',
    moderator_id: 1,
    reviewers: [2, 3, 4],
    scheduled_date: '2024-01-15T10:00:00Z',
    created_by: 1,
    created_at: '2024-01-10T09:00:00Z',
    updated_at: '2024-01-10T09:00:00Z'
  },
  {
    id: 2,
    requirement_id: 2,
    review_type: 'WALKTHROUGH',
    review_status: 'IN_PROGRESS',
    title: '数据导出功能评审',
    description: '数据导出功能需求的走查评审',
    moderator_id: 2,
    reviewers: [1, 3],
    scheduled_date: '2024-01-12T14:00:00Z',
    started_at: '2024-01-12T14:00:00Z',
    created_by: 2,
    created_at: '2024-01-08T11:00:00Z',
    updated_at: '2024-01-12T14:00:00Z'
  },
  {
    id: 3,
    requirement_id: 3,
    review_type: 'INSPECTION',
    review_status: 'COMPLETED',
    title: '权限管理需求检查',
    description: '权限管理模块需求的详细检查',
    moderator_id: 3,
    reviewers: [1, 2, 4, 5],
    scheduled_date: '2024-01-08T09:00:00Z',
    started_at: '2024-01-08T09:00:00Z',
    completed_at: '2024-01-08T11:30:00Z',
    decision: 'APPROVED_WITH_MINOR_CHANGES',
    summary: '需求整体符合要求，需要补充部分验收标准',
    created_by: 3,
    created_at: '2024-01-05T16:00:00Z',
    updated_at: '2024-01-08T11:30:00Z'
  }
]

const getStatusColor = (status: ReviewStatus): string => {
  switch (status) {
    case 'PENDING':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'IN_PROGRESS':
      return 'bg-blue-100 text-blue-800 border-blue-200 dark:text-blue-300 dark:bg-blue-900/30'
    case 'COMPLETED':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'CANCELLED':
      return 'bg-gray-100 text-gray-800 border-gray-200 dark:text-gray-200 dark:bg-gray-800 dark:border-gray-700'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200 dark:text-gray-200 dark:bg-gray-800 dark:border-gray-700'
  }
}

const getStatusIcon = (status: ReviewStatus) => {
  switch (status) {
    case 'PENDING':
      return <Clock className="w-4 h-4" />
    case 'IN_PROGRESS':
      return <AlertCircle className="w-4 h-4" />
    case 'COMPLETED':
      return <CheckCircle className="w-4 h-4" />
    case 'CANCELLED':
      return <XCircle className="w-4 h-4" />
    default:
      return <Clock className="w-4 h-4" />
  }
}

const getDecisionColor = (decision?: ReviewDecision): string => {
  switch (decision) {
    case 'APPROVED':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'APPROVED_WITH_MINOR_CHANGES':
      return 'bg-blue-100 text-blue-800 border-blue-200 dark:text-blue-300 dark:bg-blue-900/30'
    case 'NEEDS_MAJOR_REVISION':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'REJECTED':
      return 'bg-red-100 text-red-800 border-red-200 dark:text-red-300 dark:bg-red-900/30 dark:border-red-800'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200 dark:text-gray-200 dark:bg-gray-800 dark:border-gray-700'
  }
}

const ReviewCard: React.FC<{
  review: RequirementReview
  onView: (review: RequirementReview) => void
  onEdit: (review: RequirementReview) => void
}> = ({ review, onView, onEdit }) => {
  const formatDate = (dateString?: string) => {
    if (!dateString) return '未设置'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-1">{review.title}</h3>
          <p className="text-sm text-muted-foreground mb-2">
            需求ID: REQ-{review.requirement_id.toString().padStart(3, '0')}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge className={getStatusColor(review.review_status)}>
            {getStatusIcon(review.review_status)}
            <span className="ml-1">
              {review.review_status === 'PENDING' && '待开始'}
              {review.review_status === 'IN_PROGRESS' && '进行中'}
              {review.review_status === 'COMPLETED' && '已完成'}
              {review.review_status === 'CANCELLED' && '已取消'}
            </span>
          </Badge>
        </div>
      </div>

      {review.description && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {review.description}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          <span>计划时间: {formatDate(review.scheduled_date)}</span>
        </div>
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-muted-foreground" />
          <span>评审人员: {review.reviewers.length}人</span>
        </div>
      </div>

      {review.review_status === 'COMPLETED' && review.decision && (
        <div className="mb-4">
          <Badge className={getDecisionColor(review.decision)}>
            {review.decision === 'APPROVED' && '已批准'}
            {review.decision === 'APPROVED_WITH_MINOR_CHANGES' && '有条件批准'}
            {review.decision === 'NEEDS_MAJOR_REVISION' && '需要重大修改'}
            {review.decision === 'REJECTED' && '已拒绝'}
          </Badge>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Badge variant="outline">
            {review.review_type === 'FORMAL' && '正式评审'}
            {review.review_type === 'INFORMAL' && '非正式评审'}
            {review.review_type === 'WALKTHROUGH' && '走查'}
            {review.review_type === 'INSPECTION' && '检查'}
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <Tooltip content="查看详情">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onView(review)}
            >
              <Eye className="w-4 h-4" />
            </Button>
          </Tooltip>
          {review.review_status !== 'COMPLETED' && (
            <Tooltip content="编辑评审">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEdit(review)}
              >
                <Edit className="w-4 h-4" />
              </Button>
            </Tooltip>
          )}
        </div>
      </div>
    </Card>
  )
}

export const ReviewBoard: React.FC<ReviewBoardProps> = ({
  projectId,
  onCreateReview,
  onViewReview,
  onEditReview
}) => {
  const [reviews, setReviews] = useState<RequirementReview[]>(mockReviews)
  const [filteredReviews, setFilteredReviews] = useState<RequirementReview[]>(mockReviews)
  const [activeTab, setActiveTab] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')

  useEffect(() => {
    let filtered = reviews

    // 按标签页筛选
    if (activeTab !== 'all') {
      filtered = filtered.filter(review => review.review_status === activeTab.toUpperCase())
    }

    // 按搜索词筛选
    if (searchTerm) {
      filtered = filtered.filter(review =>
        review.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.description?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // 按状态筛选
    if (statusFilter !== 'all') {
      filtered = filtered.filter(review => review.review_status === statusFilter)
    }

    // 按类型筛选
    if (typeFilter !== 'all') {
      filtered = filtered.filter(review => review.review_type === typeFilter)
    }

    setFilteredReviews(filtered)
  }, [reviews, activeTab, searchTerm, statusFilter, typeFilter])

  const getTabCount = (status: string) => {
    if (status === 'all') return reviews.length
    return reviews.filter(review => review.review_status === status.toUpperCase()).length
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">需求评审看板</h2>
          <p className="text-muted-foreground mt-1">
            管理和跟踪需求评审的整个流程
          </p>
        </div>
        <Button onClick={onCreateReview} className="bg-gradient-to-r from-primary to-primary/90">
          <Plus className="w-4 h-4 mr-2" />
          创建评审
        </Button>
      </div>

      {/* 筛选和搜索 */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input
            placeholder="搜索评审标题或描述..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-md"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="PENDING">待开始</SelectItem>
            <SelectItem value="IN_PROGRESS">进行中</SelectItem>
            <SelectItem value="COMPLETED">已完成</SelectItem>
            <SelectItem value="CANCELLED">已取消</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="FORMAL">正式评审</SelectItem>
            <SelectItem value="INFORMAL">非正式评审</SelectItem>
            <SelectItem value="WALKTHROUGH">走查</SelectItem>
            <SelectItem value="INSPECTION">检查</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 评审看板 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="all">
            全部 ({getTabCount('all')})
          </TabsTrigger>
          <TabsTrigger value="pending">
            待开始 ({getTabCount('pending')})
          </TabsTrigger>
          <TabsTrigger value="in_progress">
            进行中 ({getTabCount('in_progress')})
          </TabsTrigger>
          <TabsTrigger value="completed">
            已完成 ({getTabCount('completed')})
          </TabsTrigger>
          <TabsTrigger value="cancelled">
            已取消 ({getTabCount('cancelled')})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {filteredReviews.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-muted-foreground mb-2">
                暂无评审记录
              </h3>
              <p className="text-muted-foreground mb-4">
                {activeTab === 'all' ? '还没有创建任何评审' : `当前筛选条件下没有评审记录`}
              </p>
              {activeTab === 'all' && (
                <Button onClick={onCreateReview}>
                  <Plus className="w-4 h-4 mr-2" />
                  创建第一个评审
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredReviews.map((review) => (
                <ReviewCard
                  key={review.id}
                  review={review}
                  onView={onViewReview || (() => {})}
                  onEdit={onEditReview || (() => {})}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ReviewBoard