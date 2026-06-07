/**
 * Lighthouse性能监控服务
 * 
 * 提供Web性能分析相关的API调用功能
 */
import { apiClient } from '../lib/api-client'

export interface LighthouseAuditRequest {
  url: string
  mobile?: boolean
  throttling?: boolean
  categories?: string[]
}

export interface PerformanceMetrics {
  first_contentful_paint: number
  largest_contentful_paint: number
  cumulative_layout_shift: number
  first_input_delay: number
  speed_index: number
  total_blocking_time: number
  time_to_interactive: number
}

export interface PerformanceScores {
  performance: number
  accessibility: number
  best_practices: number
  seo: number
  pwa: number
}

export interface PerformanceOpportunity {
  title: string
  description: string
  potential_savings: number
  audit_id: string
}

export interface LighthouseAuditResult {
  audit_id: string
  url: string
  device_type: string
  lighthouse_version: string
  scores: PerformanceScores
  metrics: PerformanceMetrics
  opportunities: PerformanceOpportunity[]
  created_at: string
}

export interface PerformanceHistoryItem {
  audit_id: string
  device_type: string
  scores: PerformanceScores
  key_metrics: {
    first_contentful_paint: number
    largest_contentful_paint: number
    speed_index: number
    cumulative_layout_shift: number
  }
  created_at: string
}

export interface PerformanceHistory {
  url: string
  period_days: number
  device_type_filter?: string
  total_audits: number
  history: PerformanceHistoryItem[]
}

export interface PerformanceSummary {
  url: string
  period_days: number
  total_audits: number
  latest_audit: string
  average_scores: PerformanceScores
  average_metrics: PerformanceMetrics
  trend: {
    performance_trend: number
    fcp_trend: number
    lcp_trend: number
  }
  latest_scores: PerformanceScores
  latest_metrics: PerformanceMetrics
}

export interface PerformanceComparison {
  url: string
  baseline_date: string
  comparison_date: string
  metrics_comparison: {
    [key: string]: {
      baseline: number
      current: number
      change: number
      change_percent: number
    }
  }
  scores_comparison: {
    [key: string]: {
      baseline: number
      current: number
      change: number
    }
  }
  overall_trend: 'improved' | 'degraded' | 'stable'
}

export interface TestedUrl {
  url: string
  test_count: number
  last_test_time: string
  avg_performance_score: number
}

export class LighthouseService {
  /**
   * 运行Lighthouse性能审计
   */
  static async runAudit(request: LighthouseAuditRequest): Promise<LighthouseAuditResult> {
    const response = await apiClient.post('/performance/lighthouse/audit', request)
    return response.data.data
  }

  /**
   * 获取性能历史数据
   */
  static async getHistory(
    url: string,
    days: number = 30,
    deviceType?: string
  ): Promise<PerformanceHistory> {
    const params = new URLSearchParams({
      days: days.toString()
    })
    
    if (deviceType) {
      params.append('device_type', deviceType)
    }

    const encodedUrl = encodeURIComponent(url)
    const response = await apiClient.get(`/performance/lighthouse/history/${encodedUrl}?${params}`)
    return response.data.data
  }

  /**
   * 获取性能摘要
   */
  static async getSummary(url: string, days: number = 7): Promise<PerformanceSummary> {
    const encodedUrl = encodeURIComponent(url)
    const response = await apiClient.get(`/performance/lighthouse/summary/${encodedUrl}?days=${days}`)
    return response.data.data
  }

  /**
   * 性能对比分析
   */
  static async comparePerformance(
    url: string,
    baselineDate: string,
    comparisonDate?: string
  ): Promise<PerformanceComparison> {
    const response = await apiClient.post('/performance/lighthouse/compare', {
      url,
      baseline_date: baselineDate,
      comparison_date: comparisonDate
    })
    return response.data.data
  }

  /**
   * 获取已测试的URL列表
   */
  static async getTestedUrls(limit: number = 50): Promise<TestedUrl[]> {
    const response = await apiClient.get(`/performance/lighthouse/urls?limit=${limit}`)
    return response.data.data.urls
  }

  /**
   * 格式化性能评分颜色
   */
  static getScoreColor(score: number): string {
    if (score >= 90) return 'text-green-600'
    if (score >= 50) return 'text-yellow-600'
    return 'text-red-600'
  }

  /**
   * 格式化性能评分等级
   */
  static getScoreGrade(score: number): string {
    if (score >= 90) return '优秀'
    if (score >= 50) return '需要改进'
    return '较差'
  }

  /**
   * 格式化时间值（毫秒）
   */
  static formatTime(ms: number): string {
    if (ms < 1000) {
      return `${Math.round(ms)}ms`
    }
    return `${(ms / 1000).toFixed(1)}s`
  }

  /**
   * 格式化文件大小
   */
  static formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  /**
   * 获取指标建议
   */
  static getMetricAdvice(metricName: string, value: number): string {
    const advice: { [key: string]: (value: number) => string } = {
      first_contentful_paint: (v) => {
        if (v <= 1800) return '优秀：用户能够快速看到内容'
        if (v <= 3000) return '需要改进：考虑优化关键渲染路径'
        return '较差：需要优化资源加载和渲染'
      },
      largest_contentful_paint: (v) => {
        if (v <= 2500) return '优秀：主要内容加载迅速'
        if (v <= 4000) return '需要改进：优化大型资源加载'
        return '较差：需要优化图片和视频资源'
      },
      cumulative_layout_shift: (v) => {
        if (v <= 0.1) return '优秀：页面布局稳定'
        if (v <= 0.25) return '需要改进：减少布局偏移'
        return '较差：需要为元素预留空间'
      },
      speed_index: (v) => {
        if (v <= 3400) return '优秀：页面内容显示迅速'
        if (v <= 5800) return '需要改进：优化关键资源'
        return '较差：需要优化页面加载策略'
      }
    }

    return advice[metricName]?.(value) || '无建议'
  }
}

export default LighthouseService