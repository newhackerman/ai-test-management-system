import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Progress } from '@/components/ui/Progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/Alert';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  Calendar,
  Users,
  Cpu,
  BarChart3
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useToast } from '@/hooks/useToast';

interface CostSummary {
  period: string;
  period_start: string;
  period_end: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_response_time: number;
  success_rate: number;
  error_count: number;
}

interface BudgetUsage {
  budget_id: string;
  name: string;
  period: string;
  amount: number;
  currency: string;
  current_usage: number;
  usage_percentage: number;
  remaining: number;
  warning_threshold: number;
  critical_threshold: number;
  status: 'normal' | 'warning' | 'critical' | 'exceeded';
  period_start: string;
  period_end: string;
}

interface QuotaUsage {
  quota_id: string;
  name: string;
  period: string;
  token_limit: number | null;
  request_limit: number | null;
  current_tokens: number;
  current_requests: number;
  token_percentage: number;
  request_percentage: number;
  remaining_tokens: number | null;
  remaining_requests: number | null;
  status: 'normal' | 'warning' | 'critical' | 'exceeded';
  period_start: string;
  period_end: string;
}

interface Alert {
  alert_id: string;
  level: 'info' | 'warning' | 'critical' | 'emergency';
  message: string;
  provider?: string;
  user_id?: number;
  percentage?: number;
  timestamp: string;
}

interface ProviderStats {
  provider: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_response_time: number;
  success_rate: number;
  error_count: number;
}

interface TrendData {
  date: string;
  cost: number;
  tokens: number;
  requests: number;
}

interface DashboardData {
  cost_summary: CostSummary;
  budget_usage: {
    budgets: BudgetUsage[];
    total_budgets: number;
  };
  quota_usage: {
    quotas: QuotaUsage[];
    total_quotas: number;
  };
  recent_alerts: Alert[];
  provider_stats: {
    group_by: string;
    period: string;
    statistics: ProviderStats[];
  };
  user_stats?: {
    group_by: string;
    period: string;
    statistics: any[];
  };
}

interface TrendsData {
  period_days: number;
  start_date: string;
  end_date: string;
  trends: TrendData[];
  summary: {
    total_cost: number;
    total_tokens: number;
    total_requests: number;
    avg_daily_cost: number;
    avg_daily_tokens: number;
    avg_daily_requests: number;
  };
}

const CostMonitoringDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [trendsData, setTrendsData] = useState<TrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [period, setPeriod] = useState('daily');
  const [trendDays, setTrendDays] = useState(30);
  const { toast } = useToast();

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(`/api/v1/cost-control/dashboard?period=${period}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const result = await response.json();
      if (result.success) {
        setDashboardData(result.data);
      } else {
        throw new Error(result.message || 'Failed to fetch dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast({
        title: "错误",
        description: "获取仪表板数据失败",
        variant: "destructive",
      });
    }
  };

  const fetchTrendsData = async () => {
    try {
      const response = await fetch(`/api/v1/cost-control/trends?days=${trendDays}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch trends data');
      }

      const result = await response.json();
      if (result.success) {
        setTrendsData(result.data);
      } else {
        throw new Error(result.message || 'Failed to fetch trends data');
      }
    } catch (error) {
      console.error('Error fetching trends data:', error);
      toast({
        title: "错误",
        description: "获取趋势数据失败",
        variant: "destructive",
      });
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await Promise.all([fetchDashboardData(), fetchTrendsData()]);
    setRefreshing(false);
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboardData(), fetchTrendsData()]);
      setLoading(false);
    };

    loadData();
  }, [period, trendDays]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal':
        return 'bg-green-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'critical':
        return 'bg-orange-500 dark:bg-orange-900/20';
      case 'exceeded':
        return 'bg-red-500';
      default:
        return 'bg-gray-500 dark:bg-gray-800/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal':
        return <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'critical':
        return <AlertTriangle className="h-4 w-4 text-orange-500 dark:text-orange-400" />;
      case 'exceeded':
        return <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500 dark:text-gray-400" />;
    }
  };

  const getAlertVariant = (level: string) => {
    switch (level) {
      case 'critical':
      case 'emergency':
        return 'destructive';
      case 'warning':
        return 'default';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const formatPercentage = (percentage: number) => {
    return `${(percentage * 100).toFixed(1)}%`;
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">加载中...</span>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <p>无法加载仪表板数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">成本监控仪表板</h1>
          <p className="text-muted-foreground">AI服务成本和使用情况监控</p>
        </div>
        <div className="flex items-center space-x-4">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">日</SelectItem>
              <SelectItem value="weekly">周</SelectItem>
              <SelectItem value="monthly">月</SelectItem>
            </SelectContent>
          </Select>
          <Button
            onClick={refreshData}
            disabled={refreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Cost Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总成本</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(dashboardData.cost_summary.total_cost)}
            </div>
            <p className="text-xs text-muted-foreground">
              {period === 'daily' ? '今日' : period === 'weekly' ? '本周' : '本月'}消费
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总请求数</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(dashboardData.cost_summary.total_requests)}
            </div>
            <p className="text-xs text-muted-foreground">
              成功率: {formatPercentage(dashboardData.cost_summary.success_rate)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总Token数</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(dashboardData.cost_summary.total_tokens)}
            </div>
            <p className="text-xs text-muted-foreground">
              平均响应时间: {dashboardData.cost_summary.avg_response_time.toFixed(2)}s
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">错误数</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {formatNumber(dashboardData.cost_summary.error_count)}
            </div>
            <p className="text-xs text-muted-foreground">
              错误率: {formatPercentage(1 - dashboardData.cost_summary.success_rate)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Alerts */}
      {dashboardData.recent_alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>最近告警</CardTitle>
            <CardDescription>系统最近的成本和配额告警</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dashboardData.recent_alerts.slice(0, 5).map((alert) => (
                <Alert key={alert.alert_id} variant={getAlertVariant(alert.level)}>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle className="flex items-center justify-between">
                    <span>{alert.level.toUpperCase()}</span>
                    <Badge variant="outline">
                      {new Date(alert.timestamp).toLocaleString()}
                    </Badge>
                  </AlertTitle>
                  <AlertDescription>{alert.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="budgets" className="space-y-4">
        <TabsList>
          <TabsTrigger value="budgets">预算使用</TabsTrigger>
          <TabsTrigger value="quotas">配额使用</TabsTrigger>
          <TabsTrigger value="providers">提供商统计</TabsTrigger>
          <TabsTrigger value="trends">成本趋势</TabsTrigger>
        </TabsList>

        {/* Budget Usage Tab */}
        <TabsContent value="budgets" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {dashboardData.budget_usage.budgets.map((budget) => (
              <Card key={budget.budget_id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{budget.name}</span>
                    {getStatusIcon(budget.status)}
                  </CardTitle>
                  <CardDescription>
                    {budget.period} 预算 • {budget.currency}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span>已使用</span>
                        <span>{formatPercentage(budget.usage_percentage)}</span>
                      </div>
                      <Progress 
                        value={budget.usage_percentage * 100} 
                        className="h-2"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">已使用</p>
                        <p className="font-medium">{formatCurrency(budget.current_usage, budget.currency)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">剩余</p>
                        <p className="font-medium">{formatCurrency(budget.remaining, budget.currency)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">总预算</p>
                        <p className="font-medium">{formatCurrency(budget.amount, budget.currency)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">状态</p>
                        <Badge className={getStatusColor(budget.status)}>
                          {budget.status}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Quota Usage Tab */}
        <TabsContent value="quotas" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {dashboardData.quota_usage.quotas.map((quota) => (
              <Card key={quota.quota_id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{quota.name}</span>
                    {getStatusIcon(quota.status)}
                  </CardTitle>
                  <CardDescription>
                    {quota.period} 配额
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {quota.token_limit && (
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Token使用率</span>
                          <span>{formatPercentage(quota.token_percentage)}</span>
                        </div>
                        <Progress 
                          value={quota.token_percentage * 100} 
                          className="h-2"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground mt-1">
                          <span>{formatNumber(quota.current_tokens)} / {formatNumber(quota.token_limit)}</span>
                          <span>剩余: {formatNumber(quota.remaining_tokens || 0)}</span>
                        </div>
                      </div>
                    )}
                    {quota.request_limit && (
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>请求使用率</span>
                          <span>{formatPercentage(quota.request_percentage)}</span>
                        </div>
                        <Progress 
                          value={quota.request_percentage * 100} 
                          className="h-2"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground mt-1">
                          <span>{formatNumber(quota.current_requests)} / {formatNumber(quota.request_limit)}</span>
                          <span>剩余: {formatNumber(quota.remaining_requests || 0)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Provider Statistics Tab */}
        <TabsContent value="providers" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Provider Cost Chart */}
            <Card>
              <CardHeader>
                <CardTitle>提供商成本分布</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={dashboardData.provider_stats.statistics}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ provider, total_cost }) => `${provider}: ${formatCurrency(total_cost)}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="total_cost"
                    >
                      {dashboardData.provider_stats.statistics.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Provider Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle>提供商性能对比</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dashboardData.provider_stats.statistics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="provider" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="avg_response_time" fill="#8884d8" name="平均响应时间(s)" />
                    <Bar dataKey="success_rate" fill="#82ca9d" name="成功率" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Provider Details Table */}
          <Card>
            <CardHeader>
              <CardTitle>提供商详细统计</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">提供商</th>
                      <th className="text-right p-2">总成本</th>
                      <th className="text-right p-2">请求数</th>
                      <th className="text-right p-2">Token数</th>
                      <th className="text-right p-2">成功率</th>
                      <th className="text-right p-2">平均响应时间</th>
                      <th className="text-right p-2">错误数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData.provider_stats.statistics.map((stat) => (
                      <tr key={stat.provider} className="border-b">
                        <td className="p-2 font-medium">{stat.provider}</td>
                        <td className="p-2 text-right">{formatCurrency(stat.total_cost)}</td>
                        <td className="p-2 text-right">{formatNumber(stat.total_requests)}</td>
                        <td className="p-2 text-right">{formatNumber(stat.total_tokens)}</td>
                        <td className="p-2 text-right">{formatPercentage(stat.success_rate)}</td>
                        <td className="p-2 text-right">{stat.avg_response_time.toFixed(2)}s</td>
                        <td className="p-2 text-right text-red-600 dark:text-red-400">{formatNumber(stat.error_count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cost Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">成本趋势分析</h3>
            <Select value={trendDays.toString()} onValueChange={(value) => setTrendDays(Number(value))}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7天</SelectItem>
                <SelectItem value="30">30天</SelectItem>
                <SelectItem value="90">90天</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {trendsData && (
            <>
              {/* Trend Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">总成本</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatCurrency(trendsData.summary.total_cost)}</div>
                    <p className="text-xs text-muted-foreground">
                      日均: {formatCurrency(trendsData.summary.avg_daily_cost)}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">总请求数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatNumber(trendsData.summary.total_requests)}</div>
                    <p className="text-xs text-muted-foreground">
                      日均: {formatNumber(Math.round(trendsData.summary.avg_daily_requests))}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">总Token数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{formatNumber(trendsData.summary.total_tokens)}</div>
                    <p className="text-xs text-muted-foreground">
                      日均: {formatNumber(Math.round(trendsData.summary.avg_daily_tokens))}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Trend Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>成本趋势</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={trendsData.trends}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="date" 
                          tickFormatter={(value) => new Date(value).toLocaleDateString()}
                        />
                        <YAxis tickFormatter={(value) => `$${value}`} />
                        <Tooltip 
                          labelFormatter={(value) => new Date(value).toLocaleDateString()}
                          formatter={(value) => [formatCurrency(Number(value)), '成本']}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="cost" 
                          stroke="#8884d8" 
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>请求量趋势</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={trendsData.trends}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="date" 
                          tickFormatter={(value) => new Date(value).toLocaleDateString()}
                        />
                        <YAxis />
                        <Tooltip 
                          labelFormatter={(value) => new Date(value).toLocaleDateString()}
                          formatter={(value) => [formatNumber(Number(value)), '请求数']}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="requests" 
                          stroke="#82ca9d" 
                          strokeWidth={2}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CostMonitoringDashboard;