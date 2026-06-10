// @ts-nocheck
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Play, RefreshCw, Settings, TrendingUp, Zap } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import ProjectService from '../../../services/projectService'
import { apiClient } from '../../../services/api/client'
import { formatDate } from '../../../utils/date'

const testTypeLabels: Record<string, string> = {
  load: '负载测试',
  stress: '压力测试',
  spike: '峰值测试',
  volume: '容量测试',
  endurance: '稳定性测试',
}

const emptyForm = {
  test_name: '',
  project_id: '',
  test_type: 'load',
  target_url: 'https://example.com',
  concurrent_users: 5,
  test_duration: 30,
  ramp_up_time: 10,
}

const PerformanceTest: React.FC = () => {
  const [projects, setProjects] = useState([])
  const [tests, setTests] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [lastExecution, setLastExecution] = useState(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [projectResponse, testResponse] = await Promise.all([
        ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
        apiClient.get('/api/v1/performance-tests/?page=1&page_size=20'),
      ])
      const nextProjects = projectResponse.data || []
      setProjects(nextProjects)
      setTests(testResponse.data?.data || [])
      setForm((current) => ({
        ...current,
        project_id: current.project_id || String(nextProjects[0]?.id || ''),
      }))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载性能测试数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const buildPayload = () => ({
    test_name: form.test_name.trim(),
    description: '通过性能测试页面创建',
    project_id: Number(form.project_id),
    test_type: form.test_type,
    target_url: form.target_url.trim(),
    test_scenario: { steps: [{ name: '访问目标地址', method: 'GET', url: form.target_url.trim() }] },
    load_model: {
      concurrent_users: Number(form.concurrent_users),
      ramp_up_time: Number(form.ramp_up_time),
      duration: Number(form.test_duration),
    },
    performance_criteria: { max_response_time: 1000, max_error_rate: 1 },
    test_duration: Number(form.test_duration),
    concurrent_users: Number(form.concurrent_users),
    ramp_up_time: Number(form.ramp_up_time),
    environment_config: { source: 'web-ui' },
  })

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

    setRunning(true)
    setError('')
    try {
      const createResponse = await apiClient.post('/api/v1/performance-tests/', buildPayload())
      const test = createResponse.data?.data
      const executeResponse = await apiClient.post('/api/v1/performance-tests/execute', { test_id: test.id })
      setLastExecution(executeResponse.data?.data)
      setForm((current) => ({ ...emptyForm, project_id: current.project_id }))
      await loadData()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '性能测试执行失败')
    } finally {
      setRunning(false)
    }
  }

  const runExisting = async (testId: number) => {
    setRunning(true)
    setError('')
    try {
      const response = await apiClient.post('/api/v1/performance-tests/execute', { test_id: testId })
      setLastExecution(response.data?.data)
      await loadData()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '性能测试执行失败')
    } finally {
      setRunning(false)
    }
  }

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
            <h1 className="text-2xl font-bold">性能测试</h1>
          </div>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {lastExecution && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Zap className="h-5 w-5" />
              <span>最近执行结果</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-center md:grid-cols-5">
              <Metric label="状态" value={lastExecution.status} />
              <Metric label="平均响应" value={`${lastExecution.average_response_time ?? '-'}ms`} />
              <Metric label="吞吐量" value={`${lastExecution.throughput ?? 0}/s`} />
              <Metric label="错误率" value={`${lastExecution.error_rate ?? 0}%`} />
              <Metric label="请求数" value={lastExecution.total_requests} />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>新建性能测试</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
            <Field label="目标 URL">
              <Input value={form.target_url} onChange={(event) => setForm({ ...form, target_url: event.target.value })} />
            </Field>
            <div className="grid grid-cols-3 gap-3">
              <Field label="并发">
                <Input type="number" min={1} value={form.concurrent_users} onChange={(event) => setForm({ ...form, concurrent_users: Number(event.target.value) })} />
              </Field>
              <Field label="时长">
                <Input type="number" min={1} value={form.test_duration} onChange={(event) => setForm({ ...form, test_duration: Number(event.target.value) })} />
              </Field>
              <Field label="爬坡">
                <Input type="number" min={0} value={form.ramp_up_time} onChange={(event) => setForm({ ...form, ramp_up_time: Number(event.target.value) })} />
              </Field>
            </div>
            <Button className="w-full" onClick={createAndRun} disabled={running}>
              <Play className="mr-2 h-4 w-4" />
              {running ? '执行中...' : '保存并执行'}
            </Button>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>性能测试列表</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>目标</TableHead>
                  <TableHead>并发</TableHead>
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
                    <TableCell className="max-w-[220px] truncate">{test.target_url}</TableCell>
                    <TableCell>{test.concurrent_users}</TableCell>
                    <TableCell><Badge variant={test.status === 'FAILED' ? 'destructive' : 'secondary'}>{test.status}</Badge></TableCell>
                    <TableCell>{formatDate(test.updated_at || test.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" disabled={running} onClick={() => runExisting(test.id)}>执行</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {!loading && tests.length === 0 && <div className="py-8 text-center text-gray-500">暂无性能测试</div>}
          </CardContent>
        </Card>
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

const Metric = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div>
    <p className="text-lg font-bold text-blue-600">{value}</p>
    <p className="text-sm text-gray-600">{label}</p>
  </div>
)

export default PerformanceTest
