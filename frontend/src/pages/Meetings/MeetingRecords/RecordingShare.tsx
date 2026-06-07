import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingShareProps {
  recordingId?: string;
}

export const RecordingShare: React.FC<RecordingShareProps> = () => (
  <MeetingPlaceholder title="录制分享" description="录制分享入口已恢复。" />
);

export default RecordingShare;
