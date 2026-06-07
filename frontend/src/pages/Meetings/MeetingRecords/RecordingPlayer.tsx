import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingPlayerProps {
  recordingId?: string;
}

export const RecordingPlayer: React.FC<RecordingPlayerProps> = () => (
  <MeetingPlaceholder title="录制播放" description="录制播放器入口已恢复。" />
);

export default RecordingPlayer;
