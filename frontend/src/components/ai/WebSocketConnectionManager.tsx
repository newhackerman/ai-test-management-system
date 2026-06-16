import React, { useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, RefreshCw, Trash2, Wifi, WifiOff } from 'lucide-react';

import { Alert, AlertDescription } from '../ui/Alert';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Progress } from '../ui/Progress';
import { ConnectionStatus } from '../../types/ai-assistant';
import { useWebSocketManager } from '../../hooks/useWebSocketManager';
import { cn } from '../../lib/utils';

interface WebSocketConnectionManagerProps {
  conversationId?: number;
  showDetails?: boolean;
  showControls?: boolean;
  showMetrics?: boolean;
  compact?: boolean;
  className?: string;
  onStatusChange?: (status: ConnectionStatus) => void;
}

export function WebSocketConnectionManager({
  conversationId,
  showDetails = false,
  showControls = true,
  showMetrics = false,
  compact = false,
  className,
  onStatusChange,
}: WebSocketConnectionManagerProps) {
  const ws = useWebSocketManager({ conversationId, autoConnect: true });

  useEffect(() => {
    onStatusChange?.(ws.connectionStatus);
  }, [onStatusChange, ws.connectionStatus]);

  const info = statusInfo(ws.connectionStatus, ws.isOnline);

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        {info.icon}
        <Badge variant={ws.isConnected ? 'default' : 'secondary'}>{info.label}</Badge>
        {showControls && !ws.isConnected && (
          <Button type="button" variant="ghost" size="sm" onClick={ws.reconnect} disabled={ws.isConnecting || ws.isReconnecting}>
            重连
          </Button>
        )}
      </div>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-base">
          {info.icon}
          WebSocket 连接
        </CardTitle>
        <Badge variant={ws.isConnected ? 'default' : 'secondary'}>{info.label}</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert className={info.className}>
          <AlertDescription>
            <div className="flex items-center justify-between gap-3">
              <span>{info.description}</span>
              {ws.lastError && (
                <Button type="button" variant="ghost" size="sm" onClick={ws.clearError}>
                  清除错误
                </Button>
              )}
            </div>
          </AlertDescription>
        </Alert>

        {showControls && (
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={ws.connect} disabled={ws.isConnected || ws.isConnecting}>
              <Wifi className="mr-2 h-4 w-4" />
              连接
            </Button>
            <Button type="button" variant="outline" onClick={ws.reconnect} disabled={ws.isConnecting || ws.isReconnecting}>
              <RefreshCw className={cn('mr-2 h-4 w-4', ws.isReconnecting && 'animate-spin')} />
              重连
            </Button>
            <Button type="button" variant="outline" onClick={ws.disconnect} disabled={!ws.isConnected}>
              <WifiOff className="mr-2 h-4 w-4" />
              断开
            </Button>
            <Button type="button" variant="outline" onClick={ws.clearQueue}>
              <Trash2 className="mr-2 h-4 w-4" />
              清空队列
            </Button>
          </div>
        )}

        {showDetails && (
          <div className="grid gap-3 text-sm md:grid-cols-3">
            <Detail label="会话 ID" value={conversationId ?? '-'} />
            <Detail label="队列" value={`${ws.queueStatus.size}/${ws.queueStatus.maxSize}`} />
            <Detail label="网络" value={ws.isOnline ? '在线' : '离线'} />
          </div>
        )}

        {showMetrics && <Metrics metrics={ws.metrics} />}
      </CardContent>
    </Card>
  );
}

export function SimpleWebSocketStatus({ conversationId, className }: { conversationId?: number; className?: string }) {
  return <WebSocketConnectionManager conversationId={conversationId} compact showControls={false} className={className} />;
}

export function WebSocketHealthMonitor({ conversationId, className }: { conversationId?: number; className?: string }) {
  return <WebSocketConnectionManager conversationId={conversationId} showDetails showMetrics className={className} />;
}

const Metrics: React.FC<{ metrics: ReturnType<typeof useWebSocketManager>['metrics'] }> = ({ metrics }) => {
  const uptimePercent = Math.min(100, Math.max(0, metrics.uptime || 0));
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-4">
        <Detail label="发送" value={metrics.messagesSent} />
        <Detail label="接收" value={metrics.messagesReceived} />
        <Detail label="重连" value={metrics.reconnectAttempts} />
        <Detail label="平均延迟" value={`${metrics.averageLatency.toFixed(0)}ms`} />
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>连接可用性</span>
          <span>{uptimePercent.toFixed(0)}%</span>
        </div>
        <Progress value={uptimePercent} />
      </div>
    </div>
  );
};

const Detail: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-md border p-3">
    <div className="text-xs text-muted-foreground">{label}</div>
    <div className="mt-1 font-medium">{value}</div>
  </div>
);

const statusInfo = (status: ConnectionStatus, isOnline: boolean) => {
  if (!isOnline) {
    return {
      label: '离线',
      description: '当前网络离线，实时能力不可用。',
      icon: <WifiOff className="h-4 w-4 text-red-600 dark:text-red-400" />,
      className: 'border-red-200 bg-red-50 text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800',
    };
  }

  switch (status) {
    case 'connected':
      return {
        label: '已连接',
        description: '实时连接工作正常。',
        icon: <CheckCircle className="h-4 w-4 text-green-600" />,
        className: 'border-green-200 bg-green-50 text-green-700',
      };
    case 'connecting':
    case 'reconnecting':
      return {
        label: status === 'connecting' ? '连接中' : '重连中',
        description: '正在建立实时连接。',
        icon: <RefreshCw className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />,
        className: 'border-blue-200 bg-blue-50 text-blue-700 dark:text-blue-300 dark:bg-blue-900/20',
      };
    default:
      return {
        label: '未连接',
        description: '实时连接未建立，可尝试重新连接。',
        icon: <AlertCircle className="h-4 w-4 text-orange-600" />,
        className: 'border-orange-200 bg-orange-50 text-orange-700 dark:text-orange-400 dark:bg-orange-900/20',
      };
  }
};
