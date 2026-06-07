import React, { useMemo, useState } from 'react';
import {
  Bot,
  Bookmark,
  BookmarkCheck,
  Check,
  Clock,
  Copy,
  Edit3,
  MoreHorizontal,
  RefreshCw,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  User
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '../ui/DropdownMenu';
import { Textarea } from '../ui/Textarea';
import { ContentType, MessageResponse, MessageRole } from '../../services/conversation-service';
import { MarkdownRenderer } from './MarkdownRenderer';
import { CodeHighlight } from './CodeHighlight';
import { cn } from '../../lib/utils';

interface MessageBubbleProps {
  message: MessageResponse;
  isOwn?: boolean;
  showAvatar?: boolean;
  showActions?: boolean;
  showTimestamp?: boolean;
  showTokenCount?: boolean;
  showConfidenceScore?: boolean;
  showProvider?: boolean;
  compactMode?: boolean;
  groupWithNext?: boolean;
  groupWithPrevious?: boolean;
  isSelected?: boolean;
  isHighlighted?: boolean;
  onEdit?: (messageId: number, content: string) => void;
  onDelete?: (messageId: number) => void;
  onCopy?: (content: string) => void;
  onRate?: (messageId: number, rating: 'up' | 'down') => void;
  onBookmark?: (messageId: number, bookmarked: boolean) => void;
  onRegenerate?: (messageId: number) => void;
  onShare?: (messageId: number) => void;
  onExport?: (messageId: number, format: 'text' | 'markdown' | 'json') => void;
  onSelect?: (messageId: number, selected: boolean) => void;
  onSpeak?: (content: string) => void;
  onTranslate?: (messageId: number, targetLanguage: string) => void;
  renderCustomActions?: (message: MessageResponse) => React.ReactNode;
  renderCustomContent?: (message: MessageResponse) => React.ReactNode;
  className?: string;
}

const formatTime = (value?: string) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const getRoleLabel = (role: MessageRole) => {
  if (role === MessageRole.USER) return '用户';
  if (role === MessageRole.ASSISTANT) return 'AI 助手';
  return '系统';
};

export function MessageBubble({
  message,
  isOwn,
  showAvatar = true,
  showActions = true,
  showTimestamp = true,
  showTokenCount = true,
  showConfidenceScore = true,
  showProvider = true,
  compactMode = false,
  groupWithNext = false,
  groupWithPrevious = false,
  isSelected = false,
  isHighlighted = false,
  onEdit,
  onDelete,
  onCopy,
  onRate,
  onBookmark,
  onRegenerate,
  onExport,
  renderCustomActions,
  renderCustomContent,
  className
}: MessageBubbleProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [copied, setCopied] = useState(false);

  const ownMessage = isOwn ?? message.role === MessageRole.USER;
  const isAssistant = message.role === MessageRole.ASSISTANT;
  const hasMeta = Boolean(
    (showProvider && (message.ai_provider || message.ai_model)) ||
    (showTokenCount && message.tokens_used) ||
    (showConfidenceScore && message.confidence_score != null)
  );

  const bubbleClassName = useMemo(
    () =>
      cn(
        'max-w-[86%] rounded-lg border px-4 py-3 shadow-sm transition-colors',
        compactMode && 'px-3 py-2 text-sm',
        ownMessage
          ? 'ml-auto border-blue-600 bg-blue-600 text-white'
          : 'mr-auto border-gray-200 bg-white text-gray-900',
        message.is_error && 'border-red-300 bg-red-50 text-red-900',
        message.is_streaming && 'border-blue-200 bg-blue-50 text-gray-900',
        isSelected && 'ring-2 ring-blue-400',
        isHighlighted && 'shadow-md',
        groupWithPrevious && 'mt-1',
        groupWithNext && 'mb-1'
      ),
    [compactMode, groupWithNext, groupWithPrevious, isHighlighted, isSelected, message.is_error, message.is_streaming, ownMessage]
  );

  const handleCopy = async () => {
    try {
      await navigator.clipboard?.writeText(message.content);
    } catch {
      // The callback below still lets the host app handle copy in restricted browsers.
    }
    onCopy?.(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const handleSaveEdit = () => {
    const content = editContent.trim();
    if (!content) return;
    onEdit?.(message.id, content);
    setIsEditing(false);
  };

  const renderContent = () => {
    if (renderCustomContent) return renderCustomContent(message);

    if (isEditing) {
      return (
        <div className="space-y-2">
          <Textarea value={editContent} onChange={(event) => setEditContent(event.target.value)} rows={4} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
              取消
            </Button>
            <Button size="sm" onClick={handleSaveEdit}>
              保存
            </Button>
          </div>
        </div>
      );
    }

    if (message.content_type === ContentType.CODE) {
      return <CodeHighlight code={message.content} language="typescript" showLineNumbers={false} />;
    }

    if (message.content_type === ContentType.MARKDOWN || isAssistant) {
      return <MarkdownRenderer content={message.content} />;
    }

    return <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>;
  };

  return (
    <div className={cn('group flex gap-3', ownMessage && 'justify-end', className)}>
      {showAvatar && !ownMessage && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div className={bubbleClassName}>
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs opacity-80">
            {ownMessage ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
            <span>{getRoleLabel(message.role)}</span>
            {message.is_streaming && <Badge variant="secondary">生成中</Badge>}
            {message.is_error && <Badge variant="destructive">错误</Badge>}
          </div>

          {showActions && (
            <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
              <Button variant="ghost" size="sm" className="h-7 px-2" onClick={handleCopy}>
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              </Button>
              {onRate && (
                <>
                  <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => onRate(message.id, 'up')}>
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => onRate(message.id, 'down')}>
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </Button>
                </>
              )}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-7 px-2">
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {onEdit && (
                    <DropdownMenuItem onClick={() => setIsEditing(true)}>
                      <Edit3 className="mr-2 h-4 w-4" />
                      编辑
                    </DropdownMenuItem>
                  )}
                  {onBookmark && (
                    <DropdownMenuItem onClick={() => onBookmark(message.id, !message.is_bookmarked)}>
                      {message.is_bookmarked ? <BookmarkCheck className="mr-2 h-4 w-4" /> : <Bookmark className="mr-2 h-4 w-4" />}
                      {message.is_bookmarked ? '取消收藏' : '收藏'}
                    </DropdownMenuItem>
                  )}
                  {onRegenerate && (
                    <DropdownMenuItem onClick={() => onRegenerate(message.id)}>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      重新生成
                    </DropdownMenuItem>
                  )}
                  {onExport && (
                    <DropdownMenuItem onClick={() => onExport(message.id, 'markdown')}>
                      导出 Markdown
                    </DropdownMenuItem>
                  )}
                  {onDelete && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-red-600" onClick={() => onDelete(message.id)}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        删除
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              {renderCustomActions?.(message)}
            </div>
          )}
        </div>

        {renderContent()}

        {(showTimestamp || hasMeta) && (
          <div className={cn('mt-3 flex flex-wrap items-center gap-2 text-xs opacity-70', ownMessage && 'justify-end')}>
            {showTimestamp && message.created_at && (
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatTime(message.created_at)}
              </span>
            )}
            {showProvider && message.ai_provider && <span>{message.ai_provider}</span>}
            {showProvider && message.ai_model && <span>{message.ai_model}</span>}
            {showTokenCount && message.tokens_used > 0 && <span>{message.tokens_used} tokens</span>}
            {showConfidenceScore && message.confidence_score != null && (
              <span>置信度 {(message.confidence_score * 100).toFixed(0)}%</span>
            )}
          </div>
        )}
      </div>

      {showAvatar && ownMessage && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
