import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAnalyticsStore } from '@/stores/meeting/analyticsStore'
import AnalyticsLayout from './AnalyticsLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import EmptyState from '@/components/ui/EmptyState'
import { AlertCircle, Loader2, RefreshCw, Sparkles } from 'lucide-react'

const GENERATION_METHOD_LABEL: Record<string, string> = {
  TEMPLATE_BASED: '模板生成',
  AI_ANALYSIS: 'AI 分析生成',
  SPEECH_TO_TEXT: '语音转写生成',
  MANUAL_INPUT: '手工录入',
  pending: '未生成',
}

const fmtDate = (value?: string | null): string =>
  value ? new Date(value).toLocaleString() : '暂无数据'

/**
 * 会议摘要：GET /api/v1/meetings/{id}/summary 读取已生成摘要，
 * 未生成时展示空态 + “生成摘要”（POST /summary/generate）。
 * 内容来源以 generation_method 为准在 UI 注明；无转录时内容为模板生成。
 */
const MeetingSummary: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const { summaryData, isLoadingSummary, error, fetchSummaryData, generateSummary } =
    useAnalyticsStore()
  const [generating, setGenerating] = useState(false)
  const [generateFailed, setGenerateFailed] = useState(false)
  const data = Number.isFinite(meetingId) ? summaryData[meetingId] : undefined

  useEffect(() => {
    if (Number.isFinite(meetingId)) fetchSummaryData(meetingId)
  }, [meetingId, fetchSummaryData])

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateFailed(false)
    const ok = await generateSummary(meetingId)
    setGenerating(false)
    if (!ok) setGenerateFailed(true)
  }

  const loading = isLoadingSummary || generating

  return (
    <AnalyticsLayout title="会议摘要">
      <div data-testid="meeting-summary">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">AI 会议摘要</h2>
            <p className="mt-1 text-sm text-gray-500">
              数据来源：GET /api/v1/meetings/{meetingId}/summary；生成：POST /summary/generate
            </p>
          </div>
          {data && (
            <Button variant="outline" onClick={handleGenerate} disabled={loading}>
              <RefreshCw className="mr-1 h-4 w-4" />重新生成
            </Button>
          )}
        </div>

        {loading && !data && (
          <div className="flex items-center justify-center py-12 text-gray-600">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-3">{generating ? '正在生成摘要…' : '正在加载摘要…'}</span>
          </div>
        )}

        {error && !data && !loading && !generateFailed && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              加载失败：{error}
              <Button variant="outline" size="sm" className="ml-4" onClick={() => fetchSummaryData(meetingId)}>
                重试
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {generateFailed && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              生成失败：{error ?? '后端生成接口返回错误，请稍后重试。'}
            </AlertDescription>
          </Alert>
        )}

        {!loading && !error && !data && (
          <div className="mt-6">
            <EmptyState
              title="暂无会议摘要"
              description="该会议尚未生成摘要。点击下方按钮生成；生成内容目前以后端模板规则产出，未接入真实 LLM，且无转录数据时内容基于会议基础信息生成。"
              actionLabel={generating ? '生成中…' : '生成摘要'}
              onAction={handleGenerate}
            />
          </div>
        )}

        {data && (
          <div className="mt-6 space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>会议概述</CardTitle>
                  <Badge variant="secondary">
                    {GENERATION_METHOD_LABEL[data.generation_method] ?? data.generation_method}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{data.overview}</p>
                <p className="mt-4 text-xs text-muted-foreground">
                  生成时间：{fmtDate(data.generated_at)}；语言：{data.language}；生成方式：
                  {GENERATION_METHOD_LABEL[data.generation_method] ?? data.generation_method}
                  {data.generation_method === 'TEMPLATE_BASED' &&
                    '（模板生成，未接入真实 LLM；缺转录数据时内容基于会议基础信息）'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>关键要点</CardTitle>
              </CardHeader>
              <CardContent>
                {data.key_points?.length > 0 ? (
                  <ul className="space-y-3">
                    {data.key_points.map((kp, i) => (
                      <li key={i} className="text-sm">
                        <div className="font-medium">
                          {kp.title}
                          <span className="ml-2 text-xs text-muted-foreground">重要性 {kp.importance}/5</span>
                        </div>
                        <div className="mt-1 text-gray-600">{kp.content}</div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无关键要点</p>
                )}
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>决策事项</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.decisions?.length > 0 ? (
                    <ul className="space-y-2 text-sm">
                      {data.decisions.map((d) => (
                        <li key={d.decision_id}>
                          <div className="font-medium">{d.title}</div>
                          <div className="text-gray-600">{d.description}</div>
                          <div className="text-xs text-muted-foreground">
                            决策者：{d.decision_maker ?? '暂无数据'}；影响：{d.impact_level}；状态：{d.status}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">暂无决策事项</p>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>行动项（摘要内嵌）</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.action_items?.length > 0 ? (
                    <ul className="space-y-2 text-sm">
                      {data.action_items.map((a) => (
                        <li key={a.action_id}>
                          <div className="font-medium">{a.title}</div>
                          <div className="text-xs text-muted-foreground">
                            负责人：{a.assignee ?? '暂无数据'}；截止：{a.due_date ? new Date(a.due_date).toLocaleDateString() : '暂无数据'}；
                            优先级：{a.priority}；状态：{a.status}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      暂无行动项；行动项的完整管理请见“行动项目”页。
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>下一步计划</CardTitle>
              </CardHeader>
              <CardContent>
                {data.next_steps?.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {data.next_steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无下一步计划</p>
                )}
                {Object.keys(data.participants_summary ?? {}).length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-medium">参与者摘要</div>
                    <pre className="mt-1 overflow-auto rounded bg-gray-50 p-3 text-xs">
                      {JSON.stringify(data.participants_summary, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>

            <p className="flex items-center text-xs text-muted-foreground">
              <Sparkles className="mr-1 h-3 w-3" />
              摘要内容由后端生成；是否接入真实 LLM 以后端 generation_method 与后端组说明为准。
            </p>
          </div>
        )}
      </div>
    </AnalyticsLayout>
  )
}

export default MeetingSummary
