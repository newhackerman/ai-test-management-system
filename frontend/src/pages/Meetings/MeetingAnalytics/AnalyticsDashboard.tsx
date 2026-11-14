import React, { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useAnalyticsStore } from '@/stores/meeting/analyticsStore'
import AnalyticsLayout from './AnalyticsLayout'
import { BarChart, PieChart } from './charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import EmptyState from '@/components/ui/EmptyState'
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'

const fmt = (value: number | null | undefined, suffix = ''): string =>
  value === null || value === undefined || Number.isNaN(value)
    ? '暂无数据'
    : `${Number(value).toFixed(2)}${suffix}`

/**
 * 会议分析概览：只展示 GET /api/v1/meetings/{id}/analytics 直接返回的值。
 * 后端当前仍有固定值字段（如情感评分），属后端待改造项，前端不改写数字，
 * 仅在页面底部注明数据来源与口径。
 */
const AnalyticsDashboard: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const { effectivenessData, isLoadingEffectiveness, error, fetchEffectivenessData } =
    useAnalyticsStore()
  const data = Number.isFinite(meetingId) ? effectivenessData[meetingId] : undefined

  useEffect(() => {
    if (Number.isFinite(meetingId)) fetchEffectivenessData(meetingId)
  }, [meetingId, fetchEffectivenessData])

  const sentiment = (data?.sentiment_analysis ?? {}) as Record<string, unknown>
  const speakingDistribution = (data?.participation_metrics ?? []).map((p) => ({
    name: p.user_name,
    value: p.speaking_time_minutes,
  }))
  const speakingBars = (data?.participation_metrics ?? []).map((p) => ({
    name: p.user_name,
    speakingTime: p.speaking_time_minutes,
    percentage: p.speaking_percentage,
  }))

  return (
    <AnalyticsLayout title="分析概览">
      <div data-testid="analytics-dashboard">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">会议效果综合分析</h2>
        <p className="mt-1 text-sm text-gray-500">
          数据来源：GET /api/v1/meetings/{meetingId}/analytics（接口直接返回，未做加工）
        </p>

        {isLoadingEffectiveness && !data && (
          <div className="flex items-center justify-center py-12 text-gray-600">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-3">正在加载分析数据…</span>
          </div>
        )}

        {error && !data && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              加载失败：{error}
              <Button variant="outline" size="sm" className="ml-4" onClick={() => fetchEffectivenessData(meetingId)}>
                <RefreshCw className="mr-1 h-4 w-4" />重试
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {data && (
          <div className="mt-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">整体效果评分</div>
                  <div className="mt-2 text-2xl font-semibold">{fmt(data.overall_effectiveness)}</div>
                  <div className="mt-1 text-xs text-muted-foreground">接口返回值（schema 标注 1–5 分制）</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">会议质量评分</div>
                  <div className="mt-2 text-2xl font-semibold">{fmt(data.meeting_quality_score)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">议程完成率</div>
                  <div className="mt-2 text-2xl font-semibold">{fmt(data.agenda_completion_rate, '%')}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">时间利用率</div>
                  <div className="mt-2 text-2xl font-semibold">{fmt(data.time_utilization, '%')}</div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">决策效率评分</div>
                  <div className="mt-2 text-xl font-semibold">{fmt(data.decision_efficiency)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">平均网络质量</div>
                  <div className="mt-2 text-xl font-semibold">{fmt(data.network_quality_avg)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">技术问题次数</div>
                  <div className="mt-2 text-xl font-semibold">{data.technical_issues_count ?? '暂无数据'}</div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>发言分布</CardTitle>
                </CardHeader>
                <CardContent>
                  {speakingDistribution.length > 0 ? (
                    <PieChart data={speakingDistribution} title="发言时长分布（分钟）" height={260} />
                  ) : (
                    <EmptyState
                      title="暂无逐人参与数据"
                      description="接口未返回 participation_metrics（当前后端返回空列表），无法绘制发言分布。"
                    />
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>发言时长</CardTitle>
                </CardHeader>
                <CardContent>
                  {speakingBars.length > 0 ? (
                    <BarChart data={speakingBars} xKey="name" yKey="speakingTime" title="各参与者发言时长（分钟）" height={260} />
                  ) : (
                    <EmptyState
                      title="暂无逐人参与数据"
                      description="接口未返回 participation_metrics（当前后端返回空列表），无法绘制发言时长。"
                    />
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>情感分析</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 text-sm md:grid-cols-4">
                  <div>整体情感：{typeof sentiment.overall_sentiment === 'string' ? sentiment.overall_sentiment : '暂无数据'}</div>
                  <div>情感评分：{typeof sentiment.sentiment_score === 'number' ? sentiment.sentiment_score.toFixed(2) : '暂无数据'}</div>
                  <div>积极占比：{typeof sentiment.positive_ratio === 'number' ? `${(sentiment.positive_ratio * 100).toFixed(0)}%` : '暂无数据'}</div>
                  <div>消极占比：{typeof sentiment.negative_ratio === 'number' ? `${(sentiment.negative_ratio * 100).toFixed(0)}%` : '暂无数据'}</div>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  情感评分为接口直接返回；当前后端该字段仍为固定值，待后端组改为真实计算后自动更新。
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>改进建议</CardTitle>
              </CardHeader>
              <CardContent>
                {data.improvement_suggestions?.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {data.improvement_suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无改进建议</p>
                )}
                <p className="mt-4 text-xs text-muted-foreground">
                  分析时间：{data.analyzed_at ? new Date(data.analyzed_at).toLocaleString() : '暂无数据'}
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </AnalyticsLayout>
  )
}

export default AnalyticsDashboard
