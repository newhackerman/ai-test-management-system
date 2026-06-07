import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Code, 
  GitBranch, 
  Bug, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  TrendingUp,
  Activity,
  FileText,
  Users,
  Zap,
  Target
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

interface DeveloperMetrics {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  codeQuality: number;
  testCoverage: number;
  commitFrequency: number;
  bugFixRate: number;
  reviewScore: number;
  productivityTrends: Array<{
    date: string;
    commits: number;
    tasks: number;
    reviews: number;
  }>;
  codeMetrics: Array<{
    metric: string;
    current: number;
    target: number;
  }>;
}

interface Task {
  id: number;
  title: string;
  project: string;
  priority: 'high' | 'medium' | 'low';
  status: 'todo' | 'in_progress' | 'review' | 'completed';
  type: 'feature' | 'bug' | 'refactor' | 'test';
  estimatedHours: number;
  actualHours?: number;
  deadline: string;
}

interface CodeReview {
  id: number;
  title: string;
  author: string;
  status: 'pending' | 'approved' | 'changes_requested';
  priority: 'high' | 'medium' | 'low';
  linesChanged: number;
  createdAt: string;
}

interface TechnicalDebt {
  id: number;
  type: 'code_smell' | 'duplication' | 'complexity' | 'security';
  description: string;
  severity: 'high' | 'medium' | 'low';
  file: string;
  estimatedEffort: string;
}

const DeveloperDashboard: React.FC = () => {
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
  } = useDashboard('DEVELOPER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [developerMetrics, setDeveloperMetrics] = useState<DeveloperMetrics>({
    totalTasks: 0,
    completedTasks: 0,
    inProgressTasks: 0,
    codeQuality: 0,
    testCoverage: 0,
    commitFrequency: 0,
    bugFixRate: 0,
    reviewScore: 0,
    productivityTrends: [],
    codeMetrics: []
  });

  const [tasks, setTasks] = useState<Task[]>([]);
  const [codeReviews, setCodeReviews] = useState<CodeReview[]>([]);
  const [technicalDebt, setTechnicalDebt] = useState<TechnicalDebt[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['task_update', 'code_update', 'review_update', 'quality_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['task_update', 'code_update', 'review_update', 'quality_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockMetrics: DeveloperMetrics = {
      totalTasks: 24,
      completedTasks: 18,
      inProgressTasks: 4,
      codeQuality: 87.5,
      testCoverage: 82.3,
      commitFrequency: 3.2,
      bugFixRate: 94.1,
      reviewScore: 4.6,
      productivityTrends: [
        { date: '周一', commits: 8, tasks: 3, reviews: 2 },
        { date: '周二', commits: 12, tasks: 4, reviews: 3 },
        { date: '周三', commits: 6, tasks: 2, reviews: 1 },
        { date: '周四', commits: 15, tasks: 5, reviews: 4 },
        { date: '周五', commits: 10, tasks: 4, reviews: 2 },
        { date: '周六', commits: 3, tasks: 1, reviews: 0 },
        { date: '周日', commits: 2, tasks: 0, reviews: 1 }
      ],
      codeMetrics: [
        { metric: '代码复杂度', current: 2.3, target: 3.0 },
        { metric: '重复率', current: 3.2, target: 5.0 },
        { metric: '技术债务', current: 15, target: 20 },
        { metric: '文档覆盖率', current: 78, target: 80 }
      ]
    };

    setDeveloperMetrics(mockMetrics);

    setTasks([
      { id: 1, title: '实现用户认证API', project: '电商平台', priority: 'high', status: 'in_progress', type: 'feature', estimatedHours: 8, actualHours: 6, deadline: '今天' },
      { id: 2, title: '修复支付流程bug', project: '电商平台', priority: 'high', status: 'todo', type: 'bug', estimatedHours: 4, deadline: '明天' },
      { id: 3, title: '重构数据库查询', project: '数据平台', priority: 'medium', status: 'review', type: 'refactor', estimatedHours: 12, actualHours: 10, deadline: '本周五' },
      { id: 4, title: '编写单元测试', project: '移动应用', priority: 'medium', status: 'in_progress', type: 'test', estimatedHours: 6, actualHours: 3, deadline: '下周一' },
      { id: 5, title: '优化图片上传功能', project: '电商平台', priority: 'low', status: 'todo', type: 'feature', estimatedHours: 5, deadline: '下周三' }
    ]);

    setCodeReviews([
      { id: 1, title: '用户权限管理模块', author: '张三', status: 'pending', priority: 'high', linesChanged: 245, createdAt: '2小时前' },
      { id: 2, title: '订单处理优化', author: '李四', status: 'changes_requested', priority: 'medium', linesChanged: 156, createdAt: '4小时前' },
      { id: 3, title: '数据验证增强', author: '王五', status: 'approved', priority: 'medium', linesChanged: 89, createdAt: '1天前' },
      { id: 4, title: '缓存机制改进', author: '赵六', status: 'pending', priority: 'low', linesChanged: 67, createdAt: '2天前' }
    ]);

    setTechnicalDebt([
      { id: 1, type: 'complexity', description: '用户服务类过于复杂', severity: 'high', file: 'UserService.java', estimatedEffort: '4小时' },
      { id: 2, type: 'duplication', description: '重复的数据验证逻辑', severity: 'medium', file: 'ValidationUtils.java', estimatedEffort: '2小时' },
      { id: 3, type: 'code_smell', description: '过长的方法需要拆分', severity: 'medium', file: 'OrderProcessor.java', estimatedEffort: '3小时' },
      { id: 4, type: 'security', description: '缺少输入参数验证', severity: 'high', file: 'ApiController.java', estimatedEffort: '1小时' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-indigo-300 to-purple-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">开发者仪表板</h1>
            <p className="text-indigo-100">
              欢迎回来，{user?.real_name || user?.username} | 开发人员
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{developerMetrics.inProgressTasks}</div>
            <div className="text-indigo-100">进行中任务</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">任务完成率</p>
                <p className="text-2xl font-bold text-green-600">
                  {((developerMetrics.completedTasks / developerMetrics.totalTasks) * 100).toFixed(1)}%
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                {developerMetrics.completedTasks}/{developerMetrics.totalTasks}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">代码质量</p>
                <p className="text-2xl font-bold text-blue-600">
                  {developerMetrics.codeQuality}
                </p>
              </div>
              <Code className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                优秀
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">测试覆盖率</p>
                <p className="text-2xl font-bold text-purple-600">
                  {developerMetrics.testCoverage}%
                </p>
              </div>
              <Target className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                达标
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">评审评分</p>
                <p className="text-2xl font-bold text-orange-600">
                  {developerMetrics.reviewScore}/5
                </p>
              </div>
              <Users className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                高质量
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Productivity Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>生产力趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={developerMetrics.productivityTrends}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['commits', 'tasks', 'reviews'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Code Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>代码指标</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {developerMetrics.codeMetrics.map((metric, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{metric.metric}</span>
                    <span className="text-gray-500">{metric.current}/{metric.target}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        metric.current <= metric.target ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min((metric.current / metric.target) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500">
                    目标: {metric.target} | 
                    状态: {metric.current <= metric.target ? 
                      <span className="text-green-600">达标</span> : 
                      <span className="text-red-600">超标</span>
                    }
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tasks and Reviews Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* My Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>我的任务</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tasks.map((task) => (
                <div key={task.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    task.status === 'completed' ? 'bg-green-500' :
                    task.status === 'in_progress' ? 'bg-blue-500' :
                    task.status === 'review' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{task.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {task.project}
                      </Badge>
                      <Badge 
                        variant={task.priority === 'high' ? 'destructive' : task.priority === 'medium' ? 'secondary' : 'outline'}
                        className="text-xs"
                      >
                        {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {task.type === 'feature' ? '功能' :
                         task.type === 'bug' ? 'Bug' :
                         task.type === 'refactor' ? '重构' : '测试'}
                      </Badge>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>预估: {task.estimatedHours}h {task.actualHours && `| 实际: ${task.actualHours}h`}</span>
                      <span>截止: {task.deadline}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Code Reviews */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5" />
              <span>代码评审</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {codeReviews.map((review) => (
                <div key={review.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-sm">{review.title}</p>
                    <Badge 
                      variant={
                        review.status === 'approved' ? 'default' :
                        review.status === 'pending' ? 'secondary' : 'destructive'
                      }
                      className="text-xs"
                    >
                      {review.status === 'approved' ? '已通过' :
                       review.status === 'pending' ? '待评审' : '需修改'}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mb-2">
                    <span>作者: {review.author}</span>
                    <span>变更: {review.linesChanged} 行</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <Badge 
                      variant={review.priority === 'high' ? 'destructive' : review.priority === 'medium' ? 'secondary' : 'outline'}
                      className="text-xs"
                    >
                      {review.priority === 'high' ? '高优先级' : review.priority === 'medium' ? '中优先级' : '低优先级'}
                    </Badge>
                    <span className="text-xs text-gray-500">{review.createdAt}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Technical Debt */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Bug className="h-5 w-5" />
            <span>技术债务</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {technicalDebt.map((debt) => (
              <div key={debt.id} className={`p-4 rounded-lg border-l-4 ${
                debt.severity === 'high' 
                  ? 'bg-red-50 border-red-500' 
                  : debt.severity === 'medium'
                  ? 'bg-yellow-50 border-yellow-500'
                  : 'bg-blue-50 border-blue-500'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium">{debt.description}</p>
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant={
                        debt.severity === 'high' ? 'destructive' : 
                        debt.severity === 'medium' ? 'secondary' : 'outline'
                      }
                      className="text-xs"
                    >
                      {debt.severity === 'high' ? '高' : debt.severity === 'medium' ? '中' : '低'}
                    </Badge>
                    <span className="text-xs text-gray-500">预估: {debt.estimatedEffort}</span>
                  </div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">文件: {debt.file}</span>
                  <Badge variant="outline" className="text-xs">
                    {debt.type === 'complexity' ? '复杂度' :
                     debt.type === 'duplication' ? '重复代码' :
                     debt.type === 'code_smell' ? '代码异味' : '安全问题'}
                  </Badge>
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

export default DeveloperDashboard;