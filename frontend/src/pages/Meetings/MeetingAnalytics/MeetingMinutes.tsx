import React, { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import AnalyticsLayout from './AnalyticsLayout'
import {
  analyticsService,
  apiErrorMessage,
  type MeetingMinutesResponse,
} from '@/services/meeting/analyticsService'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import EmptyState from '@/components/ui/EmptyState'
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'

const fmtDate = (value?: string | null): string =>
  value ? new Date(value).toLocaleString() : '暂无数据'

/**
 * 会议纪要：GET /api/v1/meetings/{id}/minutes 读列表，
 * POST /minutes/generate 生成（后端组在改造成落库 + 读库）。
 * 生成内容为后端模板产出，未接真实 LLM；缺转录时在 UI 注明。
 */
const MeetingMinutes: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const [minutes, setMinutes] = useState<MeetingMinutesResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!Number.isFinite(meetingId)) return
    setLoading(true)
    setError(null)
    try {
      setMinutes(await analyticsService.getMinutes(meetingId))
    } catch (err) {
      setError(apiErrorMessage(err, '获取会议纪要失败'))
    } finally {
      setLoading(false)
    }
  }, [meetingId])

  useEffect(() => {
    load()
  }, [load])

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError(null)
    try {
      await analyticsService.generateMinutes(meetingId)
      await load()
    } catch (err) {
      setGenerateError(apiErrorMessage(err, '生成会议纪要失败'))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <AnalyticsLayout title="会议纪要">
      <div data-testid="meeting-minutes">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">结构化会议纪要</h2>
            <p className="mt-1 text-sm text-gray-500">
              数据来源：GET /api/v1/meetings/{meetingId}/minutes；生成：POST /minutes/generate
            </p>
          </div>
          <Button onClick={handleGenerate} disabled={loading || generating}>
            {generating ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />生成中…
              </>
            ) : (
              '生成纪要'
            )}
          </Button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12 text-gray-600">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-3">正在加载纪要…</span>
          </div>
        )}

        {error && !loading && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              加载失败：{error}
              <Button variant="outline" size="sm" className="ml-4" onClick={load}>
                <RefreshCw className="mr-1 h-4 w-4" />重试
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {generateError && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              生成失败：{generateError}
            </AlertDescription>
          </Alert>
        )}

        {!loading && !error && minutes.length === 0 && (
          <div className="mt-6">
            <EmptyState
              title="暂无纪要"
              description="该会议还没有生成的纪要。点击“生成纪要”生成；内容为后端模板产出（未接真实 LLM），缺转录数据时基于会议基础信息生成。"
              actionLabel={generating ? '生成中…' : '生成纪要'}
              onAction={handleGenerate}
            />
          </div>
        )}

        {!loading && minutes.length > 0 && (
          <div className="mt-6 space-y-4">
            {minutes.map((m) => (
              <Card key={m.id}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-4">
                    <CardTitle>{m.title}</CardTitle>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="secondary">{m.status}</Badge>
                      <Badge variant="outline">版本 {m.version}</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {m.summary && <p className="text-sm text-gray-600">{m.summary}</p>}
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{m.content}</p>
                  <div className="mt-4 grid gap-1 text-xs text-muted-foreground md:grid-cols-3">
                    <div>类型：{m.minute_type}</div>
                    <div>
                      生成方式：{m.generation_method}
                      {m.generation_method === 'TEMPLATE_BASED' && '（模板生成，未接真实 LLM）'}
                    </div>
                    <div>创建时间：{fmtDate(m.created_at)}</div>
                    <div>参会人：{m.attendees?.length ? m.attendees.join('、') : '暂无数据'}</div>
                    <div>决策：{m.decisions?.length ?? 0} 项；行动项：{m.action_items?.length ?? 0} 项</div>
                    <div>需审批：{m.approval_required ? '是' : '否'}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AnalyticsLayout>
  )
}

export default MeetingMinutes
