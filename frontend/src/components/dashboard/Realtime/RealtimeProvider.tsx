import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useRealtime, ConnectionStatus } from '@/hooks/dashboard/useRealtime';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface RealtimeContextType {
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  realtimeData: any;
  subscribe: (events: string[]) => void;
  unsubscribe: (events: string[]) => void;
  requestData: (widgetType: string) => void;
  // 新增功能
  connectionMetrics: ConnectionMetrics;
  dataUpdateAnimations: Map<string, boolean>;
  retryConnection: () => void;
  clearAnimations: () => void;
}

interface ConnectionMetrics {
  uptime: number;
  reconnectAttempts: number;
  messagesReceived: number;
  messagesSent: number;
  lastHeartbeat: Date | null;
  averageLatency: number;
}

interface DataUpdateNotification {
  id: string;
  type: string;
  message: string;
  timestamp: Date;
  duration?: number;
}

const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

interface RealtimeProviderProps {
  children: React.ReactNode;
  enableAnimations?: boolean;
  enableNotifications?: boolean;
  notificationDuration?: number;
}

export const RealtimeProvider: React.FC<RealtimeProviderProps> = ({ 
  children, 
  enableAnimations = true,
  enableNotifications = true,
  notificationDuration = 3000
}) => {
  const realtimeHook = useRealtime();
  const [connectionMetrics, setConnectionMetrics] = useState<ConnectionMetrics>({
    uptime: 0,
    reconnectAttempts: 0,
    messagesReceived: 0,
    messagesSent: 0,
    lastHeartbeat: null,
    averageLatency: 0
  });
  
  const [dataUpdateAnimations, setDataUpdateAnimations] = useState<Map<string, boolean>>(new Map());
  const [notifications, setNotifications] = useState<DataUpdateNotification[]>([]);
  
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const connectionStartTime = useRef<Date | null>(null);
  const latencyMeasurements = useRef<number[]>([]);

  // 监控连接状态变化
  useEffect(() => {
    if (realtimeHook.isConnected && !connectionStartTime.current) {
      connectionStartTime.current = new Date();
      setConnectionMetrics(prev => ({ ...prev, reconnectAttempts: 0 }));
    } else if (!realtimeHook.isConnected) {
      connectionStartTime.current = null;
    }
  }, [realtimeHook.isConnected]);

  // 更新连接指标
  useEffect(() => {
    if (realtimeHook.isConnected && connectionStartTime.current) {
      metricsIntervalRef.current = setInterval(() => {
        const now = new Date();
        const uptime = Math.floor((now.getTime() - connectionStartTime.current!.getTime()) / 1000);
        
        setConnectionMetrics(prev => ({
          ...prev,
          uptime,
          lastHeartbeat: now,
          averageLatency: latencyMeasurements.current.length > 0 
            ? latencyMeasurements.current.reduce((a, b) => a + b, 0) / latencyMeasurements.current.length 
            : 0
        }));
      }, 1000);
    } else {
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current);
        metricsIntervalRef.current = null;
      }
    }

    return () => {
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current);
      }
    };
  }, [realtimeHook.isConnected]);

  // 用于跟踪数据变化的ref
  const prevDataRef = useRef(realtimeHook.realtimeData);

  // 监听数据更新并触发动画
  useEffect(() => {
    const handleDataUpdate = (widgetType: string) => {
      // 更新消息计数
      setConnectionMetrics(prev => ({
        ...prev,
        messagesReceived: prev.messagesReceived + 1
      }));

      // 触发动画
      if (enableAnimations) {
        setDataUpdateAnimations(prev => {
          const newMap = new Map(prev);
          newMap.set(widgetType, true);
          return newMap;
        });

        // 清除动画状态
        setTimeout(() => {
          setDataUpdateAnimations(prev => {
            const newMap = new Map(prev);
            newMap.delete(widgetType);
            return newMap;
          });
        }, 1000);
      }

      // 显示通知
      if (enableNotifications) {
        const notification: DataUpdateNotification = {
          id: `${widgetType}-${Date.now()}`,
          type: widgetType,
          message: `${getWidgetDisplayName(widgetType)}数据已更新`,
          timestamp: new Date(),
          duration: notificationDuration
        };

        setNotifications(prev => [notification, ...prev.slice(0, 4)]); // 最多保留5个通知

        // 显示toast通知
        toast.success(notification.message, {
          duration: notificationDuration,
          position: 'top-right',
          style: {
            background: '#10B981',
            color: 'white',
          },
        });

        // 自动移除通知
        setTimeout(() => {
          setNotifications(prev => prev.filter(n => n.id !== notification.id));
        }, notificationDuration);
      }
    };

    // 监听实时数据变化
    if (JSON.stringify(prevDataRef.current) !== JSON.stringify(realtimeHook.realtimeData)) {
      const currentData = realtimeHook.realtimeData;
      const previousData = prevDataRef.current;

      // 检测哪些widget数据发生了变化
      Object.keys(currentData).forEach(key => {
        if (JSON.stringify(currentData[key]) !== JSON.stringify(previousData[key])) {
          handleDataUpdate(key);
        }
      });

      prevDataRef.current = currentData;
    }
  }, [realtimeHook.realtimeData, enableAnimations, enableNotifications, notificationDuration]);

  // 重试连接
  const retryConnection = useCallback(() => {
    setConnectionMetrics(prev => ({
      ...prev,
      reconnectAttempts: prev.reconnectAttempts + 1
    }));
    
    realtimeHook.connect();
    
    if (enableNotifications) {
      toast.loading('正在重新连接...', {
        duration: 2000,
        position: 'top-center',
      });
    }
  }, [realtimeHook.connect, enableNotifications]);

  // 清除动画状态
  const clearAnimations = useCallback(() => {
    setDataUpdateAnimations(new Map());
  }, []);

  // 获取widget显示名称
  const getWidgetDisplayName = (widgetType: string): string => {
    const displayNames: Record<string, string> = {
      'project_overview': '项目概览',
      'requirement_metrics': '需求指标',
      'test_metrics': '测试指标',
      'system_metrics': '系统指标',
      'team_performance': '团队绩效',
      'quality_trends': '质量趋势',
      'risk_analysis': '风险分析',
      'progress_tracking': '进度跟踪'
    };
    return displayNames[widgetType] || widgetType;
  };

  // 扩展的上下文值
  const contextValue: RealtimeContextType = {
    ...realtimeHook,
    connectionMetrics,
    dataUpdateAnimations,
    retryConnection,
    clearAnimations
  };

  return (
    <RealtimeContext.Provider value={contextValue}>
      {children}
      
      {/* 数据更新通知组件 */}
      {enableNotifications && (
        <DataUpdateNotifications notifications={notifications} />
      )}
      
      {/* 连接状态指示器 */}
      <ConnectionStatusIndicator 
        status={realtimeHook.connectionStatus}
        metrics={connectionMetrics}
        onRetry={retryConnection}
      />
    </RealtimeContext.Provider>
  );
};

// 数据更新通知组件
const DataUpdateNotifications: React.FC<{ notifications: DataUpdateNotification[] }> = ({ notifications }) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      <AnimatePresence>
        {notifications.map((notification) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: 100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.8 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 pointer-events-auto"
          >
            <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">{notification.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

// 连接状态指示器组件
const ConnectionStatusIndicator: React.FC<{
  status: ConnectionStatus;
  metrics: ConnectionMetrics;
  onRetry: () => void;
}> = ({ status, metrics, onRetry }) => {
  const [showDetails, setShowDetails] = useState(false);

  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'bg-green-500';
      case 'connecting': return 'bg-yellow-500';
      case 'disconnected': return 'bg-red-500';
      case 'error': return 'bg-red-600';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中';
      case 'disconnected': return '已断开';
      case 'error': return '连接错误';
      default: return '未知状态';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
      >
        <div 
          className="flex items-center space-x-2 p-3 cursor-pointer"
          onClick={() => setShowDetails(!showDetails)}
        >
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}>
            {status === 'connecting' && (
              <div className="w-full h-full rounded-full animate-ping bg-current opacity-75"></div>
            )}
          </div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {getStatusText()}
          </span>
          {status === 'connected' && (
            <span className="text-xs text-gray-500">
              {Math.floor(metrics.uptime / 60)}:{(metrics.uptime % 60).toString().padStart(2, '0')}
            </span>
          )}
        </div>

        <AnimatePresence>
          {showDetails && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-gray-200 dark:border-gray-700 p-3 space-y-2"
            >
              <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <div className="flex justify-between">
                  <span>运行时间:</span>
                  <span>{Math.floor(metrics.uptime / 60)}分{metrics.uptime % 60}秒</span>
                </div>
                <div className="flex justify-between">
                  <span>重连次数:</span>
                  <span>{metrics.reconnectAttempts}</span>
                </div>
                <div className="flex justify-between">
                  <span>接收消息:</span>
                  <span>{metrics.messagesReceived}</span>
                </div>
                <div className="flex justify-between">
                  <span>平均延迟:</span>
                  <span>{metrics.averageLatency.toFixed(0)}ms</span>
                </div>
              </div>
              
              {(status === 'disconnected' || status === 'error') && (
                <button
                  onClick={onRetry}
                  className="w-full mt-2 px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition-colors"
                >
                  重新连接
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export const useRealtimeContext = () => {
  const context = useContext(RealtimeContext);
  if (context === undefined) {
    throw new Error('useRealtimeContext must be used within a RealtimeProvider');
  }
  return context;
};