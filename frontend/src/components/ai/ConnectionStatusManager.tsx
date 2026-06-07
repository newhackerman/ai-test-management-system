import React, { useCallback, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle, Clock, RefreshCw, Wifi, WifiOff, X } from 'lucide-react';

import { Alert, AlertDescription } from '../ui/Alert';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { ConnectionStatus, SyncStatus } from '../../types/ai-assistant';
import { cn } from '../../lib/utils';

type AIConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';
type ConnectionQuality = 'excellent' | 'good' | 'fair' | 'poor' | 'offline';
type Subscriber = (data: unknown) => void;

interface ConnectionStats {
  reconnectAttempts: number;
  messagesSent: number;
  messagesReceived: number;
  latency: number;
  connectedAt?: Date;
  lastMessageAt?: Date;
}

interface AIConnectionContextValue {
  isConnected: boolean;
  isConnecting: boolean;
  connectionState: AIConnectionState;
  connectionQuality: ConnectionQuality;
  connectionStats: ConnectionStats;
  lastError: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  reconnect: () => Promise<void>;
  send: (message: unknown) => boolean;
  subscribe: (eventType: string, handler?: Subscriber) => () => void;
  updateConfig: (config: Record<string, unknown>) => void;
  resetStats: () => void;
}

interface AIConnectionProviderProps {
  children: React.ReactNode;
  wsUrl?: string;
  config?: Record<string, unknown>;
}

interface ConnectionStatusManagerProps {
  connectionStatus: ConnectionStatus;
  syncStatus: SyncStatus;
  isOnline: boolean;
  onReconnect?: () => void;
  onDismiss?: () => void;
  className?: string;
}

const AIConnectionContext = React.createContext<AIConnectionContextValue | undefined>(undefined);

export function ConnectionStatusManager({
  connectionStatus,
  syncStatus,
  isOnline,
  onReconnect,
  onDismiss,
  className,
}: ConnectionStatusManagerProps) {
  const info = getStatusInfo(connectionStatus, syncStatus, isOnline);

  if (info.hidden) return null;

  return (
    <Alert className={cn(info.className, className)}>
      {info.icon}
      <AlertDescription>
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="font-medium">{info.title}</div>
            <div className="text-sm opacity-80">{info.description}</div>
          </div>
          <div className="flex items-center gap-2">
            {onReconnect && (
              <Button type="button" variant="outline" size="sm" onClick={onReconnect}>
                <RefreshCw className="mr-2 h-4 w-4" />
                重连
              </Button>
            )}
            {onDismiss && (
              <Button type="button" variant="ghost" size="icon" onClick={onDismiss}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );
}

export function AIConnectionProvider({ children }: AIConnectionProviderProps) {
  const [connectionState, setConnectionState] = useState<AIConnectionState>('disconnected');
  const [connectionQuality, setConnectionQuality] = useState<ConnectionQuality>('offline');
  const [lastError, setLastError] = useState<string | null>(null);
  const [stats, setStats] = useState<ConnectionStats>({
    reconnectAttempts: 0,
    messagesSent: 0,
    messagesReceived: 0,
    latency: 0,
  });
  const [subscribers] = useState(() => new Map<string, Set<Subscriber>>());

  const connect = useCallback(async () => {
    setConnectionState('connecting');
    setLastError(null);
    await Promise.resolve();
    setConnectionState('connected');
    setConnectionQuality('good');
    setStats((prev) => ({ ...prev, connectedAt: new Date(), latency: prev.latency || 80 }));
  }, []);

  const disconnect = useCallback(() => {
    setConnectionState('disconnected');
    setConnectionQuality('offline');
  }, []);

  const reconnect = useCallback(async () => {
    setStats((prev) => ({ ...prev, reconnectAttempts: prev.reconnectAttempts + 1 }));
    await connect();
  }, [connect]);

  const send = useCallback(
    (message: unknown) => {
      if (connectionState !== 'connected') {
        setLastError('连接未建立，消息未发送');
        return false;
      }

      setStats((prev) => ({ ...prev, messagesSent: prev.messagesSent + 1, lastMessageAt: new Date() }));
      const eventType = typeof message === 'object' && message && 'type' in message
        ? String((message as { type?: unknown }).type)
        : 'message';
      subscribers.get(eventType)?.forEach((handler) => handler(message));
      return true;
    },
    [connectionState, subscribers],
  );

  const subscribe = useCallback(
    (eventType: string, handler?: Subscriber) => {
      if (!handler) return () => undefined;
      const handlers = subscribers.get(eventType) ?? new Set<Subscriber>();
      handlers.add(handler);
      subscribers.set(eventType, handlers);
      return () => {
        handlers.delete(handler);
      };
    },
    [subscribers],
  );

  const resetStats = useCallback(() => {
    setStats({ reconnectAttempts: 0, messagesSent: 0, messagesReceived: 0, latency: 0 });
  }, []);

  const updateConfig = useCallback(() => undefined, []);

  const value = useMemo<AIConnectionContextValue>(
    () => ({
      isConnected: connectionState === 'connected',
      isConnecting: connectionState === 'connecting',
      connectionState,
      connectionQuality,
      connectionStats: stats,
      lastError,
      connect,
      disconnect,
      reconnect,
      send,
      subscribe,
      updateConfig,
      resetStats,
    }),
    [connect, connectionQuality, connectionState, disconnect, lastError, reconnect, resetStats, send, stats, subscribe, updateConfig],
  );

  return <AIConnectionContext.Provider value={value}>{children}</AIConnectionContext.Provider>;
}

export function useAIConnection() {
  const context = React.useContext(AIConnectionContext);
  if (!context) {
    throw new Error('useAIConnection must be used within AIConnectionProvider');
  }
  return context;
}

export function ConnectionStatusIndicator() {
  const { isConnected, isConnecting, lastError, reconnect } = useAIConnection();
  const icon = isConnecting ? (
    <RefreshCw className="h-4 w-4 animate-spin" />
  ) : isConnected ? (
    <Wifi className="h-4 w-4" />
  ) : (
    <WifiOff className="h-4 w-4" />
  );

  return (
    <Button type="button" variant="outline" size="sm" onClick={isConnected ? undefined : reconnect}>
      {icon}
      <span className="ml-2">{isConnected ? '已连接' : isConnecting ? '连接中' : lastError || '未连接'}</span>
    </Button>
  );
}

export function ConnectionQualityIndicator() {
  const { connectionQuality, connectionStats } = useAIConnection();
  const labelMap: Record<ConnectionQuality, string> = {
    excellent: '优秀',
    good: '良好',
    fair: '一般',
    poor: '较差',
    offline: '离线',
  };

  return (
    <Badge variant={connectionQuality === 'offline' ? 'secondary' : 'outline'}>
      {labelMap[connectionQuality]} · {connectionStats.latency}ms
    </Badge>
  );
}

export function ConnectionStatsPanel() {
  const { connectionStats, resetStats } = useAIConnection();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">连接统计</CardTitle>
        <Button type="button" variant="outline" size="sm" onClick={resetStats}>
          重置
        </Button>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-4">
        <Stat label="重连次数" value={connectionStats.reconnectAttempts} icon={<RefreshCw className="h-4 w-4" />} />
        <Stat label="发送消息" value={connectionStats.messagesSent} icon={<CheckCircle className="h-4 w-4" />} />
        <Stat label="接收消息" value={connectionStats.messagesReceived} icon={<AlertCircle className="h-4 w-4" />} />
        <Stat label="延迟" value={`${connectionStats.latency}ms`} icon={<Clock className="h-4 w-4" />} />
      </CardContent>
    </Card>
  );
}

const Stat: React.FC<{ label: string; value: React.ReactNode; icon: React.ReactNode }> = ({ label, value, icon }) => (
  <div className="rounded-md border p-3">
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      {icon}
      {label}
    </div>
    <div className="mt-1 text-lg font-semibold">{value}</div>
  </div>
);

const getStatusInfo = (connectionStatus: ConnectionStatus, syncStatus: SyncStatus, isOnline: boolean) => {
  if (isOnline && connectionStatus === 'connected' && syncStatus === 'synced') {
    return { hidden: true };
  }

  if (!isOnline) {
    return {
      hidden: false,
      icon: <WifiOff className="h-4 w-4" />,
      title: '网络已离线',
      description: '请检查网络连接后重试。',
      className: 'border-red-200 bg-red-50 text-red-700',
    };
  }

  if (connectionStatus === 'connecting' || connectionStatus === 'reconnecting') {
    return {
      hidden: false,
      icon: <RefreshCw className="h-4 w-4 animate-spin" />,
      title: connectionStatus === 'connecting' ? '正在连接' : '正在重连',
      description: '实时连接正在建立，请稍候。',
      className: 'border-blue-200 bg-blue-50 text-blue-700',
    };
  }

  if (connectionStatus === 'disconnected') {
    return {
      hidden: false,
      icon: <WifiOff className="h-4 w-4" />,
      title: '实时连接已断开',
      description: '部分实时功能可能不可用。',
      className: 'border-red-200 bg-red-50 text-red-700',
    };
  }

  return {
    hidden: false,
    icon: syncStatus === 'syncing' ? <RefreshCw className="h-4 w-4 animate-spin" /> : <AlertCircle className="h-4 w-4" />,
    title: syncStatus === 'syncing' ? '正在同步数据' : '数据同步异常',
    description: syncStatus === 'syncing' ? '数据同步中，请稍候。' : '部分数据可能未同步，请刷新或重试。',
    className: syncStatus === 'syncing' ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-orange-200 bg-orange-50 text-orange-700',
  };
};
