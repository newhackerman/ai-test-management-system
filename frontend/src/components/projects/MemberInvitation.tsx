import React, { useState } from 'react'
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Steps,
  Card,
  Space,
  Tag,
  Avatar,
  List,
  message,
  Divider,
  Typography,
  Alert
} from 'antd'
import {
  UserAddOutlined,
  MailOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { ProjectMember } from '@/types/project'
import { ProjectService } from '@/services/projectService'
import { useMutation, useQueryClient } from '@tanstack/react-query'

const { Step } = Steps
const { Text, Title } = Typography

interface MemberInvitationProps {
  projectId: number
  visible: boolean
  onClose: () => void
}

interface InvitationData {
  email: string
  role_in_project: ProjectMember['role_in_project']
  allocation_percentage: number
  responsibilities?: string
  welcome_message?: string
}

interface InvitationResult {
  email: string
  status: 'success' | 'failed' | 'pending'
  message?: string
}

const ROLE_LABELS = {
  ADMIN: '系统管理员',
  PROJECT_MANAGER: '项目经理',
  REQUIREMENT_MANAGER: '需求管理员',
  DESIGNER: '设计人员',
  ARCHITECT: '架构师',
  DEVELOPER: '开发人员',
  TESTER: '测试人员',
  DEVOPS: '运维人员',
  THIRD_PARTY: '第三方人员'
} as const

const ROLE_COLORS = {
  ADMIN: 'red',
  PROJECT_MANAGER: 'purple',
  REQUIREMENT_MANAGER: 'blue',
  DESIGNER: 'cyan',
  ARCHITECT: 'green',
  DEVELOPER: 'orange',
  TESTER: 'gold',
  DEVOPS: 'magenta',
  THIRD_PARTY: 'default'
} as const

export const MemberInvitation: React.FC<MemberInvitationProps> = ({
  projectId,
  visible,
  onClose
}) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [invitations, setInvitations] = useState<InvitationData[]>([])
  const [invitationResults, setInvitationResults] = useState<InvitationResult[]>([])
  const [form] = Form.useForm<InvitationData>()
  const queryClient = useQueryClient()

  // 发送邀请
  const sendInvitationMutation = useMutation({
    mutationFn: async (invitationList: InvitationData[]) => {
      const results: InvitationResult[] = []
      
      for (const invitation of invitationList) {
        try {
          await ProjectService.inviteMemberByEmail(projectId, {
            email: invitation.email,
            role_in_project: invitation.role_in_project,
            allocation_percentage: invitation.allocation_percentage,
            responsibilities: invitation.responsibilities,
            welcome_message: invitation.welcome_message
          })
          
          results.push({
            email: invitation.email,
            status: 'success',
            message: '邀请发送成功'
          })
        } catch (error: any) {
          results.push({
            email: invitation.email,
            status: 'failed',
            message: error.message || '发送失败，请稍后重试'
          })
        }
      }
      
      return results
    },
    onSuccess: (results) => {
      setInvitationResults(results)
      setCurrentStep(2)
      
      const successCount = results.filter(r => r.status === 'success').length
      const failedCount = results.filter(r => r.status === 'failed').length
      
      if (successCount > 0) {
        message.success(`成功发送 ${successCount} 个邀请`)
        queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'members'] })
      }
      
      if (failedCount > 0) {
        message.warning(`${failedCount} 个邀请发送失败`)
      }
    },
    onError: (error: any) => {
      message.error(error.message || '发送邀请失败')
    }
  })

  const handleAddInvitation = () => {
    form.validateFields().then(values => {
      // 检查邮箱是否已存在
      const existingEmails = invitations.map(inv => inv.email)
      if (existingEmails.includes(values.email)) {
        message.warning('该邮箱已在邀请列表中')
        return
      }

      setInvitations(prev => [...prev, values])
      form.resetFields()
      message.success('邀请信息已添加')
    })
  }

  const handleRemoveInvitation = (email: string) => {
    setInvitations(prev => prev.filter(inv => inv.email !== email))
  }

  const handleSendInvitations = () => {
    if (invitations.length === 0) {
      message.warning('请先添加邀请信息')
      return
    }
    
    setCurrentStep(1)
    sendInvitationMutation.mutate(invitations)
  }

  const handleClose = () => {
    setCurrentStep(0)
    setInvitations([])
    setInvitationResults([])
    form.resetFields()
    onClose()
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <Card title="添加邀请信息" size="small">
              <Form
                form={form}
                layout="vertical"
                initialValues={{
                  allocation_percentage: 100
                }}
              >
                <Form.Item
                  name="email"
                  label="邮箱地址"
                  rules={[
                    { required: true, message: '请输入邮箱地址' },
                    { type: 'email', message: '请输入有效的邮箱地址' }
                  ]}
                >
                  <Input
                    prefix={<MailOutlined />}
                    placeholder="请输入要邀请的用户邮箱"
                  />
                </Form.Item>

                <Form.Item
                  name="role_in_project"
                  label="项目角色"
                  rules={[{ required: true, message: '请选择项目角色' }]}
                >
                  <Select placeholder="请选择项目角色">
                    {Object.entries(ROLE_LABELS).map(([value, label]) => (
                      <Select.Option key={value} value={value}>
                        <Tag color={ROLE_COLORS[value as keyof typeof ROLE_COLORS]}>
                          {label}
                        </Tag>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  name="allocation_percentage"
                  label="参与度 (%)"
                  rules={[
                    { required: true, message: '请输入参与度' },
                    { type: 'number', min: 1, max: 200, message: '参与度应在1-200%之间' }
                  ]}
                >
                  <Input
                    type="number"
                    min={1}
                    max={200}
                    suffix="%"
                    placeholder="100"
                  />
                </Form.Item>

                <Form.Item
                  name="responsibilities"
                  label="职责描述"
                >
                  <Input.TextArea
                    rows={2}
                    placeholder="请描述该成员在项目中的具体职责..."
                  />
                </Form.Item>

                <Form.Item
                  name="welcome_message"
                  label="欢迎信息"
                >
                  <Input.TextArea
                    rows={3}
                    placeholder="可选：添加个性化的欢迎信息..."
                  />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    onClick={handleAddInvitation}
                    icon={<UserAddOutlined />}
                    block
                  >
                    添加到邀请列表
                  </Button>
                </Form.Item>
              </Form>
            </Card>

            {invitations.length > 0 && (
              <Card title={`邀请列表 (${invitations.length})`} size="small">
                <List
                  dataSource={invitations}
                  renderItem={(invitation, index) => (
                    <List.Item
                      actions={[
                        <Button
                          type="text"
                          danger
                          size="small"
                          onClick={() => handleRemoveInvitation(invitation.email)}
                        >
                          移除
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<Avatar icon={<MailOutlined />} />}
                        title={invitation.email}
                        description={
                          <Space>
                            <Tag color={ROLE_COLORS[invitation.role_in_project]}>
                              {ROLE_LABELS[invitation.role_in_project]}
                            </Tag>
                            <Text type="secondary">
                              参与度: {invitation.allocation_percentage}%
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </div>
        )

      case 1:
        return (
          <div className="text-center py-8">
            <div className="mb-4">
              <ClockCircleOutlined className="text-4xl text-blue-500" />
            </div>
            <Title level={4}>正在发送邀请...</Title>
            <Text type="secondary">
              正在向 {invitations.length} 个邮箱发送邀请，请稍候...
            </Text>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <CheckCircleOutlined className="text-4xl text-green-500 mb-2" />
              <Title level={4}>邀请发送完成</Title>
            </div>

            <Alert
              message="邀请结果"
              description={
                <div>
                  <Text>
                    成功: {invitationResults.filter(r => r.status === 'success').length} 个，
                    失败: {invitationResults.filter(r => r.status === 'failed').length} 个
                  </Text>
                </div>
              }
              type="info"
              showIcon
            />

            <List
              dataSource={invitationResults}
              renderItem={(result) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={
                          result.status === 'success' ? 
                            <CheckCircleOutlined /> : 
                            <ExclamationCircleOutlined />
                        }
                        style={{
                          backgroundColor: result.status === 'success' ? '#52c41a' : '#ff4d4f'
                        }}
                      />
                    }
                    title={result.email}
                    description={
                      <Text type={result.status === 'success' ? 'success' : 'danger'}>
                        {result.message}
                      </Text>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <Modal
      title="邀请团队成员"
      open={visible}
      onCancel={handleClose}
      width={600}
      footer={
        currentStep === 0 ? [
          <Button key="cancel" onClick={handleClose}>
            取消
          </Button>,
          <Button
            key="send"
            type="primary"
            onClick={handleSendInvitations}
            disabled={invitations.length === 0}
            loading={sendInvitationMutation.isPending}
          >
            发送邀请 ({invitations.length})
          </Button>
        ] : currentStep === 2 ? [
          <Button key="close" type="primary" onClick={handleClose}>
            完成
          </Button>
        ] : null
      }
    >
      <div className="mb-6">
        <Steps current={currentStep} size="small">
          <Step title="添加邀请" icon={<UserAddOutlined />} />
          <Step title="发送邀请" icon={<MailOutlined />} />
          <Step title="完成" icon={<CheckCircleOutlined />} />
        </Steps>
      </div>

      <Divider />

      {renderStepContent()}
    </Modal>
  )
}

export default MemberInvitation