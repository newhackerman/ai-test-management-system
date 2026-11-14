import React from 'react';
import { RefreshCw, Users } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';

const ParticipantList: React.FC = () => {
  const participants = useMeetingRoomStore((s) => s.participants);
  const refreshParticipants = useMeetingRoomStore((s) => s.refreshParticipants);
  const localParticipant = useMeetingRoomStore((s) => s.localParticipant);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2"><Users className="h-4 w-4" />参会人（{participants.length}）</span>
          <Button type="button" size="sm" variant="ghost" onClick={() => void refreshParticipants()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {participants.map((participant) => (
          <div key={participant.user_id} className="rounded-md border p-2 text-sm">
            <div className="flex items-center justify-between">
              <span>
                {participant.user?.name ?? (participant as any).user_name ?? `用户 ${participant.user_id}`}
                {localParticipant?.user_id === participant.user_id && '（我）'}
              </span>
              <span className="text-xs text-muted-foreground">{participant.participant_role}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {participant.attendance_status ?? ''}
            </div>
          </div>
        ))}
        {participants.length === 0 && <div className="text-sm text-muted-foreground">暂无参会人</div>}
      </CardContent>
    </Card>
  );
};

export default ParticipantList;
