import React, { useState } from 'react';
import { Send } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

interface ChatProps {
  meetingId?: number;
}

const Chat: React.FC<ChatProps> = () => {
  const [text, setText] = useState('');
  const [messages, setMessages] = useState<string[]>([]);
  const send = () => {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, text.trim()]);
    setText('');
  };
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">会议聊天</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          {messages.map((message, index) => <div key={index} className="rounded-md border p-2 text-sm">{message}</div>)}
          {messages.length === 0 && <div className="text-sm text-muted-foreground">暂无消息</div>}
        </div>
        <div className="flex gap-2">
          <Input value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') send(); }} />
          <Button type="button" onClick={send}><Send className="h-4 w-4" /></Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default Chat;
