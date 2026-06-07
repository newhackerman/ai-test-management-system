import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface RecordingDownloadProps {
  recordingId?: string;
}

export const RecordingDownload: React.FC<RecordingDownloadProps> = () => (
  <MeetingPlaceholder title="录制下载" description="录制下载入口已恢复。" />
);

export default RecordingDownload;
