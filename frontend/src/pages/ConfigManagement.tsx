import React, { useState, useEffect } from 'react'
import { Card, Button, Table, Space, Input, Select, Modal, Form, Switch, Tag, Tabs, message, Drawer, Row, Col, Statistic, notification } from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, 
  SyncOutlined, SettingOutlined, EyeOutlined, CopyOutlined,
  EnvironmentOutlined, LockOutlined, UnlockOutlined, HistoryOutlined,
  ImportOutlined, ExportOutlined, WifiOutlined
} from '@ant-design/icons'
import { ConfigService, ConfigItem, ConfigGroup, Environment as EnvType, ConfigCreateRequest, ConfigUpdateRequest } from '@/services/config-service'
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
  const [environmentStats, setEnvironmentStats] = useState<any>({})
  const [isImportExportVisible, setIsImportExportVisible] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [syncModalVisible, setSyncModalVisible] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // WebSocket配置更新监听
  const { client, isConnected, subscribe } = useWebSocketContext()
  const [syncForm] = Form.useForm()

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
  }, [selectedEnvironment, selectedGroup, searchText, pagination.current, pagination.pageSize])

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

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await ConfigService.getConfigs({
        environment: selectedEnvironment,
        group_id: selectedGroup,
        page: pagination.current,
        size: pagination.pageSize,
        search: searchText || undefined
      })
      
      setConfigs(response.items)
      setPagination(prev => ({
        ...prev,
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

  const loadEnvironmentStats = async () => {
    try {
      const stats = await ConfigService.getEnvironmentStatistics(selectedEnvironment)
      setEnvironmentStats(stats)
    } catch (error) {
      message.error('加载环境统计失败')
    }
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
              <span className="text-gray-400">••••••••</span>
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
              onClick={() => {
                setStatsVisible(true)
                loadEnvironmentStats()
              }}
            >
              统计信息
            </Button>
            <Button
              icon={<SyncOutlined />}
              onClick={openSyncModal}
            >
              环境同步
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
              onChange={setSelectedEnvironment}
              placeholder="环境"
            >
              {Object.entries(ENVIRONMENT_MAP).map(([value, item]) => (
                <Option key={value} value={value}>{item.label}</Option>
              ))}
            </Select>
            <Select
              value={selectedGroup}
              onChange={setSelectedGroup}
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
              placeholder="搜索配置键或描述"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={loadData}
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
        width={400}
      >
        <div className="space-y-6">
          <Card>
            <Statistic
              title="配置总数"
              value={environmentStats.total_configs || 0}
              suffix="个"
            />
          </Card>
          <Card>
            <Statistic
              title="启用配置"
              value={environmentStats.enabled_configs || 0}
              suffix="个"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
          <Card>
            <Statistic
              title="核心配置"
              value={environmentStats.core_configs || 0}
              suffix="个"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
          <Card>
            <Statistic
              title="加密配置"
              value={environmentStats.encrypted_configs || 0}
              suffix="个"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
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
    </div>
  )
}
