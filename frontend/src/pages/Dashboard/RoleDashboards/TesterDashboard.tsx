import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  TestTube, 
  Bug, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  TrendingUp,
  Activity,
  FileText,
  Shield,
  Target,
  BarChart3
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

interface TestMetrics {
  totalTestCases: number;
  executedTests: number;
  passedTests: number;
  failedTests: number;
  testCoverage: number;
  automationRate: number;
  defectDensity: number;
  executionRate: number;
  qualityScore: number;
  testTrends: Array<{
    date: string;
    executed: number;
    passed: number;
    failed: number;
  }>;
  defectTrends: Array<{
    week: string;
    found: number;
    fixed: number;
    open: number;
  }>;
}

interface TestCase {
  id: number;
  title: string;
  project: string;
  priority: 'high' | 'medium' | 'low';
  status: 'not_executed' | 'passed' | 'failed' | 'blocked';
  type: 'functional' | 'integration' | 'performance' | 'security';
  automation: 'manual' | 'semi_auto' | 'full_auto';
  lastExecuted?: string;
  assignee: string;
}

interface Defect {
  id: number;
  title: string;
  project: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  type: 'functional' | 'ui' | 'performance' | 'security';
  foundBy: string;
  assignedTo: string;
  createdAt: string;
}

interface TestEnvironment {
  id: number;
  name: string;
  status: 'available' | 'busy' | 'maintenance' | 'error';
  usage: number;
  lastUpdate: string;
  version: string;
}

const TesterDashboard: React.FC = () => {
  const { user } = useAuth();
  const {
    dashboardConfig,
    widgets,
    loading,
    error,
    saveDashboardLayout,
    resetDashboard,
    addWidget,
    removeWidget,
    updateWidget
  } = useDashboard('TESTER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [testMetrics, setTestMetrics] = useState<TestMetrics>({
    totalTestCases: 0,
    executedTests: 0,
    passedTests: 0,
    failedTests: 0,
    testCoverage: 0,
    automationRate: 0,
    defectDensity: 0,
    executionRate: 0,
    qualityScore: 0,
    testTrends: [],
    defectTrends: []
  });

  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [testEnvironments, setTestEnvironments] = useState<TestEnvironment[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['test_update', 'defect_update', 'environment_update', 'quality_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['test_update', 'defect_update', 'environment_update', 'quality_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockMetrics: TestMetrics = {
      totalTestCases: 456,
      executedTests: 389,
      passedTests: 342,
      failedTests: 47,
      testCoverage: 87.3,
      automationRate: 65.2,
      defectDensity: 2.1,
      executionRate: 85.3,
      qualityScore: 91.5,
      testTrends: [
        { date: '周一', executed: 45, passed: 38, failed: 7 },
        { date: '周二', executed: 52, passed: 46, failed: 6 },
        { date: '周三', executed: 38, passed: 32, failed: 6 },
        { date: '周四', executed: 61, passed: 54, failed: 7 },
        { date: '周五', executed: 48, passed: 42, failed: 6 },
        { date: '周六', executed: 25, passed: 22, failed: 3 },
        { date: '周日', executed: 15, passed: 13, failed: 2 }
      ],
      defectTrends: [
        { week: '第1周', found: 12, fixed: 8, open: 4 },
        { week: '第2周', found: 15, fixed: 12, open: 7 },
        { week: '第3周', found: 9, fixed: 11, open: 5 },
        { week: '第4周', found: 18, fixed: 14, open: 9 }
      ]
    };

    setTestMetrics(mockMetrics);

    setTestCases([
      { id: 1, title: '用户登录功能测试', project: '电商平台', priority: 'high', status: 'passed', type: 'functional', automation: 'full_auto', lastExecuted: '2小时前', assignee: '张三' },
      { id: 2, title: '支付流程集成测试', project: '电商平台', priority: 'high', status: 'failed', type: 'integration', automation: 'semi_auto', lastExecuted: '1小时前', assignee: '李四' },
      { id: 3, title: '页面加载性能测试', project: '移动应用', priority: 'medium', status: 'not_executed', type: 'performance', automation: 'manual', assignee: '王五' },
      { id: 4, title: '数据安全验证测试', project: '数据平台', priority: 'high', status: 'blocked', type: 'security', automation: 'manual', assignee: '赵六' },
      { id: 5, title: 'API接口功能测试', project: 'AI系统', priority: 'medium', status: 'passed', type: 'functional', automation: 'full_auto', lastExecuted: '30分钟前', assignee: '钱七' }
    ]);

    setDefects([
      { id: 1, title: '支付页面金额显示错误', project: '电商平台', severity: 'critical', status: 'open', type: 'functional', foundBy: '李四', assignedTo: '开发团队A', createdAt: '2小时前' },
      { id: 2, title: '移动端界面适配问题', project: '移动应用', severity: 'medium', status: 'in_progress', type: 'ui', foundBy: '王五', assignedTo: '前端开发', createdAt: '4小时前' },
      { id: 3, title: '数据查询响应缓慢', project: '数据平台', severity: 'high', status: 'resolved', type: 'performance', foundBy: '赵六', assignedTo: '后端开发', createdAt: '1天前' },
      { id: 4, title: '用户权限验证漏洞', project: 'AI系统', severity: 'high', status: 'open', type: 'security', foundBy: '钱七', assignedTo: '安全团队', createdAt: '6小时前' },
      { id: 5, title: '报表导出功能异常', project: '电商平台', severity: 'low', status: 'closed', type: 'functional', foundBy: '张三', assignedTo: '开发团队B', createdAt: '3天前' }
    ]);

    setTestEnvironments([
      { id: 1, name: '开发环境', status: 'available', usage: 45, lastUpdate: '10分钟前', version: 'v2.1.0' },
      { id: 2, name: '测试环境', status: 'busy', usage: 85, lastUpdate: '5分钟前', version: 'v2.0.8' },
      { id: 3, name: '预发布环境', status: 'available', usage: 20, lastUpdate: '30分钟前', version: 'v2.1.0-rc1' },
      { id: 4, name: '性能测试环境', status: 'maintenance', usage: 0, lastUpdate: '2小时前', version: 'v2.0.5' },
      { id: 5, name: '安全测试环境', status: 'error', usage: 0, lastUpdate: '1小时前', version: 'v2.0.8' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-cyan-300 to-blue-400 rounded-lg h-32"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-300 rounded-lg h-24"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <div className="text-red-500 mb-4">
              <AlertTriangle className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold mb-2">加载失败</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="bg-gradient-to-r from-cyan-600 to-blue-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">测试仪表板</h1>
            <p className="text-cyan-100">
              欢迎回来，{user?.real_name || user?.username} | 测试人员
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{testMetrics.qualityScore}%</div>
            <div className="text-cyan-100">质量评分</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">测试通过率</p>
                <p className="text-2xl font-bold text-green-600">
                  {((testMetrics.passedTests / testMetrics.executedTests) * 100).toFixed(1)}%
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                {testMetrics.passedTests}/{testMetrics.executedTests}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">测试覆盖率</p>
                <p className="text-2xl font-bold text-blue-600">
                  {testMetrics.testCoverage}%
                </p>
              </div>
              <Target className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                目标达成
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">自动化率</p>
                <p className="text-2xl font-bold text-purple-600">
                  {testMetrics.automationRate}%
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                持续提升
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">缺陷密度</p>
                <p className="text-2xl font-bold text-orange-600">
                  {testMetrics.defectDensity}
                </p>
              </div>
              <Bug className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                每千行代码
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test Execution Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>测试执行趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={testMetrics.testTrends}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['passed', 'failed'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Defect Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bug className="h-5 w-5" />
              <span>缺陷趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              data={testMetrics.defectTrends}
              config={{
                xAxisKey: 'week',
                yAxisKeys: ['found', 'fixed', 'open'],
                showDataPoints: true,
                smoothCurve: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Test Cases and Defects Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Test Cases */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TestTube className="h-5 w-5" />
              <span>最近测试用例</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {testCases.map((testCase) => (
                <div key={testCase.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    testCase.status === 'passed' ? 'bg-green-500' :
                    testCase.status === 'failed' ? 'bg-red-500' :
                    testCase.status === 'blocked' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{testCase.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {testCase.project}
                      </Badge>
                      <Badge 
                        variant={testCase.priority === 'high' ? 'destructive' : testCase.priority === 'medium' ? 'secondary' : 'outline'}
                        className="text-xs"
                      >
                        {testCase.priority === 'high' ? '高' : testCase.priority === 'medium' ? '中' : '低'}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {testCase.type === 'functional' ? '功能' :
                         testCase.type === 'integration' ? '集成' :
                         testCase.type === 'performance' ? '性能' : '安全'}
                      </Badge>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>负责人: {testCase.assignee}</span>
                      {testCase.lastExecuted && <span>执行: {testCase.lastExecuted}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Active Defects */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <XCircle className="h-5 w-5" />
              <span>活跃缺陷</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {defects.filter(d => d.status !== 'closed').map((defect) => (
                <div key={defect.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-sm">{defect.title}</p>
                    <Badge 
                      variant={
                        defect.severity === 'critical' ? 'destructive' :
                        defect.severity === 'high' ? 'destructive' :
                        defect.severity === 'medium' ? 'secondary' : 'outline'
                      }
                      className="text-xs"
                    >
                      {defect.severity === 'critical' ? '严重' :
                       defect.severity === 'high' ? '高' :
                       defect.severity === 'medium' ? '中' : '低'}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mb-2">
                    <span>项目: {defect.project}</span>
                    <span>类型: {
                      defect.type === 'functional' ? '功能' :
                      defect.type === 'ui' ? 'UI' :
                      defect.type === 'performance' ? '性能' : '安全'
                    }</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="text-xs text-gray-500">
                      <span>发现人: {defect.foundBy}</span>
                      <span className="ml-2">分配给: {defect.assignedTo}</span>
                    </div>
                    <Badge 
                      variant={
                        defect.status === 'open' ? 'destructive' :
                        defect.status === 'in_progress' ? 'secondary' : 'default'
                      }
                      className="text-xs"
                    >
                      {defect.status === 'open' ? '开放' :
                       defect.status === 'in_progress' ? '处理中' : '已解决'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Test Environments */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>测试环境</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {testEnvironments.map((env) => (
              <div key={env.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{env.name}</h4>
                  <Badge 
                    variant={
                      env.status === 'available' ? 'default' :
                      env.status === 'busy' ? 'secondary' :
                      env.status === 'maintenance' ? 'outline' : 'destructive'
                    }
                  >
                    {env.status === 'available' ? '可用' :
                     env.status === 'busy' ? '忙碌' :
                     env.status === 'maintenance' ? '维护' : '错误'}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">使用率:</span>
                    <span>{env.usage}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">版本:</span>
                    <span>{env.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">更新:</span>
                    <span>{env.lastUpdate}</span>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div 
                    className={`h-2 rounded-full ${
                      env.usage < 50 ? 'bg-green-500' :
                      env.usage < 80 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${env.usage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Custom Dashboard Grid */}
      <DashboardGrid
        widgets={widgets}
        editMode={false}
        onLayoutChange={() => {}}
        onRemoveWidget={removeWidget}
        onUpdateWidget={updateWidget}
        realtimeData={realtimeData}
      />
    </div>
  );
};

export default TesterDashboard;