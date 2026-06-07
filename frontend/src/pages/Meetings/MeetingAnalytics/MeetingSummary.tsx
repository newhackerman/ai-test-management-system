import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface MeetingSummaryProps {
  meetingId?: number;
}

export const MeetingSummary: React.FC<MeetingSummaryProps> = () => (
  <MeetingPlaceholder title="会议摘要" description="会议摘要入口已恢复。" />
);

export default MeetingSummary;
