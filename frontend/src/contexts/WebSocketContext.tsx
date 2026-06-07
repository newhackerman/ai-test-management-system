/**
 * WebSocket上下文提供器
 * 提供全局WebSocket连接管理和状态共享
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { 
  WebSocketConnectionManager, 
  createWebSocketManager,
  defaultWebSocketConfig 
} from '../services/websocket-connection-manager';
import { WSMessage, WSMessageType, ConnectionStatus } from '../types/ai-assistant';

interface WebSocketContextValue {
  // 连接管理
  connectionManager: WebSocketConnectionManager | null;
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  
  // 连接控制
  connect: () => Promise<void>;
  disconnect: () => void;
  reconnect: () => Promise<void>;
  
  // 消息发送
  sendMessage: (message: Omit<WSMessage, 'timestamp'>) => boolean;
  
  // 消息订阅
  subscribe: (messageType: WSMessageType, callback: (message: WSMessage) => void) => () => void;
  
  // 全局状态
  isOnline: boolean;
  lastError: Error | null;
  
  // 统计信息
  totalConnections: number;
  totalMessages: number;
  
  // 配置管理
  updateConfig: (config: Partial<typeof defaultWebSocketConfig>) => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  userId?: number;
  autoConnect?: boolean;
  config?: Partial<typeof defaultWebSocketConfig>;
}

export function WebSocketProvider({ 
  children, 
  userId,
  autoConnect = true,
  config = {}
}: WebSocketProviderProps) {
  const [connectionManager, setConnectionManager] = useState<WebSocketConnectionManager | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastError, setLastError] = useState<Error | null>(null);
  const [totalConnections, setTotalConnections] = useState(0);
  const [totalMessages, setTotalMessages] = useState(0);

  // 构建WebSocket URL
  const buildWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}/ws/ai-assistant`;
    
    if (userId) {
      return `${baseUrl}?user_id=${userId}`;
    }
    
    return baseUrl;
  }, [userId]);

  // 初始化连接管理器
  const initializeManager = useCallback(() => {
    if (connectionManager) {
      connectionManager.destroy();
    }

    const wsConfig = {
      ...defaultWebSocketConfig,
      ...config,
      url: buildWebSocketUrl()
    };

    const manager = createWebSocketManager(wsConfig);
    
    // 设置事件监听器
    manager.on('statusChange', ({ status }) => {
      setConnectionStatus(status);
    });

    manager.on('connected', () => {
      setTotalConnections(prev => prev + 1);
      setLastError(null);
    });

    manager.on('error', (error: Error) => {
      setLastError(error);
    });

    manager.on('message', () => {
      setTotalMessages(prev => prev + 1);
    });

    manager.on('messageSent', () => {
      setTotalMessages(prev => prev + 1);
    });

    setConnectionManager(manager);
    return manager;
  }, [connectionManager, config, buildWebSocketUrl]);

  // 连接函数
  const connect = useCallback(async () => {
    let manager = connectionManager;
    
    if (!manager) {
      manager = initializeManager();
    }
    
    if (manager) {
      try {
        await manager.connect();
      } catch (error) {
        setLastError(error as Error);
        throw error;
      }
    }
  }, [connectionManager, initializeManager]);

  // 断开连接函数
  const disconnect = useCallback(() => {
    if (connectionManager) {
      connectionManager.disconnect();
    }
  }, [connectionManager]);

  // 重连函数
  const reconnect = useCallback(async () => {
    if (connectionManager) {
      try {
        await connectionManager.reconnect();
      } catch (error) {
        setLastError(error as Error);
        throw error;
      }
    }
  }, [connectionManager]);

  // 发送消息函数
  const sendMessage = useCallback((message: Omit<WSMessage, 'timestamp'>) => {
    if (!connectionManager) {
      console.warn('WebSocket manager not initialized');
      return false;
    }

    return connectionManager.send(message);
  }, [connectionManager]);

  // 订阅消息函数
  const subscribe = useCallback((
    messageType: WSMessageType, 
    callback: (message: WSMessage) => void
  ) => {
    if (!connectionManager) {
      console.warn('WebSocket manager not initialized');
      return () => {};
    }

    return connectionManager.subscribe(messageType, callback);
  }, [connectionManager]);

  // 更新配置函数
  const updateConfig = useCallback((newConfig: Partial<typeof defaultWebSocketConfig>) => {
    // 重新初始化管理器以应用新配置
    const wasConnected = connectionStatus === 'connected';
    
    if (connectionManager) {
      connectionManager.destroy();
    }
    
    const manager = initializeManager();
    
    if (wasConnected && autoConnect) {
      manager.connect().catch(console.error);
    }
  }, [connectionManager, connectionStatus, initializeManager, autoConnect]);

  // 监听网络状态变化
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      if (autoConnect && connectionStatus === 'disconnected') {
        connect().catch(console.error);
      }
    };
    
    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [autoConnect, connectionStatus, connect]);

  // 初始化和自动连接
  useEffect(() => {
    const manager = initializeManager();

    if (autoConnect) {
      manager.connect().catch(console.error);
    }

    return () => {
      if (manager) {
        manager.destroy();
      }
    };
  }, [initializeManager, autoConnect]);

  // 当用户ID变化时重新连接
  useEffect(() => {
    if (connectionManager && connectionStatus === 'connected') {
      reconnect().catch(console.error);
    }
  }, [userId, connectionManager, connectionStatus, reconnect]);

  const contextValue: WebSocketContextValue = {
    // 连接管理
    connectionManager,
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    
    // 连接控制
    connect,
    disconnect,
    reconnect,
    
    // 消息发送
    sendMessage,
    
    // 消息订阅
    subscribe,
    
    // 全局状态
    isOnline,
    lastError,
    
    // 统计信息
    totalConnections,
    totalMessages,
    
    // 配置管理
    updateConfig
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
}

/**
 * 使用WebSocket上下文的Hook
 */
export function useWebSocketContext(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  
  return context;
}

/**
 * 用于特定对话的WebSocket Hook
 */
export function useConversationWebSocket(conversationId: number) {
  const { subscribe, sendMessage, isConnected } = useWebSocketContext();
  
  // 发送对话相关消息
  const sendConversationMessage = useCallback((
    type: WSMessageType,
    data: any
  ) => {
    return sendMessage({
      type,
      conversation_id: conversationId,
      data
    });
  }, [sendMessage, conversationId]);

  // 订阅对话相关消息
  const subscribeToConversation = useCallback((
    messageType: WSMessageType,
    callback: (message: WSMessage) => void
  ) => {
    return subscribe(messageType, (message) => {
      // 只处理与当前对话相关的消息
      if (message.conversation_id === conversationId) {
        callback(message);
      }
    });
  }, [subscribe, conversationId]);

  // 发送打字指示器
  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    return sendConversationMessage('typing', { isTyping });
  }, [sendConversationMessage]);

  return {
    isConnected,
    sendMessage: sendConversationMessage,
    subscribe: subscribeToConversation,
    sendTypingIndicator
  };
}

/**
 * WebSocket状态监控Hook
 */
export function useWebSocketMonitor() {
  const { 
    connectionStatus, 
    isConnected, 
    isOnline, 
    lastError, 
    totalConnections, 
    totalMessages,
    connectionManager
  } = useWebSocketContext();

  const [metrics, setMetrics] = useState({
    latency: 0,
    uptime: 0,
    reconnectAttempts: 0,
    queueSize: 0
  });

  // 定期更新指标
  useEffect(() => {
    if (!connectionManager) return;

    const interval = setInterval(() => {
      const managerMetrics = connectionManager.getMetrics();
      const queueStatus = connectionManager.getQueueStatus();
      
      setMetrics({
        latency: managerMetrics.averageLatency,
        uptime: managerMetrics.uptime,
        reconnectAttempts: managerMetrics.reconnectAttempts,
        queueSize: queueStatus.size
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [connectionManager]);

  return {
    connectionStatus,
    isConnected,
    isOnline,
    lastError: lastError?.message,
    totalConnections,
    totalMessages,
    metrics
  };
}

/**
 * 全局WebSocket错误处理Hook
 */
export function useWebSocketErrorHandler() {
  const { lastError, reconnect } = useWebSocketContext();
  const [errorHistory, setErrorHistory] = useState<Array<{
    error: Error;
    timestamp: Date;
    resolved: boolean;
  }>>([]);

  // 记录错误历史
  useEffect(() => {
    if (lastError) {
      setErrorHistory(prev => [
        ...prev.slice(-9), // 保留最近10个错误
        {
          error: lastError,
          timestamp: new Date(),
          resolved: false
        }
      ]);
    }
  }, [lastError]);

  // 标记错误为已解决
  const markErrorResolved = useCallback((index: number) => {
    setErrorHistory(prev => 
      prev.map((item, i) => 
        i === index ? { ...item, resolved: true } : item
      )
    );
  }, []);

  // 自动重连处理
  const handleAutoReconnect = useCallback(async () => {
    try {
      await reconnect();
      // 标记最近的错误为已解决
      if (errorHistory.length > 0) {
        markErrorResolved(errorHistory.length - 1);
      }
    } catch (error) {
      console.error('Auto reconnect failed:', error);
    }
  }, [reconnect, errorHistory, markErrorResolved]);

  return {
    currentError: lastError,
    errorHistory,
    markErrorResolved,
    handleAutoReconnect
  };
}