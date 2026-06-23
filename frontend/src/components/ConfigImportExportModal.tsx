import React, { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  CheckCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  FileTextOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { api } from '@/services/api'

const { Dragger } = Upload
const { Option } = Select
const { Text } = Typography

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
    label: '.env 文件',
    description: '环境变量格式，适合简单键值配置。',
    extensions: ['.env'],
  },
  {
    value: 'json',
    label: 'JSON 文件',
    description: '结构化 JSON 格式，适合复杂配置。',
    extensions: ['.json'],
  },
  {
    value: 'yaml',
    label: 'YAML 文件',
    description: 'YAML 格式，适合人工维护和注释。',
    extensions: ['.yml', '.yaml'],
  },
  {
    value: 'xml',
    label: 'XML 文件',
    description: 'XML 格式，适合企业系统配置交换。',
    extensions: ['.xml'],
  },
  {
    value: 'properties',
    label: 'Properties 文件',
    description: 'Java Properties 键值格式。',
    extensions: ['.properties'],
  },
]

const inferImportFormatFromFileName = (fileName: string) => {
  const lowerName = fileName.toLowerCase()
  const matched = FILE_FORMATS.find((format) =>
    format.extensions.some((extension) => lowerName.endsWith(extension)),
  )
  return matched?.value
}

const getApiPayload = <T,>(response: any): { success?: boolean; data?: T; message?: string; code?: string; error_code?: string } => {
  if (response?.success !== undefined) return response
  if (response?.data?.success !== undefined) return response.data
  return response
}

const getApiErrorMessage = (error: any, fallback: string) => {
  const data = error?.response?.data
  const normalize = (value: any): string | null => {
    if (!value) return null
    if (typeof value === 'string') return value
    if (Array.isArray(value)) {
      return value
        .map((item) => (typeof item === 'string' ? item : item?.msg || item?.message || JSON.stringify(item)))
        .join('; ')
    }
    if (typeof value === 'object') return value.msg || value.message || JSON.stringify(value)
    return String(value)
  }

  const detail = normalize(data?.detail)
  if (detail) return detail
  const apiMessage = normalize(data?.message)
  if (apiMessage) return apiMessage
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data?.message === 'string') return data.message
  if (typeof error?.message === 'string') return error.message
  return fallback
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export default function ConfigImportExportModal({
  visible,
  onCancel,
  onSuccess,
  environment,
  groupId,
}: ImportExportModalProps) {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('export')
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [importFormat, setImportFormat] = useState('json')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [importProgress, setImportProgress] = useState(0)

  const resetState = () => {
    setUploadedFile(null)
    setPreviewData(null)
    setShowPreview(false)
    setImportFormat('json')
    setImportProgress(0)
    form.resetFields()
  }

  const handleClose = () => {
    resetState()
    onCancel()
  }

  const createImportFormData = (format?: string, overwriteExisting?: boolean) => {
    if (!uploadedFile) throw new Error('请先选择文件')

    const resolvedFormat = format || importFormat || form.getFieldValue('importFormat') || 'json'
    const formData = new FormData()
    formData.append('file', uploadedFile)
    formData.append('format_type', resolvedFormat)
    formData.append('environment', environment)
    if (overwriteExisting !== undefined) {
      formData.append('overwrite_existing', String(overwriteExisting))
    }
    if (groupId) {
      formData.append('group_id', String(groupId))
    }
    return formData
  }

  const handleExport = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      const params = new URLSearchParams({
        format_type: values.exportFormat,
        environment,
        include_sensitive: String(Boolean(values.includeSensitive)),
      })

      if (groupId) params.append('group_id', String(groupId))
      if (values.configKeys) params.append('config_keys', values.configKeys)

      const blob = await api.post(`/configs/import-export/export?${params}`, null, {
        responseType: 'blob',
      }) as unknown as Blob

      const extension = FILE_FORMATS.find((item) => item.value === values.exportFormat)?.extensions[0] || '.txt'
      downloadBlob(blob, `config_${environment}_${values.exportFormat}${extension}`)
      message.success('导出成功')
      handleClose()
    } catch (error: any) {
      message.error(error?.message || '导出失败')
      console.error('配置导出失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePreviewImport = async () => {
    if (!uploadedFile) {
      message.error('请先选择文件')
      return
    }

    try {
      const values = await form.validateFields(['importFormat'])
      const selectedFormat = values.importFormat || importFormat || 'json'
      setImportFormat(selectedFormat)
      setLoading(true)

      const response = await api.post(
        '/configs/import-export/import/preview',
        createImportFormData(selectedFormat),
      )
      const payload = getApiPayload<PreviewData>(response)

      if (payload.success && payload.data) {
        setPreviewData(payload.data)
        setShowPreview(true)
      } else {
        message.error(payload.message || '预览失败')
      }
    } catch (error: any) {
      message.error(getApiErrorMessage(error, '预览失败'))
      console.error('配置导入预览失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async (overwrite = false) => {
    if (!uploadedFile) {
      message.error('请先选择文件')
      return
    }

    let progressTimer: number | undefined
    try {
      const values = showPreview ? { importFormat } : await form.validateFields(['importFormat'])
      const selectedFormat = values.importFormat || importFormat || 'json'
      setImportFormat(selectedFormat)
      setLoading(true)
      setImportProgress(5)

      progressTimer = window.setInterval(() => {
        setImportProgress((prev) => Math.min(prev + 10, 90))
      }, 200)

      const endpoint = overwrite
        ? '/configs/import-export/import/force'
        : '/configs/import-export/import'
      const response = await api.post(endpoint, createImportFormData(selectedFormat, overwrite))
      const payload = getApiPayload<any>(response)

      if (progressTimer) window.clearInterval(progressTimer)
      setImportProgress(100)

      if (payload.success) {
        const result = payload.data || {}
        message.success(`导入完成：成功 ${result.success_count || 0} 个，失败 ${result.error_count || 0} 个`)
        setTimeout(() => {
          resetState()
          onSuccess()
        }, 500)
        return
      }

      if (payload.data?.conflicts?.length) {
        Modal.confirm({
          title: '配置冲突',
          content: `发现 ${payload.data.conflicts.length} 个配置已存在，是否覆盖现有配置？`,
          okText: '覆盖导入',
          cancelText: '取消',
          onOk: () => handleImport(true),
        })
      } else {
        message.error(payload.message || '导入失败')
      }
    } catch (error: any) {
      message.error(getApiErrorMessage(error, '导入失败'))
      console.error('配置导入失败:', error)
    } finally {
      if (progressTimer) window.clearInterval(progressTimer)
      setLoading(false)
      setTimeout(() => setImportProgress(0), 500)
    }
  }

  const handleDownloadTemplate = async (format: string) => {
    try {
      const blob = await api.get(`/configs/import-export/template/${format}`, {
        responseType: 'blob',
      }) as unknown as Blob
      const extension = FILE_FORMATS.find((item) => item.value === format)?.extensions[0] || '.txt'
      downloadBlob(blob, `config_template${extension}`)
      message.success('模板下载成功')
    } catch (error) {
      message.error('模板下载失败')
      console.error('配置模板下载失败:', error)
    }
  }

  const previewColumns = [
    {
      title: '配置键',
      dataIndex: 'key',
      key: 'key',
      width: 220,
    },
    {
      title: '配置值',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
      render: (value: unknown) => (
        <Tooltip title={typeof value === 'string' ? value : JSON.stringify(value)}>
          <Text code>{typeof value === 'string' ? value : JSON.stringify(value)}</Text>
        </Tooltip>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag color="blue">{type || 'STRING'}</Tag>,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: any) => {
        const isConflict = previewData?.conflicts.some((item) => item.key === record.key)
        const isNew = previewData?.new_configs.includes(record.key)

        if (isConflict) return <Tag color="orange" icon={<ExclamationCircleOutlined />}>冲突</Tag>
        if (isNew) return <Tag color="green" icon={<CheckCircleOutlined />}>新增</Tag>
        return <Tag color="blue" icon={<InfoCircleOutlined />}>更新</Tag>
      },
    },
  ]

  const conflictColumns = [
    {
      title: '配置键',
      dataIndex: 'key',
      key: 'key',
      width: 220,
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
      ),
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
      ),
    },
  ]

  const previewRows = previewData
    ? Object.entries(previewData.configs || {}).map(([key, config]) => ({
      key,
      ...(typeof config === 'object' && config !== null ? config : { value: config, type: 'STRING' }),
    }))
    : []

  return (
    <Modal
      title="配置导入导出"
      open={visible}
      onCancel={handleClose}
      width={860}
      footer={null}
      destroyOnHidden
    >
      <div className="mb-4">
        <Space.Compact>
          <Button
            type={activeTab === 'export' ? 'primary' : 'default'}
            icon={<DownloadOutlined />}
            onClick={() => {
              setActiveTab('export')
              setShowPreview(false)
            }}
          >
            导出配置
          </Button>
          <Button
            type={activeTab === 'import' ? 'primary' : 'default'}
            icon={<UploadOutlined />}
            onClick={() => {
              setActiveTab('import')
              form.setFieldsValue({ importFormat })
            }}
          >
            导入配置
          </Button>
        </Space.Compact>
      </div>

      {activeTab === 'export' && (
        <Card title="导出配置">
          <Form form={form} layout="vertical" initialValues={{ exportFormat: 'json', includeSensitive: false }}>
            <Form.Item
              name="exportFormat"
              label="导出格式"
              rules={[{ required: true, message: '请选择导出格式' }]}
            >
              <Select placeholder="选择导出格式">
                {FILE_FORMATS.map((format) => (
                  <Option key={format.value} value={format.value}>
                    <div>
                      <div>{format.label}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>{format.description}</div>
                    </div>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="configKeys"
              label="指定配置键"
              help="可选，用逗号分隔多个配置键；留空表示导出当前环境所有配置。"
            >
              <Input.TextArea rows={2} placeholder="例如：app.name,database.host,redis.url" />
            </Form.Item>

            <Form.Item name="includeSensitive" valuePropName="checked">
              <Checkbox>包含敏感配置</Checkbox>
            </Form.Item>

            <div className="flex justify-end gap-2">
              <Button onClick={handleClose}>取消</Button>
              <Button type="primary" icon={<DownloadOutlined />} loading={loading} onClick={handleExport}>
                导出
              </Button>
            </div>
          </Form>
        </Card>
      )}

      {activeTab === 'import' && !showPreview && (
        <Card title="导入配置">
          <Form form={form} layout="vertical" initialValues={{ importFormat }}>
            <Form.Item
              name="importFormat"
              label="文件格式"
              rules={[{ required: true, message: '请选择文件格式' }]}
            >
              <Select placeholder="选择文件格式" value={importFormat} onChange={setImportFormat}>
                {FILE_FORMATS.map((format) => (
                  <Option key={format.value} value={format.value}>
                    <Space>
                      <FileTextOutlined />
                      <div>
                        <div>{format.label}</div>
                        <div style={{ fontSize: 12, color: '#666' }}>支持：{format.extensions.join(', ')}</div>
                      </div>
                    </Space>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item label="选择文件" help="支持拖拽上传或点击选择文件，文件大小限制 10MB。">
              <Dragger
                beforeUpload={(file) => {
                  const inferredFormat = inferImportFormatFromFileName(file.name)
                  if (inferredFormat) {
                    setImportFormat(inferredFormat)
                    form.setFieldsValue({ importFormat: inferredFormat })
                  }
                  setUploadedFile(file)
                  setPreviewData(null)
                  setShowPreview(false)
                  return false
                }}
                onRemove={() => {
                  setUploadedFile(null)
                  setPreviewData(null)
                  setShowPreview(false)
                }}
                fileList={uploadedFile ? [uploadedFile as any] : []}
                maxCount={1}
                accept=".env,.json,.yml,.yaml,.xml,.properties"
              >
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">导入前建议先预览，确认配置键、类型和冲突项。</p>
              </Dragger>
            </Form.Item>

            <Alert
              message="导入说明"
              description="预览不会写入数据；确认导入时如存在冲突，系统会提示是否覆盖现有配置。"
              type="info"
              className="mb-4"
              showIcon
            />

            <div className="flex flex-wrap justify-between gap-2">
              <Space wrap>
                {FILE_FORMATS.map((format) => (
                  <Button key={format.value} size="small" onClick={() => handleDownloadTemplate(format.value)}>
                    下载 {format.label} 模板
                  </Button>
                ))}
              </Space>
              <Space>
                <Button onClick={handleClose}>取消</Button>
                <Button icon={<EyeOutlined />} loading={loading} onClick={handlePreviewImport} disabled={!uploadedFile}>
                  预览
                </Button>
                <Button type="primary" icon={<UploadOutlined />} loading={loading} onClick={() => handleImport(false)} disabled={!uploadedFile}>
                  保存导入
                </Button>
              </Space>
            </div>
          </Form>
        </Card>
      )}

      {activeTab === 'import' && showPreview && previewData && (
        <div>
          <Card title="导入预览" className="mb-4">
            <Row gutter={16}>
              <Col span={6}><Statistic title="总配置数" value={previewData.total_configs} /></Col>
              <Col span={6}><Statistic title="新增配置" value={previewData.new_configs.length} valueStyle={{ color: '#52c41a' }} /></Col>
              <Col span={6}><Statistic title="冲突配置" value={previewData.conflicts.length} valueStyle={{ color: '#faad14' }} /></Col>
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
                description="以下配置在目标环境中已存在，确认导入时可选择覆盖现有值。"
                type="warning"
                className="mb-3"
                showIcon
              />
              <Table columns={conflictColumns} dataSource={previewData.conflicts} rowKey="key" size="small" scroll={{ y: 200 }} />
            </Card>
          )}

          <Card title="全部配置">
            <Table columns={previewColumns} dataSource={previewRows} rowKey="key" size="small" scroll={{ y: 300 }} />
          </Card>

          <div className="mt-4 flex justify-end gap-2">
            <Button onClick={() => setShowPreview(false)}>返回</Button>
            <Button onClick={handleClose}>取消</Button>
            <Button type="primary" icon={<UploadOutlined />} loading={loading} onClick={() => handleImport(false)}>
              保存导入
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
