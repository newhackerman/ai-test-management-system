// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Avatar,
  Button,
  Card,
  Dropdown,
  Input,
  List,
  Modal,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  LinkOutlined,
  MoreOutlined,
  PaperClipOutlined,
  PictureOutlined,
  PushpinOutlined,
  ReplyArrowOutlined,
  SendOutlined,
  SmileOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ProjectService } from '@/services/projectService';
import type { User } from '@/types';

const { TextArea } = Input;
const { Paragraph, Text } = Typography;

interface DiscussionMessage {
  id: number;
  project_id: number;
  user_id: number;
  content: string;
  message_type: 'text' | 'file' | 'image' | 'link';
  reply_to_id?: number;
  is_pinned: boolean;
  attachments?: Array<{
    id: number;
    filename: string;
    file_size: number;
    file_type: string;
    download_url: string;
  }>;
  mentions?: number[];
  created_at: string;
  updated_at: string;
  user?: User;
  reply_to?: DiscussionMessage;
  replies?: DiscussionMessage[];
}

interface ProjectDiscussionProps {
  projectId: number;
  currentUser: User;
}

const normalizeMessages = (response: any): DiscussionMessage[] => {
  const data = response?.data || response?.items || response?.messages || response || [];
  return Array.isArray(data) ? data : [];
};

const formatDateTime = (value?: string) => {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  });
};

const getUserName = (user?: User) => user?.real_name || user?.realName || user?.username || '未知用户';

export const ProjectDiscussion: React.FC<ProjectDiscussionProps> = ({ projectId, currentUser }) => {
  const [messageContent, setMessageContent] = useState('');
  const [replyingTo, setReplyingTo] = useState<DiscussionMessage | null>(null);
  const [editingMessage, setEditingMessage] = useState<DiscussionMessage | null>(null);
  const [editContent, setEditContent] = useState('');
  const [fileList, setFileList] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const queryKey = ['projects', projectId, 'messages'];

  const { data: rawMessages, isLoading } = useQuery({
    queryKey,
    queryFn: () => ProjectService.getProjectMessages(projectId),
    enabled: Boolean(projectId),
    refetchInterval: 30000,
  });

  const messages = useMemo(() => normalizeMessages(rawMessages), [rawMessages]);

  const sendMessageMutation = useMutation({
    mutationFn: (data: { content: string; reply_to_id?: number; attachments?: any[] }) =>
      ProjectService.sendProjectMessage(projectId, {
        content: data.content,
        message_type: data.attachments?.length ? 'file' : 'text',
        reply_to_id: data.reply_to_id,
        attachments: data.attachments,
      }),
    onSuccess: () => {
      message.success('消息发送成功');
      setMessageContent('');
      setReplyingTo(null);
      setFileList([]);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '消息发送失败');
    },
  });

  const editMessageMutation = useMutation({
    mutationFn: (data: { messageId: number; content: string }) =>
      ProjectService.updateProjectMessage(projectId, data.messageId, { content: data.content }),
    onSuccess: () => {
      message.success('消息编辑成功');
      setEditingMessage(null);
      setEditContent('');
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '消息编辑失败');
    },
  });

  const deleteMessageMutation = useMutation({
    mutationFn: (messageId: number) => ProjectService.deleteProjectMessage(projectId, messageId),
    onSuccess: () => {
      message.success('消息删除成功');
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '删除消息失败');
    },
  });

  const pinMessageMutation = useMutation({
    mutationFn: (messageId: number) => ProjectService.toggleMessagePin(projectId, messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: any) => {
      message.error(error?.message || '置顶操作失败');
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = () => {
    if (!messageContent.trim() && fileList.length === 0) {
      message.warning('请输入消息内容或选择附件');
      return;
    }

    sendMessageMutation.mutate({
      content: messageContent.trim(),
      reply_to_id: replyingTo?.id,
      attachments: fileList.map((file) => ({
        filename: file.name,
        file_size: file.size,
        file_type: file.type,
      })),
    });
  };

  const handleEditMessage = (msg: DiscussionMessage) => {
    setEditingMessage(msg);
    setEditContent(msg.content);
  };

  const handleDeleteMessage = (msg: DiscussionMessage) => {
    Modal.confirm({
      title: '确认删除消息',
      content: '删除后无法恢复，确定要删除这条消息吗？',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => deleteMessageMutation.mutate(msg.id),
    });
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return '0 Bytes';
    const units = ['Bytes', 'KB', 'MB', 'GB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, index)).toFixed(2)} ${units[index]}`;
  };

  const getFileIcon = (fileType = '') => {
    if (fileType.startsWith('image/')) return <PictureOutlined />;
    if (fileType.includes('document') || fileType.includes('pdf')) return <FileTextOutlined />;
    return <PaperClipOutlined />;
  };

  const renderMessage = (msg: DiscussionMessage) => {
    const isOwn = Number(msg.user_id) === Number(currentUser.id);
    const canEdit = isOwn && Date.now() - new Date(msg.created_at).getTime() < 300000;

    return (
      <List.Item key={msg.id} className={msg.is_pinned ? 'border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}>
        <div className="w-full">
          <div className="flex items-start space-x-3">
            <Avatar src={msg.user?.avatar} size="small">
              {getUserName(msg.user)[0]}
            </Avatar>

            <div className="min-w-0 flex-1">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <Text strong>{getUserName(msg.user)}</Text>
                <Text type="secondary" className="text-xs">
                  {formatDateTime(msg.created_at)}
                </Text>
                {msg.is_pinned && (
                  <Tag color="blue" icon={<PushpinOutlined />}>
                    置顶
                  </Tag>
                )}
                {msg.updated_at && msg.updated_at !== msg.created_at && (
                  <Text type="secondary" className="text-xs">
                    （已编辑）
                  </Text>
                )}
              </div>

              {msg.reply_to && (
                <div className="mb-2 rounded bg-gray-100 p-2 text-sm dark:bg-gray-800">
                  <Text type="secondary">
                    回复 {getUserName(msg.reply_to.user)}：{msg.reply_to.content}
                  </Text>
                </div>
              )}

              <Paragraph className="mb-2 whitespace-pre-wrap">{msg.content}</Paragraph>

              {msg.attachments?.length > 0 && (
                <div className="mb-2 space-y-2">
                  {msg.attachments.map((attachment) => (
                    <button
                      key={attachment.id}
                      type="button"
                      className="flex w-full items-center space-x-2 rounded bg-gray-50 p-2 text-left hover:bg-gray-100 dark:bg-gray-800/50"
                      onClick={() => window.open(attachment.download_url, '_blank')}
                    >
                      {getFileIcon(attachment.file_type)}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{attachment.filename}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(attachment.file_size)}</span>
                      </span>
                      <LinkOutlined className="text-blue-500 dark:text-blue-400" />
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-center space-x-2">
                <Button type="text" size="small" icon={<ReplyArrowOutlined />} onClick={() => setReplyingTo(msg)}>
                  回复
                </Button>

                <Dropdown
                  menu={{
                    items: [
                      ...(canEdit
                        ? [
                            {
                              key: 'edit',
                              label: '编辑',
                              icon: <EditOutlined />,
                              onClick: () => handleEditMessage(msg),
                            },
                          ]
                        : []),
                      {
                        key: 'pin',
                        label: msg.is_pinned ? '取消置顶' : '置顶',
                        icon: <PushpinOutlined />,
                        onClick: () => pinMessageMutation.mutate(msg.id),
                      },
                      ...(isOwn
                        ? [
                            {
                              key: 'delete',
                              label: '删除',
                              icon: <DeleteOutlined />,
                              danger: true,
                              onClick: () => handleDeleteMessage(msg),
                            },
                          ]
                        : []),
                    ],
                  }}
                  trigger={['click']}
                >
                  <Button type="text" size="small" icon={<MoreOutlined />} />
                </Dropdown>
              </div>
            </div>
          </div>
        </div>
      </List.Item>
    );
  };

  return (
    <Card
      title="项目讨论"
      className="flex h-full flex-col"
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
    >
      <div className="mb-4 flex-1 overflow-y-auto" style={{ maxHeight: 500 }}>
        <List
          dataSource={messages}
          renderItem={renderMessage}
          loading={isLoading}
          locale={{ emptyText: '暂无讨论消息' }}
        />
        <div ref={messagesEndRef} />
      </div>

      {replyingTo && (
        <div className="mb-3 flex items-center justify-between rounded bg-blue-50 p-3 dark:bg-blue-900/20">
          <Text type="secondary">
            回复 {getUserName(replyingTo.user)}：{replyingTo.content.slice(0, 50)}
            {replyingTo.content.length > 50 ? '...' : ''}
          </Text>
          <Button type="text" size="small" onClick={() => setReplyingTo(null)}>
            取消
          </Button>
        </div>
      )}

      <div className="border-t pt-4">
        <TextArea
          value={messageContent}
          onChange={(event) => setMessageContent(event.target.value)}
          placeholder={replyingTo ? `回复 ${getUserName(replyingTo.user)}...` : '输入消息...'}
          autoSize={{ minRows: 2, maxRows: 4 }}
          onPressEnter={(event) => {
            if (event.ctrlKey || event.metaKey) {
              event.preventDefault();
              handleSendMessage();
            }
          }}
        />

        <div className="mt-2 flex items-center justify-between">
          <Space>
            <Upload fileList={fileList} onChange={({ fileList: nextFileList }) => setFileList(nextFileList)} beforeUpload={() => false} multiple>
              <Button type="text" icon={<PaperClipOutlined />} size="small">
                附件
              </Button>
            </Upload>
            <Button type="text" icon={<SmileOutlined />} size="small" disabled>
              表情
            </Button>
          </Space>

          <Space>
            <Text type="secondary" className="text-xs">
              Ctrl+Enter 发送
            </Text>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={sendMessageMutation.isPending}
              disabled={!messageContent.trim() && fileList.length === 0}
            >
              发送
            </Button>
          </Space>
        </div>
      </div>

      <Modal
        title="编辑消息"
        open={Boolean(editingMessage)}
        onOk={() => {
          if (!editingMessage || !editContent.trim()) return;
          editMessageMutation.mutate({ messageId: editingMessage.id, content: editContent.trim() });
        }}
        onCancel={() => {
          setEditingMessage(null);
          setEditContent('');
        }}
        okText="保存"
        cancelText="取消"
        confirmLoading={editMessageMutation.isPending}
      >
        <TextArea
          value={editContent}
          onChange={(event) => setEditContent(event.target.value)}
          placeholder="编辑消息内容..."
          autoSize={{ minRows: 3, maxRows: 6 }}
        />
      </Modal>
    </Card>
  );
};

export default ProjectDiscussion;
