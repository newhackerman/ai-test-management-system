import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { Meeting, MeetingParticipant } from '@/types/meeting'

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
  joinRoom: (roomId: string, meetingCode?: string) => Promise<void>
  leaveRoom: () => Promise<void>
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
        roomId: String(meeting.id),
        meetingCode: (meeting as any).meeting_code || null,
        localParticipant: participant,
        participants: [participant],
        participantCount: 1,
        ...setConnection('connected'),
      })
    },
    joinRoom: async (roomId, meetingCode) => set({ roomId, meetingCode: meetingCode || null, ...setConnection('connected') }),
    leaveRoom: async () => get().cleanup(),
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
    selectAudioDevice: async (selectedAudioDevice) => set((state) => ({ mediaDevices: { ...state.mediaDevices, selectedAudioDevice } })),
    selectVideoDevice: async (selectedVideoDevice) => set((state) => ({ mediaDevices: { ...state.mediaDevices, selectedVideoDevice } })),
    updateAudioLevel: (audioLevel) => set((state) => ({ mediaDevices: { ...state.mediaDevices, audioLevel } })),
    toggleAudio: async () => set((state) => ({ isAudioEnabled: !state.isAudioEnabled, isMuted: state.isAudioEnabled })),
    toggleVideo: async () => set((state) => ({ isVideoEnabled: !state.isVideoEnabled, isVideoOff: state.isVideoEnabled })),
    muteAudio: async () => set({ isAudioEnabled: false, isMuted: true }),
    unmuteAudio: async () => set({ isAudioEnabled: true, isMuted: false }),
    enableVideo: async () => set({ isVideoEnabled: true, isVideoOff: false }),
    disableVideo: async () => set({ isVideoEnabled: false, isVideoOff: true }),
    startScreenShare: async () => set({ isScreenSharing: true }),
    stopScreenShare: () => set({ isScreenSharing: false, screenShareStream: null, screenShareUserId: null }),
    sendMessage: async (content, type = 'text', metadata) => {
      const message: ChatMessage = {
        id: `msg-${Date.now()}`,
        senderId: get().localParticipant?.user_id || 0,
        senderName: (get().localParticipant as any)?.user?.name || '我',
        content,
        timestamp: new Date().toISOString(),
        type,
        metadata,
        status: 'sent',
      }
      get().addMessage(message)
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
      onProgress?.(100)
      const sharedFile: SharedFile = {
        id: `file-${Date.now()}`,
        name: file.name,
        size: file.size,
        type: file.type,
        url: URL.createObjectURL(file),
        uploadedBy: get().localParticipant?.user_id || 0,
        uploadedByName: (get().localParticipant as any)?.user?.name || '我',
        uploadedAt: new Date().toISOString(),
        downloadCount: 0,
        isPublic: true,
        permissions: { canDownload: true, canDelete: true, canShare: true },
      }
      get().addSharedFile(sharedFile)
      return sharedFile
    },
    addSharedFile: (file) => set((state) => ({ sharedFiles: [...state.sharedFiles, file] })),
    removeSharedFile: async (fileId) => set((state) => ({ sharedFiles: state.sharedFiles.filter((file) => file.id !== fileId) })),
    downloadFile: async (fileId) => set((state) => ({
      sharedFiles: state.sharedFiles.map((file) =>
        file.id === fileId ? { ...file, downloadCount: file.downloadCount + 1 } : file,
      ),
    })),
    updateFileUploadProgress: (fileId, progress) => set((state) => {
      const uploadingFiles = new Map(state.uploadingFiles)
      const item = uploadingFiles.get(fileId)
      if (item) uploadingFiles.set(fileId, { ...item, progress })
      return { uploadingFiles }
    }),
    connectWhiteboard: async () => set({ whiteboardConnected: true }),
    disconnectWhiteboard: () => set({ whiteboardConnected: false, whiteboardUsers: [] }),
    updateWhiteboard: (whiteboardData) => set({ whiteboardData }),
    syncWhiteboardEvent: (event) => set({ whiteboardData: event }),
    updateWhiteboardUsers: (whiteboardUsers) => set({ whiteboardUsers }),
    startRecording: async () => set({ isRecording: true, recordingStatus: 'recording', recordingId: Date.now(), recordingDuration: 0 }),
    stopRecording: async () => set({ isRecording: false, recordingStatus: 'idle' }),
    pauseRecording: async () => set({ recordingStatus: 'pausing' }),
    resumeRecording: async () => set({ recordingStatus: 'recording' }),
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
