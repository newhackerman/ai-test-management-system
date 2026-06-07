import { apiClient } from '@/services/api/client'
import { MeetingRecording, RecordingType, FileFormat } from '@/types/meeting'

export interface StartRecordingRequest {
  name?: string
  type?: RecordingType
  format?: FileFormat
  quality?: 'LOW' | 'MEDIUM' | 'HIGH' | 'HD'
  includeAudio?: boolean
  includeVideo?: boolean
  includeScreenShare?: boolean
}

export interface RecordingPlaybackInfo {
  recording_id: number
  playback_token: string
  playback_config: {
    video_url: string
    duration: number
    resolution?: string
    format: string
    subtitles?: Array<{
      language: string
      url: string
    }>
    chapters?: Array<{
      title: string
      start_time: number
      end_time: number
    }>
  }
  expires_at: string
}

export interface RecordingShareInfo {
  share_id: string
  share_url: string
  access_type: 'PUBLIC' | 'PASSWORD' | 'PRIVATE'
  password?: string
  expires_at?: string
  download_enabled: boolean
}

export class RecordingService {
  private baseUrl = '/api/v1/meetings'

  // 录制控制
  async startRecording(meetingId: number, config: StartRecordingRequest): Promise<MeetingRecording> {
    const response = await apiClient.post<MeetingRecording>(
      `${this.baseUrl}/${meetingId}/recordings/start`,
      config
    )
    return response.data
  }

  async stopRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.post<MeetingRecording>(
      `/api/v1/recordings/${recordingId}/stop`
    )
    return response.data
  }

  async pauseRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.post<MeetingRecording>(
      `/api/v1/recordings/${recordingId}/pause`
    )
    return response.data
  }

  async resumeRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.post<MeetingRecording>(
      `/api/v1/recordings/${recordingId}/resume`
    )
    return response.data
  }

  // 录制管理
  async getRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.get<MeetingRecording>(
      `/api/v1/recordings/${recordingId}`
    )
    return response.data
  }

  async getMeetingRecordings(meetingId: number): Promise<MeetingRecording[]> {
    const response = await apiClient.get<MeetingRecording[]>(
      `${this.baseUrl}/${meetingId}/recordings`
    )
    return response.data
  }

  async getAllRecordings(params?: {
    page?: number
    pageSize?: number
    status?: string
    type?: RecordingType
    startDate?: string
    endDate?: string
    searchQuery?: string
  }): Promise<{
    recordings: MeetingRecording[]
    total: number
    page: number
    pageSize: number
  }> {
    const response = await apiClient.get('/api/v1/recordings', { params })
    return response.data
  }

  async updateRecording(recordingId: number, updates: {
    recording_name?: string
    description?: string
    is_public?: boolean
    access_password?: string
  }): Promise<MeetingRecording> {
    const response = await apiClient.put<MeetingRecording>(
      `/api/v1/recordings/${recordingId}`,
      updates
    )
    return response.data
  }

  async deleteRecording(recordingId: number): Promise<void> {
    await apiClient.delete(`/api/v1/recordings/${recordingId}`)
  }

  // 录制回放
  async getPlaybackInfo(recordingId: number): Promise<RecordingPlaybackInfo> {
    const response = await apiClient.get<RecordingPlaybackInfo>(
      `/api/v1/recordings/${recordingId}/playback`
    )
    return response.data
  }

  async generatePlaybackToken(recordingId: number, options?: {
    expiresIn?: number // 秒
    allowDownload?: boolean
    watermark?: string
  }): Promise<string> {
    const response = await apiClient.post<{ token: string }>(
      `/api/v1/recordings/${recordingId}/playback/token`,
      options
    )
    return response.data.token
  }

  async updatePlaybackProgress(recordingId: number, progress: {
    currentTime: number
    duration: number
    watchedPercentage: number
  }): Promise<void> {
    await apiClient.post(
      `/api/v1/recordings/${recordingId}/playback/progress`,
      progress
    )
  }

  // 录制分享
  async createShareLink(recordingId: number, options: {
    accessType: 'PUBLIC' | 'PASSWORD' | 'PRIVATE'
    password?: string
    expiresAt?: string
    allowDownload?: boolean
    allowComments?: boolean
  }): Promise<RecordingShareInfo> {
    const response = await apiClient.post<RecordingShareInfo>(
      `/api/v1/recordings/${recordingId}/share`,
      options
    )
    return response.data
  }

  async getShareInfo(shareId: string): Promise<RecordingShareInfo> {
    const response = await apiClient.get<RecordingShareInfo>(
      `/api/v1/recordings/share/${shareId}`
    )
    return response.data
  }

  async updateShareSettings(shareId: string, updates: {
    accessType?: 'PUBLIC' | 'PASSWORD' | 'PRIVATE'
    password?: string
    expiresAt?: string
    allowDownload?: boolean
  }): Promise<RecordingShareInfo> {
    const response = await apiClient.put<RecordingShareInfo>(
      `/api/v1/recordings/share/${shareId}`,
      updates
    )
    return response.data
  }

  async revokeShareLink(shareId: string): Promise<void> {
    await apiClient.delete(`/api/v1/recordings/share/${shareId}`)
  }

  // 录制下载
  async downloadRecording(recordingId: number, format?: FileFormat): Promise<string> {
    const response = await apiClient.get(
      `/api/v1/recordings/${recordingId}/download`,
      { 
        params: { format },
        responseType: 'blob'
      }
    )
    
    // 创建下载链接
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    return url
  }

  async getDownloadUrl(recordingId: number, format?: FileFormat): Promise<string> {
    const response = await apiClient.get<{ download_url: string }>(
      `/api/v1/recordings/${recordingId}/download-url`,
      { params: { format } }
    )
    return response.data.download_url
  }

  // 录制转换
  async convertRecording(recordingId: number, options: {
    targetFormat: FileFormat
    quality?: 'LOW' | 'MEDIUM' | 'HIGH'
    resolution?: string
    bitrate?: number
  }): Promise<{ taskId: string }> {
    const response = await apiClient.post<{ taskId: string }>(
      `/api/v1/recordings/${recordingId}/convert`,
      options
    )
    return response.data
  }

  async getConversionStatus(taskId: string): Promise<{
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
    progress: number
    result?: {
      recordingId: number
      downloadUrl: string
    }
    error?: string
  }> {
    const response = await apiClient.get(`/api/v1/recordings/convert/${taskId}/status`)
    return response.data
  }

  // 录制分析
  async getRecordingAnalytics(recordingId: number): Promise<{
    viewCount: number
    downloadCount: number
    averageWatchTime: number
    completionRate: number
    viewersByRegion: Record<string, number>
    viewersByDevice: Record<string, number>
    engagementMetrics: {
      totalViews: number
      uniqueViewers: number
      repeatViewers: number
      averageSessionDuration: number
    }
  }> {
    const response = await apiClient.get(`/api/v1/recordings/${recordingId}/analytics`)
    return response.data
  }

  // 录制字幕
  async generateSubtitles(recordingId: number, options?: {
    language?: string
    autoTranslate?: boolean
    targetLanguages?: string[]
  }): Promise<{ taskId: string }> {
    const response = await apiClient.post<{ taskId: string }>(
      `/api/v1/recordings/${recordingId}/subtitles/generate`,
      options
    )
    return response.data
  }

  async getSubtitles(recordingId: number, language?: string): Promise<Array<{
    language: string
    url: string
    format: 'SRT' | 'VTT' | 'ASS'
  }>> {
    const response = await apiClient.get(
      `/api/v1/recordings/${recordingId}/subtitles`,
      { params: { language } }
    )
    return response.data
  }

  async uploadSubtitles(recordingId: number, file: File, language: string): Promise<void> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('language', language)

    await apiClient.post(
      `/api/v1/recordings/${recordingId}/subtitles/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
  }

  // 录制章节
  async addChapter(recordingId: number, chapter: {
    title: string
    startTime: number
    endTime?: number
    description?: string
  }): Promise<{ chapterId: string }> {
    const response = await apiClient.post<{ chapterId: string }>(
      `/api/v1/recordings/${recordingId}/chapters`,
      chapter
    )
    return response.data
  }

  async getChapters(recordingId: number): Promise<Array<{
    id: string
    title: string
    startTime: number
    endTime: number
    description?: string
  }>> {
    const response = await apiClient.get(`/api/v1/recordings/${recordingId}/chapters`)
    return response.data
  }

  async updateChapter(recordingId: number, chapterId: string, updates: {
    title?: string
    startTime?: number
    endTime?: number
    description?: string
  }): Promise<void> {
    await apiClient.put(
      `/api/v1/recordings/${recordingId}/chapters/${chapterId}`,
      updates
    )
  }

  async deleteChapter(recordingId: number, chapterId: string): Promise<void> {
    await apiClient.delete(`/api/v1/recordings/${recordingId}/chapters/${chapterId}`)
  }

  // 录制评论
  async addComment(recordingId: number, comment: {
    content: string
    timestamp?: number
    parentId?: string
  }): Promise<{ commentId: string }> {
    const response = await apiClient.post<{ commentId: string }>(
      `/api/v1/recordings/${recordingId}/comments`,
      comment
    )
    return response.data
  }

  async getComments(recordingId: number, params?: {
    page?: number
    pageSize?: number
    sortBy?: 'timestamp' | 'created_at'
    sortOrder?: 'asc' | 'desc'
  }): Promise<{
    comments: Array<{
      id: string
      content: string
      timestamp?: number
      author: {
        id: number
        name: string
        avatar?: string
      }
      createdAt: string
      replies?: any[]
    }>
    total: number
  }> {
    const response = await apiClient.get(
      `/api/v1/recordings/${recordingId}/comments`,
      { params }
    )
    return response.data
  }

  // 批量操作
  async batchDeleteRecordings(recordingIds: number[]): Promise<void> {
    await apiClient.post('/api/v1/recordings/batch/delete', {
      recording_ids: recordingIds
    })
  }

  async batchUpdateRecordings(recordingIds: number[], updates: {
    is_public?: boolean
    access_password?: string
  }): Promise<void> {
    await apiClient.post('/api/v1/recordings/batch/update', {
      recording_ids: recordingIds,
      updates
    })
  }

  // 存储管理
  async getStorageUsage(): Promise<{
    totalSize: number
    usedSize: number
    availableSize: number
    recordingCount: number
    sizeByFormat: Record<FileFormat, number>
  }> {
    const response = await apiClient.get('/api/v1/recordings/storage/usage')
    return response.data
  }

  async cleanupExpiredRecordings(): Promise<{
    deletedCount: number
    freedSpace: number
  }> {
    const response = await apiClient.post('/api/v1/recordings/storage/cleanup')
    return response.data
  }
}

// 创建单例实例
export const recordingService = new RecordingService()

// 导出默认实例
export default recordingService