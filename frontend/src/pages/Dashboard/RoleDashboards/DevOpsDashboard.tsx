import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Server, 
  Database, 
  Shield, 
  Zap, 
  GitBranch, 
  AlertTriangle,
  Activity,
  Cloud,
  Network,
  HardDrive,
  TrendingUp,
  CheckCircle,
  Clock,
  Cpu
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart, GaugeChart } from '@/components/dashboard/Widgets/Charts';

interface SystemMetrics {
  systemHealth: number;
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkTraffic: number;
  uptime: number;
  deploymentSuccess: number;
  errorRate: number;
  responseTime: number;
  throughput: number;
  performanceTrends: Array<{
    time: string;
    cpu: number;
    memory: number;
    network: number;
  }>;
  deploymentHistory: Array<{
    date: string;
    deployments: number;
    success: number;
    failures: number;
  }>;
}

interface ServiceStatus {
  id: number;
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  instances: number;
  uptime: string;
}

interface DeploymentTask {
  id: number;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: 'high' | 'medium' | 'low';
  environment: string;
  startTime?: string;
  duration?: string;
}

interface SystemAlert {
  id: number;
  type: 'performance' | 'security' | 'capacity' | 'deployment';
  message: string;
  severity: 'high' | 'medium' | 'low';
  timestamp: string;
}

const DevOpsDashboard: React.FC = () => {
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
  } = useDashboard('DEVOPS');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    systemHealth: 0,
    cpuUsage: 0,
    memoryUsage: 0,
    diskUsage: 0,
    networkTraffic: 0,
    uptime: 0,
    deploymentSuccess: 0,
    errorRate: 0,
    responseTime: 0,
    throughput: 0,
    performanceTrends: [],
    deploymentHistory: []
  });

  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [deploymentTasks, setDeploymentTasks] = useState<DeploymentTask[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<SystemAlert[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['system_update', 'deployment_update', 'performance_update', 'alert_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['system_update', 'deployment_update', 'performance_update', 'alert_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockMetrics: SystemMetrics = {
      systemHealth: 96.8,
      cpuUsage: 45.2,
      memoryUsage: 67.8,
      diskUsage: 34.5,
      networkTraffic: 78.9,
      uptime: 99.9,
      deploymentSuccess: 94.2,
      errorRate: 0.12,
      responseTime: 145,
      throughput: 1250,
      performanceTrends: [
        { time: '00:00', cpu: 35, memory: 60, network: 45 },
        { time: '04:00', cpu: 28, memory: 55, network: 38 },
        { time: '08:00', cpu: 52, memory: 72, network: 65 },
        { time: '12:00', cpu: 48, memory: 68, network: 78 },
        { time: '16:00', cpu: 45, memory: 67, network: 82 },
        { time: '20:00', cpu: 38, memory: 62, network: 58 }
      ],
      deploymentHistory: [
        { date: '周一', deployments: 12, success: 11, failures: 1 },
        { date: '周二', deployments: 8, success: 8, failures: 0 },
        { date: '周三', deployments: 15, success: 14, failures: 1 },
        { date: '周四', deployments: 10, success: 9, failures: 1 },
        { date: '周五', deployments: 18, success: 17, failures: 1 },
        { date: '周六', deployments: 5, success: 5, failures: 0 },
        { date: '周日', deployments: 3, success: 3, failures: 0 }
      ]
    };

    setSystemMetrics(mockMetrics);

    setServices([
      { id: 1, name: 'API网关', status: 'healthy', cpu: 25, memory: 45, instances: 3, uptime: '15天' },
      { id: 2, name: '用户服务', status: 'healthy', cpu: 35, memory: 62, instances: 5, uptime: '12天' },
      { id: 3, name: '订单服务', status: 'warning', cpu: 78, memory: 85, instances: 4, uptime: '8天' },
      { id: 4, name: '支付服务', status: 'healthy', cpu: 42, memory: 58, instances: 2, uptime: '20天' },
      { id: 5, name: '通知服务', status: 'critical', cpu: 92, memory: 95, instances: 1, uptime: '2天' },
      { id: 6, name: '数据库', status: 'healthy', cpu: 38, memory: 72, instances: 2, uptime: '45天' }
    ]);

    setDeploymentTasks([
      { id: 1, title: '用户服务v2.1.0部署', status: 'running', priority: 'high', environment: '生产环境', startTime: '14:30', duration: '5分钟' },
      { id: 2, title: '订单服务热修复', status: 'pending', priority: 'high', environment: '生产环境' },
      { id: 3, title: '支付服务功能更新', status: 'completed', priority: 'medium', environment: '测试环境', duration: '12分钟' },
      { id: 4, title: '数据库迁移脚本', status: 'pending', priority: 'low', environment: '预发布环境' },
      { id: 5, title: '监控系统升级', status: 'failed', priority: 'medium', environment: '开发环境' }
    ]);

    setSystemAlerts([
      { id: 1, type: 'performance', message: '订单服务CPU使用率超过80%', severity: 'high', timestamp: '2分钟前' },
      { id: 2, type: 'capacity', message: '通知服务内存使用率达到95%', severity: 'high', timestamp: '5分钟前' },
      { id: 3, type: 'deployment', message: '监控系统升级失败', severity: 'medium', timestamp: '10分钟前' },
      { id: 4, type: 'security', message: '检测到异常登录尝试', severity: 'medium', timestamp: '15分钟前' },
      { id: 5, type: 'performance', message: 'API响应时间略有上升', severity: 'low', timestamp: '30分钟前' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-green-300 to-blue-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-green-600 to-blue-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">运维仪表板</h1>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{systemMetrics.systemHealth}%</div>
            <div className="text-green-100">系统健康度</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">CPU使用率</p>
                <p className="text-2xl font-bold text-blue-600">
                  {systemMetrics.cpuUsage}%
                </p>
              </div>
              <Cpu className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                正常
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">内存使用率</p>
                <p className="text-2xl font-bold text-orange-600">
                  {systemMetrics.memoryUsage}%
                </p>
              </div>
              <HardDrive className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                注意
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">部署成功率</p>
                <p className="text-2xl font-bold text-green-600">
                  {systemMetrics.deploymentSuccess}%
                </p>
              </div>
              <GitBranch className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                优秀
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">系统可用性</p>
                <p className="text-2xl font-bold text-purple-600">
                  {systemMetrics.uptime}%
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                SLA达标
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
              <span>系统性能趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              data={systemMetrics.performanceTrends}
              config={{
                xAxisKey: 'time',
                yAxisKeys: ['cpu', 'memory', 'network'],
                showDataPoints: true,
                smoothCurve: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Deployment History */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5" />
              <span>部署历史</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={systemMetrics.deploymentHistory}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['success', 'failures'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Services and Tasks Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-5 w-5" />
              <span>服务状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {services.map((service) => (
                <div key={service.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{service.name}</h4>
                    <Badge 
                      variant={
                        service.status === 'healthy' ? 'default' :
                        service.status === 'warning' ? 'secondary' : 'destructive'
                      }
                    >
                      {service.status === 'healthy' ? '健康' :
                       service.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">CPU: </span>
                      <span className={service.cpu > 80 ? 'text-red-600' : service.cpu > 60 ? 'text-yellow-600' : 'text-green-600'}>
                        {service.cpu}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">内存: </span>
                      <span className={service.memory > 80 ? 'text-red-600' : service.memory > 60 ? 'text-yellow-600' : 'text-green-600'}>
                        {service.memory}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">实例: </span>
                      <span>{service.instances}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">运行时间: </span>
                      <span>{service.uptime}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Deployment Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Cloud className="h-5 w-5" />
              <span>部署任务</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {deploymentTasks.map((task) => (
                <div key={task.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    task.status === 'completed' ? 'bg-green-500' :
                    task.status === 'running' ? 'bg-blue-500 animate-pulse' :
                    task.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{task.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {task.environment}
                      </Badge>
                      <Badge 
                        variant={task.priority === 'high' ? 'destructive' : task.priority === 'medium' ? 'secondary' : 'outline'}
                        className="text-xs"
                      >
                        {task.priority === 'high' ? '高优先级' : task.priority === 'medium' ? '中优先级' : '低优先级'}
                      </Badge>
                      {task.startTime && (
                        <span className="text-xs text-gray-500">开始: {task.startTime}</span>
                      )}
                      {task.duration && (
                        <span className="text-xs text-gray-500">耗时: {task.duration}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

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
              <div key={alert.id} className={`p-4 rounded-lg border-l-4 ${
                alert.severity === 'high' 
                  ? 'bg-red-50 border-red-500' 
                  : alert.severity === 'medium'
                  ? 'bg-yellow-50 border-yellow-500'
                  : 'bg-blue-50 border-blue-500'
              }`}>
                <div className="flex items-center justify-between">
                  <p className="font-medium">{alert.message}</p>
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant={
                        alert.severity === 'high' ? 'destructive' : 
                        alert.severity === 'medium' ? 'secondary' : 'outline'
                      }
                      className="text-xs"
                    >
                      {alert.severity === 'high' ? '高' : alert.severity === 'medium' ? '中' : '低'}
                    </Badge>
                    <span className="text-xs text-gray-500">{alert.timestamp}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  类型: {
                    alert.type === 'performance' ? '性能' :
                    alert.type === 'security' ? '安全' :
                    alert.type === 'capacity' ? '容量' : '部署'
                  }
                </p>
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

export default DevOpsDashboard;
