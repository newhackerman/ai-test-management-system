import React, { useMemo, useState } from 'react';
import { Bell, Eye, MessageSquare, Send, Settings, Users } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Textarea } from '@/components/ui/Textarea';

interface RequirementCollaborationProps {
  requirementId: number;
  currentUserId: number;
}

interface Message {
  id: number;
  userId: number;
  author: string;
  content: string;
  createdAt: string;
}

const participants = [
  { id: 1, name: '产品经理', role: '负责人' },
  { id: 2, name: '开发工程师', role: '实现人' },
  { id: 3, name: '评审专家', role: '评审人' },
  { id: 4, name: '测试工程师', role: '验证人' }
];

const RequirementCollaboration: React.FC<RequirementCollaborationProps> = ({ requirementId, currentUserId }) => {
  const [activeTab, setActiveTab] = useState('discussion');
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, userId: 1, author: '产品经理', content: '请重点确认登录失败后的提示和锁定策略。', createdAt: '2026-06-01T09:30:00+08:00' },
    { id: 2, userId: 3, author: '评审专家', content: '建议补充验证码失败次数限制和审计日志要求。', createdAt: '2026-06-01T10:15:00+08:00' }
  ]);
  const [unreadNotifications, setUnreadNotifications] = useState(3);

  const requirement = useMemo(
    () => ({
      id: requirementId,
      title: '用户登录功能',
      description: '实现用户名密码登录、记住登录状态、忘记密码和异常提示等能力。',
      status: 'REVIEWING',
      priority: 'HIGH',
      assignee: '开发工程师',
      reviewer: '评审专家'
    }),
    [requirementId]
  );

  const sendMessage = () => {
    const content = draft.trim();
    if (!content) return;
    const author = participants.find((item) => item.id === currentUserId)?.name || '当前用户';
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        userId: currentUserId,
        author,
        content,
        createdAt: new Date().toISOString()
      }
    ]);
    setDraft('');
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex items-center justify-between border-b bg-card p-4">
        <div>
          <h1 className="text-xl font-semibold">{requirement.title}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline">{requirement.status}</Badge>
            <Badge variant="destructive">{requirement.priority}</Badge>
            <span className="text-sm text-muted-foreground">需求 #{requirement.id}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 md:flex">
            <Users className="h-4 w-4 text-muted-foreground" />
            <div className="flex -space-x-2">
              {participants.map((participant) => (
                <div
                  key={participant.id}
                  className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-background bg-primary/10 text-xs font-medium"
                  title={`${participant.name} - ${participant.role}`}
                >
                  {participant.name.charAt(0)}
                </div>
              ))}
            </div>
          </div>
          <Button variant="outline" size="sm" className="relative" onClick={() => setUnreadNotifications(0)}>
            <Bell className="h-4 w-4" />
            {unreadNotifications > 0 && (
              <Badge variant="destructive" className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center p-0 text-xs">
                {unreadNotifications}
              </Badge>
            )}
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid flex-1 lg:grid-cols-[360px_1fr]">
        <aside className="border-r bg-card p-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">需求详情</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <div className="text-muted-foreground">描述</div>
                <p className="mt-1">{requirement.description}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Info label="负责人" value={requirement.assignee} />
                <Info label="评审人" value={requirement.reviewer} />
              </div>
              <div>
                <div className="mb-2 text-muted-foreground">参与人员</div>
                <div className="space-y-2">
                  {participants.map((participant) => (
                    <div key={participant.id} className="flex items-center justify-between rounded-md border p-2">
                      <span>{participant.name}</span>
                      <Badge variant="outline">{participant.role}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </aside>

        <main className="flex min-w-0 flex-col">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-1 flex-col">
            <div className="border-b px-4 py-2">
              <TabsList>
                <TabsTrigger value="discussion" className="gap-2">
                  <MessageSquare className="h-4 w-4" />
                  讨论
                </TabsTrigger>
                <TabsTrigger value="review" className="gap-2">
                  <Eye className="h-4 w-4" />
                  评审
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="discussion" className="m-0 flex flex-1 flex-col">
              <div className="flex-1 space-y-3 overflow-auto p-4">
                {messages.map((message) => (
                  <div key={message.id} className="rounded-lg border bg-card p-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="font-medium">{message.author}</span>
                      <span className="text-xs text-muted-foreground">{new Date(message.createdAt).toLocaleString('zh-CN', { hour12: false })}</span>
                    </div>
                    <p className="text-sm">{message.content}</p>
                  </div>
                ))}
              </div>
              <div className="border-t p-4">
                <div className="flex gap-2">
                  <Textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="输入讨论内容..." rows={3} />
                  <Button onClick={sendMessage} className="self-end">
                    <Send className="mr-2 h-4 w-4" />
                    发送
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="review" className="m-0 p-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">评审决策</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input placeholder="评审意见摘要" />
                  <div className="grid gap-3 md:grid-cols-3">
                    <Button>通过</Button>
                    <Button variant="outline">要求修改</Button>
                    <Button variant="destructive">拒绝</Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </div>
  );
};

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
    </div>
  );
}

export default RequirementCollaboration;
