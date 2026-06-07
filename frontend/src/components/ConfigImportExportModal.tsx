import React, { useState } from 'react'
import {
  Modal,
  Upload,
  Select,
  Form,
  Button,
  message,
  Card,
  Table,
  Tag,
  Space,
  Tooltip,
  Alert,
  Descriptions,
  Typography,
  Row,
  Col,
  Divider,
  Checkbox,
  Progress,
  Input,
  Statistic
} from 'antd'
import {
  InboxOutlined,
  DownloadOutlined,
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined
} from '@ant-design/icons'
import { api } from '@/services/api'

const { Dragger } = Upload
const { Option } = Select
const { Text, Title } = Typography

interface ImportExportModalProps {
  visible: boolean
  onCancel: () => void
  onSuccess: () => void
  environment: string
  groupId?: number
}

interface FileFormat {
  value: string
  label: string
  description: string
  extensions: string[]
}

interface PreviewData {
  preview: boolean
  total_configs: number
  conflicts: Array<{
    key: string
    existing_value: string
    new_value: string
  }>
  new_configs: string[]
  configs: Record<string, any>
}

const FILE_FORMATS: FileFormat[] = [
  {
    value: 'env',
    label: '.env文件',
    description: '环境变量格式，适用于简单的键值对配置',
    extensions: ['.env']
  },
  {
    value: 'json',
    label: 'JSON文件',
    description: 'JSON格式，支持复杂的嵌套结构',
    extensions: ['.json']
  },
  {
    value: 'yaml',
    label: 'YAML文件',
    description: 'YAML格式，人类可读且支持注释',
    extensions: ['.yml', '.yaml']
  },
  {
    value: 'xml',
    label: 'XML文件',
    description: 'XML格式，适用于企业级配置',
    extensions: ['.xml']
  },
  {
    value: 'properties',
    label: 'Properties文件',
    description: 'Java Properties格式',
    extensions: ['.properties']
  }
]

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const getAuthToken = () => {
  const directToken = localStorage.getItem('auth-access-token') || localStorage.getItem('auth_token') || localStorage.getItem('auth-token') || localStorage.getItem('token')
  if (directToken) return directToken

  try {
    return JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token || null
  } catch {
    return null
  }
}

const getApiPayload = <T,>(response: any): T => {
  if (response?.data && typeof response.data === 'object' && 'success' in response.data) {
    return response.data as T
  }
  return response as T
}

const buildApiUrl = (path: string) => `${API_BASE_URL}${path}`

export default function ConfigImportExportModal({
  visible,
  onCancel,
  onSuccess,
  environment,
  groupId
}: ImportExportModalProps) {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('export')
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [importProgress, setImportProgress] = useState(0)

  // 导出配置
  const handleExport = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      const params = new URLSearchParams({
        format_type: values.exportFormat,
        environment: environment,
        include_sensitive: values.includeSensitive || false
      })

      if (groupId) {
        params.append('group_id', String(groupId))
      }

      if (values.configKeys) {
        params.append('config_keys', values.configKeys)
      }

      // 调用导出API
      const token = getAuthToken()
      const response = await fetch(buildApiUrl(`/api/v1/configs/import-export/export?${params}`), {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      })

      if (!response.ok) {
        throw new Error('导出失败')
      }

      // 下载文件
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      const format = values.exportFormat
      const extension = FILE_FORMATS.find(f => f.value === format)?.extensions[0] || '.txt'
      a.download = `config_${environment}_${format}${extension}`
      
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      message.success('导出成功')
      onCancel()

    } catch (error) {
      message.error('导出失败')
      console.error('导出错误:', error)
    } finally {
      setLoading(false)
    }
  }

  // 预览导入
  const handlePreviewImport = async () => {
    if (!uploadedFile) {
      message.error('请先选择文件')
      return
    }

    try {
      const values = await form.validateFields()
      setLoading(true)

      const formData = new FormData()
      formData.append('file', uploadedFile)
      formData.append('format_type', values.importFormat)
      formData.append('environment', environment)
      
      if (groupId) {
        formData.append('group_id', String(groupId))
      }

      const response = await api.post('/configs/import-export/import/preview', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      const payload = getApiPayload<any>(response)

      if (payload.success) {
        setPreviewData(payload.data)
        setShowPreview(true)
      } else {
        message.error(payload.message || '预览失败')
      }

    } catch (error) {
      message.error('预览失败')
      console.error('预览错误:', error)
    } finally {
      setLoading(false)
    }
  }

  // 执行导入
  const handleImport = async (overwrite: boolean = false) => {
    if (!uploadedFile) {
      message.error('请先选择文件')
      return
    }

    try {
      const values = await form.validateFields()
      setLoading(true)
      setImportProgress(0)

      const formData = new FormData()
      formData.append('file', uploadedFile)
      formData.append('format_type', values.importFormat)
      formData.append('environment', environment)
      formData.append('overwrite_existing', String(overwrite))
      
      if (groupId) {
        formData.append('group_id', String(groupId))
      }

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setImportProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const endpoint = overwrite 
        ? '/configs/import-export/import/force' 
        : '/configs/import-export/import'

      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      const payload = getApiPayload<any>(response)

      clearInterval(progressInterval)
      setImportProgress(100)

      if (payload.success) {
        const result = payload.data
        message.success(
          `导入成功！成功：${result.success_count}个，失败：${result.error_count}个`
        )
        
        setTimeout(() => {
          onSuccess()
          onCancel()
        }, 1000)
      } else {
        if (payload.code === 'CONFLICT_ERROR' || payload.data?.conflicts?.length) {
          // 显示冲突确认对话框
          Modal.confirm({
            title: '配置冲突',
            content: `发现 ${payload.data?.conflicts?.length || 0} 个配置冲突，是否覆盖现有配置？`,
            onOk: () => handleImport(true)
          })
        } else {
          message.error(payload.message || '导入失败')
        }
      }

    } catch (error) {
      message.error('导入失败')
      console.error('导入错误:', error)
    } finally {
      setLoading(false)
      setImportProgress(0)
    }
  }

  // 下载模板
  const handleDownloadTemplate = async (format: string) => {
    try {
      const token = getAuthToken()
      const response = await fetch(
        buildApiUrl(`/api/v1/configs/import-export/template/${format}`),
        {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          }
        }
      )

      if (!response.ok) {
        throw new Error('下载模板失败')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      const extension = FILE_FORMATS.find(f => f.value === format)?.extensions[0] || '.txt'
      a.download = `config_template${extension}`
      
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      message.success('模板下载成功')

    } catch (error) {
      message.error('下载模板失败')
    }
  }

  // 预览表格列
  const previewColumns = [
    {
      title: '配置键',
      dataIndex: 'key',
      key: 'key',
      width: 200
    },
    {
      title: '配置值',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
      render: (value: string) => (
        <Tooltip title={value}>
          <Text code>{value}</Text>
        </Tooltip>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag color="blue">{type}</Tag>
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: any) => {
        const isConflict = previewData?.conflicts.some(c => c.key === record.key)
        const isNew = previewData?.new_configs.includes(record.key)
        
        if (isConflict) {
          return <Tag color="orange" icon={<ExclamationCircleOutlined />}>冲突</Tag>
        } else if (isNew) {
          return <Tag color="green" icon={<CheckCircleOutlined />}>新增</Tag>
        }
        return <Tag color="blue" icon={<InfoCircleOutlined />}>更新</Tag>
      }
    }
  ]

  // 冲突表格列
  const conflictColumns = [
    {
      title: '配置键',
      dataIndex: 'key',
      key: 'key',
      width: 200
    },
    {
      title: '现有值',
      dataIndex: 'existing_value',
      key: 'existing_value',
      ellipsis: true,
      render: (value: string) => (
        <Tooltip title={value}>
          <Text type="secondary" code>{value}</Text>
        </Tooltip>
      )
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      ellipsis: true,
      render: (value: string) => (
        <Tooltip title={value}>
          <Text strong code>{value}</Text>
        </Tooltip>
      )
    }
  ]

  return (
    <Modal
      title="配置导入导出"
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={null}
    >
      <div className="mb-4">
        <Button.Group>
          <Button 
            type={activeTab === 'export' ? 'primary' : 'default'}
            icon={<DownloadOutlined />}
            onClick={() => setActiveTab('export')}
          >
            导出配置
          </Button>
          <Button 
            type={activeTab === 'import' ? 'primary' : 'default'}
            icon={<UploadOutlined />}
            onClick={() => setActiveTab('import')}
          >
            导入配置
          </Button>
        </Button.Group>
      </div>

      {activeTab === 'export' && (
        <Card title="导出配置">
          <Form form={form} layout="vertical">
            <Form.Item
              name="exportFormat"
              label="导出格式"
              rules={[{ required: true, message: '请选择导出格式' }]}
            >
              <Select placeholder="选择导出格式">
                {FILE_FORMATS.map(format => (
                  <Option key={format.value} value={format.value}>
                    <div>
                      <div>{format.label}</div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {format.description}
                      </div>
                    </div>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="configKeys"
              label="指定配置键"
              help="可选，用逗号分隔多个配置键。留空表示导出所有配置"
            >
              <Input.TextArea 
                rows={2} 
                placeholder="例如：app.name,database.host,redis.url"
              />
            </Form.Item>

            <Form.Item name="includeSensitive" valuePropName="checked">
              <Checkbox>包含敏感配置（密码等）</Checkbox>
            </Form.Item>

            <div className="flex justify-end space-x-2">
              <Button onClick={onCancel}>取消</Button>
              <Button 
                type="primary" 
                icon={<DownloadOutlined />}
                loading={loading}
                onClick={handleExport}
              >
                导出
              </Button>
            </div>
          </Form>
        </Card>
      )}

      {activeTab === 'import' && !showPreview && (
        <Card title="导入配置">
          <Form form={form} layout="vertical">
            <Form.Item
              name="importFormat"
              label="文件格式"
              rules={[{ required: true, message: '请选择文件格式' }]}
            >
              <Select placeholder="选择文件格式">
                {FILE_FORMATS.map(format => (
                  <Option key={format.value} value={format.value}>
                    <Space>
                      <FileTextOutlined />
                      <div>
                        <div>{format.label}</div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          支持：{format.extensions.join(', ')}
                        </div>
                      </div>
                      <Button 
                        size="small" 
                        type="link"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDownloadTemplate(format.value)
                        }}
                      >
                        下载模板
                      </Button>
                    </Space>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="选择文件"
              help="支持拖拽上传或点击选择文件"
            >
              <Dragger
                beforeUpload={(file) => {
                  setUploadedFile(file)
                  return false
                }}
                fileList={uploadedFile ? [uploadedFile as any] : []}
                maxCount={1}
                accept=".env,.json,.yml,.yaml,.xml,.properties"
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">
                  支持单个文件上传，文件大小限制10MB
                </p>
              </Dragger>
            </Form.Item>

            <Alert
              message="导入说明"
              description={
                <ul className="list-disc list-inside text-sm">
                  <li>导入前请先预览文件内容，确认配置正确</li>
                  <li>如果存在配置冲突，系统会提示是否覆盖</li>
                  <li>建议在非生产环境先进行测试</li>
                  <li>导入过程中请勿关闭页面</li>
                </ul>
              }
              type="info"
              className="mb-4"
            />

            <div className="flex justify-end space-x-2">
              <Button onClick={onCancel}>取消</Button>
              <Button 
                type="default" 
                icon={<EyeOutlined />}
                loading={loading}
                onClick={handlePreviewImport}
                disabled={!uploadedFile}
              >
                预览
              </Button>
            </div>
          </Form>
        </Card>
      )}

      {activeTab === 'import' && showPreview && previewData && (
        <div>
          <Card title="导入预览" className="mb-4">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="总配置数" value={previewData.total_configs} />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="新增配置" 
                  value={previewData.new_configs.length}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="冲突配置" 
                  value={previewData.conflicts.length}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="更新配置" 
                  value={previewData.total_configs - previewData.new_configs.length - previewData.conflicts.length}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>

            {importProgress > 0 && (
              <div className="mt-4">
                <Progress percent={importProgress} status={importProgress === 100 ? 'success' : 'active'} />
              </div>
            )}
          </Card>

          {previewData.conflicts.length > 0 && (
            <Card title="配置冲突" className="mb-4">
              <Alert
                message="发现配置冲突"
                description="以下配置在目标环境中已存在，导入时将覆盖现有值"
                type="warning"
                className="mb-3"
              />
              <Table
                columns={conflictColumns}
                dataSource={previewData.conflicts}
                rowKey="key"
                size="small"
                scroll={{ y: 200 }}
              />
            </Card>
          )}

          <Card title="所有配置">
            <Table
              columns={previewColumns}
              dataSource={Object.entries(previewData.configs).map(([key, config]) => ({
                key,
                ...config
              }))}
              rowKey="key"
              size="small"
              scroll={{ y: 300 }}
            />
          </Card>

          <div className="flex justify-end space-x-2 mt-4">
            <Button onClick={() => setShowPreview(false)}>返回</Button>
            <Button onClick={onCancel}>取消</Button>
            <Button 
              type="primary" 
              icon={<UploadOutlined />}
              loading={loading}
              onClick={() => handleImport(false)}
            >
              确认导入
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
