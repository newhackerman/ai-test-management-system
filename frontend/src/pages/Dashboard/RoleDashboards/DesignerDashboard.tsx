import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Palette, 
  Layout, 
  Users, 
  Clock, 
  CheckCircle, 
  AlertTriangle,
  Figma,
  Smartphone,
  Monitor,
  Eye,
  MessageCircle,
  TrendingUp
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

const DesignerDashboard: React.FC = () => {
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
  } = useDashboard('DESIGNER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [designMetrics, setDesignMetrics] = useState({
    totalDesigns: 0,
    completedDesigns: 0,
    inProgressDesigns: 0,
    reviewPendingDesigns: 0,
    designQualityScore: 0,
    userFeedbackScore: 0,
    designSystemUsage: 0,
    prototypingProgress: 0,
    accessibilityScore: 0,
    designDeliveryRate: [] as Array<{ month: string; designs: number; prototypes: number; }>
  });

  const [recentProjects, setRecentProjects] = useState<Array<any>>([]);
  const [designReviews, setDesignReviews] = useState<Array<any>>([]);
  const [designTasks, setDesignTasks] = useState<Array<any>>([]);
  const [feedbackAlerts, setFeedbackAlerts] = useState<Array<any>>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['design_update', 'review_update', 'feedback_update', 'prototype_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['design_update', 'review_update', 'feedback_update', 'prototype_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockData = {
      totalDesigns: 48,
      completedDesigns: 32,
      inProgressDesigns: 12,
      reviewPendingDesigns: 4,
      designQualityScore: 92.5,
      userFeedbackScore: 88.3,
      designSystemUsage: 85.7,
      prototypingProgress: 76.2,
      accessibilityScore: 91.8,
      designDeliveryRate: [
        { month: '1月', designs: 8, prototypes: 6 },
        { month: '2月', designs: 12, prototypes: 9 },
        { month: '3月', designs: 15, prototypes: 12 },
        { month: '4月', designs: 13, prototypes: 11 }
      ]
    };

    setDesignMetrics(mockData);

    setRecentProjects([
      { id: 1, name: '移动端用户界面重设计', progress: 85, status: 'in_progress', deadline: '2024-01-20' },
      { id: 2, name: '管理后台界面优化', progress: 100, status: 'completed', deadline: '2024-01-15' },
      { id: 3, name: '品牌视觉系统升级', progress: 45, status: 'in_progress', deadline: '2024-01-25' },
      { id: 4, name: '用户体验流程设计', progress: 20, status: 'planning', deadline: '2024-02-01' }
    ]);

    setDesignReviews([
      { id: 1, title: '登录页面设计', reviewer: '产品经理', status: 'pending', priority: 'high' },
      { id: 2, title: '数据可视化组件', reviewer: '前端开发', status: 'approved', priority: 'medium' },
      { id: 3, title: '移动端导航设计', reviewer: 'UX专家', status: 'revision', priority: 'high' }
    ]);

    setDesignTasks([
      { id: 1, title: '完成用户头像组件设计', priority: 'high', deadline: '今天', type: 'component' },
      { id: 2, title: '制作交互原型', priority: 'medium', deadline: '明天', type: 'prototype' },
      { id: 3, title: '更新设计规范文档', priority: 'low', deadline: '本周', type: 'documentation' },
      { id: 4, title: '响应式布局适配', priority: 'high', deadline: '2天后', type: 'responsive' }
    ]);

    setFeedbackAlerts([
      { id: 1, type: 'user_feedback', message: '用户反馈：导航不够直观', severity: 'medium' },
      { id: 2, type: 'accessibility', message: '颜色对比度需要提升', severity: 'high' },
      { id: 3, type: 'performance', message: '图片加载速度较慢', severity: 'low' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-purple-300 to-pink-400 rounded-lg h-32"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-300 rounded-lg h-24 dark:bg-gray-500"></div>
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
            <div className="text-red-500 mb-4 dark:text-red-400">
              <AlertTriangle className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold mb-2">加载失败</h3>
            <p className="text-gray-600 mb-4 dark:text-gray-400">{error}</p>
            <Button onClick={() => window.location.reload()}>
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen dark:bg-gray-800/50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">设计师仪表板</h1>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{designMetrics.totalDesigns}</div>
            <div className="text-purple-100">设计项目</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">设计质量</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {designMetrics.designQualityScore}
                </p>
              </div>
              <Palette className="h-8 w-8 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600 dark:text-purple-400">
                优秀
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">用户反馈</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {designMetrics.userFeedbackScore}
                </p>
              </div>
              <Eye className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600 dark:text-green-400">
                +3.2% 本周
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">设计系统使用率</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {designMetrics.designSystemUsage}%
                </p>
              </div>
              <Layout className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600 dark:text-blue-400">
                高使用率
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">无障碍评分</p>
                <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {designMetrics.accessibilityScore}
                </p>
              </div>
              <Users className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600 dark:text-orange-400">
                AA级
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Design Progress */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>设计交付趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={designMetrics.designDeliveryRate}
              config={{
                xAxisKey: 'month',
                yAxisKeys: ['designs', 'prototypes'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Design Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Layout className="h-5 w-5" />
              <span>设计状态分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PieChart
              data={[
                { name: '已完成', value: designMetrics.completedDesigns },
                { name: '进行中', value: designMetrics.inProgressDesigns },
                { name: '待评审', value: designMetrics.reviewPendingDesigns }
              ]}
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
      </div>

      {/* Projects and Tasks Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Projects */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Figma className="h-5 w-5" />
              <span>最近项目</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentProjects.map((project: any) => (
                <div key={project.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{project.name}</h4>
                    <Badge 
                      variant={
                        project.status === 'completed' ? 'default' :
                        project.status === 'in_progress' ? 'secondary' : 'outline'
                      }
                    >
                      {project.status === 'completed' ? '已完成' :
                       project.status === 'in_progress' ? '进行中' : '计划中'}
                    </Badge>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2 dark:bg-gray-600">
                    <div 
                      className="bg-purple-600 h-2 rounded-full" 
                      style={{ width: `${project.progress}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
                    <span>{project.progress}% 完成</span>
                    <span>截止：{project.deadline}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Design Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-5 w-5" />
              <span>设计任务</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {designTasks.map((task: any) => (
                <div key={task.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    task.priority === 'high' ? 'bg-red-500' :
                    task.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{task.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {task.type === 'component' ? '组件' :
                         task.type === 'prototype' ? '原型' :
                         task.type === 'documentation' ? '文档' : '响应式'}
                      </Badge>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{task.deadline}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Reviews and Feedback Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Design Reviews */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5" />
              <span>设计评审</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {designReviews.map((review: any) => (
                <div key={review.id} className="border-l-4 border-purple-500 pl-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{review.title}</p>
                    <Badge 
                      variant={
                        review.status === 'approved' ? 'default' :
                        review.status === 'pending' ? 'secondary' : 'destructive'
                      }
                    >
                      {review.status === 'approved' ? '已通过' :
                       review.status === 'pending' ? '待评审' : '需修改'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    评审人：{review.reviewer}
                  </p>
                  <Badge 
                    variant={review.priority === 'high' ? 'destructive' : 'secondary'}
                    className="text-xs mt-1"
                  >
                    {review.priority === 'high' ? '高优先级' : '中优先级'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Feedback Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>反馈提醒</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {feedbackAlerts.map((alert: any) => (
                <div key={alert.id} className={`p-3 rounded-lg border-l-4 ${
                  alert.severity === 'high' 
                    ? 'bg-red-50 border-red-500 dark:bg-red-900/20' 
                    : alert.severity === 'medium'
                    ? 'bg-yellow-50 border-yellow-500'
                    : 'bg-blue-50 border-blue-500 dark:bg-blue-900/20'
                }`}>
                  <p className="text-sm font-medium">{alert.message}</p>
                  <Badge 
                    variant={
                      alert.severity === 'high' ? 'destructive' : 
                      alert.severity === 'medium' ? 'secondary' : 'outline'
                    }
                    className="text-xs mt-1"
                  >
                    {alert.severity === 'high' ? '高优先级' : 
                     alert.severity === 'medium' ? '中优先级' : '低优先级'}
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

export default DesignerDashboard;
