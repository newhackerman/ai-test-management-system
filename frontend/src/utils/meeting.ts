import { MeetingType, MeetingStatus, ParticipantRole, RecordingStatus } from '@/types/meeting'

// 格式化日期时间
export const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export const formatFullDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化日期
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 格式化时间
export const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化时长
export const formatDuration = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes}分钟`
  }
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  
  if (remainingMinutes === 0) {
    return `${hours}小时`
  }
  
  return `${hours}小时${remainingMinutes}分钟`
}

// 格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 获取会议类型显示文本
export const getMeetingTypeText = (type: MeetingType): string => {
  const typeMap = {
    'PROJECT_KICKOFF': '项目启动',
    'REQUIREMENT_REVIEW': '需求评审',
    'DESIGN_REVIEW': '设计评审',
    'CODE_REVIEW': '代码评审',
    'TEST_REVIEW': '测试评审',
    'PROGRESS_SYNC': '进度同步',
    'PROBLEM_SOLVING': '问题解决',
    'PROJECT_SUMMARY': '项目总结',
    'TRAINING': '培训',
    'OTHER': '其他'
  }
  return typeMap[type] || type
}

// 获取会议状态显示文本
export const getMeetingStatusText = (status: MeetingStatus): string => {
  const statusMap = {
    'SCHEDULED': '已安排',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消',
    'POSTPONED': '已延期'
  }
  return statusMap[status] || status
}

// 获取会议状态颜色
export const getMeetingStatusColor = (status: MeetingStatus): string => {
  const colorMap = {
    'SCHEDULED': 'blue',
    'IN_PROGRESS': 'green',
    'COMPLETED': 'gray',
    'CANCELLED': 'red',
    'POSTPONED': 'yellow'
  }
  return colorMap[status] || 'gray'
}

// 获取参与者角色显示文本
export const getParticipantRoleText = (role: ParticipantRole): string => {
  const roleMap = {
    'ORGANIZER': '组织者',
    'MODERATOR': '主持人',
    'PRESENTER': '演讲者',
    'PARTICIPANT': '参与者',
    'OBSERVER': '观察者'
  }
  return roleMap[role] || role
}

// 获取录制状态显示文本
export const getRecordingStatusText = (status: RecordingStatus): string => {
  const statusMap = {
    'RECORDING': '录制中',
    'PROCESSING': '处理中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'DELETED': '已删除'
  }
  return statusMap[status] || status
}

// 计算会议时长
export const calculateMeetingDuration = (startTime: string, endTime: string): number => {
  const start = new Date(startTime)
  const end = new Date(endTime)
  return Math.round((end.getTime() - start.getTime()) / (1000 * 60)) // 返回分钟数
}

// 检查会议是否即将开始
export const isMeetingStartingSoon = (startTime: string, thresholdMinutes: number = 15): boolean => {
  const now = new Date()
  const meetingStart = new Date(startTime)
  const diffMinutes = (meetingStart.getTime() - now.getTime()) / (1000 * 60)
  return diffMinutes > 0 && diffMinutes <= thresholdMinutes
}

// 检查会议是否已过期
export const isMeetingExpired = (endTime: string): boolean => {
  const now = new Date()
  const meetingEnd = new Date(endTime)
  return now > meetingEnd
}

// 生成会议链接
export const generateMeetingLink = (meetingCode: string): string => {
  const baseUrl = window.location.origin
  return `${baseUrl}/meetings/join/${meetingCode}`
}

// 复制到剪贴板
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textArea)
    return success
  }
}

// 获取时区显示文本
export const getTimezoneText = (timezone: string): string => {
  try {
    return new Intl.DateTimeFormat('zh-CN', { 
      timeZoneName: 'long',
      timeZone: timezone 
    }).formatToParts(new Date()).find(part => part.type === 'timeZoneName')?.value || timezone
  } catch {
    return timezone
  }
}

// 转换时区时间
export const convertToTimezone = (dateString: string, timezone: string): string => {
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return formatDateTime(dateString)
  }
}

// 计算会议评分颜色
export const getScoreColor = (score: number): string => {
  if (score >= 90) return 'green'
  if (score >= 80) return 'blue'
  if (score >= 70) return 'yellow'
  if (score >= 60) return 'orange'
  return 'red'
}

// 格式化百分比
export const formatPercentage = (value: number, decimals: number = 1): string => {
  return `${value.toFixed(decimals)}%`
}

// 获取会议类型图标
export const getMeetingTypeIcon = (type: MeetingType): string => {
  const iconMap = {
    'PROJECT_KICKOFF': '🚀',
    'REQUIREMENT_REVIEW': '📋',
    'DESIGN_REVIEW': '🎨',
    'CODE_REVIEW': '💻',
    'TEST_REVIEW': '🧪',
    'PROGRESS_SYNC': '📊',
    'PROBLEM_SOLVING': '🔧',
    'PROJECT_SUMMARY': '📈',
    'TRAINING': '🎓',
    'OTHER': '📝'
  }
  return iconMap[type] || '📝'
}

// 验证会议时间
export const validateMeetingTime = (startTime: string, endTime: string): {
  isValid: boolean
  error?: string
} => {
  const start = new Date(startTime)
  const end = new Date(endTime)
  const now = new Date()
  
  if (start >= end) {
    return { isValid: false, error: '开始时间必须早于结束时间' }
  }
  
  if (start < now) {
    return { isValid: false, error: '开始时间不能早于当前时间' }
  }
  
  const durationMinutes = (end.getTime() - start.getTime()) / (1000 * 60)
  if (durationMinutes < 5) {
    return { isValid: false, error: '会议时长不能少于5分钟' }
  }
  
  if (durationMinutes > 480) { // 8小时
    return { isValid: false, error: '会议时长不能超过8小时' }
  }
  
  return { isValid: true }
}

// 生成会议摘要
export const generateMeetingSummary = (
  title: string,
  startTime: string,
  endTime: string,
  participantCount: number,
  type: MeetingType
): string => {
  const typeText = getMeetingTypeText(type)
  const startText = formatDateTime(startTime)
  const duration = calculateMeetingDuration(startTime, endTime)
  const durationText = formatDuration(duration)
  
  return `${typeText}：${title}，计划于${startText}开始，预计时长${durationText}，${participantCount}人参与。`
}

// 检查会议权限
export const checkMeetingPermission = (
  userRole: ParticipantRole,
  action: 'view' | 'edit' | 'delete' | 'control' | 'record'
): boolean => {
  const permissions = {
    'ORGANIZER': ['view', 'edit', 'delete', 'control', 'record'],
    'MODERATOR': ['view', 'edit', 'control', 'record'],
    'PRESENTER': ['view', 'control'],
    'PARTICIPANT': ['view'],
    'OBSERVER': ['view']
  }
  
  return permissions[userRole]?.includes(action) || false
}

export const getSuggestedDuration = (type: MeetingType): number => {
  const durations: Record<MeetingType, number> = {
    PROJECT_KICKOFF: 90,
    REQUIREMENT_REVIEW: 60,
    DESIGN_REVIEW: 60,
    CODE_REVIEW: 45,
    TEST_REVIEW: 60,
    PROGRESS_SYNC: 30,
    PROBLEM_SOLVING: 60,
    PROJECT_SUMMARY: 60,
    TRAINING: 120,
    OTHER: 60
  }

  return durations[type] ?? 60
}

export const generateMeetingCode = (): string => {
  return Math.random().toString(36).slice(2, 10).toUpperCase()
}

export const canJoinMeeting = (startTime: string, endTime: string): boolean => {
  const now = new Date()
  const start = new Date(startTime)
  const end = new Date(endTime)
  return now >= new Date(start.getTime() - 15 * 60 * 1000) && now <= end
}
