// @ts-nocheck
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/stores/auth';
import { toast } from 'react-hot-toast';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface RealtimeData {
  [key: string]: any;
}

export const useRealtime = () => {
  const { user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [realtimeData, setRealtimeData] = useState<RealtimeData>({});
  const [subscriptions, setSubscriptions] = useState<Set<string>>(new Set());
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Get WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const roleType = user?.role || 'USER';
    const token = localStorage.getItem('token') || '';
    
    return `${protocol}//${host}/api/v1/dashboards/ws/${roleType}?token=${token}`;
  }, [user?.role]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setConnectionStatus('connecting');
      const wsUrl = getWebSocketUrl();
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        
        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'heartbeat',
              timestamp: new Date().toISOString()
            }));
          }
        }, 30000); // Send heartbeat every 30 seconds

        // Subscribe to existing subscriptions
        if (subscriptions.size > 0) {
          wsRef.current.send(JSON.stringify({
            type: 'subscribe',
            events: Array.from(subscriptions)
          }));
        }

        toast.success('实时连接已建立');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'initial_data':
              setRealtimeData(prev => ({ ...prev, ...message.data }));
              break;
              
            case 'data_update':
              setRealtimeData(prev => ({
                ...prev,
                [message.widget_type]: message.data
              }));
              break;
              
            case 'event':
              // Handle specific events
              handleRealtimeEvent(message.event_type, message.data);
              break;
              
            case 'heartbeat':
              // Heartbeat response - connection is alive
              break;
              
            case 'error':
              console.error('WebSocket error:', message.message);
              toast.error(`连接错误：${message.message}`);
              break;
              
            default:
              console.log('Unknown message type:', message.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
          
          toast.error(`连接断开，${delay / 1000} 秒后重试...`);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionStatus('error');
          toast.error('连接失败，请刷新页面重试');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        toast.error('WebSocket 连接错误');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      toast.error('创建连接失败');
    }
  }, [getWebSocketUrl, subscriptions]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // Subscribe to events
  const subscribe = useCallback((events: string[]) => {
    const newSubscriptions = new Set([...subscriptions, ...events]);
    setSubscriptions(newSubscriptions);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        events: events
      }));
    }
  }, [subscriptions]);

  // Unsubscribe from events
  const unsubscribe = useCallback((events: string[]) => {
    const newSubscriptions = new Set(subscriptions);
    events.forEach(event => newSubscriptions.delete(event));
    setSubscriptions(newSubscriptions);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        events: events
      }));
    }
  }, [subscriptions]);

  // Request specific widget data
  const requestData = useCallback((widgetType: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_data',
        widget_type: widgetType
      }));
    }
  }, []);

  // Handle realtime events
  const handleRealtimeEvent = useCallback((eventType: string, data: any) => {
    switch (eventType) {
      case 'project_update':
        toast.info('项目数据已更新');
        break;
      case 'requirement_update':
        toast.info('需求数据已更新');
        break;
      case 'test_update':
        toast.info('测试数据已更新');
        break;
      case 'system_update':
        toast.info('系统数据已更新');
        break;
      default:
        console.log('Unhandled event:', eventType, data);
    }
    
    // Update realtime data
    setRealtimeData(prev => ({
      ...prev,
      [`${eventType}_data`]: data
    }));
  }, []);

  // Auto-connect when user is available
  useEffect(() => {
    if (user) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [user, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    connectionStatus,
    realtimeData,
    subscriptions: Array.from(subscriptions),
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    requestData
  };
};
