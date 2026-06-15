// @ts-nocheck
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Clock, Edit, Loader2, Play, Square, Trash2, Users } from 'lucide-react'
import { message } from 'antd'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import meetingService from '@/services/meeting/meetingService'
import type { Meeting } from '@/types/meeting'
import EndMeetingMinutesDialog from './EndMeetingMinutesDialog'
import { meetingStatusLabels, meetingTypeLabels } from './MeetingForm'

const statusBadgeClass: Record<string, string> = {
  SCHEDULED: 'border-blue-200 bg-blue-50 text-blue-700',
  IN_PROGRESS: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  COMPLETED: 'border-gray-200 bg-gray-50 text-gray-700',
  CANCELLED: 'border-red-200 bg-red-50 text-red-700',
  POSTPONED: 'border-amber-200 bg-amber-50 text-amber-700',
}

const formatDateTime = (value?: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

const settingLabel: Record<string, string> = {
  auto_record: '自动录制',
  waiting_room_enabled: '等候室',
  mute_on_join: '入会静音',
  allow_screen_share: '屏幕共享',
  allow_chat: '聊天',
  allow_file_share: '文件共享',
}

export default function MeetingDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const meetingId = Number(id)
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [loading, setLoading] = useState(true)
  const [operating, setOperating] = useState('')
  const [minutesOpen, setMinutesOpen] = useState(false)
  const [minutesSubmitting, setMinutesSubmitting] = useState(false)

  const loadMeeting = async () => {
    setLoading(true)
    try {
      setMeeting(await meetingService.getMeeting(meetingId))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (meetingId) loadMeeting()
  }, [meetingId])

  const operate = async (action: 'start' | 'delete') => {
    if (!meeting) return
    if (action === 'delete' && !window.confirm(`确定要取消会议“${meeting.title}”吗？`)) return
    setOperating(action)
    try {
      if (action === 'start') {
        await meetingService.startMeeting(meeting.id)
        message.success('会议已开始')
      }
      if (action === 'delete') {
        await meetingService.deleteMeeting(meeting.id)
        message.success('会议已取消')
      }
      await loadMeeting()
    } finally {
      setOperating('')
    }
  }

  const submitMinutesAndEnd = async (payload: any) => {
    if (!meeting) return
    setOperating('end')
    setMinutesSubmitting(true)
    try {
      await meetingService.endMeeting(meeting.id, payload)
      message.success('会议纪要已保存，会议已结束')
      setMinutesOpen(false)
      await loadMeeting()
    } finally {
      setMinutesSubmitting(false)
      setOperating('')
    }
  }

  if (loading) {
    return (
      <div className="flex h-80 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        正在加载会议...
      </div>
    )
  }

  if (!meeting) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-3 text-muted-foreground">
        <div>会议不存在或无权查看</div>
        <Button asChild variant="outline"><Link to="/meetings">返回会议列表</Link></Button>
      </div>
    )
  }

  const agenda = Array.isArray(meeting.agenda) ? meeting.agenda : []
  const settings = meeting.meeting_settings || {}

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <Button type="button" variant="outline" size="icon" onClick={() => navigate('/meetings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">{meeting.title}</h1>
              <Badge variant="outline" className={statusBadgeClass[meeting.status] || ''}>{meetingStatusLabels[meeting.status] || meeting.status}</Badge>
              <Badge variant="outline">{meetingTypeLabels[meeting.meeting_type] || meeting.meeting_type}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">会议号：{meeting.meeting_code}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {(meeting.status === 'SCHEDULED' || meeting.status === 'POSTPONED') && (
            <Button type="button" onClick={() => operate('start')} disabled={Boolean(operating)}>
              <Play className="mr-2 h-4 w-4" />
              开始会议
            </Button>
          )}
          {meeting.status === 'IN_PROGRESS' && (
            <Button type="button" onClick={() => setMinutesOpen(true)} disabled={Boolean(operating)}>
              <Square className="mr-2 h-4 w-4" />
              结束会议
            </Button>
          )}
          {meeting.status !== 'COMPLETED' && meeting.status !== 'CANCELLED' && (
            <>
              <Button asChild variant="outline">
                <Link to={`/meetings/${meeting.id}/edit`}><Edit className="mr-2 h-4 w-4" />编辑</Link>
              </Button>
              <Button type="button" variant="outline" onClick={() => operate('delete')} disabled={Boolean(operating) || meeting.status === 'IN_PROGRESS'}>
                <Trash2 className="mr-2 h-4 w-4" />
                取消会议
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">会议说明</CardTitle></CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700 dark:text-gray-300">{meeting.description || '暂无说明'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">会议议程</CardTitle></CardHeader>
            <CardContent>
              {agenda.length ? (
                <ol className="space-y-3">
                  {agenda.map((item, index) => (
                    <li key={`${item.title}-${index}`} className="flex gap-3 rounded-md border p-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700">{index + 1}</span>
                      <div className="min-w-0">
                        <div className="font-medium text-gray-900 dark:text-gray-100">{item.title || item.description}</div>
                        <div className="text-sm text-muted-foreground">预计 {item.duration_minutes || 15} 分钟{item.presenter ? `，主讲：${item.presenter}` : ''}</div>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="text-sm text-muted-foreground">暂无议程</div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">会议信息</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-start gap-3">
                <Clock className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="text-muted-foreground">计划时间</div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{formatDateTime(meeting.scheduled_start_time)}</div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{formatDateTime(meeting.scheduled_end_time)}</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Users className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="text-muted-foreground">参会人数</div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{meeting.participant_count ?? 0}/{meeting.max_participants ?? '-'}</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CalendarDays className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="text-muted-foreground">关联项目</div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{meeting.project_id ? `项目 #${meeting.project_id}` : '未关联项目'}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">会议设置</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(settingLabel).map(([key, label]) => (
                <div key={key} className="rounded-md border px-3 py-2">
                  <div className="text-muted-foreground">{label}</div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{settings[key] ? '已开启' : '已关闭'}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
      <EndMeetingMinutesDialog
        meeting={meeting}
        open={minutesOpen}
        submitting={minutesSubmitting}
        onCancel={() => {
          if (!minutesSubmitting) setMinutesOpen(false)
        }}
        onSubmit={submitMinutesAndEnd}
      />
    </div>
  )
}
