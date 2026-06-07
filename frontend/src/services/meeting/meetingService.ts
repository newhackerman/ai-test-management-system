import { apiClient } from '@/services/api/client'
import { 
  Meeting, 
  MeetingParticipant, 
  CreateMeetingRequest, 
  UpdateMeetingRequest,
  InviteParticipantRequest,
  MeetingJoinResult,
  MeetingSearchParams,
  MeetingStats
} from '@/types/meeting'

export class MeetingService {
  private baseUrl = '/api/v1/meetings'

  private unwrap<T>(response: any): T {
    return response?.data?.data ?? response?.data ?? response
  }

  private toApiMeetingPayload(data: Partial<CreateMeetingRequest & UpdateMeetingRequest>) {
    const participantIds = (data as CreateMeetingRequest).participant_ids ||
      (data as CreateMeetingRequest).participants?.map((item) => item.user_id).filter(Boolean)

    const payload: any = {
      ...data,
      participant_ids: participantIds,
    }
    delete payload.participants
    delete payload.participant_ids_ui
    return payload
  }

  // 会议CRUD操作
  async createMeeting(data: CreateMeetingRequest): Promise<Meeting> {
    const response = await apiClient.post(this.baseUrl, this.toApiMeetingPayload(data))
    return this.unwrap<Meeting>(response)
  }

  async getMeeting(id: number): Promise<Meeting> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`)
    return this.unwrap<Meeting>(response)
  }

  async getMeetingByCode(code: string): Promise<Meeting> {
    const response = await apiClient.get<Meeting>(`${this.baseUrl}/code/${code}`)
    return response.data
  }

  async updateMeeting(id: number, data: UpdateMeetingRequest): Promise<Meeting> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, this.toApiMeetingPayload(data))
    return this.unwrap<Meeting>(response)
  }

  async deleteMeeting(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`)
  }

  // 会议列表和搜索
  async getMeetings(params?: MeetingSearchParams): Promise<{
    meetings: Meeting[]
    total: number
    page: number
    pageSize: number
  }> {
    const apiParams = {
      page: params?.page,
      page_size: params?.page_size,
      meeting_type: params?.meeting_type || params?.type,
      status: params?.status,
      project_id: params?.project_id,
      organizer_id: params?.organizer_id,
      start_date: params?.start_date || params?.date_from,
      end_date: params?.end_date || params?.date_to,
      keyword: params?.keyword || params?.query,
      sort_by: params?.sort_by,
      sort_order: params?.sort_order,
    }
    const response = await apiClient.get(this.baseUrl, { params: apiParams })
    const payload: any = response.data || response
    return {
      meetings: payload.meetings || [],
      total: payload.total || 0,
      page: payload.page || params?.page || 1,
      pageSize: payload.page_size || params?.page_size || 20,
    }
  }

  async searchMeetings(query: string, filters?: Partial<MeetingSearchParams>): Promise<Meeting[]> {
    const params = { query, ...filters }
    const response = await apiClient.get(`${this.baseUrl}/search`, { params })
    return response.data
  }

  // 会议操作
  async joinMeeting(meetingCode: string, options?: {
    audio?: boolean
    video?: boolean
    displayName?: string
  }): Promise<MeetingJoinResult> {
    const response = await apiClient.post<MeetingJoinResult>(
      `${this.baseUrl}/${meetingCode}/join`, 
      options
    )
    return response.data
  }

  async leaveMeeting(meetingCode: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingCode}/leave`)
  }

  async startMeeting(id: number): Promise<Meeting> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/start`, { action: 'start' })
    return this.unwrap<Meeting>(response)
  }

  async endMeeting(id: number, minutes?: {
    minutes_title?: string
    minutes_content?: string
    minutes_summary?: string
    key_points?: string[]
    decisions?: Array<Record<string, any>>
    action_items?: Array<Record<string, any>>
  }): Promise<Meeting> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/end`, { action: 'end', ...minutes })
    return this.unwrap<Meeting>(response)
  }

  async cancelMeeting(id: number, reason?: string): Promise<Meeting> {
    const response = await apiClient.post<Meeting>(`${this.baseUrl}/${id}/cancel`, { reason })
    return response.data
  }

  async postponeMeeting(id: number, newStartTime: string, newEndTime: string): Promise<Meeting> {
    const response = await apiClient.post<Meeting>(`${this.baseUrl}/${id}/postpone`, {
      scheduled_start_time: newStartTime,
      scheduled_end_time: newEndTime
    })
    return response.data
  }

  // 参与者管理
  async getParticipants(meetingId: number): Promise<MeetingParticipant[]> {
    const response = await apiClient.get<MeetingParticipant[]>(
      `${this.baseUrl}/${meetingId}/participants`
    )
    return response.data
  }

  async inviteParticipant(meetingId: number, data: InviteParticipantRequest): Promise<MeetingParticipant> {
    const response = await apiClient.post<MeetingParticipant>(
      `${this.baseUrl}/${meetingId}/participants`,
      data
    )
    return response.data
  }

  async inviteParticipants(meetingId: number, participants: InviteParticipantRequest[]): Promise<MeetingParticipant[]> {
    const response = await apiClient.post<MeetingParticipant[]>(
      `${this.baseUrl}/${meetingId}/participants/batch`,
      { participants }
    )
    return response.data
  }

  async updateParticipant(
    meetingId: number, 
    participantId: number, 
    updates: Partial<MeetingParticipant>
  ): Promise<MeetingParticipant> {
    const response = await apiClient.put<MeetingParticipant>(
      `${this.baseUrl}/${meetingId}/participants/${participantId}`,
      updates
    )
    return response.data
  }

  async removeParticipant(meetingId: number, participantId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/participants/${participantId}`)
  }

  async updateParticipantPermissions(
    meetingId: number, 
    participantId: number, 
    permissions: {
      can_share_screen?: boolean
      can_use_chat?: boolean
      can_use_whiteboard?: boolean
      can_record?: boolean
    }
  ): Promise<MeetingParticipant> {
    const response = await apiClient.patch<MeetingParticipant>(
      `${this.baseUrl}/${meetingId}/participants/${participantId}/permissions`,
      permissions
    )
    return response.data
  }

  async kickParticipant(meetingId: number, participantId: number, reason?: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/participants/${participantId}/kick`, { reason })
  }

  // 会议控制
  async muteParticipant(meetingId: number, participantId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/participants/${participantId}/mute`)
  }

  async unmuteParticipant(meetingId: number, participantId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/participants/${participantId}/unmute`)
  }

  async muteAllParticipants(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/mute-all`)
  }

  async unmuteAllParticipants(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/unmute-all`)
  }

  // 会议设置
  async updateMeetingSettings(meetingId: number, settings: any): Promise<Meeting> {
    const response = await apiClient.patch<Meeting>(
      `${this.baseUrl}/${meetingId}/settings`,
      settings
    )
    return response.data
  }

  async enableWaitingRoom(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/waiting-room/enable`)
  }

  async disableWaitingRoom(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/waiting-room/disable`)
  }

  async lockMeeting(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/lock`)
  }

  async unlockMeeting(meetingId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/unlock`)
  }

  // 会议统计
  async getMeetingStats(params?: {
    startDate?: string
    endDate?: string
    projectId?: number
    organizerId?: number
  }): Promise<MeetingStats> {
    const response = await apiClient.get<MeetingStats>(`${this.baseUrl}/stats`, { params })
    return response.data
  }

  async getMeetingAnalytics(meetingId: number): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/${meetingId}/analytics`)
    return response.data
  }

  // 会议模板
  async getMeetingTemplates(): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/templates`)
    return response.data
  }

  async createMeetingFromTemplate(templateId: number, data: Partial<CreateMeetingRequest>): Promise<Meeting> {
    const response = await apiClient.post<Meeting>(
      `${this.baseUrl}/templates/${templateId}/create`,
      data
    )
    return response.data
  }

  // 智能调度
  async findOptimalTime(participants: number[], duration: number, preferences?: {
    preferredTimeRange?: [string, string]
    timezone?: string
    excludeWeekends?: boolean
  }): Promise<{
    suggestedTimes: Array<{
      startTime: string
      endTime: string
      score: number
      conflicts: number
    }>
  }> {
    const response = await apiClient.post(`${this.baseUrl}/schedule/optimal`, {
      participants,
      duration,
      ...preferences
    })
    return response.data
  }

  async checkTimeConflicts(participants: number[], startTime: string, endTime: string): Promise<{
    hasConflicts: boolean
    conflicts: Array<{
      participantId: number
      conflictingMeetings: Meeting[]
    }>
  }> {
    const response = await apiClient.post(`${this.baseUrl}/schedule/conflicts`, {
      participants,
      start_time: startTime,
      end_time: endTime
    })
    return response.data
  }

  // 会议邀请
  async sendInvitations(meetingId: number, participantIds?: number[]): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/invitations/send`, {
      participant_ids: participantIds
    })
  }

  async resendInvitation(meetingId: number, participantId: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/participants/${participantId}/invite/resend`)
  }

  async respondToInvitation(meetingId: number, response: 'ACCEPTED' | 'DECLINED' | 'TENTATIVE'): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/invitation/respond`, { response })
  }

  // 日历集成
  async exportToCalendar(meetingId: number, format: 'ics' | 'outlook' | 'google'): Promise<string> {
    const response = await apiClient.get(`${this.baseUrl}/${meetingId}/calendar/export`, {
      params: { format },
      responseType: 'text'
    })
    return response.data
  }

  // 错误处理和重试
  private async withRetry<T>(operation: () => Promise<T>, maxRetries = 3): Promise<T> {
    let lastError: Error
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await operation()
      } catch (error) {
        lastError = error as Error
        
        // 如果是网络错误或服务器错误，进行重试
        if (i < maxRetries - 1 && this.shouldRetry(error)) {
          await this.delay(Math.pow(2, i) * 1000) // 指数退避
          continue
        }
        
        throw error
      }
    }
    
    throw lastError!
  }

  private shouldRetry(error: any): boolean {
    // 网络错误或5xx服务器错误可以重试
    return (
      !error.response || 
      error.code === 'NETWORK_ERROR' ||
      (error.response.status >= 500 && error.response.status < 600)
    )
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// 创建单例实例
export const meetingService = new MeetingService()

// 导出默认实例
export default meetingService
