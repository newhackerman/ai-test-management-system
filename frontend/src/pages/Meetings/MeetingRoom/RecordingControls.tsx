import React, { useEffect, useState } from 'react';
import { Circle, Pause, Play, Square } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { meetingRoomUtils, useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';

const RecordingControls: React.FC = () => {
  const isRecording = useMeetingRoomStore((s) => s.isRecording);
  const recordingStatus = useMeetingRoomStore((s) => s.recordingStatus);
  const recordingDuration = useMeetingRoomStore((s) => s.recordingDuration);
  const updateRecordingDuration = useMeetingRoomStore((s) => s.updateRecordingDuration);
  const startRecording = useMeetingRoomStore((s) => s.startRecording);
  const stopRecording = useMeetingRoomStore((s) => s.stopRecording);
  const pauseRecording = useMeetingRoomStore((s) => s.pauseRecording);
  const resumeRecording = useMeetingRoomStore((s) => s.resumeRecording);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isRecording) return;
    const timer = window.setInterval(() => setElapsed((v) => v + 1), 1000);
    return () => window.clearInterval(timer);
  }, [isRecording]);

  useEffect(() => {
    updateRecordingDuration(elapsed);
  }, [elapsed, updateRecordingDuration]);

  if (!isRecording && recordingStatus !== 'starting' && recordingStatus !== 'stopping') {
    return (
      <Button type="button" variant="outline" onClick={() => void startRecording()}>
        <Circle className="mr-2 h-4 w-4" />
        开始录制
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-red-600">
        ● 录制中 {meetingRoomUtils.formatRecordingDuration(recordingDuration)}
      </span>
      {recordingStatus === 'recording' ? (
        <Button type="button" size="sm" variant="outline" onClick={() => void pauseRecording()}>
          <Pause className="mr-1 h-4 w-4" />暂停
        </Button>
      ) : (
        <Button type="button" size="sm" variant="outline" onClick={() => void resumeRecording()}>
          <Play className="mr-1 h-4 w-4" />恢复
        </Button>
      )}
      <Button type="button" size="sm" variant="destructive" onClick={() => void stopRecording()}>
        <Square className="mr-1 h-4 w-4" />停止录制
      </Button>
    </div>
  );
};

export default RecordingControls;
