import React, { useEffect, useState } from 'react'
import { Button, Card, Form, Input, message, Modal, Select, Space, Table, Tag, Tooltip } from 'antd'
import {
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { allureReportService, AllureReportResponse, TestExecutionData } from '../services/allure-report-service'
import ProjectService from '../services/projectService'

const { Option } = Select

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const toAbsoluteReportUrl = (url?: string) => {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  return `${apiBaseUrl.replace(/\/$/, '')}${url.startsWith('/') ? url : `/${url}`}`
}

const initialExecution = {
  test_case_id: '',
  test_name: '',
  status: 'PASSED',
  environment: 'test',
  description: '',
  error_message: '',
}

const AllureReports: React.FC = () => {
  const [reports, setReports] = useState<AllureReportResponse[]>([])
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [form] = Form.useForm()

  const loadReports = async () => {
    setLoading(true)
    try {
      const reportList = await allureReportService.listReports()
      setReports(reportList)
    } catch (error: any) {
      message.error(error?.message || '加载 Allure 报告列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadProjects = async () => {
    try {
      const response = await ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' })
      setProjects(response.data || [])
    } catch {
      setProjects([])
    }
  }

  useEffect(() => {
    loadReports()
    loadProjects()
  }, [])

  const generateReportFromData = async (values: any) => {
    setLoading(true)
    try {
      const now = new Date().toISOString()
      const testExecutions: TestExecutionData[] = values.test_executions.map((item: any) => ({
        test_case_id: item.test_case_id,
        test_name: item.test_name,
        status: item.status,
        start_time: now,
        end_time: now,
        description: item.description,
        error_message: item.status === 'FAILED' ? item.error_message : undefined,
        environment: item.environment,
        labels: {
          suite: values.suite_name || 'default',
        },
      }))

      await allureReportService.generateReportFromData({
        report_name: values.report_name,
        suite_name: values.suite_name,
        project_id: values.project_id ? Number(values.project_id) : undefined,
        test_executions: testExecutions,
        auto_serve: true,
      })
      message.success('Allure 报告生成成功')
      setGenerateModalVisible(false)
      form.resetFields()
      await loadReports()
    } catch (error: any) {
      message.error(error?.message || '生成 Allure 报告失败')
    } finally {
      setLoading(false)
    }
  }

  const openReport = (record: AllureReportResponse) => {
    const reportUrl = toAbsoluteReportUrl(record.report_url)
    if (!reportUrl) {
      message.warning('报告访问地址不存在')
      return
    }
    window.open(reportUrl, '_blank')
  }

  const deleteReport = async (reportId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个 Allure 报告吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await allureReportService.deleteReport(reportId)
          message.success('报告删除成功')
          await loadReports()
        } catch (error: any) {
          message.error(error?.message || '删除报告失败')
        }
      },
    })
  }

  const formatFileSize = (bytes = 0): string => {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const index = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, index)).toFixed(2)} ${units[index]}`
  }

  const statusTag = (status: string) => {
    const config: Record<string, { color: string; text: string }> = {
      completed: { color: 'green', text: '已完成' },
      generating: { color: 'blue', text: '生成中' },
      failed: { color: 'red', text: '失败' },
      pending: { color: 'orange', text: '等待中' },
    }
    const item = config[status] || { color: 'default', text: status }
    return <Tag color={item.color}>{item.text}</Tag>
  }

  const columns = [
    {
      title: '报告名称',
      dataIndex: 'report_name',
      key: 'report_name',
      render: (text: string) => (
        <Space>
          <FileTextOutlined />
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: statusTag,
    },
    {
      title: '测试统计',
      key: 'test_stats',
      render: (record: AllureReportResponse) => (
        <Space>
          <Tag color="green">通过 {record.passed_count}</Tag>
          <Tag color="red">失败 {record.failed_count}</Tag>
          <Tag color="orange">跳过 {record.skipped_count}</Tag>
        </Space>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: formatFileSize,
    },
    {
      title: '生成耗时',
      dataIndex: 'generation_time',
      key: 'generation_time',
      render: (time: number) => `${Number(time || 0).toFixed(2)}s`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: AllureReportResponse) => (
        <Space>
          <Tooltip title="查看报告">
            <Button type="link" icon={<EyeOutlined />} onClick={() => openReport(record)} />
          </Tooltip>
          <Tooltip title="删除报告">
            <Button type="link" danger icon={<DeleteOutlined />} onClick={() => deleteReport(record.report_id)} />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>Allure 测试报告</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                form.setFieldsValue({ test_executions: [initialExecution] })
                setGenerateModalVisible(true)
              }}
            >
              生成报告
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadReports} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="report_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      <Modal
        title="生成 Allure 报告"
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false)
          form.resetFields()
        }}
        footer={null}
        width={900}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={generateReportFromData} initialValues={{ test_executions: [initialExecution] }}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Form.Item name="report_name" label="报告名称" rules={[{ required: true, message: '请输入报告名称' }]}>
              <Input placeholder="请输入报告名称" />
            </Form.Item>
            <Form.Item name="suite_name" label="测试套件名称">
              <Input placeholder="例如：登录回归测试" />
            </Form.Item>
            <Form.Item name="project_id" label="关联项目">
              <Select placeholder="选择项目" allowClear showSearch optionFilterProp="children">
                {projects.map((project) => (
                  <Option key={project.id} value={project.id}>{project.project_name || project.name || `项目 #${project.id}`}</Option>
                ))}
              </Select>
            </Form.Item>
          </div>

          <Form.List name="test_executions">
            {(fields, { add, remove }) => (
              <div className="space-y-4">
                {fields.map(({ key, name, ...restField }) => (
                  <Card key={key} size="small" title={`测试结果 ${name + 1}`} extra={fields.length > 1 && <Button type="link" danger onClick={() => remove(name)}>删除</Button>}>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                      <Form.Item {...restField} name={[name, 'test_case_id']} label="用例 ID" rules={[{ required: true, message: '请输入用例 ID' }]}>
                        <Input placeholder="例如：TC-LOGIN-001" />
                      </Form.Item>
                      <Form.Item {...restField} name={[name, 'test_name']} label="测试名称" rules={[{ required: true, message: '请输入测试名称' }]}>
                        <Input placeholder="请输入测试名称" />
                      </Form.Item>
                      <Form.Item {...restField} name={[name, 'status']} label="执行状态" rules={[{ required: true, message: '请选择执行状态' }]}>
                        <Select>
                          <Option value="PASSED">通过</Option>
                          <Option value="FAILED">失败</Option>
                          <Option value="SKIPPED">跳过</Option>
                        </Select>
                      </Form.Item>
                    </div>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <Form.Item {...restField} name={[name, 'environment']} label="执行环境">
                        <Input placeholder="例如：test、staging" />
                      </Form.Item>
                      <Form.Item {...restField} name={[name, 'error_message']} label="失败原因">
                        <Input placeholder="失败时填写" />
                      </Form.Item>
                    </div>
                    <Form.Item {...restField} name={[name, 'description']} label="结果说明">
                      <Input.TextArea rows={2} placeholder="填写执行结果、关键断言或备注" />
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add(initialExecution)} block icon={<PlusOutlined />}>
                  添加测试结果
                </Button>
              </div>
            )}
          </Form.List>

          <Form.Item className="mt-6 mb-0">
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                生成报告
              </Button>
              <Button onClick={() => setGenerateModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AllureReports
