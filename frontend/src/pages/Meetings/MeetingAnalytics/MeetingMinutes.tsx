import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface MeetingMinutesProps {
  meetingId?: number;
}

export const MeetingMinutes: React.FC<MeetingMinutesProps> = () => (
  <MeetingPlaceholder title="会议纪要" description="会议纪要入口已恢复。" />
);

export default MeetingMinutes;
