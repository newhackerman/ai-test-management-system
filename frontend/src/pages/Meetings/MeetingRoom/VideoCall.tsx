import React from 'react';
import { Video } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/Card';

interface VideoCallProps {
  streams?: any[];
}

const VideoCall: React.FC<VideoCallProps> = ({ streams = [] }) => (
  <Card>
    <CardContent className="flex h-80 items-center justify-center bg-muted/40 pt-6 text-muted-foreground">
      <div className="text-center">
        <Video className="mx-auto mb-2 h-8 w-8" />
        视频区域已恢复，当前 {streams.length} 路视频流
      </div>
    </CardContent>
  </Card>
);

export default VideoCall;
