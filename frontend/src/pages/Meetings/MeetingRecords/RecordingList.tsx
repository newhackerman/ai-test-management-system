// @ts-nocheck
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Eye, Loader2, Play, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
import { message } from 'antd'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Pagination } from '@/components/ui/Pagination'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
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
  if (bytes < 1024) return `${bytes} B`
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

export default function RecordingList() {
  const navigate = useNavigate()
  // 同一组件挂两个路由：/meetings/recordings（全局）与
  // /meetings/:id/recordings（按会议）；有 id 时只查该会议。
  const { id } = useParams()
  const meetingId = id ? Number(id) : undefined
  const [recordings, setRecordings] = useState<MeetingRecording[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [keyword, setKeyword] = useState('')
  const [keywordInput, setKeywordInput] = useState('')
  const [stats, setStats] = useState<{ total_recordings: number; active_recordings: number; completed_recordings: number; failed_recordings: number } | null>(null)
  const [operatingId, setOperatingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, pageSize: 20, status: status || undefined, type: (type || undefined) as any, searchQuery: keyword.trim() || undefined }
      const result = meetingId
        ? await recordingService.getMeetingRecordings(meetingId, params)
        : await recordingService.getAllRecordings(params)
      setRecordings(result.recordings)
      setTotal(result.total)
      setTotalPages(Math.max(result.totalPages, 1))
      try {
        setStats(await recordingService.getStatistics(meetingId))
      } catch {
        setStats(null)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载录制列表失败')
    } finally {
      setLoading(false)
    }
  }, [meetingId, page, status, type, keyword])

  useEffect(() => { load() }, [load])

  const handleDelete = async (recording: MeetingRecording) => {
    if (!window.confirm(`确定要删除录制“${recording.recording_name}”吗？删除后列表中不再显示。`)) return
    setOperatingId(recording.id)
    try {
      await recordingService.deleteRecording(recording.id)
      message.success('录制已删除')
      await load()
    } finally {
      setOperatingId(null)
    }
  }

  const handleStart = async () => {
    // 仅按会议列表提供开始录制入口；后端要求会议进行中且有录制权限，
    // 否则会返回 400/403（见接口返回的错误信息）。
    if (!meetingId) return
    setOperatingId(-1)
    try {
      const rec = await recordingService.startRecording(meetingId, { quality: 'MEDIUM', format: 'MP4', type: 'FULL_MEETING' })
      message.success(`录制已开始：${rec?.recording_name || ''}`)
      await load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '开始录制失败')
    } finally {
      setOperatingId(null)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
            {meetingId ? `会议 #${meetingId} 的录制` : '会议录制'}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {meetingId ? '该会议的全部录制记录。' : '全部会议的录制记录。无头环境下录制可能失败，失败记录会如实展示，不会伪造可播放文件。'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {meetingId && (
            <>
              <Button type="button" variant="outline" onClick={() => navigate(`/meetings/${meetingId}`)}>返回会议</Button>
              <Button type="button" onClick={handleStart} disabled={operatingId === -1}>
                <Plus className="mr-2 h-4 w-4" />开始录制
              </Button>
            </>
          )}
          <Button type="button" variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />刷新
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: '录制总数', value: stats.total_recordings },
            { label: '进行中', value: stats.active_recordings },
            { label: '已完成', value: stats.completed_recordings },
            { label: '失败', value: stats.failed_recordings },
          ].map((item) => (
            <Card key={item.label}>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground">{item.label}</div>
                <div className="mt-2 text-xl font-semibold">{item.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader><CardTitle className="text-lg">录制列表</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="按录制名称搜索"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { setKeyword(keywordInput); setPage(1) } }}
              />
            </div>
            <div className="w-full md:w-40">
              <Select value={status} onValueChange={(v) => { setStatus(v || ''); setPage(1) }}>
                <SelectTrigger><SelectValue placeholder="全部状态" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部状态</SelectItem>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full md:w-44">
              <Select value={type} onValueChange={(v) => { setType(v || ''); setPage(1) }}>
                <SelectTrigger><SelectValue placeholder="全部类型" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部类型</SelectItem>
                  {Object.entries(typeLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={() => { setKeyword(keywordInput); setPage(1) }}>搜索</Button>
          </div>

          {loading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载录制...
            </div>
          ) : error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          ) : recordings.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-2 text-muted-foreground">
              <div>暂无录制</div>
              <div className="text-xs">该筛选条件下没有录制记录；开始录制后记录会出现在这里。</div>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>录制名称</TableHead>
                    <TableHead>会议</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>时长</TableHead>
                    <TableHead>大小</TableHead>
                    <TableHead>开始时间</TableHead>
                    <TableHead>观看 / 下载</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recordings.map((rec) => (
                    <TableRow key={rec.id}>
                      <TableCell>
                        <Link to={`/meetings/recordings/${rec.id}`} className="font-medium text-blue-600 hover:underline">
                          {rec.recording_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Link to={`/meetings/${rec.meeting_id}`} className="text-blue-600 hover:underline">#{rec.meeting_id}</Link>
                      </TableCell>
                      <TableCell>{typeLabels[rec.recording_type] || rec.recording_type}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={statusBadgeClass[rec.recording_status] || ''}>
                          {statusLabels[rec.recording_status] || rec.recording_status}
                        </Badge>
                        {rec.recording_status === 'PROCESSING' && typeof rec.processing_progress === 'number' && (
                          <span className="ml-2 text-xs text-muted-foreground">{rec.processing_progress}%</span>
                        )}
                      </TableCell>
                      <TableCell>{formatDuration(rec.duration_seconds)}</TableCell>
                      <TableCell>{formatFileSize(rec.file_size)}</TableCell>
                      <TableCell>{formatDateTime(rec.start_time)}</TableCell>
                      <TableCell>{rec.view_count ?? 0} / {rec.download_count ?? 0}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button type="button" variant="outline" size="sm" onClick={() => navigate(`/meetings/recordings/${rec.id}`)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          {rec.recording_status === 'COMPLETED' && (
                            <Button type="button" variant="outline" size="sm" onClick={() => navigate(`/meetings/recordings/${rec.id}/player`)}>
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={operatingId === rec.id || rec.recording_status === 'RECORDING'}
                            onClick={() => handleDelete(rec)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>共 {total} 条</span>
                <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
