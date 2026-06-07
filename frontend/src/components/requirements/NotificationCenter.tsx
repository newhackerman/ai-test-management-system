import React, { useState, useEffect } from 'react'
import { 
  Bell, 
  BellRing, 
  Check, 
  X, 
  Eye, 
  MessageSquare, 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  User, 
  Settings,
  Filter,
  MoreHorizontal,
  Trash2,
  Archive
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Switch } from '@/components/ui/Switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/DropdownMenu'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Separator } from '@/components/ui/Separator'
import { Label } from '@/components/ui/Label'
import { Avatar } from '@/components/ui/Avatar'

// 通知类型定义
export type NotificationType = 
  | 'requirement_created' 
  | 'requirement_updated' 
  | 'requirement_status_changed'
  | 'review_requested'
  | 'review_completed'
  | 'comment_added'
  | 'mention'
  | 'deadline_reminder'
  | 'approval_needed'
  | 'system_announcement'

export type NotificationPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Notification {
  id: number
  type: NotificationType
  priority: NotificationPriority
  title: string
  message: string
  is_read: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
  related_id?: number // 相关的需求、评审等ID
  related_type?: 'requirement' | 'review' | 'comment'
  sender?: {
    id: number
    username: string
    real_name?: string
    avatar?: string
  }
  actions?: Array<{
    type: 'view' | 'approve' | 'reject' | 'reply'
    label: string
    url?: string
  }>
}

export interface NotificationSettings {
  email_enabled: boolean
  push_enabled: boolean
  requirement_updates: boolean
  review_requests: boolean
  comments_and_mentions: boolean
  deadline_reminders: boolean
  system_announcements: boolean
  quiet_hours_enabled: boolean
  quiet_hours_start: string
  quiet_hours_end: string
}

interface NotificationCenterProps {
  currentUserId: number
  onNotificationClick?: (notification: Notification) => void
  onNotificationAction?: (notificationId: number, action: string) => void
  onSettingsUpdate?: (settings: NotificationSettings) => void
  className?: string
}

// Mock data
const mockNotifications: Notification[] = [
  {
    id: 1,
    type: 'review_requested',
    priority: 'high',
    title: '需求评审请求',
    message: '张产品 请求你评审需求 "用户登录功能"',
    is_read: false,
    is_archived: false,
    created_at: '2024-01-15T09:00:00Z',
    updated_at: '2024-01-15T09:00:00Z',
    related_id: 1,
    related_type: 'requirement',
    sender: {
      id: 1,
      username: 'product_manager',
      real_name: '张产品',
      avatar: '/avatars/pm.jpg'
    },
    actions: [
      { type: 'view', label: '查看需求', url: '/requirements/1' },
      { type: 'approve', label: '开始评审' }
    ]
  },
  {
    id: 2,
    type: 'comment_added',
    priority: 'medium',
    title: '新评论',
    message: '李安全 在需求 "用户登录功能" 中添加了评论',
    is_read: false,
    is_archived: false,
    created_at: '2024-01-15T08:30:00Z',
    updated_at: '2024-01-15T08:30:00Z',
    related_id: 1,
    related_type: 'comment',
    sender: {
      id: 2,
      username: 'security_expert',
      real_name: '李安全'
    },
    actions: [
      { type: 'view', label: '查看评论', url: '/requirements/1#comments' },
      { type: 'reply', label: '回复' }
    ]
  },
  {
    id: 3,
    type: 'requirement_status_changed',
    priority: 'medium',
    title: '需求状态变更',
    message: '需求 "用户登录功能" 状态已更新为 "评审中"',
    is_read: true,
    is_archived: false,
    created_at: '2024-01-15T08:00:00Z',
    updated_at: '2024-01-15T08:00:00Z',
    related_id: 1,
    related_type: 'requirement',
    actions: [
      { type: 'view', label: '查看需求', url: '/requirements/1' }
    ]
  },
  {
    id: 4,
    type: 'mention',
    priority: 'high',
    title: '有人@了你',
    message: '王技术 在讨论中提到了你',
    is_read: false,
    is_archived: false,
    created_at: '2024-01-15T07:45:00Z',
    updated_at: '2024-01-15T07:45:00Z',
    related_id: 1,
    related_type: 'comment',
    sender: {
      id: 3,
      username: 'tech_lead',
      real_name: '王技术'
    },
    actions: [
      { type: 'view', label: '查看讨论', url: '/requirements/1#discussion' },
      { type: 'reply', label: '回复' }
    ]
  },
  {
    id: 5,
    type: 'deadline_reminder',
    priority: 'urgent',
    title: '截止日期提醒',
    message: '需求 "用户登录功能" 将在明天到期，请及时处理',
    is_read: false,
    is_archived: false,
    created_at: '2024-01-15T07:00:00Z',
    updated_at: '2024-01-15T07:00:00Z',
    related_id: 1,
    related_type: 'requirement',
    actions: [
      { type: 'view', label: '查看需求', url: '/requirements/1' }
    ]
  }
]

const mockSettings: NotificationSettings = {
  email_enabled: true,
  push_enabled: true,
  requirement_updates: true,
  review_requests: true,
  comments_and_mentions: true,
  deadline_reminders: true,
  system_announcements: false,
  quiet_hours_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00'
}

const NotificationIcon: React.FC<{ type: NotificationType; className?: string }> = ({ type, className }) => {
  const iconMap = {
    requirement_created: FileText,
    requirement_updated: FileText,
    requirement_status_changed: CheckCircle,
    review_requested: Eye,
    review_completed: CheckCircle,
    comment_added: MessageSquare,
    mention: User,
    deadline_reminder: Clock,
    approval_needed: AlertTriangle,
    system_announcement: Bell
  }
  
  const Icon = iconMap[type] || Bell
  return <Icon className={className} />
}

const PriorityBadge: React.FC<{ priority: NotificationPriority }> = ({ priority }) => {
  const variants = {
    low: 'secondary',
    medium: 'outline',
    high: 'default',
    urgent: 'destructive'
  } as const
  
  const labels = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
  }
  
  return (
    <Badge variant={variants[priority]} className="text-xs">
      {labels[priority]}
    </Badge>
  )
}

const NotificationItem: React.FC<{
  notification: Notification
  onRead: (id: number) => void
  onArchive: (id: number) => void
  onDelete: (id: number) => void
  onClick: (notification: Notification) => void
  onAction: (notificationId: number, action: string) => void
}> = ({ notification, onRead, onArchive, onDelete, onClick, onAction }) => {
  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
    
    if (diffInMinutes < 1) return '刚刚'
    if (diffInMinutes < 60) return `${diffInMinutes}分钟前`
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}小时前`
    return date.toLocaleDateString('zh-CN')
  }

  return (
    <Card 
      className={`p-4 cursor-pointer transition-colors hover:bg-muted/50 ${
        !notification.is_read ? 'border-l-4 border-l-primary bg-primary/5' : ''
      }`}
      onClick={() => onClick(notification)}
    >
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          {notification.sender?.avatar ? (
            <Avatar className="w-8 h-8">
              <img src={notification.sender.avatar} alt={notification.sender.real_name} />
            </Avatar>
          ) : (
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
              <NotificationIcon type={notification.type} className="w-4 h-4" />
            </div>
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-medium truncate">
                {notification.title}
              </h4>
              <PriorityBadge priority={notification.priority} />
              {!notification.is_read && (
                <div className="w-2 h-2 bg-primary rounded-full" />
              )}
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-xs text-muted-foreground">
                {formatTime(notification.created_at)}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                    <MoreHorizontal className="w-3 h-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {!notification.is_read && (
                    <DropdownMenuItem onClick={(e) => {
                      e.stopPropagation()
                      onRead(notification.id)
                    }}>
                      <Check className="w-4 h-4 mr-2" />
                      标记为已读
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation()
                    onArchive(notification.id)
                  }}>
                    <Archive className="w-4 h-4 mr-2" />
                    归档
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(notification.id)
                    }}
                    className="text-destructive"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    删除
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
            {notification.message}
          </p>
          
          {notification.actions && notification.actions.length > 0 && (
            <div className="flex items-center space-x-2">
              {notification.actions.map((action, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    onAction(notification.id, action.type)
                  }}
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

const NotificationSettings: React.FC<{
  settings: NotificationSettings
  onUpdate: (settings: NotificationSettings) => void
}> = ({ settings, onUpdate }) => {
  const handleSettingChange = (key: keyof NotificationSettings, value: any) => {
    onUpdate({ ...settings, [key]: value })
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">通知设置</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">邮件通知</Label>
              <p className="text-xs text-muted-foreground">通过邮件接收通知</p>
            </div>
            <Switch
              checked={settings.email_enabled}
              onCheckedChange={(checked) => handleSettingChange('email_enabled', checked)}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">推送通知</Label>
              <p className="text-xs text-muted-foreground">浏览器推送通知</p>
            </div>
            <Switch
              checked={settings.push_enabled}
              onCheckedChange={(checked) => handleSettingChange('push_enabled', checked)}
            />
          </div>
          
          <Separator />
          
          <div className="space-y-3">
            <h4 className="text-sm font-medium">通知类型</h4>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">需求更新</Label>
              <Switch
                checked={settings.requirement_updates}
                onCheckedChange={(checked) => handleSettingChange('requirement_updates', checked)}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">评审请求</Label>
              <Switch
                checked={settings.review_requests}
                onCheckedChange={(checked) => handleSettingChange('review_requests', checked)}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">评论和@提及</Label>
              <Switch
                checked={settings.comments_and_mentions}
                onCheckedChange={(checked) => handleSettingChange('comments_and_mentions', checked)}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">截止日期提醒</Label>
              <Switch
                checked={settings.deadline_reminders}
                onCheckedChange={(checked) => handleSettingChange('deadline_reminders', checked)}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">系统公告</Label>
              <Switch
                checked={settings.system_announcements}
                onCheckedChange={(checked) => handleSettingChange('system_announcements', checked)}
              />
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm font-medium">免打扰时间</Label>
                <p className="text-xs text-muted-foreground">在指定时间段内不接收通知</p>
              </div>
              <Switch
                checked={settings.quiet_hours_enabled}
                onCheckedChange={(checked) => handleSettingChange('quiet_hours_enabled', checked)}
              />
            </div>
            
            {settings.quiet_hours_enabled && (
              <div className="flex items-center space-x-4 pl-4">
                <div className="flex items-center space-x-2">
                  <Label className="text-xs">开始时间</Label>
                  <Select
                    value={settings.quiet_hours_start}
                    onValueChange={(value) => handleSettingChange('quiet_hours_start', value)}
                  >
                    <SelectTrigger className="w-20 h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 24 }, (_, i) => {
                        const hour = i.toString().padStart(2, '0')
                        return (
                          <SelectItem key={hour} value={`${hour}:00`}>
                            {hour}:00
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Label className="text-xs">结束时间</Label>
                  <Select
                    value={settings.quiet_hours_end}
                    onValueChange={(value) => handleSettingChange('quiet_hours_end', value)}
                  >
                    <SelectTrigger className="w-20 h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 24 }, (_, i) => {
                        const hour = i.toString().padStart(2, '0')
                        return (
                          <SelectItem key={hour} value={`${hour}:00`}>
                            {hour}:00
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  currentUserId,
  onNotificationClick,
  onNotificationAction,
  onSettingsUpdate,
  className
}) => {
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications)
  const [settings, setSettings] = useState<NotificationSettings>(mockSettings)
  const [filter, setFilter] = useState<'all' | 'unread' | 'archived'>('all')
  const [typeFilter, setTypeFilter] = useState<NotificationType | 'all'>('all')

  const filteredNotifications = notifications.filter(notification => {
    if (filter === 'unread' && notification.is_read) return false
    if (filter === 'archived' && !notification.is_archived) return false
    if (filter !== 'archived' && notification.is_archived) return false
    if (typeFilter !== 'all' && notification.type !== typeFilter) return false
    return true
  })

  const unreadCount = notifications.filter(n => !n.is_read && !n.is_archived).length

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      handleMarkAsRead(notification.id)
    }
    onNotificationClick?.(notification)
  }

  const handleMarkAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, is_read: true } : n
    ))
  }

  const handleArchive = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, is_archived: true } : n
    ))
  }

  const handleDelete = (id: number) => {
    setNotifications(notifications.filter(n => n.id !== id))
  }

  const handleMarkAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, is_read: true })))
  }

  const handleSettingsUpdate = (newSettings: NotificationSettings) => {
    setSettings(newSettings)
    onSettingsUpdate?.(newSettings)
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <Tabs defaultValue="notifications" className="flex-1 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -top-2 -right-2 h-5 w-5 flex items-center justify-center p-0 text-xs"
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </Badge>
              )}
            </div>
            <h3 className="font-semibold">通知中心</h3>
          </div>
          
          <TabsList className="grid w-auto grid-cols-2">
            <TabsTrigger value="notifications">通知</TabsTrigger>
            <TabsTrigger value="settings">设置</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="notifications" className="flex-1 flex flex-col m-0">
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center space-x-2">
              <Select value={filter} onValueChange={(value: any) => setFilter(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="unread">未读</SelectItem>
                  <SelectItem value="archived">已归档</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={typeFilter} onValueChange={(value: any) => setTypeFilter(value)}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有类型</SelectItem>
                  <SelectItem value="review_requested">评审请求</SelectItem>
                  <SelectItem value="comment_added">新评论</SelectItem>
                  <SelectItem value="mention">@提及</SelectItem>
                  <SelectItem value="deadline_reminder">截止提醒</SelectItem>
                  <SelectItem value="requirement_status_changed">状态变更</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {unreadCount > 0 && (
              <Button variant="outline" size="sm" onClick={handleMarkAllAsRead}>
                <Check className="w-4 h-4 mr-1" />
                全部已读
              </Button>
            )}
          </div>

          <ScrollArea className="flex-1 p-4">
            <div className="space-y-3">
              {filteredNotifications.length === 0 ? (
                <div className="text-center py-8">
                  <Bell className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-muted-foreground mb-2">
                    没有通知
                  </h3>
                  <p className="text-muted-foreground">
                    {filter === 'unread' ? '所有通知都已读完' : '暂时没有新通知'}
                  </p>
                </div>
              ) : (
                filteredNotifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={handleMarkAsRead}
                    onArchive={handleArchive}
                    onDelete={handleDelete}
                    onClick={handleNotificationClick}
                    onAction={(id, action) => onNotificationAction?.(id, action)}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="settings" className="flex-1 m-0">
          <ScrollArea className="flex-1 p-4">
            <NotificationSettings
              settings={settings}
              onUpdate={handleSettingsUpdate}
            />
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default NotificationCenter
    