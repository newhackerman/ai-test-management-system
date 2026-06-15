import React, { useState, useEffect } from 'react'
import { Card, Button, Table, Space, Modal, Form, Input, Switch, ColorPicker, Select, message, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOutlined } from '@ant-design/icons'
import { ConfigService, ConfigGroup } from '@/services/config-service'

const { TextArea } = Input

// 图标选项
const ICON_OPTIONS = [
  { value: 'settings', label: '设置' },
  { value: 'database', label: '数据库' },
  { value: 'layer-group', label: '分层' },
  { value: 'shield', label: '安全' },
  { value: 'envelope', label: '邮件' },
  { value: 'file-text', label: '文件' },
  { value: 'briefcase', label: '业务' },
  { value: 'plug', label: '插件' },
  { value: 'cloud', label: '云服务' },
  { value: 'api', label: 'API' }
]

export default function ConfigGroupManagement() {
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [loading, setLoading] = useState(false)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [editingGroup, setEditingGroup] = useState<ConfigGroup | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadGroups()
  }, [])

  const loadGroups = async () => {
    setLoading(true)
    try {
      const groupList = await ConfigService.getConfigGroups()
      setGroups(groupList)
    } catch (error) {
      message.error('加载分组列表失败')
      console.error('加载分组失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '分组名称',
      dataIndex: 'group_name',
      key: 'group_name',
      render: (text: string, record: ConfigGroup) => (
        <div className="flex items-center space-x-2">
          <FolderOutlined style={{ color: record.color || '#1890ff' }} />
          <span className="font-medium">{text}</span>
          {record.is_system && <Tag color="red">系统</Tag>}
        </div>
      )
    },
    {
      title: '分组代码',
      dataIndex: 'group_code',
      key: 'group_code',
      render: (text: string) => (
        <code className="bg-gray-100 px-2 py-1 rounded text-sm dark:bg-gray-800">{text}</code>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '层级',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: number) => (
        <Tag color="blue">L{level}</Tag>
      )
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80
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
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: ConfigGroup) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            disabled={record.is_system}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
            disabled={record.is_system}
          >
            删除
          </Button>
        </Space>
      )
    }
  ]

  const handleEdit = (group: ConfigGroup) => {
    setEditingGroup(group)
    form.setFieldsValue(group)
    setIsModalVisible(true)
  }

  const handleDelete = (group: ConfigGroup) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除分组 "${group.group_name}" 吗？删除后该分组下的配置将移至未分组。`,
      onOk: async () => {
        try {
          await ConfigService.deleteConfigGroup(group.id)
          message.success('删除成功')
          loadGroups()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  const handleSubmit = async (values: any) => {
    const payload = {
      ...values,
      level: Number(values.level || 1),
      sort_order: Number(values.sort_order || 0)
    }

    try {
      if (editingGroup) {
        await ConfigService.updateConfigGroup(editingGroup.id, payload)
        message.success('更新成功')
      } else {
        await ConfigService.createConfigGroup(payload)
        message.success('创建成功')
      }
      
      setIsModalVisible(false)
      form.resetFields()
      setEditingGroup(null)
      loadGroups()
    } catch (error) {
      message.error(editingGroup ? '更新失败' : '创建失败')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingGroup(null)
            form.resetFields()
            setIsModalVisible(true)
          }}
        >
          新增分组
        </Button>
      </div>

      <Card size="small">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold">分组列表</div>
            <div className="text-xs text-muted-foreground">系统分组不可直接编辑或删除</div>
          </div>
          <Button onClick={loadGroups}>刷新</Button>
        </div>
        <Table
          columns={columns}
          dataSource={groups}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
          }}
        />
      </Card>

      <Modal
        title={editingGroup ? '编辑分组' : '新增分组'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false)
          form.resetFields()
          setEditingGroup(null)
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            level: 1,
            sort_order: 0,
            is_enabled: true,
            is_system: false
          }}
        >
          <Form.Item
            name="group_name"
            label="分组名称"
            rules={[{ required: true, message: '请输入分组名称' }]}
          >
            <Input placeholder="如: 系统配置" />
          </Form.Item>
          
          <Form.Item
            name="group_code"
            label="分组代码"
            rules={[
              { required: true, message: '请输入分组代码' },
              { pattern: /^[a-z][a-z0-9_]*$/, message: '代码只能包含小写字母、数字和下划线，且以字母开头' }
            ]}
          >
            <Input placeholder="如: system_config" disabled={!!editingGroup} />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="分组的详细描述" />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="icon"
              label="图标"
            >
              <Select placeholder="选择图标" allowClear>
                {ICON_OPTIONS.map(option => (
                  <Select.Option key={option.value} value={option.value}>
                    {option.label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="color"
              label="颜色"
            >
              <Input placeholder="#1890ff" />
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="level"
              label="层级"
              rules={[{ required: true, message: '请输入层级' }]}
            >
              <Select>
                <Select.Option value={1}>1级</Select.Option>
                <Select.Option value={2}>2级</Select.Option>
                <Select.Option value={3}>3级</Select.Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="sort_order"
              label="排序序号"
              rules={[{ required: true, message: '请输入排序序号' }]}
            >
              <Input type="number" placeholder="0" />
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item name="is_enabled" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>

            <Form.Item name="is_system" valuePropName="checked">
              <Switch checkedChildren="系统分组" unCheckedChildren="自定义分组" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
