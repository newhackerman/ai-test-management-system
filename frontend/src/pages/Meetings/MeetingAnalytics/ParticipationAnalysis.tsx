import React from 'react';
import { MeetingPlaceholder } from '../MeetingPlaceholder';

interface ParticipationAnalysisProps {
  meetingId?: number;
}

export const ParticipationAnalysis: React.FC<ParticipationAnalysisProps> = () => (
  <MeetingPlaceholder title="参与度分析" />
);

export default ParticipationAnalysis;
