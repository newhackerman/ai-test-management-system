import React, { useState } from 'react'
import { Card, Tabs, Button, Space, Spin } from 'antd'
import { 
  TeamOutlined, 
  UserAddOutlined, 
  BarChartOutlined,
  MailOutlined 
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { ProjectService } from '@/services/projectService'
import MemberList from './MemberList'
import MemberInvitation from './MemberInvitation'
import WorkloadChart from './WorkloadChart'

interface TeamManagementProps {
  projectId: number
  editable?: boolean
}

export const TeamManagement: React.FC<TeamManagementProps> = ({ 
  projectId, 
  editable = false 
}) => {
  const [invitationVisible, setInvitationVisible] = useState(false)

  // 获取项目成员数据
  const { data: members = [], isLoading } = useQuery({
    queryKey: ['projects', projectId, 'members'],
    queryFn: () => ProjectService.getProjectMembers(projectId),
    enabled: !!projectId
  })

  const tabItems = [
    {
      key: 'members',
      label: (
        <Space>
          <TeamOutlined />
          成员管理
        </Space>
      ),
      children: (
        <MemberList 
          projectId={projectId} 
          editable={editable}
        />
      )
    },
    {
      key: 'workload',
      label: (
        <Space>
          <BarChartOutlined />
          工作负载
        </Space>
      ),
      children: (
        <WorkloadChart 
          members={members} 
          loading={isLoading}
        />
      )
    }
  ]

  if (isLoading) {
    return (
      <Card>
        <div className="flex justify-center items-center h-64">
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>团队协作管理</span>
          </Space>
        }
        extra={
          editable && (
            <Space>
              <Button
                type="primary"
                icon={<MailOutlined />}
                onClick={() => setInvitationVisible(true)}
              >
                邀请成员
              </Button>
            </Space>
          )
        }
      >
        <Tabs
          items={tabItems}
          defaultActiveKey="members"
          size="large"
        />
      </Card>

      {/* 成员邀请模态框 */}
      <MemberInvitation
        projectId={projectId}
        visible={invitationVisible}
        onClose={() => setInvitationVisible(false)}
      />
    </div>
  )
}

export default TeamManagement