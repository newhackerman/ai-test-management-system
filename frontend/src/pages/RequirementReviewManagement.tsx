import React, { useState } from 'react'
import { ArrowLeft, Eye, Edit, MessageSquare, FileText } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Card } from '@/components/ui/Card'
import ReviewBoard from '@/components/requirements/ReviewBoard'
import ReviewCommentPanel from '@/components/requirements/ReviewCommentPanel'
import ReviewDecisionPanel from '@/components/requirements/ReviewDecisionPanel'
import { RequirementReview, ReviewDecision, ReviewStatus } from '@/types/requirement'

type ViewMode = 'board' | 'detail'

// Mock current user
const mockCurrentUser = {
  id: 1,
  username: 'moderator',
  real_name: '王五'
}

// Mock review data
const mockReview: RequirementReview = {
  id: 1,
  requirement_id: 1,
  review_type: 'FORMAL',
  review_status: 'IN_PROGRESS',
  title: '用户登录功能需求评审',
  description: '对用户登录功能的详细需求进行正式评审，包括功能完整性、安全性、用户体验等方面的评估。',
  review_criteria: '1. 功能完整性检查\n2. 安全性评估\n3. 用户体验分析\n4. 技术可行性评估\n5. 验收标准完整性',
  moderator_id: 1,
  reviewers: [2, 3, 4, 5],
  scheduled_date: '2024-01-15T10:00:00Z',
  started_at: '2024-01-15T10:00:00Z',
  created_by: 1,
  created_at: '2024-01-10T09:00:00Z',
  updated_at: '2024-01-15T10:00:00Z'
}

function RequirementReviewManagement() {
  const [viewMode, setViewMode] = useState<ViewMode>('board')
  const [selectedReview, setSelectedReview] = useState<RequirementReview | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  const handleViewReview = (review: RequirementReview) => {
    setSelectedReview(review)
    setViewMode('detail')
    setActiveTab('overview')
  }

  const handleEditReview = (review: RequirementReview) => {
    setSelectedReview(review)
    setViewMode('detail')
    setActiveTab('overview')
    // TODO: Implement edit mode
  }

  const handleCreateReview = () => {
    // TODO: Implement create review dialog
    console.log('Create new review')
  }

  const handleBackToBoard = () => {
    setSelectedReview(null)
    setViewMode('board')
  }

  const handleDecisionSubmit = (decision: ReviewDecision, summary: string) => {
    console.log('Decision submitted:', { decision, summary })
    // TODO: Implement API call to submit decision
  }

  const handleStatusUpdate = (status: ReviewStatus) => {
    console.log('Status updated:', status)
    // TODO: Implement API call to update status
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return '未设置'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <div className="space-y-6 min-h-full custom-scrollbar">
      {viewMode === 'board' && (
        <>
          {/* 页面标题 */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">需求评审管理</h1>
              <p className="text-muted-foreground mt-1">
                管理和跟踪需求评审的整个流程，确保需求质量
              </p>
            </div>
          </div>

          {/* 评审看板 */}
          <ReviewBoard
            onCreateReview={handleCreateReview}
            onViewReview={handleViewReview}
            onEditReview={handleEditReview}
          />
        </>
      )}

      {viewMode === 'detail' && selectedReview && (
        <>
          {/* 详情页标题 */}
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={handleBackToBoard}
              className="p-2"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-foreground">{selectedReview.title}</h1>
              <p className="text-muted-foreground">
                需求ID: REQ-{selectedReview.requirement_id.toString().padStart(3, '0')} • 
                评审ID: {selectedReview.id} • 
                创建时间: {formatDate(selectedReview.created_at)}
              </p>
            </div>
          </div>

          {/* 评审详情标签页 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview" className="flex items-center space-x-2">
                <Eye className="w-4 h-4" />
                <span>评审概览</span>
              </TabsTrigger>
              <TabsTrigger value="comments" className="flex items-center space-x-2">
                <MessageSquare className="w-4 h-4" />
                <span>评审意见</span>
              </TabsTrigger>
              <TabsTrigger value="decision" className="flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>评审决策</span>
              </TabsTrigger>
              <TabsTrigger value="requirement" className="flex items-center space-x-2">
                <Edit className="w-4 h-4" />
                <span>需求详情</span>
              </TabsTrigger>
            </TabsList>

            {/* 评审概览 */}
            <TabsContent value="overview" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 评审基本信息 */}
                <div className="lg:col-span-2">
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">评审信息</h3>
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium mb-2">评审描述</h4>
                        <p className="text-sm text-muted-foreground">
                          {selectedReview.description || '暂无描述'}
                        </p>
                      </div>
                      
                      {selectedReview.review_criteria && (
                        <div>
                          <h4 className="font-medium mb-2">评审标准</h4>
                          <div className="bg-muted/50 rounded-md p-4">
                            <pre className="text-sm whitespace-pre-wrap">
                              {selectedReview.review_criteria}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </Card>
                </div>

                {/* 评审状态和进度 */}
                <div>
                  <ReviewDecisionPanel
                    review={selectedReview}
                    currentUserId={mockCurrentUser.id}
                    isModerator={selectedReview.moderator_id === mockCurrentUser.id}
                    onDecisionSubmit={handleDecisionSubmit}
                    onStatusUpdate={handleStatusUpdate}
                  />
                </div>
              </div>
            </TabsContent>

            {/* 评审意见 */}
            <TabsContent value="comments">
              <ReviewCommentPanel
                reviewId={selectedReview.id}
                requirementId={selectedReview.requirement_id}
                currentUserId={mockCurrentUser.id}
                canComment={selectedReview.reviewers.includes(mockCurrentUser.id)}
                canResolve={selectedReview.moderator_id === mockCurrentUser.id}
                onCommentAdded={(comment) => {
                  console.log('Comment added:', comment)
                }}
                onCommentResolved={(commentId, resolution) => {
                  console.log('Comment resolved:', { commentId, resolution })
                }}
              />
            </TabsContent>

            {/* 评审决策 */}
            <TabsContent value="decision">
              <ReviewDecisionPanel
                review={selectedReview}
                currentUserId={mockCurrentUser.id}
                isModerator={selectedReview.moderator_id === mockCurrentUser.id}
                onDecisionSubmit={handleDecisionSubmit}
                onStatusUpdate={handleStatusUpdate}
              />
            </TabsContent>

            {/* 需求详情 */}
            <TabsContent value="requirement">
              <Card className="p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">需求详情</h3>
                    <Button variant="outline" size="sm">
                      <Edit className="w-4 h-4 mr-2" />
                      查看完整需求
                    </Button>
                  </div>
                  
                  <div className="bg-muted/50 rounded-md p-4">
                    <p className="text-sm text-muted-foreground">
                      需求ID: REQ-{selectedReview.requirement_id.toString().padStart(3, '0')}
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">
                      点击"查看完整需求"按钮可以查看需求的详细信息，包括需求描述、验收标准、依赖关系等。
                    </p>
                  </div>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  )
}

export default RequirementReviewManagement