import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface MeetingRoomProps {
  meetingId?: string;
  meetingCode?: string;
}

const MeetingRoom: React.FC<MeetingRoomProps> = () => (
  <MeetingPlaceholder title="会议室" />
);

export default MeetingRoom;
