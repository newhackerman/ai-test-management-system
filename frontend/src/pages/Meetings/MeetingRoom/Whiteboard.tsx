import React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

interface WhiteboardProps {
  meetingId?: number;
}

const Whiteboard: React.FC<WhiteboardProps> = () => (
  <Card>
    <CardHeader><CardTitle className="text-base">白板</CardTitle></CardHeader>
    <CardContent className="flex h-64 items-center justify-center text-muted-foreground">白板入口已恢复</CardContent>
  </Card>
);

export default Whiteboard;
