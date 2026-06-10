// @ts-nocheck
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CalendarDays, Clock, Edit, Eye, Loader2, Play, Plus, RefreshCw, Search, Square, Trash2, Users } from 'lucide-react'
import { message } from 'antd'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import meetingService from '@/services/meeting/meetingService'
import type { Meeting } from '@/types/meeting'
import EndMeetingMinutesDialog from './EndMeetingMinutesDialog'
import { meetingStatusLabels, meetingTypeLabels } from './MeetingForm'

const pad = (value: number) => String(value).padStart(2, '0')
const toDateText = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
const toDateTimeStart = (date: Date) => `${toDateText(date)}T00:00:00`
const toDateTimeEnd = (date: Date) => `${toDateText(date)}T23:59:59`

const statusBadgeClass: Record<string, string> = {
  SCHEDULED: 'border-blue-200 bg-blue-50 text-blue-700',
  IN_PROGRESS: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  COMPLETED: 'border-gray-200 bg-gray-50 text-gray-700',
  CANCELLED: 'border-red-200 bg-red-50 text-red-700',
  POSTPONED: 'border-amber-200 bg-amber-50 text-amber-700',
}

const quickFilters = [
  { key: 'today', label: '今日会议' },
  { key: 'upcoming', label: '待开始' },
  { key: 'running', label: '进行中' },
  { key: 'all', label: '全部会议' },
]

const formatDateTime = (value?: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const formatTimeRange = (meeting: Meeting) => `${formatDateTime(meeting.scheduled_start_time)} - ${formatDateTime(meeting.scheduled_end_time).slice(-5)}`

const getAgendaPreview = (meeting: Meeting) => {
  const agenda = Array.isArray(meeting.agenda) ? meeting.agenda : []
  return agenda.map((item) => item.title || item.description).filter(Boolean).slice(0, 3).join('、')
}

export default function MeetingList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialDate = searchParams.get('date') === 'today' ? 'today' : 'all'
  const [quickFilter, setQuickFilter] = useState(initialDate)
  const [status, setStatus] = useState('')
  const [keyword, setKeyword] = useState('')
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [operatingId, setOperatingId] = useState<number | null>(null)
  const [endingMeeting, setEndingMeeting] = useState<Meeting | null>(null)
  const [minutesSubmitting, setMinutesSubmitting] = useState(false)

  const query = useMemo(() => {
    const params: any = {
      page: 1,
      page_size: 50,
      sort_by: 'scheduled_start_time',
      sort_order: quickFilter === 'all' ? 'desc' : 'asc',
      keyword: keyword.trim() || undefined,
      status: status || undefined,
    }
    const today = new Date()

    if (quickFilter === 'today') {
      params.start_date = toDateTimeStart(today)
      params.end_date = toDateTimeEnd(today)
      params.sort_order = 'asc'
    }
    if (quickFilter === 'upcoming') {
      params.status = 'SCHEDULED'
      params.sort_order = 'asc'
    }
    if (quickFilter === 'running') {
      params.status = 'IN_PROGRESS'
      params.sort_order = 'asc'
    }
    return params
  }, [keyword, quickFilter, status])

  const loadMeetings = async () => {
    setLoading(true)
    try {
      const response = await meetingService.getMeetings(query)
      setMeetings(response.meetings || [])
      setTotal(response.total || 0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMeetings()
  }, [query])

  const changeQuickFilter = (key: string) => {
    setQuickFilter(key)
    const next = new URLSearchParams(searchParams)
    if (key === 'today') next.set('date', 'today')
    else next.delete('date')
    setSearchParams(next, { replace: true })
  }

  const runOperation = async (meeting: Meeting, action: 'start' | 'delete') => {
    if (action === 'delete' && !window.confirm(`确定要取消会议“${meeting.title}”吗？`)) return
    setOperatingId(meeting.id)
    try {
      if (action === 'start') {
        await meetingService.startMeeting(meeting.id)
        message.success('会议已开始')
      }
      if (action === 'delete') {
        await meetingService.deleteMeeting(meeting.id)
        message.success('会议已取消')
      }
      await loadMeetings()
    } finally {
      setOperatingId(null)
    }
  }

  const submitMinutesAndEnd = async (payload: any) => {
    if (!endingMeeting) return
    setOperatingId(endingMeeting.id)
    setMinutesSubmitting(true)
    try {
      await meetingService.endMeeting(endingMeeting.id, payload)
      message.success('会议纪要已保存，会议已结束')
      setEndingMeeting(null)
      await loadMeetings()
    } finally {
      setMinutesSubmitting(false)
      setOperatingId(null)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">会议管理</h1>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={loadMeetings} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button asChild>
            <Link to="/meetings/create"><Plus className="mr-2 h-4 w-4" />新建会议</Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-wrap gap-2">
            {quickFilters.map((item) => (
              <Button
                key={item.key}
                type="button"
                variant={quickFilter === item.key ? 'default' : 'outline'}
                size="sm"
                onClick={() => changeQuickFilter(item.key)}
              >
                {item.label}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} className="pl-9" placeholder="搜索会议标题或说明" />
            </div>
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              <option value="">全部状态</option>
              <option value="SCHEDULED">待开始</option>
              <option value="IN_PROGRESS">进行中</option>
              <option value="COMPLETED">已结束</option>
              <option value="POSTPONED">已延期</option>
              <option value="CANCELLED">已取消</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg">会议列表</CardTitle>
          <span className="text-sm text-muted-foreground">共 {total} 条</span>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="flex h-52 items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在加载会议...
            </div>
          ) : meetings.length ? meetings.map((meeting) => {
            const busy = operatingId === meeting.id
            const agendaPreview = getAgendaPreview(meeting)
            return (
              <div key={meeting.id} className="rounded-lg border bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate text-base font-semibold text-gray-900">{meeting.title}</h2>
                      <Badge variant="outline" className={statusBadgeClass[meeting.status] || ''}>{meetingStatusLabels[meeting.status] || meeting.status}</Badge>
                      <Badge variant="outline">{meetingTypeLabels[meeting.meeting_type] || meeting.meeting_type}</Badge>
                    </div>
                    <div className="grid grid-cols-1 gap-2 text-sm text-muted-foreground md:grid-cols-3">
                      <span className="flex items-center gap-2"><Clock className="h-4 w-4" />{formatTimeRange(meeting)}</span>
                      <span className="flex items-center gap-2"><Users className="h-4 w-4" />{meeting.participant_count ?? 0}/{meeting.max_participants ?? '-'}</span>
                      <span className="flex items-center gap-2"><CalendarDays className="h-4 w-4" />会议号 {meeting.meeting_code}</span>
                    </div>
                    {meeting.description && <p className="line-clamp-2 text-sm text-gray-600">{meeting.description}</p>}
                    {agendaPreview && <p className="text-sm text-gray-600">议程：{agendaPreview}</p>}
                  </div>
                  <div className="flex flex-wrap gap-2 lg:justify-end">
                    <Button type="button" variant="outline" size="sm" onClick={() => navigate(`/meetings/${meeting.id}`)}>
                      <Eye className="mr-1 h-4 w-4" />查看
                    </Button>
                    {meeting.status === 'SCHEDULED' || meeting.status === 'POSTPONED' ? (
                      <Button type="button" size="sm" onClick={() => runOperation(meeting, 'start')} disabled={busy}>
                        <Play className="mr-1 h-4 w-4" />开始
                      </Button>
                    ) : null}
                    {meeting.status === 'IN_PROGRESS' ? (
                      <Button type="button" size="sm" onClick={() => setEndingMeeting(meeting)} disabled={busy}>
                        <Square className="mr-1 h-4 w-4" />结束
                      </Button>
                    ) : null}
                    {meeting.status !== 'COMPLETED' && meeting.status !== 'CANCELLED' ? (
                      <>
                        <Button type="button" variant="outline" size="sm" onClick={() => navigate(`/meetings/${meeting.id}/edit`)}>
                          <Edit className="mr-1 h-4 w-4" />编辑
                        </Button>
                        <Button type="button" variant="outline" size="sm" onClick={() => runOperation(meeting, 'delete')} disabled={busy || meeting.status === 'IN_PROGRESS'}>
                          <Trash2 className="mr-1 h-4 w-4" />取消
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>
            )
          }) : (
            <div className="flex h-56 flex-col items-center justify-center gap-3 text-muted-foreground">
              <CalendarDays className="h-10 w-10" />
              <div>暂无会议</div>
              <Button asChild size="sm"><Link to="/meetings/create">新建会议</Link></Button>
            </div>
          )}
        </CardContent>
      </Card>
      <EndMeetingMinutesDialog
        meeting={endingMeeting}
        open={Boolean(endingMeeting)}
        submitting={minutesSubmitting}
        onCancel={() => {
          if (!minutesSubmitting) setEndingMeeting(null)
        }}
        onSubmit={submitMinutesAndEnd}
      />
    </div>
  )
}
