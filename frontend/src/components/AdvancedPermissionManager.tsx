import React, { useState, useEffect } from 'react'
import {
  Modal, Form, Input, Select, Switch, Button, Tabs, Card, Space, Tag,
  Table, DatePicker, TimePicker, Checkbox, Alert, message, Tooltip,
  Typography, Row, Col, Divider, Badge, Steps, Timeline
} from 'antd'
import {
  SecurityScanOutlined, ClockCircleOutlined, TeamOutlined,
  SettingOutlined, EyeOutlined, EditOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ExclamationCircleOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '@/services/api'

const { Option } = Select
const { TextArea } = Input
const { TabPane } = Tabs
const { Text, Title } = Typography
const { RangePicker } = DatePicker
const { Step } = Steps

interface AdvancedPermissionManagerProps {
  visible: boolean
  onCancel: () => void
  userId?: number
  userName?: string
}

const AdvancedPermissionManager: React.FC<AdvancedPermissionManagerProps> = ({
  visible,
  onCancel,
  userId,
  userName
}) => {
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('temporary')
  const [loading, setLoading] = useState(false)
  const [permissionTemplates, setPermissionTemplates] = useState<any[]>([])
  const [userPermissions, setUserPermissions] = useState<any>({})
  const [auditLogs, setAuditLogs] = useState<any[]>([])

  useEffect(() => {
    if (visible) {
      loadPermissionTemplates()
      if (userId) {
        loadUserPermissions()
        loadAuditLogs()
      }
    }
  }, [visible, userId])

  const loadPermissionTemplates = async () => {
    try {
      const response = await api.get('/configs/advanced-permissions/templates')
      if (response.data.success) {
        setPermissionTemplates(response.data.data)
      }
    } catch (error) {
      console.error('加载权限模板失败:', error)
    }
  }

  const loadUserPermissions = async () => {
    try {
      const response = await api.get(`/configs/advanced-permissions/user/${userId}/effective`)
      if (response.data.success) {
        setUserPermissions(response.data.data)
      }
    } catch (error) {
      console.error('加载用户权限失败:', error)
    }
  }

  const loadAuditLogs = async () => {
    try {
      const response = await api.get('/configs/advanced-permissions/audit-logs', {
        params: { user_id: userId, page: 1, size: 10 }
      })
      if (response.data.success) {
        setAuditLogs(response.data.data.items || [])
      }
    } catch (error) {
      console.error('加载审计日志失败:', error)
    }
  }

  const handleGrantTemporaryPermission = async (values: any) => {
    setLoading(true)
    try {
      const response = await api.post('/configs/advanced-permissions/temporary/grant', {
        user_id: userId,
        permission_level: values.permission_level,
        scope_type: values.scope_type,
        scope_config: values.scope_config || {},
        duration_hours: values.duration_hours,
        reason: values.reason
      })

      if (response.data.success) {
        message.success('临时权限授予成功')
        form.resetFields()
        loadUserPermissions()
      }
    } catch (error) {
      message.error('授予临时权限失败')
      console.error('授予临时权限失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateScheduledPermission = async (values: any) => {
    setLoading(true)
    try {
      const response = await api.post('/configs/advanced-permissions/scheduled/create', {
        user_id: userId,
        permission_level: values.permission_level,
        scope_type: values.scope_type,
        scope_config: values.scope_config || {},
        schedule_name: values.schedule_name,
        work_days: values.work_days,
        work_hours: {
          start: values.work_hours?.[0]?.format('HH:mm') || '09:00',
          end: values.work_hours?.[1]?.format('HH:mm') || '18:00'
        },
        valid_from: values.valid_period?.[0]?.format('YYYY-MM-DD'),
        valid_until: values.valid_period?.[1]?.format('YYYY-MM-DD')
      })

      if (response.data.success) {
        message.success('定时权限创建成功')
        form.resetFields()
        loadUserPermissions()
      }
    } catch (error) {
      message.error('创建定时权限失败')
      console.error('创建定时权限失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigureRowLevelPermission = async (values: any) => {
    setLoading(true)
    try {
      const response = await api.post('/configs/advanced-permissions/row-level/configure', {
        user_id: userId,
        permission_level: values.permission_level,
        resource_type: values.resource_type,
        filter_conditions: values.filter_conditions,
        expires_hours: values.expires_hours
      })

      if (response.data.success) {
        message.success('行级权限配置成功')
        form.resetFields()
        loadUserPermissions()
      }
    } catch (error) {
      message.error('配置行级权限失败')
      console.error('配置行级权限失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApplyTemplate = (template: any) => {
    form.setFieldsValue(template.config)
    message.success(`已应用模板: ${template.name}`)
  }

  const handleCheckPermission = async () => {
    try {
      const values = form.getFieldsValue()
      const response = await api.post('/configs/advanced-permissions/check', {
        user_id: userId,
        config_key: values.config_key,
        environment: values.environment,
        action: values.action,
        required_level: values.required_level || 'READ'
      })

      if (response.data.success) {
        const result = response.data.data
        if (result.has_permission) {
          message.success('权限检查通过')
        } else {
          message.error(`权限检查失败: ${result.error_message}`)
        }
      }
    } catch (error) {
      message.error('权限检查失败')
      console.error('权限检查失败:', error)
    }
  }

  const renderTemporaryPermissionTab = () => (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleGrantTemporaryPermission}
    >
      <Alert
        message="临时权限管理"
        description="为用户授予有时间限制的临时权限，适用于紧急情况或临时授权场景"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="权限级别"
            name="permission_level"
            rules={[{ required: true, message: '请选择权限级别' }]}
          >
            <Select placeholder="选择权限级别">
              <Option value="READ">只读权限</Option>
              <Option value="WRITE">读写权限</Option>
              <Option value="ADMIN">管理员权限</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="权限范围"
            name="scope_type"
            rules={[{ required: true, message: '请选择权限范围' }]}
          >
            <Select placeholder="选择权限范围">
              <Option value="GLOBAL">全局权限</Option>
              <Option value="ENVIRONMENT">环境权限</Option>
              <Option value="GROUP">分组权限</Option>
              <Option value="TAG">标签权限</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="有效时长(小时)"
            name="duration_hours"
            rules={[{ required: true, message: '请输入有效时长' }]}
          >
            <Select placeholder="选择有效时长">
              <Option value={1}>1小时</Option>
              <Option value={4}>4小时</Option>
              <Option value={8}>8小时</Option>
              <Option value={24}>24小时</Option>
              <Option value={72}>72小时</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="范围配置" name="scope_config">
            <TextArea
              placeholder='JSON格式，如: {"environments": ["dev", "test"]}'
              rows={3}
            />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="授权原因"
        name="reason"
        rules={[{ required: true, message: '请输入授权原因' }]}
      >
        <TextArea
          placeholder="请详细说明授权原因和业务需要"
          rows={3}
        />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            授予临时权限
          </Button>
          <Button onClick={() => form.resetFields()}>
            重置
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )

  const renderScheduledPermissionTab = () => (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleCreateScheduledPermission}
    >
      <Alert
        message="定时权限管理"
        description="配置基于时间计划的权限，如工作时间权限、特定日期权限等"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="计划名称"
            name="schedule_name"
            rules={[{ required: true, message: '请输入计划名称' }]}
          >
            <Input placeholder="输入计划名称" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="权限级别"
            name="permission_level"
            rules={[{ required: true, message: '请选择权限级别' }]}
          >
            <Select placeholder="选择权限级别">
              <Option value="READ">只读权限</Option>
              <Option value="WRITE">读写权限</Option>
              <Option value="ADMIN">管理员权限</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="工作日"
            name="work_days"
            rules={[{ required: true, message: '请选择工作日' }]}
          >
            <Checkbox.Group>
              <Row>
                <Col span={8}><Checkbox value={1}>周一</Checkbox></Col>
                <Col span={8}><Checkbox value={2}>周二</Checkbox></Col>
                <Col span={8}><Checkbox value={3}>周三</Checkbox></Col>
                <Col span={8}><Checkbox value={4}>周四</Checkbox></Col>
                <Col span={8}><Checkbox value={5}>周五</Checkbox></Col>
                <Col span={8}><Checkbox value={6}>周六</Checkbox></Col>
                <Col span={8}><Checkbox value={7}>周日</Checkbox></Col>
              </Row>
            </Checkbox.Group>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="工作时间"
            name="work_hours"
            rules={[{ required: true, message: '请选择工作时间' }]}
          >
            <TimePicker.RangePicker
              format="HH:mm"
              placeholder={['开始时间', '结束时间']}
            />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="有效期"
        name="valid_period"
      >
        <RangePicker placeholder={['开始日期', '结束日期']} />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            创建定时权限
          </Button>
          <Button onClick={() => form.resetFields()}>
            重置
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )

  const renderRowLevelPermissionTab = () => (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleConfigureRowLevelPermission}
    >
      <Alert
        message="行级权限管理"
        description="配置基于数据行的权限控制，如只能访问自己创建的配置、特定标签的配置等"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="权限级别"
            name="permission_level"
            rules={[{ required: true, message: '请选择权限级别' }]}
          >
            <Select placeholder="选择权限级别">
              <Option value="READ">只读权限</Option>
              <Option value="WRITE">读写权限</Option>
              <Option value="ADMIN">管理员权限</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="资源类型"
            name="resource_type"
            rules={[{ required: true, message: '请选择资源类型' }]}
          >
            <Select placeholder="选择资源类型">
              <Option value="config">配置项</Option>
              <Option value="group">配置分组</Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="过滤条件"
        name="filter_conditions"
        rules={[{ required: true, message: '请输入过滤条件' }]}
      >
        <TextArea
          placeholder='JSON格式，如: {"created_by": "self", "tags": ["finance"]}'
          rows={4}
        />
      </Form.Item>

      <Form.Item
        label="有效期(小时)"
        name="expires_hours"
      >
        <Select placeholder="选择有效期，不选择表示永久有效">
          <Option value={24}>24小时</Option>
          <Option value={72}>72小时</Option>
          <Option value={168}>1周</Option>
          <Option value={720}>1个月</Option>
        </Select>
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            配置行级权限
          </Button>
          <Button onClick={() => form.resetFields()}>
            重置
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )

  const renderPermissionCheckTab = () => (
    <div>
      <Alert
        message="权限检查工具"
        description="检查用户对特定资源的权限状态，用于测试和调试权限配置"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Form layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="配置键" name="config_key">
              <Input placeholder="输入配置键名" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="环境" name="environment">
              <Select placeholder="选择环境">
                <Option value="dev">开发环境</Option>
                <Option value="test">测试环境</Option>
                <Option value="staging">预发环境</Option>
                <Option value="prod">生产环境</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="操作类型" name="action">
              <Select placeholder="选择操作类型">
                <Option value="read">读取</Option>
                <Option value="update">更新</Option>
                <Option value="delete">删除</Option>
                <Option value="create">创建</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="所需权限级别" name="required_level">
              <Select placeholder="选择权限级别" defaultValue="READ">
                <Option value="READ">只读</Option>
                <Option value="WRITE">读写</Option>
                <Option value="ADMIN">管理员</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item>
          <Button type="primary" onClick={handleCheckPermission}>
            检查权限
          </Button>
        </Form.Item>
      </Form>
    </div>
  )

  const renderUserPermissionsTab = () => (
    <div>
      <Title level={4}>用户有效权限</Title>
      
      <Row gutter={16}>
        {Object.entries(userPermissions).map(([type, permissions]: [string, any]) => (
          <Col span={8} key={type} style={{ marginBottom: 16 }}>
            <Card
              size="small"
              title={
                <span>
                  {type === 'global' && <SecurityScanOutlined />}
                  {type === 'role' && <TeamOutlined />}
                  {type === 'time_based' && <ClockCircleOutlined />}
                  <span style={{ marginLeft: 8 }}>
                    {type === 'global' && '全局权限'}
                    {type === 'role' && '角色权限'}
                    {type === 'row_level' && '行级权限'}
                    {type === 'column_level' && '列级权限'}
                    {type === 'time_based' && '时间权限'}
                    {type === 'temporary' && '临时权限'}
                    {type === 'scheduled' && '定时权限'}
                  </span>
                </span>
              }
            >
              <Badge
                count={Array.isArray(permissions) ? permissions.length : 0}
                style={{ backgroundColor: '#16a34a' }}
              >
                <div style={{ minHeight: 60 }}>
                  {Array.isArray(permissions) && permissions.length > 0 ? (
                    permissions.map((perm: any, index: number) => (
                      <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                        {perm.level || perm.permission_level || 'READ'}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无权限</Text>
                  )}
                </div>
              </Badge>
            </Card>
          </Col>
        ))}
      </Row>

      <Divider />

      <Title level={4}>权限模板</Title>
      <Row gutter={16}>
        {permissionTemplates.map((template, index) => (
          <Col span={8} key={index} style={{ marginBottom: 16 }}>
            <Card
              size="small"
              title={template.name}
              extra={
                <Button
                  type="link"
                  size="small"
                  onClick={() => handleApplyTemplate(template)}
                >
                  应用
                </Button>
              }
            >
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {template.description}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )

  const renderAuditLogsTab = () => (
    <div>
      <Title level={4}>权限审计日志</Title>
      
      <Table
        dataSource={auditLogs}
        size="small"
        pagination={{ pageSize: 10 }}
        rowKey="id"
        columns={[
          {
            title: '操作',
            dataIndex: 'action',
            key: 'action',
            render: (action: string) => (
              <Tag color="blue">{action}</Tag>
            )
          },
          {
            title: '资源',
            dataIndex: 'resource_id',
            key: 'resource_id',
            ellipsis: true
          },
          {
            title: '权限级别',
            dataIndex: 'permission_level',
            key: 'permission_level',
            render: (level: string) => (
              <Tag color="green">{level}</Tag>
            )
          },
          {
            title: '结果',
            dataIndex: 'is_allowed',
            key: 'is_allowed',
            render: (allowed: boolean) => (
              allowed ? (
                <CheckCircleOutlined style={{ color: '#16a34a' }} />
              ) : (
                <CloseCircleOutlined style={{ color: '#f87171' }} />
              )
            )
          },
          {
            title: '时间',
            dataIndex: 'request_time',
            key: 'request_time',
            render: (time: string) => dayjs(time).format('MM-DD HH:mm')
          }
        ]}
      />
    </div>
  )

  return (
    <Modal
      title={
        <span>
          <SecurityScanOutlined style={{ marginRight: 8 }} />
          高级权限管理 {userName && `- ${userName}`}
        </span>
      }
      open={visible}
      onCancel={onCancel}
      width={1200}
      footer={null}
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="临时权限" key="temporary">
          {renderTemporaryPermissionTab()}
        </TabPane>
        <TabPane tab="定时权限" key="scheduled">
          {renderScheduledPermissionTab()}
        </TabPane>
        <TabPane tab="行级权限" key="row-level">
          {renderRowLevelPermissionTab()}
        </TabPane>
        <TabPane tab="权限检查" key="check">
          {renderPermissionCheckTab()}
        </TabPane>
        <TabPane tab="用户权限" key="user-permissions">
          {renderUserPermissionsTab()}
        </TabPane>
        <TabPane tab="审计日志" key="audit-logs">
          {renderAuditLogsTab()}
        </TabPane>
      </Tabs>
    </Modal>
  )
}

export default AdvancedPermissionManager