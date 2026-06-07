import React, { useState } from 'react';
import { MessageSquare, Send, ThumbsUp, Trash2 } from 'lucide-react';

import { Avatar, AvatarFallback } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Textarea } from '@/components/ui/Textarea';

export interface DiscussionMessage {
  id: number;
  requirement_id: number;
  parent_id?: number;
  content: string;
  message_type: 'text' | 'mention' | 'system';
  author_id: number;
  author: {
    id: number;
    username: string;
    real_name?: string;
    avatar?: string;
    role?: string;
  };
  reactions?: Array<{ type: 'like' | 'dislike' | 'agree' | 'disagree'; count: number; users: number[] }>;
  is_pinned: boolean;
  is_edited: boolean;
  edited_at?: string;
  created_at: string;
  updated_at: string;
  replies?: DiscussionMessage[];
  mentions?: Array<{ user_id: number; username: string; real_name?: string }>;
  attachments?: Array<{ id: string; name: string; url: string; type: string; size: number }>;
}

interface DiscussionPanelProps {
  requirementId: number;
  currentUserId: number;
  onMessageSent?: (message: DiscussionMessage) => void;
  onMessageUpdated?: (message: DiscussionMessage) => void;
  onMessageDeleted?: (messageId: number) => void;
  onReactionAdded?: (messageId: number, reactionType: string) => void;
  className?: string;
}

export const DiscussionPanel: React.FC<DiscussionPanelProps> = ({
  requirementId,
  currentUserId,
  onMessageSent,
  onMessageDeleted,
  onReactionAdded,
  className,
}) => {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [content, setContent] = useState('');

  const sendMessage = () => {
    const text = content.trim();
    if (!text) return;
    const message: DiscussionMessage = {
      id: Date.now(),
      requirement_id: requirementId,
      content: text,
      message_type: 'text',
      author_id: currentUserId,
      author: { id: currentUserId, username: 'current_user', real_name: '当前用户' },
      reactions: [],
      is_pinned: false,
      is_edited: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      replies: [],
    };
    setMessages((prev) => [message, ...prev]);
    setContent('');
    onMessageSent?.(message);
  };

  const deleteMessage = (id: number) => {
    setMessages((prev) => prev.filter((message) => message.id !== id));
    onMessageDeleted?.(id);
  };

  const likeMessage = (id: number) => {
    setMessages((prev) => prev.map((message) => {
      if (message.id !== id) return message;
      const like = message.reactions?.find((reaction) => reaction.type === 'like');
      const reactions = like
        ? message.reactions?.map((reaction) => reaction.type === 'like' ? { ...reaction, count: reaction.count + 1 } : reaction)
        : [...(message.reactions ?? []), { type: 'like' as const, count: 1, users: [currentUserId] }];
      return { ...message, reactions };
    }));
    onReactionAdded?.(id, 'like');
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <MessageSquare className="h-5 w-5" />
          需求讨论
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="输入讨论内容" />
          <div className="flex justify-end">
            <Button type="button" onClick={sendMessage} disabled={!content.trim()}>
              <Send className="mr-2 h-4 w-4" />
              发送
            </Button>
          </div>
        </div>
        <div className="space-y-3">
          {messages.map((message) => (
            <div key={message.id} className="rounded-md border p-3">
              <div className="flex items-start gap-3">
                <Avatar>
                  <AvatarFallback>{(message.author.real_name || message.author.username).slice(0, 1).toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{message.author.real_name || message.author.username}</span>
                    {message.author.role && <Badge variant="outline">{message.author.role}</Badge>}
                    <span className="text-xs text-muted-foreground">{new Date(message.created_at).toLocaleString('zh-CN')}</span>
                  </div>
                  <div className="mt-2 whitespace-pre-wrap text-sm">{message.content}</div>
                  <div className="mt-3 flex gap-2">
                    <Button type="button" variant="ghost" size="sm" onClick={() => likeMessage(message.id)}>
                      <ThumbsUp className="mr-1 h-4 w-4" />
                      {message.reactions?.find((reaction) => reaction.type === 'like')?.count ?? 0}
                    </Button>
                    {message.author_id === currentUserId && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => deleteMessage(message.id)}>
                        <Trash2 className="mr-1 h-4 w-4" />
                        删除
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          {messages.length === 0 && <div className="flex h-32 items-center justify-center text-muted-foreground">暂无讨论</div>}
        </div>
      </CardContent>
    </Card>
  );
};

export default DiscussionPanel;
