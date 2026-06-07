export { RealtimeProvider, useRealtimeContext } from './RealtimeProvider';
export { default as WebSocketClient } from './WebSocketClient';
export { DataUpdater, withDataUpdater, useDataUpdater } from './DataUpdater';

// 类型导出
export type { ConnectionStatus } from '@/hooks/dashboard/useRealtime';

// 重新导出相关类型
export interface RealtimeConfig {
  enableAnimations?: boolean;
  enableNotifications?: boolean;
  notificationDuration?: number;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableHeartbeat?: boolean;
  heartbeatInterval?: number;
}

export interface DataUpdateOptions {
  animationType?: 'pulse' | 'glow' | 'shake' | 'bounce' | 'fade';
  animationDuration?: number;
  showUpdateIndicator?: boolean;
}

// 默认配置
export const defaultRealtimeConfig: RealtimeConfig = {
  enableAnimations: true,
  enableNotifications: true,
  notificationDuration: 3000,
  autoReconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  enableHeartbeat: true,
  heartbeatInterval: 30000
};

export const defaultDataUpdateOptions: DataUpdateOptions = {
  animationType: 'pulse',
  animationDuration: 1000,
  showUpdateIndicator: true
};