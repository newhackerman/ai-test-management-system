import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Layers, 
  Database, 
  Shield, 
  Zap, 
  GitBranch, 
  AlertTriangle,
  Server,
  Cloud,
  Network,
  Code,
  TrendingUp,
  Activity,
  CheckCircle,
  Clock
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart, GaugeChart } from '@/components/dashboard/Widgets/Charts';

interface ArchitectureMetrics {
  systemHealth: number;
  performanceScore: number;
  securityScore: number;
  scalabilityIndex: number;
  technicalDebt: number;
  codeQuality: number;
  apiStability: number;
  infrastructureUtilization: number;
  systemComplexity: number;
  architectureCompliance: number;
  performanceTrends: Array<{
    date: string;
    response_time: number;
    throughput: number;
    error_rate: number;
  }>;
  securityTrends: Array<{
    date: string;
    vulnerabilities: number;
    patches: number;
    compliance: number;
  }>;
}

interface SystemComponent {
  id: number;
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  instances: number;
}

interface ArchitectureReview {
  id: number;
  title: string;
  reviewer: string;
  status: 'pending' | 'approved' | 'revision';
  priority: 'high' | 'medium' | 'low';
}

interface TechnicalTask {
  id: number;
  title: string;
  priority: 'high' | 'medium' | 'low';
  deadline: string;
  type: 'performance' | 'reliability' | 'security' | 'infrastructure';
}

interface SystemAlert {
  id: number;
  type: 'performance' | 'security' | 'capacity' | 'dependency';
  message: string;
  severity: 'high' | 'medium' | 'low';
}

const ArchitectDashboard: React.FC = () => {
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
  } = useDashboard('ARCHITECT');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [architectureMetrics, setArchitectureMetrics] = useState<ArchitectureMetrics>({
    systemHealth: 0,
    performanceScore: 0,
    securityScore: 0,
    scalabilityIndex: 0,
    technicalDebt: 0,
    codeQuality: 0,
    apiStability: 0,
    infrastructureUtilization: 0,
    systemComplexity: 0,
    architectureCompliance: 0,
    performanceTrends: [],
    securityTrends: []
  });

  const [systemComponents, setSystemComponents] = useState<SystemComponent[]>([]);
  const [architectureReviews, setArchitectureReviews] = useState<ArchitectureReview[]>([]);
  const [technicalTasks, setTechnicalTasks] = useState<TechnicalTask[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<SystemAlert[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['system_update', 'performance_update', 'security_update', 'architecture_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['system_update', 'performance_update', 'security_update', 'architecture_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockData: ArchitectureMetrics = {
      systemHealth: 94.2,
      performanceScore: 87.5,
      securityScore: 91.8,
      scalabilityIndex: 85.3,
      technicalDebt: 23.7,
      codeQuality: 89.4,
      apiStability: 96.1,
      infrastructureUtilization: 78.9,
      systemComplexity: 67.2,
      architectureCompliance: 92.6,
      performanceTrends: [
        { date: '1月', response_time: 120, throughput: 850, error_rate: 0.2 },
        { date: '2月', response_time: 115, throughput: 920, error_rate: 0.15 },
        { date: '3月', response_time: 110, throughput: 980, error_rate: 0.12 },
        { date: '4月', response_time: 108, throughput: 1050, error_rate: 0.1 }
      ],
      securityTrends: [
        { date: '1月', vulnerabilities: 12, patches: 10, compliance: 88 },
        { date: '2月', vulnerabilities: 8, patches: 8, compliance: 92 },
        { date: '3月', vulnerabilities: 5, patches: 5, compliance: 95 },
        { date: '4月', vulnerabilities: 3, patches: 3, compliance: 97 }
      ]
    };

    setArchitectureMetrics(mockData);

    setSystemComponents([
      { id: 1, name: '用户服务', status: 'healthy', cpu: 45, memory: 62, instances: 3 },
      { id: 2, name: '订单服务', status: 'warning', cpu: 78, memory: 85, instances: 5 },
      { id: 3, name: '支付服务', status: 'healthy', cpu: 32, memory: 48, instances: 2 },
      { id: 4, name: '通知服务', status: 'critical', cpu: 92, memory: 95, instances: 1 }
    ]);

    setArchitectureReviews([
      { id: 1, title: '微服务架构重构方案', reviewer: '技术总监', status: 'pending', priority: 'high' },
      { id: 2, title: '数据库分片策略', reviewer: 'DBA', status: 'approved', priority: 'medium' },
      { id: 3, title: 'API网关升级方案', reviewer: '运维团队', status: 'revision', priority: 'high' }
    ]);

    setTechnicalTasks([
      { id: 1, title: '优化数据库查询性能', priority: 'high', deadline: '今天', type: 'performance' },
      { id: 2, title: '实施服务熔断机制', priority: 'medium', deadline: '明天', type: 'reliability' },
      { id: 3, title: '更新安全策略文档', priority: 'low', deadline: '本周', type: 'security' },
      { id: 4, title: '容器化部署优化', priority: 'high', deadline: '2天后', type: 'infrastructure' }
    ]);

    setSystemAlerts([
      { id: 1, type: 'performance', message: '订单服务响应时间超过阈值', severity: 'high' },
      { id: 2, type: 'security', message: '检测到异常API调用模式', severity: 'medium' },
      { id: 3, type: 'capacity', message: '数据库连接池使用率过高', severity: 'high' },
      { id: 4, type: 'dependency', message: '第三方服务依赖不稳定', severity: 'medium' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-indigo-300 to-blue-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-indigo-600 to-blue-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">架构师仪表板</h1>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{architectureMetrics.systemHealth}%</div>
            <div className="text-indigo-100">系统健康度</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">性能评分</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {architectureMetrics.performanceScore}
                </p>
              </div>
              <Zap className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600 dark:text-green-400">
                优秀
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">安全评分</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {architectureMetrics.securityScore}
                </p>
              </div>
              <Shield className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600 dark:text-blue-400">
                高安全
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">可扩展性</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {architectureMetrics.scalabilityIndex}
                </p>
              </div>
              <Layers className="h-8 w-8 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600 dark:text-purple-400">
                良好
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">技术债务</p>
                <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {architectureMetrics.technicalDebt}%
                </p>
              </div>
              <Code className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600 dark:text-orange-400">
                可控范围
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>性能趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              data={architectureMetrics.performanceTrends}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['response_time', 'throughput'],
                showDataPoints: true,
                smoothCurve: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Security Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>安全趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={architectureMetrics.securityTrends}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['vulnerabilities', 'patches'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Components and Tasks Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Components */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-5 w-5" />
              <span>系统组件</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemComponents.map((component) => (
                <div key={component.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{component.name}</h4>
                    <Badge 
                      variant={
                        component.status === 'healthy' ? 'default' :
                        component.status === 'warning' ? 'secondary' : 'destructive'
                      }
                    >
                      {component.status === 'healthy' ? '健康' :
                       component.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">CPU: </span>
                      <span className={component.cpu > 80 ? 'text-red-600 dark:text-red-400' : component.cpu > 60 ? 'text-yellow-600' : 'text-green-600'}>
                        {component.cpu}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">内存: </span>
                      <span className={component.memory > 80 ? 'text-red-600 dark:text-red-400' : component.memory > 60 ? 'text-yellow-600' : 'text-green-600'}>
                        {component.memory}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">实例: </span>
                      <span>{component.instances}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Technical Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5" />
              <span>技术任务</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {technicalTasks.map((task) => (
                <div key={task.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    task.priority === 'high' ? 'bg-red-500' :
                    task.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{task.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {task.type === 'performance' ? '性能' :
                         task.type === 'reliability' ? '可靠性' :
                         task.type === 'security' ? '安全' : '基础设施'}
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

      {/* Architecture Reviews and Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Architecture Reviews */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5" />
              <span>架构评审</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {architectureReviews.map((review) => (
                <div key={review.id} className="border-l-4 border-indigo-500 pl-3">
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

        {/* System Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>系统告警</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemAlerts.map((alert) => (
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

export default ArchitectDashboard;
