import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingDetailProps {
  recordingId?: string;
}

export const RecordingDetail: React.FC<RecordingDetailProps> = () => (
  <MeetingPlaceholder title="录制详情" description="录制详情入口已恢复。" />
);

export default RecordingDetail;
