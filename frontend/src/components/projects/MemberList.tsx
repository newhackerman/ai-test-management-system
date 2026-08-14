// @ts-nocheck
import { useState } from 'react'
import {
  DeleteOutlined,
  EditOutlined,
  MailOutlined,
  MoreOutlined,
  PhoneOutlined,
  PlusOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Avatar, Button, Card, Dropdown, Form, Input, InputNumber, message, Modal, Progress, Select, Space, Table, Tag, Tooltip } from 'antd'

import { apiClient } from '@/lib/api-client'
import { ProjectService } from '@/services/projectService'
import type { ProjectMember } from '@/types/project'

interface MemberListProps {
  projectId: number
  editable?: boolean
}

interface MemberFormData {
  user_id: number
  role_in_project: ProjectMember['role_in_project']
  allocation_percentage: number
  responsibilities?: string
}

interface AvailableUser {
  id: number
  username: string
  real_name?: string
  full_name?: string
  nickname?: string
  email?: string
}

const ROLE_COLORS = {
  ADMIN: 'red',
  PROJECT_MANAGER: 'purple',
  REQUIREMENT_MANAGER: 'blue',
  DESIGNER: 'cyan',
  ARCHITECT: 'green',
  DEVELOPER: 'orange',
  TESTER: 'gold',
  DEVOPS: 'magenta',
  THIRD_PARTY: 'default',
} as const

const ROLE_LABELS = {
  ADMIN: '系统管理员',
  PROJECT_MANAGER: '项目经理',
  REQUIREMENT_MANAGER: '需求管理员',
  DESIGNER: '设计人员',
  ARCHITECT: '架构师',
  DEVELOPER: '开发人员',
  TESTER: '测试人员',
  DEVOPS: '运维人员',
  THIRD_PARTY: '第三方人员',
} as const

const STATUS_LABELS = {
  ACTIVE: { color: 'green', text: '活跃' },
  INACTIVE: { color: 'default', text: '非活跃' },
  ON_LEAVE: { color: 'orange', text: '请假' },
} as const

const getUserName = (user?: any) => user?.real_name || user?.full_name || user?.nickname || user?.username || '未命名用户'

const formatDate = (value?: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

const unwrapList = (response: any): AvailableUser[] => {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.users)) return response.users
  if (Array.isArray(response?.data)) return response.data
  if (Array.isArray(response?.data?.users)) return response.data.users
  return []
}

export const MemberList: React.FC<MemberListProps> = ({ projectId, editable = false }) => {
  const [isAddModalVisible, setIsAddModalVisible] = useState(false)
  const [isEditModalVisible, setIsEditModalVisible] = useState(false)
  const [editingMember, setEditingMember] = useState<ProjectMember | null>(null)
  const [form] = Form.useForm<MemberFormData>()
  const queryClient = useQueryClient()

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['projects', projectId, 'members'],
    queryFn: async () => {
      const response = await ProjectService.getProjectMembers(projectId)
      return Array.isArray(response) ? response : response?.members || response?.data || []
    },
    enabled: !!projectId,
  })

  const { data: availableUsers = [], isLoading: loadingUsers } = useQuery({
    queryKey: ['users', 'available'],
    queryFn: async () => unwrapList(await apiClient.get('/users?size=200')),
    enabled: isAddModalVisible,
  })

  const addMemberMutation = useMutation({
    mutationFn: (data: MemberFormData) => ProjectService.addProjectMember(projectId, data),
    onSuccess: () => {
      message.success('成员添加成功')
      setIsAddModalVisible(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'members'] })
    },
    onError: (error: any) => message.error(error?.message || '添加成员失败'),
  })

  const updateMemberMutation = useMutation({
    mutationFn: ({ memberId, data }: { memberId: number; data: Partial<MemberFormData> }) =>
      ProjectService.updateProjectMember(projectId, memberId, data),
    onSuccess: () => {
      message.success('成员信息更新成功')
      setIsEditModalVisible(false)
      setEditingMember(null)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'members'] })
    },
    onError: (error: any) => message.error(error?.message || '更新成员信息失败'),
  })

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: number) => ProjectService.removeProjectMember(projectId, memberId),
    onSuccess: () => {
      message.success('成员移除成功')
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'members'] })
    },
    onError: (error: any) => message.error(error?.message || '移除成员失败'),
  })

  const handleAddMember = () => {
    form.validateFields().then((values) => addMemberMutation.mutate(values))
  }

  const handleEditMember = (member: ProjectMember) => {
    setEditingMember(member)
    form.setFieldsValue({
      role_in_project: member.role_in_project,
      allocation_percentage: member.allocation_percentage,
      responsibilities: member.responsibilities,
    })
    setIsEditModalVisible(true)
  }

  const handleUpdateMember = () => {
    if (!editingMember) return
    form.validateFields().then((values) => {
      updateMemberMutation.mutate({
        memberId: editingMember.id,
        data: values,
      })
    })
  }

  const handleRemoveMember = (member: ProjectMember) => {
    Modal.confirm({
      title: '确认移除成员',
      content: `确定要将 ${getUserName(member.user)} 从项目中移除吗？`,
      okText: '移除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => removeMemberMutation.mutate(member.id),
    })
  }

  const getWorkloadColor = (allocation: number) => {
    if (allocation >= 100) return '#f87171'
    if (allocation >= 80) return '#fbbf24'
    if (allocation >= 60) return '#16a34a'
    return '#2563eb'
  }

  const columns: any[] = [
    {
      title: '成员',
      key: 'member',
      render: (record: ProjectMember) => (
        <Space>
          <Avatar src={record.user?.avatar || record.user?.avatar_url} icon={<UserOutlined />} size="small" />
          <div>
            <div className="font-medium">{getUserName(record.user)}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{record.user?.email || '-'}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role_in_project',
      key: 'role',
      render: (role: ProjectMember['role_in_project']) => (
        <Tag color={ROLE_COLORS[role]}>{ROLE_LABELS[role] || role}</Tag>
      ),
    },
    {
      title: '参与度',
      dataIndex: 'allocation_percentage',
      key: 'allocation',
      render: (allocation: number) => (
        <div className="w-28">
          <Progress percent={allocation} size="small" strokeColor={getWorkloadColor(allocation)} />
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: ProjectMember['status']) => {
        const config = STATUS_LABELS[status] || STATUS_LABELS.ACTIVE
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '加入时间',
      dataIndex: 'join_date',
      key: 'join_date',
      render: formatDate,
    },
    {
      title: '联系方式',
      key: 'contact',
      render: (record: ProjectMember) => (
        <Space>
          {record.user?.email && (
            <Tooltip title={record.user.email}>
              <Button type="text" size="small" icon={<MailOutlined />} onClick={() => window.open(`mailto:${record.user?.email}`)} />
            </Tooltip>
          )}
          {record.user?.phone && (
            <Tooltip title={record.user.phone}>
              <Button type="text" size="small" icon={<PhoneOutlined />} onClick={() => window.open(`tel:${record.user?.phone}`)} />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ]

  if (editable) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (record: ProjectMember) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'edit',
                label: '编辑',
                icon: <EditOutlined />,
                onClick: () => handleEditMember(record),
              },
              {
                key: 'remove',
                label: '移除',
                icon: <DeleteOutlined />,
                danger: true,
                onClick: () => handleRemoveMember(record),
              },
            ],
          }}
          trigger={['click']}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    })
  }

  const renderMemberForm = (includeUser: boolean) => (
    <Form form={form} layout="vertical" initialValues={{ allocation_percentage: 100 }}>
      {includeUser && (
        <Form.Item name="user_id" label="选择用户" rules={[{ required: true, message: '请选择用户' }]}>
          <Select
            placeholder="请选择要添加的用户"
            showSearch
            loading={loadingUsers}
            optionFilterProp="label"
            options={availableUsers.map((user) => ({
              value: user.id,
              label: `${getUserName(user)}${user.email ? ` (${user.email})` : ''}`,
            }))}
          />
        </Form.Item>
      )}

      <Form.Item name="role_in_project" label="项目角色" rules={[{ required: true, message: '请选择项目角色' }]}>
        <Select placeholder="请选择项目角色">
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <Select.Option key={value} value={value}>
              <Tag color={ROLE_COLORS[value as keyof typeof ROLE_COLORS]}>{label}</Tag>
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="allocation_percentage"
        label="参与度（%）"
        rules={[
          { required: true, message: '请输入参与度' },
          { type: 'number', min: 1, max: 200, message: '参与度应在 1-200% 之间' },
        ]}
      >
        <InputNumber min={1} max={200} formatter={(value) => `${value}%`} parser={(value) => value!.replace('%', '')} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name="responsibilities" label="职责描述">
        <Input.TextArea rows={3} placeholder="请描述该成员在项目中的具体职责..." />
      </Form.Item>
    </Form>
  )

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>团队成员（{members.length}）</span>
        </Space>
      }
      extra={
        editable && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsAddModalVisible(true)}>
            添加成员
          </Button>
        )
      }
    >
      <Table columns={columns} dataSource={members} rowKey="id" loading={isLoading} pagination={false} size="small" />

      <Modal
        title="添加团队成员"
        open={isAddModalVisible}
        onOk={handleAddMember}
        onCancel={() => {
          setIsAddModalVisible(false)
          form.resetFields()
        }}
        confirmLoading={addMemberMutation.isPending}
        okText="添加"
        cancelText="取消"
      >
        {renderMemberForm(true)}
      </Modal>

      <Modal
        title="编辑成员信息"
        open={isEditModalVisible}
        onOk={handleUpdateMember}
        onCancel={() => {
          setIsEditModalVisible(false)
          setEditingMember(null)
          form.resetFields()
        }}
        confirmLoading={updateMemberMutation.isPending}
        okText="保存"
        cancelText="取消"
      >
        {renderMemberForm(false)}
      </Modal>
    </Card>
  )
}

export default MemberList
