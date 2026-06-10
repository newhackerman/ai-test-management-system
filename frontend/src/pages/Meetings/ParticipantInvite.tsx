import React from 'react';
import { MeetingPlaceholder } from './MeetingPlaceholder';

interface ParticipantInviteProps {
  meetingId?: number;
  onInviteSent?: () => void;
}

const ParticipantInvite: React.FC<ParticipantInviteProps> = () => (
  <MeetingPlaceholder title="邀请参会人" />
);

export default ParticipantInvite;
