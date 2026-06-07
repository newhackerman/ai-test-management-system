import React, { useState } from 'react'
import { Card, Tabs, Badge, Space } from 'antd'
import {
  MessageOutlined,
  FolderOutlined,
  BellOutlined,
  TeamOutlined
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { ProjectService } from '@/services/projectService'
import ProjectDiscussion from './ProjectDiscussion'
import DocumentSharing from './DocumentSharing'
import ProjectNotifications from './ProjectNotifications'
import type { User } from '@/types'

interface ProjectCollaborationProps {
  projectId: number
  currentUser: User
  editable?: boolean
}

export const ProjectCollaboration: React.FC<ProjectCollaborationProps> = ({
  projectId,
  currentUser,
  editable = false
}) => {
  // 获取未读通知数量
  const { data: unreadCount = 0 } = useQuery({
    queryKey: ['projects', projectId, 'unread-notifications'],
    queryFn: () => ProjectService.getUnreadNotificationCount(projectId),
    enabled: !!projectId,
    refetchInterval: 30000 // 30秒刷新一次
  })

  // 获取未读消息数量
  const { data: unreadMessages = 0 } = useQuery({
    queryKey: ['projects', projectId, 'unread-messages'],
    queryFn: () => ProjectService.getUnreadMessageCount(projectId),
    enabled: !!projectId,
    refetchInterval: 15000 // 15秒刷新一次
  })

  const tabItems = [
    {
      key: 'discussion',
      label: (
        <Space>
          <Badge count={unreadMessages} size="small">
            <MessageOutlined />
          </Badge>
          <span>项目讨论</span>
        </Space>
      ),
      children: (
        <ProjectDiscussion
          projectId={projectId}
          currentUser={currentUser}
        />
      )
    },
    {
      key: 'documents',
      label: (
        <Space>
          <FolderOutlined />
          <span>文档共享</span>
        </Space>
      ),
      children: (
        <DocumentSharing
          projectId={projectId}
        />
      )
    },
    {
      key: 'notifications',
      label: (
        <Space>
          <Badge count={unreadCount} size="small">
            <BellOutlined />
          </Badge>
          <span>通知中心</span>
        </Space>
      ),
      children: (
        <ProjectNotifications
          projectId={projectId}
          currentUser={currentUser}
        />
      )
    }
  ]

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>沟通协作</span>
        </Space>
      }
      className="h-full"
      bodyStyle={{ height: 'calc(100% - 57px)' }}
    >
      <Tabs
        items={tabItems}
        defaultActiveKey="discussion"
        size="large"
        className="h-full"
        tabBarStyle={{ marginBottom: 16 }}
      />
    </Card>
  )
}

export default ProjectCollaboration
