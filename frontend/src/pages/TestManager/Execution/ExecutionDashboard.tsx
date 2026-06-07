import React from 'react'
import { Link } from 'react-router-dom'
import { Play, Pause, CheckCircle, XCircle, Clock, Users, TrendingUp, Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Button } from '../../../components/ui/Button'
import { Badge } from '../../../components/ui/Badge'
import { Progress } from '../../../components/ui/Progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { useExecutions, useExecutionStatistics, usePauseExecution } from '../../../hooks/testmanager/useExecution'
import { ExecutionStatus, ExecutionType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const ExecutionDashboard: React.FC = () => {
  const { data: executionsData, isLoading } = useExecutions({ 
    page: 1, 
    size: 10,
    execution_status: ExecutionStatus.IN_PROGRESS 
  })
  const { data: statistics } = useExecutionStatistics()
  const pauseExecution = usePauseExecution()

  const executions = executionsData?.data || []
  const stats = statistics || {
    total_executions: 0,
    in_progress: 0,
    completed_today: 0,
    pass_rate: 0,
    avg_duration: 0,
    active_executors: 0,
  }

  const getStatusBadge = (status: ExecutionStatus) => {
    const statusConfig = {
      [ExecutionStatus.NOT_EXECUTED]: { label: '未执行', variant: 'secondary' as const, icon: Clock },
      [ExecutionStatus.IN_PROGRESS]: { label: '执行中', variant: 'default' as const, icon: Play },
      [ExecutionStatus.PASSED]: { label: '通过', variant: 'default' as const, icon: CheckCircle },
      [ExecutionStatus.FAILED]: { label: '失败', variant: 'destructive' as const, icon: XCircle },
      [ExecutionStatus.BLOCKED]: { label: '阻塞', variant: 'secondary' as const, icon: Pause },
      [ExecutionStatus.SKIPPED]: { label: '跳过', variant: 'outline' as const, icon: Clock },
    }
    
    const config = statusConfig[status]
    const Icon = config.icon
    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    )
  }

  const getTypeLabel = (type: ExecutionType) => {
    return type === ExecutionType.MANUAL ? '手动' : '自动化'
  }

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">测试执行仪表板</h1>
          <p className="text-gray-600">实时监控测试执行状态和进度</p>
        </div>
        <div className="flex space-x-2">
          <Link to="/test-manager/executions/manual">
            <Button>
              <Play className="w-4 h-4 mr-2" />
              开始手动测试
            </Button>
          </Link>
          <Link to="/test-manager/executions/automation">
            <Button variant="outline">
              <Activity className="w-4 h-4 mr-2" />
              自动化测试
            </Button>
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">总执行数</p>
                <p className="text-2xl font-bold">{stats.total_executions}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Play className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">执行中</p>
                <p className="text-2xl font-bold">{stats.in_progress}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">今日完成</p>
                <p className="text-2xl font-bold">{stats.completed_today}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">通过率</p>
                <p className="text-2xl font-bold">{stats.pass_rate}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>执行进度概览</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>总体进度</span>
                    <span>{stats.pass_rate}%</span>
                  </div>
                  <Progress value={stats.pass_rate} className="h-3" />
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">{stats.completed_today}</p>
                    <p className="text-sm text-gray-600">今日完成</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">{stats.avg_duration}min</p>
                    <p className="text-sm text-gray-600">平均时长</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>执行统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm">活跃执行者</span>
                <div className="flex items-center space-x-1">
                  <Users className="w-4 h-4 text-gray-500" />
                  <span className="font-medium">{stats.active_executors}</span>
                </div>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm">平均执行时长</span>
                <span className="font-medium">{stats.avg_duration} 分钟</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm">执行效率</span>
                <Badge variant="default">良好</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Executions */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>正在执行的测试</CardTitle>
          <Link to="/test-manager/executions">
            <Button variant="outline" size="sm">查看全部</Button>
          </Link>
        </CardHeader>
        <CardContent>
          {executions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>执行编号</TableHead>
                  <TableHead>测试用例</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>执行者</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>持续时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.map((execution) => {
                  const duration = execution.started_at 
                    ? Math.floor((new Date().getTime() - new Date(execution.started_at).getTime()) / 1000 / 60)
                    : 0

                  return (
                    <TableRow key={execution.id}>
                      <TableCell>
                        <Link 
                          to={`/test-manager/executions/${execution.id}`}
                          className="font-medium text-blue-600 hover:text-blue-800"
                        >
                          {execution.execution_code}
                        </Link>
                      </TableCell>
                      <TableCell>测试用例</TableCell>
                      <TableCell>
                        <Badge variant="outline">{getTypeLabel(execution.execution_type)}</Badge>
                      </TableCell>
                      <TableCell>{getStatusBadge(execution.execution_status)}</TableCell>
                      <TableCell>执行者</TableCell>
                      <TableCell>{execution.started_at ? formatDate(execution.started_at) : '-'}</TableCell>
                      <TableCell>{duration > 0 ? `${duration} 分钟` : '-'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.alert(`执行编号：${execution.execution_code}\n状态：${execution.execution_status}\n环境：${execution.test_environment || '-'}`)}
                          >
                            查看
                          </Button>
                          {execution.execution_status === ExecutionStatus.IN_PROGRESS && (
                            <Button variant="ghost" size="sm" onClick={() => pauseExecution.mutate(execution.id)}>
                              <Pause className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-gray-500">
              当前没有正在执行的测试
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link to="/test-manager/executions/manual">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Play className="w-8 h-8 text-green-500" />
                <div>
                  <h3 className="font-semibold">手动测试执行</h3>
                  <p className="text-sm text-gray-600">开始手动执行测试用例</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/executions/automation">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Activity className="w-8 h-8 text-blue-500" />
                <div>
                  <h3 className="font-semibold">自动化测试</h3>
                  <p className="text-sm text-gray-600">配置和运行自动化测试</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/executions/history">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Clock className="w-8 h-8 text-purple-500" />
                <div>
                  <h3 className="font-semibold">执行历史</h3>
                  <p className="text-sm text-gray-600">查看历史执行记录</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}

export default ExecutionDashboard
