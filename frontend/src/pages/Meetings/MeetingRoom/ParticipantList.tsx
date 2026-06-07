import React from 'react';
import { Users } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

interface ParticipantListProps {
  participants?: any[];
}

const ParticipantList: React.FC<ParticipantListProps> = ({ participants = [] }) => (
  <Card>
    <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Users className="h-4 w-4" />参会人</CardTitle></CardHeader>
    <CardContent className="space-y-2">
      {participants.map((participant, index) => (
        <div key={participant.id ?? index} className="rounded-md border p-2 text-sm">
          {participant.user?.name ?? participant.name ?? participant.username ?? `参会人 ${index + 1}`}
        </div>
      ))}
      {participants.length === 0 && <div className="text-sm text-muted-foreground">暂无参会人</div>}
    </CardContent>
  </Card>
);

export default ParticipantList;
