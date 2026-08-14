import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CodeOutlined,
  CrownOutlined,
  DeleteOutlined,
  DeploymentUnitOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '../services/api/client';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;
const { Option } = Select;

interface Role {
  id: number;
  code: string;
  name: string;
  description: string;
  is_system_role: boolean;
  is_active: boolean;
  priority: number;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
  user_count?: number;
}

interface RoleStats {
  total_roles: number;
  system_roles: number;
  active_roles: number;
  total_users: number;
}

const normalizeRole = (role: any): Role => ({
  id: role.id,
  code: role.code || '',
  name: role.name || role.code || '',
  description: role.description || '',
  is_system_role: Boolean(role.is_system_role),
  is_active: Boolean(role.is_active),
  priority: role.priority ?? role.sort_order ?? role.sort ?? 0,
  sort_order: role.sort_order ?? role.sort ?? role.priority ?? 0,
  created_at: role.created_at,
  updated_at: role.updated_at,
  user_count: role.user_count ?? 0,
});

const formatDate = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
};

const EightRoleManagement: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<RoleStats | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const getRoleIcon = (roleCode: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      SUPER_ADMIN: <CrownOutlined style={{ color: '#f50' }} />,
      SYSTEM_ADMIN: <SafetyOutlined style={{ color: '#f59e0b' }} />,
      CONFIG_ADMIN: <SettingOutlined style={{ color: '#7c3aed' }} />,
      PROJECT_MANAGER: <TeamOutlined style={{ color: '#2563eb' }} />,
      DEVELOPER: <CodeOutlined style={{ color: '#16a34a' }} />,
      TESTER: <ExperimentOutlined style={{ color: '#13c2c2' }} />,
      DEVOPS: <DeploymentUnitOutlined style={{ color: '#eb2f96' }} />,
      READONLY_USER: <EyeOutlined style={{ color: '#8c8c8c' }} />,
      admin: <SafetyOutlined style={{ color: '#f59e0b' }} />,
      user: <UserOutlined style={{ color: '#8c8c8c' }} />,
    };
    return iconMap[roleCode] || <UserOutlined />;
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 100) return 'red';
    if (priority >= 80) return 'orange';
    if (priority >= 60) return 'blue';
    if (priority >= 40) return 'green';
    return 'default';
  };

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/roles/system');
      const data = response.data;
      const roleList = (data.roles || data.data || []).map(normalizeRole);
      setRoles(roleList);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      message.error('获取角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchRoleStats = async () => {
    try {
      const response = await apiClient.get('/roles/stats');
      const data = response.data?.data || response.data;
      setStats({
        total_roles: data.total_roles ?? 0,
        system_roles: data.system_roles ?? 0,
        active_roles: data.active_roles ?? 0,
        total_users: data.total_users ?? 0,
      });
    } catch (error) {
      console.error('Failed to fetch role stats:', error);
    }
  };

  useEffect(() => {
    fetchRoles();
    fetchRoleStats();
  }, []);

  const filteredRoles = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    return roles.filter((role) => {
      const matchesSearch =
        !keyword ||
        role.name.toLowerCase().includes(keyword) ||
        role.code.toLowerCase().includes(keyword) ||
        role.description.toLowerCase().includes(keyword);
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && role.is_active) ||
        (statusFilter === 'inactive' && !role.is_active);
      return matchesSearch && matchesStatus;
    });
  }, [roles, searchTerm, statusFilter]);

  const derivedStats: RoleStats = {
    total_roles: stats?.total_roles || roles.length,
    system_roles: stats?.system_roles || roles.filter((role) => role.is_system_role).length,
    active_roles: stats?.active_roles || roles.filter((role) => role.is_active).length,
    total_users: stats?.total_users || roles.reduce((total, role) => total + (role.user_count || 0), 0),
  };

  const handleViewDetail = (role: Role) => {
    setSelectedRole(role);
    setDetailModalVisible(true);
  };

  const handleEditRole = () => {
    message.info('编辑角色功能暂未开放');
  };

  const handleAddRole = () => {
    message.info('添加角色功能暂未开放');
  };

  const handleDeleteRole = async (roleId: number) => {
    try {
      await apiClient.delete(`/roles/${roleId}`);
      message.success('角色删除成功');
      fetchRoles();
      fetchRoleStats();
    } catch (error) {
      console.error('Failed to delete role:', error);
      message.error('删除角色失败');
    }
  };

  const columns: ColumnsType<Role> = [
    {
      title: '角色信息',
      key: 'roleInfo',
      width: 300,
      render: (_, record) => (
        <div className="flex items-center space-x-3">
          <div className="text-2xl">{getRoleIcon(record.code)}</div>
          <div>
            <div className="font-medium text-gray-900 dark:text-gray-100">{record.name}</div>
            <div className="text-sm text-gray-500 font-mono dark:text-gray-400">{record.code}</div>
          </div>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: { showTitle: false },
      render: (description: string) => (
        <Tooltip title={description || '-'}>
          <Text ellipsis style={{ width: 220 }}>{description || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      sorter: (a, b) => a.priority - b.priority,
      render: (priority: number) => <Tag color={getPriorityColor(priority)}>{priority}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>{isActive ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'is_system_role',
      key: 'is_system_role',
      width: 120,
      render: (isSystemRole: boolean) => (
        <Tag color={isSystemRole ? 'blue' : 'green'}>
          {isSystemRole ? '系统角色' : '自定义角色'}
        </Tag>
      ),
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 90,
      render: (count: number) => <span className="text-blue-600 font-medium dark:text-blue-400">{count || 0}</span>,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看详情">
            <Button type="text" icon={<InfoCircleOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          <Tooltip title="编辑角色">
            <Button type="text" icon={<EditOutlined />} onClick={handleEditRole} />
          </Tooltip>
          {!record.is_system_role && (
            <Popconfirm
              title="确定删除此角色吗？"
              onConfirm={() => handleDeleteRole(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除角色">
                <Button type="text" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="mb-2">8种用户角色管理</Title>
          <Paragraph type="secondary">
            管理系统中的系统预置角色和自定义角色。
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchRoles(); fetchRoleStats(); }}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRole}>
            添加角色
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="总角色数" value={derivedStats.total_roles} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="系统角色" value={derivedStats.system_roles} prefix={<SafetyOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="启用角色" value={derivedStats.active_roles} prefix={<SettingOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总用户数" value={derivedStats.total_users} prefix={<UserOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Search
              placeholder="搜索角色名称、代码或描述"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              style={{ width: '100%' }}
              value={statusFilter}
              onChange={setStatusFilter}
              placeholder="筛选状态"
            >
              <Option value="all">全部状态</Option>
              <Option value="active">启用</Option>
              <Option value="inactive">禁用</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Button onClick={() => { setSearchTerm(''); setStatusFilter('all'); }}>
              重置
            </Button>
          </Col>
        </Row>
      </Card>

      <Card title={`角色列表 (${filteredRoles.length})`}>
        <Table
          columns={columns}
          dataSource={filteredRoles}
          rowKey="id"
          loading={loading}
          pagination={{
            total: filteredRoles.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={
          <div className="flex items-center space-x-2">
            {selectedRole && getRoleIcon(selectedRole.code)}
            <span>角色详情</span>
          </div>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={620}
      >
        {selectedRole && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="角色名称" span={2}>{selectedRole.name}</Descriptions.Item>
            <Descriptions.Item label="角色代码" span={2}>
              <Text code>{selectedRole.code}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="角色描述" span={2}>{selectedRole.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={getPriorityColor(selectedRole.priority)}>{selectedRole.priority}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="排序">{selectedRole.sort_order}</Descriptions.Item>
            <Descriptions.Item label="角色类型">
              <Tag color={selectedRole.is_system_role ? 'blue' : 'green'}>
                {selectedRole.is_system_role ? '系统角色' : '自定义角色'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedRole.is_active ? 'success' : 'default'}>
                {selectedRole.is_active ? '启用' : '禁用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>{formatDate(selectedRole.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间" span={2}>{formatDate(selectedRole.updated_at)}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default EightRoleManagement;
