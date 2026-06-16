// @ts-nocheck
import React, { useState } from 'react';
import {
  AlertTriangle,
  Lock,
  Mic,
  MicOff,
  MoreVertical,
  Play,
  Settings,
  Shield,
  Square,
  Unlock,
  UserCheck,
  UserX,
  Users,
  Video,
  VideoOff
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/Dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/DropdownMenu';
import { Switch } from '@/components/ui/Switch';
import { useMeetingStore } from '@/stores/meeting/meetingStore';
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';
import type { Meeting, MeetingParticipant, ParticipantRole } from '@/types/meeting';

interface MeetingControlsProps {
  meeting?: Meeting | null;
  className?: string;
}

interface ConfirmAction {
  title: string;
  message: string;
  action: () => void | Promise<void>;
}

const roleLabels: Record<string, string> = {
  ORGANIZER: '主持人',
  MODERATOR: '协助主持人',
  PRESENTER: '演讲者',
  PARTICIPANT: '参与者',
  OBSERVER: '观察者'
};

const MeetingControls: React.FC<MeetingControlsProps> = ({ meeting, className }) => {
  const { startMeeting, endMeeting, updateMeeting } = useMeetingStore();
  const {
    participants,
    updateParticipant,
    removeParticipant,
    isAudioEnabled,
    isVideoEnabled,
    toggleAudio,
    toggleVideo
  } = useMeetingRoomStore();

  const [isAllMuted, setIsAllMuted] = useState(false);
  const [isLocked, setIsLocked] = useState(Boolean(meeting?.meeting_settings?.require_moderator_approval));
  const [showEmergencyControls, setShowEmergencyControls] = useState(false);
  const [showParticipantManager, setShowParticipantManager] = useState(false);
  const [showMeetingSettings, setShowMeetingSettings] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);

  const currentUserId = 1;
  const safeParticipants = Array.isArray(participants) ? participants : [];
  const currentParticipant = safeParticipants.find((participant) => participant.user_id === currentUserId);
  const isOrganizer = meeting?.organizer_id === currentUserId;
  const isModerator = currentParticipant?.participant_role === 'MODERATOR';
  const canControl = isOrganizer || isModerator;

  const handleStartMeeting = async () => {
    if (meeting?.id) await startMeeting(meeting.id);
  };

  const handleEndMeeting = () => {
    if (!meeting?.id) return;
    setConfirmAction({
      title: '结束会议',
      message: '确定要结束会议吗？会议结束后所有参与者将断开连接。',
      action: async () => endMeeting(meeting.id)
    });
  };

  const handleMuteAll = () => {
    const nextMuted = !isAllMuted;
    setIsAllMuted(nextMuted);
    safeParticipants.forEach((participant) => {
      if (participant.user_id !== currentUserId && participant.participant_role !== 'ORGANIZER') {
        updateParticipant(participant.user_id, { ...participant, is_muted: nextMuted });
      }
    });
  };

  const handleKickParticipant = (participant: MeetingParticipant) => {
    setConfirmAction({
      title: '移除参与者',
      message: `确定要将 ${participant.user?.name || `用户 ${participant.user_id}`} 移出会议吗？`,
      action: () => {
        removeParticipant(participant.user_id);
        updateParticipant(participant.user_id, {
          ...participant,
          attendance_status: 'KICKED_OUT'
        });
      }
    });
  };

  const handleChangeRole = (participant: MeetingParticipant, role: ParticipantRole) => {
    updateParticipant(participant.user_id, { ...participant, participant_role: role });
  };

  const handleToggleLock = () => {
    const nextLocked = !isLocked;
    setIsLocked(nextLocked);
    if (meeting?.id) {
      updateMeeting(meeting.id, {
        meeting_settings: {
          ...meeting.meeting_settings,
          require_moderator_approval: nextLocked
        }
      });
    }
  };

  const handleEmergencyEnd = () => {
    if (!meeting?.id) return;
    setConfirmAction({
      title: '紧急结束会议',
      message: '确定要紧急结束会议吗？这会立即断开所有参与者。',
      action: async () => {
        await endMeeting(meeting.id);
        setShowEmergencyControls(false);
      }
    });
  };

  const handleClearRoom = () => {
    setConfirmAction({
      title: '清空会议室',
      message: '确定要移除所有非主持人参与者吗？',
      action: () => {
        safeParticipants.forEach((participant) => {
          if (participant.participant_role !== 'ORGANIZER' && participant.user_id !== currentUserId) {
            removeParticipant(participant.user_id);
          }
        });
        setShowEmergencyControls(false);
      }
    });
  };

  if (!canControl) {
    return (
      <div className={`flex items-center gap-2 ${className || ''}`}>
        <Badge variant="secondary">参与者</Badge>
        <Button size="sm" variant="outline" onClick={toggleAudio}>
          {isAudioEnabled ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
        </Button>
        <Button size="sm" variant="outline" onClick={toggleVideo}>
          {isVideoEnabled ? <Video className="h-4 w-4" /> : <VideoOff className="h-4 w-4" />}
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className={`flex flex-wrap items-center gap-2 ${className || ''}`}>
        <Badge variant={meeting?.status === 'IN_PROGRESS' ? 'default' : 'secondary'}>
          {meeting?.status === 'IN_PROGRESS'
            ? '进行中'
            : meeting?.status === 'SCHEDULED'
              ? '未开始'
              : meeting?.status === 'COMPLETED'
                ? '已结束'
                : '未知状态'}
        </Badge>

        {meeting?.status === 'SCHEDULED' && (
          <Button size="sm" onClick={handleStartMeeting} className="bg-green-600 text-white hover:bg-green-700">
            <Play className="mr-1 h-4 w-4" />
            开始会议
          </Button>
        )}

        {meeting?.status === 'IN_PROGRESS' && (
          <>
            <Button size="sm" variant="destructive" onClick={handleEndMeeting}>
              <Square className="mr-1 h-4 w-4" />
              结束会议
            </Button>
            <Button size="sm" variant="outline" onClick={handleMuteAll}>
              {isAllMuted ? <Mic className="mr-1 h-4 w-4" /> : <MicOff className="mr-1 h-4 w-4" />}
              {isAllMuted ? '取消全员静音' : '全员静音'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowParticipantManager(true)}>
              <Users className="mr-1 h-4 w-4" />
              参与者
            </Button>
            <Button size="sm" variant="outline" onClick={handleToggleLock}>
              {isLocked ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
            </Button>
          </>
        )}

        <Button size="sm" variant="outline" onClick={() => setShowMeetingSettings(true)}>
          <Settings className="h-4 w-4" />
        </Button>

        <DropdownMenu open={showEmergencyControls} onOpenChange={setShowEmergencyControls}>
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="outline" className="border-red-600 text-red-600 hover:bg-red-50 dark:text-red-400 dark:bg-red-900/20">
              <AlertTriangle className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="text-red-600 dark:text-red-400">紧急控制</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleEmergencyEnd} className="text-red-600 focus:text-red-600 dark:text-red-400">
              <Square className="mr-2 h-4 w-4" />
              紧急结束会议
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleClearRoom} className="text-red-600 focus:text-red-600 dark:text-red-400">
              <UserX className="mr-2 h-4 w-4" />
              清空会议室
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleToggleLock}>
              <Shield className="mr-2 h-4 w-4" />
              {isLocked ? '解锁会议' : '锁定会议'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={showParticipantManager} onOpenChange={setShowParticipantManager}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>参与者管理</DialogTitle>
            <DialogDescription>管理会议参与者角色、权限和会议状态。</DialogDescription>
          </DialogHeader>

          <div className="max-h-96 space-y-2 overflow-y-auto">
            {safeParticipants.map((participant) => (
              <div key={participant.user_id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200">
                    {participant.user?.name?.charAt(0) || 'U'}
                  </div>
                  <div>
                    <div className="font-medium">{participant.user?.name || `用户 ${participant.user_id}`}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{roleLabels[participant.participant_role] || participant.participant_role}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {participant.can_share_screen && <Badge variant="secondary">屏幕</Badge>}
                  {participant.can_use_chat && <Badge variant="secondary">聊天</Badge>}
                  {participant.can_record && <Badge variant="secondary">录制</Badge>}

                  {participant.user_id !== currentUserId && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button size="sm" variant="outline">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleChangeRole(participant, 'MODERATOR')}>
                          <UserCheck className="mr-2 h-4 w-4" />
                          设为协助主持人
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleChangeRole(participant, 'PARTICIPANT')}>
                          <UserCheck className="mr-2 h-4 w-4" />
                          设为参与者
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-red-600 dark:text-red-400" onClick={() => handleKickParticipant(participant)}>
                          <UserX className="mr-2 h-4 w-4" />
                          移出会议
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>
            ))}

            {safeParticipants.length === 0 && (
              <div className="rounded-lg border p-8 text-center text-sm text-gray-500 dark:text-gray-400">暂无参与者</div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowParticipantManager(false)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showMeetingSettings} onOpenChange={setShowMeetingSettings}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>会议设置</DialogTitle>
            <DialogDescription>实时调整会议配置和权限。</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="font-medium">等候室</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">新参与者需要主持人批准</div>
              </div>
              <Switch
                checked={Boolean(meeting?.is_waiting_room_enabled)}
                onCheckedChange={(checked) => meeting?.id && updateMeeting(meeting.id, { is_waiting_room_enabled: checked })}
              />
            </div>

            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="font-medium">会议录制</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">自动录制会议内容</div>
              </div>
              <Switch
                checked={Boolean(meeting?.is_recording_enabled)}
                onCheckedChange={(checked) => meeting?.id && updateMeeting(meeting.id, { is_recording_enabled: checked })}
              />
            </div>

            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="font-medium">会议锁定</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">阻止新的参与者加入</div>
              </div>
              <Switch checked={isLocked} onCheckedChange={handleToggleLock} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMeetingSettings(false)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(confirmAction)} onOpenChange={() => setConfirmAction(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{confirmAction?.title}</DialogTitle>
            <DialogDescription>{confirmAction?.message}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmAction(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                await confirmAction?.action();
                setConfirmAction(null);
              }}
            >
              确认
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MeetingControls;
