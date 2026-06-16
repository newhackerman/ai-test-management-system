// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  Bot,
  Bookmark,
  Copy,
  Download,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  Trash2,
  User,
  Wifi,
  WifiOff,
} from 'lucide-react';

import { Alert, AlertDescription } from '../ui/Alert';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent } from '../ui/Card';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/DropdownMenu';
import { Input } from '../ui/Input';
import { Switch } from '../ui/Switch';
import { useMessages, useSendMessage } from '../../hooks/useConversations';
import { useStreamingChat } from '../../hooks/useStreaming';
import {
  ContentType,
  ConversationResponse,
  MessageResponse,
  MessageRole,
} from '../../services/conversation-service';
import { cn } from '../../lib/utils';
import MessageInput from './MessageInput';

interface ChatInterfaceProps {
  conversation: ConversationResponse;
  className?: string;
  onSendMessage?: (message: string) => void;
  onNewConversation?: () => void;
  onConversationUpdate?: (conversation: ConversationResponse) => void;
  theme?: 'light' | 'dark' | 'auto';
  density?: 'compact' | 'standard' | 'comfortable';
  showAvatar?: boolean;
  showTimestamp?: boolean;
  showTokenCount?: boolean;
  enableSounds?: boolean;
  enableStreaming?: boolean;
  enableVoiceInput?: boolean;
  enableFileUpload?: boolean;
  enableTemplates?: boolean;
  enableMarkdown?: boolean;
  maxMessageLength?: number;
  autoScroll?: boolean;
  showTypingIndicator?: boolean;
  enableOfflineMode?: boolean;
}

interface ChatSettings {
  streamingEnabled: boolean;
  autoScroll: boolean;
  soundEnabled: boolean;
  showTimestamps: boolean;
  showTokenCounts: boolean;
  compactMode: boolean;
}

type FilterValue = 'all' | 'user' | 'assistant' | 'system';

const normalizeRole = (role: string) => String(role || '').toUpperCase();

const formatDateTime = (value?: string) => {
  if (!value) return '';
  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  });
};

const toMessageResponse = (message: any, index: number, conversationId: number): MessageResponse => ({
  id: Number(message.id || `0${index}`),
  session_id: conversationId,
  role: normalizeRole(message.role) as MessageRole,
  content: message.content || '',
  content_type: message.content_type || ContentType.TEXT,
  tokens_used: message.tokens_used || 0,
  is_streaming: Boolean(message.is_streaming || message.isStreaming),
  is_error: Boolean(message.is_error),
  is_bookmarked: Boolean(message.is_bookmarked),
  created_at: message.created_at || message.timestamp || new Date().toISOString(),
  updated_at: message.updated_at,
  message_metadata: message.message_metadata || message.metadata,
});

export function ChatInterface({
  conversation,
  className,
  onSendMessage,
  onNewConversation,
  onConversationUpdate,
  density = 'standard',
  showAvatar = true,
  showTimestamp = true,
  showTokenCount = true,
  enableSounds = true,
  enableStreaming = true,
  enableVoiceInput = false,
  enableFileUpload = true,
  enableTemplates = true,
  enableMarkdown = true,
  maxMessageLength = 10000,
  autoScroll = true,
}: ChatInterfaceProps) {
  const [settings, setSettings] = useState<ChatSettings>({
    streamingEnabled: enableStreaming,
    autoScroll,
    soundEnabled: enableSounds,
    showTimestamps: showTimestamp,
    showTokenCounts: showTokenCount,
    compactMode: density === 'compact',
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [messageFilter, setMessageFilter] = useState<FilterValue>('all');
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<number>>(new Set());
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const {
    data: messagesData,
    isLoading,
    error: messagesError,
    refetch,
  } = useMessages(conversation.id);
  const sendMessageMutation = useSendMessage();
  const {
    messages: streamingMessages,
    isStreaming,
    error: streamingError,
    sendMessage: sendStreamingMessage,
    stopStreaming,
    clearError: clearStreamingError,
  } = useStreamingChat(conversation.id);

  const persistedMessages = useMemo(
    () => (messagesData?.messages || []).map((message, index) => toMessageResponse(message, index, conversation.id)),
    [conversation.id, messagesData?.messages],
  );

  const liveMessages = useMemo(
    () => streamingMessages.map((message, index) => toMessageResponse(message, index + 100000, conversation.id)),
    [conversation.id, streamingMessages],
  );

  const allMessages = settings.streamingEnabled && liveMessages.length > 0 ? liveMessages : persistedMessages;

  const filteredMessages = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    return allMessages.filter((message) => {
      const roleMatched = messageFilter === 'all' || normalizeRole(message.role) === messageFilter.toUpperCase();
      const keywordMatched = !keyword || message.content.toLowerCase().includes(keyword);
      return roleMatched && keywordMatched;
    });
  }, [allMessages, messageFilter, searchQuery]);

  const stats = useMemo(() => {
    const totalTokens = allMessages.reduce((sum, message) => sum + (message.tokens_used || 0), 0);
    return {
      total: allMessages.length,
      user: allMessages.filter((message) => normalizeRole(message.role) === MessageRole.USER).length,
      assistant: allMessages.filter((message) => normalizeRole(message.role) === MessageRole.ASSISTANT).length,
      totalTokens,
    };
  }, [allMessages]);

  useEffect(() => {
    if (settings.autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredMessages, settings.autoScroll]);

  const updateSettings = (updates: Partial<ChatSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const playSound = () => {
    if (settings.soundEnabled) {
      audioRef.current?.play().catch(() => undefined);
    }
  };

  const handleSend = async (content: string, contentType?: ContentType, metadata?: Record<string, any>) => {
    if (!content.trim()) return;
    onSendMessage?.(content);
    playSound();

    try {
      if (settings.streamingEnabled) {
        await sendStreamingMessage(content, {
          content_type: contentType || ContentType.TEXT,
          ...metadata,
          timestamp: new Date().toISOString(),
        });
      } else {
        await sendMessageMutation.mutateAsync({
          conversationId: conversation.id,
          request: {
            content,
            content_type: contentType || ContentType.TEXT,
            metadata,
          },
        });

        onConversationUpdate?.({
          ...conversation,
          message_count: (conversation.message_count || 0) + 1,
          last_activity_at: new Date().toISOString(),
        });
      }
    } catch (error) {
      console.error('Send message failed:', error);
    }
  };

  const handleCopy = async (message: MessageResponse) => {
    await navigator.clipboard.writeText(message.content);
    setCopiedId(message.id);
    window.setTimeout(() => setCopiedId(null), 1500);
  };

  const handleBookmark = (messageId: number) => {
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  };

  const exportConversation = () => {
    const content = allMessages
      .map((message) => `[${formatDateTime(message.created_at)}] ${message.role}\n${message.content}`)
      .join('\n\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${conversation.title || 'conversation'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const sending = sendMessageMutation.isPending || isStreaming;
  const errorText = streamingError || sendMessageMutation.error?.message || messagesError?.message;

  return (
    <div className={cn('flex h-full flex-col bg-white', settings.compactMode && 'text-sm', className)}>
      <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-3 dark:bg-gray-800/50">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
            <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate font-medium">{conversation.title || 'AI 对话'}</h3>
              <Badge variant="outline" className="text-xs">
                {settings.streamingEnabled ? '流式' : '普通'}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span>{conversation.ai_provider || 'AI'}</span>
              {conversation.ai_model && <span>{conversation.ai_model}</span>}
              <span>{stats.total} 条消息</span>
              {settings.showTokenCounts && stats.totalTokens > 0 && <span>{stats.totalTokens} tokens</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative hidden sm:block">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="搜索消息"
              className="h-8 w-48 pl-8"
            />
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={exportConversation}>
            <Download className="h-4 w-4" />
          </Button>
          {onNewConversation && (
            <Button type="button" variant="outline" size="sm" onClick={onNewConversation}>
              新建
            </Button>
          )}
          <SettingsMenu
            settings={settings}
            updateSettings={updateSettings}
            messageFilter={messageFilter}
            setMessageFilter={setMessageFilter}
          />
        </div>
      </div>

      <div className="flex items-center justify-between border-b px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-2">
          {navigator.onLine ? <Wifi className="h-3.5 w-3.5 text-green-600 dark:text-green-400" /> : <WifiOff className="h-3.5 w-3.5 text-orange-600 dark:text-orange-400" />}
          <span>{navigator.onLine ? '在线' : '离线'}</span>
          {sending && (
            <span className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              正在处理
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span>用户 {stats.user}</span>
          <span>助手 {stats.assistant}</span>
        </div>
      </div>

      {errorText && (
        <div className="px-4 pt-3">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between gap-3">
              <span>{errorText}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  clearStreamingError?.();
                  sendMessageMutation.reset?.();
                }}
              >
                关闭
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            加载消息中...
          </div>
        ) : filteredMessages.length === 0 ? (
          <EmptyState enableTemplates={enableTemplates} />
        ) : (
          <div className={cn('space-y-4', settings.compactMode && 'space-y-2')}>
            {filteredMessages.map((message) => (
              <MessageRow
                key={message.id}
                message={message}
                showAvatar={showAvatar}
                showTimestamp={settings.showTimestamps}
                showTokenCount={settings.showTokenCounts}
                bookmarked={bookmarkedIds.has(message.id) || message.is_bookmarked}
                copied={copiedId === message.id}
                onCopy={() => handleCopy(message)}
                onBookmark={() => handleBookmark(message.id)}
              />
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <MessageInput
        onSend={handleSend}
        disabled={sendMessageMutation.isPending}
        isStreaming={isStreaming}
        onStopStreaming={stopStreaming}
        showTemplates={enableTemplates}
        showFileUpload={enableFileUpload}
        showVoiceInput={enableVoiceInput}
        maxLength={maxMessageLength}
        supportedTypes={enableMarkdown ? [ContentType.TEXT, ContentType.MARKDOWN, ContentType.CODE] : [ContentType.TEXT]}
        className="border-t"
      />

      <audio ref={audioRef} preload="auto" className="hidden">
        <source src="/sounds/notification.mp3" type="audio/mpeg" />
        <source src="/sounds/notification.ogg" type="audio/ogg" />
      </audio>
    </div>
  );
}

const SettingsMenu: React.FC<{
  settings: ChatSettings;
  updateSettings: (updates: Partial<ChatSettings>) => void;
  messageFilter: FilterValue;
  setMessageFilter: (value: FilterValue) => void;
}> = ({ settings, updateSettings, messageFilter, setMessageFilter }) => (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button type="button" variant="outline" size="sm">
        <Settings className="h-4 w-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-64">
      <DropdownMenuLabel>聊天设置</DropdownMenuLabel>
      <DropdownMenuSeparator />
      <SettingSwitch label="流式响应" checked={settings.streamingEnabled} onChange={(value) => updateSettings({ streamingEnabled: value })} />
      <SettingSwitch label="自动滚动" checked={settings.autoScroll} onChange={(value) => updateSettings({ autoScroll: value })} />
      <SettingSwitch label="声音提醒" checked={settings.soundEnabled} onChange={(value) => updateSettings({ soundEnabled: value })} />
      <SettingSwitch label="显示时间" checked={settings.showTimestamps} onChange={(value) => updateSettings({ showTimestamps: value })} />
      <SettingSwitch label="显示 Token" checked={settings.showTokenCounts} onChange={(value) => updateSettings({ showTokenCounts: value })} />
      <SettingSwitch label="紧凑模式" checked={settings.compactMode} onChange={(value) => updateSettings({ compactMode: value })} />
      <DropdownMenuSeparator />
      <DropdownMenuLabel>消息筛选</DropdownMenuLabel>
      {[
        ['all', '全部消息'],
        ['user', '用户消息'],
        ['assistant', '助手消息'],
        ['system', '系统消息'],
      ].map(([value, label]) => (
        <DropdownMenuCheckboxItem
          key={value}
          checked={messageFilter === value}
          onCheckedChange={() => setMessageFilter(value as FilterValue)}
        >
          {label}
        </DropdownMenuCheckboxItem>
      ))}
    </DropdownMenuContent>
  </DropdownMenu>
);

const SettingSwitch: React.FC<{ label: string; checked: boolean; onChange: (value: boolean) => void }> = ({ label, checked, onChange }) => (
  <div className="flex items-center justify-between px-2 py-2">
    <span className="text-sm">{label}</span>
    <Switch checked={checked} onCheckedChange={onChange} />
  </div>
);

const EmptyState: React.FC<{ enableTemplates: boolean }> = ({ enableTemplates }) => (
  <div className="flex h-full flex-col items-center justify-center py-12 text-center">
    <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
      <Bot className="h-8 w-8 text-blue-600 dark:text-blue-400" />
    </div>
    <h3 className="mb-2 text-lg font-medium">开始对话</h3>
    <p className="mb-4 max-w-md text-gray-500 dark:text-gray-400">发送消息，与 AI 助手讨论测试设计、缺陷分析、代码审查或项目问题。</p>
    {enableTemplates && (
      <div className="flex flex-wrap justify-center gap-2">
        <Badge variant="outline" className="gap-1">
          <Sparkles className="h-3 w-3" />
          测试用例
        </Badge>
        <Badge variant="outline">缺陷分析</Badge>
        <Badge variant="outline">代码审查</Badge>
      </div>
    )}
  </div>
);

const MessageRow: React.FC<{
  message: MessageResponse;
  showAvatar: boolean;
  showTimestamp: boolean;
  showTokenCount: boolean;
  bookmarked: boolean;
  copied: boolean;
  onCopy: () => void;
  onBookmark: () => void;
}> = ({ message, showAvatar, showTimestamp, showTokenCount, bookmarked, copied, onCopy, onBookmark }) => {
  const isUser = normalizeRole(message.role) === MessageRole.USER;

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      {showAvatar && (
        <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full', isUser ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 dark:text-gray-300 dark:bg-gray-800')}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>
      )}
      <Card className={cn('max-w-[78%]', isUser ? 'bg-blue-600 text-white' : 'bg-white')}>
        <CardContent className="p-3">
          <div className="whitespace-pre-wrap break-words text-sm leading-6">{message.content}</div>
          <div className={cn('mt-3 flex flex-wrap items-center gap-2 text-xs', isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400')}>
            {showTimestamp && <span>{formatDateTime(message.created_at)}</span>}
            {showTokenCount && message.tokens_used > 0 && <span>{message.tokens_used} tokens</span>}
            {message.is_streaming && <span>生成中...</span>}
            {message.is_error && <span className="text-red-500 dark:text-red-400">异常</span>}
            <div className="ml-auto flex items-center gap-1">
              <Button type="button" variant="ghost" size="sm" className="h-7 px-2" onClick={onCopy}>
                <Copy className="mr-1 h-3.5 w-3.5" />
                {copied ? '已复制' : '复制'}
              </Button>
              <Button type="button" variant="ghost" size="sm" className="h-7 px-2" onClick={onBookmark}>
                <Bookmark className={cn('mr-1 h-3.5 w-3.5', bookmarked && 'fill-current')} />
                收藏
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ChatInterface;
