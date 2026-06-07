import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface ParticipationAnalysisProps {
  meetingId?: number;
}

export const ParticipationAnalysis: React.FC<ParticipationAnalysisProps> = () => (
  <MeetingPlaceholder title="参与度分析" description="参与度分析入口已恢复。" />
);

export default ParticipationAnalysis;
