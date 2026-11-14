// @ts-nocheck
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

export interface RecordingListParams {
  page?: number
  pageSize?: number
  status?: string
  type?: RecordingType
  format?: FileFormat
  startDate?: string
  endDate?: string
  searchQuery?: string
}

export interface RecordingListPage {
  recordings: MeetingRecording[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

/**
 * 录制服务（会议模块用这个；另有一个同名 services/recordingService.ts
 * 是旧的静态类，供 useRecording hook 用，两者不要混用）。
 *
 * 后端路由挂在 /api/v1/meetings/recordings 下。历史遗留问题：
 * 本文件曾有一批方法调 /api/v1/recordings/…（share、download、
 * subtitles、chapters、comments、batch、storage、playback token 等），
 * 该前缀后端不存在；其中 share/download 已改到正确前缀，其余高级
 * 端点后端至今没有（字幕/章节/评论/转换/批量/存储管理/播放 token
 * 均为第一版裁剪项，见文末注释），相关方法已删除，不再留 404 调用。
 */
export class RecordingService {
  private baseUrl = '/api/v1/meetings'

  private toListPage(body: any): RecordingListPage {
    return {
      recordings: body?.recordings ?? [],
      total: body?.total ?? 0,
      page: body?.page ?? 1,
      pageSize: body?.page_size ?? body?.pageSize ?? 20,
      totalPages: body?.total_pages ?? body?.totalPages ?? 1,
    }
  }

  private toListQuery(params?: RecordingListParams): Record<string, any> {
    if (!params) return {}
    return {
      page: params.page,
      page_size: params.pageSize,
      status: params.status,
      recording_type: params.type,
      file_format: params.format,
      start_date: params.startDate,
      end_date: params.endDate,
      keyword: params.searchQuery,
    }
  }

  // 录制控制
  async startRecording(meetingId: number, config: StartRecordingRequest): Promise<MeetingRecording> {
    const qualityMap: Record<string, string> = { LOW: 'low', MEDIUM: 'standard', HIGH: 'high', HD: 'high' }
    const response = await apiClient.post(
      `${this.baseUrl}/recordings/${meetingId}/recordings/start`,
      {
        recording_name: config.name,
        recording_type: config.type,
        file_format: config.format,
        quality: qualityMap[config.quality || 'MEDIUM'],
        auto_transcription: true,
        include_chat: true,
        include_whiteboard: true,
      }
    )
    // 开始接口返回 {success, recording_id, message, data} 包裹形
    return response.data?.data
  }

  async stopRecording(recordingId: number): Promise<MeetingRecording> {
    await apiClient.post(
      `/api/v1/meetings/recordings/${recordingId}/stop`
    )
    // 停止接口只返回 {success, recording_id, message}，取详情再返回
    return this.getRecording(recordingId)
  }

  async pauseRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.post(
      `/api/v1/meetings/recordings/${recordingId}/pause`
    )
    return response.data?.data
  }

  async resumeRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.post(
      `/api/v1/meetings/recordings/${recordingId}/resume`
    )
    return response.data?.data
  }

  // 录制管理
  async getRecording(recordingId: number): Promise<MeetingRecording> {
    const response = await apiClient.get<MeetingRecording>(
      `/api/v1/meetings/recordings/${recordingId}`
    )
    return response.data
  }

  async getMeetingRecordings(meetingId: number, params?: RecordingListParams): Promise<RecordingListPage> {
    const response = await apiClient.get(
      `${this.baseUrl}/recordings/${meetingId}/recordings`,
      { params: this.toListQuery(params) }
    )
    // 后端返回 {recordings, total, page, page_size, total_pages} 对象，
    // 不是数组；此前直接当数组返回，列表页拿不到数据。
    return this.toListPage(response.data)
  }

  async getAllRecordings(params?: RecordingListParams): Promise<RecordingListPage> {
    // 全局列表后端端点：GET /api/v1/meetings/recordings/all。
    // 此前调的 GET /api/v1/recordings 后端不存在（404）；裸
    // GET /api/v1/meetings/recordings 也会被
    // GET /api/v1/meetings/{meeting_id} 截获成 422，见后端注释。
    const response = await apiClient.get('/api/v1/meetings/recordings/all', {
      params: this.toListQuery(params),
    })
    return this.toListPage(response.data)
  }

  async updateRecording(recordingId: number, updates: {
    recording_name?: string
    is_public?: boolean
    access_password?: string
  }): Promise<MeetingRecording> {
    // 注意：没有 description 字段——MeetingRecording 模型无此列，
    // 传了也落不了盘（见后端 UpdateRecordingRequest 注释）。
    const response = await apiClient.put<MeetingRecording>(
      `/api/v1/meetings/recordings/${recordingId}`,
      updates
    )
    return response.data
  }

  async deleteRecording(recordingId: number): Promise<void> {
    await apiClient.delete(`/api/v1/meetings/recordings/${recordingId}`)
  }

  async getStatistics(meetingId?: number): Promise<{
    total_recordings: number
    active_recordings: number
    completed_recordings: number
    failed_recordings: number
    total_duration_minutes: number
    total_file_size_mb: number
    by_type: Record<string, number>
    by_format: Record<string, number>
  }> {
    const response = await apiClient.get('/api/v1/meetings/recordings/statistics', {
      params: meetingId ? { meeting_id: meetingId } : {},
    })
    return response.data
  }

  // 录制回放
  async getPlaybackInfo(recordingId: number): Promise<RecordingPlaybackInfo> {
    const response = await apiClient.get<RecordingPlaybackInfo>(
      `/api/v1/meetings/recordings/${recordingId}/playback`
    )
    return response.data
  }

  // 录制分享
  async createShareLink(recordingId: number, options: {
    accessType: 'PUBLIC' | 'PASSWORD' | 'PRIVATE'
    password?: string
    expiresAt?: string
    allowDownload?: boolean
    allowComments?: boolean
  }): Promise<RecordingShareInfo> {
    // 此前调 POST /api/v1/recordings/{id}/share，前缀错误；
    // 后端真实路径是 /api/v1/meetings/recordings/{id}/share，
    // 请求体是 {is_public, access_password, expires_at, allow_download}。
    // 非公开分享后端强制要求密码（无密码 → 422）。
    const isPublic = options.accessType === 'PUBLIC'
    if (!isPublic && !options.password) {
      throw new Error('非公开分享必须设置访问密码')
    }
    const response = await apiClient.post(
      `/api/v1/meetings/recordings/${recordingId}/share`,
      {
        is_public: isPublic,
        access_password: options.password,
        expires_at: options.expiresAt,
        allow_download: options.allowDownload ?? true,
      }
    )
    const body = response.data
    return {
      share_id: body?.share_code ?? String(recordingId),
      share_url: body?.share_url ?? `/meetings/recordings/${recordingId}`,
      access_type: options.accessType,
      password: options.password,
      expires_at: body?.expires_at ?? options.expiresAt,
      download_enabled: options.allowDownload ?? true,
    }
  }

  // 录制下载
  async downloadRecording(recordingId: number, format?: FileFormat): Promise<string> {
    // 此前调 GET /api/v1/recordings/{id}/download，前缀错误且后端
    // 无此路由；真实路径是 /api/v1/meetings/recordings/{id}/download，
    // 带 Bearer 鉴权走 blob 下载（<a href> 直链没法带请求头）。
    const response = await apiClient.get(
      `/api/v1/meetings/recordings/${recordingId}/download`,
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
    // 仅返回下载端点路径；直接当 <a href> 用会 401（全局中间件要求
    // Bearer 头），下载请走 downloadRecording（blob），播放请走
    // getPlaybackInfo 返回的 video_url（带播放 token）。
    return `/api/v1/meetings/recordings/${recordingId}/download`
  }
}

// 创建单例实例
export const recordingService = new RecordingService()

// 导出默认实例
export default recordingService

/**
 * 第一版裁剪、不再提供的方法（后端无对应端点，留着只会调出 404）：
 * 播放 token 生成 / 播放进度上报、分享查询与修改/撤销、格式转换与
 * 转换状态、录制分析、字幕生成/查询/上传、章节增删改查、评论增查、
 * 批量删除/更新、存储用量与过期清理。如后续后端补齐，再按
 * /api/v1/meetings/recordings/{id}/… 前缀逐个加回。
 */
