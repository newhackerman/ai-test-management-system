import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface ActionItemsProps {
  meetingId?: number;
}

export const ActionItems: React.FC<ActionItemsProps> = () => (
  <MeetingPlaceholder title="行动项" />
);

export default ActionItems;
