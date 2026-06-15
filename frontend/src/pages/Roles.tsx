import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Dropdown,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  MoreOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'

const { Search } = Input
const { TextArea } = Input
const { Text } = Typography

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

interface Role {
  id: number
  name: string
  raw_name?: string
  code: string
  description: string
  is_active: boolean
  is_system_role: boolean
  priority?: number
  sort?: number
  sort_order?: number
  user_count: number
  permission_count: number
  permissions?: Permission[]
  created_at: string
  updated_at?: string
}

interface Permission {
  id: number
  code: string
  name: string
  description?: string
  module: string
  type?: string
  action?: string
  is_active?: boolean
}

interface RoleUser {
  id: number
  username: string
  email: string
  nickname?: string
  status?: string
  is_active: boolean
  last_login_at?: string
  created_at?: string
}

interface RoleStats {
  total_roles: number
  active_roles: number
  inactive_roles: number
  system_roles?: number
  custom_roles?: number
  average_users_per_role: number
  total_permissions: number
}

const ROLE_NAME_MAP: Record<string, string> = {
  admin: '系统管理员',
  user: '普通用户',
  SUPER_ADMIN: '超级管理员',
  SYSTEM_ADMIN: '系统管理员',
  CONFIG_ADMIN: '配置管理员',
  PROJECT_MANAGER: '项目管理员',
  DEVELOPER: '开发人员',
  TESTER: '测试人员',
  DEVOPS: '运维人员',
  READONLY_USER: '只读用户',
}

const getAuthToken = () => {
  const legacyToken = localStorage.getItem('auth-access-token') || localStorage.getItem('token') || localStorage.getItem('auth_token')
  if (legacyToken) return legacyToken

  const authStorage = localStorage.getItem('auth-storage')
  if (!authStorage) return null

  try {
    return JSON.parse(authStorage)?.state?.token || null
  } catch {
    return null
  }
}

const apiFetch = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
  const token = getAuthToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = typeof data === 'object' ? data?.detail || data?.message : data
    throw new Error(detail || `请求失败：${response.status}`)
  }

  return data as T
}

const formatDateTime = (value?: string) => {
  if (!value) return '-'
  const base = value.includes('T') ? value : value.replace(' ', 'T')
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(base) ? base : `${base}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
}

const normalizeRoleName = (role: any) => ROLE_NAME_MAP[role.code] || role.name || role.raw_name || ''

const normalizeRole = (role: any): Role => ({
  id: Number(role.id),
  name: normalizeRoleName(role),
  raw_name: role.raw_name,
  code: role.code || '',
  description: role.description || '',
  is_active: role.is_active !== false,
  is_system_role: Boolean(role.is_system_role || role.is_system),
  priority: Number(role.priority || 0),
  sort: Number(role.sort ?? role.sort_order ?? 0),
  sort_order: Number(role.sort_order ?? role.sort ?? 0),
  user_count: Number(role.user_count || 0),
  permission_count: Number(role.permission_count || role.permissions?.length || 0),
  permissions: role.permissions || [],
  created_at: role.created_at,
  updated_at: role.updated_at,
})

const Roles: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [roleUsers, setRoleUsers] = useState<RoleUser[]>([])
  const [loading, setLoading] = useState(false)
  const [statsLoading, setStatsLoading] = useState(false)
  const [permissionsLoading, setPermissionsLoading] = useState(false)
  const [usersLoading, setUsersLoading] = useState(false)
  const [savingPermissions, setSavingPermissions] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>()
  const [statusFilter, setStatusFilter] = useState<string>()
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [stats, setStats] = useState<RoleStats | null>(null)
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  const [form] = Form.useForm()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<Role | null>(null)
  const [viewingRole, setViewingRole] = useState<Role | null>(null)
  const [permissionRole, setPermissionRole] = useState<Role | null>(null)
  const [userRole, setUserRole] = useState<Role | null>(null)
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([])

  const permissionOptions = useMemo(
    () =>
      permissions.map((permission) => ({
        label: (
          <Space direction="vertical" size={0}>
            <span>{permission.name}</span>
            <Text type="secondary" className="text-xs">
              {permission.code}
            </Text>
          </Space>
        ),
        value: permission.id,
      })),
    [permissions],
  )

  const fetchStats = useCallback(async () => {
    setStatsLoading(true)
    try {
      const data = await apiFetch<RoleStats>('/api/v1/roles/stats')
      setStats(data)
    } catch (error: any) {
      message.warning(error.message || '获取角色统计失败')
    } finally {
      setStatsLoading(false)
    }
  }, [])

  const fetchRoles = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(pagination.current),
        size: String(pagination.pageSize),
      })
      if (searchText.trim()) params.set('search', searchText.trim())
      if (typeFilter) params.set('type', typeFilter)
      if (statusFilter) params.set('status', statusFilter)

      const data = await apiFetch<any>(`/api/v1/roles?${params.toString()}`)
      const list = (data.data || data.roles || []).map(normalizeRole)
      setRoles(list)
      setPagination((prev) => ({ ...prev, total: Number(data.total || list.length) }))
    } catch (error: any) {
      setRoles([])
      message.error(error.message || '获取角色列表失败')
    } finally {
      setLoading(false)
    }
  }, [pagination.current, pagination.pageSize, searchText, statusFilter, typeFilter])

  const fetchPermissions = useCallback(async () => {
    setPermissionsLoading(true)
    try {
      const data = await apiFetch<any>('/api/v1/roles/permissions/catalog')
      setPermissions(data.permissions || data.data || [])
    } catch (error: any) {
      setPermissions([])
      message.error(error.message || '获取权限列表失败')
    } finally {
      setPermissionsLoading(false)
    }
  }, [])

  const refresh = useCallback(() => {
    fetchRoles()
    fetchStats()
  }, [fetchRoles, fetchStats])

  useEffect(() => {
    fetchRoles()
  }, [fetchRoles])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  const resetToFirstPage = (setter: (value: string | undefined) => void, value?: string) => {
    setter(value)
    setPagination((prev) => ({ ...prev, current: 1 }))
  }

  const handleCreateRole = async (values: any) => {
    try {
      const payload = {
        name: values.name,
        code: values.code.toUpperCase(),
        description: values.description || '',
        is_active: values.is_active !== false,
        priority: values.priority || 0,
        sort_order: values.sort_order || 0,
        permission_ids: values.permission_ids || [],
      }
      await apiFetch('/api/v1/roles', { method: 'POST', body: JSON.stringify(payload) })
      message.success('角色创建成功')
      setIsCreateModalOpen(false)
      form.resetFields()
      refresh()
    } catch (error: any) {
      message.error(error.message || '角色创建失败')
    }
  }

  const handleUpdateRole = async (values: any) => {
    if (!editingRole) return
    try {
      const payload = {
        name: values.name,
        description: values.description || '',
        is_active: values.is_active !== false,
        priority: values.priority || 0,
        sort_order: values.sort_order || 0,
      }
      await apiFetch(`/api/v1/roles/${editingRole.id}`, { method: 'PUT', body: JSON.stringify(payload) })
      message.success('角色更新成功')
      setEditingRole(null)
      form.resetFields()
      refresh()
    } catch (error: any) {
      message.error(error.message || '角色更新失败')
    }
  }

  const handleDeleteRole = async (role: Role) => {
    Modal.confirm({
      title: '确认删除角色',
      content: `删除后无法恢复，确定删除“${role.name}”吗？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await apiFetch(`/api/v1/roles/${role.id}`, { method: 'DELETE' })
        message.success('角色删除成功')
        refresh()
      },
    })
  }

  const handleBatchDelete = async () => {
    const targetRoles = roles.filter((role) => selectedRowKeys.includes(role.id))
    Modal.confirm({
      title: '确认批量删除',
      content: `确定删除选中的 ${targetRoles.length} 个自定义角色吗？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        for (const role of targetRoles) {
          await apiFetch(`/api/v1/roles/${role.id}`, { method: 'DELETE' })
        }
        setSelectedRowKeys([])
        message.success('批量删除完成')
        refresh()
      },
    })
  }

  const handleToggleRoleStatus = async (role: Role) => {
    try {
      const action = role.is_active ? 'deactivate' : 'activate'
      await apiFetch(`/api/v1/roles/${role.id}/${action}`, { method: 'POST' })
      message.success(role.is_active ? '角色已停用' : '角色已启用')
      refresh()
    } catch (error: any) {
      message.error(error.message || '角色状态更新失败')
    }
  }

  const openEditModal = (role: Role) => {
    setEditingRole(role)
    form.setFieldsValue({
      name: role.raw_name || role.name,
      description: role.description,
      is_active: role.is_active,
      priority: role.priority || 0,
      sort_order: role.sort_order || role.sort || 0,
    })
  }

  const openViewModal = async (role: Role) => {
    try {
      const data = await apiFetch<any>(`/api/v1/roles/${role.id}`)
      setViewingRole(normalizeRole(data.data || data))
    } catch (error: any) {
      message.error(error.message || '获取角色详情失败')
    }
  }

  const openPermissionModal = async (role: Role) => {
    setPermissionRole(role)
    setSelectedPermissionIds([])
    try {
      if (permissions.length === 0) await fetchPermissions()
      const data = await apiFetch<any>(`/api/v1/roles/${role.id}/permissions`)
      const assigned = data.permissions || data.data || []
      setSelectedPermissionIds(assigned.map((permission: Permission) => permission.id))
    } catch (error: any) {
      message.error(error.message || '获取角色权限失败')
    }
  }

  const saveRolePermissions = async () => {
    if (!permissionRole) return
    setSavingPermissions(true)
    try {
      await apiFetch(`/api/v1/roles/${permissionRole.id}/permissions`, {
        method: 'POST',
        body: JSON.stringify({ permission_ids: selectedPermissionIds }),
      })
      message.success('权限分配成功')
      setPermissionRole(null)
      refresh()
    } catch (error: any) {
      message.error(error.message || '权限分配失败')
    } finally {
      setSavingPermissions(false)
    }
  }

  const openUsersModal = async (role: Role) => {
    setUserRole(role)
    setUsersLoading(true)
    try {
      const data = await apiFetch<any>(`/api/v1/roles/${role.id}/users?page=1&size=100`)
      setRoleUsers(data.users || data.data || [])
    } catch (error: any) {
      setRoleUsers([])
      message.error(error.message || '获取角色用户失败')
    } finally {
      setUsersLoading(false)
    }
  }

  const columns: ColumnsType<Role> = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <span className="font-medium">{record.name}</span>
            {record.is_system_role ? <Tag color="blue">系统</Tag> : <Tag color="green">自定义</Tag>}
          </Space>
          {record.description ? <Text type="secondary">{record.description}</Text> : null}
        </Space>
      ),
    },
    {
      title: '角色代码',
      dataIndex: 'code',
      key: 'code',
      width: 180,
      render: (code) => <code className="rounded bg-gray-100 px-2 py-1">{code}</code>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active) => <Badge status={active ? 'success' : 'default'} text={active ? '启用' : '停用'} />,
    },
    {
      title: '用户',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 110,
      render: (count, record) => (
        <Button type="link" size="small" onClick={() => openUsersModal(record)}>
          {count || 0} 人
        </Button>
      ),
    },
    {
      title: '权限',
      dataIndex: 'permission_count',
      key: 'permission_count',
      width: 110,
      render: (count, record) => (
        <Button type="link" size="small" onClick={() => openPermissionModal(record)}>
          {count || 0} 项
        </Button>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 90,
      render: (_, record) => record.sort_order ?? record.sort ?? 0,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: formatDateTime,
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_, record) => (
        <Dropdown
          trigger={['click']}
          menu={{
            items: [
              { key: 'view', label: '查看详情', icon: <EyeOutlined />, onClick: () => openViewModal(record) },
              { key: 'permissions', label: '分配权限', icon: <SafetyOutlined />, onClick: () => openPermissionModal(record) },
              { key: 'users', label: '查看用户', icon: <TeamOutlined />, onClick: () => openUsersModal(record) },
              { key: 'edit', label: '编辑', icon: <EditOutlined />, onClick: () => openEditModal(record) },
              {
                key: 'toggle',
                label: record.is_active ? '停用' : '启用',
                disabled: record.code === 'SUPER_ADMIN',
                onClick: () => handleToggleRoleStatus(record),
              },
              { type: 'divider' },
              {
                key: 'delete',
                label: '删除',
                icon: <DeleteOutlined />,
                danger: true,
                disabled: record.is_system_role,
                onClick: () => handleDeleteRole(record),
              },
            ],
          }}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ]

  const roleForm = (
    <Form form={form} layout="vertical" initialValues={{ is_active: true, priority: 0, sort_order: 0 }} onFinish={editingRole ? handleUpdateRole : handleCreateRole}>
      <Form.Item
        name="name"
        label="角色名称"
        rules={[
          { required: true, message: '请输入角色名称' },
          { min: 2, max: 100, message: '角色名称长度为 2-100 个字符' },
        ]}
      >
        <Input placeholder="请输入角色名称" />
      </Form.Item>

      {!editingRole && (
        <Form.Item
          name="code"
          label="角色代码"
          normalize={(value) => value?.toUpperCase()}
          rules={[
            { required: true, message: '请输入角色代码' },
            { pattern: /^[A-Z0-9_]+$/, message: '只能包含大写字母、数字和下划线' },
            { min: 2, max: 50, message: '角色代码长度为 2-50 个字符' },
          ]}
        >
          <Input placeholder="例如：CUSTOM_ADMIN" />
        </Form.Item>
      )}

      <Form.Item name="description" label="角色描述">
        <TextArea rows={3} maxLength={500} showCount placeholder="请输入角色描述" />
      </Form.Item>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Form.Item name="priority" label="优先级">
          <InputNumber min={0} max={999} className="w-full" />
        </Form.Item>
        <Form.Item name="sort_order" label="排序">
          <InputNumber min={0} max={999} className="w-full" />
        </Form.Item>
        <Form.Item name="is_active" label="启用状态" valuePropName="checked">
          <Switch checkedChildren="启用" unCheckedChildren="停用" />
        </Form.Item>
      </div>

      {!editingRole && (
        <Form.Item name="permission_ids" label="初始权限">
          <Checkbox.Group className="w-full">
            <Spin spinning={permissionsLoading}>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {permissionOptions.map((option) => (
                  <Checkbox key={option.value} value={option.value}>
                    {option.label}
                  </Checkbox>
                ))}
              </div>
            </Spin>
          </Checkbox.Group>
        </Form.Item>
      )}
    </Form>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-3">
        <Space wrap size={8}>
          <Button icon={<ReloadOutlined />} onClick={refresh}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRole(null)
              form.resetFields()
              form.setFieldsValue({ is_active: true, priority: 0, sort_order: 0 })
              setIsCreateModalOpen(true)
              if (permissions.length === 0) fetchPermissions()
            }}
          >
            新增角色
          </Button>
        </Space>
      </div>

      <Spin spinning={statsLoading}>
        <div className="grid grid-cols-2 gap-2 rounded-lg border bg-card p-3 md:grid-cols-5">
          <StatCard value={stats?.total_roles ?? 0} label="总角色数" className="text-blue-600" />
          <StatCard value={stats?.active_roles ?? 0} label="启用角色" className="text-green-600" />
          <StatCard value={stats?.inactive_roles ?? 0} label="停用角色" className="text-gray-600" />
          <StatCard value={stats?.total_permissions ?? 0} label="权限总数" className="text-purple-600" />
          <StatCard value={(stats?.average_users_per_role ?? 0).toFixed(1)} label="平均用户数" className="text-orange-600" />
        </div>
      </Spin>

      <Card size="small">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold">角色列表</div>
            <div className="text-xs text-muted-foreground">共 {pagination.total} 条记录</div>
          </div>
          <Space wrap size={8}>
            <Search
              allowClear
              placeholder="搜索角色名称、代码、描述"
              value={searchText}
              onChange={(event) => {
                setSearchText(event.target.value)
                setPagination((prev) => ({ ...prev, current: 1 }))
              }}
              style={{ width: 280 }}
            />
            <Select
              allowClear
              placeholder="角色类型"
              value={typeFilter}
              onChange={(value) => resetToFirstPage(setTypeFilter, value)}
              style={{ width: 140 }}
              options={[
                { label: '系统角色', value: 'system' },
                { label: '自定义角色', value: 'custom' },
              ]}
            />
            <Select
              allowClear
              placeholder="状态"
              value={statusFilter}
              onChange={(value) => resetToFirstPage(setStatusFilter, value)}
              style={{ width: 120 }}
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
            {selectedRowKeys.length > 0 && (
              <Button danger onClick={handleBatchDelete}>
                批量删除 ({selectedRowKeys.length})
              </Button>
            )}
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={roles}
          loading={loading}
          size="middle"
          rowKey="id"
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
            getCheckboxProps: (record) => ({ disabled: record.is_system_role }),
          }}
          pagination={pagination}
          onChange={(pag: TablePaginationConfig) => {
            setPagination((prev) => ({
              ...prev,
              current: pag.current || 1,
              pageSize: pag.pageSize || 10,
            }))
          }}
        />
      </Card>

      <Modal
        title="新增角色"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={720}
        destroyOnHidden
        forceRender
      >
        {roleForm}
      </Modal>

      <Modal
        title="编辑角色"
        open={Boolean(editingRole)}
        onCancel={() => {
          setEditingRole(null)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={640}
        destroyOnHidden
        forceRender
      >
        {roleForm}
      </Modal>

      <Modal title="角色详情" open={Boolean(viewingRole)} onCancel={() => setViewingRole(null)} footer={<Button onClick={() => setViewingRole(null)}>关闭</Button>} width={760}>
        {viewingRole && (
          <Space direction="vertical" className="w-full" size="large">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="角色名称">{viewingRole.name}</Descriptions.Item>
              <Descriptions.Item label="角色代码">{viewingRole.code}</Descriptions.Item>
              <Descriptions.Item label="角色类型">{viewingRole.is_system_role ? <Tag color="blue">系统角色</Tag> : <Tag color="green">自定义角色</Tag>}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge status={viewingRole.is_active ? 'success' : 'default'} text={viewingRole.is_active ? '启用' : '停用'} />
              </Descriptions.Item>
              <Descriptions.Item label="用户数">{viewingRole.user_count}</Descriptions.Item>
              <Descriptions.Item label="权限数">{viewingRole.permission_count}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDateTime(viewingRole.created_at)}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{formatDateTime(viewingRole.updated_at)}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {viewingRole.description || '-'}
              </Descriptions.Item>
            </Descriptions>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={viewingRole.permissions || []}
              columns={[
                { title: '权限名称', dataIndex: 'name' },
                { title: '权限代码', dataIndex: 'code' },
                { title: '模块', dataIndex: 'module' },
              ]}
            />
          </Space>
        )}
      </Modal>

      <Modal
        title={permissionRole ? `分配权限：${permissionRole.name}` : '分配权限'}
        open={Boolean(permissionRole)}
        onCancel={() => setPermissionRole(null)}
        onOk={saveRolePermissions}
        confirmLoading={savingPermissions}
        width={760}
      >
        <Spin spinning={permissionsLoading}>
          <Checkbox.Group value={selectedPermissionIds} onChange={(values) => setSelectedPermissionIds(values.map(Number))} className="w-full">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {permissionOptions.map((option) => (
                <Checkbox key={option.value} value={option.value}>
                  {option.label}
                </Checkbox>
              ))}
            </div>
          </Checkbox.Group>
        </Spin>
      </Modal>

      <Modal
        title={userRole ? `角色用户：${userRole.name}` : '角色用户'}
        open={Boolean(userRole)}
        onCancel={() => {
          setUserRole(null)
          setRoleUsers([])
        }}
        footer={<Button onClick={() => setUserRole(null)}>关闭</Button>}
        width={820}
      >
        <Table
          size="small"
          rowKey="id"
          loading={usersLoading}
          dataSource={roleUsers}
          columns={[
            { title: '用户名', dataIndex: 'username' },
            { title: '昵称', dataIndex: 'nickname', render: (value) => value || '-' },
            { title: '邮箱', dataIndex: 'email' },
            {
              title: '状态',
              dataIndex: 'is_active',
              render: (active) => <Badge status={active ? 'success' : 'default'} text={active ? '启用' : '停用'} />,
            },
            { title: '最后登录', dataIndex: 'last_login_at', render: formatDateTime },
          ]}
          pagination={false}
        />
      </Modal>
    </div>
  )
}

const StatCard = ({ value, label, className }: { value: React.ReactNode; label: string; className: string }) => (
  <div className="rounded-md border bg-background px-3 py-2">
    <div className={`text-xl font-bold leading-6 ${className}`}>{value}</div>
    <div className="text-xs text-muted-foreground">{label}</div>
  </div>
)

export default Roles
