import React from 'react';
import { MeetingPlaceholder } from './MeetingPlaceholder';

interface ParticipantInviteProps {
  meetingId?: number;
  onInviteSent?: () => void;
}

const ParticipantInvite: React.FC<ParticipantInviteProps> = () => (
  <MeetingPlaceholder title="邀请参会人" description="邀请入口已恢复，后续可继续接入用户选择和邮件邀请。" />
);

export default ParticipantInvite;
