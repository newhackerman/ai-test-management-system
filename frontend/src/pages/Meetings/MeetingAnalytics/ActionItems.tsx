import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface ActionItemsProps {
  meetingId?: number;
}

export const ActionItems: React.FC<ActionItemsProps> = () => (
  <MeetingPlaceholder title="行动项" description="会议行动项入口已恢复。" />
);

export default ActionItems;
