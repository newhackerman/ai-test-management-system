/**
 * 使用统计服务 - 提供增强的AI服务使用统计API
 */

export interface TimeSeriesPoint {
  timestamp: string;
  requests: number;
  tokens: number;
  cost: number;
  response_time: number;
  success_rate: number;
  concurrent_users: number;
  error_count: number;
}

export interface ModelUsageMetrics {
  model: string;
  provider: string;
  requests: number;
  tokens: number;
  cost: number;
  avg_response_time: number;
  success_rate: number;
  popularity_score: number;
  avg_tokens_per_request: number;
  peak_hour: number;
  error_rate: number;
}

export interface UserActivityMetrics {
  user_id: number;
  username: string;
  department?: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_session_duration: number;
  most_used_model: string;
  activity_score: number;
  last_active?: string;
  favorite_providers: string[];
}

export interface PerformanceMetrics {
  period: string;
  avg_response_time: number;
  p50_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
  throughput: number;
  error_rate: number;
  availability: number;
  peak_concurrent_users: number;
  total_uptime: number;
}

export interface UsagePattern {
  pattern_type: string;
  peak_hours: number[];
  low_usage_hours: number[];
  usage_distribution: Record<string, number>;
  seasonal_trends: Record<string, number>;
}

export interface TimeSeriesResponse {
  time_range: string;
  granularity: string;
  data_points: number;
  time_series: TimeSeriesPoint[];
}

export interface ModelMetricsResponse {
  period: string;
  total_models: number;
  model_metrics: ModelUsageMetrics[];
}

export interface UserActivityResponse {
  period: string;
  total_users: number;
  user_metrics: UserActivityMetrics[];
}

export interface ExportRequest {
  format: 'json' | 'csv' | 'excel';
  period: 'daily' | 'weekly' | 'monthly';
  include_details: boolean;
}

class UsageStatisticsService {
  private baseUrl = '/api/v1/cost-control/enhanced-statistics';

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    if (!result.success) {
      throw new Error(result.message || 'API request failed');
    }

    return result.data;
  }

  /**
   * 获取时间序列使用统计
   */
  async getTimeSeriesData(params: {
    time_range?: string;
    granularity?: string;
    provider?: string;
    user_id?: number;
  } = {}): Promise<TimeSeriesResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.time_range) searchParams.append('time_range', params.time_range);
    if (params.granularity) searchParams.append('granularity', params.granularity);
    if (params.provider) searchParams.append('provider', params.provider);
    if (params.user_id) searchParams.append('user_id', params.user_id.toString());

    const queryString = searchParams.toString();
    const endpoint = `/time-series${queryString ? `?${queryString}` : ''}`;
    
    return this.request<TimeSeriesResponse>(endpoint);
  }

  /**
   * 获取模型使用指标
   */
  async getModelUsageMetrics(params: {
    period?: string;
    limit?: number;
  } = {}): Promise<ModelMetricsResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.period) searchParams.append('period', params.period);
    if (params.limit) searchParams.append('limit', params.limit.toString());

    const queryString = searchParams.toString();
    const endpoint = `/model-metrics${queryString ? `?${queryString}` : ''}`;
    
    return this.request<ModelMetricsResponse>(endpoint);
  }

  /**
   * 获取用户活动指标
   */
  async getUserActivityMetrics(params: {
    period?: string;
    limit?: number;
  } = {}): Promise<UserActivityResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.period) searchParams.append('period', params.period);
    if (params.limit) searchParams.append('limit', params.limit.toString());

    const queryString = searchParams.toString();
    const endpoint = `/user-activity${queryString ? `?${queryString}` : ''}`;
    
    return this.request<UserActivityResponse>(endpoint);
  }

  /**
   * 获取性能指标
   */
  async getPerformanceMetrics(params: {
    period?: string;
  } = {}): Promise<PerformanceMetrics> {
    const searchParams = new URLSearchParams();
    
    if (params.period) searchParams.append('period', params.period);

    const queryString = searchParams.toString();
    const endpoint = `/performance${queryString ? `?${queryString}` : ''}`;
    
    return this.request<PerformanceMetrics>(endpoint);
  }

  /**
   * 获取使用模式分析
   */
  async getUsagePatterns(params: {
    pattern_type?: string;
    period?: string;
  } = {}): Promise<UsagePattern> {
    const searchParams = new URLSearchParams();
    
    if (params.pattern_type) searchParams.append('pattern_type', params.pattern_type);
    if (params.period) searchParams.append('period', params.period);

    const queryString = searchParams.toString();
    const endpoint = `/usage-patterns${queryString ? `?${queryString}` : ''}`;
    
    return this.request<UsagePattern>(endpoint);
  }

  /**
   * 导出使用统计数据
   */
  async exportUsageData(exportRequest: ExportRequest): Promise<any> {
    return this.request('/export', {
      method: 'POST',
      body: JSON.stringify(exportRequest),
    });
  }

  /**
   * 获取统计摘要
   */
  async getStatisticsSummary(period: string = 'daily'): Promise<{
    total_requests: number;
    total_tokens: number;
    total_cost: number;
    avg_response_time: number;
    error_rate: number;
    availability: number;
    active_users: number;
    active_models: number;
  }> {
    try {
      // 并行获取各种统计数据
      const [timeSeriesData, modelMetrics, performanceMetrics] = await Promise.all([
        this.getTimeSeriesData({ time_range: period === 'daily' ? '24h' : '7d' }),
        this.getModelUsageMetrics({ period }),
        this.getPerformanceMetrics({ period })
      ]);

      // 计算汇总数据
      const totalRequests = timeSeriesData.time_series.reduce((sum, point) => sum + point.requests, 0);
      const totalTokens = timeSeriesData.time_series.reduce((sum, point) => sum + point.tokens, 0);
      const totalCost = timeSeriesData.time_series.reduce((sum, point) => sum + point.cost, 0);
      const avgResponseTime = performanceMetrics.avg_response_time;
      const errorRate = performanceMetrics.error_rate;
      const availability = performanceMetrics.availability;
      const activeModels = modelMetrics.model_metrics.length;

      // 计算活跃用户数 (从时间序列数据中的并发用户数取最大值)
      const activeUsers = Math.max(...timeSeriesData.time_series.map(point => point.concurrent_users));

      return {
        total_requests: totalRequests,
        total_tokens: totalTokens,
        total_cost: totalCost,
        avg_response_time: avgResponseTime,
        error_rate: errorRate,
        availability: availability,
        active_users: activeUsers,
        active_models: activeModels
      };
    } catch (error) {
      console.error('Error getting statistics summary:', error);
      // 返回默认值
      return {
        total_requests: 0,
        total_tokens: 0,
        total_cost: 0,
        avg_response_time: 0,
        error_rate: 0,
        availability: 1,
        active_users: 0,
        active_models: 0
      };
    }
  }
}

// 导出单例实例
export const usageStatisticsService = new UsageStatisticsService();
export default usageStatisticsService;