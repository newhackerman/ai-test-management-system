// @ts-nocheck
import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, CalendarDays, CheckCircle2, Settings2, Users } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Textarea } from '@/components/ui/Textarea'
import ProjectService from '@/services/projectService'
import userService from '@/services/user-service'
import type { Meeting } from '@/types/meeting'

export const meetingTypeLabels: Record<string, string> = {
  PROJECT_KICKOFF: '项目启动会',
  REQUIREMENT_REVIEW: '需求评审会',
  DESIGN_REVIEW: '设计评审会',
  CODE_REVIEW: '代码评审会',
  TEST_REVIEW: '测试评审会',
  PROGRESS_SYNC: '进度同步会',
  PROBLEM_SOLVING: '问题解决会',
  PROJECT_SUMMARY: '项目总结会',
  TRAINING: '培训会议',
  OTHER: '其他会议',
}

export const meetingStatusLabels: Record<string, string> = {
  SCHEDULED: '待开始',
  IN_PROGRESS: '进行中',
  COMPLETED: '已结束',
  CANCELLED: '已取消',
  POSTPONED: '已延期',
}

const meetingTypeOptions = Object.entries(meetingTypeLabels).map(([value, label]) => ({ value, label }))

const pad = (value: number) => String(value).padStart(2, '0')
const toDateText = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
const toTimeText = (date: Date) => `${pad(date.getHours())}:${pad(date.getMinutes())}`

const nextHalfHour = () => {
  const date = new Date()
  date.setSeconds(0, 0)
  const minutes = date.getMinutes()
  date.setMinutes(minutes < 30 ? 30 : 60)
  return date
}

const parseMeetingDate = (value?: string) => {
  if (!value) return new Date()
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? new Date() : date
}

const defaultForm = () => {
  const start = nextHalfHour()
  const end = new Date(start.getTime() + 60 * 60 * 1000)
  return {
    title: '',
    description: '',
    meeting_type: 'PROGRESS_SYNC',
    date: toDateText(start),
    start_time: toTimeText(start),
    end_time: toTimeText(end),
    project_id: '',
    max_participants: 50,
    participant_ids: [],
    agenda_text: '会议目标\n当前进展\n风险与阻塞\n下一步行动',
    auto_record: false,
    waiting_room_enabled: true,
    mute_on_join: true,
    allow_screen_share: true,
    allow_chat: true,
    allow_file_share: true,
  }
}

const formFromMeeting = (meeting?: Meeting | null) => {
  if (!meeting) return defaultForm()
  const start = parseMeetingDate(meeting.scheduled_start_time)
  const end = parseMeetingDate(meeting.scheduled_end_time)
  return {
    ...defaultForm(),
    title: meeting.title || '',
    description: meeting.description || '',
    meeting_type: meeting.meeting_type || 'PROGRESS_SYNC',
    date: toDateText(start),
    start_time: toTimeText(start),
    end_time: toTimeText(end),
    project_id: meeting.project_id ? String(meeting.project_id) : '',
    max_participants: meeting.max_participants || 50,
    agenda_text: (meeting.agenda || []).map((item) => item.title || item.description).filter(Boolean).join('\n') || '会议目标\n关键议题\n行动项',
    auto_record: Boolean(meeting.meeting_settings?.auto_record || meeting.is_recording_enabled),
    waiting_room_enabled: meeting.meeting_settings?.waiting_room_enabled ?? meeting.is_waiting_room_enabled ?? true,
    mute_on_join: meeting.meeting_settings?.mute_on_join ?? true,
    allow_screen_share: meeting.meeting_settings?.allow_screen_share ?? true,
    allow_chat: meeting.meeting_settings?.allow_chat ?? true,
    allow_file_share: meeting.meeting_settings?.allow_file_share ?? true,
  }
}

const buildAgenda = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((title, index) => ({
      title,
      description: '',
      duration_minutes: 15,
      order: index + 1,
    }))

const composeDateTime = (date: string, time: string) => `${date}T${time || '00:00'}:00`

export default function MeetingForm({
  initialMeeting,
  submitting,
  submitLabel,
  allowParticipants = true,
  onSubmit,
  onCancel,
}: {
  initialMeeting?: Meeting | null
  submitting?: boolean
  submitLabel: string
  allowParticipants?: boolean
  onSubmit: (payload: any) => Promise<void>
  onCancel: () => void
}) {
  const [projects, setProjects] = useState([])
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(() => formFromMeeting(initialMeeting))
  const [error, setError] = useState('')

  useEffect(() => setForm(formFromMeeting(initialMeeting)), [initialMeeting?.id])

  useEffect(() => {
    ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' })
      .then((response) => setProjects(response.data || []))
      .catch(() => setProjects([]))

    userService.getUsers({ page: 1, size: 100, status: 'active', sort_by: 'username', sort_order: 'asc' })
      .then((response) => setUsers(response.users || []))
      .catch(() => setUsers([]))
  }, [])

  const selectedUsers = useMemo(() => new Set(form.participant_ids || []), [form.participant_ids])

  const update = (field: string, value: any) => {
    setForm((current) => ({ ...current, [field]: value }))
    setError('')
  }

  const toggleParticipant = (userId: number) => {
    setForm((current) => {
      const selected = new Set(current.participant_ids || [])
      selected.has(userId) ? selected.delete(userId) : selected.add(userId)
      return { ...current, participant_ids: Array.from(selected) }
    })
    setError('')
  }

  const submit = async (event) => {
    event.preventDefault()
    const title = form.title.trim()
    if (!title) {
      setError('请输入会议标题')
      return
    }

    const start = composeDateTime(form.date, form.start_time)
    const end = composeDateTime(form.date, form.end_time)
    if (new Date(start) >= new Date(end)) {
      setError('结束时间必须晚于开始时间')
      return
    }

    await onSubmit({
      title,
      description: form.description.trim() || undefined,
      meeting_type: form.meeting_type,
      scheduled_start_time: start,
      scheduled_end_time: end,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai',
      project_id: form.project_id ? Number(form.project_id) : undefined,
      max_participants: Number(form.max_participants) || 50,
      participant_ids: allowParticipants ? form.participant_ids : undefined,
      agenda: buildAgenda(form.agenda_text),
      is_recording_enabled: Boolean(form.auto_record),
      is_waiting_room_enabled: Boolean(form.waiting_room_enabled),
      is_password_protected: false,
      meeting_settings: {
        auto_record: Boolean(form.auto_record),
        waiting_room_enabled: Boolean(form.waiting_room_enabled),
        mute_on_join: Boolean(form.mute_on_join),
        allow_screen_share: Boolean(form.allow_screen_share),
        allow_chat: Boolean(form.allow_chat),
        allow_file_share: Boolean(form.allow_file_share),
      },
    })
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
            <CheckCircle2 className="h-4 w-4 text-blue-600" />
            基本信息
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <Label htmlFor="meeting_title">会议标题 *</Label>
              <Input id="meeting_title" value={form.title} onChange={(event) => update('title', event.target.value)} placeholder="例如：登录模块需求评审会" autoFocus />
            </div>
            <div>
              <Label htmlFor="meeting_type">会议类型</Label>
              <select id="meeting_type" value={form.meeting_type} onChange={(event) => update('meeting_type', event.target.value)} className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                {meetingTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
            <div>
              <Label htmlFor="meeting_project">关联项目</Label>
              <select id="meeting_project" value={form.project_id} onChange={(event) => update('project_id', event.target.value)} className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="">不关联项目</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.project_name}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="meeting_description">会议说明</Label>
              <Textarea id="meeting_description" value={form.description} onChange={(event) => update('description', event.target.value)} rows={3} placeholder="说明会议目标、背景、需要提前准备的材料" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
            <CalendarDays className="h-4 w-4 text-blue-600" />
            时间与议程
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="md:col-span-2">
              <Label htmlFor="meeting_date">日期</Label>
              <Input id="meeting_date" type="date" value={form.date} onChange={(event) => update('date', event.target.value)} />
            </div>
            <div>
              <Label htmlFor="meeting_start">开始</Label>
              <Input id="meeting_start" type="time" value={form.start_time} onChange={(event) => update('start_time', event.target.value)} />
            </div>
            <div>
              <Label htmlFor="meeting_end">结束</Label>
              <Input id="meeting_end" type="time" value={form.end_time} onChange={(event) => update('end_time', event.target.value)} />
            </div>
            <div className="md:col-span-4">
              <Label htmlFor="meeting_agenda">议程</Label>
              <Textarea id="meeting_agenda" value={form.agenda_text} onChange={(event) => update('agenda_text', event.target.value)} rows={5} placeholder="每行一个议程项" />
            </div>
          </div>
        </CardContent>
      </Card>

      {allowParticipants && (
        <Card>
          <CardContent className="space-y-4 p-5">
            <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
              <Users className="h-4 w-4 text-blue-600" />
              参会人员
            </div>
            <div className="grid max-h-56 grid-cols-1 gap-2 overflow-y-auto rounded-md border p-3 md:grid-cols-3">
              {users.length ? users.map((user) => (
                <label key={user.id} className="flex items-center gap-2 rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-800/50 dark:hover:bg-gray-800">
                  <input type="checkbox" checked={selectedUsers.has(user.id)} onChange={() => toggleParticipant(user.id)} />
                  <span className="truncate">{user.real_name || user.nickname || user.username}</span>
                </label>
              )) : <span className="text-sm text-gray-500 dark:text-gray-400">暂无可选用户</span>}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
            <Settings2 className="h-4 w-4 text-blue-600" />
            会议设置
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.waiting_room_enabled} onChange={(event) => update('waiting_room_enabled', event.target.checked)} />启用等候室</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.mute_on_join} onChange={(event) => update('mute_on_join', event.target.checked)} />入会静音</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.auto_record} onChange={(event) => update('auto_record', event.target.checked)} />自动录制</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.allow_screen_share} onChange={(event) => update('allow_screen_share', event.target.checked)} />允许屏幕共享</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.allow_chat} onChange={(event) => update('allow_chat', event.target.checked)} />允许聊天</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.allow_file_share} onChange={(event) => update('allow_file_share', event.target.checked)} />允许文件共享</label>
          </div>
          <div className="max-w-xs">
            <Label htmlFor="max_participants">人数上限</Label>
            <Input id="max_participants" type="number" min="2" max="1000" value={form.max_participants} onChange={(event) => update('max_participants', event.target.value)} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>取消</Button>
        <Button type="submit" disabled={submitting}>{submitting ? '保存中...' : submitLabel}</Button>
      </div>
    </form>
  )
}
