import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAnalyticsStore } from '@/stores/meeting/analyticsStore'
import AnalyticsLayout from './AnalyticsLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Progress } from '@/components/ui/Progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { AlertCircle, Download, FileText, Loader2 } from 'lucide-react'

/**
 * 报告生成：POST /api/v1/meetings/{id}/analytics/reports/generate（format html|markdown），
 * 生成后按后端返回的 download_url（或约定下载端点）下载。
 * 进度按真实请求阶段推进，不再用 setTimeout 假进度；端点未就绪（404）时进入错误态。
 */
const ReportGenerator: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const meetingId = Number(id)
  const { reportGeneration, generateReport, resetReportGeneration } = useAnalyticsStore()
  const [format, setFormat] = useState<'html' | 'markdown'>('markdown')

  const handleGenerate = async () => {
    resetReportGeneration()
    await generateReport(meetingId, format, { format })
  }

  return (
    <AnalyticsLayout title="报告生成">
      <div data-testid="report-generator">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">会议分析报告</h2>
        <p className="mt-1 text-sm text-gray-500">
          数据来源：POST /api/v1/meetings/{meetingId}/analytics/reports/generate；报告聚合分析、摘要与纪要数据生成。
        </p>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>生成报告</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-xs">
              <label className="text-sm font-medium">报告格式</label>
              <Select
                value={format}
                onValueChange={(v) => setFormat(v as 'html' | 'markdown')}
                disabled={reportGeneration.isGenerating}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择格式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="markdown">Markdown（.md）</SelectItem>
                  <SelectItem value="html">HTML（.html）</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleGenerate} disabled={reportGeneration.isGenerating}>
                {reportGeneration.isGenerating ? (
                  <>
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />生成中…
                  </>
                ) : (
                  <>
                    <FileText className="mr-1 h-4 w-4" />生成报告
                  </>
                )}
              </Button>
              {reportGeneration.downloadUrl && !reportGeneration.isGenerating && (
                <Button variant="outline" asChild>
                  <a href={reportGeneration.downloadUrl} download={reportGeneration.fileName ?? undefined}>
                    <Download className="mr-1 h-4 w-4" />下载报告
                  </a>
                </Button>
              )}
            </div>

            {(reportGeneration.isGenerating || reportGeneration.progress > 0) && (
              <div className="space-y-2">
                <Progress value={reportGeneration.progress} />
                <p className="text-sm text-gray-600">
                  {reportGeneration.currentStep}（{reportGeneration.progress}%）
                </p>
                <p className="text-xs text-muted-foreground">
                  进度按真实请求阶段推进：请求后端生成 → 后端返回 → 准备下载。
                </p>
              </div>
            )}

            {reportGeneration.error && (
              <Alert className="border-red-200 bg-red-50">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-800">{reportGeneration.error}</AlertDescription>
              </Alert>
            )}

            {!reportGeneration.isGenerating &&
              !reportGeneration.error &&
              reportGeneration.progress === 100 && (
                <Alert className="border-green-200 bg-green-50">
                  <AlertDescription className="text-green-800">
                    报告生成完成{reportGeneration.downloadUrl ? '，点击“下载报告”获取文件。' : '。'}
                  </AlertDescription>
                </Alert>
              )}
          </CardContent>
        </Card>

        <p className="mt-4 text-xs text-muted-foreground">
          报告内容聚合自会议分析（GET /analytics）、摘要（GET /summary）与纪要（GET /minutes）接口的真实返回；
          若某项数据缺失，报告中对应部分标注“暂无数据”，不填补假内容。
        </p>
      </div>
    </AnalyticsLayout>
  )
}

export default ReportGenerator
