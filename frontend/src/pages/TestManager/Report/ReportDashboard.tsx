// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BarChart3, Download, Eye, FileText, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
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
  { type: 'execution', title: '执行报告', description: '汇总测试执行结果和通过率', icon: FileText, color: 'text-blue-500' },
  { type: 'defect', title: '缺陷报告', description: '汇总缺陷数量、状态和严重程度', icon: BarChart3, color: 'text-red-500' },
  { type: 'coverage', title: '覆盖率报告', description: '汇总需求和测试覆盖情况', icon: BarChart3, color: 'text-green-500' },
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
  const [testPlans, setTestPlans] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    report_type: 'all',
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
    const mostUsedFormat = Object.entries(formatCounts).sort((a: any, b: any) => b[1] - a[1])[0]?.[0] || '-'
    return {
      totalReports: total,
      thisMonth,
      importedReports: analytics?.summary?.total_imported_reports || 0,
      mostUsedFormat,
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
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card>
        <CardHeader className="gap-3 p-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="mr-2 text-lg">报告列表</CardTitle>
              <Badge variant="outline">共 {loading ? '-' : total} 条</Badge>
              <Badge variant="secondary">本月 {loading ? '-' : statistics.thisMonth}</Badge>
              <Badge variant="outline">导入 {loading ? '-' : statistics.importedReports}</Badge>
              <Badge variant="outline">常用 {loading ? '-' : statistics.mostUsedFormat}</Badge>
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(220px,1fr)_150px_130px_190px] xl:w-[760px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
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
                  <TableHead>报告名称</TableHead>
                  <TableHead>业务类型</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>格式</TableHead>
                  <TableHead>大小</TableHead>
                  <TableHead>生成时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report: any) => (
                  <TableRow key={`${report.type}-${report.id}-${report.format}`}>
                    <TableCell>
                      <div className="font-medium">{report.name}</div>
                      <div className="text-xs text-gray-500">{report.id}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{reportTypeLabel(report.summary?.business_report_type || report.summary?.report_type)}</Badge>
                      {report.summary?.test_plan_id && (
                        <div className="mt-1 text-xs text-gray-500">计划 #{report.summary.test_plan_id}</div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={report.type === 'generated' ? 'default' : 'secondary'}>
                        {report.type === 'generated' ? '生成' : '导入'}
                      </Badge>
                    </TableCell>
                    <TableCell><Badge variant="outline">{formatLabel(report.format)}</Badge></TableCell>
                    <TableCell>{sizeLabel(report.size)}</TableCell>
                    <TableCell>{formatDate(report.created_at)}</TableCell>
                    <TableCell>{report.status || '-'}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          title="预览"
                          disabled={report.type !== 'generated' || previewLoadingId === report.id}
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
                ))}
              </TableBody>
            </Table>
          </div>

          {!loading && reports.length === 0 && (
            <div className="py-8 text-center text-gray-500">暂无报告数据</div>
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(previewReport)} onOpenChange={(open) => !open && setPreviewReport(null)}>
        <DialogContent className="max-w-5xl">
          {previewReport && (
            <div className="space-y-4">
              <DialogHeader>
                <DialogTitle>{previewReport.name}</DialogTitle>
              </DialogHeader>
              {String(previewReport.format || '').toLowerCase() === 'html' ? (
                <iframe
                  title="报告预览"
                  className="h-[70vh] w-full rounded-md border bg-white"
                  srcDoc={previewReport.preview_content}
                />
              ) : (
                <pre className="max-h-[70vh] overflow-auto rounded-md border bg-gray-950 p-4 text-sm text-gray-100">
                  {previewReport.preview_content}
                </pre>
              )}
              <DialogFooter>
                <Button variant="outline" onClick={() => setPreviewReport(null)}>关闭</Button>
                <Button onClick={() => handleDownload(previewReport)}>下载</Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteReport)}
        title="删除报告"
        description={`确认删除报告“${deleteReport?.name || ''}”？生成报告的所有格式文件也会一并删除。`}
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
