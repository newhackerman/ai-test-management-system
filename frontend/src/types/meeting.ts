// 会议类型枚举
export const MeetingType = {
  PROJECT_KICKOFF: 'PROJECT_KICKOFF',
  REQUIREMENT_REVIEW: 'REQUIREMENT_REVIEW',
  DESIGN_REVIEW: 'DESIGN_REVIEW',
  CODE_REVIEW: 'CODE_REVIEW',
  TEST_REVIEW: 'TEST_REVIEW',
  PROGRESS_SYNC: 'PROGRESS_SYNC',
  PROBLEM_SOLVING: 'PROBLEM_SOLVING',
  PROJECT_SUMMARY: 'PROJECT_SUMMARY',
  TRAINING: 'TRAINING',
  OTHER: 'OTHER'
} as const
export type MeetingType = typeof MeetingType[keyof typeof MeetingType]

// 会议状态枚举
export const MeetingStatus = {
  SCHEDULED: 'SCHEDULED',
  IN_PROGRESS: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
  CANCELLED: 'CANCELLED',
  POSTPONED: 'POSTPONED'
} as const
export type MeetingStatus = typeof MeetingStatus[keyof typeof MeetingStatus]

// 参与者角色枚举
export const ParticipantRole = {
  ORGANIZER: 'ORGANIZER',
  MODERATOR: 'MODERATOR',
  PRESENTER: 'PRESENTER',
  PARTICIPANT: 'PARTICIPANT',
  OBSERVER: 'OBSERVER'
} as const
export type ParticipantRole = typeof ParticipantRole[keyof typeof ParticipantRole]

// 邀请状态枚举
export const InvitationStatus = {
  PENDING: 'PENDING',
  ACCEPTED: 'ACCEPTED',
  DECLINED: 'DECLINED',
  TENTATIVE: 'TENTATIVE'
} as const
export type InvitationStatus = typeof InvitationStatus[keyof typeof InvitationStatus]

// 出席状态枚举
export const AttendanceStatus = {
  NOT_JOINED: 'NOT_JOINED',
  JOINED: 'JOINED',
  LEFT: 'LEFT',
  KICKED_OUT: 'KICKED_OUT'
} as const
export type AttendanceStatus = typeof AttendanceStatus[keyof typeof AttendanceStatus]

// 录制类型枚举
export const RecordingType = {
  FULL_MEETING: 'FULL_MEETING',
  SCREEN_SHARE: 'SCREEN_SHARE',
  AUDIO_ONLY: 'AUDIO_ONLY',
  HIGHLIGHTS: 'HIGHLIGHTS'
} as const
export type RecordingType = typeof RecordingType[keyof typeof RecordingType]

// 录制状态枚举
export const RecordingStatus = {
  RECORDING: 'RECORDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  DELETED: 'DELETED'
} as const
export type RecordingStatus = typeof RecordingStatus[keyof typeof RecordingStatus]

// 文件格式枚举
export const FileFormat = {
  MP4: 'MP4',
  WEBM: 'WEBM',
  MP3: 'MP3',
  M4A: 'M4A'
} as const
export type FileFormat = typeof FileFormat[keyof typeof FileFormat]

// 用户基本信息
export interface User {
  id: number
  name: string
  email: string
  avatar?: string
  timezone?: string
}

// 会议实体
export interface Meeting {
  id: number
  meeting_code: string
  title: string
  description?: string
  meeting_type: MeetingType
  status: MeetingStatus
  
  // 时间管理
  scheduled_start_time: string
  scheduled_end_time: string
  actual_start_time?: string
  actual_end_time?: string
  timezone: string
  
  // 会议配置
  max_participants: number
  is_recording_enabled: boolean
  is_waiting_room_enabled: boolean
  is_password_protected: boolean
  meeting_password?: string
  
  // 关联信息
  project_id?: number
  organizer_id: number
  organizer?: User
  
  // 会议设置
  agenda?: AgendaItem[]
  meeting_settings?: MeetingSettings
  
  // 统计信息
  participant_count: number
  duration_minutes: number
  
  // 审计字段
  created_at: string
  updated_at: string
}

// 议程项目
export interface AgendaItem {
  id: string
  title: string
  description?: string
  duration_minutes: number
  presenter?: string
  order: number
}

// 会议设置
export interface MeetingSettings {
  auto_record?: boolean
  allow_screen_share?: boolean
  allow_chat?: boolean
  allow_whiteboard?: boolean
  mute_on_join?: boolean
  video_on_join?: boolean
  waiting_room_enabled?: boolean
  lobby_enabled?: boolean
  max_participants?: number
}

// 会议参与者
export interface MeetingParticipant {
  id: number
  meeting_id: number
  user_id: number
  user?: User
  participant_role: ParticipantRole
  invitation_status: InvitationStatus
  attendance_status: AttendanceStatus
  
  // 权限设置
  can_share_screen: boolean
  can_use_chat: boolean
  can_use_whiteboard: boolean
  can_record: boolean
  
  // 参与统计
  join_time?: string
  leave_time?: string
  total_duration_minutes: number
  speak_duration_minutes: number
  interaction_count: number
  
  // 设备信息
  device_info?: DeviceInfo
  network_quality?: NetworkQuality
  
  // 审计字段
  invited_at: string
  updated_at: string
}

// 设备信息
export interface DeviceInfo {
  browser?: string
  os?: string
  device_type?: 'desktop' | 'mobile' | 'tablet'
  audio_device?: string
  video_device?: string
}

// 网络质量
export interface NetworkQuality {
  connection_type?: string
  bandwidth?: number
  latency?: number
  packet_loss?: number
  quality_score?: number
}

// 会议录制
export interface MeetingRecording {
  id: number
  meeting_id: number
  recording_name: string
  recording_type: RecordingType
  file_format: FileFormat
  
  // 文件信息
  file_path: string
  file_size: number
  duration_seconds: number
  resolution?: string
  
  // 录制状态
  recording_status: RecordingStatus
  processing_progress: number
  
  // 时间信息
  start_time: string
  end_time?: string
  
  // 访问控制
  is_public: boolean
  access_password?: string
  download_count: number
  view_count: number
  
  // 审计字段
  created_by: number
  created_at: string
  updated_at: string
}

// 会议纪要
export interface MeetingMinutes {
  id: number
  meeting_id: number
  title: string
  content: string
  summary?: string
  
  // 纪要类型
  minute_type: 'AUTO_GENERATED' | 'MANUAL_CREATED' | 'AI_ENHANCED' | 'COLLABORATIVE'
  generation_method?: 'SPEECH_TO_TEXT' | 'MANUAL_INPUT' | 'AI_ANALYSIS' | 'TEMPLATE_BASED'
  
  // 结构化内容
  agenda_items?: AgendaItem[]
  decisions?: Decision[]
  action_items?: ActionItem[]
  attendees?: string[]
  key_points?: string[]
  
  // 状态管理
  status: 'DRAFT' | 'UNDER_REVIEW' | 'APPROVED' | 'PUBLISHED' | 'ARCHIVED'
  approval_required: boolean
  
  // 版本管理
  version: string
  parent_minute_id?: number
  
  // 审计字段
  created_by: number
  approved_by?: number
  created_at: string
  updated_at: string
  approved_at?: string
}

// 决策事项
export interface Decision {
  id: string
  title: string
  description: string
  decision_maker: string
  decision_date: string
  impact: 'LOW' | 'MEDIUM' | 'HIGH'
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'IMPLEMENTED'
}

// 行动项目
export interface ActionItem {
  id: string
  title: string
  description: string
  assignee: string
  due_date?: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  progress: number
}

// 会议加入结果
export interface MeetingJoinResult {
  status: 'SUCCESS' | 'WAITING_ROOM' | 'FAILED'
  message?: string
  access_token?: string
  meeting_config?: MeetingConfig
  webrtc_config?: WebRTCConfig
}

// 会议配置
export interface MeetingConfig {
  meeting_id: number
  participant_id: number
  permissions: {
    can_share_screen: boolean
    can_use_chat: boolean
    can_use_whiteboard: boolean
    can_record: boolean
  }
  settings: MeetingSettings
}

// WebRTC配置
export interface WebRTCConfig {
  ice_servers: RTCIceServer[]
  media_constraints: MediaStreamConstraints
  signaling_url: string
  room_id: string
}

// 会议统计
export interface MeetingStats {
  total_meetings: number
  active_meetings: number
  completed_meetings: number
  total_participants: number
  average_duration: number
  meeting_types: Record<MeetingType, number>
}

// 创建会议请求
export interface CreateMeetingRequest {
  title: string
  description?: string
  meeting_type: MeetingType
  scheduled_start_time: string
  scheduled_end_time: string
  timezone?: string
  project_id?: number
  participants?: Array<{
    user_id: number
    role: ParticipantRole
  }>
  participant_ids?: number[]
  agenda?: AgendaItem[]
  max_participants?: number
  is_recording_enabled?: boolean
  is_waiting_room_enabled?: boolean
  is_password_protected?: boolean
  meeting_settings?: MeetingSettings
  auto_schedule?: boolean
}

// 更新会议请求
export interface UpdateMeetingRequest {
  title?: string
  description?: string
  meeting_type?: MeetingType
  scheduled_start_time?: string
  scheduled_end_time?: string
  timezone?: string
  max_participants?: number
  is_recording_enabled?: boolean
  is_waiting_room_enabled?: boolean
  is_password_protected?: boolean
  agenda?: AgendaItem[]
  meeting_settings?: MeetingSettings
}

// 邀请参与者请求
export interface InviteParticipantRequest {
  user_id?: number
  email?: string
  role: ParticipantRole
  permissions?: {
    can_share_screen?: boolean
    can_use_chat?: boolean
    can_use_whiteboard?: boolean
    can_record?: boolean
  }
}

// 会议搜索参数
export interface MeetingSearchParams {
  query?: string
  keyword?: string
  status?: MeetingStatus
  type?: MeetingType
  meeting_type?: MeetingType
  date_from?: string
  date_to?: string
  start_date?: string
  end_date?: string
  organizer_id?: number
  project_id?: number
  page?: number
  page_size?: number
  sort_by?: 'created_at' | 'scheduled_start_time' | 'title'
  sort_order?: 'asc' | 'desc'
}
