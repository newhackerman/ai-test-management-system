import React, { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Tooltip
} from 'antd';
import {
  BarChartOutlined,
  CheckCircleOutlined,
  HeartOutlined,
  HistoryOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  WarningOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useAutoRecovery } from '../../hooks/useAutoRecovery';
import type { FailureType, ManualRecoveryRequest } from '../../services/api/autoRecovery';

interface RecoveryHistoryItem {
  id?: string | number;
  recovery_id?: string;
  failure_type?: string;
  recovery_status?: string;
  recovery_message?: string;
  actions_taken?: string[];
  execution_time?: string;
}

const defaultFailureTypes: FailureType[] = [
  { value: 'database_connection', name: '数据库连接', description: '数据库连接异常或超时' },
  { value: 'redis_connection', name: 'Redis连接', description: 'Redis连接异常或超时' },
  { value: 'high_cpu_usage', name: 'CPU占用过高', description: '系统CPU占用超过阈值' },
  { value: 'high_memory_usage', name: '内存占用过高', description: '系统内存占用超过阈值' },
  { value: 'disk_full', name: '磁盘空间不足', description: '磁盘使用率超过阈值' },
  { value: 'service_unavailable', name: '服务不可用', description: '核心服务不可用' },
  { value: 'slow_response', name: '响应过慢', description: '接口响应时间超过阈值' },
  { value: 'error_rate_high', name: '错误率过高', description: '接口错误率超过阈值' }
];

const statusText: Record<string, string> = {
  success: '成功',
  failed: '失败',
  pending: '处理中',
  skipped: '已跳过'
};

const severityColor: Record<string, string> = {
  low: 'blue',
  medium: 'orange',
  high: 'red',
  critical: 'purple'
};

const thresholdLabelMap: Record<string, string> = {
  high_cpu_usage: 'CPU 使用率',
  high_memory_usage: '内存使用率',
  disk_full: '磁盘使用率',
  slow_response: '响应时间',
  error_rate_high: '错误率'
};

const getSeverityColor = (severity?: string) => severityColor[severity || ''] || 'default';
const getRecoveryStatusColor = (status?: string) => {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'pending') return 'processing';
  if (status === 'skipped') return 'warning';
  return 'default';
};

const formatTime = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const getThresholdUnit = (key: string) => {
  if (key.includes('usage') || key.includes('rate') || key.includes('disk')) return '%';
  if (key.includes('response')) return 'ms';
  return '';
};

const AutoRecoveryPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [manualRecoveryModalVisible, setManualRecoveryModalVisible] = useState(false);
  const [thresholdModalVisible, setThresholdModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [thresholdForm] = Form.useForm();

  const {
    monitoringStatus,
    failureDetection,
    recoveryStatistics,
    recoveryHistory,
    failureTypes,
    failureThresholds,
    loading,
    startMonitoring,
    stopMonitoring,
    detectFailures,
    executeManualRecovery,
    refreshRecoveryHistory,
    refreshRecoveryStatistics,
    updateFailureThresholds,
    performHealthCheck
  } = useAutoRecovery();

  const availableFailureTypes = failureTypes.length > 0 ? failureTypes : defaultFailureTypes;
  const currentThresholds = Object.keys(failureThresholds).length > 0
    ? failureThresholds
    : {
        high_cpu_usage: 90,
        high_memory_usage: 95,
        disk_full: 98,
        slow_response: 5000,
        error_rate_high: 10
      };

  const recoveryHistoryColumns: ColumnsType<RecoveryHistoryItem> = useMemo(
    () => [
      {
        title: '故障类型',
        dataIndex: 'failure_type',
        key: 'failure_type',
        render: (type?: string) => <Tag color="blue">{type || '-'}</Tag>
      },
      {
        title: '恢复状态',
        dataIndex: 'recovery_status',
        key: 'recovery_status',
        render: (status?: string) => (
          <Tag color={getRecoveryStatusColor(status)}>{statusText[status || ''] || status || '-'}</Tag>
        )
      },
      {
        title: '恢复消息',
        dataIndex: 'recovery_message',
        key: 'recovery_message',
        ellipsis: true,
        render: (message?: string) => message || '-'
      },
      {
        title: '执行动作',
        dataIndex: 'actions_taken',
        key: 'actions_taken',
        render: (actions?: string[]) => (
          <Tooltip title={actions?.join('、') || '暂无动作记录'}>
            <span>{actions?.length || 0} 项操作</span>
          </Tooltip>
        )
      },
      {
        title: '执行时间',
        dataIndex: 'execution_time',
        key: 'execution_time',
        render: formatTime
      }
    ],
    []
  );

  const handleManualRecovery = async (values: {
    failure_type: string;
    description?: string;
    force_recovery?: boolean;
  }) => {
    const request: ManualRecoveryRequest = {
      failure_type: values.failure_type,
      force_recovery: Boolean(values.force_recovery),
      failure_details: {
        manual_trigger: true,
        description: values.description || '管理员手动触发恢复操作'
      }
    };

    const result = await executeManualRecovery(request);
    if (result) {
      setManualRecoveryModalVisible(false);
      form.resetFields();
    }
  };

  const handleThresholdUpdate = async (values: Record<string, number>) => {
    await updateFailureThresholds(values);
    setThresholdModalVisible(false);
    thresholdForm.resetFields();
  };

  const renderOverview = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title="监控状态"
        extra={
          <Space wrap>
            <Button
              type={monitoringStatus?.is_monitoring ? 'default' : 'primary'}
              icon={monitoringStatus?.is_monitoring ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={monitoringStatus?.is_monitoring ? stopMonitoring : startMonitoring}
              loading={loading}
            >
              {monitoringStatus?.is_monitoring ? '停止监控' : '启动监控'}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={detectFailures} loading={loading}>
              检测故障
            </Button>
            <Button icon={<HeartOutlined />} onClick={performHealthCheck} loading={loading}>
              健康检查
            </Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="监控状态"
              value={monitoringStatus?.is_monitoring ? '监控中' : '未启动'}
              prefix={
                monitoringStatus?.is_monitoring
                  ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  : <WarningOutlined style={{ color: '#faad14' }} />
              }
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="检测到的故障"
              value={failureDetection?.failures_detected || 0}
              suffix="个"
              valueStyle={{ color: failureDetection?.failures_detected ? '#cf1322' : '#52c41a' }}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic title="总恢复次数" value={recoveryStatistics?.total_recoveries || 0} suffix="次" />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Statistic
              title="恢复成功率"
              value={recoveryStatistics?.success_rate || 0}
              suffix="%"
              precision={1}
              valueStyle={{ color: (recoveryStatistics?.success_rate || 0) >= 90 ? '#52c41a' : '#faad14' }}
            />
          </Col>
        </Row>

        {monitoringStatus?.message && (
          <Alert
            message={monitoringStatus.message}
            type={monitoringStatus.is_monitoring ? 'success' : 'info'}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {failureDetection && failureDetection.failures_detected > 0 && (
        <Card title="最近检测到的故障">
          <Timeline
            items={failureDetection.failures.map((failure, index) => ({
              key: `${failure.failure_type}-${index}`,
              color: getSeverityColor(failure.severity),
              dot: <WarningOutlined />,
              children: (
                <Space direction="vertical" size={4}>
                  <Space>
                    <Tag color={getSeverityColor(failure.severity)}>{failure.severity?.toUpperCase()}</Tag>
                    <strong>{failure.failure_type}</strong>
                  </Space>
                  <span>{failure.message}</span>
                  <span style={{ color: '#8c8c8c' }}>{formatTime(failure.detected_at)}</span>
                </Space>
              )
            }))}
          />
        </Card>
      )}

      {recoveryStatistics?.failure_type_statistics && (
        <Card title="故障类型统计">
          <Row gutter={[16, 16]}>
            {Object.entries(recoveryStatistics.failure_type_statistics).map(([type, statistic]) => (
              <Col xs={24} md={12} xl={8} key={type}>
                <Card size="small" title={type}>
                  <Statistic title="恢复次数" value={statistic.count} />
                  <Progress
                    percent={Number(statistic.avg_success_rate || 0)}
                    status={statistic.avg_success_rate >= 90 ? 'success' : 'normal'}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}
    </Space>
  );

  const renderHistory = () => (
    <Card
      title="恢复历史记录"
      extra={
        <Button icon={<ReloadOutlined />} onClick={refreshRecoveryHistory} loading={loading}>
          刷新
        </Button>
      }
    >
      <Table
        columns={recoveryHistoryColumns}
        dataSource={recoveryHistory as RecoveryHistoryItem[]}
        rowKey={(record, index) => String(record.id || record.recovery_id || index)}
        size="small"
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
        }}
      />
    </Card>
  );

  const renderSettings = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title="故障阈值配置"
        extra={
          <Button
            type="primary"
            icon={<SettingOutlined />}
            onClick={() => {
              thresholdForm.setFieldsValue(currentThresholds);
              setThresholdModalVisible(true);
            }}
          >
            修改阈值
          </Button>
        }
      >
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }} bordered>
          {Object.entries(currentThresholds).map(([key, value]) => (
            <Descriptions.Item key={key} label={thresholdLabelMap[key] || key}>
              {value}
              {getThresholdUnit(key)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Card>

      <Card
        title="手动恢复操作"
        extra={
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => setManualRecoveryModalVisible(true)}
          >
            执行手动恢复
          </Button>
        }
      >
        <Alert
          message="手动恢复会针对指定故障类型立即执行恢复流程。建议先执行健康检查或故障检测，再按结果选择恢复类型。"
          type="info"
          showIcon
        />
      </Card>
    </Space>
  );

  return (
    <div className="auto-recovery-page">
      <Card
        title={
          <Space>
            自动恢复服务
            <Badge status={monitoringStatus?.is_monitoring ? 'processing' : 'default'} />
          </Space>
        }
        extra={
          <Button icon={<BarChartOutlined />} onClick={refreshRecoveryStatistics} loading={loading}>
            刷新统计
          </Button>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: (
                <Space>
                  <CheckCircleOutlined />
                  概览
                </Space>
              ),
              children: renderOverview()
            },
            {
              key: 'history',
              label: (
                <Space>
                  <HistoryOutlined />
                  恢复历史
                </Space>
              ),
              children: renderHistory()
            },
            {
              key: 'settings',
              label: (
                <Space>
                  <SettingOutlined />
                  配置管理
                </Space>
              ),
              children: renderSettings()
            }
          ]}
        />
      </Card>

      <Modal
        title="手动执行恢复操作"
        open={manualRecoveryModalVisible}
        onCancel={() => {
          setManualRecoveryModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleManualRecovery}>
          <Form.Item
            name="failure_type"
            label="故障类型"
            rules={[{ required: true, message: '请选择故障类型' }]}
          >
            <Select
              placeholder="选择要恢复的故障类型"
              options={availableFailureTypes.map((type) => ({
                value: type.value,
                label: `${type.name || type.value} - ${type.description || '暂无说明'}`
              }))}
            />
          </Form.Item>

          <Form.Item name="description" label="操作说明">
            <Input.TextArea rows={3} placeholder="请输入本次手动恢复的原因或处理说明" />
          </Form.Item>

          <Form.Item name="force_recovery" valuePropName="checked">
            <Checkbox>强制恢复，忽略冷却时间限制</Checkbox>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                执行恢复
              </Button>
              <Button
                onClick={() => {
                  setManualRecoveryModalVisible(false);
                  form.resetFields();
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="故障阈值配置"
        open={thresholdModalVisible}
        onCancel={() => {
          setThresholdModalVisible(false);
          thresholdForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={thresholdForm} layout="vertical" onFinish={handleThresholdUpdate}>
          {Object.entries(currentThresholds).map(([key]) => (
            <Form.Item
              key={key}
              name={key}
              label={thresholdLabelMap[key] || key}
              rules={[
                { required: true, message: '请输入阈值' },
                { type: 'number', min: 0, message: '阈值不能小于 0' }
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                precision={key.includes('usage') || key.includes('rate') ? 1 : 0}
                addonAfter={getThresholdUnit(key)}
              />
            </Form.Item>
          ))}

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                更新配置
              </Button>
              <Button
                onClick={() => {
                  setThresholdModalVisible(false);
                  thresholdForm.resetFields();
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AutoRecoveryPage;
