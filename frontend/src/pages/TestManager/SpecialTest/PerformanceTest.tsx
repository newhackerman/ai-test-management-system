// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Copy,
  FileText,
  Play,
  Plus,
  RefreshCw,
  Save,
  Settings,
  Square,
  X,
  XCircle,
} from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import ProjectService from '../../../services/projectService'
import { apiClient } from '../../../services/api/client'
import {
  EXECUTION_ENVIRONMENTS,
  RUNNER_TYPE_OPTIONS,
  TestExecutionConfigService,
  type TestExecutionConfig,
  type TestExecutionEnvironment,
} from '../../../services/testExecutionConfigService'
import { formatDate } from '../../../utils/date'

const testTypeLabels: Record<string, string> = {
  load: '负载测试',
  stress: '压力测试',
  spike: '峰值测试',
  volume: '容量测试',
  endurance: '稳定性测试',
}

const statusLabels: Record<string, string> = {
  CREATED: '未执行',
  QUEUED: '已调度',
  SCHEDULED: '待执行',
  DISPATCHED: '已调度',
  RUNNING: '执行中',
  COMPLETED: '通过',
  FAILED: '未通过',
  STOPPED: '已停止',
}

const emptyForm = {
  test_name: '',
  description: '',
  project_id: '',
  test_type: 'load',
  target_url: '',
  concurrent_users: 5,
  test_duration: 10,
  ramp_up_time: 2,
  think_time_ms: 200,
  request_timeout: 10,
  max_response_time: 1000,
  p95_response_time: 1500,
  max_error_rate: 1,
  min_throughput: 0,
  script_type: 'none',
  script_repository: '',
  script_branch: '',
  script_path: '',
  script_entry: '',
  script_arguments: '',
  data_files: '',
}

const performanceFrameworks = new Set(['jmeter', 'k6', 'locust', 'python', 'pytest', 'javascript', 'custom_command', 'auto'])

const remoteDispatchMessage = '已创建远程调度任务，等待所选执行节点执行并回传结果。'

const normalizeDispatchState = (item: any) => {
  if (!item || typeof item !== 'object') return item
  const isRemoteDispatch = item.execution_mode === 'remote_runner' || item.dispatch_status === 'QUEUED' || item.dispatch_status === 'DISPATCHED'
  if (item.status !== 'QUEUED' && item.dispatch_status !== 'QUEUED') return item
  if (!isRemoteDispatch && item.status !== 'QUEUED') return item
  return {
    ...item,
    status: 'DISPATCHED',
    dispatch_status: item.dispatch_status === 'QUEUED' ? 'DISPATCHED' : item.dispatch_status,
    progress_percentage: Number(item.progress_percentage || 0) > 0 ? item.progress_percentage : 5,
    dispatch_message: item.dispatch_message || remoteDispatchMessage,
  }
}

const normalizePerformanceTest = (item: any) => {
  if (!item || typeof item !== 'object') return item
  if (item.status !== 'QUEUED') return item
  return { ...item, status: 'DISPATCHED' }
}

const numberOrZero = (value: any) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const formatMs = (value: any) => (value === null || value === undefined ? '-' : `${Number(value).toFixed(0)} ms`)
const formatPercent = (value: any) => (value === null || value === undefined ? '-' : `${Number(value).toFixed(2)}%`)
const formatRate = (value: any) => (value === null || value === undefined ? '-' : `${Number(value).toFixed(2)}/s`)
const isActiveExecutionStatus = (status?: string) => ['SCHEDULED', 'QUEUED', 'DISPATCHED', 'RUNNING'].includes(status || '')
const toLocalDatetimeValue = (date: Date) => {
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

const normalizeProjectList = (payload: any) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.data)) return payload.data
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.projects)) return payload.projects
  if (Array.isArray(payload?.data?.data)) return payload.data.data
  if (Array.isArray(payload?.data?.items)) return payload.data.items
  if (Array.isArray(payload?.data?.projects)) return payload.data.projects
  return []
}

const fallbackProjectsFromTests = (items: any[]) => {
  const ids = Array.from(new Set(items.map((item) => Number(item.project_id)).filter(Boolean)))
  return ids.map((id) => ({ id, project_name: `项目 #${id}` }))
}

const PerformanceTest: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([])
  const [tests, setTests] = useState<any[]>([])
  const [form, setForm] = useState<any>(emptyForm)
  const [selectedTestId, setSelectedTestId] = useState<number | null>(null)
  const [executions, setExecutions] = useState<any[]>([])
  const [activeExecution, setActiveExecution] = useState<any>(null)
  const [resultDetail, setResultDetail] = useState<any>(null)
  const [editingTestId, setEditingTestId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formFlash, setFormFlash] = useState(false)
  const formRef = useRef<HTMLDivElement>(null)
  const nameInputRef = useRef<HTMLInputElement>(null)
  const [executionConfigs, setExecutionConfigs] = useState<TestExecutionConfig[]>([])
  const [executionConfigLoading, setExecutionConfigLoading] = useState(false)
  const [executionEnvironment, setExecutionEnvironment] = useState<TestExecutionEnvironment>('perf')
  const [selectedConfigId, setSelectedConfigId] = useState('')
  const [scheduleMode, setScheduleMode] = useState<'immediate' | 'scheduled'>('immediate')
  const [scheduledAt, setScheduledAt] = useState('')

  const selectedTest = useMemo(
    () => tests.find((item) => Number(item.id) === Number(selectedTestId)) || null,
    [tests, selectedTestId],
  )

  const latestExecution = activeExecution || executions[0] || null
  const latestSummary = latestExecution?.summary || selectedTest?.last_result || {}
  const performanceExecutionConfigs = useMemo(() => (
    executionConfigs.filter((item) => (
      item.enabled &&
      performanceFrameworks.has(String(item.framework || ''))
    ))
  ), [executionConfigs])
  const availableEnvironments = useMemo(() => (
    EXECUTION_ENVIRONMENTS.filter((environment) => performanceExecutionConfigs.some((item) => item.environment === environment.value))
  ), [performanceExecutionConfigs])
  const environmentConfigs = useMemo(() => (
    performanceExecutionConfigs.filter((item) => item.environment === executionEnvironment)
  ), [performanceExecutionConfigs, executionEnvironment])
  const selectedExecutionConfig = useMemo(() => (
    environmentConfigs.find((item) => item.id === selectedConfigId) || environmentConfigs[0] || null
  ), [environmentConfigs, selectedConfigId])
  const selectedConfigIsLocalBlocked = Boolean(
    selectedExecutionConfig &&
    selectedExecutionConfig.runner_type === 'local' &&
    !(selectedExecutionConfig as any).allow_local_debug,
  )
  const canSubmitSelectedConfig = Boolean(selectedExecutionConfig) && !selectedConfigIsLocalBlocked

  const loadExecutionConfigs = async () => {
    setExecutionConfigLoading(true)
    try {
      const list = await TestExecutionConfigService.listAll()
      setExecutionConfigs(list)
    } catch {
      setExecutionConfigs([])
    } finally {
      setExecutionConfigLoading(false)
    }
  }

  const loadData = async (preferredTestId?: number | null) => {
    setLoading(true)
    setError('')
    try {
      const [projectResponse, directProjectResponse, testResponse] = await Promise.allSettled([
        ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
        apiClient.get('/projects?page=1&size=100&sort_by=updated_at&sort_order=desc'),
        apiClient.get('/performance-tests/?page=1&page_size=50'),
      ])
      const testsPayload = testResponse.status === 'fulfilled' ? testResponse.value : null
      const nextTests = (testsPayload?.data?.data || []).map(normalizePerformanceTest)
      const serviceProjects = projectResponse.status === 'fulfilled' ? normalizeProjectList(projectResponse.value) : []
      const directProjects = directProjectResponse.status === 'fulfilled' ? normalizeProjectList(directProjectResponse.value?.data || directProjectResponse.value) : []
      const nextProjects = serviceProjects.length ? serviceProjects : directProjects.length ? directProjects : fallbackProjectsFromTests(nextTests)
      setProjects(nextProjects)
      setTests(nextTests)
      setSelectedTestId((current) => {
        if (preferredTestId && nextTests.some((item: any) => Number(item.id) === Number(preferredTestId))) return preferredTestId
        if (current && nextTests.some((item: any) => Number(item.id) === Number(current))) return current
        return null
      })
      setForm((current: any) => ({
        ...current,
        project_id: current.project_id || String(nextProjects[0]?.id || ''),
      }))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载性能测试数据失败')
    } finally {
      setLoading(false)
    }
  }

  const loadExecutions = async (testId?: number | null) => {
    if (!testId) {
      setExecutions([])
      return
    }
    try {
      const response = await apiClient.get(`/performance-tests/tests/${testId}/executions?page=1&page_size=20`)
      setExecutions((response.data?.data || []).map(normalizeDispatchState))
    } catch {
      setExecutions([])
    }
  }

  useEffect(() => {
    loadData()
    loadExecutionConfigs()
  }, [])

  useEffect(() => {
    if (!showForm || editingTestId || form.project_id || !projects.length) return
    setForm((current: any) => (
      current.project_id ? current : { ...current, project_id: String(projects[0]?.id || '') }
    ))
  }, [showForm, editingTestId, form.project_id, projects])

  useEffect(() => {
    if (!performanceExecutionConfigs.length) {
      setSelectedConfigId('')
      return
    }
    if (!performanceExecutionConfigs.some((item) => item.environment === executionEnvironment)) {
      setExecutionEnvironment(performanceExecutionConfigs[0].environment)
      return
    }
    if (!environmentConfigs.some((item) => item.id === selectedConfigId)) {
      setSelectedConfigId(environmentConfigs[0]?.id || '')
    }
  }, [performanceExecutionConfigs, environmentConfigs, executionEnvironment, selectedConfigId])

  useEffect(() => {
    loadExecutions(selectedTest?.id)
  }, [selectedTest?.id])

  useEffect(() => {
    const executionId = activeExecution?.execution_id
    if (!executionId || !isActiveExecutionStatus(activeExecution?.status)) return
    if (activeExecution?.status === 'DISPATCHED' && activeExecution?.execution_mode === 'remote_runner') return
    const previousStatus = activeExecution?.status

    const timer = window.setInterval(async () => {
      try {
        const response = await apiClient.get(`/performance-tests/executions/${executionId}/status`)
        const nextExecution = normalizeDispatchState(response.data?.data)
        setActiveExecution(nextExecution)
        const statusChanged = nextExecution?.status && nextExecution.status !== previousStatus
        if (statusChanged) {
          await loadData(nextExecution.test_id)
          await loadExecutions(nextExecution.test_id)
        }
        if (nextExecution && !isActiveExecutionStatus(nextExecution.status)) {
          window.clearInterval(timer)
          if (!statusChanged) {
            await loadData(nextExecution.test_id)
            await loadExecutions(nextExecution.test_id)
          }
          await loadResult(nextExecution.execution_id)
          setRunning(false)
        }
      } catch {
        window.clearInterval(timer)
        setRunning(false)
      }
    }, 1500)

    return () => window.clearInterval(timer)
  }, [activeExecution?.execution_id, activeExecution?.status])

  const updateForm = (patch: Record<string, any>) => setForm((current: any) => ({ ...current, ...patch }))

  const toForm = (test: any) => {
    const scenario = test?.test_scenario || {}
    const loadModel = test?.load_model || {}
    const criteria = test?.performance_criteria || {}
    const scriptConfig = scenario.script_config || {}
    return {
      test_name: test?.test_name || '',
      description: test?.description || '',
      project_id: String(test?.project_id || ''),
      test_type: test?.test_type || 'load',
      target_url: test?.target_url || '',
      concurrent_users: test?.concurrent_users || loadModel.concurrent_users || 5,
      test_duration: test?.test_duration || loadModel.duration || 10,
      ramp_up_time: test?.ramp_up_time || loadModel.ramp_up_time || 2,
      think_time_ms: loadModel.think_time_ms ?? 200,
      request_timeout: loadModel.request_timeout ?? 10,
      max_response_time: criteria.max_response_time ?? 1000,
      p95_response_time: criteria.p95_response_time ?? 1500,
      max_error_rate: criteria.max_error_rate ?? 1,
      min_throughput: criteria.min_throughput ?? 0,
      script_type: scriptConfig.script_type || scenario.script_type || 'none',
      script_repository: scriptConfig.repository || scenario.script_repository || '',
      script_branch: scriptConfig.branch || scenario.script_branch || '',
      script_path: scriptConfig.script_path || scenario.script_path || scenario.script_file || '',
      script_entry: scriptConfig.entry_file || scenario.script_entry || '',
      script_arguments: scriptConfig.arguments || scenario.script_arguments || '',
      data_files: scriptConfig.data_files || scenario.data_files || '',
    }
  }

  const startCreate = () => {
    setEditingTestId(null)
    setForm({
      ...emptyForm,
      project_id: String(projects[0]?.id || ''),
    })
    setShowForm(true)
    setError('')
    setFormFlash(true)
    window.setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      nameInputRef.current?.focus()
    }, 0)
    window.setTimeout(() => setFormFlash(false), 1200)
  }

  const editTest = (test: any) => {
    setEditingTestId(Number(test.id))
    setSelectedTestId(Number(test.id))
    setForm(toForm(test))
    setShowForm(true)
    setError('')
    window.setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      nameInputRef.current?.focus()
    }, 0)
  }

  const buildPayload = () => ({
    test_name: form.test_name.trim(),
    description: form.description.trim() || '通过性能测试页面创建',
    project_id: Number(form.project_id),
    test_type: form.test_type,
    target_url: form.target_url.trim(),
    test_scenario: {
      script_config: {
        script_type: form.script_type,
        repository: form.script_repository.trim(),
        branch: form.script_branch.trim(),
        script_path: form.script_path.trim(),
        entry_file: form.script_entry.trim(),
        arguments: form.script_arguments.trim(),
        data_files: form.data_files.trim(),
      },
      script_type: form.script_type,
      script_path: form.script_path.trim(),
      script_file: form.script_entry.trim() || form.script_path.trim(),
    },
    load_model: {
      concurrent_users: Number(form.concurrent_users),
      ramp_up_time: Number(form.ramp_up_time),
      duration: Number(form.test_duration),
      think_time_ms: Number(form.think_time_ms),
      request_timeout: Number(form.request_timeout),
    },
    performance_criteria: {
      max_response_time: Number(form.max_response_time),
      p95_response_time: Number(form.p95_response_time),
      max_error_rate: Number(form.max_error_rate),
      min_throughput: Number(form.min_throughput),
    },
    test_duration: Number(form.test_duration),
    concurrent_users: Number(form.concurrent_users),
    ramp_up_time: Number(form.ramp_up_time),
    environment_config: { source: 'web-ui', mode: 'http-sampling' },
  })

  const validateForm = () => {
    if (!form.test_name.trim()) return '请填写测试名称'
    if (!form.project_id) return '请选择所属项目'
    if (!form.target_url.trim()) return '请填写目标 URL'
    if (numberOrZero(form.concurrent_users) < 1) return '并发用户必须大于 0'
    if (numberOrZero(form.concurrent_users) > 200000) return '并发用户数过大，请拆分场景或使用分布式压测节点'
    return ''
  }

  const buildExecutionConfigPayload = () => {
    if (!selectedExecutionConfig) return null
    return {
      source: 'test_execution_config',
      config_id: selectedExecutionConfig.id,
      config_name: selectedExecutionConfig.name,
      framework: selectedExecutionConfig.framework,
      framework_label: selectedExecutionConfig.framework_label,
      environment: selectedExecutionConfig.environment,
      timeout: selectedExecutionConfig.timeout,
      runner_type: selectedExecutionConfig.runner_type,
      runner_name: selectedExecutionConfig.runner_name,
      runner_host: selectedExecutionConfig.runner_host,
      runner_port: selectedExecutionConfig.runner_port,
      runner_user: selectedExecutionConfig.runner_user,
      runner_os: selectedExecutionConfig.runner_os,
      runner_workdir: selectedExecutionConfig.runner_workdir,
      credential_ref: selectedExecutionConfig.credential_ref,
      agent_id: selectedExecutionConfig.agent_id,
      agent_callback_url: selectedExecutionConfig.agent_callback_url,
      docker_image: selectedExecutionConfig.docker_image,
      docker_network: selectedExecutionConfig.docker_network,
      docker_volumes: selectedExecutionConfig.docker_volumes,
      docker_args: selectedExecutionConfig.docker_args,
      kubernetes_context: selectedExecutionConfig.kubernetes_context,
      kubernetes_namespace: selectedExecutionConfig.kubernetes_namespace,
      kubernetes_image: selectedExecutionConfig.kubernetes_image,
      kubernetes_job_template: selectedExecutionConfig.kubernetes_job_template,
      ci_provider: selectedExecutionConfig.ci_provider,
      ci_pipeline_url: selectedExecutionConfig.ci_pipeline_url,
      ci_project: selectedExecutionConfig.ci_project,
      ci_branch: selectedExecutionConfig.ci_branch,
      ci_token_ref: selectedExecutionConfig.ci_token_ref,
      ci_variables: selectedExecutionConfig.ci_variables,
      tool_home: selectedExecutionConfig.tool_home,
      executable_path: selectedExecutionConfig.executable_path,
      command: selectedExecutionConfig.command,
      command_template: selectedExecutionConfig.command_template,
      pre_command: selectedExecutionConfig.pre_command,
      post_command: selectedExecutionConfig.post_command,
      working_directory: selectedExecutionConfig.working_directory,
      result_collection: selectedExecutionConfig.result_collection,
      result_directory: selectedExecutionConfig.result_directory,
      result_file_pattern: selectedExecutionConfig.result_file_pattern,
      report_directory: selectedExecutionConfig.report_directory,
      result_format: selectedExecutionConfig.result_format,
      artifact_patterns: selectedExecutionConfig.artifact_patterns,
      jmeter_properties: selectedExecutionConfig.jmeter_properties,
      distributed_hosts: selectedExecutionConfig.distributed_hosts,
      environment_variables: selectedExecutionConfig.environment_variables,
      allow_local_debug: (selectedExecutionConfig as any).allow_local_debug === true,
    }
  }

  const saveTest = async () => {
    const message = validateForm()
    if (message) {
      setError(message)
      return null
    }

    setSaving(true)
    setError('')
    try {
      const response = editingTestId
        ? await apiClient.put(`/performance-tests/${editingTestId}`, buildPayload())
        : await apiClient.post('/performance-tests/', buildPayload())
      const test = response.data?.data
      const savedId = test?.id ? Number(test.id) : null
      setSelectedTestId(savedId)
      setEditingTestId(savedId)
      await loadData(savedId)
      setSelectedTestId(savedId)
      setShowForm(false)
      return test
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '保存性能测试失败')
      return null
    } finally {
      setSaving(false)
    }
  }

  const runTest = async (testId?: number) => {
    const id = testId || selectedTest?.id
    if (!id) {
      setError('请先选择或保存一个性能测试场景')
      return
    }
    const executionConfig = buildExecutionConfigPayload()
    if (!executionConfig) {
      setError('请先在系统管理 - 配置项 - 测试执行配置中启用性能测试执行节点，然后选择执行方式。')
      return
    }
    if (selectedConfigIsLocalBlocked) {
      setError('当前选中的执行配置是本机执行。性能测试请使用 SSH、Agent、Docker、Kubernetes 或 CI 执行节点；如仅用于调试，请在配置中显式开启本机调试。')
      return
    }
    if (scheduleMode === 'scheduled') {
      if (!scheduledAt) {
        setError('请选择计划执行时间')
        return
      }
      if (new Date(scheduledAt).getTime() <= Date.now()) {
        setError('计划执行时间必须晚于当前时间')
        return
      }
    }

    setRunning(true)
    setError('')
    setResultDetail(null)
    try {
      const response = await apiClient.post('/performance-tests/execute', {
        test_id: id,
        execution_config: executionConfig,
        schedule_mode: scheduleMode === 'scheduled' ? 'scheduled' : 'immediate',
        scheduled_at: scheduleMode === 'scheduled' ? new Date(scheduledAt).toISOString() : undefined,
      })
      const execution = normalizeDispatchState(response.data?.data)
      setActiveExecution(execution)
      setSelectedTestId(id)
      await loadExecutions(id)
      setRunning(false)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '性能测试执行失败')
      setRunning(false)
    }
  }

  const saveAndRunForm = async () => {
    const created = await saveTest()
    if (!created?.id) return
    await runTest(Number(created.id))
  }

  const loadResult = async (executionId: string) => {
    try {
      const response = await apiClient.get(`/performance-tests/executions/${executionId}/results`)
      setResultDetail(response.data?.data || null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载性能测试结果失败')
    }
  }

  const stopExecution = async (executionId?: string) => {
    if (!executionId) return
    setError('')
    try {
      await apiClient.post(`/performance-tests/executions/${executionId}/stop`)
      setRunning(false)
      await loadData(selectedTest?.id)
      await loadExecutions(selectedTest?.id)
      setActiveExecution((current: any) => (
        current?.execution_id === executionId ? { ...current, status: 'STOPPED', current_users: 0, progress_percentage: 100 } : current
      ))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '停止性能测试失败')
    }
  }

  const importExecutionResult = async (execution: any) => {
    if (!execution?.execution_id) return
    const text = window.prompt('粘贴执行节点回传的 JSON 摘要，例如 total_requests、average_response_time、p95_response_time、throughput、error_rate。')
    if (!text?.trim()) return
    try {
      const payload = JSON.parse(text)
      const response = await apiClient.post(`/performance-tests/executions/${execution.execution_id}/results`, payload)
      const nextExecution = normalizeDispatchState(response.data?.data)
      setActiveExecution(nextExecution)
      await loadData()
      await loadExecutions(execution.test_id || selectedTest?.id)
      await loadResult(execution.execution_id)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '导入性能测试结果失败，请确认 JSON 格式和字段。')
    }
  }

  const cloneSelected = () => {
    if (!selectedTest) return
    setForm({ ...toForm(selectedTest), test_name: `${selectedTest.test_name || '性能测试'} 副本` })
    setShowForm(true)
    setFormFlash(true)
    window.setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      nameInputRef.current?.focus()
    }, 0)
    window.setTimeout(() => setFormFlash(false), 1200)
  }

  const deleteTest = async (test: any) => {
    if (!test?.id) return
    if (!window.confirm(`确定删除性能场景“${test.test_name}”？相关执行记录也会删除。`)) return
    setError('')
    try {
      await apiClient.delete(`/performance-tests/${test.id}`)
      if (Number(editingTestId) === Number(test.id)) startCreate()
      if (Number(selectedTestId) === Number(test.id)) setSelectedTestId(null)
      await loadData()
      setExecutions([])
      setResultDetail(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '删除性能测试失败')
    }
  }

  const statusBadge = (status?: string) => {
    const isFailed = status === 'FAILED'
    const isPassed = status === 'COMPLETED'
    const isPending = isActiveExecutionStatus(status)
    return (
      <Badge variant={isFailed ? 'destructive' : isPassed ? 'default' : isPending ? 'secondary' : 'secondary'}>
        {statusLabels[status || 'CREATED'] || status || '-'}
      </Badge>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/test-manager">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回测试管理
            </Link>
          </Button>
          <div className="h-5 w-px bg-border" />
          <div className="text-sm text-muted-foreground">场景、负载、阈值、执行节点、结果回传</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button data-testid="performance-new" variant="outline" size="sm" onClick={startCreate}>
            <Plus className="mr-2 h-4 w-4" />
            新建场景
          </Button>
          <Button variant="outline" size="sm" onClick={() => loadData()} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button variant="outline" size="sm" onClick={cloneSelected} disabled={!selectedTest}>
            <Copy className="mr-2 h-4 w-4" />
            复制场景
          </Button>
          <Button data-testid="performance-run-selected" size="sm" onClick={() => runTest(selectedTest?.id)} disabled={running || saving || !selectedTest || !canSubmitSelectedConfig}>
            <Play className="mr-2 h-4 w-4" />
            {running ? '提交中' : selectedTest ? (scheduleMode === 'scheduled' ? '创建定时任务' : '提交当前场景') : '请选择场景'}
          </Button>
        </div>
      </div>

      <div data-testid="performance-current-scenario" className="flex flex-col gap-2 rounded-md border bg-muted/30 px-4 py-3 text-sm md:flex-row md:items-center md:justify-between">
        {selectedTest ? (
          <>
          <div className="min-w-0">
            <span className="text-muted-foreground">当前场景：</span>
            <span data-testid="performance-current-name" className="font-medium">{selectedTest.test_name}</span>
            <span className="ml-2 text-muted-foreground">{selectedTest.concurrent_users} 并发 / {selectedTest.test_duration}s</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            {statusBadge(selectedTest.status)}
            <span>点击列表中的场景名称或“选择”切换当前场景</span>
          </div>
          </>
        ) : (
          <>
            <div className="min-w-0 font-medium">尚未选择性能场景</div>
            <div className="text-muted-foreground">请先在下方列表点击“选择”或新建并保存场景后再提交执行。</div>
          </>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}
      {!executionConfigLoading && performanceExecutionConfigs.length === 0 && (
        <div className="flex flex-col gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200 md:flex-row md:items-center md:justify-between">
          <span>当前没有已启用的性能测试执行配置。请在系统管理的测试执行配置中启用 JMeter、k6、Locust、Python、JavaScript、自动识别或自定义命令配置。</span>
          <Button asChild variant="outline" size="sm">
            <Link to="/config">去配置</Link>
          </Button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Metric icon={FileText} label="场景数" value={tests.length} />
        <Metric icon={Activity} label="最近状态" value={statusLabels[latestExecution?.status] || statusLabels[selectedTest?.status] || '-'} />
        <Metric icon={BarChart3} label="平均响应" value={formatMs(latestExecution?.average_response_time ?? latestSummary.average_response_time)} />
        <Metric icon={Activity} label="吞吐量" value={formatRate(latestExecution?.throughput ?? latestSummary.throughput)} />
        <Metric icon={AlertTriangle} label="错误率" value={formatPercent(latestExecution?.error_rate ?? latestSummary.error_rate)} />
      </div>

      {latestExecution && (
        <Card>
          <CardContent className="pt-4">
            <div className="grid gap-3 md:grid-cols-[1.4fr_3fr]">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {latestExecution.status === 'COMPLETED' ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : latestExecution.status === 'FAILED' ? <XCircle className="h-4 w-4 text-red-600" /> : <Activity className="h-4 w-4 text-blue-600" />}
                  <span className="font-medium">最近执行</span>
                  {statusBadge(latestExecution.status)}
                  {isActiveExecutionStatus(latestExecution.status) && (
                    <Button data-testid="performance-stop" variant="outline" size="sm" onClick={() => stopExecution(latestExecution.execution_id)}>
                      <Square className="mr-2 h-3.5 w-3.5" />
                      停止
                    </Button>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">{latestExecution.execution_id}</div>
                {latestExecution.dispatch_message && (
                  <div className="text-xs text-muted-foreground">{latestExecution.dispatch_message}</div>
                )}
                {latestExecution.scheduled_at && (
                  <div className="text-xs text-muted-foreground">计划时间：{formatDate(latestExecution.scheduled_at)}</div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-6">
                <Info label="执行节点" value={latestExecution.runner_name || latestExecution.runner_host || '-'} />
                <Info label="成功/失败" value={`${latestExecution.successful_requests || 0}/${latestExecution.failed_requests || 0}`} />
                <Info label="平均" value={formatMs(latestExecution.average_response_time)} />
                <Info label="最大" value={formatMs(latestExecution.max_response_time)} />
                <Info label="吞吐" value={formatRate(latestExecution.throughput)} />
                <Info label="耗时" value={latestExecution.duration ? `${latestExecution.duration}s` : '-'} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {showForm && (
        <Card
          ref={formRef}
          data-testid="performance-form-panel"
          className={`transition-shadow duration-500 ${formFlash ? 'ring-2 ring-primary shadow-lg' : ''}`}
        >
          <CardHeader className="gap-3 border-b pb-3">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Save className="h-4 w-4" />
                {editingTestId ? '编辑性能场景' : '新建性能场景'}
                <Badge variant="secondary">{editingTestId ? '编辑中' : '新建'}</Badge>
              </CardTitle>
              <Button data-testid="performance-cancel-form" variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                <X className="mr-2 h-4 w-4" />
                收起
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              配置场景、脚本来源、负载模型、通过阈值和远程执行节点；保存后可在列表中提交执行。
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_420px]">
              <div className="space-y-4">
                <SectionTitle title="基础信息" />
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <Field label="场景名称" className="col-span-2">
                    <Input ref={nameInputRef} data-testid="performance-test-name" value={form.test_name} onChange={(event) => updateForm({ test_name: event.target.value })} />
                  </Field>
                  <Field label="所属项目">
                    <select data-testid="performance-project" className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.project_id} onChange={(event) => updateForm({ project_id: event.target.value })}>
                      <option value="">请选择项目</option>
                      {projects.map((project) => (
                        <option key={project.id} value={String(project.id)}>{project.project_name || project.name || `项目 #${project.id}`}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="类型">
                    <select className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.test_type} onChange={(event) => updateForm({ test_type: event.target.value })}>
                      {Object.entries(testTypeLabels).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="目标 URL" className="col-span-2 lg:col-span-4">
                    <Input data-testid="performance-target-url" value={form.target_url} onChange={(event) => updateForm({ target_url: event.target.value })} />
                  </Field>
                  <Field label="说明" className="col-span-2 lg:col-span-4">
                    <Textarea rows={2} value={form.description} onChange={(event) => updateForm({ description: event.target.value })} />
                  </Field>
                </div>

                <SectionTitle title="测试脚本" />
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
                  <Field label="脚本类型">
                    <select className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={form.script_type} onChange={(event) => updateForm({ script_type: event.target.value })}>
                      <option value="none">仅使用目标 URL</option>
                      <option value="jmeter">JMeter JMX</option>
                      <option value="k6">k6 JavaScript</option>
                      <option value="locust">Locust Python</option>
                      <option value="python">Python 脚本</option>
                      <option value="custom_command">自定义命令</option>
                    </select>
                  </Field>
                  <Field label="脚本路径">
                    <Input value={form.script_path} onChange={(event) => updateForm({ script_path: event.target.value })} placeholder="/opt/perf/scripts/order.jmx" />
                  </Field>
                  <Field label="入口文件">
                    <Input value={form.script_entry} onChange={(event) => updateForm({ script_entry: event.target.value })} placeholder="tests/order.jmx 鎴?scripts/load.py" />
                  </Field>
                  <Field label="代码仓库">
                    <Input value={form.script_repository} onChange={(event) => updateForm({ script_repository: event.target.value })} placeholder="git@example.com:qa/perf-tests.git" />
                  </Field>
                  <Field label="分支">
                    <Input value={form.script_branch} onChange={(event) => updateForm({ script_branch: event.target.value })} placeholder="main" />
                  </Field>
                  <Field label="执行参数">
                    <Input value={form.script_arguments} onChange={(event) => updateForm({ script_arguments: event.target.value })} placeholder="-Jenv=test -Jusers=200" />
                  </Field>
                  <Field label="数据文件" className="col-span-2 lg:col-span-3">
                    <Input value={form.data_files} onChange={(event) => updateForm({ data_files: event.target.value })} placeholder="data/users.csv, data/orders.csv" />
                  </Field>
                </div>

              </div>

              <div className="space-y-4 rounded-md border bg-muted/20 p-3">
                <SectionTitle title="执行调度" />
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    type="button"
                    variant={scheduleMode === 'immediate' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setScheduleMode('immediate')}
                  >
                    立即提交
                  </Button>
                  <Button
                    type="button"
                    variant={scheduleMode === 'scheduled' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => {
                      setScheduleMode('scheduled')
                      if (!scheduledAt) setScheduledAt(toLocalDatetimeValue(new Date(Date.now() + 10 * 60 * 1000)))
                    }}
                  >
                    定时提交
                  </Button>
                </div>
                {scheduleMode === 'scheduled' && (
                  <Field label="计划执行时间">
                    <Input
                      data-testid="performance-scheduled-at"
                      type="datetime-local"
                      value={scheduledAt}
                      min={toLocalDatetimeValue(new Date(Date.now() + 60 * 1000))}
                      onChange={(event) => setScheduledAt(event.target.value)}
                    />
                  </Field>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <Field label="执行环境">
                    <select
                      data-testid="performance-execution-environment"
                      className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                      value={executionEnvironment}
                      onChange={(event) => setExecutionEnvironment(event.target.value as TestExecutionEnvironment)}
                      disabled={executionConfigLoading || !availableEnvironments.length}
                    >
                      {availableEnvironments.length === 0 && <option value={executionEnvironment}>暂无可用环境</option>}
                      {availableEnvironments.map((environment) => (
                        <option key={environment.value} value={environment.value}>{environment.label}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="执行方式">
                    <select
                      data-testid="performance-execution-config"
                      className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                      value={selectedExecutionConfig?.id || ''}
                      onChange={(event) => setSelectedConfigId(event.target.value)}
                      disabled={executionConfigLoading || !environmentConfigs.length}
                    >
                      {environmentConfigs.length === 0 && <option value="">暂无执行配置</option>}
                      {environmentConfigs.map((config) => (
                        <option key={config.id} value={config.id}>
                          {config.name}（{config.framework_label || config.framework} / {RUNNER_TYPE_OPTIONS.find((item) => item.value === config.runner_type)?.label || config.runner_type}）
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="outline" size="sm" onClick={loadExecutionConfigs} disabled={executionConfigLoading}>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    刷新配置
                  </Button>
                  <Button asChild variant="outline" size="sm">
                    <Link to="/config">
                      <Settings className="mr-2 h-4 w-4" />
                      维护配置
                    </Link>
                  </Button>
                </div>
                {selectedExecutionConfig && (
                  <div className="grid gap-2 text-sm">
                    <Info label="节点类型" value={RUNNER_TYPE_OPTIONS.find((item) => item.value === selectedExecutionConfig.runner_type)?.label || selectedExecutionConfig.runner_type} />
                    <Info label="节点地址" value={selectedExecutionConfig.runner_host || selectedExecutionConfig.agent_id || selectedExecutionConfig.ci_pipeline_url || '-'} />
                    <Info label="结果采集" value={selectedExecutionConfig.result_collection || '-'} />
                    <Info label="命令模板" value={selectedExecutionConfig.command_template ? '已配置' : '未配置'} />
                  </div>
                )}
                {selectedConfigIsLocalBlocked && (
                  <div data-testid="performance-local-runner-warning" className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                    当前选中的是本机执行配置，性能测试提交请使用 SSH、Agent、Docker、Kubernetes 或 CI 节点；本机执行只应用于显式调试配置。
                  </div>
                )}

                <SectionTitle title="负载模型" />
                <div className="grid grid-cols-2 gap-3">
                  <NumberField label="并发" value={form.concurrent_users} onChange={(value) => updateForm({ concurrent_users: value })} min={1} />
                  <NumberField label="时长(s)" value={form.test_duration} onChange={(value) => updateForm({ test_duration: value })} min={1} />
                  <NumberField label="爬坡(s)" value={form.ramp_up_time} onChange={(value) => updateForm({ ramp_up_time: value })} min={0} />
                  <NumberField label="间隔(ms)" value={form.think_time_ms} onChange={(value) => updateForm({ think_time_ms: value })} min={0} />
                  <NumberField label="超时(s)" value={form.request_timeout} onChange={(value) => updateForm({ request_timeout: value })} min={1} />
                </div>

                <SectionTitle title="通过阈值" />
                <div className="grid grid-cols-2 gap-3">
                  <NumberField label="平均响应(ms)" value={form.max_response_time} onChange={(value) => updateForm({ max_response_time: value })} min={1} />
                  <NumberField label="P95(ms)" value={form.p95_response_time} onChange={(value) => updateForm({ p95_response_time: value })} min={1} />
                  <NumberField label="错误率(%)" value={form.max_error_rate} onChange={(value) => updateForm({ max_error_rate: value })} min={0} />
                  <NumberField label="最小吞吐/s" value={form.min_throughput} onChange={(value) => updateForm({ min_throughput: value })} min={0} />
                </div>

                <div className="grid gap-2">
                  <Button data-testid="performance-save" onClick={saveTest} disabled={saving || running || !form.project_id}>
                    <Save className="mr-2 h-4 w-4" />
                    {editingTestId ? '保存修改' : '保存场景'}
                  </Button>
                  <Button data-testid="performance-save-run" variant="outline" onClick={saveAndRunForm} disabled={saving || running || !form.project_id || !canSubmitSelectedConfig}>
                    <Play className="mr-2 h-4 w-4" />
                    {scheduleMode === 'scheduled' ? '保存并定时' : '保存并提交'}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
          <Card className="min-w-0">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                性能场景
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[84px] min-w-[84px]">当前</TableHead>
                    <TableHead className="w-[28%] min-w-[140px]">名称</TableHead>
                    <TableHead className="min-w-[80px]">类型</TableHead>
                    <TableHead className="min-w-[110px]">负载</TableHead>
                    <TableHead className="min-w-[80px]">最近结果</TableHead>
                    <TableHead className="min-w-[120px]">目标</TableHead>
                    <TableHead className="w-[180px] min-w-[160px] text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tests.map((test: any) => (
                    <TableRow key={test.id} data-testid={`performance-row-${test.id}`} className={Number(selectedTest?.id) === Number(test.id) ? 'border-l-4 border-l-primary bg-primary/5' : ''}>
                      <TableCell>
                        {Number(selectedTest?.id) === Number(test.id) ? (
                          <Badge variant="default">当前</Badge>
                        ) : (
                          <Button data-testid={`performance-pick-${test.id}`} variant="outline" size="sm" onClick={() => setSelectedTestId(test.id)}>选择</Button>
                        )}
                      </TableCell>
                      <TableCell>
                        <button data-testid={`performance-select-${test.id}`} className="text-left font-medium text-primary hover:underline" onClick={() => setSelectedTestId(test.id)}>{test.test_name}</button>
                        <div className="mt-1 text-xs text-muted-foreground">{formatDate(test.updated_at || test.created_at)}</div>
                      </TableCell>
                      <TableCell>{testTypeLabels[test.test_type] || test.test_type}</TableCell>
                      <TableCell>{test.concurrent_users} 并发 / {test.test_duration}s</TableCell>
                      <TableCell>{statusBadge(test.status)}</TableCell>
                      <TableCell className="max-w-[220px] truncate">{test.target_url}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button data-testid={`performance-edit-${test.id}`} variant="ghost" size="sm" onClick={() => editTest(test)}>编辑</Button>
                          <Button data-testid={`performance-run-${test.id}`} variant="ghost" size="sm" disabled={running || !canSubmitSelectedConfig} onClick={() => runTest(test.id)}>提交</Button>
                          <Button data-testid={`performance-delete-${test.id}`} variant="ghost" size="sm" className="text-red-600 hover:text-red-700" disabled={running} onClick={() => deleteTest(test)}>删除</Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!loading && tests.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">暂无性能场景</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              </div>
            </CardContent>
          </Card>

        <div className="min-w-0 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4" />
                执行历史
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[140px]">执行ID</TableHead>
                    <TableHead className="min-w-[80px]">状态</TableHead>
                    <TableHead className="min-w-[130px]">计划时间</TableHead>
                    <TableHead className="min-w-[120px]">执行节点</TableHead>
                    <TableHead className="min-w-[60px]">请求</TableHead>
                    <TableHead className="min-w-[110px]">平均/P95</TableHead>
                    <TableHead className="min-w-[70px]">吞吐</TableHead>
                    <TableHead className="min-w-[70px]">错误率</TableHead>
                    <TableHead className="min-w-[100px] text-right">结果</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((execution: any) => (
                    <TableRow key={execution.execution_id} data-testid={`performance-execution-${execution.execution_id}`}>
                      <TableCell>
                        <div className="font-mono text-xs">{execution.execution_id}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{formatDate(execution.start_time)}</div>
                      </TableCell>
                      <TableCell>{statusBadge(execution.status)}</TableCell>
                      <TableCell>{execution.scheduled_at ? formatDate(execution.scheduled_at) : '-'}</TableCell>
                      <TableCell>
                        <div className="max-w-[160px] truncate">{execution.runner_name || execution.runner_host || '-'}</div>
                        <div className="text-xs text-muted-foreground">{execution.framework || execution.runner_type || '-'}</div>
                      </TableCell>
                      <TableCell>{execution.total_requests || 0}</TableCell>
                      <TableCell>{formatMs(execution.average_response_time)} / {formatMs(execution.summary?.p95_response_time)}</TableCell>
                      <TableCell>{formatRate(execution.throughput)}</TableCell>
                      <TableCell>{formatPercent(execution.error_rate)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button data-testid={`performance-result-${execution.execution_id}`} variant="ghost" size="sm" onClick={() => loadResult(execution.execution_id)} disabled={isActiveExecutionStatus(execution.status)}>查看</Button>
                          <Button variant="ghost" size="sm" onClick={() => importExecutionResult(execution)} disabled={execution.status === 'STOPPED'}>导入</Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {executions.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="h-20 text-center text-muted-foreground">选中场景后显示执行历史</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              </div>
            </CardContent>
          </Card>

          {resultDetail && (
            <Card data-testid="performance-result-detail">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  结果分析
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
                  <Info label="平均" value={formatMs(resultDetail.performance_metrics?.average_response_time)} />
                  <Info label="P90" value={formatMs(resultDetail.performance_metrics?.p90_response_time)} />
                  <Info label="P95" value={formatMs(resultDetail.performance_metrics?.p95_response_time)} />
                  <Info label="P99" value={formatMs(resultDetail.performance_metrics?.p99_response_time)} />
                  <Info label="吞吐" value={formatRate(resultDetail.performance_metrics?.throughput)} />
                  <Info label="错误率" value={formatPercent(resultDetail.performance_metrics?.error_rate)} />
                </div>
                {resultDetail.performance_bottlenecks?.length > 0 && (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                    {resultDetail.performance_bottlenecks.map((item: any, index: number) => (
                      <div key={index}>{item.type}: {item.actual}{item.unit || ''} / 阈值 {item.threshold}{item.unit || ''}</div>
                    ))}
                  </div>
                )}
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border p-3">
                    <div className="mb-2 text-sm font-semibold">状态码分布</div>
                    <div className="space-y-1 text-sm">
                      {Object.entries(resultDetail.execution_summary?.status_codes || {}).map(([code, count]) => (
                        <div key={code} className="flex justify-between">
                          <span className="font-mono">{code}</span>
                          <span>{String(count)} 次</span>
                        </div>
                      ))}
                      {Object.keys(resultDetail.execution_summary?.status_codes || {}).length === 0 && (
                        <div className="text-muted-foreground">暂无状态码数据</div>
                      )}
                    </div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="mb-2 text-sm font-semibold">执行摘要</div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <Info label="总请求" value={resultDetail.execution_summary?.total_requests || 0} />
                      <Info label="成功/失败" value={`${resultDetail.execution_summary?.successful_requests || 0}/${resultDetail.execution_summary?.failed_requests || 0}`} />
                      <Info label="耗时" value={resultDetail.execution_summary?.duration ? `${resultDetail.execution_summary.duration}s` : '-'} />
                      <Info label="结论" value={resultDetail.test_passed ? '通过' : '未通过'} />
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {resultDetail.recommendations?.map((item: string, index: number) => (
                    <div key={index} className="rounded-md bg-muted px-3 py-2 text-sm">{item}</div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

const Field = ({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) => (
  <label className={`block space-y-1.5 text-sm font-medium ${className}`}>
    <span>{label}</span>
    {children}
  </label>
)

const NumberField = ({ label, value, onChange, min }: { label: string; value: any; onChange: (value: number) => void; min: number }) => (
  <Field label={label}>
    <Input type="number" min={min} value={value} onChange={(event) => onChange(Number(event.target.value))} />
  </Field>
)

const SectionTitle = ({ title }: { title: string }) => (
  <div className="text-sm font-semibold text-muted-foreground">{title}</div>
)

const Metric = ({ icon: Icon, label, value }: { icon: any; label: string; value: React.ReactNode }) => (
  <Card>
    <CardContent className="flex items-center gap-3 p-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="truncate text-base font-semibold">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </CardContent>
  </Card>
)

const Info = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="min-w-0">
    <div className="truncate font-semibold">{value}</div>
    <div className="text-xs text-muted-foreground">{label}</div>
  </div>
)

export default PerformanceTest
