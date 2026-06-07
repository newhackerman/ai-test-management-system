import React from 'react'
import { Link } from 'react-router-dom'
import { 
  FileText, 
  TestTube, 
  Play, 
  Bug, 
  BarChart3, 
  Shield, 
  Zap,
  TrendingUp,
  Users,
  Calendar
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Progress } from '../../components/ui/Progress'
import { Badge } from '../../components/ui/Badge'
import { useTestPlans } from '../../hooks/testmanager/useTestPlan'
import { useTestCases } from '../../hooks/testmanager/useTestCase'
import { useDefects } from '../../hooks/testmanager/useDefect'
import { useExecutionStatistics } from '../../hooks/testmanager/useExecution'
import { TestPlanStatus, DefectSeverity } from '../../types/testmanager'

const TestManager: React.FC = () => {
  const { data: plansData } = useTestPlans({ page: 1, size: 5 })
  const { data: casesData } = useTestCases({ page: 1, size: 1 })
  const { data: defectsData } = useDefects({ page: 1, size: 1 })
  const { data: executionStats } = useExecutionStatistics()

  const plans = plansData?.data || []
  const defects = defectsData?.data || []
  const stats = {
    totalPlans: plansData?.total || 0,
    activePlans: plans.filter((plan) => plan.status === TestPlanStatus.IN_PROGRESS).length,
    totalCases: casesData?.total || 0,
    executedCases: executionStats?.total_executions || 0,
    passedCases: Math.round(((executionStats?.pass_rate || 0) / 100) * (executionStats?.total_executions || 0)),
    failedCases: Math.max((executionStats?.total_executions || 0) - Math.round(((executionStats?.pass_rate || 0) / 100) * (executionStats?.total_executions || 0)), 0),
    totalDefects: defectsData?.total || 0,
    criticalDefects: defects.filter((defect) => defect.severity === DefectSeverity.CRITICAL).length,
    highDefects: defects.filter((defect) => defect.severity === DefectSeverity.HIGH).length,
    executionRate: plans.reduce((sum, plan) => sum + (Number(plan.execution_rate) || 0), 0) / (plans.length || 1),
    passRate: executionStats?.pass_rate || 0,
  }

  const recentPlans = plans.map((plan) => ({
    id: plan.id,
    name: plan.plan_name,
    status: plan.status,
    progress: Number(plan.execution_rate) || 0,
  }))

  const quickActions = [
    {
      title: '创建测试计划',
      description: '创建新的测试计划',
      icon: FileText,
      link: '/test-manager/test-plans/create',
      color: 'bg-blue-500',
    },
    {
      title: '创建测试用例',
      description: '添加新的测试用例',
      icon: TestTube,
      link: '/test-manager/test-cases/create',
      color: 'bg-green-500',
    },
    {
      title: '执行测试',
      description: '开始测试执行',
      icon: Play,
      link: '/test-manager/executions',
      color: 'bg-purple-500',
    },
    {
      title: '报告缺陷',
      description: '创建新的缺陷报告',
      icon: Bug,
      link: '/test-manager/defects/create',
      action: 'create-defect',
      color: 'bg-red-500',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">测试管理</h1>
        <p className="text-gray-600 mt-2">管理测试计划、用例、执行和缺陷的完整生命周期</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {quickActions.map((action) => (
          <Link key={action.title} to={action.action === 'create-defect' ? '/test-manager/defects' : action.link}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="pt-6">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${action.color}`}>
                    <action.icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{action.title}</h3>
                    <p className="text-sm text-gray-600">{action.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Statistics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">测试计划</p>
                <p className="text-2xl font-bold">{stats.totalPlans}</p>
                <p className="text-xs text-gray-500">活跃: {stats.activePlans}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <TestTube className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">测试用例</p>
                <p className="text-2xl font-bold">{stats.totalCases}</p>
                <p className="text-xs text-gray-500">已执行: {stats.executedCases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">执行率</p>
                <p className="text-2xl font-bold">{stats.executionRate}%</p>
                <Progress value={stats.executionRate} className="h-2 mt-1" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Bug className="w-5 h-5 text-red-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">缺陷</p>
                <p className="text-2xl font-bold">{stats.totalDefects}</p>
                <p className="text-xs text-gray-500">严重: {stats.criticalDefects}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Test Plans */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>最近的测试计划</CardTitle>
              <Link to="/test-manager/test-plans">
                <Button variant="outline" size="sm">查看全部</Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentPlans.map((plan) => (
                  <div key={plan.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <h4 className="font-medium">{plan.name}</h4>
                      <div className="flex items-center space-x-2 mt-1">
                        <Badge variant="secondary">{plan.status}</Badge>
                        <span className="text-sm text-gray-500">进度: {plan.progress}%</span>
                      </div>
                    </div>
                    <div className="w-24">
                      <Progress value={plan.progress} className="h-2" />
                    </div>
                  </div>
                ))}
                {recentPlans.length === 0 && (
                  <div className="text-center py-8 text-gray-500">暂无测试计划数据</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Test Quality Metrics */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>质量指标</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>通过率</span>
                  <span>{stats.passRate}%</span>
                </div>
                <Progress value={stats.passRate} className="h-2" />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">通过</span>
                  <span className="text-sm font-medium text-green-600">{stats.passedCases}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">失败</span>
                  <span className="text-sm font-medium text-red-600">{stats.failedCases}</span>
                </div>
              </div>

              <div className="pt-4 border-t">
                <h4 className="font-medium mb-2">缺陷分布</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm">严重</span>
                    <Badge variant="destructive">{stats.criticalDefects}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">高</span>
                    <Badge variant="secondary">{stats.highDefects}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">其他</span>
                    <Badge variant="outline">{stats.totalDefects - stats.criticalDefects - stats.highDefects}</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link to="/test-manager/test-plans">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <FileText className="w-8 h-8 text-blue-500" />
                <div>
                  <h3 className="font-semibold">测试计划管理</h3>
                  <p className="text-sm text-gray-600">创建和管理测试计划</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/test-cases">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <TestTube className="w-8 h-8 text-green-500" />
                <div>
                  <h3 className="font-semibold">测试用例管理</h3>
                  <p className="text-sm text-gray-600">设计和维护测试用例</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/executions">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Play className="w-8 h-8 text-purple-500" />
                <div>
                  <h3 className="font-semibold">测试执行</h3>
                  <p className="text-sm text-gray-600">执行测试并记录结果</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/defects">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Bug className="w-8 h-8 text-red-500" />
                <div>
                  <h3 className="font-semibold">缺陷管理</h3>
                  <p className="text-sm text-gray-600">跟踪和管理缺陷</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/reports">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <BarChart3 className="w-8 h-8 text-indigo-500" />
                <div>
                  <h3 className="font-semibold">测试报告</h3>
                  <p className="text-sm text-gray-600">生成和查看测试报告</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/test-manager/performance">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Zap className="w-8 h-8 text-yellow-500" />
                <div>
                  <h3 className="font-semibold">专项测试</h3>
                  <p className="text-sm text-gray-600">性能和安全测试</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}

export default TestManager
