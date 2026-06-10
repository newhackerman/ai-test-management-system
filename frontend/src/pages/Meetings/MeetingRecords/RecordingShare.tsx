import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingShareProps {
  recordingId?: string;
}

export const RecordingShare: React.FC<RecordingShareProps> = () => (
  <MeetingPlaceholder title="录制分享" />
);

export default RecordingShare;
