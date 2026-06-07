import React, { useState, useEffect } from 'react'
import { 
  MessageSquare, 
  Plus, 
  Edit, 
  Trash2, 
  CheckCircle, 
  AlertTriangle, 
  Info, 
  XCircle,
  Clock,
  User,
  Calendar,
  Filter,
  Search
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Textarea } from '@/components/ui/Textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Avatar } from '@/components/ui/Avatar'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/Dialog'
import { Label } from '@/components/ui/Label'
import { Separator } from '@/components/ui/Separator'
import { Tooltip } from '@/components/ui/Tooltip'

// 评审意见类型定义
export type CommentType = 'ISSUE' | 'SUGGESTION' | 'QUESTION' | 'APPROVAL' | 'REJECTION'
export type CommentSeverity = 'CRITICAL' | 'MAJOR' | 'MINOR' | 'TRIVIAL'
export type CommentStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | 'REJECTED'

export interface ReviewComment {
  id: number
  review_id: number
  requirement_id: number
  comment_type: CommentType
  severity?: CommentSeverity
  content: string
  suggestion?: string
  section?: string
  line_number?: number
  status: CommentStatus
  resolution?: string
  reviewer_id: number
  resolved_by?: number
  resolved_at?: string
  created_at: string
  updated_at: string
  reviewer?: {
    id: number
    username: string
    real_name?: string
    avatar?: string
  }
  resolver?: {
    id: number
    username: string
    real_name?: string
  }
}

interface ReviewCommentPanelProps {
  reviewId: number
  requirementId: number
  currentUserId: number
  canComment?: boolean
  canResolve?: boolean
  onCommentAdded?: (comment: ReviewComment) => void
  onCommentUpdated?: (comment: ReviewComment) => void
  onCommentResolved?: (commentId: number, resolution: string) => void
}

// Mock data
const mockComments: ReviewComment[] = [
  {
    id: 1,
    review_id: 1,
    requirement_id: 1,
    comment_type: 'ISSUE',
    severity: 'MAJOR',
    content: '需求描述中缺少对异常情况的处理说明，特别是网络连接失败时的用户体验。',
    suggestion: '建议增加网络异常处理的详细说明，包括重试机制和用户提示。',
    section: '功能描述',
    line_number: 15,
    status: 'OPEN',
    reviewer_id: 2,
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
    reviewer: {
      id: 2,
      username: 'reviewer1',
      real_name: '张三',
      avatar: '/avatars/reviewer1.jpg'
    }
  },
  {
    id: 2,
    review_id: 1,
    requirement_id: 1,
    comment_type: 'SUGGESTION',
    severity: 'MINOR',
    content: '建议在登录界面增加"记住密码"功能，提升用户体验。',
    section: '用户界面',
    status: 'RESOLVED',
    resolution: '已采纳建议，将在下个版本中实现此功能。',
    reviewer_id: 3,
    resolved_by: 1,
    resolved_at: '2024-01-15T14:20:00Z',
    created_at: '2024-01-15T11:15:00Z',
    updated_at: '2024-01-15T14:20:00Z',
    reviewer: {
      id: 3,
      username: 'reviewer2',
      real_name: '李四'
    },
    resolver: {
      id: 1,
      username: 'moderator',
      real_name: '王五'
    }
  },
  {
    id: 3,
    review_id: 1,
    requirement_id: 1,
    comment_type: 'QUESTION',
    content: '关于密码复杂度要求，是否需要支持特殊字符？现有描述不够明确。',
    section: '安全要求',
    status: 'IN_PROGRESS',
    reviewer_id: 4,
    created_at: '2024-01-15T12:00:00Z',
    updated_at: '2024-01-15T12:00:00Z',
    reviewer: {
      id: 4,
      username: 'reviewer3',
      real_name: '赵六'
    }
  }
]

const getCommentTypeIcon = (type: CommentType) => {
  switch (type) {
    case 'ISSUE':
      return <AlertTriangle className="w-4 h-4" />
    case 'SUGGESTION':
      return <Info className="w-4 h-4" />
    case 'QUESTION':
      return <MessageSquare className="w-4 h-4" />
    case 'APPROVAL':
      return <CheckCircle className="w-4 h-4" />
    case 'REJECTION':
      return <XCircle className="w-4 h-4" />
    default:
      return <MessageSquare className="w-4 h-4" />
  }
}

const getCommentTypeColor = (type: CommentType): string => {
  switch (type) {
    case 'ISSUE':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'SUGGESTION':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'QUESTION':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'APPROVAL':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'REJECTION':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const getSeverityColor = (severity?: CommentSeverity): string => {
  switch (severity) {
    case 'CRITICAL':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'MAJOR':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'MINOR':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'TRIVIAL':
      return 'bg-gray-100 text-gray-800 border-gray-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const getStatusColor = (status: CommentStatus): string => {
  switch (status) {
    case 'OPEN':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'IN_PROGRESS':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'RESOLVED':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'CLOSED':
      return 'bg-gray-100 text-gray-800 border-gray-200'
    case 'REJECTED':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const CommentCard: React.FC<{
  comment: ReviewComment
  currentUserId: number
  canResolve: boolean
  onResolve: (commentId: number, resolution: string) => void
}> = ({ comment, currentUserId, canResolve, onResolve }) => {
  const [isResolving, setIsResolving] = useState(false)
  const [resolution, setResolution] = useState('')

  const handleResolve = () => {
    if (resolution.trim()) {
      onResolve(comment.id, resolution)
      setIsResolving(false)
      setResolution('')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <Card className="p-4">
      <div className="flex items-start space-x-3">
        <Avatar className="w-8 h-8">
          {comment.reviewer?.avatar ? (
            <img src={comment.reviewer.avatar} alt={comment.reviewer.real_name} />
          ) : (
            <div className="w-full h-full bg-primary/10 flex items-center justify-center">
              <User className="w-4 h-4" />
            </div>
          )}
        </Avatar>
        
        <div className="flex-1 space-y-3">
          {/* 评论头部 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-medium">
                {comment.reviewer?.real_name || comment.reviewer?.username}
              </span>
              <Badge className={getCommentTypeColor(comment.comment_type)}>
                {getCommentTypeIcon(comment.comment_type)}
                <span className="ml-1">
                  {comment.comment_type === 'ISSUE' && '问题'}
                  {comment.comment_type === 'SUGGESTION' && '建议'}
                  {comment.comment_type === 'QUESTION' && '疑问'}
                  {comment.comment_type === 'APPROVAL' && '同意'}
                  {comment.comment_type === 'REJECTION' && '反对'}
                </span>
              </Badge>
              {comment.severity && (
                <Badge className={getSeverityColor(comment.severity)}>
                  {comment.severity === 'CRITICAL' && '严重'}
                  {comment.severity === 'MAJOR' && '重要'}
                  {comment.severity === 'MINOR' && '一般'}
                  {comment.severity === 'TRIVIAL' && '轻微'}
                </Badge>
              )}
              <Badge className={getStatusColor(comment.status)}>
                {comment.status === 'OPEN' && '待处理'}
                {comment.status === 'IN_PROGRESS' && '处理中'}
                {comment.status === 'RESOLVED' && '已解决'}
                {comment.status === 'CLOSED' && '已关闭'}
                {comment.status === 'REJECTED' && '已拒绝'}
              </Badge>
            </div>
            <span className="text-sm text-muted-foreground">
              {formatDate(comment.created_at)}
            </span>
          </div>

          {/* 位置信息 */}
          {(comment.section || comment.line_number) && (
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              {comment.section && (
                <span>章节: {comment.section}</span>
              )}
              {comment.line_number && (
                <span>行号: {comment.line_number}</span>
              )}
            </div>
          )}

          {/* 评论内容 */}
          <div className="space-y-2">
            <p className="text-sm">{comment.content}</p>
            {comment.suggestion && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <p className="text-sm text-blue-800">
                  <strong>建议:</strong> {comment.suggestion}
                </p>
              </div>
            )}
          </div>

          {/* 解决方案 */}
          {comment.status === 'RESOLVED' && comment.resolution && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <div className="flex items-center space-x-2 mb-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-800">已解决</span>
                {comment.resolver && (
                  <span className="text-sm text-green-600">
                    by {comment.resolver.real_name || comment.resolver.username}
                  </span>
                )}
                {comment.resolved_at && (
                  <span className="text-sm text-green-600">
                    {formatDate(comment.resolved_at)}
                  </span>
                )}
              </div>
              <p className="text-sm text-green-800">{comment.resolution}</p>
            </div>
          )}

          {/* 解决操作 */}
          {comment.status === 'OPEN' && canResolve && (
            <div className="space-y-2">
              {!isResolving ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsResolving(true)}
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  解决此意见
                </Button>
              ) : (
                <div className="space-y-2">
                  <Textarea
                    placeholder="请输入解决方案..."
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    rows={3}
                  />
                  <div className="flex items-center space-x-2">
                    <Button size="sm" onClick={handleResolve}>
                      确认解决
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsResolving(false)
                        setResolution('')
                      }}
                    >
                      取消
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

const AddCommentDialog: React.FC<{
  onSubmit: (comment: Omit<ReviewComment, 'id' | 'created_at' | 'updated_at' | 'reviewer'>) => void
  reviewId: number
  requirementId: number
  currentUserId: number
}> = ({ onSubmit, reviewId, requirementId, currentUserId }) => {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    comment_type: 'ISSUE' as CommentType,
    severity: 'MINOR' as CommentSeverity,
    content: '',
    suggestion: '',
    section: '',
    line_number: ''
  })

  const handleSubmit = () => {
    if (!formData.content.trim()) return

    const comment = {
      review_id: reviewId,
      requirement_id: requirementId,
      comment_type: formData.comment_type,
      severity: formData.comment_type === 'ISSUE' ? formData.severity : undefined,
      content: formData.content,
      suggestion: formData.suggestion || undefined,
      section: formData.section || undefined,
      line_number: formData.line_number ? parseInt(formData.line_number) : undefined,
      status: 'OPEN' as CommentStatus,
      reviewer_id: currentUserId
    }

    onSubmit(comment)
    setOpen(false)
    setFormData({
      comment_type: 'ISSUE',
      severity: 'MINOR',
      content: '',
      suggestion: '',
      section: '',
      line_number: ''
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          添加评审意见
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>添加评审意见</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="comment_type">意见类型</Label>
              <Select
                value={formData.comment_type}
                onValueChange={(value: CommentType) => 
                  setFormData({ ...formData, comment_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ISSUE">问题</SelectItem>
                  <SelectItem value="SUGGESTION">建议</SelectItem>
                  <SelectItem value="QUESTION">疑问</SelectItem>
                  <SelectItem value="APPROVAL">同意</SelectItem>
                  <SelectItem value="REJECTION">反对</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {formData.comment_type === 'ISSUE' && (
              <div>
                <Label htmlFor="severity">严重程度</Label>
                <Select
                  value={formData.severity}
                  onValueChange={(value: CommentSeverity) => 
                    setFormData({ ...formData, severity: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CRITICAL">严重</SelectItem>
                    <SelectItem value="MAJOR">重要</SelectItem>
                    <SelectItem value="MINOR">一般</SelectItem>
                    <SelectItem value="TRIVIAL">轻微</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="section">相关章节</Label>
              <Input
                id="section"
                placeholder="如：功能描述、验收标准等"
                value={formData.section}
                onChange={(e) => setFormData({ ...formData, section: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="line_number">行号</Label>
              <Input
                id="line_number"
                type="number"
                placeholder="具体行号（可选）"
                value={formData.line_number}
                onChange={(e) => setFormData({ ...formData, line_number: e.target.value })}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="content">意见内容 *</Label>
            <Textarea
              id="content"
              placeholder="请详细描述您的意见..."
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={4}
            />
          </div>

          {(formData.comment_type === 'SUGGESTION' || formData.comment_type === 'ISSUE') && (
            <div>
              <Label htmlFor="suggestion">改进建议</Label>
              <Textarea
                id="suggestion"
                placeholder="请提供具体的改进建议..."
                value={formData.suggestion}
                onChange={(e) => setFormData({ ...formData, suggestion: e.target.value })}
                rows={3}
              />
            </div>
          )}

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={!formData.content.trim()}>
              提交意见
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export const ReviewCommentPanel: React.FC<ReviewCommentPanelProps> = ({
  reviewId,
  requirementId,
  currentUserId,
  canComment = true,
  canResolve = false,
  onCommentAdded,
  onCommentUpdated,
  onCommentResolved
}) => {
  const [comments, setComments] = useState<ReviewComment[]>(mockComments)
  const [filteredComments, setFilteredComments] = useState<ReviewComment[]>(mockComments)
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<string>('all')

  useEffect(() => {
    let filtered = comments

    if (searchTerm) {
      filtered = filtered.filter(comment =>
        comment.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
        comment.suggestion?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(comment => comment.comment_type === typeFilter)
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(comment => comment.status === statusFilter)
    }

    if (severityFilter !== 'all') {
      filtered = filtered.filter(comment => comment.severity === severityFilter)
    }

    setFilteredComments(filtered)
  }, [comments, searchTerm, typeFilter, statusFilter, severityFilter])

  const handleAddComment = (commentData: Omit<ReviewComment, 'id' | 'created_at' | 'updated_at' | 'reviewer'>) => {
    const newComment: ReviewComment = {
      ...commentData,
      id: Date.now(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      reviewer: {
        id: currentUserId,
        username: 'current_user',
        real_name: '当前用户'
      }
    }
    
    setComments([newComment, ...comments])
    onCommentAdded?.(newComment)
  }

  const handleResolveComment = (commentId: number, resolution: string) => {
    setComments(comments.map(comment => 
      comment.id === commentId 
        ? {
            ...comment,
            status: 'RESOLVED' as CommentStatus,
            resolution,
            resolved_by: currentUserId,
            resolved_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        : comment
    ))
    onCommentResolved?.(commentId, resolution)
  }

  const getStatusCount = (status: string) => {
    if (status === 'all') return comments.length
    return comments.filter(comment => comment.status === status).length
  }

  return (
    <div className="space-y-6">
      {/* 标题和操作 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">评审意见</h3>
          <p className="text-sm text-muted-foreground">
            共 {comments.length} 条意见，
            {getStatusCount('OPEN')} 条待处理，
            {getStatusCount('RESOLVED')} 条已解决
          </p>
        </div>
        {canComment && (
          <AddCommentDialog
            onSubmit={handleAddComment}
            reviewId={reviewId}
            requirementId={requirementId}
            currentUserId={currentUserId}
          />
        )}
      </div>

      {/* 筛选器 */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input
            placeholder="搜索评审意见..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-md"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="ISSUE">问题</SelectItem>
            <SelectItem value="SUGGESTION">建议</SelectItem>
            <SelectItem value="QUESTION">疑问</SelectItem>
            <SelectItem value="APPROVAL">同意</SelectItem>
            <SelectItem value="REJECTION">反对</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="OPEN">待处理</SelectItem>
            <SelectItem value="IN_PROGRESS">处理中</SelectItem>
            <SelectItem value="RESOLVED">已解决</SelectItem>
            <SelectItem value="CLOSED">已关闭</SelectItem>
          </SelectContent>
        </Select>
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="严重程度" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部程度</SelectItem>
            <SelectItem value="CRITICAL">严重</SelectItem>
            <SelectItem value="MAJOR">重要</SelectItem>
            <SelectItem value="MINOR">一般</SelectItem>
            <SelectItem value="TRIVIAL">轻微</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 评论列表 */}
      <div className="space-y-4">
        {filteredComments.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-muted-foreground mb-2">
              暂无评审意见
            </h3>
            <p className="text-muted-foreground">
              {comments.length === 0 ? '还没有人提出评审意见' : '当前筛选条件下没有找到相关意见'}
            </p>
          </div>
        ) : (
          filteredComments.map((comment) => (
            <CommentCard
              key={comment.id}
              comment={comment}
              currentUserId={currentUserId}
              canResolve={canResolve}
              onResolve={handleResolveComment}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default ReviewCommentPanel