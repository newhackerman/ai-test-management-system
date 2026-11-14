// @ts-nocheck
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Loader2, Play, Share2, Trash2 } from 'lucide-react'
import { message } from 'antd'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Switch } from '@/components/ui/Switch'
import recordingService from '@/services/meeting/recordingService'
import type { MeetingRecording } from '@/types/meeting'

const statusBadgeClass: Record<string, string> = {
  RECORDING: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  PAUSED: 'border-amber-200 bg-amber-50 text-amber-700',
  PROCESSING: 'border-blue-200 bg-blue-50 text-blue-700',
  COMPLETED: 'border-gray-200 bg-gray-50 text-gray-700',
  FAILED: 'border-red-200 bg-red-50 text-red-700',
  DELETED: 'border-gray-200 bg-gray-50 text-gray-500',
}

const statusLabels: Record<string, string> = {
  RECORDING: '录制中',
  PAUSED: '已暂停',
  PROCESSING: '处理中',
  COMPLETED: '已完成',
  FAILED: '失败',
  DELETED: '已删除',
}

const typeLabels: Record<string, string> = {
  FULL_MEETING: '完整会议',
  SCREEN_SHARE: '屏幕共享',
  AUDIO_ONLY: '仅音频',
  HIGHLIGHTS: '精彩片段',
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '-'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`
}

const formatDateTime = (value?: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

export default function RecordingDetail() {
  const navigate = useNavigate()
  const { recordingId } = useParams()
  const id = Number(recordingId)
  const [recording, setRecording] = useState<MeetingRecording | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [password, setPassword] = useState('')
  const [shareAccessType, setShareAccessType] = useState<'PUBLIC' | 'PASSWORD' | 'PRIVATE'>('PUBLIC')
  const [sharePassword, setSharePassword] = useState('')
  const [shareUrl, setShareUrl] = useState('')
  const [sharing, setSharing] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const rec = await recordingService.getRecording(id)
      setRecording(rec)
      setName(rec.recording_name)
      setIsPublic(Boolean(rec.is_public))
      setPassword(rec.access_password || '')
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载录制详情失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  const handleSave = async () => {
    if (!name.trim()) {
      message.error('录制名称不能为空')
      return
    }
    setSaving(true)
    try {
      const updated = await recordingService.updateRecording(id, {
        recording_name: name.trim(),
        is_public: isPublic,
        access_password: password || undefined,
      })
      setRecording(updated)
      message.success('录制信息已更新')
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '更新失败')
    } finally {
      setSaving(false)
    }
  }

  const handleShare = async () => {
    setSharing(true)
    try {
      const info = await recordingService.createShareLink(id, {
        accessType: shareAccessType,
        password: sharePassword || undefined,
        allowDownload: true,
      })
      setShareUrl(info.share_url)
      message.success('分享链接已生成')
      await load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '分享失败')
    } finally {
      setSharing(false)
    }
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const url = await recordingService.downloadRecording(id)
      const a = document.createElement('a')
      a.href = url
      a.download = `${recording?.recording_name || `recording_${id}`}.${(recording?.file_format || 'MP4').toLowerCase()}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      message.success('开始下载')
      await load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '下载失败：录制文件不存在或无权限')
    } finally {
      setDownloading(false)
    }
  }

  const handleDelete = async () => {
    if (!recording) return
    if (!window.confirm(`确定要删除录制“${recording.recording_name}”吗？`)) return
    try {
      await recordingService.deleteRecording(id)
      message.success('录制已删除')
      navigate('/meetings/recordings')
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败')
    }
  }

  if (loading) {
    return (
      <div className="flex h-80 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载录制详情...
      </div>
    )
  }

  if (error || !recording) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-3 text-muted-foreground">
        <div>{error || '录制不存在或无权查看'}</div>
        <Button asChild variant="outline"><Link to="/meetings/recordings">返回录制列表</Link></Button>
      </div>
    )
  }

  const canPlay = recording.recording_status === 'COMPLETED'

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <Button type="button" variant="outline" size="icon" onClick={() => navigate('/meetings/recordings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">{recording.recording_name}</h1>
              <Badge variant="outline" className={statusBadgeClass[recording.recording_status] || ''}>
                {statusLabels[recording.recording_status] || recording.recording_status}
              </Badge>
              <Badge variant="outline">{typeLabels[recording.recording_type] || recording.recording_type}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              录制 #{recording.id} · 所属会议 <Link to={`/meetings/${recording.meeting_id}`} className="text-blue-600 hover:underline">#{recording.meeting_id}</Link>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {canPlay && (
            <Button type="button" onClick={() => navigate(`/meetings/recordings/${recording.id}/player`)}>
              <Play className="mr-2 h-4 w-4" />播放
            </Button>
          )}
          <Button type="button" variant="outline" onClick={handleDownload} disabled={downloading || !canPlay}>
            <Download className="mr-2 h-4 w-4" />下载
          </Button>
          <Button type="button" variant="outline" onClick={handleDelete} disabled={recording.recording_status === 'RECORDING'}>
            <Trash2 className="mr-2 h-4 w-4" />删除
          </Button>
        </div>
      </div>

      {recording.recording_status === 'FAILED' && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          录制失败，未生成可播放文件。无头环境下 ffmpeg 因无 X11/PulseAudio 无法采集是已知限制；本页不伪造播放内容。
        </div>
      )}
      {recording.recording_status === 'RECORDING' && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          录制进行中。请在会议室或录制列表中停止录制；停止后如文件未生成，状态会变为失败并如实展示。
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">录制信息</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
                {[
                  ['文件格式', recording.file_format],
                  ['分辨率', recording.resolution || '-'],
                  ['文件大小', formatFileSize(recording.file_size)],
                  ['时长', formatDuration(recording.duration_seconds)],
                  ['处理进度', typeof recording.processing_progress === 'number' ? `${recording.processing_progress}%` : '-'],
                  ['观看次数', String(recording.view_count ?? 0)],
                  ['下载次数', String(recording.download_count ?? 0)],
                  ['开始时间', formatDateTime(recording.start_time)],
                  ['结束时间', formatDateTime(recording.end_time)],
                  ['创建时间', formatDateTime(recording.created_at)],
                  ['创建人', `#${recording.created_by}`],
                  ['是否公开', recording.is_public ? '是' : '否'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="mt-1 font-medium text-gray-900 dark:text-gray-100">{value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 break-all text-xs text-muted-foreground">文件路径：{recording.file_path || '-'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">分享</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <div className="w-full md:w-48">
                  <Select value={shareAccessType} onValueChange={(v) => setShareAccessType(v as any)}>
                    <SelectTrigger><SelectValue placeholder="分享方式" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PUBLIC">公开链接</SelectItem>
                      <SelectItem value="PASSWORD">密码访问</SelectItem>
                      <SelectItem value="PRIVATE">私密（需密码）</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {shareAccessType !== 'PUBLIC' && (
                  <Input
                    placeholder="访问密码（必填）"
                    value={sharePassword}
                    onChange={(e) => setSharePassword(e.target.value)}
                  />
                )}
                <Button type="button" onClick={handleShare} disabled={sharing}>
                  <Share2 className="mr-2 h-4 w-4" />生成分享链接
                </Button>
              </div>
              {shareUrl && (
                <p className="break-all text-sm">分享链接：<span className="font-medium">{shareUrl}</span></p>
              )}
              <p className="text-xs text-muted-foreground">非公开分享必须设置访问密码；分享链接指向本站内录制详情页。</p>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">编辑</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="recording-name">录制名称</Label>
                <Input id="recording-name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="recording-public">公开</Label>
                <Switch id="recording-public" checked={isPublic} onCheckedChange={setIsPublic} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="recording-password">访问密码</Label>
                <Input
                  id="recording-password"
                  type="password"
                  placeholder="公开录制可留空"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <p className="text-xs text-muted-foreground">后端没有录制描述字段，暂不支持改描述。</p>
              <Button type="button" className="w-full" onClick={handleSave} disabled={saving}>
                {saving ? '保存中...' : '保存修改'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
