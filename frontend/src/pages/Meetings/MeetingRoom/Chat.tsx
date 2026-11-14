import React, { useEffect, useState } from 'react';
import { Send } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';

const Chat: React.FC = () => {
  const [text, setText] = useState('');
  const messages = useMeetingRoomStore((s) => s.messages);
  const sendMessage = useMeetingRoomStore((s) => s.sendMessage);
  const loadMessages = useMeetingRoomStore((s) => s.loadMessages);
  const meetingId = useMeetingRoomStore((s) => s.meeting?.id);

  useEffect(() => {
    if (meetingId) void loadMessages();
  }, [meetingId, loadMessages]);

  const send = () => {
    if (!text.trim()) return;
    void sendMessage(text.trim());
    setText('');
  };

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">会议聊天</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="max-h-64 space-y-2 overflow-y-auto">
          {messages.map((message) => (
            <div key={message.id} className="rounded-md border p-2 text-sm">
              <div className="mb-0.5 flex justify-between text-xs text-muted-foreground">
                <span>{message.senderName}</span>
                <span>{message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}</span>
              </div>
              <div>{message.content}</div>
              {message.status === 'failed' && <div className="text-xs text-red-500">发送失败</div>}
              {message.status === 'sending' && <div className="text-xs text-muted-foreground">发送中…</div>}
            </div>
          ))}
          {messages.length === 0 && <div className="text-sm text-muted-foreground">暂无消息</div>}
        </div>
        <div className="flex gap-2">
          <Input
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') send(); }}
            placeholder="输入消息，回车发送"
          />
          <Button type="button" onClick={send}><Send className="h-4 w-4" /></Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default Chat;
