import { AlertOutlined, CheckCircleOutlined, ClockCircleOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons'
import { Avatar, Card, Col, Empty, Progress, Row, Space, Statistic, Tag, Tooltip } from 'antd'
import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from 'recharts'

import type { ProjectMember } from '@/types/project'

interface WorkloadChartProps {
  members: ProjectMember[]
  loading?: boolean
}

interface WorkloadData {
  member: ProjectMember
  workload: number
  efficiency: number
  status: 'normal' | 'overloaded' | 'underloaded'
}

const ROLE_COLORS = {
  ADMIN: '#ff4d4f',
  PROJECT_MANAGER: '#722ed1',
  REQUIREMENT_MANAGER: '#1890ff',
  DESIGNER: '#13c2c2',
  ARCHITECT: '#52c41a',
  DEVELOPER: '#fa8c16',
  TESTER: '#fadb14',
  DEVOPS: '#eb2f96',
  THIRD_PARTY: '#d9d9d9',
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

const getUserName = (user?: any) => user?.real_name || user?.full_name || user?.nickname || user?.username || '未命名用户'

const getEfficiency = (workload: number) => {
  if (workload > 120) return Math.max(55, 100 - (workload - 100) * 0.7)
  if (workload < 60) return Math.max(60, workload + 20)
  return Math.min(100, 88 + (100 - Math.abs(90 - workload)) * 0.08)
}

export const WorkloadChart: React.FC<WorkloadChartProps> = ({ members, loading = false }) => {
  const workloadData = useMemo<WorkloadData[]>(() => {
    return members.map((member) => {
      const workload = Number(member.allocation_percentage || 0)
      const efficiency = getEfficiency(workload)
      const status = workload > 120 ? 'overloaded' : workload < 60 ? 'underloaded' : 'normal'

      return { member, workload, efficiency, status }
    })
  }, [members])

  const statistics = useMemo(() => {
    const totalMembers = workloadData.length
    const overloadedMembers = workloadData.filter((item) => item.status === 'overloaded').length
    const underloadedMembers = workloadData.filter((item) => item.status === 'underloaded').length
    const normalMembers = totalMembers - overloadedMembers - underloadedMembers
    const avgWorkload = totalMembers ? workloadData.reduce((sum, item) => sum + item.workload, 0) / totalMembers : 0
    const avgEfficiency = totalMembers ? workloadData.reduce((sum, item) => sum + item.efficiency, 0) / totalMembers : 0

    return { totalMembers, overloadedMembers, underloadedMembers, normalMembers, avgWorkload, avgEfficiency }
  }, [workloadData])

  const chartData = workloadData.map((item) => ({
    name: getUserName(item.member.user),
    workload: item.workload,
    efficiency: Number(item.efficiency.toFixed(1)),
    role: item.member.role_in_project,
  }))

  const pieData = [
    { name: '正常负载', value: statistics.normalMembers, color: '#52c41a' },
    { name: '负载过重', value: statistics.overloadedMembers, color: '#ff4d4f' },
    { name: '负载不足', value: statistics.underloadedMembers, color: '#faad14' },
  ].filter((item) => item.value > 0)

  const getWorkloadStatus = (workload: number) => {
    if (workload > 120) return { color: 'red', text: '过载', icon: <AlertOutlined /> }
    if (workload < 60) return { color: 'orange', text: '不足', icon: <ClockCircleOutlined /> }
    return { color: 'green', text: '正常', icon: <CheckCircleOutlined /> }
  }

  if (loading) {
    return (
      <Card title="工作负载分析" loading>
        <div style={{ height: 400 }} />
      </Card>
    )
  }

  if (members.length === 0) {
    return (
      <Card title="工作负载分析">
        <Empty description="暂无团队成员数据" />
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card title={<Space><TeamOutlined />工作负载概览</Space>}>
        <Row gutter={[16, 16]}>
          <Col xs={12} lg={6}>
            <Statistic title="团队成员" value={statistics.totalMembers} suffix="人" prefix={<UserOutlined />} />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic
              title="平均负载"
              value={statistics.avgWorkload}
              precision={1}
              suffix="%"
              valueStyle={{ color: statistics.avgWorkload > 100 ? '#ff4d4f' : '#3f8600' }}
            />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic title="平均效率" value={statistics.avgEfficiency} precision={1} suffix="%" valueStyle={{ color: '#1890ff' }} />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic
              title="负载异常"
              value={statistics.overloadedMembers + statistics.underloadedMembers}
              suffix="人"
              valueStyle={{ color: statistics.overloadedMembers + statistics.underloadedMembers > 0 ? '#ff4d4f' : '#3f8600' }}
            />
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="成员工作负载分布">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <RechartsTooltip
                  formatter={(value, name) => [`${value}%`, name === 'workload' ? '工作负载' : '工作效率']}
                />
                <Bar dataKey="workload" fill="#1890ff" name="workload" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="负载状态分布">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={80} paddingAngle={5} dataKey="value">
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Card title="成员工作负载详情">
        <Row gutter={[16, 16]}>
          {workloadData.map(({ member, workload, efficiency }) => {
            const statusConfig = getWorkloadStatus(workload)

            return (
              <Col xs={24} lg={12} key={member.id}>
                <Card size="small" className="h-full">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <Space>
                      <Avatar src={member.user?.avatar || (member.user as any)?.avatar_url} icon={<UserOutlined />} size="small" />
                      <div>
                        <div className="font-medium">{getUserName(member.user)}</div>
                        <Tag color={ROLE_COLORS[member.role_in_project]}>{ROLE_LABELS[member.role_in_project] || member.role_in_project}</Tag>
                      </div>
                    </Space>
                    <Tag color={statusConfig.color} icon={statusConfig.icon}>
                      {statusConfig.text}
                    </Tag>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <div className="mb-1 flex justify-between text-sm">
                        <span>工作负载</span>
                        <span>{workload}%</span>
                      </div>
                      <Progress
                        percent={Math.min(workload, 200)}
                        strokeColor={workload > 120 ? '#ff4d4f' : workload < 60 ? '#faad14' : '#52c41a'}
                        size="small"
                      />
                    </div>

                    <div>
                      <div className="mb-1 flex justify-between text-sm">
                        <span>工作效率</span>
                        <span>{efficiency.toFixed(1)}%</span>
                      </div>
                      <Progress percent={efficiency} strokeColor="#1890ff" size="small" />
                    </div>

                    {member.responsibilities && (
                      <Tooltip title={member.responsibilities}>
                        <div className="truncate text-xs text-gray-500">职责：{member.responsibilities}</div>
                      </Tooltip>
                    )}
                  </div>
                </Card>
              </Col>
            )
          })}
        </Row>
      </Card>
    </div>
  )
}

export default WorkloadChart
