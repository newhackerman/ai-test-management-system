import React, { useMemo, useState } from 'react';
import { Archive, Loader2, MessageCircle, Plus, Search, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Input } from '../ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/Select';
import { Skeleton } from '../ui/Skeleton';
import { useConversationManager, useConversations, useSearchConversations } from '../../hooks/useConversations';
import { ConversationGroup, ConversationResponse, SessionStatus } from '../../services/conversation-service';

interface ConversationListProps {
  onSelectConversation: (conversation: ConversationResponse) => void;
  onCreateConversation: () => void;
  selectedConversationId?: number | null;
  className?: string;
}

const statusLabels: Record<SessionStatus, string> = {
  [SessionStatus.ACTIVE]: '活跃',
  [SessionStatus.ARCHIVED]: '已归档',
  [SessionStatus.DELETED]: '已删除',
};

const groupLabels: Record<ConversationGroup, string> = {
  [ConversationGroup.WORK]: '工作',
  [ConversationGroup.STUDY]: '学习',
  [ConversationGroup.PROJECT]: '项目',
  [ConversationGroup.PERSONAL]: '个人',
  [ConversationGroup.RESEARCH]: '研究',
  [ConversationGroup.DEVELOPMENT]: '开发',
  [ConversationGroup.TESTING]: '测试',
  [ConversationGroup.OTHER]: '其他',
};

export function ConversationList({
  onSelectConversation,
  onCreateConversation,
  selectedConversationId,
  className = '',
}: ConversationListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [groupFilter, setGroupFilter] = useState<ConversationGroup | 'all'>('all');
  const { deleteConversation, archiveConversation, isLoading: managing } = useConversationManager();
  const { searchResults, isSearching, searchConversations, clearSearch } = useSearchConversations();

  const params = useMemo(
    () => ({
      status_filter: statusFilter === 'all' ? undefined : statusFilter,
      group: groupFilter === 'all' ? undefined : groupFilter,
      sort_by: 'last_activity_at',
      sort_order: 'desc',
      page: 1,
      size: 30,
    }),
    [groupFilter, statusFilter],
  );

  const { data, isLoading, error } = useConversations(params);
  const conversations = searchResults?.conversations ?? data?.conversations ?? [];
  const totalCount = searchResults?.total_count ?? data?.total_count ?? 0;

  const handleSearch = async (value: string) => {
    setSearchQuery(value);
    if (!value.trim()) {
      clearSearch();
      return;
    }
    await searchConversations({
      query: value.trim(),
      status: statusFilter === 'all' ? undefined : statusFilter,
      group: groupFilter === 'all' ? undefined : groupFilter,
      page: 1,
      size: 30,
    });
  };

  const handleDelete = async (conversation: ConversationResponse, event: React.MouseEvent) => {
    event.stopPropagation();
    if (!window.confirm(`确定删除对话“${conversation.title}”吗？`)) return;
    await deleteConversation(conversation.id);
  };

  const handleArchive = async (conversation: ConversationResponse, event: React.MouseEvent) => {
    event.stopPropagation();
    await archiveConversation(conversation.id);
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-lg">对话列表</CardTitle>
          <Button type="button" size="sm" onClick={onCreateConversation}>
            <Plus className="mr-2 h-4 w-4" />
            新建
          </Button>
        </div>

        <div className="grid gap-2 md:grid-cols-[1fr_120px_120px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              value={searchQuery}
              onChange={(event) => handleSearch(event.target.value)}
              placeholder="搜索对话标题"
            />
          </div>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as SessionStatus | 'all')}>
            <SelectTrigger>
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              {Object.values(SessionStatus).map((status) => (
                <SelectItem key={status} value={status}>
                  {statusLabels[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={groupFilter} onValueChange={(value) => setGroupFilter(value as ConversationGroup | 'all')}>
            <SelectTrigger>
              <SelectValue placeholder="分组" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分组</SelectItem>
              {Object.values(ConversationGroup).map((group) => (
                <SelectItem key={group} value={group}>
                  {groupLabels[group]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        {(isLoading || isSearching) && (
          <div className="space-y-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {error && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">加载对话失败</div>}

        {!isLoading && !isSearching && conversations.length === 0 && (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-muted-foreground">
            <MessageCircle className="h-8 w-8" />
            <div>{searchQuery ? '没有找到匹配的对话' : '暂无对话'}</div>
          </div>
        )}

        {!isLoading && !isSearching && conversations.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            className={`w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/60 ${
              selectedConversationId === conversation.id ? 'border-primary bg-primary/5' : ''
            }`}
            onClick={() => onSelectConversation(conversation)}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{conversation.title || '未命名对话'}</div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">{statusLabels[conversation.status] ?? conversation.status}</Badge>
                  {conversation.ai_model && <span>{conversation.ai_model}</span>}
                  <span>{conversation.message_count ?? 0} 条消息</span>
                  {conversation.last_activity_at && (
                    <span>
                      {formatDistanceToNow(new Date(conversation.last_activity_at), { addSuffix: true, locale: zhCN })}
                    </span>
                  )}
                </div>
                {conversation.tags && conversation.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {conversation.tags.slice(0, 4).map((tag) => (
                      <Badge key={tag} variant="secondary">{tag}</Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                <Button type="button" variant="ghost" size="icon" disabled={managing} onClick={(event) => handleArchive(conversation, event)}>
                  {managing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Archive className="h-4 w-4" />}
                </Button>
                <Button type="button" variant="ghost" size="icon" disabled={managing} onClick={(event) => handleDelete(conversation, event)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </button>
        ))}

        <div className="pt-2 text-xs text-muted-foreground">共 {totalCount} 个对话</div>
      </CardContent>
    </Card>
  );
}
