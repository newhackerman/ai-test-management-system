import { api } from './api'

export interface RecordingConfig {
  quality: 'low' | 'medium' | 'high'
  format: 'mp4' | 'webm'
  includeAudio: boolean
  includeVideo: boolean
  includeScreenShare: boolean
  includeChat: boolean
}

export interface RecordingStatus {
  id: number
  meetingId: number
  recordingName: string
  recordingType: 'FULL_MEETING' | 'SCREEN_SHARE' | 'AUDIO_ONLY' | 'HIGHLIGHTS'
  fileFormat: 'MP4' | 'WEBM' | 'MP3' | 'M4A'
  filePath?: string
  fileSize: number
  durationSeconds: number
  resolution?: string
  recordingStatus: 'RECORDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'DELETED'
  processingProgress: number
  startTime: string
  endTime?: string
  isPublic: boolean
  accessPassword?: string
  downloadCount: number
  viewCount: number
  createdBy: number
  createdAt: string
  updatedAt: string
}

export interface StartRecordingRequest {
  meetingId: number
  recordingName?: string
  recordingType?: 'FULL_MEETING' | 'SCREEN_SHARE' | 'AUDIO_ONLY' | 'HIGHLIGHTS'
  fileFormat?: 'MP4' | 'WEBM' | 'MP3' | 'M4A'
  config: RecordingConfig
}

export interface PlaybackInfo {
  recordingId: number
  playbackToken: string
  playbackConfig: {
    videoUrl: string
    duration: number
    resolution?: string
    format: string
    subtitles?: any[]
    chapters?: any[]
  }
  expiresAt: string
}

export class RecordingService {
  /**
   * 开始录制
   */
  static async startRecording(request: StartRecordingRequest): Promise<RecordingStatus> {
    const response = await api.post(`/meetings/${request.meetingId}/recordings/start`, request)
    return response.data
  }

  /**
   * 停止录制
   */
  static async stopRecording(recordingId: number): Promise<RecordingStatus> {
    const response = await api.post(`/recordings/${recordingId}/stop`)
    return response.data
  }

  /**
   * 暂停录制
   */
  static async pauseRecording(recordingId: number): Promise<RecordingStatus> {
    const response = await api.post(`/recordings/${recordingId}/pause`)
    return response.data
  }

  /**
   * 恢复录制
   */
  static async resumeRecording(recordingId: number): Promise<RecordingStatus> {
    const response = await api.post(`/recordings/${recordingId}/resume`)
    return response.data
  }

  /**
   * 获取会议录制列表
   */
  static async getMeetingRecordings(meetingId: number): Promise<RecordingStatus[]> {
    const response = await api.get(`/meetings/${meetingId}/recordings`)
    return response.data
  }

  /**
   * 获取录制详情
   */
  static async getRecordingDetails(recordingId: number): Promise<RecordingStatus> {
    const response = await api.get(`/recordings/${recordingId}`)
    return response.data
  }

  /**
   * 获取录制播放信息
   */
  static async getPlaybackInfo(recordingId: number): Promise<PlaybackInfo> {
    const response = await api.get(`/recordings/${recordingId}/playback`)
    return response.data
  }

  /**
   * 删除录制
   */
  static async deleteRecording(recordingId: number): Promise<void> {
    await api.delete(`/recordings/${recordingId}`)
  }

  /**
   * 更新录制信息
   */
  static async updateRecording(recordingId: number, updates: Partial<RecordingStatus>): Promise<RecordingStatus> {
    const response = await api.put(`/recordings/${recordingId}`, updates)
    return response.data
  }

  /**
   * 检查录制权限
   */
  static async checkRecordingPermission(meetingId: number): Promise<{
    canRecord: boolean
    canStart: boolean
    canStop: boolean
    canPause: boolean
    reason?: string
  }> {
    const response = await api.get(`/meetings/${meetingId}/recording-permissions`)
    return response.data
  }

  /**
   * 获取存储配额信息
   */
  static async getStorageQuota(): Promise<{
    used: number
    total: number
    available: number
    unit: string
  }> {
    const response = await api.get('/recordings/storage-quota')
    return response.data
  }

  /**
   * 获取录制配置选项
   */
  static async getRecordingOptions(): Promise<{
    qualities: Array<{ value: string; label: string; description: string }>
    formats: Array<{ value: string; label: string; description: string }>
    maxDuration: number
    maxFileSize: number
  }> {
    const response = await api.get('/recordings/options')
    return response.data
  }
}

export default RecordingService