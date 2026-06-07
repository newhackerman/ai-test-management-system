import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface MeetingRoomProps {
  meetingId?: string;
  meetingCode?: string;
}

const MeetingRoom: React.FC<MeetingRoomProps> = () => (
  <MeetingPlaceholder title="会议室" description="会议室入口已恢复，音视频、聊天和白板可继续逐项接入。" />
);

export default MeetingRoom;
