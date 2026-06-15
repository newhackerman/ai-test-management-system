// @ts-nocheck
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { message } from 'antd'

import { Button } from '@/components/ui/Button'
import meetingService from '@/services/meeting/meetingService'
import MeetingForm from './MeetingForm'

export default function CreateMeeting() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  const submit = async (payload: any) => {
    setSubmitting(true)
    try {
      const meeting = await meetingService.createMeeting(payload)
      message.success('会议创建成功')
      navigate(`/meetings/${meeting.id}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button type="button" variant="outline" size="icon" onClick={() => navigate('/meetings')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
      </div>

      <MeetingForm
        submitLabel="创建会议"
        submitting={submitting}
        onSubmit={submit}
        onCancel={() => navigate('/meetings')}
      />
    </div>
  )
}
