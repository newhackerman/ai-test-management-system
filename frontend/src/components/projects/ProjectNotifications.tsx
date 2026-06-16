// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react';
import {
  Avatar,
  Badge,
  Button,
  Card,
  Divider,
  Dropdown,
  Empty,
  Form,
  List,
  Modal,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  AlertOutlined,
  BellOutlined,
  CalendarOutlined,
  CheckOutlined,
  DeleteOutlined,
  FileTextOutlined,
  FilterOutlined,
  MessageOutlined,
  MoreOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ProjectService } from '@/services/projectService';
import type { User } from '@/types';

const { Text, Title } = Typography;

interface Notification {
  id: number;
  project_id: number;
  user_id: number;
  type: 'message' | 'task' | 'document' | 'milestone' | 'member' | 'system';
  title: string;
  content: string;
  data?: any;
  is_read: boolean;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  created_at: string;
  sender?: User;
}

interface NotificationSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  message_notifications: boolean;
  task_notifications: boolean;
  document_notifications: boolean;
  milestone_notifications: boolean;
  member_notifications: boolean;
}

interface ProjectNotificationsProps {
  projectId: number;
  currentUser: User;
}

const defaultSettings: NotificationSettings = {
  email_notifications: true,
  push_notifications: true,
  message_notifications: true,
  task_notifications: true,
  document_notifications: true,
  milestone_notifications: true,
  member_notifications: true,
};

const normalizeNotifications = (response: any): Notification[] => {
  const data = response?.data || response?.items || response?.notifications || response || [];
  return Array.isArray(data) ? data : [];
};

const formatDateTime = (value?: string) => {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  });
};

export const ProjectNotifications: React.FC<ProjectNotificationsProps> = ({ projectId, currentUser }) => {
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [settingsForm] = Form.useForm<NotificationSettings>();
  const queryClient = useQueryClient();

  const notificationQueryKey = ['projects', projectId, 'notifications'];
  const settingsQueryKey = ['projects', projectId, currentUser.id, 'notification-settings'];

  const { data: rawNotifications, isLoading } = useQuery({
    queryKey: notificationQueryKey,
    queryFn: () => ProjectService.getProjectNotifications(projectId),
    enabled: Boolean(projectId),
    refetchInterval: 30000,
  });

  const { data: settings = defaultSettings } = useQuery({
    queryKey: settingsQueryKey,
    queryFn: async () => {
      try {
        const response = await ProjectService.getProjectNotificationSettings(projectId);
        return { ...defaultSettings, ...(response?.data || response || {}) };
      } catch {
        return defaultSettings;
      }
    },
    enabled: Boolean(projectId),
  });

  useEffect(() => {
    if (settingsVisible) {
      settingsForm.setFieldsValue(settings);
    }
  }, [settings, settingsForm, settingsVisible]);

  const notifications = useMemo(() => normalizeNotifications(rawNotifications), [rawNotifications]);

  const markAsReadMutation = useMutation({
    mutationFn: (notificationIds: number[]) => ProjectService.markNotificationAsRead(projectId, notificationIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationQueryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '标记已读失败');
    },
  });

  const deleteNotificationMutation = useMutation({
    mutationFn: (notificationId: number) => ProjectService.deleteProjectNotification(projectId, notificationId),
    onSuccess: () => {
      message.success('通知删除成功');
      queryClient.invalidateQueries({ queryKey: notificationQueryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '通知删除失败');
    },
  });

  const updateSettingsMutation = useMutation({
    mutationFn: (values: NotificationSettings) => ProjectService.updateProjectNotificationSettings(projectId, values),
    onSuccess: () => {
      message.success('通知设置已保存');
      setSettingsVisible(false);
      queryClient.invalidateQueries({ queryKey: settingsQueryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '通知设置保存失败');
    },
  });

  const filteredNotifications = notifications.filter((notification) => {
    if (filterType === 'all') return true;
    if (filterType === 'unread') return !notification.is_read;
    return notification.type === filterType;
  });

  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  const handleMarkAllAsRead = () => {
    const unreadIds = notifications.filter((notification) => !notification.is_read).map((notification) => notification.id);
    if (unreadIds.length > 0) {
      markAsReadMutation.mutate(unreadIds);
    }
  };

  const handleDeleteNotification = (notificationId: number) => {
    Modal.confirm({
      title: '确认删除通知',
      content: '删除后无法恢复，确定要删除这条通知吗？',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => deleteNotificationMutation.mutate(notificationId),
    });
  };

  const handleUpdateSettings = async () => {
    const values = await settingsForm.validateFields();
    updateSettingsMutation.mutate(values);
  };

  const getNotificationIcon = (type: Notification['type']) => {
    const icons = {
      message: <MessageOutlined style={{ color: '#1890ff' }} />,
      task: <FileTextOutlined style={{ color: '#52c41a' }} />,
      document: <FileTextOutlined style={{ color: '#faad14' }} />,
      milestone: <CalendarOutlined style={{ color: '#722ed1' }} />,
      member: <TeamOutlined style={{ color: '#13c2c2' }} />,
      system: <AlertOutlined style={{ color: '#ff4d4f' }} />,
    };
    return icons[type] || icons.system;
  };

  const getNotificationTypeText = (type: Notification['type']) => {
    const texts = {
      message: '消息',
      task: '任务',
      document: '文档',
      milestone: '里程碑',
      member: '成员',
      system: '系统',
    };
    return texts[type] || '系统';
  };

  const getPriorityColor = (priority: Notification['priority']) => {
    const colors = {
      low: 'default',
      medium: 'processing',
      high: 'warning',
      urgent: 'error',
    };
    return colors[priority] || 'default';
  };

  const getPriorityText = (priority: Notification['priority']) => {
    const texts = {
      low: '低',
      medium: '中',
      high: '高',
      urgent: '紧急',
    };
    return texts[priority] || '中';
  };

  return (
    <div className="space-y-6">
      <Card
        title={
          <Space>
            <Badge count={unreadCount} size="small">
              <BellOutlined />
            </Badge>
            <span>项目通知</span>
          </Space>
        }
        extra={
          <Space>
            <Dropdown
              menu={{
                items: [
                  { key: 'all', label: '全部通知' },
                  { key: 'unread', label: '未读通知' },
                  { key: 'message', label: '消息通知' },
                  { key: 'task', label: '任务通知' },
                  { key: 'document', label: '文档通知' },
                  { key: 'milestone', label: '里程碑通知' },
                  { key: 'member', label: '成员通知' },
                  { key: 'system', label: '系统通知' },
                ],
                onClick: ({ key }) => setFilterType(key),
              }}
              trigger={['click']}
            >
              <Button icon={<FilterOutlined />} size="small">
                筛选
              </Button>
            </Dropdown>

            {unreadCount > 0 && (
              <Button type="link" size="small" onClick={handleMarkAllAsRead} loading={markAsReadMutation.isPending}>
                全部已读
              </Button>
            )}

            <Button icon={<SettingOutlined />} size="small" onClick={() => setSettingsVisible(true)}>
              设置
            </Button>
          </Space>
        }
      >
        <List
          dataSource={filteredNotifications}
          loading={isLoading}
          renderItem={(notification) => (
            <List.Item
              className={`${!notification.is_read ? 'bg-blue-50' : ''} transition-colors hover:bg-gray-50 dark:bg-gray-800/50`}
              actions={[
                <Dropdown
                  key="actions"
                  menu={{
                    items: [
                      ...(!notification.is_read
                        ? [
                            {
                              key: 'read',
                              label: '标记已读',
                              icon: <CheckOutlined />,
                              onClick: () => markAsReadMutation.mutate([notification.id]),
                            },
                          ]
                        : []),
                      {
                        key: 'delete',
                        label: '删除',
                        icon: <DeleteOutlined />,
                        danger: true,
                        onClick: () => handleDeleteNotification(notification.id),
                      },
                    ],
                  }}
                  trigger={['click']}
                >
                  <Button type="text" size="small" icon={<MoreOutlined />} />
                </Dropdown>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  <Badge dot={!notification.is_read}>
                    <Avatar src={notification.sender?.avatar} icon={notification.sender ? <UserOutlined /> : getNotificationIcon(notification.type)} size="small" />
                  </Badge>
                }
                title={
                  <div className="flex items-center justify-between gap-3">
                    <Space wrap>
                      <span className={!notification.is_read ? 'font-semibold' : ''}>{notification.title}</span>
                      <Tag color={getPriorityColor(notification.priority)}>{getPriorityText(notification.priority)}</Tag>
                    </Space>
                    <Text type="secondary" className="shrink-0 text-xs">
                      {formatDateTime(notification.created_at)}
                    </Text>
                  </div>
                }
                description={
                  <div className="space-y-1">
                    <div>{notification.content}</div>
                    <Space size="small" wrap>
                      <Tag>{getNotificationTypeText(notification.type)}</Tag>
                      {notification.sender && (
                        <Text type="secondary" className="text-xs">
                          来自：{notification.sender.real_name || notification.sender.realName || notification.sender.username}
                        </Text>
                      )}
                    </Space>
                  </div>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: <Empty description="暂无通知" /> }}
          pagination={{
            pageSize: 10,
            showSizeChanger: false,
            showQuickJumper: false,
            simple: true,
          }}
        />
      </Card>

      <Modal
        title="通知设置"
        open={settingsVisible}
        onOk={handleUpdateSettings}
        onCancel={() => setSettingsVisible(false)}
        okText="保存"
        cancelText="取消"
        confirmLoading={updateSettingsMutation.isPending}
      >
        <Form form={settingsForm} layout="vertical" initialValues={settings}>
          <Title level={5}>通知方式</Title>
          <Form.Item name="email_notifications" label="邮件通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="push_notifications" label="站内推送" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Divider />

          <Title level={5}>通知类型</Title>
          <Form.Item name="message_notifications" label="消息通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="task_notifications" label="任务通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="document_notifications" label="文档通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="milestone_notifications" label="里程碑通知" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="member_notifications" label="成员通知" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectNotifications;
