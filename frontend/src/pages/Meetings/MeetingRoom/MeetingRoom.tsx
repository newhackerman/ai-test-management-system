import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertTriangle, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { useAuthStore } from '@/stores/auth';
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore';
import { meetingService } from '@/services/meeting/meetingService';
import type { Meeting, MeetingParticipant } from '@/types/meeting';
import Chat from './Chat';
import FileShare from './FileShare';
import JitsiMeet from './JitsiMeet';
import MeetingControls from './MeetingControls';
import ParticipantList from './ParticipantList';
import RecordingControls from './RecordingControls';
import Whiteboard from './Whiteboard';

// 实时会议室：音视频走 Jitsi Meet（meet.jit.si，房间 meeting_{code}）+ 本系统外壳
// （参会人/聊天/文件/白板/录制/会议控制）。自研 WebRTC mesh 暂缓（2026-11-08 用户决定）。
// 信令 WS 只保留“在场”登记（参会人列表），不再建 PC、不再拉本地流。
const MeetingRoom: React.FC = () => {
  const { meetingId: meetingIdParam, meetingCode } = useParams<{ meetingId?: string; meetingCode?: string }>();
  const currentUser = useAuthStore((s) => s.user);
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const connectionStatus = useMeetingRoomStore((s) => s.connectionStatus);
  const error = useMeetingRoomStore((s) => s.error);
  const warnings = useMeetingRoomStore((s) => s.warnings);
  const initializeRoom = useMeetingRoomStore((s) => s.initializeRoom);
  const joinRoom = useMeetingRoomStore((s) => s.joinRoom);
  const leaveRoom = useMeetingRoomStore((s) => s.leaveRoom);
  const loadMessages = useMeetingRoomStore((s) => s.loadMessages);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      let resolved: Meeting;
      if (meetingCode) {
        resolved = await meetingService.getMeetingByCode(meetingCode);
      } else if (meetingIdParam) {
        resolved = await meetingService.getMeeting(Number(meetingIdParam));
      } else {
        throw new Error('缺少会议 ID 或会议编码');
      }
      setMeeting(resolved);

      const participants = await meetingService.getParticipants(resolved.id);
      const me = participants.find((p) => p.user_id === currentUser?.id)
        ?? participants.find((p) => p.user_id === resolved.organizer_id)
        ?? participants[0];
      // 非参会者：先走 REST 加入（会写入参会人表），否则 WS 加入会被拒。
      if (currentUser?.id && !participants.some((p) => p.user_id === currentUser.id) && resolved.meeting_code) {
        try {
          await meetingService.joinMeeting(resolved.meeting_code);
        } catch (e) {
          console.warn('REST 加入会议失败，仍尝试直接进房:', e);
        }
      }
      const localParticipant: MeetingParticipant = me ?? ({
        user_id: currentUser?.id ?? 0,
        meeting_id: resolved.id,
        participant_role: 'PARTICIPANT',
      } as MeetingParticipant);
      await initializeRoom(resolved, localParticipant);
      await joinRoom(resolved.id);
      await loadMessages();
    } catch (e) {
      // 用 warn 而不是 error：加载失败是页面状态，不是代码异常；
      // 巡游把 console.error 计为页面错误。
      console.warn('加载会议室失败:', e);
      setLoadError(e instanceof Error ? e.message : '加载会议室失败');
    } finally {
      setLoading(false);
    }
  }, [meetingCode, meetingIdParam, currentUser?.id, initializeRoom, joinRoom, loadMessages]);

  useEffect(() => {
    void load();
    return () => {
      void leaveRoom();
    };
    // 只在进入页面时加载一次；leaveRoom 在卸载时执行。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-6 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />正在加入会议室…
      </div>
    );
  }

  if (loadError || !meeting) {
    return (
      <Card className="m-6">
        <CardContent className="space-y-3 pt-6">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />{loadError ?? '会议不存在'}
          </div>
          <Button type="button" variant="outline" onClick={() => void load()}>重新加载</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{meeting.title} · 会议室</h1>
          <div className="text-sm text-muted-foreground">
            会议编码 {meeting.meeting_code} · Jitsi 房间 meeting_{meeting.meeting_code} · 连接状态 {connectionStatus}
          </div>
        </div>
        <MeetingControls meeting={meeting} />
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />{error}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
          {warnings.map((w, i) => <div key={i}>{w}</div>)}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <JitsiMeet
            roomName={`meeting_${meeting.meeting_code}`}
            displayName={currentUser?.real_name || currentUser?.username || '参会者'}
          />
          <div className="flex flex-wrap items-center gap-2">
            <RecordingControls />
          </div>
          <Whiteboard />
          <FileShare meetingId={meeting.id} currentUserId={currentUser?.id ?? 0} />
        </div>
        <div className="space-y-4">
          <ParticipantList />
          <Chat />
        </div>
      </div>

      <div className="text-xs text-muted-foreground">
        提示：音视频由 Jitsi Meet（meet.jit.si）提供，房间名取自会议编码，同一会议进同一房间；
        参会人/聊天/文件/白板/录制是本系统外壳。房间与白板状态只存后端进程内存，重启即丢。
      </div>
    </div>
  );
};

export default MeetingRoom;
