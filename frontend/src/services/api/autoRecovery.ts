/**
 * 自动恢复服务API
 */
import { apiClient } from './client';

export interface FailureDetection {
  failures_detected: number;
  failures: Array<{
    failure_type: string;
    severity: string;
    message: string;
    detected_at: string;
    details: Record<string, any>;
  }>;
  detection_time: string;
}

export interface RecoveryAction {
  recovery_id: string;
  failure_type: string;
  recovery_status: string;
  recovery_message: string;
  actions_taken: string[];
  execution_time: string;
}

export interface RecoveryStatistics {
  total_recoveries: number;
  successful_recoveries: number;
  success_rate: number;
  recent_24h_recoveries: number;
  failure_type_statistics: Record<string, {
    count: number;
    avg_success_rate: number;
  }>;
  monitoring_status: string;
}

export interface MonitoringStatus {
  is_monitoring: boolean;
  status: string;
  message: string;
  uptime?: string;
}

export interface FailureType {
  value: string;
  name: string;
  description: string;
}

export interface ManualRecoveryRequest {
  failure_type: string;
  failure_details?: Record<string, any>;
  force_recovery?: boolean;
}

export interface UpdateThresholdsRequest {
  thresholds: Record<string, number>;
}

/**
 * 自动恢复服务API类
 */
export class AutoRecoveryAPI {
  /**
   * 启动自动恢复监控
   */
  static async startMonitoring(): Promise<MonitoringStatus> {
    const response = await apiClient.post('/auto-recovery/start-monitoring');
    return response.data.data;
  }

  /**
   * 停止自动恢复监控
   */
  static async stopMonitoring(): Promise<MonitoringStatus> {
    const response = await apiClient.post('/auto-recovery/stop-monitoring');
    return response.data.data;
  }

  /**
   * 获取监控状态
   */
  static async getMonitoringStatus(): Promise<MonitoringStatus> {
    const response = await apiClient.get('/auto-recovery/monitoring-status');
    return response.data.data;
  }

  /**
   * 手动检测系统故障
   */
  static async detectFailures(): Promise<FailureDetection> {
    const response = await apiClient.post('/auto-recovery/detect-failures');
    return response.data.data;
  }

  /**
   * 手动执行恢复操作
   */
  static async manualRecovery(request: ManualRecoveryRequest): Promise<RecoveryAction> {
    const response = await apiClient.post('/auto-recovery/manual-recovery', request);
    return response.data.data;
  }

  /**
   * 获取恢复历史记录
   */
  static async getRecoveryHistory(limit: number = 50): Promise<{
    data: any[];
    total: number;
    page: number;
    page_size: number;
  }> {
    const response = await apiClient.get('/auto-recovery/recovery-history', {
      params: { limit }
    });
    return response.data;
  }

  /**
   * 获取恢复统计信息
   */
  static async getRecoveryStatistics(): Promise<RecoveryStatistics> {
    const response = await apiClient.get('/auto-recovery/statistics');
    return response.data.data;
  }

  /**
   * 获取支持的故障类型
   */
  static async getFailureTypes(): Promise<FailureType[]> {
    const response = await apiClient.get('/auto-recovery/failure-types');
    return response.data.data;
  }

  /**
   * 获取故障阈值配置
   */
  static async getFailureThresholds(): Promise<Record<string, number>> {
    const response = await apiClient.get('/auto-recovery/thresholds');
    return response.data.data;
  }

  /**
   * 更新故障阈值配置
   */
  static async updateFailureThresholds(request: UpdateThresholdsRequest): Promise<Record<string, number>> {
    const response = await apiClient.put('/auto-recovery/thresholds', request);
    return response.data.data;
  }

  /**
   * 自动恢复服务健康检查
   */
  static async healthCheck(): Promise<Record<string, any>> {
    const response = await apiClient.get('/auto-recovery/health-check');
    return response.data.data;
  }
}

export default AutoRecoveryAPI;