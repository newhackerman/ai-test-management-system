import React, { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRealtimeContext } from './RealtimeProvider';
import { toast } from 'react-hot-toast';

interface WebSocketClientProps {
  children: React.ReactNode;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableHeartbeat?: boolean;
  heartbeatInterval?: number;
}

export const WebSocketClient: React.FC<WebSocketClientProps> = ({
  children,
  autoReconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
  enableHeartbeat = true,
  heartbeatInterval = 30000
}) => {
  const {
    isConnected,
    connectionStatus,
    connectionMetrics,
    retryConnection
  } = useRealtimeContext();

  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 自动重连逻辑
  useEffect(() => {
    if (!isConnected && autoReconnect && reconnectAttempts < maxReconnectAttempts) {
      if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
        setIsReconnecting(true);
        
        const delay = Math.min(reconnectInterval * Math.pow(2, reconnectAttempts), 30000);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          retryConnection();
        }, delay);

        toast.error(`连接断开，${delay / 1000}秒后自动重连...`, {
          duration: delay,
          position: 'bottom-center',
        });
      }
    } else if (isConnected) {
      setReconnectAttempts(0);
      setIsReconnecting(false);
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    } else if (reconnectAttempts >= maxReconnectAttempts) {
      setIsReconnecting(false);
      toast.error('连接失败次数过多，请手动重试', {
        duration: 5000,
        position: 'bottom-center',
      });
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isConnected, connectionStatus, autoReconnect, reconnectAttempts, maxReconnectAttempts, reconnectInterval, retryConnection]);

  // 心跳检测
  useEffect(() => {
    if (isConnected && enableHeartbeat) {
      heartbeatIntervalRef.current = setInterval(() => {
        // 心跳逻辑已在useRealtime hook中实现
        console.log('Heartbeat check - connection alive');
      }, heartbeatInterval);
    } else {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    }

    return () => {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };
  }, [isConnected, enableHeartbeat, heartbeatInterval]);

  // 手动重连
  const handleManualReconnect = useCallback(() => {
    setReconnectAttempts(0);
    setIsReconnecting(true);
    retryConnection();
  }, [retryConnection]);

  // 完全断开连接
  const handleDisconnect = useCallback(() => {
    setReconnectAttempts(maxReconnectAttempts); // 阻止自动重连
    setIsReconnecting(false);
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, [maxReconnectAttempts]);

  return (
    <div className="relative">
      {children}
      
      {/* 连接状态覆盖层 */}
      <AnimatePresence>
        {!isConnected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl max-w-md mx-4"
            >
              <div className="text-center">
                <div className="mb-4">
                  {isReconnecting ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-lg font-medium text-gray-700 dark:text-gray-300">
                        重新连接中...
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-6 h-6 bg-red-500 rounded-full"></div>
                      <span className="text-lg font-medium text-gray-700 dark:text-gray-300">
                        连接已断开
                      </span>
                    </div>
                  )}
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  {isReconnecting ? (
                    <p>正在尝试重新连接到服务器...</p>
                  ) : (
                    <p>与服务器的连接已断开，实时数据更新已暂停</p>
                  )}
                </div>

                <div className="text-xs text-gray-500 dark:text-gray-500 mb-6 space-y-1">
                  <div>重连尝试: {reconnectAttempts}/{maxReconnectAttempts}</div>
                  <div>连接状态: {connectionStatus}</div>
                  {connectionMetrics.lastHeartbeat && (
                    <div>
                      最后心跳: {connectionMetrics.lastHeartbeat.toLocaleTimeString()}
                    </div>
                  )}
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={handleManualReconnect}
                    disabled={isReconnecting}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isReconnecting ? '连接中...' : '立即重连'}
                  </button>
                  
                  <button
                    onClick={handleDisconnect}
                    className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  >
                    取消重连
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default WebSocketClient;