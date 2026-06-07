import React, { useState } from 'react';
import { Circle, Square } from 'lucide-react';

import { Button } from '@/components/ui/Button';

interface RecordingControlsProps {
  meetingId?: number;
}

const RecordingControls: React.FC<RecordingControlsProps> = () => {
  const [recording, setRecording] = useState(false);
  return (
    <Button type="button" variant={recording ? 'destructive' : 'outline'} onClick={() => setRecording((prev) => !prev)}>
      {recording ? <Square className="mr-2 h-4 w-4" /> : <Circle className="mr-2 h-4 w-4" />}
      {recording ? '停止录制' : '开始录制'}
    </Button>
  );
};

export default RecordingControls;
