import React from 'react';
import { MeetingPlaceholder } from './MeetingPlaceholder';

interface SmartSchedulerProps {
  projectId?: number;
  onScheduleGenerated?: (data: unknown) => void;
}

const SmartScheduler: React.FC<SmartSchedulerProps> = () => (
  <MeetingPlaceholder title="智能排期" />
);

export default SmartScheduler;
