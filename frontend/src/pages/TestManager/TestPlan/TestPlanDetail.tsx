import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Edit, Play, Pause, CheckCircle, Download, Users, Calendar, Target } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Progress } from '../../../components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import { useExportTestPlan, useTestPlan, useTestPlanProgress, useUpdateTestPlanStatus } from '../../../hooks/testmanager/useTestPlan'
import { TestPlanStatus, TestType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const TestPlanDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const planId = parseInt(id!, 10)

  const { data: testPlan, isLoading, error } = useTestPlan(planId)
  const { data: progress } = useTestPlanProgress(planId)
  const exportTestPlan = useExportTestPlan()
  const updateTestPlanStatus = useUpdateTestPlanStatus()

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (error || !testPlan) {
    return <div className="text-red-500 text-center">加载失败</div>
  }

  const getStatusBadge = (status: TestPlanStatus) => {
    const statusConfig = {
      [TestPlanStatus.DRAFT]: { label: '草稿', variant: 'secondary' as const },
      [TestPlanStatus.APPROVED]: { label: '已批准', variant: 'default' as const },
      [TestPlanStatus.IN_PROGRESS]: { label: '进行中', variant: 'default' as const },
      [TestPlanStatus.PAUSED]: { label: '暂停', variant: 'secondary' as const },
      [TestPlanStatus.COMPLETED]: { label: '已完成', variant: 'default' as const },
      [TestPlanStatus.CANCELLED]: { label: '已取消', variant: 'destructive' as const },
    }
    
    const config = statusConfig[status]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getTypeLabel = (type: TestType) => {
    const typeLabels = {
      [TestType.FUNCTIONAL]: '功能测试',
      [TestType.PERFORMANCE]: '性能测试',
      [TestType.SECURITY]: '安全测试',
      [TestType.INTEGRATION]: '集成测试',
      [TestType.REGRESSION]: '回归测试',
      [TestType.ACCEPTANCE]: '验收测试',
    }
    return typeLabels[type] || type
  }

  const executionRate = testPlan.total_cases > 0 ? (testPlan.executed_cases / testPlan.total_cases) * 100 : 0
  const passRate = testPlan.executed_cases > 0 ? (testPlan.passed_cases / testPlan.executed_cases) * 100 : 0
  const updatingStatus = updateTestPlanStatus.isPending

  const handleExport = (format: 'csv' | 'txt') => {
    exportTestPlan.mutate({ id: planId, format })
  }

  const handleStatusChange = (status: TestPlanStatus) => {
    updateTestPlanStatus.mutate({ id: planId, status })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/test-plans">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{testPlan.plan_name}</h1>
            <p className="text-gray-600">{testPlan.plan_code}</p>
          </div>
          {getStatusBadge(testPlan.status)}
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {testPlan.status === TestPlanStatus.DRAFT && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.APPROVED)}>
              <CheckCircle className="w-4 h-4 mr-2" />
              批准
            </Button>
          )}
          {testPlan.status === TestPlanStatus.APPROVED && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.IN_PROGRESS)}>
              <Play className="w-4 h-4 mr-2" />
              开始执行
            </Button>
          )}
          {testPlan.status === TestPlanStatus.IN_PROGRESS && (
            <>
              <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.PAUSED)}>
                <Pause className="w-4 h-4 mr-2" />
                暂停
              </Button>
              <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.COMPLETED)}>
                <CheckCircle className="w-4 h-4 mr-2" />
                完成
              </Button>
            </>
          )}
          {testPlan.status === TestPlanStatus.PAUSED && (
            <Button variant="outline" disabled={updatingStatus} onClick={() => handleStatusChange(TestPlanStatus.IN_PROGRESS)}>
              <Play className="w-4 h-4 mr-2" />
              继续执行
            </Button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" disabled={exportTestPlan.isPending}>
                <Download className="w-4 h-4 mr-2" />
                {exportTestPlan.isPending ? '导出中...' : '导出'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleExport('csv')}>导出 CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('txt')}>导出 TXT</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Link to={`/test-manager/test-plans/${planId}/edit`}>
            <Button>
              <Edit className="w-4 h-4 mr-2" />
              编辑
            </Button>
          </Link>
        </div>
      </div>     
 {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Target className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">总用例数</p>
                <p className="text-2xl font-bold">{testPlan.total_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">已执行</p>
                <p className="text-2xl font-bold">{testPlan.executed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-green-500 rounded-full" />
              <div>
                <p className="text-sm font-medium text-gray-600">通过</p>
                <p className="text-2xl font-bold text-green-600">{testPlan.passed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-red-500 rounded-full" />
              <div>
                <p className="text-sm font-medium text-gray-600">失败</p>
                <p className="text-2xl font-bold text-red-600">{testPlan.failed_cases}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Section */}
      <Card>
        <CardHeader>
          <CardTitle>执行进度</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>执行进度</span>
                <span>{executionRate.toFixed(1)}%</span>
              </div>
              <Progress value={executionRate} className="h-3" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>通过率</span>
                <span>{passRate.toFixed(1)}%</span>
              </div>
              <Progress value={passRate} className="h-3" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Information */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="test-cases">测试用例</TabsTrigger>
          <TabsTrigger value="execution">执行记录</TabsTrigger>
          <TabsTrigger value="defects">缺陷</TabsTrigger>
          <TabsTrigger value="reports">报告</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-600">测试类型</label>
                  <p>{getTypeLabel(testPlan.test_type)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">描述</label>
                  <p>{testPlan.description || '暂无描述'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">测试范围</label>
                  <p>{testPlan.test_scope || '暂无定义'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">测试策略</label>
                  <p>{testPlan.test_strategy || '暂无定义'}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>时间安排</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">计划开始时间</label>
                    <p>{testPlan.planned_start_date ? formatDate(testPlan.planned_start_date) : '未设置'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">计划结束时间</label>
                    <p>{testPlan.planned_end_date ? formatDate(testPlan.planned_end_date) : '未设置'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">实际开始时间</label>
                    <p>{testPlan.actual_start_date ? formatDate(testPlan.actual_start_date) : '未开始'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">实际结束时间</label>
                    <p>{testPlan.actual_end_date ? formatDate(testPlan.actual_end_date) : '未完成'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="test-cases">
          <Card>
            <CardHeader>
              <CardTitle>测试用例</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                测试用例列表将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="execution">
          <Card>
            <CardHeader>
              <CardTitle>执行记录</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                执行记录将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="defects">
          <Card>
            <CardHeader>
              <CardTitle>相关缺陷</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                缺陷列表将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports">
          <Card>
            <CardHeader>
              <CardTitle>测试报告</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                测试报告将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TestPlanDetail
