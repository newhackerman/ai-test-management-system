import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Users, 
  Settings, 
  Shield, 
  Activity, 
  Database, 
  AlertTriangle,
  TrendingUp,
  Server,
  BarChart3,
  CheckCircle,
  Clock,
  Eye
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

interface SystemOverview {
  totalUsers: number;
  activeUsers: number;
  totalProjects: number;
  systemHealth: number;
  storageUsage: number;
  apiCalls: number;
  errorRate: number;
  uptime: number;
  userGrowth: Array<{
    month: string;
    users: number;
    active: number;
  }>;
  systemMetrics: Array<{
    time: string;
    cpu: number;
    memory: number;
    requests: number;
  }>;
}

interface UserActivity {
  id: number;
  username: string;
  action: string;
  timestamp: string;
  ip: string;
  status: 'success' | 'warning' | 'error';
}

interface SystemAlert {
  id: number;
  type: 'security' | 'performance' | 'system' | 'user';
  message: string;
  severity: 'high' | 'medium' | 'low';
  timestamp: string;
}

interface ModuleStatus {
  id: number;
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  uptime: number;
  lastCheck: string;
  users: number;
}

const AdminDashboard: React.FC = () => {
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
  } = useDashboard('ADMIN');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [systemOverview, setSystemOverview] = useState<SystemOverview>({
    totalUsers: 0,
    activeUsers: 0,
    totalProjects: 0,
    systemHealth: 0,
    storageUsage: 0,
    apiCalls: 0,
    errorRate: 0,
    uptime: 0,
    userGrowth: [],
    systemMetrics: []
  });

  const [userActivities, setUserActivities] = useState<UserActivity[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<SystemAlert[]>([]);
  const [moduleStatus, setModuleStatus] = useState<ModuleStatus[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['system_update', 'user_update', 'security_update', 'performance_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['system_update', 'user_update', 'security_update', 'performance_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockOverview: SystemOverview = {
      totalUsers: 1247,
      activeUsers: 892,
      totalProjects: 156,
      systemHealth: 98.5,
      storageUsage: 67.3,
      apiCalls: 125847,
      errorRate: 0.08,
      uptime: 99.97,
      userGrowth: [
        { month: '1月', users: 980, active: 720 },
        { month: '2月', users: 1050, active: 780 },
        { month: '3月', users: 1120, active: 820 },
        { month: '4月', users: 1200, active: 860 },
        { month: '5月', users: 1247, active: 892 }
      ],
      systemMetrics: [
        { time: '00:00', cpu: 25, memory: 45, requests: 1200 },
        { time: '04:00', cpu: 18, memory: 38, requests: 800 },
        { time: '08:00', cpu: 45, memory: 62, requests: 2100 },
        { time: '12:00', cpu: 52, memory: 68, requests: 2800 },
        { time: '16:00', cpu: 48, memory: 65, requests: 2500 },
        { time: '20:00', cpu: 35, memory: 55, requests: 1800 }
      ]
    };

    setSystemOverview(mockOverview);

    setUserActivities([
      { id: 1, username: '张三', action: '登录系统', timestamp: '2分钟前', ip: '192.168.1.100', status: 'success' },
      { id: 2, username: '李四', action: '创建项目', timestamp: '5分钟前', ip: '192.168.1.101', status: 'success' },
      { id: 3, username: '王五', action: '修改用户权限', timestamp: '10分钟前', ip: '192.168.1.102', status: 'warning' },
      { id: 4, username: '赵六', action: '删除文件', timestamp: '15分钟前', ip: '192.168.1.103', status: 'success' },
      { id: 5, username: '钱七', action: '登录失败', timestamp: '20分钟前', ip: '192.168.1.104', status: 'error' }
    ]);

    setSystemAlerts([
      { id: 1, type: 'security', message: '检测到异常登录尝试', severity: 'high', timestamp: '5分钟前' },
      { id: 2, type: 'performance', message: '数据库响应时间超过阈值', severity: 'medium', timestamp: '10分钟前' },
      { id: 3, type: 'system', message: '存储空间使用率达到70%', severity: 'medium', timestamp: '30分钟前' },
      { id: 4, type: 'user', message: '用户并发数创新高', severity: 'low', timestamp: '1小时前' }
    ]);

    setModuleStatus([
      { id: 1, name: '用户管理', status: 'healthy', uptime: 99.9, lastCheck: '1分钟前', users: 892 },
      { id: 2, name: '项目管理', status: 'healthy', uptime: 99.8, lastCheck: '1分钟前', users: 456 },
      { id: 3, name: '需求管理', status: 'warning', uptime: 98.5, lastCheck: '2分钟前', users: 234 },
      { id: 4, name: '测试管理', status: 'healthy', uptime: 99.7, lastCheck: '1分钟前', users: 178 },
      { id: 5, name: 'AI助手', status: 'healthy', uptime: 99.6, lastCheck: '1分钟前', users: 345 },
      { id: 6, name: '仪表板', status: 'healthy', uptime: 99.9, lastCheck: '30秒前', users: 567 }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-blue-300 to-indigo-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">系统管理仪表板</h1>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{systemOverview.systemHealth}%</div>
            <div className="text-blue-100">系统健康度</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">总用户数</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {systemOverview.totalUsers.toLocaleString()}
                </p>
              </div>
              <Users className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600 dark:text-blue-400">
                活跃: {systemOverview.activeUsers}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">项目总数</p>
                <p className="text-2xl font-bold text-green-600">
                  {systemOverview.totalProjects}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                +12 本月
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">API调用量</p>
                <p className="text-2xl font-bold text-purple-600">
                  {(systemOverview.apiCalls / 1000).toFixed(1)}K
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                今日
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">系统可用性</p>
                <p className="text-2xl font-bold text-orange-600">
                  {systemOverview.uptime}%
                </p>
              </div>
              <Server className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                SLA达标
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Growth */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>用户增长趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              data={systemOverview.userGrowth}
              config={{
                xAxisKey: 'month',
                yAxisKeys: ['users', 'active'],
                showDataPoints: true,
                smoothCurve: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* System Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>系统性能指标</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart
              data={systemOverview.systemMetrics}
              config={{
                xAxisKey: 'time',
                yAxisKeys: ['cpu', 'memory'],
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

      {/* Module Status and Activities Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>模块状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {moduleStatus.map((module) => (
                <div key={module.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      module.status === 'healthy' ? 'bg-green-500' :
                      module.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <p className="font-medium text-sm">{module.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        可用性: {module.uptime}% | 用户: {module.users}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge 
                      variant={
                        module.status === 'healthy' ? 'default' :
                        module.status === 'warning' ? 'secondary' : 'destructive'
                      }
                      className="text-xs"
                    >
                      {module.status === 'healthy' ? '正常' :
                       module.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1 dark:text-gray-400">{module.lastCheck}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* User Activities */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Eye className="h-5 w-5" />
              <span>用户活动</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {userActivities.map((activity) => (
                <div key={activity.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    activity.status === 'success' ? 'bg-green-500' :
                    activity.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{activity.username} - {activity.action}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">IP: {activity.ip}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{activity.timestamp}</span>
                    </div>
                  </div>
                  <Badge 
                    variant={
                      activity.status === 'success' ? 'default' :
                      activity.status === 'warning' ? 'secondary' : 'destructive'
                    }
                    className="text-xs"
                  >
                    {activity.status === 'success' ? '成功' :
                     activity.status === 'warning' ? '警告' : '失败'}
                  </Badge>
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
                  ? 'bg-red-50 border-red-500 dark:bg-red-900/20' 
                  : alert.severity === 'medium'
                  ? 'bg-yellow-50 border-yellow-500'
                  : 'bg-blue-50 border-blue-500 dark:bg-blue-900/20'
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
                    <span className="text-xs text-gray-500 dark:text-gray-400">{alert.timestamp}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mt-1 dark:text-gray-400">
                  类型: {
                    alert.type === 'security' ? '安全' :
                    alert.type === 'performance' ? '性能' :
                    alert.type === 'system' ? '系统' : '用户'
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

export default AdminDashboard;
