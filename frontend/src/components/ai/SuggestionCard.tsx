/**
 * 建议卡片组件
 * 
 * 功能特性：
 * - 建议分类展示
 * - 状态筛选和排序
 * - 建议详情查看
 * - 接受/拒绝操作
 * - 实施反馈记录
 * - 乐观更新与回滚机制
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Textarea } from '../ui/Textarea';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Star,
  MessageSquare,
  Calendar,
  User,
  ChevronDown,
  ChevronUp,
  Loader2
} from 'lucide-react';
import { Suggestion, SuggestionStatus, SuggestionPriority, SuggestionType } from '../../types/ai-assistant';
import { cn } from '../../lib/utils';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept?: (suggestionId: number) => Promise<void>;
  onReject?: (suggestionId: number) => Promise<void>;
  onRate?: (suggestionId: number, rating: number) => Promise<void>;
  onFeedback?: (suggestionId: number, feedback: string) => Promise<void>;
  showActions?: boolean;
  className?: string;
}

const statusConfig = {
  [SuggestionStatus.PENDING]: {
    label: '待处理',
    color: 'bg-yellow-100 text-yellow-800',
    icon: Clock
  },
  [SuggestionStatus.ACCEPTED]: {
    label: '已接受',
    color: 'bg-green-100 text-green-800',
    icon: CheckCircle
  },
  [SuggestionStatus.REJECTED]: {
    label: '已拒绝',
    color: 'bg-red-100 text-red-800',
    icon: XCircle
  },
  [SuggestionStatus.IMPLEMENTED]: {
    label: '已实施',
    color: 'bg-blue-100 text-blue-800',
    icon: CheckCircle
  },
  [SuggestionStatus.CANCELLED]: {
    label: '已取消',
    color: 'bg-gray-100 text-gray-800',
    icon: XCircle
  }
};

const priorityConfig = {
  [SuggestionPriority.LOW]: {
    label: '低',
    color: 'bg-gray-100 text-gray-800'
  },
  [SuggestionPriority.MEDIUM]: {
    label: '中',
    color: 'bg-blue-100 text-blue-800'
  },
  [SuggestionPriority.HIGH]: {
    label: '高',
    color: 'bg-orange-100 text-orange-800'
  },
  [SuggestionPriority.CRITICAL]: {
    label: '紧急',
    color: 'bg-red-100 text-red-800'
  }
};

const typeConfig = {
  [SuggestionType.OPTIMIZATION]: {
    label: '优化建议',
    color: 'bg-purple-100 text-purple-800'
  },
  [SuggestionType.IMPROVEMENT]: {
    label: '改进建议',
    color: 'bg-green-100 text-green-800'
  },
  [SuggestionType.RISK_MITIGATION]: {
    label: '风险缓解',
    color: 'bg-red-100 text-red-800'
  },
  [SuggestionType.QUALITY_ENHANCEMENT]: {
    label: '质量提升',
    color: 'bg-blue-100 text-blue-800'
  },
  [SuggestionType.PROCESS_IMPROVEMENT]: {
    label: '流程改进',
    color: 'bg-indigo-100 text-indigo-800'
  }
};

export function SuggestionCard({
  suggestion,
  onAccept,
  onReject,
  onRate,
  onFeedback,
  showActions = true,
  className
}: SuggestionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRating, setIsRating] = useState(false);
  const [isFeedback, setIsFeedback] = useState(false);
  const [feedback, setFeedback] = useState(suggestion.user_feedback || '');
  const [rating, setRating] = useState(suggestion.user_rating || 0);
  const [isLoading, setIsLoading] = useState(false);

  const statusInfo = statusConfig[suggestion.status];
  const priorityInfo = priorityConfig[suggestion.priority];
  const typeInfo = typeConfig[suggestion.type];
  const StatusIcon = statusInfo.icon;

  const handleAccept = async () => {
    if (!onAccept) return;
    
    setIsLoading(true);
    try {
      await onAccept(suggestion.id);
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    if (!onReject) return;
    
    setIsLoading(true);
    try {
      await onReject(suggestion.id);
    } catch (error) {
      console.error('Failed to reject suggestion:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRating = async (newRating: number) => {
    if (!onRate) return;
    
    setRating(newRating);
    try {
      await onRate(suggestion.id, newRating);
      setIsRating(false);
    } catch (error) {
      console.error('Failed to rate suggestion:', error);
      setRating(suggestion.user_rating || 0);
    }
  };

  const handleFeedback = async () => {
    if (!onFeedback) return;
    
    try {
      await onFeedback(suggestion.id, feedback);
      setIsFeedback(false);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const canTakeAction = suggestion.status === SuggestionStatus.PENDING;
  const isImplemented = suggestion.status === SuggestionStatus.IMPLEMENTED;

  return (
    <Card className={cn(
      'transition-all duration-200 hover:shadow-md',
      suggestion._syncing && 'opacity-75',
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-semibold mb-2 line-clamp-2">
              {suggestion.title}
            </CardTitle>
            
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <Badge className={statusInfo.color}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {statusInfo.label}
              </Badge>
              
              <Badge variant="outline" className={priorityInfo.color}>
                {priorityInfo.label}
              </Badge>
              
              <Badge variant="outline" className={typeInfo.color}>
                {typeInfo.label}
              </Badge>

              {suggestion._syncing && (
                <Badge variant="outline" className="bg-blue-50 text-blue-600">
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  同步中
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-4 text-sm text-gray-500">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {formatDate(suggestion.created_at)}
              </div>
              
              {suggestion.ai_provider && (
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {suggestion.ai_provider}
                </div>
              )}

              {suggestion.user_rating && (
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  {suggestion.user_rating}/5
                </div>
              )}
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-2 shrink-0"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="space-y-4">
          {/* 建议描述 */}
          <div className={cn(
            'text-gray-700',
            !isExpanded && 'line-clamp-3'
          )}>
            {suggestion.description}
          </div>

          {/* 展开内容 */}
          {isExpanded && (
            <div className="space-y-4 border-t pt-4">
              {/* 行动项 */}
              {suggestion.action_items && suggestion.action_items.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">行动项</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                    {suggestion.action_items.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 预期收益 */}
              {suggestion.expected_benefit && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">预期收益</h4>
                  <p className="text-sm text-gray-600">{suggestion.expected_benefit}</p>
                </div>
              )}

              {/* 预估工作量 */}
              {suggestion.estimated_effort && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">预估工作量</h4>
                  <p className="text-sm text-gray-600">{suggestion.estimated_effort}</p>
                </div>
              )}

              {/* 实施说明 */}
              {suggestion.implementation_notes && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">实施说明</h4>
                  <p className="text-sm text-gray-600">{suggestion.implementation_notes}</p>
                </div>
              )}

              {/* 用户反馈 */}
              {suggestion.user_feedback && !isFeedback && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">用户反馈</h4>
                  <p className="text-sm text-gray-600">{suggestion.user_feedback}</p>
                </div>
              )}

              {/* 实施信息 */}
              {isImplemented && suggestion.implemented_at && (
                <div className="bg-green-50 p-3 rounded-lg">
                  <h4 className="font-medium text-green-900 mb-2">实施信息</h4>
                  <div className="text-sm text-green-700 space-y-1">
                    <p>实施时间: {formatDate(suggestion.implemented_at)}</p>
                    {suggestion.implementation_result && (
                      <p>实施结果: {suggestion.implementation_result}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 操作按钮 */}
          {showActions && (
            <div className="flex flex-wrap gap-2 pt-2 border-t">
              {canTakeAction && (
                <>
                  <Button
                    size="sm"
                    onClick={handleAccept}
                    disabled={isLoading}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-1" />
                    )}
                    接受
                  </Button>
                  
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    disabled={isLoading}
                    className="border-red-200 text-red-600 hover:bg-red-50"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4 mr-1" />
                    )}
                    拒绝
                  </Button>
                </>
              )}

              {/* 评分按钮 */}
              {!isRating && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsRating(true)}
                >
                  <Star className="w-4 h-4 mr-1" />
                  {suggestion.user_rating ? '修改评分' : '评分'}
                </Button>
              )}

              {/* 反馈按钮 */}
              {!isFeedback && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsFeedback(true)}
                >
                  <MessageSquare className="w-4 h-4 mr-1" />
                  {suggestion.user_feedback ? '修改反馈' : '添加反馈'}
                </Button>
              )}
            </div>
          )}

          {/* 评分界面 */}
          {isRating && (
            <div className="bg-gray-50 p-3 rounded-lg space-y-3">
              <h4 className="font-medium text-gray-900">为此建议评分</h4>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => handleRating(star)}
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center transition-colors',
                      star <= rating
                        ? 'bg-yellow-400 text-white'
                        : 'bg-gray-200 text-gray-400 hover:bg-gray-300'
                    )}
                  >
                    <Star className="w-4 h-4" />
                  </button>
                ))}
                <span className="ml-2 text-sm text-gray-600">
                  {rating > 0 ? `${rating}/5` : '请选择评分'}
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsRating(false)}
                >
                  取消
                </Button>
              </div>
            </div>
          )}

          {/* 反馈界面 */}
          {isFeedback && (
            <div className="bg-gray-50 p-3 rounded-lg space-y-3">
              <h4 className="font-medium text-gray-900">添加反馈</h4>
              <Textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="请输入您对此建议的反馈..."
                className="min-h-[80px]"
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleFeedback}
                  disabled={!feedback.trim()}
                >
                  提交反馈
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setIsFeedback(false);
                    setFeedback(suggestion.user_feedback || '');
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}