// @ts-nocheck
/**
 * WebSocket杩炴帴绠＄悊Hook
 * 鎻愪緵React缁勪欢浣跨敤WebSocket杩炴帴绠＄悊鍣ㄧ殑渚挎嵎鎺ュ彛
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  WebSocketConnectionManager, 
  WebSocketConfig, 
  ConnectionMetrics,
  QueuedMessage,
  createWebSocketManager,
  defaultWebSocketConfig
} from '../services/websocket-connection-manager';
import { WSMessage, WSMessageType, ConnectionStatus } from '../types/ai-assistant';

export interface UseWebSocketManagerOptions extends Partial<WebSocketConfig> {
  autoConnect?: boolean;
  userId?: number;
  conversationId?: number;
}

export interface UseWebSocketManagerReturn {
  // 杩炴帴鐘舵€?
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  isReconnecting: boolean;
  
  // 杩炴帴鎺у埗
  connect: () => Promise<void>;
  disconnect: () => void;
  reconnect: () => Promise<void>;
  
  // 娑堟伅鍙戦€?
  sendMessage: (message: Omit<WSMessage, 'timestamp'>) => boolean;
  sendTypingIndicator: (isTyping: boolean) => void;
  
  // 娑堟伅璁㈤槄
  subscribe: (messageType: WSMessageType, callback: (message: WSMessage) => void) => () => void;
  
  // 鐘舵€佷俊鎭?
  metrics: ConnectionMetrics;
  queueStatus: {
    size: number;
    maxSize: number;
    oldestMessage?: Date;
    newestMessage?: Date;
  };
  
  // 閿欒澶勭悊
  lastError: Error | null;
  clearError: () => void;
  
  // 闃熷垪绠＄悊
  clearQueue: () => void;
  
  // 缃戠粶鐘舵€?
  isOnline: boolean;
}

export function useWebSocketManager(options: UseWebSocketManagerOptions = {}): UseWebSocketManagerReturn {
  const {
    autoConnect = true,
    userId,
    conversationId,
    url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/ai-assistant`,
    ...configOptions
  } = options;

  // 鐘舵€佺鐞?
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [metrics, setMetrics] = useState<ConnectionMetrics>({
    reconnectAttempts: 0,
    totalReconnects: 0,
    messagesSent: 0,
    messagesReceived: 0,
    bytesTransferred: 0,
    averageLatency: 0,
    uptime: 0
  });
  const [queueStatus, setQueueStatus] = useState({
    size: 0,
    maxSize: 1000,
    oldestMessage: undefined as Date | undefined,
    newestMessage: undefined as Date | undefined
  });
  const [lastError, setLastError] = useState<Error | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // WebSocket绠＄悊鍣ㄥ紩鐢?
  const managerRef = useRef<WebSocketConnectionManager | null>(null);
  const subscribersRef = useRef<Map<string, () => void>>(new Map());

  // 鏋勫缓WebSocket URL
  const buildWebSocketUrl = useCallback(() => {
    const baseUrl = url;
    const params = new URLSearchParams();
    
    if (userId) {
      params.append('user_id', userId.toString());
    }
    
    if (conversationId) {
      params.append('conversation_id', conversationId.toString());
    }
    
    return params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;
  }, [url, userId, conversationId]);

  // 鍒濆鍖朩ebSocket绠＄悊鍣?
  const initializeManager = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.destroy();
    }

    const config: WebSocketConfig = {
      ...defaultWebSocketConfig,
      ...configOptions,
      url: buildWebSocketUrl()
    };

    const manager = createWebSocketManager(config);
    managerRef.current = manager;

    // 璁剧疆浜嬩欢鐩戝惉鍣?
    manager.on('statusChange', ({ status }) => {
      setConnectionStatus(status);
    });

    manager.on('connected', ({ metrics: connectedMetrics }) => {
      setMetrics(connectedMetrics);
      setLastError(null);
    });

    manager.on('disconnected', ({ metrics: disconnectedMetrics }) => {
      setMetrics(disconnectedMetrics);
    });

    manager.on('error', (error: Error) => {
      setLastError(error);
      console.error('WebSocket error:', error);
    });

    manager.on('messageQueued', () => {
      setQueueStatus(manager.getQueueStatus());
    });

    manager.on('queueProcessed', () => {
      setQueueStatus(manager.getQueueStatus());
    });

    manager.on('queueCleared', () => {
      setQueueStatus(manager.getQueueStatus());
    });

    manager.on('heartbeat', () => {
      setMetrics(manager.getMetrics());
    });

    manager.on('reconnectScheduled', () => {
      setMetrics(manager.getMetrics());
    });

    manager.on('maxReconnectAttemptsReached', () => {
      setLastError(new Error('Maximum reconnect attempts reached'));
    });

    manager.on('networkOnline', () => {
      setIsOnline(true);
    });

    manager.on('networkOffline', () => {
      setIsOnline(false);
    });

    return manager;
  }, [buildWebSocketUrl, configOptions]);

  // 杩炴帴鍑芥暟
  const connect = useCallback(async () => {
    if (!managerRef.current) {
      initializeManager();
    }
    
    if (managerRef.current) {
      try {
        await managerRef.current.connect();
      } catch (error) {
        setLastError(error as Error);
        throw error;
      }
    }
  }, [initializeManager]);

  // 鏂紑杩炴帴鍑芥暟
  const disconnect = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.disconnect();
    }
  }, []);

  // 閲嶈繛鍑芥暟
  const reconnect = useCallback(async () => {
    if (managerRef.current) {
      try {
        await managerRef.current.reconnect();
      } catch (error) {
        setLastError(error as Error);
        throw error;
      }
    }
  }, []);

  // 鍙戦€佹秷鎭嚱鏁?
  const sendMessage = useCallback((message: Omit<WSMessage, 'timestamp'>) => {
    if (!managerRef.current) {
      console.warn('WebSocket manager not initialized');
      return false;
    }

    return managerRef.current.send(message);
  }, []);

  // 鍙戦€佹墦瀛楁寚绀哄櫒
  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    sendMessage({
      type: 'typing',
      data: { 
        isTyping, 
        userId,
        conversationId 
      }
    });
  }, [sendMessage, userId, conversationId]);

  // 璁㈤槄娑堟伅
  const subscribe = useCallback((
    messageType: WSMessageType, 
    callback: (message: WSMessage) => void
  ) => {
    if (!managerRef.current) {
      console.warn('WebSocket manager not initialized');
      return () => {};
    }

    const unsubscribe = managerRef.current.subscribe(messageType, callback);
    const key = `${messageType}_${Date.now()}_${Math.random()}`;
    subscribersRef.current.set(key, unsubscribe);

    return () => {
      unsubscribe();
      subscribersRef.current.delete(key);
    };
  }, []);

  // 娓呴櫎閿欒
  const clearError = useCallback(() => {
    setLastError(null);
  }, []);

  // 娓呯┖闃熷垪
  const clearQueue = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.clearQueue();
    }
  }, []);

  // 鐩戝惉缃戠粶鐘舵€佸彉鍖?
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // 鍒濆鍖栧拰鑷姩杩炴帴
  useEffect(() => {
    initializeManager();

    if (autoConnect) {
      connect().catch(console.error);
    }

    return () => {
      // 娓呯悊璁㈤槄
      subscribersRef.current.forEach(unsubscribe => unsubscribe());
      subscribersRef.current.clear();

      // 閿€姣佺鐞嗗櫒
      if (managerRef.current) {
        managerRef.current.destroy();
        managerRef.current = null;
      }
    };
  }, [initializeManager, autoConnect, connect]);

  // 褰撶敤鎴稩D鎴栧璇滻D鍙樺寲鏃堕噸鏂拌繛鎺?
  useEffect(() => {
    if (managerRef.current && connectionStatus === 'connected') {
      reconnect().catch(console.error);
    }
  }, [userId, conversationId, reconnect, connectionStatus]);

  // 瀹氭湡鏇存柊鎸囨爣
  useEffect(() => {
    const interval = setInterval(() => {
      if (managerRef.current && connectionStatus === 'connected') {
        setMetrics(managerRef.current.getMetrics());
        setQueueStatus(managerRef.current.getQueueStatus());
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [connectionStatus]);

  return {
    // 杩炴帴鐘舵€?
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    isConnecting: connectionStatus === 'connecting',
    isReconnecting: connectionStatus === 'reconnecting',
    
    // 杩炴帴鎺у埗
    connect,
    disconnect,
    reconnect,
    
    // 娑堟伅鍙戦€?
    sendMessage,
    sendTypingIndicator,
    
    // 娑堟伅璁㈤槄
    subscribe,
    
    // 鐘舵€佷俊鎭?
    metrics,
    queueStatus,
    
    // 閿欒澶勭悊
    lastError,
    clearError,
    
    // 闃熷垪绠＄悊
    clearQueue,
    
    // 缃戠粶鐘舵€?
    isOnline
  };
}

/**
 * 绠€鍖栫増WebSocket Hook - 涓撻棬鐢ㄤ簬AI鍔╂墜
 */
export function useAIWebSocket(conversationId?: number) {
  // 浠庤璇佷笂涓嬫枃鑾峰彇鐢ㄦ埛ID锛堣繖閲岄渶瑕佹牴鎹疄闄呯殑璁よ瘉瀹炵幇璋冩暣锛?
  const userId = 1; // TODO: 浠庤璇佺姸鎬佽幏鍙栧疄闄呯敤鎴稩D

  return useWebSocketManager({
    userId,
    conversationId,
    autoConnect: true,
    heartbeatInterval: 30000,
    maxReconnectAttempts: 10,
    messageQueueSize: 500
  });
}

/**
 * WebSocket鐘舵€侀€夋嫨鍣℉ook
 */
export function useWebSocketStatus() {
  const { connectionStatus, isConnected, metrics, lastError, isOnline } = useWebSocketManager({
    autoConnect: false
  });

  return {
    connectionStatus,
    isConnected,
    isOnline,
    latency: metrics.averageLatency,
    uptime: metrics.uptime,
    error: lastError?.message,
    reconnectAttempts: metrics.reconnectAttempts
  };
}