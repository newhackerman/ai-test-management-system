import React, { useState, useEffect } from 'react'
import { Card, Button, Table, Space, Input, Select, Modal, Form, Switch, Tag, Tabs, message, Drawer, Row, Col, Statistic, notification, InputNumber, Popconfirm, Progress } from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, 
  SyncOutlined, SettingOutlined, EyeOutlined, CopyOutlined,
  EnvironmentOutlined, LockOutlined, UnlockOutlined, HistoryOutlined,
  ImportOutlined, ExportOutlined, WifiOutlined
} from '@ant-design/icons'
import { ConfigService, ConfigItem, ConfigGroup, Environment as EnvType, ConfigCreateRequest, ConfigUpdateRequest } from '@/services/config-service'
import {
  BROWSER_OPTIONS,
  EXECUTION_ENVIRONMENTS,
  FRAMEWORK_OPTIONS,
  RESULT_COLLECTION_OPTIONS,
  RESULT_FORMAT_OPTIONS,
  RUNNER_TYPE_OPTIONS,
  TestExecutionConfigService,
  type TestExecutionConfig,
  type TestExecutionEnvironment,
  type TestRunnerType,
} from '@/services/testExecutionConfigService'
import ConfigImportExportModal from '@/components/ConfigImportExportModal'
import { useWebSocketContext } from '@/components/providers/WebSocketProvider'
import { useWebSocketMessage } from '@/hooks/use-websocket'

const { Search } = Input
const { Option } = Select
const { TextArea } = Input
const { TabPane } = Tabs
// 配置类型映射 - 支持15种类型
const CONFIG_TYPE_MAP = {
  STRING: { label: '字符串', color: 'blue' },
  TEXT: { label: '长文本', color: 'geekblue' },
  INTEGER: { label: '整数', color: 'green' },
  FLOAT: { label: '浮点数', color: 'lime' },
  BOOLEAN: { label: '布尔值', color: 'orange' },
  JSON: { label: 'JSON', color: 'purple' },
  ARRAY: { label: '数组', color: 'magenta' },
  EMAIL: { label: '邮箱', color: 'cyan' },
  URL: { label: '链接', color: 'gold' },
  ENUM: { label: '枚举', color: 'volcano' },
  PASSWORD: { label: '密码', color: 'red' },
  FILE: { label: '文件', color: 'blue' },
  COLOR: { label: '颜色', color: 'pink' },
  DATE: { label: '日期', color: 'green' },
  TIME: { label: '时间', color: 'purple' }
}

// 环境映射
const ENVIRONMENT_MAP = {
  dev: { label: '开发环境', color: 'blue' },
  test: { label: '测试环境', color: 'orange' },
  staging: { label: '预发环境', color: 'purple' },
  prod: { label: '生产环境', color: 'green' },
  demo: { label: '演示环境', color: 'cyan' },
  perf: { label: '性能测试环境', color: 'magenta' }
}

export default function ConfigManagement() {
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [environments, setEnvironments] = useState<EnvType[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEnvironment, setSelectedEnvironment] = useState<'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'>('dev')
  const [selectedGroup, setSelectedGroup] = useState<number | undefined>()
  const [searchText, setSearchText] = useState('')
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState<ConfigItem | null>(null)
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('configs')
  const [showValue, setShowValue] = useState<Record<string, boolean>>({})
  const [statsVisible, setStatsVisible] = useState(false)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsEnvironment, setStatsEnvironment] = useState<'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'>('dev')
  const [environmentStats, setEnvironmentStats] = useState<any>({})
  const [isImportExportVisible, setIsImportExportVisible] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [syncModalVisible, setSyncModalVisible] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [executionConfigVisible, setExecutionConfigVisible] = useState(false)
  const [executionConfigLoading, setExecutionConfigLoading] = useState(false)
  const [executionConfigSaving, setExecutionConfigSaving] = useState(false)
  const [executionConfigEnvironment, setExecutionConfigEnvironment] = useState<TestExecutionEnvironment>('test')
  const [executionConfigs, setExecutionConfigs] = useState<TestExecutionConfig[]>([])
  const [executionConfigFormVisible, setExecutionConfigFormVisible] = useState(false)
  const [editingExecutionConfig, setEditingExecutionConfig] = useState<TestExecutionConfig | null>(null)

  // WebSocket配置更新监听
  const { client, isConnected, subscribe } = useWebSocketContext()
  const [syncForm] = Form.useForm()
  const [executionConfigForm] = Form.useForm()
  const selectedExecutionFramework = Form.useWatch('framework', executionConfigForm) || 'auto'
  const selectedRunnerType = (Form.useWatch('runner_type', executionConfigForm) || 'local') as TestRunnerType
  const isBrowserExecution = ['auto', 'playwright', 'selenium'].includes(selectedExecutionFramework)
  const isJMeterExecution = selectedExecutionFramework === 'jmeter'
  const isCommandExecution = ['pytest', 'javascript', 'custom_command', 'har'].includes(selectedExecutionFramework)
  const isRemoteRunner = ['ssh', 'agent', 'docker', 'kubernetes', 'ci'].includes(selectedRunnerType)
  const isSshRunner = selectedRunnerType === 'ssh'
  const isAgentRunner = selectedRunnerType === 'agent'
  const isDockerRunner = selectedRunnerType === 'docker'
  const isKubernetesRunner = selectedRunnerType === 'kubernetes'
  const isCiRunner = selectedRunnerType === 'ci'

  // 分页配置
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  })

  // 加载数据
  useEffect(() => {
    loadData()
    loadGroups()
    loadEnvironments()
  }, [selectedEnvironment, selectedGroup, pagination.current, pagination.pageSize])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPagination(prev => {
        if (prev.current === 1) {
          loadData({ page: 1, search: searchText })
          return prev
        }
        return { ...prev, current: 1 }
      })
    }, 350)

    return () => window.clearTimeout(timer)
  }, [searchText])

  // WebSocket连接状态监听
  useEffect(() => {
    setWsConnected(isConnected)
  }, [isConnected])

  // WebSocket配置变更监听
  useEffect(() => {
    if (!client || !isConnected) return

    // 订阅配置变更消息
    const unsubscribeConfigChange = subscribe('config_change', (payload: any) => {
      console.log('收到配置变更通知:', payload)
      
      const { config_key, environment, change_type, user_id } = payload.data || payload
      
      // 只处理当前环境的变更
      if (environment && environment !== selectedEnvironment) {
        return
      }
      
      // 显示通知
      const changeTypeMap = {
        'CREATE': '创建',
        'UPDATE': '更新', 
        'DELETE': '删除'
      }
      
      notification.info({
        message: '配置变更通知',
        description: `配置 "${config_key}" 已被${changeTypeMap[change_type] || change_type}`,
        icon: <WifiOutlined style={{ color: '#1890ff' }} />,
        duration: 4
      })
      
      // 自动刷新配置列表
      setTimeout(() => {
        loadData()
      }, 500)
    })

    // 订阅审核状态变更消息
    const unsubscribeAuditChange = subscribe('audit_status_change', (payload: any) => {
      console.log('收到审核状态变更通知:', payload)
      
      notification.info({
        message: '审核状态变更',
        description: '配置审核状态已更新，请刷新页面查看最新状态',
        icon: <SettingOutlined style={{ color: '#52c41a' }} />,
        duration: 3
      })
    })

    return () => {
      unsubscribeConfigChange()
      unsubscribeAuditChange()
    }
  }, [client, isConnected, selectedEnvironment, subscribe])

  useEffect(() => {
    if (!executionConfigVisible) return
    loadExecutionConfigs()
  }, [executionConfigVisible, executionConfigEnvironment])

  const loadData = async (overrides: { page?: number; size?: number; search?: string } = {}) => {
    setLoading(true)
    const nextPage = overrides.page ?? pagination.current
    const nextSize = overrides.size ?? pagination.pageSize
    const nextSearch = (overrides.search ?? searchText).trim()
    try {
      const response = await ConfigService.getConfigs({
        environment: selectedEnvironment,
        group_id: selectedGroup,
        page: nextPage,
        size: nextSize,
        search: nextSearch || undefined
      })
      
      setConfigs(response.items)
      setPagination(prev => ({
        ...prev,
        current: nextPage,
        pageSize: nextSize,
        total: response.total
      }))
    } catch (error) {
      message.error('加载配置列表失败')
      console.error('加载配置失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadGroups = async () => {
    try {
      const groupList = await ConfigService.getConfigGroups()
      setGroups(groupList)
    } catch (error) {
      console.error('加载分组失败:', error)
    }
  }

  const loadEnvironments = async () => {
    try {
      const envList = await ConfigService.getEnvironments()
      setEnvironments(envList)
    } catch (error) {
      console.error('加载环境失败:', error)
    }
  }

  const loadEnvironmentStats = async (environment = statsEnvironment) => {
    setStatsLoading(true)
    try {
      const stats = await ConfigService.getEnvironmentStatistics(environment)
      setEnvironmentStats(stats)
    } catch (error) {
      message.error('加载环境统计失败')
    } finally {
      setStatsLoading(false)
    }
  }

  const openStatsDrawer = () => {
    setStatsEnvironment(selectedEnvironment)
    setStatsVisible(true)
    loadEnvironmentStats(selectedEnvironment)
  }

  // 表格列定义
  const columns = [
    {
      title: '配置键',
      dataIndex: 'config_key',
      key: 'config_key',
      width: 250,
      fixed: 'left' as const,
      render: (text: string, record: ConfigItem) => (
        <div>
          <div className="font-medium">{text}</div>
          {record.is_core && <Tag color="red">核心</Tag>}
          {record.is_encrypted && <Tag color="orange">加密</Tag>}
          {record.is_required && <Tag color="blue">必填</Tag>}
        </div>
      )
    },
    {
      title: '配置值',
      dataIndex: 'config_value',
      key: 'config_value',
      width: 200,
      render: (text: string, record: ConfigItem) => {
        const isPassword = record.config_type === 'PASSWORD'
        const shouldShow = showValue[record.id] || false
        
        if (isPassword && !shouldShow) {
          return (
            <div className="flex items-center space-x-2">
              <span className="text-gray-400 dark:text-gray-500">••••••••</span>
              <Button 
                type="link" 
                size="small" 
                icon={<EyeOutlined />}
                onClick={() => setShowValue(prev => ({...prev, [record.id]: true}))}
              />
            </div>
          )
        }
        
        return (
          <div className="flex items-center space-x-2">
            <span className="truncate max-w-[150px]" title={text}>{text}</span>
            <Button 
              type="link" 
              size="small" 
              icon={<CopyOutlined />}
              onClick={() => {
                navigator.clipboard.writeText(text)
                message.success('已复制到剪贴板')
              }}
            />
            {isPassword && (
              <Button 
                type="link" 
                size="small" 
                icon={<EyeOutlined />}
                onClick={() => setShowValue(prev => ({...prev, [record.id]: false}))}
              />
            )}
          </div>
        )
      }
    },
    {
      title: '类型',
      dataIndex: 'config_type',
      key: 'config_type',
      width: 100,
      render: (type: keyof typeof CONFIG_TYPE_MAP) => (
        <Tag color={CONFIG_TYPE_MAP[type]?.color}>
          {CONFIG_TYPE_MAP[type]?.label}
        </Tag>
      )
    },
    {
      title: '分组',
      dataIndex: 'group_id',
      key: 'group_id',
      width: 120,
      render: (groupId: number) => {
        const group = groups.find(g => g.id === groupId)
        return group ? (
          <Tag color={group.color || 'default'}>
            {group.group_name}
          </Tag>
        ) : '-'
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      render: (text: string) => (
        <span className="truncate" title={text}>{text || '-'}</span>
      )
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 80,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 150,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: ConfigItem) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ]

  // 处理编辑
  const handleEdit = (config: ConfigItem) => {
    setEditingConfig(config)
    form.setFieldsValue({
      ...config,
      tags: config.tags?.join(',') || ''
    })
    setIsModalVisible(true)
  }

  // 处理删除
  const handleDelete = (config: ConfigItem) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除配置 "${config.config_key}" 吗？`,
      onOk: async () => {
        try {
          await ConfigService.deleteConfig(config.config_key, selectedEnvironment)
          message.success('删除成功')
          loadData()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  // 处理新增/编辑提交
  const handleSubmit = async (values: any) => {
    try {
      const data = {
        ...values,
        tags: values.tags ? values.tags.split(',').map((tag: string) => tag.trim()).filter(Boolean) : []
      }

      if (editingConfig) {
        // 编辑
        await ConfigService.updateConfig(editingConfig.config_key, data, selectedEnvironment)
        message.success('更新成功')
      } else {
        // 新增
        await ConfigService.createConfig({
          ...data,
          environment: selectedEnvironment
        })
        message.success('创建成功')
      }

      setIsModalVisible(false)
      form.resetFields()
      setEditingConfig(null)
      loadData()
    } catch (error) {
      message.error(editingConfig ? '更新失败' : '创建失败')
    }
  }

  const openSyncModal = () => {
    syncForm.setFieldsValue({
      source_env: selectedEnvironment,
      target_env: selectedEnvironment === 'prod' ? 'test' : 'prod'
    })
    setSyncModalVisible(true)
  }

  const handleSyncSubmit = async (values: { source_env: string; target_env: string; config_keys?: string }) => {
    if (values.source_env === values.target_env) {
      message.warning('源环境和目标环境不能相同')
      return
    }

    const configKeys = values.config_keys
      ?.split('\n')
      .map((key) => key.trim())
      .filter(Boolean)

    setSyncing(true)
    try {
      await ConfigService.syncEnvironments(values.source_env, values.target_env, configKeys?.length ? configKeys : undefined)
      message.success('环境同步任务已提交')
      setSyncModalVisible(false)
      syncForm.resetFields()
      if (values.target_env === selectedEnvironment) {
        loadData()
      }
    } catch (error) {
      message.error('环境同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const openExecutionConfigModal = () => {
    setExecutionConfigEnvironment(selectedEnvironment)
    setExecutionConfigVisible(true)
  }

  const loadExecutionConfigs = async () => {
    setExecutionConfigLoading(true)
    try {
      const list = await TestExecutionConfigService.list(executionConfigEnvironment)
      setExecutionConfigs(list)
    } catch (error) {
      message.error('加载测试执行配置失败')
      setExecutionConfigs([])
    } finally {
      setExecutionConfigLoading(false)
    }
  }

  const getDefaultExecutionFormValues = (framework = 'auto'): Record<string, any> => {
    if (framework === 'jmeter') {
      return {
        runner_type: 'ssh',
        runner_port: 22,
        runner_workdir: '/opt/test-runs/jmeter',
        command_template: 'jmeter -n -t {script} -l {result_jtl} -j {log_file} -e -o {report_dir}',
        result_collection: 'ssh_download',
        result_format: 'jtl',
        result_file_pattern: '*.jtl',
        report_directory: 'report',
        timeout: 1800,
      }
    }
    if (framework === 'playwright') {
      return {
        runner_type: 'local',
        command_template: 'npx playwright test {script}',
        result_collection: 'local',
        result_format: 'playwright-report',
        artifact_patterns: 'playwright-report/**\ntest-results/**',
        report_directory: 'playwright-report',
      }
    }
    if (framework === 'selenium') {
      return {
        runner_type: 'local',
        command_template: 'python {script}',
        result_collection: 'local',
        result_format: 'junit',
        result_file_pattern: '*.xml',
        timeout: 1200,
      }
    }
    if (framework === 'pytest') {
      return {
        runner_type: 'local',
        command_template: 'pytest {script} --junitxml={result_file}',
        result_collection: 'local',
        result_format: 'junit',
        result_file_pattern: '*.xml',
      }
    }
    if (framework === 'javascript') {
      return {
        runner_type: 'local',
        command_template: 'node {script}',
        result_collection: 'local',
        result_format: 'json',
      }
    }
    if (framework === 'har') {
      return {
        runner_type: 'local',
        result_collection: 'local',
        result_format: 'json',
        result_file_pattern: '*.json',
      }
    }
    return {
      runner_type: 'local',
      result_collection: 'local',
      result_format: 'text',
      timeout: 900,
    }
  }

  const openExecutionConfigForm = (config?: TestExecutionConfig) => {
    const defaults = getDefaultExecutionFormValues(config?.framework || 'auto')
    setEditingExecutionConfig(config || null)
    executionConfigForm.setFieldsValue({
      name: config?.name || '',
      framework: config?.framework || 'auto',
      browser: config?.browser || 'chrome',
      parallel_count: config?.parallel_count || 1,
      retry_count: config?.retry_count || 0,
      timeout: config?.timeout || defaults.timeout || 900,
      headless: config?.headless ?? true,
      enabled: config?.enabled ?? true,
      runner_type: config?.runner_type || defaults.runner_type,
      runner_name: config?.runner_name || '',
      runner_host: config?.runner_host || '',
      runner_port: config?.runner_port || defaults.runner_port,
      runner_user: config?.runner_user || '',
      runner_os: config?.runner_os || '',
      runner_workdir: config?.runner_workdir || defaults.runner_workdir || '',
      credential_ref: config?.credential_ref || '',
      agent_id: config?.agent_id || '',
      agent_callback_url: config?.agent_callback_url || '',
      docker_image: config?.docker_image || defaults.docker_image || '',
      docker_network: config?.docker_network || '',
      docker_volumes: config?.docker_volumes || '',
      docker_args: config?.docker_args || '',
      kubernetes_context: config?.kubernetes_context || '',
      kubernetes_namespace: config?.kubernetes_namespace || '',
      kubernetes_image: config?.kubernetes_image || defaults.kubernetes_image || '',
      kubernetes_job_template: config?.kubernetes_job_template || '',
      ci_provider: config?.ci_provider || '',
      ci_pipeline_url: config?.ci_pipeline_url || '',
      ci_project: config?.ci_project || '',
      ci_branch: config?.ci_branch || '',
      ci_token_ref: config?.ci_token_ref || '',
      ci_variables: config?.ci_variables || '',
      tool_home: config?.tool_home || '',
      executable_path: config?.executable_path || '',
      working_directory: config?.working_directory || '',
      command: config?.command || '',
      command_template: config?.command_template || defaults.command_template || '',
      pre_command: config?.pre_command || '',
      post_command: config?.post_command || '',
      result_collection: config?.result_collection || defaults.result_collection,
      result_directory: config?.result_directory || '',
      result_file_pattern: config?.result_file_pattern || defaults.result_file_pattern || '',
      report_directory: config?.report_directory || defaults.report_directory || '',
      result_format: config?.result_format || defaults.result_format,
      artifact_patterns: config?.artifact_patterns || defaults.artifact_patterns || '',
      jmeter_properties: config?.jmeter_properties || '',
      distributed_hosts: config?.distributed_hosts || '',
      environment_variables: config?.environment_variables
        ? Object.entries(config.environment_variables).map(([key, value]) => `${key}=${value}`).join('\n')
        : '',
      description: config?.description || '',
    })
    setExecutionConfigFormVisible(true)
  }

  const parseEnvironmentVariables = (value?: string) => {
    const variables: Record<string, string> = {}
    String(value || '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .forEach((line) => {
        const separatorIndex = line.indexOf('=')
        if (separatorIndex <= 0) return
        const key = line.slice(0, separatorIndex).trim()
        const val = line.slice(separatorIndex + 1).trim()
        if (key) variables[key] = val
      })
    return Object.keys(variables).length ? variables : undefined
  }

  const handleExecutionConfigSubmit = async (values: any) => {
    setExecutionConfigSaving(true)
    try {
      const frameworkLabel = FRAMEWORK_OPTIONS.find((item) => item.value === values.framework)?.label || values.framework
      const nextConfig: Partial<TestExecutionConfig> = {
        ...editingExecutionConfig,
        name: values.name,
        environment: executionConfigEnvironment,
        framework: values.framework,
        framework_label: frameworkLabel,
        browser: values.browser,
        parallel_count: values.parallel_count,
        retry_count: values.retry_count,
        timeout: values.timeout,
        headless: values.headless,
        enabled: values.enabled,
        runner_type: values.runner_type,
        runner_name: values.runner_name,
        runner_host: values.runner_host,
        runner_port: values.runner_port,
        runner_user: values.runner_user,
        runner_os: values.runner_os,
        runner_workdir: values.runner_workdir,
        credential_ref: values.credential_ref,
        agent_id: values.agent_id,
        agent_callback_url: values.agent_callback_url,
        docker_image: values.docker_image,
        docker_network: values.docker_network,
        docker_volumes: values.docker_volumes,
        docker_args: values.docker_args,
        kubernetes_context: values.kubernetes_context,
        kubernetes_namespace: values.kubernetes_namespace,
        kubernetes_image: values.kubernetes_image,
        kubernetes_job_template: values.kubernetes_job_template,
        ci_provider: values.ci_provider,
        ci_pipeline_url: values.ci_pipeline_url,
        ci_project: values.ci_project,
        ci_branch: values.ci_branch,
        ci_token_ref: values.ci_token_ref,
        ci_variables: values.ci_variables,
        tool_home: values.tool_home,
        executable_path: values.executable_path,
        working_directory: values.working_directory,
        command: values.command,
        command_template: values.command_template,
        pre_command: values.pre_command,
        post_command: values.post_command,
        result_collection: values.result_collection,
        result_directory: values.result_directory,
        result_file_pattern: values.result_file_pattern,
        report_directory: values.report_directory,
        result_format: values.result_format,
        artifact_patterns: values.artifact_patterns,
        jmeter_properties: values.jmeter_properties,
        distributed_hosts: values.distributed_hosts,
        environment_variables: parseEnvironmentVariables(values.environment_variables),
        description: values.description,
      }
      const saved = await TestExecutionConfigService.upsert(executionConfigEnvironment, nextConfig)
      setExecutionConfigs(saved)
      setExecutionConfigFormVisible(false)
      setEditingExecutionConfig(null)
      executionConfigForm.resetFields()
      loadData()
      message.success(editingExecutionConfig ? '测试执行配置已更新' : '测试执行配置已创建')
    } catch (error) {
      message.error('保存测试执行配置失败')
    } finally {
      setExecutionConfigSaving(false)
    }
  }

  const handleDeleteExecutionConfig = async (config: TestExecutionConfig) => {
    setExecutionConfigLoading(true)
    try {
      const nextList = await TestExecutionConfigService.remove(executionConfigEnvironment, config.id)
      setExecutionConfigs(nextList)
      loadData()
      message.success('测试执行配置已删除')
    } catch (error) {
      message.error('删除测试执行配置失败')
    } finally {
      setExecutionConfigLoading(false)
    }
  }

  const initializeExecutionConfigs = async () => {
    setExecutionConfigLoading(true)
    try {
      const list = await TestExecutionConfigService.initializeDefaults(executionConfigEnvironment)
      setExecutionConfigs(list)
      loadData()
      message.success('默认测试执行配置已初始化')
    } catch (error) {
      message.error('初始化测试执行配置失败')
    } finally {
      setExecutionConfigLoading(false)
    }
  }

  const executionConfigColumns = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      width: 210,
      render: (text: string, record: TestExecutionConfig) => (
        <div>
          <div className="font-medium">{text}</div>
          {record.description && <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{record.description}</div>}
        </div>
      )
    },
    {
      title: '执行方式',
      dataIndex: 'framework_label',
      key: 'framework_label',
      width: 150,
      render: (text: string, record: TestExecutionConfig) => <Tag color="blue">{text || record.framework}</Tag>
    },
    {
      title: '执行节点',
      key: 'runner',
      width: 180,
      render: (_: any, record: TestExecutionConfig) => {
        const runnerLabel = RUNNER_TYPE_OPTIONS.find((item) => item.value === record.runner_type)?.label || record.runner_type || '本机执行'
        return (
          <div>
            <div className="font-medium">{record.runner_name || runnerLabel}</div>
            <div className="text-xs text-muted-foreground">
              {record.runner_host ? `${record.runner_user ? `${record.runner_user}@` : ''}${record.runner_host}${record.runner_port ? `:${record.runner_port}` : ''}` : runnerLabel}
            </div>
          </div>
        )
      }
    },
    {
      title: '并发/重试',
      key: 'parallel_retry',
      width: 110,
      render: (_: any, record: TestExecutionConfig) => `${record.parallel_count} / ${record.retry_count}`
    },
    {
      title: '超时',
      dataIndex: 'timeout',
      key: 'timeout',
      width: 90,
      render: (value: number) => `${value || 0}s`
    },
    {
      title: '工具与采集',
      key: 'runtime',
      width: 220,
      render: (_: any, record: TestExecutionConfig) => (
        <Space size={[4, 4]} wrap>
          {record.executable_path && <Tag color="geekblue">工具路径</Tag>}
          {record.docker_image && <Tag color="blue">Docker</Tag>}
          {record.agent_id && <Tag color="green">Agent</Tag>}
          {record.kubernetes_namespace && <Tag color="lime">K8s</Tag>}
          {record.ci_provider && <Tag color="gold">{record.ci_provider}</Tag>}
          {record.command_template && <Tag color="purple">命令模板</Tag>}
          {record.result_collection && <Tag color="cyan">{RESULT_COLLECTION_OPTIONS.find((item) => item.value === record.result_collection)?.label || record.result_collection}</Tag>}
          {record.result_file_pattern && <Tag>{record.result_file_pattern}</Tag>}
          {['auto', 'playwright', 'selenium'].includes(record.framework) && record.headless && <Tag>无头</Tag>}
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean) => <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '停用'}</Tag>
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: TestExecutionConfig) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openExecutionConfigForm(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该测试执行配置？" onConfirm={() => handleDeleteExecutionConfig(record)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  const statsTotal = Number(environmentStats.total_configs || 0)
  const statsEnabled = Number(environmentStats.enabled_configs || 0)
  const statsDisabled = Number(environmentStats.disabled_configs || 0)
  const statsCore = Number(environmentStats.core_configs || 0)
  const statsEncrypted = Number(environmentStats.encrypted_configs || 0)
  const statsRequired = Number(environmentStats.required_configs || 0)
  const statsRecentlyUpdated = Number(environmentStats.recently_updated_configs || 0)
  const getStatsPercent = (value: number) => (statsTotal > 0 ? Math.round((value / statsTotal) * 100) : 0)
  const statsTypeRows = Object.entries(environmentStats.type_statistics || {})
    .map(([type, count]) => ({
      key: type,
      type,
      label: CONFIG_TYPE_MAP[type as keyof typeof CONFIG_TYPE_MAP]?.label || type,
      color: CONFIG_TYPE_MAP[type as keyof typeof CONFIG_TYPE_MAP]?.color || 'default',
      count: Number(count || 0),
      percent: statsTotal > 0 ? Math.round((Number(count || 0) / statsTotal) * 100) : 0,
    }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)
  const statsGroupRows = (environmentStats.group_statistics || [])
    .map((item: any) => ({
      key: item.group_id ?? 'ungrouped',
      group_name: item.group_name || '未分组',
      config_count: Number(item.config_count || 0),
      percent: statsTotal > 0 ? Math.round((Number(item.config_count || 0) / statsTotal) * 100) : 0,
    }))
    .filter((item: any) => item.config_count > 0)
    .sort((a: any, b: any) => b.config_count - a.config_count)
  const statsLastUpdated = environmentStats.last_updated_at
    ? new Date(environmentStats.last_updated_at).toLocaleString()
    : '-'

  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap justify-end gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              icon={<ImportOutlined />}
              onClick={() => setIsImportExportVisible(true)}
            >
              导入导出
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={openStatsDrawer}
            >
              统计信息
            </Button>
            <Button
              icon={<SyncOutlined />}
              onClick={openSyncModal}
            >
              环境同步
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={openExecutionConfigModal}
            >
              测试执行配置
            </Button>
            <Tag
              icon={<WifiOutlined />}
              color={wsConnected ? 'success' : 'default'}
              className="m-0 flex h-8 items-center"
              title={wsConnected ? 'WebSocket已连接，实时接收配置更新' : 'WebSocket未连接'}
            >
              {wsConnected ? '实时更新' : '离线模式'}
            </Tag>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingConfig(null)
                form.resetFields()
                setIsModalVisible(true)
              }}
            >
              新增配置
            </Button>
          </div>
        </div>
      </div>

      <Card size="small">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold">配置列表</div>
            <div className="text-xs text-muted-foreground">共 {pagination.total} 条记录</div>
          </div>
          <div className="grid w-full grid-cols-1 gap-2 md:w-auto md:grid-cols-[130px_170px_260px]">
            <Select
              value={selectedEnvironment}
              onChange={(value) => {
                setSelectedEnvironment(value)
                setPagination(prev => ({ ...prev, current: 1 }))
              }}
              placeholder="环境"
            >
              {Object.entries(ENVIRONMENT_MAP).map(([value, item]) => (
                <Option key={value} value={value}>{item.label}</Option>
              ))}
            </Select>
            <Select
              value={selectedGroup}
              onChange={(value) => {
                setSelectedGroup(value)
                setPagination(prev => ({ ...prev, current: 1 }))
              }}
              placeholder="全部分组"
              allowClear
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.group_name}
                </Option>
              ))}
            </Select>
            <Search
              placeholder="搜索配置键、值、描述、标签或分组"
              value={searchText}
              allowClear
              onChange={(e) => {
                setSearchText(e.target.value)
              }}
              onSearch={(value) => {
                setSearchText(value)
                setPagination(prev => ({ ...prev, current: 1 }))
                loadData({ page: 1, search: value })
              }}
            />
          </div>
        </div>
        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1200 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            onChange: (page, size) => {
              setPagination(prev => ({
                ...prev,
                current: page,
                pageSize: size || 20
              }))
            }
          }}
        />
      </Card>

      {/* 新增/编辑对话框 */}
      <Modal
        title={editingConfig ? '编辑配置' : '新增配置'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false)
          form.resetFields()
          setEditingConfig(null)
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="config_key"
            label="配置键"
            rules={[{ required: true, message: '请输入配置键' }]}
          >
            <Input placeholder="如: system.app_name" disabled={!!editingConfig} />
          </Form.Item>
          
          <Form.Item
            name="config_value"
            label="配置值"
            rules={[{ required: true, message: '请输入配置值' }]}
          >
            <TextArea rows={3} placeholder="请输入配置值" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="config_type"
                label="配置类型"
                rules={[{ required: true, message: '请选择配置类型' }]}
              >
                <Select placeholder="请选择">
                  {Object.entries(CONFIG_TYPE_MAP).map(([key, value]) => (
                    <Option key={key} value={key}>{value.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="group_id"
                label="配置分组"
              >
                <Select placeholder="请选择分组" allowClear>
                  {groups.map(group => (
                    <Option key={group.id} value={group.id}>
                      {group.group_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={2} placeholder="配置项的详细描述" />
          </Form.Item>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="is_core" valuePropName="checked">
                <Switch checkedChildren="核心" unCheckedChildren="普通" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_required" valuePropName="checked">
                <Switch checkedChildren="必填" unCheckedChildren="可选" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_encrypted" valuePropName="checked">
                <Switch checkedChildren="加密" unCheckedChildren="明文" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_enabled" valuePropName="checked" initialValue={true}>
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 统计信息抽屉 */}
      <Drawer
        title="环境配置统计"
        placement="right"
        onClose={() => setStatsVisible(false)}
        open={statsVisible}
        width={900}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Space wrap>
              <span className="text-sm text-muted-foreground">统计环境</span>
              <Select
                value={statsEnvironment}
                onChange={(value) => {
                  setStatsEnvironment(value)
                  loadEnvironmentStats(value)
                }}
                style={{ width: 150 }}
              >
                {Object.entries(ENVIRONMENT_MAP).map(([value, item]) => (
                  <Option key={value} value={value}>{item.label}</Option>
                ))}
              </Select>
            </Space>
            <Button icon={<SyncOutlined />} loading={statsLoading} onClick={() => loadEnvironmentStats(statsEnvironment)}>
              刷新
            </Button>
          </div>

          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Statistic title="配置总数" value={statsTotal} suffix="个" />
            </Col>
            <Col span={6}>
              <Statistic title="启用" value={statsEnabled} suffix="个" valueStyle={{ color: '#389e0d' }} />
            </Col>
            <Col span={6}>
              <Statistic title="停用" value={statsDisabled} suffix="个" valueStyle={{ color: statsDisabled ? '#d4380d' : undefined }} />
            </Col>
            <Col span={6}>
              <Statistic title="近 7 天变更" value={statsRecentlyUpdated} suffix="个" />
            </Col>
          </Row>

          <Card size="small" title="配置健康度">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>启用率</span>
                  <span>{getStatsPercent(statsEnabled)}%</span>
                </div>
                <Progress percent={getStatsPercent(statsEnabled)} size="small" status={statsDisabled ? 'active' : 'success'} />
              </Col>
              <Col span={12}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>加密占比</span>
                  <span>{getStatsPercent(statsEncrypted)}%</span>
                </div>
                <Progress percent={getStatsPercent(statsEncrypted)} size="small" strokeColor="#722ed1" />
              </Col>
              <Col span={12}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>核心配置</span>
                  <span>{statsCore} 个</span>
                </div>
                <Progress percent={getStatsPercent(statsCore)} size="small" strokeColor="#cf1322" />
              </Col>
              <Col span={12}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>必填配置</span>
                  <span>{statsRequired} 个</span>
                </div>
                <Progress percent={getStatsPercent(statsRequired)} size="small" strokeColor="#0958d9" />
              </Col>
            </Row>
            <div className="mt-3 text-xs text-muted-foreground">
              最后更新时间：{statsLastUpdated}
            </div>
          </Card>

          <Row gutter={[12, 12]}>
            <Col span={12}>
              <Card size="small" title="类型分布">
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  loading={statsLoading}
                  dataSource={statsTypeRows}
                  locale={{ emptyText: '暂无类型统计' }}
                  columns={[
                    {
                      title: '类型',
                      dataIndex: 'label',
                      key: 'label',
                      render: (_: string, record: any) => <Tag color={record.color}>{record.label}</Tag>,
                    },
                    {
                      title: '数量',
                      dataIndex: 'count',
                      key: 'count',
                      width: 70,
                      align: 'right' as const,
                    },
                    {
                      title: '占比',
                      dataIndex: 'percent',
                      key: 'percent',
                      width: 80,
                      render: (value: number) => `${value}%`,
                    },
                  ]}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="分组分布">
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  loading={statsLoading}
                  dataSource={statsGroupRows}
                  locale={{ emptyText: '暂无分组统计' }}
                  columns={[
                    {
                      title: '分组',
                      dataIndex: 'group_name',
                      key: 'group_name',
                      ellipsis: true,
                    },
                    {
                      title: '数量',
                      dataIndex: 'config_count',
                      key: 'config_count',
                      width: 70,
                      align: 'right' as const,
                    },
                    {
                      title: '占比',
                      dataIndex: 'percent',
                      key: 'percent',
                      width: 80,
                      render: (value: number) => `${value}%`,
                    },
                  ]}
                />
              </Card>
            </Col>
          </Row>
        </div>
      </Drawer>

      {/* 导入导出模态框 */}
      <ConfigImportExportModal
        visible={isImportExportVisible}
        onCancel={() => setIsImportExportVisible(false)}
        onSuccess={() => {
          setIsImportExportVisible(false)
          loadData() // 重新加载数据
        }}
        environment={selectedEnvironment}
        groupId={selectedGroup}
      />

      <Modal
        title="环境同步"
        open={syncModalVisible}
        onCancel={() => {
          setSyncModalVisible(false)
          syncForm.resetFields()
        }}
        onOk={() => syncForm.submit()}
        confirmLoading={syncing}
        width={560}
      >
        <Form form={syncForm} layout="vertical" onFinish={handleSyncSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="source_env" label="源环境" rules={[{ required: true, message: '请选择源环境' }]}>
                <Select>
                  {Object.entries(ENVIRONMENT_MAP).map(([value, item]) => (
                    <Option key={value} value={value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="target_env" label="目标环境" rules={[{ required: true, message: '请选择目标环境' }]}>
                <Select>
                  {Object.entries(ENVIRONMENT_MAP).map(([value, item]) => (
                    <Option key={value} value={value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="config_keys" label="指定配置键">
            <TextArea rows={4} placeholder="每行一个配置键；留空则同步全部可同步配置" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="测试执行配置"
        open={executionConfigVisible}
        onCancel={() => {
          setExecutionConfigVisible(false)
          setExecutionConfigFormVisible(false)
          setEditingExecutionConfig(null)
        }}
        footer={null}
        width={1080}
        destroyOnHidden
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Space wrap>
              <span className="text-sm text-muted-foreground">配置环境</span>
              <Select
                value={executionConfigEnvironment}
                onChange={setExecutionConfigEnvironment}
                style={{ width: 160 }}
              >
                {EXECUTION_ENVIRONMENTS.map((item) => (
                  <Option key={item.value} value={item.value}>{item.label}</Option>
                ))}
              </Select>
            </Space>
            <Space wrap>
              <Button onClick={initializeExecutionConfigs} loading={executionConfigLoading}>
                初始化默认配置
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => openExecutionConfigForm()}>
                新增执行配置
              </Button>
            </Space>
          </div>
          <Table
            columns={executionConfigColumns}
            dataSource={executionConfigs}
            rowKey="id"
            loading={executionConfigLoading}
            size="middle"
            scroll={{ x: 1050 }}
            pagination={false}
            locale={{ emptyText: '当前环境还没有测试执行配置，可初始化默认配置或手动新增' }}
          />
        </div>
      </Modal>

      <Modal
        title={editingExecutionConfig ? '编辑测试执行配置' : '新增测试执行配置'}
        open={executionConfigFormVisible}
        onCancel={() => {
          setExecutionConfigFormVisible(false)
          setEditingExecutionConfig(null)
          executionConfigForm.resetFields()
        }}
        onOk={() => executionConfigForm.submit()}
        confirmLoading={executionConfigSaving}
        width={960}
        destroyOnHidden
      >
        <Form
          form={executionConfigForm}
          layout="vertical"
          onFinish={handleExecutionConfigSubmit}
          onValuesChange={(changedValues) => {
            if (changedValues.framework) {
              executionConfigForm.setFieldsValue(getDefaultExecutionFormValues(changedValues.framework))
            }
            if (changedValues.runner_type) {
              const runnerType = changedValues.runner_type as TestRunnerType
              const nextCollection = runnerType === 'ssh'
                ? 'ssh_download'
                : runnerType === 'agent'
                  ? 'agent_callback'
                  : runnerType === 'ci'
                    ? 'ci_artifact'
                    : 'local'
              executionConfigForm.setFieldsValue({ result_collection: nextCollection })
            }
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="配置名称" rules={[{ required: true, message: '请输入配置名称' }]}>
                <Input placeholder="如：测试环境 JMeter 压测节点" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="framework" label="执行方式" rules={[{ required: true, message: '请选择执行方式' }]}>
                <Select>
                  {FRAMEWORK_OPTIONS.map((item) => (
                    <Option key={item.value} value={item.value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="runner_type" label="执行节点类型" rules={[{ required: true, message: '请选择执行节点类型' }]}>
                <Select>
                  {RUNNER_TYPE_OPTIONS.map((item) => (
                    <Option key={item.value} value={item.value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="runner_name" label="节点名称">
                <Input placeholder="如：性能测试机-01" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="enabled" label="启用状态" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          {isSshRunner && (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="runner_host"
                  label="目标机器"
                  rules={selectedRunnerType === 'ssh' ? [{ required: true, message: '请输入目标机器 IP 或域名' }] : []}
                >
                  <Input placeholder="如：10.10.20.15" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="runner_user" label="登录用户">
                  <Input placeholder="如：tester" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="runner_port" label="端口">
                  <InputNumber min={0} max={65535} precision={0} className="w-full" placeholder="SSH 默认 22" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="runner_workdir" label="远端工作目录">
                  <Input placeholder="如：/opt/test-runs/jmeter 或 D:\\test-runs\\jmeter" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="credential_ref" label="凭据引用">
                  <Input placeholder="填写已加密保存的凭据键，不在这里保存明文密码" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {isAgentRunner && (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="agent_id" label="Agent ID" rules={[{ required: true, message: '请输入 Agent ID' }]}>
                  <Input placeholder="如：agent-test-01" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="runner_host" label="Agent 所在机器">
                  <Input placeholder="如：10.10.20.21" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="agent_callback_url" label="结果回调地址">
                  <Input placeholder="Agent 执行完成后回调的平台地址" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="runner_workdir" label="Agent 工作目录">
                  <Input placeholder="如：/opt/agent/workspace" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="credential_ref" label="Agent 凭据引用">
                  <Input placeholder="填写已加密保存的 token/凭据键" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {isDockerRunner && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="docker_image" label="Docker 镜像" rules={[{ required: true, message: '请输入 Docker 镜像' }]}>
                  <Input placeholder="如：mcr.microsoft.com/playwright:v1.49.1-jammy" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="docker_network" label="网络">
                  <Input placeholder="可选；如：host、bridge、test-net" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="docker_volumes" label="额外挂载">
                  <TextArea rows={2} placeholder="每行一个挂载，如：D:\\data:/data 或 /opt/cache:/cache" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="docker_args" label="Docker 参数">
                  <TextArea rows={2} placeholder="每行一个参数，如：--shm-size=1g&#10;--ipc=host" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {isKubernetesRunner && (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="kubernetes_context" label="集群上下文">
                  <Input placeholder="可选；kubectl context" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="kubernetes_namespace" label="Namespace" rules={[{ required: true, message: '请输入 Namespace' }]}>
                  <Input placeholder="如：qa-test" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="kubernetes_image" label="执行镜像" rules={[{ required: true, message: '请输入执行镜像' }]}>
                  <Input placeholder="如：python:3.12 或 playwright 镜像" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="kubernetes_job_template" label="Job 模板">
                  <TextArea rows={4} placeholder="可选；填写 Job YAML 模板，平台后续按模板创建一次性执行任务" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {isCiRunner && (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="ci_provider" label="CI 平台" rules={[{ required: true, message: '请选择 CI 平台' }]}>
                  <Select placeholder="请选择">
                    <Option value="jenkins">Jenkins</Option>
                    <Option value="gitlab">GitLab CI</Option>
                    <Option value="github">GitHub Actions</Option>
                    <Option value="custom">自定义流水线</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item name="ci_pipeline_url" label="流水线地址" rules={[{ required: true, message: '请输入流水线地址' }]}>
                  <Input placeholder="如：Jenkins job URL 或 GitLab pipeline trigger URL" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="ci_project" label="项目标识">
                  <Input placeholder="如：group/project 或 job name" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="ci_branch" label="分支">
                  <Input placeholder="如：main、release/test" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="ci_token_ref" label="Token 凭据引用">
                  <Input placeholder="填写已加密保存的 token 配置键" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="ci_variables" label="流水线变量">
                  <TextArea rows={3} placeholder="每行一个 KEY=VALUE，例如 TEST_ENV=test&#10;SUITE=smoke" />
                </Form.Item>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="parallel_count" label="并发数" rules={[{ required: true, message: '请输入并发数' }]}>
                <InputNumber min={1} max={100} precision={0} className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="retry_count" label="重试次数" rules={[{ required: true, message: '请输入重试次数' }]}>
                <InputNumber min={0} max={20} precision={0} className="w-full" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="timeout" label="超时时间（秒）" rules={[{ required: true, message: '请输入超时时间' }]}>
                <InputNumber min={1} max={1800} precision={0} className="w-full" />
              </Form.Item>
            </Col>
          </Row>

          {isBrowserExecution && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="browser" label="浏览器" rules={[{ required: true, message: '请选择浏览器' }]}>
                  <Select>
                    {BROWSER_OPTIONS.map((item) => (
                      <Option key={item.value} value={item.value}>{item.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="headless" label="无头模式" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="working_directory" label={isRemoteRunner ? '本机准备目录' : '工作目录'}>
                <Input placeholder="脚本执行或临时产物生成的目录；留空使用系统临时目录" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="runner_os" label="节点系统">
                <Select allowClear placeholder="可选">
                  <Option value="linux">Linux</Option>
                  <Option value="windows">Windows</Option>
                  <Option value="macos">macOS</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {(isJMeterExecution || isCommandExecution || isBrowserExecution || selectedExecutionFramework === 'auto') && (
            <>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="tool_home" label={isJMeterExecution ? 'JMETER_HOME' : '工具/运行时目录'}>
                    <Input placeholder={isJMeterExecution ? '如：/opt/apache-jmeter-5.6.3' : '如：Node/Python/浏览器驱动安装目录，可选'} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="executable_path" label={isJMeterExecution ? 'JMeter 可执行文件' : '可执行文件路径'}>
                    <Input placeholder={isJMeterExecution ? '如：/opt/apache-jmeter-5.6.3/bin/jmeter' : '如：python、node、npx 或绝对路径，可选'} />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="command_template"
                label="命令模板"
                tooltip="可使用 {script}、{result_file}、{result_jtl}、{report_dir}、{log_file} 占位符"
              >
                <TextArea rows={2} placeholder="例如：npx playwright test {script} 或 pytest {script} --junitxml={result_file}" />
              </Form.Item>
            </>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="result_collection" label="结果采集方式" rules={[{ required: true, message: '请选择结果采集方式' }]}>
                <Select>
                  {RESULT_COLLECTION_OPTIONS.map((item) => (
                    <Option key={item.value} value={item.value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="result_format" label="结果格式">
                <Select>
                  {RESULT_FORMAT_OPTIONS.map((item) => (
                    <Option key={item.value} value={item.value}>{item.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="result_file_pattern" label="结果文件">
                <Input placeholder="如：*.jtl、*.xml" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="result_directory" label="结果目录">
                <Input placeholder="如：/opt/test-runs/jmeter/results" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="report_directory" label="报告目录">
                <Input placeholder="如：report 或 /opt/test-runs/jmeter/report" />
              </Form.Item>
            </Col>
          </Row>

          {isJMeterExecution && (
            <>
              <Form.Item name="jmeter_properties" label="JMeter 属性">
                <TextArea rows={3} placeholder="每行一个 -J 参数，例如：threads=50&#10;ramp_time=60&#10;duration=300" />
              </Form.Item>
              <Form.Item name="distributed_hosts" label="分布式压测节点">
                <Input placeholder="可选；多个节点用英文逗号分隔，如：10.1.1.11,10.1.1.12" />
              </Form.Item>
            </>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="pre_command" label="前置命令">
                <TextArea rows={2} placeholder="可选；执行测试前准备环境" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="post_command" label="后置命令">
                <TextArea rows={2} placeholder="可选；执行后清理或归档" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="command" label="固定执行命令">
            <TextArea rows={2} placeholder="可选；填写后优先使用该命令，适合固定脚本或流水线触发命令" />
          </Form.Item>

          <Form.Item name="artifact_patterns" label="产物匹配规则">
            <TextArea rows={2} placeholder="每行一个规则，例如 report/** 或 test-results/**" />
          </Form.Item>

          <Form.Item name="environment_variables" label="环境变量">
            <TextArea rows={3} placeholder="每行一个 KEY=VALUE，例如 BASE_URL=https://test.example.com" />
          </Form.Item>

          <Form.Item name="description" label="说明">
            <TextArea rows={2} placeholder="说明该配置适用的测试范围、执行节点或注意事项" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
