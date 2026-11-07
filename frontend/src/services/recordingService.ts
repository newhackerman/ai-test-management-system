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
  recordingStatus: 'RECORDING' | 'PAUSED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'DELETED'
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

/**
 * 后端返回 snake_case，后端录制路由挂在 /api/v1/meetings/recordings 下。
 * 注意：api 拦截器已把响应解包为 body，所以这里不再取 response.data；
 * 只有暂停/恢复接口的 body 是 {success, message, data} 包裹形，需取 .data。
 */
const toCamelKey = (key: string) => key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())

function toRecordingStatus(raw: any): RecordingStatus {
  const out: Record<string, any> = {}
  Object.entries(raw || {}).forEach(([k, v]) => {
    out[toCamelKey(k)] = v
  })
  return out as RecordingStatus
}

export class RecordingService {
  /**
   * 开始录制
   */
  static async startRecording(request: StartRecordingRequest): Promise<RecordingStatus> {
    const body: any = await api.post(`/meetings/recordings/${request.meetingId}/recordings/start`, request)
    // 开始接口只返回 recording_id，取详情再返回完整录制对象
    return RecordingService.getRecordingDetails(body.recording_id)
  }

  /**
   * 停止录制
   */
  static async stopRecording(recordingId: number): Promise<RecordingStatus> {
    await api.post(`/meetings/recordings/${recordingId}/stop`)
    return RecordingService.getRecordingDetails(recordingId)
  }

  /**
   * 暂停录制
   */
  static async pauseRecording(recordingId: number): Promise<RecordingStatus> {
    const body: any = await api.post(`/meetings/recordings/${recordingId}/pause`)
    return toRecordingStatus(body.data)
  }

  /**
   * 恢复录制
   */
  static async resumeRecording(recordingId: number): Promise<RecordingStatus> {
    const body: any = await api.post(`/meetings/recordings/${recordingId}/resume`)
    return toRecordingStatus(body.data)
  }

  /**
   * 获取会议录制列表
   */
  static async getMeetingRecordings(meetingId: number): Promise<RecordingStatus[]> {
    const body: any = await api.get(`/meetings/recordings/${meetingId}/recordings`)
    return (body.recordings || []).map(toRecordingStatus)
  }

  /**
   * 获取录制详情
   */
  static async getRecordingDetails(recordingId: number): Promise<RecordingStatus> {
    const body: any = await api.get(`/meetings/recordings/${recordingId}`)
    return toRecordingStatus(body)
  }

  /**
   * 获取录制播放信息
   */
  static async getPlaybackInfo(recordingId: number): Promise<PlaybackInfo> {
    return (await api.get(`/meetings/recordings/${recordingId}/playback`)) as unknown as PlaybackInfo
  }

  /**
   * 删除录制
   */
  static async deleteRecording(recordingId: number): Promise<void> {
    await api.delete(`/meetings/recordings/${recordingId}`)
  }

  /**
   * 更新录制信息
   */
  static async updateRecording(recordingId: number, updates: Partial<RecordingStatus>): Promise<RecordingStatus> {
    const response: any = await api.put(`/meetings/recordings/${recordingId}`, updates)
    return toRecordingStatus(response.data ?? response)
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
    return (await api.get(`/meetings/${meetingId}/recording-permissions`)) as unknown as {
    canRecord: boolean
    canStart: boolean
    canStop: boolean
    canPause: boolean
    reason?: string
  }
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