// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, Calendar, Download, FileText, Plus, RefreshCw, Search } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
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
  const [reports, setReports] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [downloadingId, setDownloadingId] = useState('')
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">测试报告</h1>
          <p className="text-gray-600">生成、查看和下载测试报告</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadReports} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Link to={`/test-manager/reports/generate${filters.test_plan_id !== 'all' ? `?test_plan_id=${filters.test_plan_id}` : ''}`}>
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

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">报告总数</p>
                <p className="text-2xl font-bold">{loading ? '-' : statistics.totalReports}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">本月生成</p>
                <p className="text-2xl font-bold">{loading ? '-' : statistics.thisMonth}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">导入报告</p>
                <p className="text-2xl font-bold">{loading ? '-' : statistics.importedReports}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Download className="h-5 w-5 text-orange-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">常用格式</p>
                <p className="text-2xl font-bold">{loading ? '-' : statistics.mostUsedFormat}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_180px_160px_220px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                value={filters.search}
                onChange={(event) => updateFilter('search', event.target.value)}
                placeholder="搜索报告名称"
                className="pl-10"
              />
            </div>
            <Select value={filters.report_type} onValueChange={(value) => updateFilter('report_type', value)}>
              <SelectTrigger><SelectValue placeholder="报告类型" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                {reportTypeCards.map((item) => (
                  <SelectItem key={item.type} value={item.type}>{item.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.format_filter} onValueChange={(value) => updateFilter('format_filter', value)}>
              <SelectTrigger><SelectValue placeholder="格式" /></SelectTrigger>
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
              <SelectTrigger><SelectValue placeholder="测试计划" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部测试计划</SelectItem>
                {testPlans.map((plan: any) => (
                  <SelectItem key={plan.id} value={String(plan.id)}>{plan.plan_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {reportTypeCards.map((item) => {
          const Icon = item.icon
          return (
            <Link key={item.type} to={`/test-manager/reports/generate?type=${item.type}${filters.test_plan_id !== 'all' ? `&test_plan_id=${filters.test_plan_id}` : ''}`}>
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="pt-6">
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-8 w-8 ${item.color}`} />
                    <div>
                      <h3 className="font-semibold">{item.title}</h3>
                      <p className="text-sm text-gray-600">{item.description}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>最近的报告</CardTitle>
        </CardHeader>
        <CardContent>
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
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={report.type !== 'generated' || downloadingId === report.id}
                        onClick={() => handleDownload(report)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
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
    </div>
  )
}

export default ReportDashboard
