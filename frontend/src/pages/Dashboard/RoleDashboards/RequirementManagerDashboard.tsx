import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  FileText, 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  Users, 
  TrendingUp,
  MessageSquare,
  GitBranch,
  Target,
  BarChart3
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

const RequirementManagerDashboard: React.FC = () => {
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
  } = useDashboard('REQUIREMENT_MANAGER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [requirementMetrics, setRequirementMetrics] = useState({
    totalRequirements: 0,
    statusDistribution: {} as Record<string, number>,
    priorityDistribution: {} as Record<string, number>,
    completionRate: 0,
    qualityScore: 0,
    changeFrequency: 0,
    traceabilityCoverage: 0,
    stakeholderEngagement: 0,
    reviewProgress: 0,
    deliveryTimeline: [] as Array<{ month: string; planned: number; actual: number; }>
  });

  const [recentActivities, setRecentActivities] = useState<Array<any>>([]);
  const [pendingReviews, setPendingReviews] = useState<Array<any>>([]);
  const [riskAlerts, setRiskAlerts] = useState<Array<any>>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['requirement_update', 'review_update', 'stakeholder_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['requirement_update', 'review_update', 'stakeholder_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockData = {
      totalRequirements: 156,
      statusDistribution: {
        '待分析': 12,
        '已确认': 45,
        '开发中': 67,
        '已完成': 32
      },
      priorityDistribution: {
        '高': 23,
        '中': 89,
        '低': 44
      },
      completionRate: 78.5,
      qualityScore: 85.2,
      changeFrequency: 12.3,
      traceabilityCoverage: 92.1,
      stakeholderEngagement: 88.7,
      reviewProgress: 76.4,
      deliveryTimeline: [
        { month: '1月', planned: 20, actual: 18 },
        { month: '2月', planned: 25, actual: 23 },
        { month: '3月', planned: 30, actual: 32 },
        { month: '4月', planned: 28, actual: 26 }
      ]
    };

    setRequirementMetrics(mockData);

    setRecentActivities([
      { id: 1, type: 'requirement_created', title: '新增需求：用户权限管理', time: '2分钟前', user: '张三' },
      { id: 2, type: 'requirement_updated', title: '更新需求：数据导出功能', time: '15分钟前', user: '李四' },
      { id: 3, type: 'review_completed', title: '完成评审：API接口设计', time: '1小时前', user: '王五' },
      { id: 4, type: 'stakeholder_feedback', title: '干系人反馈：UI界面优化', time: '2小时前', user: '赵六' }
    ]);

    setPendingReviews([
      { id: 1, title: '移动端适配需求', priority: 'high', deadline: '2024-01-15', reviewer: '产品经理' },
      { id: 2, title: '性能优化需求', priority: 'medium', deadline: '2024-01-18', reviewer: '技术架构师' },
      { id: 3, title: '安全加固需求', priority: 'high', deadline: '2024-01-20', reviewer: '安全专家' }
    ]);

    setRiskAlerts([
      { id: 1, type: 'deadline', message: '3个需求即将超期', severity: 'high' },
      { id: 2, type: 'quality', message: '需求质量评分下降', severity: 'medium' },
      { id: 3, type: 'dependency', message: '发现循环依赖关系', severity: 'high' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-blue-300 to-purple-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">需求管理仪表板</h1>
            <p className="text-blue-100">
              欢迎回来，{user?.real_name || user?.username} | 需求管理人员
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{requirementMetrics.totalRequirements}</div>
            <div className="text-blue-100">总需求数</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">完成率</p>
                <p className="text-2xl font-bold text-green-600">
                  {requirementMetrics.completionRate}%
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                +2.3% 本周
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">质量评分</p>
                <p className="text-2xl font-bold text-blue-600">
                  {requirementMetrics.qualityScore}
                </p>
              </div>
              <Target className="h-8 w-8 text-blue-600" />
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
                <p className="text-sm font-medium text-gray-600">追溯覆盖率</p>
                <p className="text-2xl font-bold text-purple-600">
                  {requirementMetrics.traceabilityCoverage}%
                </p>
              </div>
              <GitBranch className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                高覆盖
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">干系人参与度</p>
                <p className="text-2xl font-bold text-orange-600">
                  {requirementMetrics.stakeholderEngagement}%
                </p>
              </div>
              <Users className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                活跃
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>需求状态分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PieChart
              data={Object.entries(requirementMetrics.statusDistribution).map(([key, value]) => ({
                name: key,
                value: value as number
              }))}
              config={{
                showPercentage: true,
                showLegend: true,
                donut: false,
                showTotal: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Delivery Timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>交付时间线</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={requirementMetrics.deliveryTimeline}
              config={{
                xAxisKey: 'month',
                yAxisKeys: ['planned', 'actual'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Activity and Reviews Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activities */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-5 w-5" />
              <span>最近活动</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivities.map((activity: any) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activity.title}</p>
                    <p className="text-xs text-gray-500">
                      {activity.user} · {activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pending Reviews */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5" />
              <span>待评审需求</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pendingReviews.map((review: any) => (
                <div key={review.id} className="border-l-4 border-blue-500 pl-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{review.title}</p>
                    <Badge 
                      variant={review.priority === 'high' ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
                      {review.priority === 'high' ? '高' : '中'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500">
                    评审人：{review.reviewer}
                  </p>
                  <p className="text-xs text-gray-500">
                    截止：{review.deadline}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Risk Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>风险预警</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {riskAlerts.map((alert: any) => (
                <div key={alert.id} className={`p-3 rounded-lg border-l-4 ${
                  alert.severity === 'high' 
                    ? 'bg-red-50 border-red-500' 
                    : 'bg-yellow-50 border-yellow-500'
                }`}>
                  <p className="text-sm font-medium">{alert.message}</p>
                  <Badge 
                    variant={alert.severity === 'high' ? 'destructive' : 'secondary'}
                    className="text-xs mt-1"
                  >
                    {alert.severity === 'high' ? '高风险' : '中风险'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

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

export default RequirementManagerDashboard;