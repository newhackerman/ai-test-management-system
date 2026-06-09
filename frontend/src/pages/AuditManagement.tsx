import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Typography,
  Tabs,
  Badge,
  Descriptions,
  Timeline,
  Progress,
  Statistic,
  Row,
  Col,
  Tooltip,
  Popconfirm
} from 'antd'
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  MessageOutlined,
  HistoryOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { ConfigService } from '@/services/config-service'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

interface AuditRecord {
  id: number
  audit_code: string
  config_key: string
  environment: string
  old_value?: string
  new_value: string
  change_type: 'CREATE' | 'UPDATE' | 'DELETE'
  audit_status: 'PENDING' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'CANCELLED'
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
  apply_user?: any
  audit_user?: any
  apply_reason: string
  audit_reason?: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  estimated_downtime?: number
  rollback_plan?: string
  applied_at: string
  audited_at?: string
  executed_at?: string
}

interface AuditStatistics {
  status_stats: {
    total: number
    pending: number
    approved: number
    rejected: number
    cancelled: number
  }
  priority_stats: {
    low: number
    medium: number
    high: number
    urgent: number
  }
  risk_stats: {
    low: number
    medium: number
    high: number
    critical: number
  }
  approval_rate: number
  processed_count: number
}

export default function AuditManagement() {
  const [audits, setAudits] = useState<AuditRecord[]>([])
  const [pendingAudits, setPendingAudits] = useState<AuditRecord[]>([])
  const [statistics, setStatistics] = useState<AuditStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedAudit, setSelectedAudit] = useState<AuditRecord | null>(null)
  const [isDetailVisible, setIsDetailVisible] = useState(false)
  const [isApproveVisible, setIsApproveVisible] = useState(false)
  const [isRejectVisible, setIsRejectVisible] = useState(false)
  const [activeTab, setActiveTab] = useState('pending')
  const [form] = Form.useForm()

  // 分页配置
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  })

  // 过滤条件
  const [filters, setFilters] = useState({
    audit_status: undefined as string | undefined,
    config_key: undefined as string | undefined,
    environment: undefined as string | undefined,
    priority: undefined as string | undefined
  })

  useEffect(() => {
    loadData()
    loadStatistics()
  }, [activeTab, pagination.current, pagination.pageSize, filters])

  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'pending') {
        await loadPendingAudits()
      } else {
        await loadAllAudits()
      }
    } catch (error) {
      message.error('加载审核数据失败')
      console.error('加载审核数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadPendingAudits = async () => {
    try {
      // 实现获取待审核列表的API调用
      const response = await ConfigService.getPendingAudits();
      setPendingAudits(response);
    } catch (error) {
      message.error('加载待审核列表失败');
      console.error('加载待审核列表失败:', error);
      setPendingAudits([]);
    }
  }

  const loadAllAudits = async () => {
    try {
      // 实现获取审核列表的API调用
      const response = await ConfigService.getAuditList({
        ...filters,
        page: pagination.current,
        size: pagination.pageSize
      });
      setAudits(response.items);
      setPagination(prev => ({ ...prev, total: response.total }));
    } catch (error) {
      message.error('加载审核列表失败');
      console.error('加载审核列表失败:', error);
      setAudits([]);
      setPagination(prev => ({ ...prev, total: 0 }));
    }
  }

  const loadStatistics = async () => {
    try {
      // 实现获取审核统计的API调用
      const response = await ConfigService.getAuditStatistics();
      setStatistics(response);
    } catch (error) {
      console.error('加载审核统计失败:', error);
      const emptyStats = {
        status_stats: {
          total: 0,
          pending: 0,
          approved: 0,
          rejected: 0,
          cancelled: 0
        },
        priority_stats: {
          low: 0,
          medium: 0,
          high: 0,
          urgent: 0
        },
        risk_stats: {
          low: 0,
          medium: 0,
          high: 0,
          critical: 0
        },
        approval_rate: 0,
        processed_count: 0
      };
      setStatistics(emptyStats);
    }
  }

  const handleApprove = async (audit: AuditRecord) => {
    setSelectedAudit(audit);
    setIsApproveVisible(true);
  }

  const handleReject = async (audit: AuditRecord) => {
    setSelectedAudit(audit);
    setIsRejectVisible(true);
  }

  const handleViewDetail = (audit: AuditRecord) => {
    setSelectedAudit(audit);
    setIsDetailVisible(true);
  }

  const confirmApprove = async () => {
    if (!selectedAudit) return;

    try {
      const values = await form.validateFields();
      
      // 实现审核通过的API调用
      await ConfigService.approveAudit(selectedAudit.id, values.audit_reason);
      
      message.success('审核通过成功');
      setIsApproveVisible(false);
      form.resetFields();
      loadData();
    } catch (error) {
      message.error('审核通过失败: ' + (error as any).response?.data?.message || '未知错误');
    }
  }

  const confirmReject = async () => {
    if (!selectedAudit) return;

    try {
      const values = await form.validateFields();
      
      // 实现审核驳回的API调用
      await ConfigService.rejectAudit(selectedAudit.id, values.audit_reason);
      
      message.success('审核驳回成功');
      setIsRejectVisible(false);
      form.resetFields();
      loadData();
    } catch (error) {
      message.error('审核驳回失败: ' + (error as any).response?.data?.message || '未知错误');
    }
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      'PENDING': { color: 'orange', text: '待审核' },
      'IN_REVIEW': { color: 'blue', text: '审核中' },
      'APPROVED': { color: 'green', text: '已通过' },
      'REJECTED': { color: 'red', text: '已驳回' },
      'CANCELLED': { color: 'gray', text: '已取消' }
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const getPriorityTag = (priority: string) => {
    const priorityMap: Record<string, { color: string; text: string }> = {
      'LOW': { color: 'green', text: '低' },
      'MEDIUM': { color: 'blue', text: '中' },
      'HIGH': { color: 'orange', text: '高' },
      'URGENT': { color: 'red', text: '紧急' }
    }
    const config = priorityMap[priority] || { color: 'default', text: priority }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const getRiskTag = (risk: string) => {
    const riskMap: Record<string, { color: string; text: string }> = {
      'LOW': { color: 'green', text: '低风险' },
      'MEDIUM': { color: 'yellow', text: '中风险' },
      'HIGH': { color: 'orange', text: '高风险' },
      'CRITICAL': { color: 'red', text: '严重风险' }
    }
    const config = riskMap[risk] || { color: 'default', text: risk }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns = [
    {
      title: '审核编号',
      dataIndex: 'audit_code',
      key: 'audit_code',
      width: 150,
      render: (text: string, record: AuditRecord) => (
        <Button type="link" onClick={() => handleViewDetail(record)}>
          {text}
        </Button>
      )
    },
    {
      title: '配置项',
      dataIndex: 'config_key',
      key: 'config_key',
      width: 200,
      render: (text: string, record: AuditRecord) => (
        <div>
          <div className="font-medium">{text}</div>
          <Tag>{record.environment}</Tag>
        </div>
      )
    },
    {
      title: '变更类型',
      dataIndex: 'change_type',
      key: 'change_type',
      width: 100,
      render: (text: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          'CREATE': { color: 'blue', text: '新增' },
          'UPDATE': { color: 'orange', text: '修改' },
          'DELETE': { color: 'red', text: '删除' }
        }
        const config = typeMap[text] || { color: 'default', text }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    {
      title: '状态',
      dataIndex: 'audit_status',
      key: 'audit_status',
      width: 100,
      render: getStatusTag
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: getPriorityTag
    },
    {
      title: '风险级别',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: getRiskTag
    },
    {
      title: '申请时间',
      dataIndex: 'applied_at',
      key: 'applied_at',
      width: 150,
      render: (text: string) => new Date(text).toLocaleString('zh-CN')
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: AuditRecord) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              icon={<EyeOutlined />} 
              size="small" 
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          {record.audit_status === 'PENDING' && (
            <>
              <Tooltip title="审核通过">
                <Button
                  icon={<CheckOutlined />}
                  size="small"
                  type="primary"
                  onClick={() => handleApprove(record)}
                />
              </Tooltip>
              <Tooltip title="审核驳回">
                <Button
                  icon={<CloseOutlined />}
                  size="small"
                  danger
                  onClick={() => handleReject(record)}
                />
              </Tooltip>
            </>
          )}
        </Space>
      )
    }
  ]

  return (
    <div className="space-y-4">
      <div>
        <Title level={2} className="!m-0 !text-2xl">审计日志</Title>
        <Text type="secondary" className="text-sm">配置变更审核申请的处理和管理</Text>
      </div>

      {/* 统计信息 */}
      {statistics && (
        <div className="grid grid-cols-2 gap-2 rounded-lg border bg-card p-3 md:grid-cols-4">
          <AuditStat icon={<ClockCircleOutlined />} label="待审核" value={statistics.status_stats.pending} className="text-amber-600" />
          <AuditStat label="审核通过率" value={`${Number(statistics.approval_rate || 0).toFixed(1)}%`} className="text-green-600" />
          <AuditStat icon={<SettingOutlined />} label="本月审核" value={statistics.processed_count} className="text-blue-600" />
          <AuditStat icon={<UserOutlined />} label="总申请数" value={statistics.status_stats.total} className="text-foreground" />
        </div>
      )}

      <Card size="small">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'pending',
              label: (
              <Badge count={pendingAudits.length} offset={[10, 0]}>
                <span>待审核</span>
              </Badge>
              ),
              children: (
                <Table
                  columns={columns}
                  dataSource={pendingAudits}
                  rowKey="id"
                  loading={loading}
                  size="middle"
                  scroll={{ x: 1200 }}
                />
              ),
            },
            {
              key: 'all',
              label: '全部审核',
              children: (
                <>
                  <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-4">
                    <Select
                      placeholder="审核状态"
                      allowClear
                      value={filters.audit_status}
                      onChange={(value) => setFilters(prev => ({ ...prev, audit_status: value }))}
                    >
                      <Option value="PENDING">待审核</Option>
                      <Option value="APPROVED">已通过</Option>
                      <Option value="REJECTED">已驳回</Option>
                      <Option value="CANCELLED">已取消</Option>
                    </Select>
                    <Select
                      placeholder="环境"
                      allowClear
                      value={filters.environment}
                      onChange={(value) => setFilters(prev => ({ ...prev, environment: value }))}
                    >
                      <Option value="dev">开发环境</Option>
                      <Option value="test">测试环境</Option>
                      <Option value="prod">生产环境</Option>
                    </Select>
                    <Select
                      placeholder="优先级"
                      allowClear
                      value={filters.priority}
                      onChange={(value) => setFilters(prev => ({ ...prev, priority: value }))}
                    >
                      <Option value="LOW">低</Option>
                      <Option value="MEDIUM">中</Option>
                      <Option value="HIGH">高</Option>
                      <Option value="URGENT">紧急</Option>
                    </Select>
                    <Input
                      placeholder="搜索配置键"
                      allowClear
                      value={filters.config_key}
                      onChange={(e) => setFilters(prev => ({ ...prev, config_key: e.target.value }))}
                    />
                  </div>

                  <Table
                    columns={columns}
                    dataSource={audits}
                    rowKey="id"
                    loading={loading}
                    pagination={pagination}
                    onChange={(paginationConfig) => setPagination(prev => ({
                      ...prev,
                      current: paginationConfig.current || 1,
                      pageSize: paginationConfig.pageSize || 20
                    }))}
                    size="middle"
                    scroll={{ x: 1200 }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* 审核详情模态框 */}
      <Modal
        title="审核详情"
        open={isDetailVisible}
        onCancel={() => setIsDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedAudit && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="审核编号">{selectedAudit.audit_code}</Descriptions.Item>
              <Descriptions.Item label="状态">{getStatusTag(selectedAudit.audit_status)}</Descriptions.Item>
              <Descriptions.Item label="配置键">{selectedAudit.config_key}</Descriptions.Item>
              <Descriptions.Item label="环境">{selectedAudit.environment}</Descriptions.Item>
              <Descriptions.Item label="变更类型">{selectedAudit.change_type}</Descriptions.Item>
              <Descriptions.Item label="优先级">{getPriorityTag(selectedAudit.priority)}</Descriptions.Item>
              <Descriptions.Item label="风险级别">{getRiskTag(selectedAudit.risk_level)}</Descriptions.Item>
              <Descriptions.Item label="预估停机">{selectedAudit.estimated_downtime || 0} 分钟</Descriptions.Item>
              <Descriptions.Item label="变更前值" span={2}>
                <Text code>{selectedAudit.old_value || '无'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="变更后值" span={2}>
                <Text code>{selectedAudit.new_value}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="申请原因" span={2}>
                {selectedAudit.apply_reason}
              </Descriptions.Item>
              {selectedAudit.audit_reason && (
                <Descriptions.Item label="审核意见" span={2}>
                  {selectedAudit.audit_reason}
                </Descriptions.Item>
              )}
              {selectedAudit.rollback_plan && (
                <Descriptions.Item label="回滚方案" span={2}>
                  {selectedAudit.rollback_plan}
                </Descriptions.Item>
              )}
            </Descriptions>

            <div className="mt-4">
              <Title level={5}>审核时间线</Title>
              <Timeline>
                <Timeline.Item color="blue">
                  申请提交 - {new Date(selectedAudit.applied_at).toLocaleString('zh-CN')}
                </Timeline.Item>
                {selectedAudit.audited_at && (
                  <Timeline.Item color={selectedAudit.audit_status === 'APPROVED' ? 'green' : 'red'}>
                    审核{selectedAudit.audit_status === 'APPROVED' ? '通过' : '驳回'} - {new Date(selectedAudit.audited_at).toLocaleString('zh-CN')}
                  </Timeline.Item>
                )}
                {selectedAudit.executed_at && (
                  <Timeline.Item color="green">
                    配置已生效 - {new Date(selectedAudit.executed_at).toLocaleString('zh-CN')}
                  </Timeline.Item>
                )}
              </Timeline>
            </div>
          </div>
        )}
      </Modal>

      {/* 审核通过模态框 */}
      <Modal
        title="审核通过"
        open={isApproveVisible}
        onOk={confirmApprove}
        onCancel={() => {
          setIsApproveVisible(false)
          form.resetFields()
        }}
        okText="确认通过"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="审核意见" name="audit_reason">
            <TextArea
              rows={4}
              placeholder="请输入审核意见（可选）"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 审核驳回模态框 */}
      <Modal
        title="审核驳回"
        open={isRejectVisible}
        onOk={confirmReject}
        onCancel={() => {
          setIsRejectVisible(false)
          form.resetFields()
        }}
        okText="确认驳回"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <Form form={form} layout="vertical">
          <Form.Item 
            label="驳回原因" 
            name="audit_reason"
            rules={[{ required: true, message: '请输入驳回原因' }]}
          >
            <TextArea
              rows={4}
              placeholder="请详细说明驳回原因"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

const AuditStat = ({
  icon,
  label,
  value,
  className,
}: {
  icon?: React.ReactNode
  label: string
  value: React.ReactNode
  className: string
}) => (
  <div className="rounded-md border bg-background px-3 py-2">
    <div className={`flex items-center gap-2 text-xl font-bold leading-6 ${className}`}>
      {icon}
      <span>{value}</span>
    </div>
    <div className="text-xs text-muted-foreground">{label}</div>
  </div>
)
