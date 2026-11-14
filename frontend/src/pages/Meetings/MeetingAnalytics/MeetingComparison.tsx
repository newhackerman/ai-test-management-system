import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import meetingService from '@/services/meeting/meetingService'
import {
  analyticsService,
  apiErrorMessage,
  type MeetingAnalyticsResponse,
} from '@/services/meeting/analyticsService'
import type { Meeting } from '@/types/meeting'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Checkbox } from '@/components/ui/Checkbox'
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
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react'

interface ComparedMeeting {
  meeting: Meeting
  analytics: MeetingAnalyticsResponse | null
  error?: string | null
}

const fmt = (value: number | null | undefined, suffix = ''): string =>
  value === null || value === undefined || Number.isNaN(value)
    ? '暂无数据'
    : `${Number(value).toFixed(2)}${suffix}`

const avg = (values: number[]): number | null =>
  values.length > 0 ? values.reduce((s, v) => s + v, 0) / values.length : null

/**
 * 会议对比：无后端对比端点，前端拼装——GET /api/v1/meetings 列表 + 逐个 GET /analytics。
 * 对比维度只用 analytics 返回体的标准维度：
 * 效果评分、参与度、发言分布、决策效率、时长利用率、议程完成率。
 * 注意：接口未返回“决策数”，以决策效率评分代替，并在页面与报告中注明；
 * “时长利用率”即接口 time_utilization 字段，维度定义待用户确认。
 */
const MeetingComparison: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [total, setTotal] = useState(0)
  const [loadingList, setLoadingList] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [comparing, setComparing] = useState(false)
  const [compared, setCompared] = useState<ComparedMeeting[]>([])
  const [compareError, setCompareError] = useState<string | null>(null)

  const loadMeetings = useCallback(async () => {
    setLoadingList(true)
    setListError(null)
    try {
      const result = await meetingService.getMeetings({ page: 1, page_size: 50 })
      setMeetings(result.meetings ?? [])
      setTotal(result.total ?? 0)
    } catch (err) {
      setListError(apiErrorMessage(err, '获取会议列表失败'))
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    loadMeetings()
  }, [loadMeetings])

  const toggleSelect = (meetingId: number) => {
    setSelected((prev) =>
      prev.includes(meetingId)
        ? prev.filter((id) => id !== meetingId)
        : prev.length >= 5
          ? prev
          : [...prev, meetingId],
    )
  }

  const handleCompare = async () => {
    if (selected.length < 2) return
    setComparing(true)
    setCompareError(null)
    const chosen = meetings.filter((m) => selected.includes(m.id))
    const results = await Promise.all(
      chosen.map(async (meeting): Promise<ComparedMeeting> => {
        try {
          const analytics = await analyticsService.getAnalytics(meeting.id)
          return { meeting, analytics }
        } catch (err) {
          return { meeting, analytics: null, error: apiErrorMessage(err, '获取分析失败') }
        }
      }),
    )
    setCompared(results)
    if (results.every((r) => !r.analytics)) {
      setCompareError('所选会议的分析数据均获取失败，请检查后端分析接口。')
    }
    setComparing(false)
  }

  const topSpeaker = (a: MeetingAnalyticsResponse | null): string => {
    if (!a || !a.participation_metrics?.length) return '暂无数据'
    const top = [...a.participation_metrics].sort(
      (x, y) => y.speaking_percentage - x.speaking_percentage,
    )[0]
    return `${top.user_name}（${top.speaking_percentage.toFixed(1)}%）`
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-800/50">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div data-testid="meeting-comparison">
          <Link
            to="/meetings"
            className="flex w-fit items-center space-x-2 text-gray-600 hover:text-gray-900 dark:text-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
            <span className="font-medium">返回会议列表</span>
          </Link>
          <h1 className="mt-4 text-3xl font-bold text-gray-900 dark:text-gray-100">会议对比</h1>
          <p className="mt-1 text-sm text-gray-500">
            选择会议：从会议列表中勾选 2–5 个会议，对比其分析数据。数据来源：GET /api/v1/meetings
            + 逐个 GET /api/v1/meetings/{'{id}'}/analytics（无后端对比端点，前端拼装）。
          </p>

          {loadingList && (
            <div className="flex items-center justify-center py-12 text-gray-600">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-3">正在加载会议列表…</span>
            </div>
          )}

          {listError && !loadingList && (
            <Alert className="mt-6 border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">
                加载失败：{listError}
                <Button variant="outline" size="sm" className="ml-4" onClick={loadMeetings}>
                  重试
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {!loadingList && !listError && meetings.length === 0 && (
            <div className="mt-6">
              <EmptyState title="暂无会议" description="还没有可对比的会议，请先创建会议。" />
            </div>
          )}

          {!loadingList && meetings.length > 0 && (
            <>
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>选择会议（共 {total} 个，已选 {selected.length} 个，最多 5 个）</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {meetings.map((m) => (
                      <label key={m.id} className="flex cursor-pointer items-center gap-3 text-sm">
                        <Checkbox
                          checked={selected.includes(m.id)}
                          onCheckedChange={() => toggleSelect(m.id)}
                        />
                        <span className="font-medium">{m.title}</span>
                        <span className="text-muted-foreground">
                          {m.scheduled_start_time
                            ? new Date(m.scheduled_start_time).toLocaleString()
                            : '暂无数据'}
                          {' · '}
                          {m.status}
                        </span>
                      </label>
                    ))}
                  </div>
                  <Button
                    className="mt-4"
                    onClick={handleCompare}
                    disabled={selected.length < 2 || comparing}
                  >
                    {comparing ? (
                      <>
                        <Loader2 className="mr-1 h-4 w-4 animate-spin" />对比分析加载中…
                      </>
                    ) : (
                      '开始对比'
                    )}
                  </Button>
                  {selected.length < 2 && (
                    <p className="mt-2 text-xs text-muted-foreground">请至少选择 2 个会议。</p>
                  )}
                </CardContent>
              </Card>

              {compareError && (
                <Alert className="mt-6 border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-800">{compareError}</AlertDescription>
                </Alert>
              )}

              {compared.length > 0 && (
                <Card className="mt-6">
                  <CardHeader>
                    <CardTitle>对比结果</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>对比维度</TableHead>
                          {compared.map(({ meeting }) => (
                            <TableHead key={meeting.id}>{meeting.title}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <TableRow>
                          <TableCell className="font-medium">整体效果评分</TableCell>
                          {compared.map(({ meeting, analytics, error }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? fmt(analytics.overall_effectiveness) : error ?? '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">会议质量评分</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? fmt(analytics.meeting_quality_score) : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">参与度（平均参与度评分）</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics?.participation_metrics?.length
                                ? fmt(avg(analytics.participation_metrics.map((p) => p.engagement_score)))
                                : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">发言分布（发言占比最高者）</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>{topSpeaker(analytics)}</TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">决策效率评分（接口未返回决策数）</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? fmt(analytics.decision_efficiency) : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">议程完成率</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? fmt(analytics.agenda_completion_rate, '%') : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">时长利用率</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? fmt(analytics.time_utilization, '%') : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium">技术问题次数</TableCell>
                          {compared.map(({ meeting, analytics }) => (
                            <TableCell key={meeting.id}>
                              {analytics ? String(analytics.technical_issues_count) : '暂无数据'}
                            </TableCell>
                          ))}
                        </TableRow>
                      </TableBody>
                    </Table>
                    <p className="mt-4 text-xs text-muted-foreground">
                      口径说明：各维度均为 analytics 返回体的标准字段原值；“决策数”接口未返回，以决策效率评分代替；
                      “时长利用率”即 time_utilization 字段，该维度定义待用户确认；参与人数/发言分布依赖
                      participation_metrics，接口返回空列表时显示“暂无数据”。
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default MeetingComparison
