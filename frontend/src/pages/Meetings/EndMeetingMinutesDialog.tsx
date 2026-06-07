// @ts-nocheck
import { useEffect, useState } from 'react'
import { AlertCircle, X } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Textarea } from '@/components/ui/Textarea'
import type { Meeting } from '@/types/meeting'

const lines = (value: string) => value.split('\n').map((item) => item.trim()).filter(Boolean)

const actionItemsFromText = (value: string) =>
  lines(value).map((title, index) => ({
    id: `action-${index + 1}`,
    title,
    status: 'PENDING',
    priority: 'MEDIUM',
  }))

const decisionsFromText = (value: string) =>
  lines(value).map((title, index) => ({
    id: `decision-${index + 1}`,
    title,
    status: 'APPROVED',
  }))

export default function EndMeetingMinutesDialog({
  meeting,
  open,
  submitting,
  onCancel,
  onSubmit,
}: {
  meeting: Meeting | null
  open: boolean
  submitting?: boolean
  onCancel: () => void
  onSubmit: (payload: any) => Promise<void>
}) {
  const [form, setForm] = useState({
    minutes_title: '',
    minutes_summary: '',
    minutes_content: '',
    key_points_text: '',
    decisions_text: '',
    action_items_text: '',
  })
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !meeting) return
    setForm({
      minutes_title: `${meeting.title} - 会议纪要`,
      minutes_summary: '',
      minutes_content: '',
      key_points_text: '',
      decisions_text: '',
      action_items_text: '',
    })
    setError('')
  }, [open, meeting?.id])

  if (!open || !meeting) return null

  const update = (field: string, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    setError('')
  }

  const submit = async () => {
    const content = form.minutes_content.trim()
    if (!content) {
      setError('请填写会议纪要内容')
      return
    }

    await onSubmit({
      minutes_title: form.minutes_title.trim() || `${meeting.title} - 会议纪要`,
      minutes_summary: form.minutes_summary.trim() || undefined,
      minutes_content: content,
      key_points: lines(form.key_points_text),
      decisions: decisionsFromText(form.decisions_text),
      action_items: actionItemsFromText(form.action_items_text),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">填写会议纪要并结束会议</h2>
            <p className="text-sm text-muted-foreground">{meeting.title}</p>
          </div>
          <button type="button" className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={onCancel} disabled={submitting}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <Label htmlFor="minutes_title">纪要标题</Label>
            <Input id="minutes_title" value={form.minutes_title} onChange={(event) => update('minutes_title', event.target.value)} />
          </div>

          <div>
            <Label htmlFor="minutes_summary">会议摘要</Label>
            <Textarea id="minutes_summary" rows={2} value={form.minutes_summary} onChange={(event) => update('minutes_summary', event.target.value)} placeholder="简要说明会议结论和整体进展" />
          </div>

          <div>
            <Label htmlFor="minutes_content">会议纪要 *</Label>
            <Textarea id="minutes_content" rows={7} value={form.minutes_content} onChange={(event) => update('minutes_content', event.target.value)} placeholder="记录讨论内容、结论、问题和后续安排" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="key_points">关键要点</Label>
              <Textarea id="key_points" rows={4} value={form.key_points_text} onChange={(event) => update('key_points_text', event.target.value)} placeholder="每行一条" />
            </div>
            <div>
              <Label htmlFor="decisions">决策事项</Label>
              <Textarea id="decisions" rows={4} value={form.decisions_text} onChange={(event) => update('decisions_text', event.target.value)} placeholder="每行一条" />
            </div>
            <div>
              <Label htmlFor="action_items">行动项</Label>
              <Textarea id="action_items" rows={4} value={form.action_items_text} onChange={(event) => update('action_items_text', event.target.value)} placeholder="每行一条" />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t px-5 py-4">
          <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>取消</Button>
          <Button type="button" onClick={submit} disabled={submitting}>{submitting ? '正在结束...' : '保存纪要并结束会议'}</Button>
        </div>
      </div>
    </div>
  )
}
