import React, { useState, useMemo } from 'react'
import { RequirementStatus, Requirement } from '@/types/requirement'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Avatar } from '@/components/ui/Avatar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { DatePicker } from '@/components/ui/DatePicker'
import { Separator } from '@/components/ui/Separator'
import { cn } from '@/lib/utils'
import { format, parseISO, isAfter, isBefore } from 'date-fns'
import { zhCN } from 'date-fns/locale'

// 状态历史记录类型
interface StatusHistoryRecord {
  id: number
  requirement_id: number
  old_status: RequirementStatus | null
  new_status: RequirementStatus
  change_reason?: string
  change_description?: string
  changed_by: number
  changed_at: string
  user?: {
    id: number
    username: string
    real_name?: string
    avatar?: string
  }
}

// 状态配置
const STATUS_CONFIG: Record<RequirementStatus, {
  label: string
  color: string
  bgColor: string
  icon: string
}> = {
  DRAFT: { label: '草稿', color: 'text-gray-600', bgColor: 'bg-gray-100', icon: '📝' },
  PENDING_REVIEW: { label: '待评审', color: 'text-yellow-600', bgColor: 'bg-yellow-100', icon: '⏳' },
  REVIEWING: { label: '评审中', color: 'text-blue-600', bgColor: 'bg-blue-100 dark:bg-blue-900/30', icon: '👥' },
  NEEDS_REVISION: { label: '需修改', color: 'text-orange-600', bgColor: 'bg-orange-100', icon: '✏️' },
  APPROVED: { label: '已批准', color: 'text-green-600', bgColor: 'bg-green-100', icon: '✅' },
  IN_DEVELOPMENT: { label: '开发中', color: 'text-purple-600', bgColor: 'bg-purple-100', icon: '⚡' },
  PAUSED: { label: '已暂停', color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-100 dark:bg-gray-800', icon: '⏸️' },
  TESTING: { label: '待测试', color: 'text-indigo-600', bgColor: 'bg-indigo-100', icon: '🧪' },
  TEST_FAILED: { label: '测试失败', color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-100 dark:bg-red-900/30', icon: '❌' },
  COMPLETED: { label: '已完成', color: 'text-emerald-600', bgColor: 'bg-emerald-100', icon: '🎉' },
  DEPLOYED: { label: '已上线', color: 'text-teal-600', bgColor: 'bg-teal-100', icon: '🚀' },
  CLOSED: { label: '已关闭', color: 'text-slate-600', bgColor: 'bg-slate-100', icon: '🔒' },
  CANCELLED: { label: '已取消', color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-100 dark:bg-red-900/30', icon: '🚫' }
}

// 时间线项组件
interface TimelineItemProps {
  record: StatusHistoryRecord
  isFirst?: boolean
  isLast?: boolean
}

const TimelineItem: React.FC<TimelineItemProps> = ({ record, isFirst, isLast }) => {
  const oldConfig = record.old_status ? STATUS_CONFIG[record.old_status] : null
  const newConfig = STATUS_CONFIG[record.new_status]
  
  return (
    <div className="relative flex gap-4 pb-6">
      {/* 时间线 */}
      <div className="flex flex-col items-center">
        <div className={cn(
          'w-3 h-3 rounded-full border-2 bg-white',
          isFirst ? 'border-green-500' : 'border-gray-300 dark:border-gray-600'
        )} />
        {!isLast && <div className="w-0.5 h-full bg-gray-200 mt-2" />}
      </div>
      
      {/* 内容 */}
      <div className="flex-1 min-w-0">
        <div className="bg-white rounded-lg border p-4 shadow-sm dark:bg-gray-800">
          {/* 头部信息 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {record.user && (
                <Avatar className="w-6 h-6">
                  <img 
                    src={record.user.avatar || `/api/placeholder/32/32`} 
                    alt={record.user.real_name || record.user.username}
                  />
                </Avatar>
              )}
              <span className="text-sm font-medium">
                {record.user?.real_name || record.user?.username || '系统'}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              {format(parseISO(record.changed_at), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
            </span>
          </div>
          
          {/* 状态变更 */}
          <div className="flex items-center gap-3 mb-3">
            {oldConfig ? (
              <>
                <Badge className={cn('text-xs', oldConfig.bgColor, oldConfig.color)}>
                  {oldConfig.icon} {oldConfig.label}
                </Badge>
                <span className="text-muted-foreground">→</span>
              </>
            ) : (
              <span className="text-xs text-muted-foreground">创建需求</span>
            )}
            <Badge className={cn('text-xs', newConfig.bgColor, newConfig.color)}>
              {newConfig.icon} {newConfig.label}
            </Badge>
          </div>
          
          {/* 变更原因 */}
          {record.change_reason && (
            <div className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground">变更原因:</div>
              <div className="text-sm bg-muted/50 p-2 rounded">
                {record.change_reason}
              </div>
            </div>
          )}
          
          {/* 变更描述 */}
          {record.change_description && (
            <div className="space-y-1 mt-2">
              <div className="text-xs font-medium text-muted-foreground">详细描述:</div>
              <div className="text-sm text-muted-foreground">
                {record.change_description}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 状态统计图表组件
interface StatusStatisticsProps {
  history: StatusHistoryRecord[]
}

const StatusStatistics: React.FC<StatusStatisticsProps> = ({ history }) => {
  // 计算状态停留时间
  const statusDurations = useMemo(() => {
    const durations: Record<RequirementStatus, number> = {} as any
    
    for (let i = 0; i < history.length; i++) {
      const current = history[i]
      const next = history[i + 1]
      
      const startTime = parseISO(current.changed_at)
      const endTime = next ? parseISO(next.changed_at) : new Date()
      const duration = endTime.getTime() - startTime.getTime()
      
      durations[current.new_status] = (durations[current.new_status] || 0) + duration
    }
    
    return durations
  }, [history])

  // 转换为天数并排序
  const sortedDurations = Object.entries(statusDurations)
    .map(([status, duration]) => ({
      status: status as RequirementStatus,
      days: Math.ceil(duration / (1000 * 60 * 60 * 24)),
      config: STATUS_CONFIG[status as RequirementStatus]
    }))
    .sort((a, b) => b.days - a.days)

  const maxDays = Math.max(...sortedDurations.map(item => item.days))

  return (
    <div className="space-y-4">
      <h4 className="font-medium">状态停留时间统计</h4>
      <div className="space-y-3">
        {sortedDurations.map(({ status, days, config }) => (
          <div key={status} className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge className={cn('text-xs', config.bgColor, config.color)}>
                {config.icon} {config.label}
              </Badge>
              <span className="text-sm font-medium">{days} 天</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${(days / maxDays) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      
      {sortedDurations.length === 0 && (
        <div className="text-center text-muted-foreground py-8">
          <p>暂无统计数据</p>
        </div>
      )}
    </div>
  )
}

interface StatusHistoryViewerProps {
  requirement: Requirement
  history?: StatusHistoryRecord[]
  loading?: boolean
  onRefresh?: () => void
  className?: string
}

export const StatusHistoryViewer: React.FC<StatusHistoryViewerProps> = ({
  requirement,
  history = [],
  loading = false,
  onRefresh,
  className
}) => {
  const [filterStatus, setFilterStatus] = useState<RequirementStatus | 'all'>('all')
  const [filterUser, setFilterUser] = useState<string>('all')
  const [dateRange, setDateRange] = useState<{ start?: Date; end?: Date }>({})

  // 获取唯一用户列表
  const uniqueUsers = useMemo(() => {
    const users = history
      .filter(record => record.user)
      .map(record => record.user!)
    
    const uniqueUsersMap = new Map()
    users.forEach(user => {
      uniqueUsersMap.set(user.id, user)
    })
    
    return Array.from(uniqueUsersMap.values())
  }, [history])

  // 过滤历史记录
  const filteredHistory = useMemo(() => {
    return history.filter(record => {
      // 状态过滤
      if (filterStatus !== 'all' && record.new_status !== filterStatus) {
        return false
      }
      
      // 用户过滤
      if (filterUser !== 'all' && record.user?.id.toString() !== filterUser) {
        return false
      }
      
      // 日期过滤
      const recordDate = parseISO(record.changed_at)
      if (dateRange.start && isBefore(recordDate, dateRange.start)) {
        return false
      }
      if (dateRange.end && isAfter(recordDate, dateRange.end)) {
        return false
      }
      
      return true
    })
  }, [history, filterStatus, filterUser, dateRange])

  // 按时间倒序排列
  const sortedHistory = [...filteredHistory].sort((a, b) => 
    new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime()
  )

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <span>状态历史</span>
            <Badge variant="outline" className="text-xs">
              {requirement.requirement_code}
            </Badge>
          </CardTitle>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
              {loading ? '刷新中...' : '刷新'}
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="timeline" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="timeline">时间线</TabsTrigger>
            <TabsTrigger value="statistics">统计分析</TabsTrigger>
          </TabsList>
          
          <TabsContent value="timeline" className="space-y-4">
            {/* 过滤器 */}
            <div className="flex flex-wrap gap-3 p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">状态:</span>
                <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    {Object.entries(STATUS_CONFIG).map(([status, config]) => (
                      <SelectItem key={status} value={status}>
                        {config.icon} {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">操作人:</span>
                <Select value={filterUser} onValueChange={setFilterUser}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    {uniqueUsers.map(user => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.real_name || user.username}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">开始日期:</span>
                <DatePicker
                  selected={dateRange.start}
                  onSelect={(date) => setDateRange(prev => ({ ...prev, start: date }))}
                  placeholder="选择开始日期"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">结束日期:</span>
                <DatePicker
                  selected={dateRange.end}
                  onSelect={(date) => setDateRange(prev => ({ ...prev, end: date }))}
                  placeholder="选择结束日期"
                />
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFilterStatus('all')
                  setFilterUser('all')
                  setDateRange({})
                }}
              >
                清空过滤
              </Button>
            </div>
            
            {/* 时间线 */}
            <div className="space-y-0">
              {sortedHistory.length > 0 ? (
                sortedHistory.map((record, index) => (
                  <TimelineItem
                    key={record.id}
                    record={record}
                    isFirst={index === 0}
                    isLast={index === sortedHistory.length - 1}
                  />
                ))
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <p className="text-lg mb-2">📋</p>
                  <p>暂无状态变更记录</p>
                  {(filterStatus !== 'all' || filterUser !== 'all' || dateRange.start || dateRange.end) && (
                    <p className="text-sm mt-2">尝试调整过滤条件查看更多记录</p>
                  )}
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="statistics" className="space-y-4">
            <StatusStatistics history={history} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default StatusHistoryViewer