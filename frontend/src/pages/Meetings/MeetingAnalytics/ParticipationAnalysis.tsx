import React, { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useAnalyticsStore } from '@/stores/meeting/analyticsStore'
import AnalyticsLayout from './AnalyticsLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import EmptyState from '@/components/ui/EmptyState'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/Table'
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'

const fmt = (value: number | null | undefined, digits = 2): string =>
  value === null || value === undefined || Number.isNaN(value)
    ? '暂无数据'
    : Number(value).toFixed(digits)

/**
 * 参与度分析：复用 GET /api/v1/meetings/{id}/analytics 返回的 participation_metrics。
 * 后端未提供加入/离开时间、总时长字段，页面不展示这些列、不编造；
 * 逐人列表为空时展示空态（当前后端返回空列表）。
 */
const ParticipationAnalysis: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const { participationData, isLoadingParticipation, error, fetchParticipationData } =
    useAnalyticsStore()
  const data = Number.isFinite(meetingId) ? participationData[meetingId] : undefined

  useEffect(() => {
    if (Number.isFinite(meetingId)) fetchParticipationData(meetingId)
  }, [meetingId, fetchParticipationData])

  return (
    <AnalyticsLayout title="参与度分析">
      <div data-testid="participation-analysis">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">参与者表现分析</h2>
        <p className="mt-1 text-sm text-gray-500">
          数据来源：GET /api/v1/meetings/{meetingId}/analytics 的 participation_metrics（接口直接返回）
        </p>

        {isLoadingParticipation && !data && (
          <div className="flex items-center justify-center py-12 text-gray-600">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-3">正在加载参与度数据…</span>
          </div>
        )}

        {error && !data && (
          <Alert className="mt-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              加载失败：{error}
              <Button variant="outline" size="sm" className="ml-4" onClick={() => fetchParticipationData(meetingId)}>
                <RefreshCw className="mr-1 h-4 w-4" />重试
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {data && (
          <div className="mt-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">参与人数</div>
                  <div className="mt-2 text-2xl font-semibold">
                    {data.hasData ? data.participants.length : '暂无数据'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">平均参与度评分</div>
                  <div className="mt-2 text-2xl font-semibold">{fmt(data.averageEngagement)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">总互动次数</div>
                  <div className="mt-2 text-2xl font-semibold">
                    {data.totalInteractions === null ? '暂无数据' : data.totalInteractions}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>参与者明细</CardTitle>
              </CardHeader>
              <CardContent>
                {!data.hasData ? (
                  <EmptyState
                    title="暂无逐人参与数据"
                    description="接口未返回 participation_metrics（当前后端返回空列表）。加入/离开时间、总时长等字段接口未提供，待后端补齐采集后展示。"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>参与者</TableHead>
                        <TableHead>发言时长（分钟）</TableHead>
                        <TableHead>发言占比</TableHead>
                        <TableHead>互动次数</TableHead>
                        <TableHead>参与度评分</TableHead>
                        <TableHead>专注度评分</TableHead>
                        <TableHead>贡献质量评分</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.participants.map((p) => (
                        <TableRow key={p.user_id}>
                          <TableCell>{p.user_name}</TableCell>
                          <TableCell>{fmt(p.speaking_time_minutes, 1)}</TableCell>
                          <TableCell>{fmt(p.speaking_percentage, 1)}%</TableCell>
                          <TableCell>{p.interaction_count}</TableCell>
                          <TableCell>{fmt(p.engagement_score)}</TableCell>
                          <TableCell>{fmt(p.attention_score)}</TableCell>
                          <TableCell>{fmt(p.contribution_quality)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
                <p className="mt-4 text-xs text-muted-foreground">
                  注：接口未返回加入/离开时间与总时长，暂不展示；参与度趋势图需时序数据，接口未提供，暂不绘制。
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </AnalyticsLayout>
  )
}

export default ParticipationAnalysis
