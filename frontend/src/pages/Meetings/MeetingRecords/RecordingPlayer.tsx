// @ts-nocheck
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Loader2 } from 'lucide-react'
import { message } from 'antd'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import recordingService, { RecordingPlaybackInfo } from '@/services/meeting/recordingService'
import type { MeetingRecording } from '@/types/meeting'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const formatDuration = (seconds?: number) => {
  if (!seconds && seconds !== 0) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`
}

export default function RecordingPlayer() {
  const navigate = useNavigate()
  const { recordingId } = useParams()
  const id = Number(recordingId)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [recording, setRecording] = useState<MeetingRecording | null>(null)
  const [playback, setPlayback] = useState<RecordingPlaybackInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [videoError, setVideoError] = useState<string | null>(null)
  const [playbackRate, setPlaybackRate] = useState('1')
  const [downloading, setDownloading] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    setVideoError(null)
    try {
      // 先拿录制本身（决定错误态里能否展示录制状态），再拿播放信息；
      // 不要用 Promise.all：播放 400 会把已取到的录制也一起丢掉。
      const rec = await recordingService.getRecording(id)
      setRecording(rec)
      const info = await recordingService.getPlaybackInfo(id)
      setPlayback(info)
    } catch (err: any) {
      // 未完成处理的录制后端返回 400“录制尚未完成处理”；不存在返回 404。
      // 播放页不伪造播放器：拿不到播放信息就如实展示原因。
      setError(err?.response?.data?.detail || err?.message || '获取播放信息失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = Number(playbackRate)
  }, [playbackRate, playback])

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
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '下载失败：录制文件不存在或无权限')
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-80 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载播放信息...
      </div>
    )
  }

  if (error || !playback || !recording) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-3 text-muted-foreground">
        <div>{error || '无法播放该录制'}</div>
        {recording && (
          <div className="text-sm">录制状态：{recording.recording_status}；仅已完成的录制可以播放。</div>
        )}
        <div className="flex gap-2">
          <Button asChild variant="outline"><Link to={`/meetings/recordings/${id}`}>返回录制详情</Link></Button>
          <Button type="button" variant="outline" onClick={load}>重试</Button>
        </div>
      </div>
    )
  }

  const config = playback.playback_config || {}
  // video_url 是后端给的下载地址（含播放 token），相对路径时拼上
  // API 根地址；<video> 不带 Authorization 请求头，靠 token 鉴权。
  const videoUrl = config.video_url?.startsWith('http')
    ? config.video_url
    : `${API_BASE}${config.video_url || ''}`
  const subtitles = Array.isArray(config.subtitles) ? config.subtitles : []
  const chapters = Array.isArray(config.chapters) ? config.chapters : []

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <Button type="button" variant="outline" size="icon" onClick={() => navigate(`/meetings/recordings/${id}`)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">{recording.recording_name}</h1>
              <Badge variant="outline">{config.format || recording.file_format}</Badge>
              {config.resolution && <Badge variant="outline">{config.resolution}</Badge>}
            </div>
            <p className="text-sm text-muted-foreground">
              录制 #{recording.id} · 时长 {formatDuration(config.duration ?? recording.duration_seconds)} · 播放令牌 24 小时内有效
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={handleDownload} disabled={downloading}>
            <Download className="mr-2 h-4 w-4" />下载
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate('/meetings/recordings')}>返回列表</Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <video
            ref={videoRef}
            className="aspect-video w-full rounded-md bg-black"
            controls
            preload="metadata"
            src={videoUrl}
            onError={() => setVideoError('视频加载失败：文件可能不存在或已过期，请刷新重试。')}
          />
          {videoError && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{videoError}</div>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="text-sm text-muted-foreground">倍速</span>
            <div className="w-28">
              <Select value={playbackRate} onValueChange={setPlaybackRate}>
                <SelectTrigger><SelectValue placeholder="倍速" /></SelectTrigger>
                <SelectContent>
                  {['0.5', '0.75', '1', '1.25', '1.5', '2'].map((rate) => (
                    <SelectItem key={rate} value={rate}>{rate}x</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <span className="text-sm text-muted-foreground">音量 / 全屏请用播放器自带控制。</span>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-lg">章节</CardTitle></CardHeader>
          <CardContent>
            {chapters.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无章节信息（后端未提供章节数据）。</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {chapters.map((ch: any, index: number) => (
                  <li key={index} className="flex justify-between gap-2">
                    <button
                      type="button"
                      className="text-left text-blue-600 hover:underline"
                      onClick={() => { if (videoRef.current) { videoRef.current.currentTime = ch.start_time || 0; videoRef.current.play() } }}
                    >
                      {ch.title}
                    </button>
                    <span className="text-muted-foreground">{formatDuration(ch.start_time)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-lg">字幕</CardTitle></CardHeader>
          <CardContent>
            {subtitles.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无字幕（后端未提供字幕数据；录制转录依赖录制文件与 STT，全链路暂缺）。</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {subtitles.map((sub: any, index: number) => (
                  <li key={index}>{sub.language} · {sub.url}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
