import React from 'react';
import { MeetingPlaceholder } from './MeetingPlaceholder';

interface SmartSchedulerProps {
  projectId?: number;
  onScheduleGenerated?: (data: unknown) => void;
}

const SmartScheduler: React.FC<SmartSchedulerProps> = () => (
  <MeetingPlaceholder title="智能排期" description="智能排期入口已恢复，后续可继续接入排期推荐算法。" />
);

export default SmartScheduler;
