// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, CheckCircle, RefreshCw, Scan, Settings, Shield } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Checkbox } from '../../../components/ui/Checkbox'
import { Input } from '../../../components/ui/Input'
import { Progress } from '../../../components/ui/Progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import ProjectService from '../../../services/projectService'
import { apiClient } from '../../../services/api/client'
import { formatDate } from '../../../utils/date'

const testTypeLabels: Record<string, string> = {
  web_scan: 'Web 安全扫描',
  api_scan: 'API 安全扫描',
  header_scan: '安全头检查',
  tls_scan: 'TLS 检查',
}

const scanDepthLabels: Record<string, string> = {
  LIGHT: '轻度扫描',
  MEDIUM: '中度扫描',
  DEEP: '深度扫描',
}

const categoryOptions = [
  { value: 'SECURITY_HEADERS', label: '安全响应头' },
  { value: 'SSL_TLS', label: 'SSL/TLS' },
  { value: 'SQL_INJECTION', label: 'SQL 注入' },
  { value: 'XSS', label: 'XSS 跨站脚本' },
  { value: 'CSRF', label: 'CSRF' },
  { value: 'AUTHENTICATION', label: '身份认证' },
  { value: 'AUTHORIZATION', label: '权限控制' },
  { value: 'DATA_EXPOSURE', label: '数据暴露' },
]

const emptyForm = {
  test_name: '',
  project_id: '',
  test_type: 'web_scan',
  target_url: 'https://example.com',
  scan_depth: 'MEDIUM',
  include_authenticated: false,
  vulnerability_categories: ['SECURITY_HEADERS', 'SSL_TLS'],
}

const SecurityTest: React.FC = () => {
  const [projects, setProjects] = useState([])
  const [tests, setTests] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [lastExecution, setLastExecution] = useState(null)
  const [lastResult, setLastResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [projectResponse, testResponse] = await Promise.all([
        ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
        apiClient.get('/api/v1/security-tests/?page=1&page_size=20'),
      ])
      const nextProjects = projectResponse.data || []
      setProjects(nextProjects)
      setTests(testResponse.data?.data || [])
      setForm((current) => ({
        ...current,
        project_id: current.project_id || String(nextProjects[0]?.id || ''),
      }))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载安全测试数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const selectedCategories = form.vulnerability_categories

  const summary = useMemo(() => {
    const fallback = { total: 0, critical: 0, high: 0, medium: 0, low: 0 }
    return lastResult?.vulnerability_summary || fallback
  }, [lastResult])

  const vulnerabilities = lastResult?.vulnerabilities || []
  const securityScore = typeof lastResult?.security_score === 'number' ? Math.round(lastResult.security_score) : null

  const toggleCategory = (value: string, checked: boolean) => {
    setForm((current) => ({
      ...current,
      vulnerability_categories: checked
        ? Array.from(new Set([...current.vulnerability_categories, value]))
        : current.vulnerability_categories.filter((item) => item !== value),
    }))
  }

  const buildPayload = () => ({
    test_name: form.test_name.trim(),
    description: '通过安全测试页面创建',
    project_id: Number(form.project_id),
    test_type: form.test_type,
    target_url: form.target_url.trim(),
    scan_scope: {
      urls: [form.target_url.trim()],
      include_authenticated: form.include_authenticated,
    },
    security_policies: ['basic_web_security'],
    vulnerability_categories: selectedCategories,
    scan_depth: form.scan_depth,
    authentication_config: form.include_authenticated ? { enabled: true } : null,
    exclusion_rules: [],
  })

  const executeTest = async (testId: number) => {
    const executeResponse = await apiClient.post('/api/v1/security-tests/execute', {
      test_id: testId,
      scan_tools: ['basic_header_probe'],
      execution_config: { source: 'web-ui' },
    })
    const execution = executeResponse.data?.data
    setLastExecution(execution)

    if (execution?.execution_id) {
      const resultResponse = await apiClient.get(`/api/v1/security-tests/executions/${execution.execution_id}/results`)
      setLastResult(resultResponse.data?.data)
    }
  }

  const createAndRun = async () => {
    if (!form.test_name.trim()) {
      setError('请填写测试名称')
      return
    }
    if (!form.project_id) {
      setError('请选择所属项目')
      return
    }
    if (!form.target_url.trim()) {
      setError('请填写目标 URL')
      return
    }

    setScanning(true)
    setError('')
    try {
      const createResponse = await apiClient.post('/api/v1/security-tests/', buildPayload())
      const test = createResponse.data?.data
      await executeTest(test.id)
      setForm((current) => ({ ...emptyForm, project_id: current.project_id }))
      await loadData()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '安全扫描失败')
    } finally {
      setScanning(false)
    }
  }

  const runExisting = async (testId: number) => {
    setScanning(true)
    setError('')
    try {
      await executeTest(testId)
      await loadData()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '安全扫描失败')
    } finally {
      setScanning(false)
    }
  }

  const recommendations = lastResult?.recommendations?.length
    ? lastResult.recommendations
    : ['执行一次安全扫描后，这里会显示基于结果生成的修复建议。']

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回测试管理
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">安全测试</h1>
          </div>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading || scanning}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {lastExecution && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>最近扫描结果</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-sm">
                <span>扫描进度</span>
                <span>{lastExecution.progress_percentage ?? 0}%</span>
              </div>
              <Progress value={lastExecution.progress_percentage ?? 0} className="h-3" />
            </div>
            <div className="grid grid-cols-2 gap-4 text-center md:grid-cols-6">
              <Metric label="状态" value={statusLabel(lastExecution.status)} />
              <Metric label="安全评分" value={securityScore ?? '-'} />
              <Metric label="发现漏洞" value={lastExecution.vulnerabilities_found ?? 0} />
              <Metric label="严重" value={lastExecution.critical_vulnerabilities ?? 0} tone="red" />
              <Metric label="高危" value={lastExecution.high_vulnerabilities ?? 0} tone="orange" />
              <Metric label="已扫 URL" value={lastExecution.scanned_urls ?? 0} />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Tabs defaultValue="config" className="space-y-4">
            <TabsList>
              <TabsTrigger value="config">扫描配置</TabsTrigger>
              <TabsTrigger value="vulnerabilities">漏洞列表</TabsTrigger>
              <TabsTrigger value="history">扫描历史</TabsTrigger>
            </TabsList>

            <TabsContent value="config">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Settings className="h-5 w-5" />
                    <span>新建安全扫描</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="测试名称">
                      <Input value={form.test_name} onChange={(event) => setForm({ ...form, test_name: event.target.value })} />
                    </Field>
                    <Field label="所属项目">
                      <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.project_id} onChange={(event) => setForm({ ...form, project_id: event.target.value })}>
                        <option value="">请选择项目</option>
                        {projects.map((project) => (
                          <option key={project.id} value={String(project.id)}>{project.project_name || project.name || `项目 #${project.id}`}</option>
                        ))}
                      </select>
                    </Field>
                    <Field label="测试类型">
                      <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.test_type} onChange={(event) => setForm({ ...form, test_type: event.target.value })}>
                        {Object.entries(testTypeLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </Field>
                    <Field label="扫描深度">
                      <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.scan_depth} onChange={(event) => setForm({ ...form, scan_depth: event.target.value })}>
                        {Object.entries(scanDepthLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </Field>
                  </div>

                  <Field label="目标 URL">
                    <Input value={form.target_url} onChange={(event) => setForm({ ...form, target_url: event.target.value })} />
                  </Field>

                  <div>
                    <p className="mb-3 text-sm font-medium">漏洞类别</p>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                      {categoryOptions.map((category) => (
                        <label key={category.value} className="flex items-center space-x-2 rounded-md border p-3 text-sm">
                          <Checkbox checked={selectedCategories.includes(category.value)} onCheckedChange={(checked) => toggleCategory(category.value, !!checked)} />
                          <span>{category.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <label className="flex items-center space-x-2 text-sm">
                    <Checkbox checked={form.include_authenticated} onCheckedChange={(checked) => setForm({ ...form, include_authenticated: !!checked })} />
                    <span>包含认证后页面扫描</span>
                  </label>

                  <Button onClick={createAndRun} disabled={scanning} className="w-full md:w-auto">
                    <Scan className="mr-2 h-4 w-4" />
                    {scanning ? '扫描中...' : '保存并扫描'}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="vulnerabilities">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <AlertTriangle className="h-5 w-5" />
                    <span>发现的漏洞</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>漏洞标题</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>严重程度</TableHead>
                        <TableHead>影响 URL</TableHead>
                        <TableHead>状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {vulnerabilities.map((vulnerability: any) => (
                        <TableRow key={vulnerability.vulnerability_id}>
                          <TableCell>
                            <div className="font-medium">{vulnerability.title}</div>
                            <div className="mt-1 max-w-[360px] text-xs text-gray-500">{vulnerability.recommendation}</div>
                          </TableCell>
                          <TableCell><Badge variant="outline">{vulnerabilityTypeLabel(vulnerability.vulnerability_type)}</Badge></TableCell>
                          <TableCell>{severityBadge(vulnerability.severity)}</TableCell>
                          <TableCell className="max-w-[260px] truncate font-mono text-sm">{vulnerability.affected_url}</TableCell>
                          <TableCell>{vulnerability.status === 'OPEN' ? '待处理' : vulnerability.status}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {vulnerabilities.length === 0 && <div className="py-8 text-center text-gray-500">暂无扫描漏洞结果</div>}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history">
              <Card>
                <CardHeader>
                  <CardTitle>扫描历史</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>扫描名称</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>目标 URL</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>更新时间</TableHead>
                        <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tests.map((test: any) => (
                        <TableRow key={test.id}>
                          <TableCell className="font-medium">{test.test_name}</TableCell>
                          <TableCell><Badge variant="outline">{testTypeLabels[test.test_type] || test.test_type}</Badge></TableCell>
                          <TableCell className="max-w-[260px] truncate font-mono text-sm">{test.target_url}</TableCell>
                          <TableCell>{statusBadge(test.status)}</TableCell>
                          <TableCell>{formatDate(test.updated_at || test.created_at)}</TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" disabled={scanning} onClick={() => runExisting(test.id)}>重新扫描</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {!loading && tests.length === 0 && <div className="py-8 text-center text-gray-500">暂无安全扫描</div>}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>安全概览</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">安全评分</span>
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-20 rounded-full bg-gray-200">
                    <div className={scoreColor(securityScore)} style={{ width: `${securityScore ?? 0}%` }} />
                  </div>
                  <span className="text-sm font-medium">{securityScore === null ? '-' : `${securityScore}/100`}</span>
                </div>
              </div>
              <SummaryRow label="严重漏洞" value={summary.critical} variant="destructive" />
              <SummaryRow label="高危漏洞" value={summary.high} variant="destructive" />
              <SummaryRow label="中危漏洞" value={summary.medium} variant="default" />
              <SummaryRow label="低危漏洞" value={summary.low} variant="secondary" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>安全建议</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {recommendations.map((recommendation: string, index: number) => (
                <div key={`${recommendation}-${index}`} className="flex items-start space-x-3 rounded-md border bg-gray-50 p-3">
                  {summary.total > 0 ? <AlertTriangle className="mt-0.5 h-5 w-5 text-orange-500" /> : <CheckCircle className="mt-0.5 h-5 w-5 text-green-500" />}
                  <p className="text-sm text-gray-700">{recommendation}</p>
                </div>
              ))}
            </CardContent>
          </Card>
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

const Metric = ({ label, value, tone = 'blue' }: { label: string; value: React.ReactNode; tone?: string }) => {
  const color = tone === 'red' ? 'text-red-600' : tone === 'orange' ? 'text-orange-600' : 'text-blue-600'
  return (
    <div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  )
}

const SummaryRow = ({ label, value, variant }: { label: string; value: number; variant: any }) => (
  <div className="flex justify-between">
    <span className="text-sm">{label}</span>
    <Badge variant={value > 0 ? variant : 'secondary'}>{value}</Badge>
  </div>
)

const statusLabel = (status: string) => {
  const labels: Record<string, string> = {
    CREATED: '已创建',
    RUNNING: '扫描中',
    COMPLETED: '已完成',
    FAILED: '失败',
    STOPPED: '已停止',
  }
  return labels[status] || status || '-'
}

const statusBadge = (status: string) => {
  const variant = status === 'FAILED' ? 'destructive' : status === 'COMPLETED' ? 'default' : 'secondary'
  return <Badge variant={variant}>{statusLabel(status)}</Badge>
}

const severityBadge = (severity: string) => {
  const normalized = String(severity || '').toUpperCase()
  const labels: Record<string, string> = { CRITICAL: '严重', HIGH: '高危', MEDIUM: '中危', LOW: '低危' }
  const variant = normalized === 'CRITICAL' || normalized === 'HIGH' ? 'destructive' : normalized === 'MEDIUM' ? 'default' : 'secondary'
  return <Badge variant={variant}>{labels[normalized] || normalized}</Badge>
}

const vulnerabilityTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    SECURITY_HEADERS: '安全响应头',
    SSL_TLS: 'SSL/TLS',
    CONNECTIVITY: '连通性',
    SQL_INJECTION: 'SQL 注入',
    XSS: 'XSS',
    CSRF: 'CSRF',
    AUTHENTICATION: '身份认证',
    AUTHORIZATION: '权限控制',
    DATA_EXPOSURE: '数据暴露',
  }
  return labels[type] || type
}

const scoreColor = (score: number | null) => {
  const color = score === null ? 'bg-gray-300' : score >= 85 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
  return `h-2 rounded-full ${color}`
}

export default SecurityTest
