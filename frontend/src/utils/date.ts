/**
 * 日期格式化工具函数
 */

export const formatDate = (dateString: string | Date, format: string = 'YYYY-MM-DD HH:mm:ss'): string => {
  if (!dateString) return ''
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  
  if (isNaN(date.getTime())) return ''
  
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

export const formatRelativeTime = (dateString: string | Date): string => {
  if (!dateString) return ''
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffSeconds < 60) {
    return '刚刚'
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`
  } else if (diffHours < 24) {
    return `${diffHours}小时前`
  } else if (diffDays < 7) {
    return `${diffDays}天前`
  } else {
    return formatDate(date, 'YYYY-MM-DD')
  }
}

export const isToday = (dateString: string | Date): boolean => {
  if (!dateString) return false
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const today = new Date()
  
  return date.toDateString() === today.toDateString()
}

export const isThisWeek = (dateString: string | Date): boolean => {
  if (!dateString) return false
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const today = new Date()
  const weekStart = new Date(today.setDate(today.getDate() - today.getDay()))
  
  return date >= weekStart
}

export const isThisMonth = (dateString: string | Date): boolean => {
  if (!dateString) return false
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const today = new Date()
  
  return date.getMonth() === today.getMonth() && date.getFullYear() === today.getFullYear()
}