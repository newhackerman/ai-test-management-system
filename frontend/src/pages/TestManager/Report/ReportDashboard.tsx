// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BarChart3, CheckCircle2, Clock, Download, Eye, FileText, Layers, Plus, RefreshCw, Search, Shield, Trash2, Upload, XCircle } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../../components/ui/Dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import ConfirmDialog from '../../../components/ui/ConfirmDialog'
import { reportsApi } from '../../../services/api/reports'
import { testPlanService } from '../../../services/testmanager/testPlanService'
import { formatDate } from '../../../utils/date'

const reportTypeCards = [
  { type: 'execution', title: '执行报告', description: '汇总测试执行结果和通过率', icon: FileText, color: 'text-blue-500 dark:text-blue-400' },
  { type: 'defect', title: '缺陷报告', description: '汇总缺陷数量、状态和严重程度', icon: BarChart3, color: 'text-red-500 dark:text-red-400' },
  { type: 'coverage', title: '覆盖率报告', description: '汇总需求和测试覆盖情况', icon: BarChart3, color: 'text-green-500 dark:text-green-400' },
]

const sourceOptions = [
  { value: 'all', label: '全部来源' },
  { value: 'generated', label: '平台生成' },
  { value: 'imported', label: '外部导入' },
]

const importSourceOptions = [
  { value: 'custom', label: '通用报告' },
  { value: 'allure', label: 'Allure' },
  { value: 'junit', label: 'JUnit' },
  { value: 'testng', label: 'TestNG' },
  { value: 'pytest', label: 'Pytest' },
  { value: 'selenium', label: 'Selenium' },
  { value: 'postman', label: 'Postman' },
  { value: 'jmeter', label: 'JMeter' },
]

const formatLabel = (format?: string) => String(format || '-').toUpperCase()
const reportTypeLabel = (value?: string) => reportTypeCards.find((item) => item.type === value)?.title || value || '-'
const sizeLabel = (size?: number) => {
  const value = Number(size || 0)
  if (!value) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
const sourceTypeLabel = (value?: string) => ({
  allure: 'Allure',
  junit: 'JUnit',
  testng: 'TestNG',
  pytest: 'Pytest',
  selenium: 'Selenium',
  postman: 'Postman',
  jmeter: 'JMeter',
  custom: '通用',
}[String(value || '').toLowerCase()] || value || '-')
const statusLabel = (value?: string) => ({
  completed: '已生成',
  partial: '部分生成',
  failed: '失败',
  imported: '已导入',
}[String(value || '').toLowerCase()] || value || '-')
const toNumber = (...values: any[]) => {
  for (const value of values) {
    if (value === null || value === undefined || value === '') continue
    const numeric = Number(String(value).replace('%', ''))
    if (Number.isFinite(numeric)) return numeric
  }
  return 0
}
const reportMetrics = (report: any) => {
  const summary = report?.summary || {}
  const total = toNumber(
    summary.total_cases,
    summary.totalCases,
    summary.total_tests,
    summary.test_results_count,
    summary['总用例'],
    summary.total,
  )
  const passed = toNumber(summary.passed, summary.passed_tests, summary['通过'])
  const failed = toNumber(summary.failed, summary.failed_tests, summary['失败'])
  const blocked = toNumber(summary.blocked, summary.blocked_tests, summary['阻塞'])
  const skipped = toNumber(summary.skipped, summary.skipped_tests, summary['跳过'])
  const executed = toNumber(summary.executed, summary.executed_cases, summary.executed_tests, passed + failed + blocked + skipped)
  const passRate = toNumber(summary.pass_rate, summary.passRate, summary['通过率'], executed ? (passed / executed) * 100 : 0)
  return {
    total,
    executed,
    passed,
    failed,
    blocked,
    skipped,
    passRate: Math.round(passRate * 10) / 10,
    totalDefects: toNumber(summary.total_defects, summary.totalDefects, summary['缺陷总数']),
    openDefects: toNumber(summary.open_defects, summary.openDefects, summary['未关闭缺陷']),
    highRiskDefects: toNumber(summary.high_risk_defects, summary.highRiskDefects, summary['高风险缺陷']),
  }
}

const ReportDashboard: React.FC = () => {
  const navigate = useNavigate()
  const [reports, setReports] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [downloadingId, setDownloadingId] = useState('')
  const [previewLoadingId, setPreviewLoadingId] = useState('')
  const [previewReport, setPreviewReport] = useState<any>(null)
  const [deleteReport, setDeleteReport] = useState<any>(null)
  const [error, setError] = useState('')
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importSourceType, setImportSourceType] = useState('custom')
  const [importDescription, setImportDescription] = useState('')
  const [testPlans, setTestPlans] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    report_type: 'all',
    source_filter: 'all',
    format_filter: 'all',
    test_plan_id: 'all',
  })

  const loadReports = async () => {
    setLoading(true)
    setError('')
    try {
      const [listResponse, analyticsResponse] = await Promise.all([
        reportsApi.getUnifiedReports({
          page: 1,
          page_size: 20,
          search: filters.search.trim() || undefined,
          report_type: filters.report_type === 'all' ? undefined : filters.report_type,
          source_filter: filters.source_filter === 'all' ? undefined : filters.source_filter,
          format_filter: filters.format_filter === 'all' ? undefined : filters.format_filter,
          test_plan_id: filters.test_plan_id === 'all' ? undefined : Number(filters.test_plan_id),
        }),
        reportsApi.getAnalytics(30),
      ])
      setReports(listResponse?.data || [])
      setTotal(Number(listResponse?.total || 0))
      setAnalytics(analyticsResponse?.data || null)
    } catch (err: any) {
      setError(err?.message || '加载报告数据失败')
      setReports([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReports()
  }, [filters])

  useEffect(() => {
    let cancelled = false
    testPlanService.getTestPlans({ page: 1, size: 100 })
      .then((response) => {
        if (!cancelled) setTestPlans(response.data || [])
      })
      .catch(() => {
        if (!cancelled) setTestPlans([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const updateFilter = (key: string, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  const statistics = useMemo(() => {
    const now = new Date()
    const thisMonth = reports.filter((report: any) => {
      const date = new Date(report.created_at)
      return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth()
    }).length
    const formatCounts = reports.reduce((result: any, report: any) => {
      const format = formatLabel(report.format)
      result[format] = (result[format] || 0) + 1
      return result
    }, {})
    const generatedReports = reports.filter((report: any) => report.type === 'generated').length
    const importedReports = reports.filter((report: any) => report.type === 'imported').length
    const metricsList = reports.map(reportMetrics)
    const importedWithResults = reports.filter((report: any) => report.type === 'imported' && reportMetrics(report).total > 0)
    const importedPassRates = importedWithResults
      .map((report: any) => reportMetrics(report).passRate)
      .filter((value: number) => Number.isFinite(value))
    const averageImportedPassRate = importedPassRates.length
      ? Math.round((importedPassRates.reduce((sum: number, value: number) => sum + value, 0) / importedPassRates.length) * 10) / 10
      : 0
    const mostUsedFormat = Object.entries(formatCounts).sort((a: any, b: any) => b[1] - a[1])[0]?.[0] || '-'
    const totalCases = metricsList.reduce((sum: number, item: any) => sum + item.total, 0)
    const executed = metricsList.reduce((sum: number, item: any) => sum + item.executed, 0)
    const failed = metricsList.reduce((sum: number, item: any) => sum + item.failed, 0)
    const openDefects = metricsList.reduce((sum: number, item: any) => sum + item.openDefects, 0)
    const passRate = executed
      ? Math.round((metricsList.reduce((sum: number, item: any) => sum + item.passed, 0) / executed) * 1000) / 10
      : 0
    return {
      totalReports: total,
      thisMonth,
      generatedReports,
      importedReports: analytics?.summary?.total_imported_reports || importedReports,
      averageImportedPassRate,
      mostUsedFormat,
      totalCases,
      executed,
      failed,
      passRate,
      openDefects,
      externalResults: analytics?.summary?.total_test_results || metricsList.reduce((sum: number, item: any) => sum + item.total, 0),
    }
  }, [reports, total, analytics])

  const handleDownload = async (report: any) => {
    if (report.type !== 'generated') return
    setDownloadingId(report.id)
    try {
      const blob = await reportsApi.downloadReport(report.id, report.format)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${report.name || report.id}.${report.format}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } finally {
      setDownloadingId('')
    }
  }

  const handlePreview = async (report: any) => {
    if (report.type === 'imported') {
      setPreviewLoadingId(report.id)
      try {
        const [detailResponse, resultsResponse] = await Promise.all([
          reportsApi.getImportedReportDetails(report.id),
          reportsApi.getImportedReportTestResults(report.id, { page: 1, page_size: 50 }),
        ])
        setPreviewReport({
          ...report,
          imported_detail: detailResponse?.data,
          imported_results: resultsResponse?.data || [],
          imported_total: resultsResponse?.total || 0,
        })
      } catch (err: any) {
        setError(err?.response?.data?.detail || err?.message || '加载导入报告详情失败')
      } finally {
        setPreviewLoadingId('')
      }
      return
    }
    if (report.type !== 'generated') return
    const format = String(report.format || '').toLowerCase()
    if (!['html', 'json', 'csv', 'txt'].includes(format)) {
      setPreviewReport({
        ...report,
        preview_content: '该格式不支持内联预览，请下载后查看。',
      })
      return
    }
    setPreviewLoadingId(report.id)
    try {
      const content = await reportsApi.previewReport(report.id, report.format)
      setPreviewReport({ ...report, preview_content: content })
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '预览报告失败')
    } finally {
      setPreviewLoadingId('')
    }
  }

  const handleImportReport = async () => {
    if (!importFile) {
      setError('请选择要导入的报告文件')
      return
    }
    setImporting(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', importFile)
      formData.append('source_type', importSourceType)
      if (importDescription.trim()) formData.append('description', importDescription.trim())
      await reportsApi.importReport(formData)
      setImportDialogOpen(false)
      setImportFile(null)
      setImportSourceType('custom')
      setImportDescription('')
      await loadReports()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '导入报告失败')
    } finally {
      setImporting(false)
    }
  }

  const confirmDeleteReport = async () => {
    if (!deleteReport) return
    try {
      if (deleteReport.type === 'generated') {
        await reportsApi.deleteGeneratedReport(deleteReport.id)
      } else {
        await reportsApi.deleteImportedReport(deleteReport.id)
      }
      setDeleteReport(null)
      await loadReports()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '删除报告失败')
    }
  }

  const buildGenerateLink = (type?: string) => {
    const params = new URLSearchParams()
    if (type) params.set('type', type)
    if (filters.test_plan_id !== 'all') params.set('test_plan_id', filters.test_plan_id)
    const query = params.toString()
    return `/test-manager/reports/generate${query ? `?${query}` : ''}`
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={loadReports} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            导入报告
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <BarChart3 className="mr-2 h-4 w-4" />
                快捷生成
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {reportTypeCards.map((item) => {
                const Icon = item.icon
                return (
                  <DropdownMenuItem key={item.type} onSelect={() => navigate(buildGenerateLink(item.type))}>
                    <Icon className={`mr-2 h-4 w-4 ${item.color}`} />
                    {item.title}
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuContent>
          </DropdownMenu>
          <Link to={buildGenerateLink()}>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              生成报告
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800">
          {error}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <SummaryTile label="报告总数" value={loading ? '-' : statistics.totalReports} />
        <SummaryTile label="用例总数" value={loading ? '-' : statistics.totalCases} />
        <SummaryTile label="已执行" value={loading ? '-' : statistics.executed} />
        <SummaryTile label="失败" value={loading ? '-' : statistics.failed} />
        <SummaryTile label="通过率" value={loading ? '-' : `${statistics.passRate}%`} />
        <SummaryTile label="未关闭缺陷" value={loading ? '-' : statistics.openDefects} />
      </div>

      <Card>
        <CardHeader className="gap-3 p-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="mr-2 text-lg">报告列表</CardTitle>
              <Badge variant="outline">共 {loading ? '-' : total} 条</Badge>
              <Badge variant="secondary">本月 {loading ? '-' : statistics.thisMonth}</Badge>
              <Badge variant="outline">生成 {loading ? '-' : statistics.generatedReports}</Badge>
              <Badge variant="outline">导入 {loading ? '-' : statistics.importedReports}</Badge>
              <Badge variant="outline">导入通过率 {loading ? '-' : `${statistics.averageImportedPassRate}%`}</Badge>
              <Badge variant="outline">常用 {loading ? '-' : statistics.mostUsedFormat}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(220px,1fr)_130px_150px_130px_190px] xl:w-[900px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                <Input
                  value={filters.search}
                  onChange={(event) => updateFilter('search', event.target.value)}
                  placeholder="搜索报告名称"
                  className="h-9 pl-10"
                />
              </div>
              <Select value={filters.report_type} onValueChange={(value) => updateFilter('report_type', value)}>
                <SelectTrigger className="h-9"><SelectValue placeholder="报告类型" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  {reportTypeCards.map((item) => (
                    <SelectItem key={item.type} value={item.type}>{item.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <select
                value={filters.source_filter}
                onChange={(event) => updateFilter('source_filter', event.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label="报告来源"
              >
                {sourceOptions.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
              <Select value={filters.format_filter} onValueChange={(value) => updateFilter('format_filter', value)}>
                <SelectTrigger className="h-9"><SelectValue placeholder="格式" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部格式</SelectItem>
                  <SelectItem value="html">HTML</SelectItem>
                  <SelectItem value="xlsx">Excel</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filters.test_plan_id} onValueChange={(value) => updateFilter('test_plan_id', value)}>
                <SelectTrigger className="h-9"><SelectValue placeholder="测试计划" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部测试计划</SelectItem>
                  {testPlans.map((plan: any) => (
                    <SelectItem key={plan.id} value={String(plan.id)}>{plan.plan_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[260px]">报告</TableHead>
                  <TableHead className="min-w-[150px]">范围</TableHead>
                  <TableHead className="min-w-[140px]">来源</TableHead>
                  <TableHead className="min-w-[220px]">执行摘要</TableHead>
                  <TableHead className="min-w-[140px]">缺陷</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="min-w-[150px]">时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report: any) => {
                  const metrics = reportMetrics(report)
                  return (
                    <TableRow key={`${report.type}-${report.id}-${report.format}`}>
                      <TableCell>
                        <div className="font-medium">{report.name}</div>
                        <div className="mt-1 flex flex-wrap gap-1 text-xs text-muted-foreground">
                          <span>{report.id}</span>
                          {report.summary?.file_name && report.summary.file_name !== report.name && <span>· {report.summary.file_name}</span>}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {report.type === 'imported' ? '外部测试报告' : reportTypeLabel(report.summary?.business_report_type || report.summary?.report_type)}
                        </Badge>
                        {report.summary?.test_plan_id ? (
                          <div className="mt-1 text-xs text-muted-foreground">测试计划 #{report.summary.test_plan_id}</div>
                        ) : (
                          <div className="mt-1 text-xs text-muted-foreground">未关联测试计划</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          <Badge variant={report.type === 'generated' ? 'default' : 'secondary'}>
                            {report.type === 'generated' ? '平台生成' : '外部导入'}
                          </Badge>
                          <Badge variant="outline">{report.type === 'imported' ? sourceTypeLabel(report.summary?.source_type) : formatLabel(report.format)}</Badge>
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">{formatLabel(report.format)} · {sizeLabel(report.size)}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <span className="font-medium">{metrics.executed || 0}</span>
                          <span className="text-muted-foreground"> / {metrics.total || 0} 已执行</span>
                        </div>
                        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full bg-emerald-500"
                            style={{ width: `${Math.max(0, Math.min(100, metrics.passRate))}%` }}
                          />
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          通过 {metrics.passed} · 失败 {metrics.failed} · 阻塞/跳过 {metrics.blocked + metrics.skipped}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">总数 {metrics.totalDefects}</div>
                        <div className="mt-1 text-xs text-muted-foreground">未关闭 {metrics.openDefects} · 高风险 {metrics.highRiskDefects}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={String(report.status).toLowerCase() === 'failed' ? 'destructive' : 'outline'}>
                          {statusLabel(report.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(report.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            title="预览"
                            disabled={previewLoadingId === report.id}
                            onClick={() => handlePreview(report)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            title="下载"
                            disabled={report.type !== 'generated' || downloadingId === report.id}
                            onClick={() => handleDownload(report)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            title="删除"
                            onClick={() => setDeleteReport(report)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          {!loading && reports.length === 0 && (
            <div className="py-8 text-center text-gray-500 dark:text-gray-400">暂无报告数据</div>
          )}
        </CardContent>
      </Card>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>导入外部测试报告</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium">报告来源</label>
              <Select value={importSourceType} onValueChange={setImportSourceType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {importSourceOptions.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">报告文件</label>
              <Input
                type="file"
                accept=".html,.htm,.xml,.json,.pdf,.docx,.xlsx,.csv,.txt"
                onChange={(event) => setImportFile(event.target.files?.[0] || null)}
              />
              <p className="mt-1 text-xs text-muted-foreground">支持 Allure/JUnit/TestNG、HTML/XML/PDF/Word/Excel/JSON/CSV/TXT 等外部报告解析。</p>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">导入说明</label>
              <Input
                value={importDescription}
                onChange={(event) => setImportDescription(event.target.value)}
                placeholder="可选；说明报告来源、测试轮次或执行环境"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>取消</Button>
            <Button onClick={handleImportReport} disabled={importing}>{importing ? '导入中...' : '导入'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(previewReport)} onOpenChange={(open) => !open && setPreviewReport(null)}>
        <DialogContent className="w-[92vw] max-w-[1600px] max-h-[92vh] overflow-hidden flex flex-col p-0">
          {previewReport && (() => {
            const m = reportMetrics(previewReport)
            const isImported = previewReport.type === 'imported'
            const format = String(previewReport.format || '').toLowerCase()
            const isGeneratedHtml = !isImported && format === 'html'
            const isGeneratedText = !isImported && ['json', 'csv', 'txt'].includes(format)
            const previewContent = previewReport.preview_content
            const qualityColor = m.passRate >= 90 ? '#10b981' : m.passRate >= 70 ? '#f59e0b' : '#ef4444'
            const qualityLabel = m.passRate >= 90 ? '优秀' : m.passRate >= 70 ? '良好' : '需改进'
            const qualityBg = m.passRate >= 90 ? 'bg-emerald-50 dark:bg-emerald-900/20' : m.passRate >= 70 ? 'bg-amber-50 dark:bg-amber-900/20' : 'bg-rose-50 dark:bg-rose-900/20'
            const qualityBorder = m.passRate >= 90 ? 'border-emerald-200 dark:border-emerald-800' : m.passRate >= 70 ? 'border-amber-200 dark:border-amber-800' : 'border-rose-200 dark:border-rose-800'
            const ringCircumference = 2 * Math.PI * 42
            const ringOffset = ringCircumference - (Math.max(0, Math.min(100, m.passRate)) / 100) * ringCircumference
            const isLoading = previewLoadingId === previewReport.id
            const headerAccent = isImported ? 'from-indigo-500/10 via-transparent to-transparent' : 'from-emerald-500/10 via-transparent to-transparent'
            return (
              <>
                <DialogHeader className={`flex-shrink-0 border-b bg-gradient-to-r ${headerAccent} px-6 py-4`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <DialogTitle className="truncate text-lg">{previewReport.name}</DialogTitle>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
                        <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 font-mono">
                          <FileText className="h-3 w-3" />
                          {previewReport.id?.slice(0, 12)}
                        </span>
                        <Badge variant={isImported ? 'secondary' : 'default'}>
                          {isImported ? '外部导入' : '平台生成'}
                        </Badge>
                        <Badge variant="outline">{formatLabel(previewReport.format)}</Badge>
                        {isImported && (
                          <Badge variant="outline">
                            {sourceTypeLabel(previewReport.imported_detail?.source_type || previewReport.summary?.source_type)}
                          </Badge>
                        )}
                        <span className="text-muted-foreground">{sizeLabel(previewReport.size)}</span>
                        <span className="text-muted-foreground">·</span>
                        <span className="text-muted-foreground">{formatDate(previewReport.created_at)}</span>
                      </div>
                    </div>
                    {!isImported && (
                      <Button size="sm" onClick={() => handleDownload(previewReport)} disabled={downloadingId === previewReport.id}>
                        <Download className="mr-2 h-4 w-4" />
                        {downloadingId === previewReport.id ? '下载中...' : '下载'}
                      </Button>
                    )}
                  </div>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto">
                  {isImported ? (
                    <div className="space-y-5 p-6">
                      {/* 顶部：通过率环 + 关键指标 */}
                      <div className="grid gap-4 md:grid-cols-[220px_1fr]">
                        <div className={`flex flex-col items-center justify-center rounded-xl border ${qualityBorder} ${qualityBg} p-5`}>
                          <div className="relative h-32 w-32">
                            <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
                              <circle cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="8" fill="none" className="text-muted/40" />
                              <circle
                                cx="50" cy="50" r="42"
                                stroke={qualityColor}
                                strokeWidth="8"
                                fill="none"
                                strokeLinecap="round"
                                strokeDasharray={ringCircumference}
                                strokeDashoffset={ringOffset}
                                style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                              />
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                              <div className="text-3xl font-bold tabular-nums" style={{ color: qualityColor }}>{m.passRate.toFixed(1)}%</div>
                              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">通过率</div>
                            </div>
                          </div>
                          <div className={`mt-3 inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium`} style={{ color: qualityColor, background: `${qualityColor}20` }}>
                            <Shield className="h-3 w-3" />
                            质量等级：{qualityLabel}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                          <MetricCard icon={Layers} label="测试总数" value={m.total || (previewReport.imported_total ?? 0)} color="#6366f1" subtle />
                          <MetricCard icon={CheckCircle2} label="通过" value={m.passed} color="#10b981" />
                          <MetricCard icon={XCircle} label="失败" value={m.failed} color="#ef4444" />
                          <MetricCard icon={Clock} label="跳过/阻塞" value={m.skipped + m.blocked} color="#f59e0b" subtle />
                          <MetricCard icon={BarChart3} label="已执行" value={m.executed} color="#3b82f6" subtle />
                          <MetricCard icon={Shield} label="未关闭缺陷" value={m.openDefects} color="#a855f7" subtle />
                        </div>
                      </div>

                      {/* 通过率条 */}
                      <div className="rounded-lg border bg-card p-4">
                        <div className="mb-2 flex items-center justify-between text-xs">
                          <span className="font-medium text-foreground">执行结果分布</span>
                          <span className="text-muted-foreground">通过 {m.passed} · 失败 {m.failed} · 跳过/阻塞 {m.skipped + m.blocked}</span>
                        </div>
                        <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
                          {m.total > 0 && (
                            <>
                              <div className="h-full bg-emerald-500 transition-all" style={{ width: `${(m.passed / m.total) * 100}%` }} title={`通过 ${m.passed}`} />
                              <div className="h-full bg-rose-500 transition-all" style={{ width: `${(m.failed / m.total) * 100}%` }} title={`失败 ${m.failed}`} />
                              <div className="h-full bg-amber-400 transition-all" style={{ width: `${((m.skipped + m.blocked) / m.total) * 100}%` }} title={`跳过/阻塞 ${m.skipped + m.blocked}`} />
                            </>
                          )}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
                          <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />通过 {m.total ? ((m.passed / m.total) * 100).toFixed(1) : 0}%</span>
                          <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-rose-500" />失败 {m.total ? ((m.failed / m.total) * 100).toFixed(1) : 0}%</span>
                          <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />跳过/阻塞 {m.total ? (((m.skipped + m.blocked) / m.total) * 100).toFixed(1) : 0}%</span>
                        </div>
                      </div>

                      {/* 测试结果表 */}
                      {(previewReport.imported_results || []).length > 0 ? (
                        <div className="rounded-lg border overflow-hidden">
                          <div className="max-h-[40vh] overflow-auto">
                            <Table>
                              <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur">
                                <TableRow>
                                  <TableHead className="w-[40%]">测试名称</TableHead>
                                  <TableHead className="w-[90px]">状态</TableHead>
                                  <TableHead className="w-[90px]">耗时</TableHead>
                                  <TableHead>套件/类</TableHead>
                                  <TableHead>错误信息</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {(previewReport.imported_results || []).map((item: any, index: number) => {
                                  const st = String(item.status || '').toUpperCase()
                                  const statusStyle = st === 'PASSED'
                                    ? { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500' }
                                    : st === 'FAILED'
                                    ? { bg: 'bg-rose-50 dark:bg-rose-900/20', text: 'text-rose-700 dark:text-rose-400', dot: 'bg-rose-500' }
                                    : { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-400', dot: 'bg-amber-500' }
                                  return (
                                    <TableRow key={`${item.test_name}-${index}`} className={st === 'FAILED' ? 'bg-rose-50/30 dark:bg-rose-900/5' : ''}>
                                      <TableCell className="font-medium">{item.test_name || '-'}</TableCell>
                                      <TableCell>
                                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                                          <span className={`h-1.5 w-1.5 rounded-full ${statusStyle.dot}`} />
                                          {st === 'PASSED' ? '通过' : st === 'FAILED' ? '失败' : st === 'SKIPPED' ? '跳过' : item.status || '-'}
                                        </span>
                                      </TableCell>
                                      <TableCell className="font-mono text-xs text-muted-foreground">
                                        {item.duration != null ? (Number(item.duration) < 1 ? `${(Number(item.duration) * 1000).toFixed(0)}ms` : `${Number(item.duration).toFixed(2)}s`) : '-'}
                                      </TableCell>
                                      <TableCell className="text-xs text-muted-foreground">{item.test_suite || item.test_class || '-'}</TableCell>
                                      <TableCell className="max-w-[260px] truncate text-xs text-rose-600 dark:text-rose-400" title={item.error_message || ''}>{item.error_message || '-'}</TableCell>
                                    </TableRow>
                                  )
                                })}
                              </TableBody>
                            </Table>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">该导入报告没有解析出测试结果。</div>
                      )}
                    </div>
                  ) : isGeneratedHtml ? (
                    <div className="flex h-full w-full flex-col bg-white">
                      {isLoading ? (
                        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
                          <RefreshCw className="h-6 w-6 animate-spin" />
                          <span className="text-sm">正在加载报告内容...</span>
                        </div>
                      ) : previewContent ? (
                        <iframe
                          title="报告预览"
                          className="h-full w-full border-0 bg-white"
                          style={{ minHeight: '80vh' }}
                          srcDoc={previewContent}
                        />
                      ) : (
                        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-16 text-center text-muted-foreground">
                          <FileText className="h-12 w-12 opacity-40" />
                          <div className="text-sm font-medium">报告内容加载失败或为空</div>
                          <div className="text-xs">请尝试下载后在本地浏览器中查看完整报告</div>
                          <Button size="sm" className="mt-3" onClick={() => handleDownload(previewReport)}>
                            <Download className="mr-2 h-4 w-4" />下载报告
                          </Button>
                        </div>
                      )}
                    </div>
                  ) : isGeneratedText ? (
                    <div className="p-6">
                      {isLoading ? (
                        <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
                          <RefreshCw className="h-6 w-6 animate-spin" />
                          <span className="text-sm">正在加载报告内容...</span>
                        </div>
                      ) : previewContent ? (
                        <pre className="max-h-[75vh] overflow-auto rounded-lg border bg-gray-950 p-4 text-sm text-gray-100 font-mono">
                          {previewContent}
                        </pre>
                      ) : (
                        <div className="rounded-lg border border-dashed p-16 text-center text-sm text-muted-foreground">
                          报告内容加载失败或为空，请稍后重试或下载后查看。
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center gap-3 p-20 text-center text-muted-foreground">
                      <FileText className="h-14 w-14 opacity-40" />
                      <div className="text-sm font-medium">该报告格式（{formatLabel(previewReport.format)}）暂不支持在线预览</div>
                      <div className="text-xs">请点击下载按钮，在本地应用中查看完整报告</div>
                    </div>
                  )}
                </div>

                <DialogFooter className="flex-shrink-0 border-t bg-muted/30 px-6 py-3">
                  <Button variant="outline" onClick={() => setPreviewReport(null)}>关闭</Button>
                  {isImported && (
                    <Button onClick={() => handleDownload(previewReport)} disabled={downloadingId === previewReport.id}>
                      <Download className="mr-2 h-4 w-4" />
                      {downloadingId === previewReport.id ? '下载中...' : '下载'}
                    </Button>
                  )}
                </DialogFooter>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteReport)}
        title="删除报告"
        description={`确认删除报告“${deleteReport?.name || ''}”？${deleteReport?.type === 'generated' ? '生成报告的所有格式文件也会一并删除。' : '导入报告的解析结果和原始记录会一并删除。'}`}
        confirmText="删除"
        cancelText="取消"
        variant="destructive"
        onCancel={() => setDeleteReport(null)}
        onConfirm={confirmDeleteReport}
      />
    </div>
  )
}

export default ReportDashboard

const SummaryTile = ({ label, value }: { label: string; value: any }) => (
  <div className="rounded-md border bg-muted/20 p-3">
    <div className="text-xs text-muted-foreground">{label}</div>
    <div className="mt-1 truncate text-lg font-semibold">{value}</div>
  </div>
)

const MetricCard = ({ icon: Icon, label, value, color, subtle }: { icon: any; label: string; value: any; color: string; subtle?: boolean }) => (
  <div className={`group relative overflow-hidden rounded-lg border bg-card p-3 transition hover:shadow-md`}>
    <div className="absolute inset-y-0 left-0 w-1" style={{ background: color }} />
    <div className="flex items-start gap-3 pl-2">
      <div
        className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg"
        style={{ background: `${color}${subtle ? '15' : '20'}`, color }}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="mt-0.5 text-2xl font-bold tabular-nums text-foreground">{value ?? 0}</div>
      </div>
    </div>
  </div>
)
