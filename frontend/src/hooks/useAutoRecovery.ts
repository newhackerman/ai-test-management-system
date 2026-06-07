import { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import AutoRecoveryAPI, {
  FailureDetection,
  FailureType,
  ManualRecoveryRequest,
  MonitoringStatus,
  RecoveryAction,
  RecoveryStatistics
} from '../services/api/autoRecovery';

interface UseAutoRecoveryReturn {
  monitoringStatus: MonitoringStatus | null;
  failureDetection: FailureDetection | null;
  recoveryStatistics: RecoveryStatistics | null;
  recoveryHistory: any[];
  failureTypes: FailureType[];
  failureThresholds: Record<string, number>;
  loading: boolean;
  startMonitoring: () => Promise<void>;
  stopMonitoring: () => Promise<void>;
  refreshMonitoringStatus: () => Promise<void>;
  detectFailures: () => Promise<void>;
  executeManualRecovery: (request: ManualRecoveryRequest) => Promise<RecoveryAction | null>;
  refreshRecoveryHistory: () => Promise<void>;
  refreshRecoveryStatistics: () => Promise<void>;
  refreshFailureTypes: () => Promise<void>;
  refreshFailureThresholds: () => Promise<void>;
  updateFailureThresholds: (thresholds: Record<string, number>) => Promise<void>;
  performHealthCheck: () => Promise<Record<string, any> | null>;
}

const getErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
};

export const useAutoRecovery = (): UseAutoRecoveryReturn => {
  const [monitoringStatus, setMonitoringStatus] = useState<MonitoringStatus | null>(null);
  const [failureDetection, setFailureDetection] = useState<FailureDetection | null>(null);
  const [recoveryStatistics, setRecoveryStatistics] = useState<RecoveryStatistics | null>(null);
  const [recoveryHistory, setRecoveryHistory] = useState<any[]>([]);
  const [failureTypes, setFailureTypes] = useState<FailureType[]>([]);
  const [failureThresholds, setFailureThresholds] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  const refreshMonitoringStatus = useCallback(async () => {
    try {
      const status = await AutoRecoveryAPI.getMonitoringStatus();
      setMonitoringStatus(status);
    } catch (error) {
      console.error('获取自动恢复监控状态失败:', error);
    }
  }, []);

  const refreshRecoveryHistory = useCallback(async () => {
    try {
      const response = await AutoRecoveryAPI.getRecoveryHistory();
      setRecoveryHistory(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('获取恢复历史失败:', error);
    }
  }, []);

  const refreshRecoveryStatistics = useCallback(async () => {
    try {
      const statistics = await AutoRecoveryAPI.getRecoveryStatistics();
      setRecoveryStatistics(statistics);
    } catch (error) {
      console.error('获取恢复统计失败:', error);
    }
  }, []);

  const refreshFailureTypes = useCallback(async () => {
    try {
      const types = await AutoRecoveryAPI.getFailureTypes();
      setFailureTypes(Array.isArray(types) ? types : []);
    } catch (error) {
      console.error('获取故障类型失败:', error);
    }
  }, []);

  const refreshFailureThresholds = useCallback(async () => {
    try {
      const thresholds = await AutoRecoveryAPI.getFailureThresholds();
      setFailureThresholds(thresholds || {});
    } catch (error) {
      console.error('获取故障阈值失败:', error);
    }
  }, []);

  const startMonitoring = useCallback(async () => {
    try {
      setLoading(true);
      const status = await AutoRecoveryAPI.startMonitoring();
      setMonitoringStatus(status);
      message.success(status.message || '自动恢复监控已启动');
    } catch (error) {
      console.error('启动自动恢复监控失败:', error);
      message.error(getErrorMessage(error, '启动自动恢复监控失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const stopMonitoring = useCallback(async () => {
    try {
      setLoading(true);
      const status = await AutoRecoveryAPI.stopMonitoring();
      setMonitoringStatus(status);
      message.success(status.message || '自动恢复监控已停止');
    } catch (error) {
      console.error('停止自动恢复监控失败:', error);
      message.error(getErrorMessage(error, '停止自动恢复监控失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const detectFailures = useCallback(async () => {
    try {
      setLoading(true);
      const detection = await AutoRecoveryAPI.detectFailures();
      setFailureDetection(detection);

      if (detection.failures_detected > 0) {
        message.warning(`检测到 ${detection.failures_detected} 个故障`);
      } else {
        message.success('未检测到系统故障');
      }
    } catch (error) {
      console.error('故障检测失败:', error);
      message.error(getErrorMessage(error, '故障检测失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const executeManualRecovery = useCallback(
    async (request: ManualRecoveryRequest): Promise<RecoveryAction | null> => {
      try {
        setLoading(true);
        const result = await AutoRecoveryAPI.manualRecovery(request);

        if (result.recovery_status === 'success') {
          message.success(result.recovery_message || '恢复操作执行成功');
        } else {
          message.warning(result.recovery_message || '恢复操作已执行，请检查结果');
        }

        await Promise.all([refreshRecoveryHistory(), refreshRecoveryStatistics()]);
        return result;
      } catch (error) {
        console.error('手动恢复失败:', error);
        message.error(getErrorMessage(error, '手动恢复失败'));
        return null;
      } finally {
        setLoading(false);
      }
    },
    [refreshRecoveryHistory, refreshRecoveryStatistics]
  );

  const updateFailureThresholds = useCallback(async (thresholds: Record<string, number>) => {
    try {
      setLoading(true);
      const updatedThresholds = await AutoRecoveryAPI.updateFailureThresholds({ thresholds });
      setFailureThresholds(updatedThresholds || thresholds);
      message.success('故障阈值配置已更新');
    } catch (error) {
      console.error('更新故障阈值失败:', error);
      message.error(getErrorMessage(error, '更新故障阈值失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const performHealthCheck = useCallback(async (): Promise<Record<string, any> | null> => {
    try {
      setLoading(true);
      const healthStatus = await AutoRecoveryAPI.healthCheck();

      if (healthStatus?.service_status === 'healthy') {
        message.success('自动恢复服务运行正常');
      } else {
        message.warning('自动恢复服务状态异常，请查看详情');
      }

      return healthStatus;
    } catch (error) {
      console.error('健康检查失败:', error);
      message.error(getErrorMessage(error, '健康检查失败'));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.all([
      refreshMonitoringStatus(),
      refreshRecoveryStatistics(),
      refreshRecoveryHistory(),
      refreshFailureTypes(),
      refreshFailureThresholds()
    ]);
  }, [
    refreshFailureThresholds,
    refreshFailureTypes,
    refreshMonitoringStatus,
    refreshRecoveryHistory,
    refreshRecoveryStatistics
  ]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshMonitoringStatus();
      if (monitoringStatus?.is_monitoring) {
        void refreshRecoveryStatistics();
      }
    }, 30000);

    return () => window.clearInterval(interval);
  }, [monitoringStatus?.is_monitoring, refreshMonitoringStatus, refreshRecoveryStatistics]);

  return {
    monitoringStatus,
    failureDetection,
    recoveryStatistics,
    recoveryHistory,
    failureTypes,
    failureThresholds,
    loading,
    startMonitoring,
    stopMonitoring,
    refreshMonitoringStatus,
    detectFailures,
    executeManualRecovery,
    refreshRecoveryHistory,
    refreshRecoveryStatistics,
    refreshFailureTypes,
    refreshFailureThresholds,
    updateFailureThresholds,
    performHealthCheck
  };
};

export default useAutoRecovery;
