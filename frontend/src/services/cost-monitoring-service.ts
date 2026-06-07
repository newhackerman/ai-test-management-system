import { apiClient } from '@/lib/api-client';

export interface CostSummary {
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

export interface BudgetUsage {
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

export interface QuotaUsage {
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

export interface Alert {
  alert_id: string;
  level: 'info' | 'warning' | 'critical' | 'emergency';
  message: string;
  provider?: string;
  user_id?: number;
  percentage?: number;
  timestamp: string;
}

export interface ProviderStats {
  provider: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_response_time: number;
  success_rate: number;
  error_count: number;
}

export interface UserStats {
  user_id: number;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_response_time: number;
  success_rate: number;
  error_count: number;
}

export interface ModelStats {
  model: string;
  provider: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_response_time: number;
  success_rate: number;
  error_count: number;
}

export interface DashboardData {
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
    statistics: UserStats[];
  };
}

export interface TrendData {
  date: string;
  cost: number;
  tokens: number;
  requests: number;
}

export interface TrendsData {
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

export interface StatisticsData {
  group_by: string;
  period: string;
  statistics: ProviderStats[] | UserStats[] | ModelStats[];
}

export interface BudgetUsageData {
  budgets: BudgetUsage[];
  total_budgets: number;
}

export interface QuotaUsageData {
  quotas: QuotaUsage[];
  total_quotas: number;
}

export interface Budget {
  budget_id: string;
  name: string;
  period: string;
  amount: number;
  currency: string;
  providers: string[];
  users: number[];
  departments: string[];
  warning_threshold: number;
  critical_threshold: number;
  auto_disable_on_exceed: boolean;
  allow_overage: boolean;
  overage_limit: number;
}

export interface Quota {
  quota_id: string;
  name: string;
  period: string;
  token_limit: number | null;
  request_limit: number | null;
  providers: string[];
  users: number[];
  departments: string[];
  auto_reset: boolean;
  grace_period_minutes: number;
}

export class CostMonitoringService {
  private baseUrl = '/api/v1/cost-control';

  /**
   * 获取成本监控仪表板数据
   */
  async getDashboardData(period: string = 'daily'): Promise<DashboardData> {
    const response = await apiClient.get(`${this.baseUrl}/dashboard`, {
      params: { period }
    });
    return response.data;
  }

  /**
   * 获取成本摘要
   */
  async getCostSummary(
    period: string = 'daily',
    provider?: string,
    userId?: number
  ): Promise<CostSummary> {
    const response = await apiClient.get(`${this.baseUrl}/summary`, {
      params: { period, provider, user_id: userId }
    });
    return response.data;
  }

  /**
   * 获取成本趋势数据
   */
  async getCostTrends(
    days: number = 30,
    provider?: string,
    userId?: number
  ): Promise<TrendsData> {
    const response = await apiClient.get(`${this.baseUrl}/trends`, {
      params: { days, provider, user_id: userId }
    });
    return response.data;
  }

  /**
   * 获取使用统计数据
   */
  async getUsageStatistics(
    period: string = 'daily',
    groupBy: string = 'provider'
  ): Promise<StatisticsData> {
    const response = await apiClient.get(`${this.baseUrl}/statistics`, {
      params: { period, group_by: groupBy }
    });
    return response.data;
  }

  /**
   * 获取预算使用情况
   */
  async getBudgetUsage(budgetId?: string): Promise<BudgetUsageData> {
    const response = await apiClient.get(`${this.baseUrl}/budget-usage`, {
      params: { budget_id: budgetId }
    });
    return response.data;
  }

  /**
   * 获取配额使用情况
   */
  async getQuotaUsage(quotaId?: string): Promise<QuotaUsageData> {
    const response = await apiClient.get(`${this.baseUrl}/quota-usage`, {
      params: { quota_id: quotaId }
    });
    return response.data;
  }

  /**
   * 获取成本告警
   */
  async getCostAlerts(level?: string, limit: number = 100): Promise<Alert[]> {
    const response = await apiClient.get(`${this.baseUrl}/alerts`, {
      params: { level, limit }
    });
    return response.data;
  }

  /**
   * 获取预算配置列表
   */
  async getBudgets(): Promise<Budget[]> {
    const response = await apiClient.get(`${this.baseUrl}/budgets`);
    return response.data;
  }

  /**
   * 获取配额配置列表
   */
  async getQuotas(): Promise<Quota[]> {
    const response = await apiClient.get(`${this.baseUrl}/quotas`);
    return response.data;
  }

  /**
   * 创建预算配置
   */
  async createBudget(budgetData: Partial<Budget>): Promise<{ budget_id: string }> {
    const response = await apiClient.post(`${this.baseUrl}/budgets`, budgetData);
    return response.data;
  }

  /**
   * 创建配额配置
   */
  async createQuota(quotaData: Partial<Quota>): Promise<{ quota_id: string }> {
    const response = await apiClient.post(`${this.baseUrl}/quotas`, quotaData);
    return response.data;
  }

  /**
   * 删除预算配置
   */
  async deleteBudget(budgetId: string): Promise<{ budget_id: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/budgets/${budgetId}`);
    return response.data;
  }

  /**
   * 删除配额配置
   */
  async deleteQuota(quotaId: string): Promise<{ quota_id: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/quotas/${quotaId}`);
    return response.data;
  }

  /**
   * 检查成本和配额限制
   */
  async checkCostLimits(checkData: {
    provider: string;
    estimated_cost: number;
    estimated_tokens?: number;
    user_id?: number;
  }): Promise<{
    allowed: boolean;
    budget_allowed: boolean;
    quota_allowed: boolean;
    alerts: Alert[];
  }> {
    const response = await apiClient.post(`${this.baseUrl}/check`, checkData);
    return response.data;
  }

  /**
   * 记录使用情况
   */
  async recordUsage(usageData: {
    provider: string;
    user_id?: number;
    input_tokens: number;
    output_tokens: number;
    cost: number;
    response_time: number;
    success?: boolean;
  }): Promise<{ recorded: boolean }> {
    const response = await apiClient.post(`${this.baseUrl}/usage`, usageData);
    return response.data;
  }

  /**
   * 清除告警历史
   */
  async clearAlerts(before?: string): Promise<{ cleared_count: number }> {
    const response = await apiClient.delete(`${this.baseUrl}/alerts`, {
      params: { before }
    });
    return response.data;
  }
}

// 导出单例实例
export const costMonitoringService = new CostMonitoringService();