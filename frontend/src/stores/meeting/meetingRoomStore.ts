import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { Meeting, MeetingParticipant } from '@/types/meeting'
import { webrtcService } from '@/services/meeting/webrtcService'
import { chatService } from '@/services/meeting/chatService'
import { recordingService } from '@/services/meeting/recordingService'
import { fileService } from '@/services/fileService'
import { meetingService } from '@/services/meeting/meetingService'
import { apiClient, getAuthToken } from '@/services/api/client'

// webrtcService 的事件回调引用：重加入房间时先 off 掉，避免重复监听。
let roomJoinedHandler: ((msg: any) => void) | null = null
let participantJoinedHandler: ((msg: any) => void) | null = null
let participantLeftHandler: ((msg: any) => void) | null = null

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'
export type NetworkQuality = 'excellent' | 'good' | 'poor' | 'disconnected'

export interface MediaDeviceState {
  audioDevices: MediaDeviceInfo[]
  videoDevices: MediaDeviceInfo[]
  selectedAudioDevice?: string
  selectedVideoDevice?: string
  audioLevel: number
  videoResolution?: { width: number; height: number }
}

export interface MeetingRoomConfig {
  enableAudio: boolean
  enableVideo: boolean
  enableScreenShare: boolean
  enableChat: boolean
  enableWhiteboard: boolean
  enableRecording: boolean
  autoJoinAudio: boolean
  autoJoinVideo: boolean
  maxParticipants: number
}

export interface SyncEvent {
  type:
    | 'participant_joined'
    | 'participant_left'
    | 'participant_updated'
    | 'media_state_changed'
    | 'chat_message'
    | 'whiteboard_updated'
    | 'recording_state_changed'
  data: unknown
  userId: number
  timestamp: string
}

export interface ChatMessage {
  id: string
  senderId: number
  senderName: string
  senderAvatar?: string
  content: string
  timestamp: string
  type: 'text' | 'file' | 'system' | 'emoji' | 'mention'
  metadata?: {
    fileId?: string
    fileName?: string
    fileSize?: number
    mentionedUsers?: number[]
    replyTo?: string
    edited?: boolean
    editedAt?: string
  }
  status: 'sending' | 'sent' | 'delivered' | 'failed'
}

export interface SharedFile {
  id: string
  name: string
  size: number
  type: string
  url: string
  thumbnailUrl?: string
  uploadedBy: number
  uploadedByName: string
  uploadedAt: string
  downloadCount: number
  isPublic: boolean
  permissions: {
    canDownload: boolean
    canDelete: boolean
    canShare: boolean
  }
}

interface MeetingRoomState {
  meeting: Meeting | null
  roomId: string | null
  meetingCode: string | null
  sessionId: string | null
  mediaError: string | null
  connectionStatus: ConnectionStatus
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean
  reconnectAttempts: number
  maxReconnectAttempts: number
  lastConnectedAt: string | null
  participants: MeetingParticipant[]
  localParticipant: MeetingParticipant | null
  participantCount: number
  localStream: MediaStream | null
  remoteStreams: Map<number, MediaStream>
  screenShareStream: MediaStream | null
  screenShareUserId: number | null
  screenShareId: string | null
  isAudioEnabled: boolean
  isVideoEnabled: boolean
  isScreenSharing: boolean
  isMuted: boolean
  isVideoOff: boolean
  mediaDevices: MediaDeviceState
  messages: ChatMessage[]
  unreadCount: number
  isTyping: boolean
  typingUsers: number[]
  sharedFiles: SharedFile[]
  uploadingFiles: Map<string, { progress: number; file: File }>
  whiteboardData: any
  whiteboardConnected: boolean
  whiteboardUsers: number[]
  isRecording: boolean
  recordingId: number | null
  recordingStatus: 'idle' | 'starting' | 'recording' | 'pausing' | 'stopping'
  recordingDuration: number
  networkQuality: NetworkQuality
  connectionStats: {
    latency: number
    packetLoss: number
    bandwidth: { upload: number; download: number }
    jitter: number
  }
  config: MeetingRoomConfig
  permissions: {
    canShareScreen: boolean
    canUseChat: boolean
    canUseWhiteboard: boolean
    canRecord: boolean
    canMuteOthers: boolean
    canRemoveParticipants: boolean
    canEndMeeting: boolean
  }
  error: string | null
  warnings: string[]
  persistedState: {
    audioEnabled: boolean
    videoEnabled: boolean
    selectedAudioDevice?: string
    selectedVideoDevice?: string
    chatNotifications: boolean
  }
}

interface MeetingRoomActions {
  initializeRoom: (meeting: Meeting, participant: MeetingParticipant) => Promise<void>
  joinRoom: (meetingId: number) => Promise<void>
  leaveRoom: () => Promise<void>
  startLocalMedia: () => Promise<void>
  loadMessages: () => Promise<void>
  refreshParticipants: () => Promise<void>
  reconnect: () => Promise<void>
  updateConnectionStatus: (status: ConnectionStatus) => void
  addParticipant: (participant: MeetingParticipant) => void
  removeParticipant: (userId: number) => void
  updateParticipant: (userId: number, updates: Partial<MeetingParticipant>) => void
  updateParticipantCount: (count: number) => void
  setLocalStream: (stream: MediaStream | null) => void
  addRemoteStream: (userId: number, stream: MediaStream) => void
  removeRemoteStream: (userId: number) => void
  setScreenShareStream: (stream: MediaStream | null, userId?: number) => void
  updateMediaDevices: (devices: Partial<MediaDeviceState>) => void
  selectAudioDevice: (deviceId: string) => Promise<void>
  selectVideoDevice: (deviceId: string) => Promise<void>
  updateAudioLevel: (level: number) => void
  toggleAudio: () => Promise<void>
  toggleVideo: () => Promise<void>
  muteAudio: () => Promise<void>
  unmuteAudio: () => Promise<void>
  enableVideo: () => Promise<void>
  disableVideo: () => Promise<void>
  startScreenShare: () => Promise<void>
  stopScreenShare: () => void
  sendMessage: (content: string, type?: ChatMessage['type'], metadata?: ChatMessage['metadata']) => Promise<void>
  addMessage: (message: ChatMessage) => void
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void
  deleteMessage: (messageId: string) => void
  markMessagesAsRead: () => void
  setTyping: (isTyping: boolean) => void
  updateTypingUsers: (userIds: number[]) => void
  uploadFile: (file: File, onProgress?: (progress: number) => void) => Promise<SharedFile>
  addSharedFile: (file: SharedFile) => void
  removeSharedFile: (fileId: string) => Promise<void>
  downloadFile: (fileId: string) => Promise<void>
  updateFileUploadProgress: (fileId: string, progress: number) => void
  connectWhiteboard: () => Promise<void>
  disconnectWhiteboard: () => void
  updateWhiteboard: (data: any) => void
  syncWhiteboardEvent: (event: any) => void
  updateWhiteboardUsers: (userIds: number[]) => void
  startRecording: (config?: any) => Promise<void>
  stopRecording: () => Promise<void>
  pauseRecording: () => Promise<void>
  resumeRecording: () => Promise<void>
  updateRecordingStatus: (status: MeetingRoomState['recordingStatus']) => void
  updateRecordingDuration: (duration: number) => void
  updateNetworkQuality: (quality: NetworkQuality) => void
  updateConnectionStats: (stats: Partial<MeetingRoomState['connectionStats']>) => void
  updateConfig: (config: Partial<MeetingRoomConfig>) => void
  updatePermissions: (permissions: Partial<MeetingRoomState['permissions']>) => void
  setError: (error: string | null) => void
  addWarning: (warning: string) => void
  clearError: () => void
  clearWarnings: () => void
  handleSyncEvent: (event: SyncEvent) => void
  broadcastEvent: (event: Omit<SyncEvent, 'timestamp'>) => void
  updatePersistedState: (state: Partial<MeetingRoomState['persistedState']>) => void
  loadPersistedState: () => void
  reset: () => void
  cleanup: () => void
}

export type MeetingRoomStore = MeetingRoomState & MeetingRoomActions

const initialState: MeetingRoomState = {
  meeting: null,
  roomId: null,
  meetingCode: null,
  sessionId: null,
  mediaError: null,
  connectionStatus: 'disconnected',
  isConnected: false,
  isConnecting: false,
  isReconnecting: false,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  lastConnectedAt: null,
  participants: [],
  localParticipant: null,
  participantCount: 0,
  localStream: null,
  remoteStreams: new Map(),
  screenShareStream: null,
  screenShareUserId: null,
  screenShareId: null,
  isAudioEnabled: true,
  isVideoEnabled: true,
  isScreenSharing: false,
  isMuted: false,
  isVideoOff: false,
  mediaDevices: { audioDevices: [], videoDevices: [], audioLevel: 0 },
  messages: [],
  unreadCount: 0,
  isTyping: false,
  typingUsers: [],
  sharedFiles: [],
  uploadingFiles: new Map(),
  whiteboardData: null,
  whiteboardConnected: false,
  whiteboardUsers: [],
  isRecording: false,
  recordingId: null,
  recordingStatus: 'idle',
  recordingDuration: 0,
  networkQuality: 'disconnected',
  connectionStats: { latency: 0, packetLoss: 0, bandwidth: { upload: 0, download: 0 }, jitter: 0 },
  config: {
    enableAudio: true,
    enableVideo: true,
    enableScreenShare: true,
    enableChat: true,
    enableWhiteboard: true,
    enableRecording: true,
    autoJoinAudio: true,
    autoJoinVideo: false,
    maxParticipants: 50,
  },
  permissions: {
    canShareScreen: true,
    canUseChat: true,
    canUseWhiteboard: true,
    canRecord: true,
    canMuteOthers: false,
    canRemoveParticipants: false,
    canEndMeeting: false,
  },
  error: null,
  warnings: [],
  persistedState: {
    audioEnabled: true,
    videoEnabled: true,
    chatNotifications: true,
  },
}

const setConnection = (status: ConnectionStatus) => ({
  connectionStatus: status,
  isConnected: status === 'connected',
  isConnecting: status === 'connecting',
  isReconnecting: status === 'reconnecting',
  lastConnectedAt: status === 'connected' ? new Date().toISOString() : null,
})

export const useMeetingRoomStore = create<MeetingRoomStore>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,
    initializeRoom: async (meeting, participant) => {
      set({
        meeting,
        roomId: `room_${meeting.id}`,
        meetingCode: (meeting as any).meeting_code || null,
        localParticipant: participant,
        participants: [participant],
        participantCount: 1,
        // 注意：这里只完成本地初始化，不代表已连接；连接由 joinRoom 完成。
        ...setConnection('disconnected'),
      })
    },
    joinRoom: async (meetingId) => {
      const state = get()
      const meeting = state.meeting
      if (!meeting || meeting.id !== meetingId) {
        set({ error: '请先初始化会议室（缺少会议信息）' })
        return
      }
      set({ ...setConnection('connecting'), error: null, mediaError: null })
      try {
        const token = getAuthToken()
        if (!token) throw new Error('未登录，无法建立信令连接')
        // 在场登记：只完成 WS 加入（参会人列表靠 participantJoined 更新）。
        // 音视频已改走 Jitsi Meet（2026-11-08 用户决定），这里不再建 PC、不再拉本地流。
        if (roomJoinedHandler) webrtcService.off('roomJoined', roomJoinedHandler)
        if (participantJoinedHandler) webrtcService.off('participantJoined', participantJoinedHandler)
        if (participantLeftHandler) webrtcService.off('participantLeft', participantLeftHandler)
        roomJoinedHandler = async (msg: any) => {
          get().setError(null)
          const sessionId = msg.session_id as string | undefined
          if (sessionId) set({ sessionId })
        }
        participantJoinedHandler = async (msg: any) => {
          const userId = msg.user_id as number
          if (!userId) return
          get().addParticipant({
            user_id: userId,
            meeting_id: meetingId,
            participant_role: 'PARTICIPANT',
          } as MeetingParticipant)
        }
        participantLeftHandler = (msg: any) => {
          const userId = msg.user_id as number
          if (!userId) return
          get().removeParticipant(userId)
        }
        webrtcService.on('roomJoined', roomJoinedHandler)
        webrtcService.on('participantJoined', participantJoinedHandler)
        webrtcService.on('participantLeft', participantLeftHandler)

        await webrtcService.connectSignaling(meetingId, token)
        set({ ...setConnection('connected') })
      } catch (error) {
        set({
          ...setConnection('error'),
          error: error instanceof Error ? error.message : '加入会议室失败',
        })
      }
    },
    startLocalMedia: async () => {
      try {
        const stream = await webrtcService.getLocalStream()
        set({ localStream: stream, mediaError: null })
      } catch {
        set({ mediaError: '无法访问摄像头/麦克风，请检查设备权限' })
      }
    },
    loadMessages: async () => {
      const meetingId = get().meeting?.id
      if (!meetingId) return
      try {
        const body: any = await chatService.getChatHistory(meetingId, { pageSize: 50 })
        const list = body?.messages ?? []
        set({
          messages: list.map((m: any) => ({
            id: String(m.id),
            senderId: m.sender_id,
            senderName: m.sender_name ?? `用户 ${m.sender_id}`,
            content: m.content,
            timestamp: m.sent_at ?? m.created_at,
            type: 'text' as const,
            status: 'sent' as const,
          })),
          unreadCount: 0,
        })
      } catch (error) {
        console.warn('加载聊天记录失败:', error)
      }
    },
    refreshParticipants: async () => {
      const meetingId = get().meeting?.id
      if (!meetingId) return
      try {
        const list = await meetingService.getParticipants(meetingId)
        set({ participants: list, participantCount: list.length })
      } catch (error) {
        console.warn('刷新参会人失败:', error)
      }
    },
    leaveRoom: async () => {
      if (roomJoinedHandler) webrtcService.off('roomJoined', roomJoinedHandler)
      if (participantJoinedHandler) webrtcService.off('participantJoined', participantJoinedHandler)
      if (participantLeftHandler) webrtcService.off('participantLeft', participantLeftHandler)
      roomJoinedHandler = participantJoinedHandler = participantLeftHandler = null
      webrtcService.cleanup()
      get().cleanup()
    },
    reconnect: async () => set({ reconnectAttempts: get().reconnectAttempts + 1, ...setConnection('connected') }),
    updateConnectionStatus: (status) => set(setConnection(status)),
    addParticipant: (participant) => set((state) => {
      const participants = [...state.participants.filter((item) => item.user_id !== participant.user_id), participant]
      return { participants, participantCount: participants.length }
    }),
    removeParticipant: (userId) => set((state) => {
      const participants = state.participants.filter((participant) => participant.user_id !== userId)
      return { participants, participantCount: participants.length }
    }),
    updateParticipant: (userId, updates) => set((state) => ({
      participants: state.participants.map((participant) =>
        participant.user_id === userId ? { ...participant, ...updates } : participant,
      ),
      localParticipant: state.localParticipant?.user_id === userId
        ? { ...state.localParticipant, ...updates }
        : state.localParticipant,
    })),
    updateParticipantCount: (participantCount) => set({ participantCount }),
    setLocalStream: (localStream) => set({ localStream }),
    addRemoteStream: (userId, stream) => set((state) => {
      const remoteStreams = new Map(state.remoteStreams)
      remoteStreams.set(userId, stream)
      return { remoteStreams }
    }),
    removeRemoteStream: (userId) => set((state) => {
      const remoteStreams = new Map(state.remoteStreams)
      remoteStreams.delete(userId)
      return { remoteStreams }
    }),
    setScreenShareStream: (screenShareStream, userId) => set({
      screenShareStream,
      screenShareUserId: screenShareStream ? userId || null : null,
      isScreenSharing: Boolean(screenShareStream),
    }),
    updateMediaDevices: (devices) => set((state) => ({ mediaDevices: { ...state.mediaDevices, ...devices } })),
    selectAudioDevice: async (selectedAudioDevice) => {
      try {
        await webrtcService.switchMediaDevice(selectedAudioDevice, 'audio')
      } catch (e) {
        console.warn('切换音频设备失败:', e)
      }
      set((state) => ({ mediaDevices: { ...state.mediaDevices, selectedAudioDevice } }))
    },
    selectVideoDevice: async (selectedVideoDevice) => {
      try {
        await webrtcService.switchMediaDevice(selectedVideoDevice, 'video')
      } catch (e) {
        console.warn('切换视频设备失败:', e)
      }
      set((state) => ({ mediaDevices: { ...state.mediaDevices, selectedVideoDevice } }))
    },
    updateAudioLevel: (audioLevel) => set((state) => ({ mediaDevices: { ...state.mediaDevices, audioLevel } })),
    toggleAudio: async () => {
      // 真实开关：改本地音频轨道的 enabled；无本地流时只改状态。
      const enabled = webrtcService.toggleAudio()
      const hasStream = Boolean(get().localStream)
      set((state) => ({
        isAudioEnabled: hasStream ? enabled : !state.isAudioEnabled,
        isMuted: hasStream ? !enabled : state.isAudioEnabled,
      }))
    },
    toggleVideo: async () => {
      const enabled = webrtcService.toggleVideo()
      const hasStream = Boolean(get().localStream)
      set((state) => ({
        isVideoEnabled: hasStream ? enabled : !state.isVideoEnabled,
        isVideoOff: hasStream ? !enabled : state.isVideoEnabled,
      }))
    },
    muteAudio: async () => {
      webrtcService.toggleAudio(false)
      set({ isAudioEnabled: false, isMuted: true })
    },
    unmuteAudio: async () => {
      webrtcService.toggleAudio(true)
      set({ isAudioEnabled: true, isMuted: false })
    },
    enableVideo: async () => {
      webrtcService.toggleVideo(true)
      set({ isVideoEnabled: true, isVideoOff: false })
    },
    disableVideo: async () => {
      webrtcService.toggleVideo(false)
      set({ isVideoEnabled: false, isVideoOff: true })
    },
    startScreenShare: async () => {
      const meetingId = get().meeting?.id
      if (!meetingId) return
      try {
        const stream = await webrtcService.startScreenShare()
        set({ screenShareStream: stream, screenShareUserId: get().localParticipant?.user_id ?? null, isScreenSharing: true })
        // 通知后端（需要 WS 会话 ID；拿不到时只做本地共享，不报错）。
        const sessionId = webrtcService.getSessionId()
        if (sessionId) {
          const resp: any = await apiClient.post(`/api/v1/meetings/${meetingId}/screen-share/start`, {
            session_id: sessionId,
            share_type: 'screen',
          })
          const shareId = resp?.data?.share_id ?? resp?.data?.data?.share_id
          if (shareId) set({ screenShareId: shareId })
        }
      } catch (error) {
        set({ error: error instanceof Error ? error.message : '开始屏幕共享失败' })
      }
    },
    stopScreenShare: () => {
      const meetingId = get().meeting?.id
      const sessionId = webrtcService.getSessionId()
      const shareId = get().screenShareId
      void webrtcService.stopScreenShare()
      if (meetingId && sessionId && shareId) {
        apiClient.post(`/api/v1/meetings/${meetingId}/screen-share/stop`, {
          session_id: sessionId,
          share_id: shareId,
        }).catch((e) => console.warn('通知后端停止屏幕共享失败:', e))
      }
      set({ isScreenSharing: false, screenShareStream: null, screenShareUserId: null, screenShareId: null })
    },
    sendMessage: async (content, type = 'text', metadata) => {
      const meetingId = get().meeting?.id
      const message: ChatMessage = {
        id: `msg-${Date.now()}`,
        senderId: get().localParticipant?.user_id || 0,
        senderName: (get().localParticipant as any)?.user?.name || '我',
        content,
        timestamp: new Date().toISOString(),
        type,
        metadata,
        status: 'sending',
      }
      get().addMessage(message)
      if (!meetingId) {
        get().updateMessage(message.id, { status: 'failed' })
        return
      }
      try {
        // chatService 返回的是后端 SendChatMessageResponse 信封，data 才是消息。
        const body: any = await chatService.sendMessage(meetingId, {
          content,
          messageType: 'TEXT',
        })
        const data = body?.data ?? body
        get().updateMessage(message.id, {
          id: String(data?.id ?? message.id),
          senderId: data?.sender_id ?? message.senderId,
          senderName: data?.sender_name ?? message.senderName,
          timestamp: data?.sent_at ?? message.timestamp,
          status: 'sent',
        })
      } catch (error) {
        get().updateMessage(message.id, { status: 'failed' })
        set({ error: error instanceof Error ? error.message : '发送消息失败' })
      }
    },
    addMessage: (message) => set((state) => ({ messages: [...state.messages, message], unreadCount: state.unreadCount + 1 })),
    updateMessage: (messageId, updates) => set((state) => ({
      messages: state.messages.map((message) => (message.id === messageId ? { ...message, ...updates } : message)),
    })),
    deleteMessage: (messageId) => set((state) => ({ messages: state.messages.filter((message) => message.id !== messageId) })),
    markMessagesAsRead: () => set({ unreadCount: 0 }),
    setTyping: (isTyping) => set({ isTyping }),
    updateTypingUsers: (typingUsers) => set({ typingUsers }),
    uploadFile: async (file, onProgress) => {
      const meetingId = get().meeting?.id
      if (!meetingId) throw new Error('缺少会议信息，无法上传')
      const uploaded = await fileService.uploadFile(file, { meetingId, isPublic: false }, (p) => onProgress?.(p))
      const sharedFile: SharedFile = {
        id: uploaded.id,
        name: uploaded.name,
        size: uploaded.size,
        type: uploaded.type,
        url: uploaded.url,
        uploadedBy: get().localParticipant?.user_id || 0,
        uploadedByName: uploaded.uploadedBy?.name || (get().localParticipant as any)?.user?.name || '我',
        uploadedAt: uploaded.uploadedAt || new Date().toISOString(),
        downloadCount: uploaded.downloadCount ?? 0,
        isPublic: uploaded.isPublic ?? false,
        permissions: { canDownload: true, canDelete: true, canShare: true },
      }
      get().addSharedFile(sharedFile)
      return sharedFile
    },
    addSharedFile: (file) => set((state) => ({ sharedFiles: [...state.sharedFiles, file] })),
    removeSharedFile: async (fileId) => {
      // 后端没有文件删除接口：只从本地列表移除，并告警说明。
      get().addWarning('后端暂无文件删除接口，已仅从本地列表移除')
      set((state) => ({ sharedFiles: state.sharedFiles.filter((file) => file.id !== fileId) }))
    },
    downloadFile: async (fileId) => {
      // 后端没有文件下载接口：只本地记一次下载数，并告警说明。
      get().addWarning('后端暂无文件下载接口，无法下载')
      set((state) => ({
        sharedFiles: state.sharedFiles.map((file) =>
          file.id === fileId ? { ...file, downloadCount: file.downloadCount + 1 } : file,
        ),
      }))
    },
    updateFileUploadProgress: (fileId, progress) => set((state) => {
      const uploadingFiles = new Map(state.uploadingFiles)
      const item = uploadingFiles.get(fileId)
      if (item) uploadingFiles.set(fileId, { ...item, progress })
      return { uploadingFiles }
    }),
    connectWhiteboard: async () => {
      const meetingId = get().meeting?.id
      if (!meetingId) return
      try {
        const resp: any = await apiClient.get(`/api/v1/meetings/${meetingId}/whiteboard/state`)
        const state = resp?.data ?? resp
        set({ whiteboardData: state?.content ?? state, whiteboardConnected: true })
      } catch (error) {
        console.warn('加载白板状态失败:', error)
        set({ whiteboardConnected: false })
      }
    },
    disconnectWhiteboard: () => set({ whiteboardConnected: false, whiteboardUsers: [] }),
    updateWhiteboard: (whiteboardData) => set({ whiteboardData }),
    syncWhiteboardEvent: (event) => {
      // 白板操作要落到后端：调 POST /whiteboard/action；失败只告警。
      const meetingId = get().meeting?.id
      const userId = get().localParticipant?.user_id
      if (meetingId && userId && event?.action_type) {
        apiClient.post(`/api/v1/meetings/${meetingId}/whiteboard/action`, {
          action_type: event.action_type,
          user_id: userId,
          data: event.data ?? {},
        }).then((resp: any) => {
          const state = resp?.data?.data ?? resp?.data
          if (state?.content) set({ whiteboardData: state.content })
        }).catch((e) => console.warn('同步白板操作失败:', e))
      }
      set({ whiteboardData: event?.data ?? event })
    },
    updateWhiteboardUsers: (whiteboardUsers) => set({ whiteboardUsers }),
    startRecording: async () => {
      const meetingId = get().meeting?.id
      if (!meetingId) return
      set({ recordingStatus: 'starting' })
      try {
        const recording = await recordingService.startRecording(meetingId, {
          name: `Meeting_${meetingId}_${new Date().toISOString().slice(0, 10)}`,
          type: 'FULL_MEETING',
          format: 'MP4',
          quality: 'MEDIUM',
        } as any)
        set({ isRecording: true, recordingStatus: 'recording', recordingId: recording?.id ?? null, recordingDuration: 0 })
      } catch (error) {
        set({ recordingStatus: 'idle', error: error instanceof Error ? error.message : '开始录制失败' })
      }
    },
    stopRecording: async () => {
      const recordingId = get().recordingId
      if (!recordingId) {
        set({ isRecording: false, recordingStatus: 'idle' })
        return
      }
      set({ recordingStatus: 'stopping' })
      try {
        await recordingService.stopRecording(recordingId)
        set({ isRecording: false, recordingStatus: 'idle', recordingId: null })
      } catch (error) {
        set({ recordingStatus: 'recording', error: error instanceof Error ? error.message : '停止录制失败' })
      }
    },
    pauseRecording: async () => {
      const recordingId = get().recordingId
      if (!recordingId) return
      try {
        await recordingService.pauseRecording(recordingId)
        set({ recordingStatus: 'pausing' })
      } catch (error) {
        set({ error: error instanceof Error ? error.message : '暂停录制失败' })
      }
    },
    resumeRecording: async () => {
      const recordingId = get().recordingId
      if (!recordingId) return
      try {
        await recordingService.resumeRecording(recordingId)
        set({ recordingStatus: 'recording' })
      } catch (error) {
        set({ error: error instanceof Error ? error.message : '恢复录制失败' })
      }
    },
    updateRecordingStatus: (recordingStatus) => set({ recordingStatus, isRecording: recordingStatus === 'recording' }),
    updateRecordingDuration: (recordingDuration) => set({ recordingDuration }),
    updateNetworkQuality: (networkQuality) => set({ networkQuality }),
    updateConnectionStats: (stats) => set((state) => ({ connectionStats: { ...state.connectionStats, ...stats } })),
    updateConfig: (config) => set((state) => ({ config: { ...state.config, ...config } })),
    updatePermissions: (permissions) => set((state) => ({ permissions: { ...state.permissions, ...permissions } })),
    setError: (error) => set({ error }),
    addWarning: (warning) => set((state) => ({ warnings: [...state.warnings, warning] })),
    clearError: () => set({ error: null }),
    clearWarnings: () => set({ warnings: [] }),
    handleSyncEvent: (event) => {
      if (event.type === 'chat_message') get().addMessage(event.data as ChatMessage)
      if (event.type === 'whiteboard_updated') get().updateWhiteboard(event.data)
    },
    broadcastEvent: (event) => get().handleSyncEvent({ ...event, timestamp: new Date().toISOString() }),
    updatePersistedState: (persistedState) => set((state) => ({ persistedState: { ...state.persistedState, ...persistedState } })),
    loadPersistedState: () => undefined,
    reset: () => set({ ...initialState, remoteStreams: new Map(), uploadingFiles: new Map() }),
    cleanup: () => {
      get().localStream?.getTracks().forEach((track) => track.stop())
      get().screenShareStream?.getTracks().forEach((track) => track.stop())
      get().remoteStreams.forEach((stream) => stream.getTracks().forEach((track) => track.stop()))
      get().reset()
    },
  })),
)

export const selectConnectionStatus = (state: MeetingRoomStore) => state.connectionStatus
export const selectIsConnected = (state: MeetingRoomStore) => state.isConnected
export const selectParticipants = (state: MeetingRoomStore) => state.participants
export const selectLocalParticipant = (state: MeetingRoomStore) => state.localParticipant
export const selectMessages = (state: MeetingRoomStore) => state.messages
export const selectUnreadCount = (state: MeetingRoomStore) => state.unreadCount
export const selectSharedFiles = (state: MeetingRoomStore) => state.sharedFiles
export const selectIsRecording = (state: MeetingRoomStore) => state.isRecording
export const selectNetworkQuality = (state: MeetingRoomStore) => state.networkQuality
export const selectMediaDevices = (state: MeetingRoomStore) => state.mediaDevices
export const selectPermissions = (state: MeetingRoomStore) => state.permissions
export const selectConfig = (state: MeetingRoomStore) => state.config

export const subscribeToConnectionStatus = (callback: (status: ConnectionStatus) => void) =>
  useMeetingRoomStore.subscribe(selectConnectionStatus, callback)
export const subscribeToParticipants = (callback: (participants: MeetingParticipant[]) => void) =>
  useMeetingRoomStore.subscribe(selectParticipants, callback)
export const subscribeToMessages = (callback: (messages: ChatMessage[]) => void) =>
  useMeetingRoomStore.subscribe(selectMessages, callback)
export const subscribeToRecordingState = (callback: (isRecording: boolean) => void) =>
  useMeetingRoomStore.subscribe(selectIsRecording, callback)

export const meetingRoomUtils = {
  canSendMessage: () => {
    const { isConnected, permissions } = useMeetingRoomStore.getState()
    return isConnected && permissions.canUseChat
  },
  canShareScreen: () => {
    const { isConnected, permissions, isScreenSharing } = useMeetingRoomStore.getState()
    return isConnected && permissions.canShareScreen && !isScreenSharing
  },
  canRecord: () => {
    const { isConnected, permissions, isRecording } = useMeetingRoomStore.getState()
    return isConnected && permissions.canRecord && !isRecording
  },
  getConnectionStatusText: (status: ConnectionStatus) => ({
    connecting: '连接中',
    connected: '已连接',
    disconnected: '已断开',
    reconnecting: '重连中',
    error: '连接错误',
  }[status] || '未知状态'),
  getNetworkQualityText: (quality: NetworkQuality) => ({
    excellent: '优秀',
    good: '良好',
    poor: '较差',
    disconnected: '已断开',
  }[quality] || '未知'),
  formatRecordingDuration: (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return hours > 0
      ? `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
      : `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  },
  formatFileSize: (bytes: number) => {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    return `${(bytes / 1024 ** index).toFixed(2)} ${units[index]}`
  },
  isPreviewableFile: (type: string) =>
    ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf', 'text/plain', 'application/json'].includes(type),
}

export type {
  ConnectionStatus as MeetingConnectionStatus,
  NetworkQuality as MeetingNetworkQuality,
  MediaDeviceState as MeetingMediaDeviceState,
  MeetingRoomConfig as MeetingRoomConfiguration,
  SyncEvent as MeetingRoomSyncEvent,
}
