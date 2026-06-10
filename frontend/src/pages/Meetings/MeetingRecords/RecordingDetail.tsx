import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingDetailProps {
  recordingId?: string;
}

export const RecordingDetail: React.FC<RecordingDetailProps> = () => (
  <MeetingPlaceholder title="录制详情" />
);

export default RecordingDetail;
