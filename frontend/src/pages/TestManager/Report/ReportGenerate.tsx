// @ts-nocheck
import React, { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowLeft, Download, Eye, FileText, Settings } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Checkbox } from '../../../components/ui/Checkbox'
import { reportsApi } from '../../../services/api/reports'
import { ReportFormat, ReportType } from '../../../types/testmanager'

const reportTypes = [
  { value: ReportType.EXECUTION, label: '执行报告' },
  { value: ReportType.DEFECT, label: '缺陷报告' },
  { value: ReportType.COVERAGE, label: '覆盖率报告' },
  { value: ReportType.QUALITY, label: '质量报告' },
  { value: ReportType.PERFORMANCE, label: '性能报告' },
  { value: ReportType.SECURITY, label: '安全报告' },
]

const formats = [
  { value: ReportFormat.HTML, label: 'HTML' },
  { value: ReportFormat.PDF, label: 'PDF' },
  { value: ReportFormat.EXCEL, label: 'Excel' },
  { value: ReportFormat.JSON, label: 'JSON' },
]

const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

const queryTypeToReportType = (type: string | null) => ({
  execution: ReportType.EXECUTION,
  defect: ReportType.DEFECT,
  coverage: ReportType.COVERAGE,
  quality: ReportType.QUALITY,
  performance: ReportType.PERFORMANCE,
  security: ReportType.SECURITY,
}[String(type || '').toLowerCase()] || ReportType.EXECUTION)

const readAiDraft = (stateDraft: any, destination: string) => {
  if (stateDraft?.source === 'ai-assistant' && stateDraft.destination === destination) return stateDraft

  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_IMPORT_DRAFT_KEY) || 'null')
    return saved?.source === 'ai-assistant' && saved.destination === destination ? saved : null
  } catch {
    return null
  }
}

const firstReadableLine = (content = '', fallback = 'AI 分析报告') => {
  const line = content
    .split('\n')
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith('|') && !/^[-*_]{3,}$/.test(item))

  return (line || fallback)
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[\d一二三四五六七八九十]+[.、)]\s*/, '')
    .slice(0, 100)
}

const buildReportName = (draft: any) => {
  if (!draft) return ''
  const title = draft.sessionTitle && draft.sessionTitle !== '新的 AI 对话'
    ? draft.sessionTitle
    : draft.title || firstReadableLine(draft.content)
  return `${title.slice(0, 60)} - AI 分析报告`
}

const reportTypeToBackend = (type: ReportType) => ({
  [ReportType.EXECUTION]: 'test_execution',
  [ReportType.DEFECT]: 'custom',
  [ReportType.COVERAGE]: 'test_coverage',
  [ReportType.QUALITY]: 'quality_metrics',
  [ReportType.PERFORMANCE]: 'performance',
  [ReportType.SECURITY]: 'security',
}[type] || 'custom')

const formatToBackend = (format: ReportFormat) => ({
  [ReportFormat.HTML]: 'html',
  [ReportFormat.PDF]: 'pdf',
  [ReportFormat.EXCEL]: 'excel',
  [ReportFormat.JSON]: 'json',
}[format] || 'html')

const ReportGenerate: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [aiDraft] = useState(() => readAiDraft((location.state as any)?.aiImport, 'report'))
  const initialReportType = queryTypeToReportType(new URLSearchParams(location.search).get('type'))
  const [config, setConfig] = useState(() => ({
    report_name: buildReportName(aiDraft),
    report_type: initialReportType,
    report_format: ReportFormat.HTML,
    report_period_start: '',
    report_period_end: '',
    include_charts: false,
    include_details: true,
  }))
  const [sourceContent, setSourceContent] = useState(aiDraft?.content || '')
  const [isGenerating, setIsGenerating] = useState(false)
  const [previewData, setPreviewData] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (aiDraft) sessionStorage.removeItem(AI_IMPORT_DRAFT_KEY)
  }, [aiDraft])

  const updateConfig = (key: string, value: any) => setConfig((current) => ({ ...current, [key]: value }))

  const handleGenerate = async () => {
    if (!config.report_name.trim()) {
      setError('请填写报告名称')
      return
    }

    setIsGenerating(true)
    setError('')
    try {
      const lines = sourceContent
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)

      await reportsApi.generateReport({
        report_name: config.report_name.trim(),
        report_type: reportTypeToBackend(config.report_type),
        formats: [formatToBackend(config.report_format)],
        include_charts: config.include_charts,
        include_details: config.include_details,
        title: config.report_name.trim(),
        summary: {
          来源: aiDraft ? 'AI 助手' : '手工生成',
          报告类型: reportTypes.find((item) => item.value === config.report_type)?.label || config.report_type,
          正文字数: sourceContent.length,
          生成时间: new Date().toLocaleString('zh-CN', { hour12: false }),
        },
        sections: [
          {
            title: aiDraft ? 'AI 分析内容' : '报告内容',
            description: aiDraft?.sessionTitle || '由报告生成页提交',
            data: lines.length ? lines : ['暂无正文内容，请返回补充报告内容。'],
          },
        ],
        metadata: {
          来源页面: aiDraft ? 'AI 助手' : '报告生成',
          开始日期: config.report_period_start || '-',
          结束日期: config.report_period_end || '-',
        },
      })
      navigate('/test-manager/reports')
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '生成报告失败')
    } finally {
      setIsGenerating(false)
    }
  }

  const handlePreview = () => {
    setPreviewData({
      report_name: config.report_name || '-',
      report_type: reportTypes.find((item) => item.value === config.report_type)?.label || '-',
      report_format: formats.find((item) => item.value === config.report_format)?.label || '-',
      source: aiDraft ? 'AI 助手' : '手工生成',
      content_lines: sourceContent.split('\n').filter((line) => line.trim()).length,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/reports">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回报告列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">生成测试报告</h1>
            <p className="text-gray-600">配置并生成自定义测试报告。</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                报告配置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="报告名称">
                <Input
                  value={config.report_name}
                  onChange={(event) => updateConfig('report_name', event.target.value)}
                  placeholder="请输入报告名称"
                />
              </Field>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <Field label="报告类型">
                  <Select value={config.report_type} onValueChange={(value) => updateConfig('report_type', value)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {reportTypes.map((item) => (
                        <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="输出格式">
                  <Select value={config.report_format} onValueChange={(value) => updateConfig('report_format', value)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {formats.map((item) => (
                        <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="开始日期">
                  <Input
                    type="date"
                    value={config.report_period_start}
                    onChange={(event) => updateConfig('report_period_start', event.target.value)}
                  />
                </Field>
                <Field label="结束日期">
                  <Input
                    type="date"
                    value={config.report_period_end}
                    onChange={(event) => updateConfig('report_period_end', event.target.value)}
                  />
                </Field>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox checked={config.include_charts} onCheckedChange={(checked) => updateConfig('include_charts', Boolean(checked))} />
                  包含图表
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox checked={config.include_details} onCheckedChange={(checked) => updateConfig('include_details', Boolean(checked))} />
                  包含明细
                </label>
              </div>
            </CardContent>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                报告内容
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                rows={12}
                value={sourceContent}
                onChange={(event) => setSourceContent(event.target.value)}
                placeholder="填写或从 AI 助手导入报告正文"
              />
              {aiDraft && (
                <p className="mt-2 text-xs text-blue-700">已从 AI 助手导入报告内容，生成前可继续编辑。</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>操作</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button variant="outline" onClick={handlePreview} className="w-full">
                <Eye className="mr-2 h-4 w-4" />
                预览
              </Button>
              <Button onClick={handleGenerate} disabled={isGenerating || !config.report_name} className="w-full">
                <Download className="mr-2 h-4 w-4" />
                {isGenerating ? '生成中...' : '生成报告'}
              </Button>
            </CardContent>
          </Card>

          {previewData && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  报告预览
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <Info label="报告名称" value={previewData.report_name} />
                <Info label="报告类型" value={previewData.report_type} />
                <Info label="输出格式" value={previewData.report_format} />
                <Info label="来源" value={previewData.source} />
                <Info label="正文行数" value={previewData.content_lines} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-2 text-sm font-medium">
    <span>{label}</span>
    {children}
  </label>
)

const Info = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="flex justify-between">
    <span className="text-gray-500">{label}</span>
    <span className="font-medium">{value}</span>
  </div>
)

export default ReportGenerate
