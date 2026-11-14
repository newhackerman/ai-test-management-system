import React, { useEffect, useRef, useState } from 'react';

import { Card, CardContent } from '@/components/ui/Card';

// 音视频层：Jitsi Meet（公开 meet.jit.si）iframe API 嵌入。
// 用户决定（2026-11-08）：“参加会议”与“开启会议”先用互联网通用会议室跑通，
// 自研 WebRTC mesh 暂缓。房间名 meeting_{会议 code}，同一会议进同一房间。
// 本组件只负责音视频；会议记录/参会人/聊天/白板/文件/录制仍由本系统外壳提供。
// window.__jitsiApi / window.__jitsiJoined 是 E2E 探针钩子（见 e2e/test_e2e_jitsi_room.py）。

declare global {
  interface Window {
    JitsiMeetExternalAPI?: any;
    __jitsiApi?: any;
    __jitsiJoined?: boolean;
  }
}

const JITSI_DOMAIN = 'meet.jit.si';
const JITSI_SCRIPT = `https://${JITSI_DOMAIN}/external_api.js`;

function loadJitsiScript(): Promise<void> {
  if (window.JitsiMeetExternalAPI) return Promise.resolve();
  const existing = document.querySelector(`script[src="${JITSI_SCRIPT}"]`);
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('加载 Jitsi 脚本失败')));
    });
  }
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = JITSI_SCRIPT;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('加载 Jitsi 脚本失败（meet.jit.si 不可达？）'));
    document.head.appendChild(s);
  });
}

interface JitsiMeetProps {
  roomName: string;
  displayName: string;
}

const JitsiMeet: React.FC<JitsiMeetProps> = ({ roomName, displayName }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<'loading' | 'joined' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [participantCount, setParticipantCount] = useState(0);

  useEffect(() => {
    let disposed = false;
    let api: any = null;
    setStatus('loading');
    setError(null);
    window.__jitsiJoined = false;
    loadJitsiScript()
      .then(() => {
        if (disposed || !containerRef.current) return;
        api = new window.JitsiMeetExternalAPI(JITSI_DOMAIN, {
          roomName,
          parentNode: containerRef.current,
          configOverwrite: {
            prejoinPageEnabled: false,
            disableDeepLinking: true,
            startWithAudioMuted: false,
            startWithVideoMuted: false,
          },
          interfaceConfigOverwrite: {
            SHOW_JITSI_WATERMARK: false,
          },
          userInfo: { displayName },
        });
        window.__jitsiApi = api;
        const refreshCount = () => {
          try {
            const list = api.getParticipantsInfo?.() ?? [];
            setParticipantCount(Array.isArray(list) ? list.length : 0);
          } catch {
            // getParticipantsInfo 在加入完成前可能抛错，忽略即可。
          }
        };
        api.addEventListener('videoConferenceJoined', () => {
          setStatus('joined');
          window.__jitsiJoined = true;
          refreshCount();
        });
        api.addEventListener('participantJoined', refreshCount);
        api.addEventListener('participantLeft', refreshCount);
        api.addEventListener('videoConferenceLeft', () => {
          setStatus('loading');
          window.__jitsiJoined = false;
        });
      })
      .catch((e) => {
        if (!disposed) {
          setError(e instanceof Error ? e.message : '加载 Jitsi 失败');
          setStatus('error');
        }
      });
    return () => {
      disposed = true;
      try {
        api?.dispose();
      } catch {
        // dispose 失败不影响页面卸载。
      }
      if (window.__jitsiApi === api) window.__jitsiApi = undefined;
      window.__jitsiJoined = false;
    };
  }, [roomName, displayName]);

  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div
          ref={containerRef}
          data-testid="jitsi-container"
          data-jitsi-joined={status === 'joined' ? 'true' : 'false'}
          className="h-[480px] w-full overflow-hidden rounded-md border bg-black"
        />
        {status === 'loading' && (
          <div className="text-sm text-muted-foreground">正在连接 Jitsi 会议室 {roomName}…</div>
        )}
        {status === 'joined' && (
          <div className="text-xs text-muted-foreground">
            已加入 Jitsi 房间 {roomName} · 房内 {participantCount} 人（音视频由 meet.jit.si 提供）
          </div>
        )}
        {status === 'error' && <div className="text-sm text-red-600">Jitsi 加载失败：{error}</div>}
      </CardContent>
    </Card>
  );
};

export default JitsiMeet;
