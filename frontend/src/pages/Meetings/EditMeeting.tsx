// @ts-nocheck
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { message } from 'antd'

import { Button } from '@/components/ui/Button'
import meetingService from '@/services/meeting/meetingService'
import type { Meeting } from '@/types/meeting'
import MeetingForm from './MeetingForm'

export default function EditMeeting() {
  const navigate = useNavigate()
  const { id } = useParams()
  const meetingId = Number(id)
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!meetingId) return
    setLoading(true)
    meetingService.getMeeting(meetingId)
      .then(setMeeting)
      .finally(() => setLoading(false))
  }, [meetingId])

  const submit = async (payload: any) => {
    setSubmitting(true)
    try {
      await meetingService.updateMeeting(meetingId, payload)
      message.success('会议已更新')
      navigate(`/meetings/${meetingId}`)
    } finally {
      setSubmitting(false)
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

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Button type="button" variant="outline" size="icon" onClick={() => navigate(`/meetings/${meetingId}`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">编辑会议</h1>
        </div>
      </div>

      <MeetingForm
        initialMeeting={meeting}
        allowParticipants={false}
        submitLabel="保存修改"
        submitting={submitting}
        onSubmit={submit}
        onCancel={() => navigate(`/meetings/${meetingId}`)}
      />
    </div>
  )
}
