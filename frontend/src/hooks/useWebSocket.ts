/**
 * WebSocket连接管理Hook
 * 提供实时通信功能
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { WSMessage, WSMessageType, ConnectionStatus } from '../types/ai-assistant';

interface UseWebSocketOptions {
  url?: string;
  protocols?: string | string[];
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: WSMessage) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  lastMessage: WSMessage | null;
  sendMessage: (message: WSMessage) => void;
  connect: () => void;
  disconnect: () => void;
  subscribe: (messageType: WSMessageType, callback: (message: WSMessage) => void) => () => void;
  isConnected: boolean;
  error: string | null;
}

const getDefaultWebSocketUrl = () => {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
  const wsBaseUrl = apiBaseUrl.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  return `${wsBaseUrl}/api/v1/ai-websocket/ws/ai-assistant`;
};

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = getDefaultWebSocketUrl(),
    protocols,
    onOpen,
    onClose,
    onError,
    onMessage,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const subscribersRef = useRef<Map<WSMessageType, Set<(message: WSMessage) => void>>>(new Map());
  const isManualDisconnectRef = useRef(false);
  const callbacksRef = useRef({ onOpen, onClose, onError, onMessage });

  useEffect(() => {
    callbacksRef.current = { onOpen, onClose, onError, onMessage };
  }, [onOpen, onClose, onError, onMessage]);

  // 清理定时器
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // 发送心跳
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const heartbeatMessage: WSMessage = {
        type: 'status',
        data: { type: 'heartbeat' },
        timestamp: new Date().toISOString()
      };
      wsRef.current.send(JSON.stringify(heartbeatMessage));
      
      // 设置下一次心跳
      heartbeatTimeoutRef.current = setTimeout(sendHeartbeat, heartbeatInterval);
    }
  }, [heartbeatInterval]);

  // 处理消息分发
  const handleMessage = useCallback((message: WSMessage) => {
    setLastMessage(message);
    callbacksRef.current.onMessage?.(message);

    // 分发给订阅者
    const subscribers = subscribersRef.current.get(message.type);
    if (subscribers) {
      subscribers.forEach(callback => {
        try {
          callback(message);
        } catch (error) {
          console.error('Error in WebSocket message subscriber:', error);
        }
      });
    }

    // 处理心跳响应
    if (message.type === 'status' && message.data?.type === 'pong') {
      // 心跳响应，连接正常
    }
  }, []);

  // 连接WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // 已经连接
    }

    isManualDisconnectRef.current = false;
    setConnectionStatus('connecting');
    setError(null);

    try {
      const ws = new WebSocket(url, protocols);
      wsRef.current = ws;

      ws.onopen = (event) => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setError(null);
        reconnectCountRef.current = 0;
        
        // 开始心跳
        sendHeartbeat();
        
        callbacksRef.current.onOpen?.(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setConnectionStatus('disconnected');
        clearTimeouts();
        
        callbacksRef.current.onClose?.(event);

        // 自动重连（如果不是手动断开）
        if (!isManualDisconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
          setConnectionStatus('reconnecting');
          reconnectCountRef.current++;
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (${reconnectCountRef.current}/${reconnectAttempts})`);
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket连接错误');
        callbacksRef.current.onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          setError('消息解析失败');
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setError('无法创建WebSocket连接');
      setConnectionStatus('disconnected');
    }
  }, [url, protocols, handleMessage, sendHeartbeat, reconnectAttempts, reconnectInterval, clearTimeouts]);

  // 断开连接
  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    clearTimeouts();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    setConnectionStatus('disconnected');
  }, [clearTimeouts]);

  // 发送消息
  const sendMessage = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message));
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        setError('发送消息失败');
      }
    } else {
      console.warn('WebSocket is not connected, message not sent:', message);
      setError('WebSocket未连接');
    }
  }, []);

  // 订阅特定类型的消息
  const subscribe = useCallback((
    messageType: WSMessageType, 
    callback: (message: WSMessage) => void
  ) => {
    if (!subscribersRef.current.has(messageType)) {
      subscribersRef.current.set(messageType, new Set());
    }
    
    const subscribers = subscribersRef.current.get(messageType)!;
    subscribers.add(callback);

    // 返回取消订阅函数
    return () => {
      subscribers.delete(callback);
      if (subscribers.size === 0) {
        subscribersRef.current.delete(messageType);
      }
    };
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // 自动连接
  useEffect(() => {
    connect();
  }, [connect]);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    subscribe,
    isConnected: connectionStatus === 'connected',
    error
  };
}

/**
 * 简化版WebSocket Hook - 仅用于AI助手
 */
export function useAIWebSocket() {
  const [userId, setUserId] = useState<number | null>(null);

  // 获取当前用户ID（这里应该从认证状态获取）
  useEffect(() => {
    // TODO: 从认证状态获取用户ID
    setUserId(1); // 临时硬编码
  }, []);

  const webSocket = useWebSocket({
    url: userId ? `${getDefaultWebSocketUrl()}?user_id=${userId}` : undefined,
    onOpen: () => {
      console.log('AI WebSocket connected');
    },
    onClose: (event) => {
      console.log('AI WebSocket disconnected:', event.code);
    },
    onError: (error) => {
      console.error('AI WebSocket error:', error);
    }
  });

  return webSocket;
}
