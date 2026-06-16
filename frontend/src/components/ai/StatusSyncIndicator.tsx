/**
 * 状态同步指示器组件
 * 显示实时同步状态、连接状态和待处理操作
 */

import React, { useState, useEffect } from 'react';
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Clock,
  Zap,
  Settings,
  Info
} from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/Tooltip';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/Popover';
import { Progress } from '../ui/Progress';
import { Separator } from '../ui/Separator';
import { useRealTimeSync } from '../../hooks/useRealTimeSync';
import { SyncStatus, ConnectionStatus } from '../../types/ai-assistant';
import { cn } from '../../lib/utils';

interface StatusSyncIndicatorProps {
  conversationId?: number;
  className?: string;
  showDetails?: boolean;
  compact?: boolean;
  onForceSync?: () => void;
  onResolveConflicts?: () => void;
}

interface StatusConfig {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  label: string;
  description: string;
}

const syncStatusConfig: Record<SyncStatus, StatusConfig> = {
  synced: {
    icon: CheckCircle2,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: '已同步',
    description: '所有数据已与服务器同步'
  },
  syncing: {
    icon: RefreshCw,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    label: '同步中',
    description: '正在与服务器同步数据'
  },
  error: {
    icon: XCircle,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    label: '同步错误',
    description: '同步过程中发生错误'
  },
  offline: {
    icon: WifiOff,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    label: '离线',
    description: '当前处于离线状态，数据将在连接恢复后同步'
  }
};

const connectionStatusConfig: Record<ConnectionStatus, StatusConfig> = {
  connected: {
    icon: Wifi,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: '已连接',
    description: 'WebSocket连接正常'
  },
  connecting: {
    icon: RefreshCw,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    label: '连接中',
    description: '正在建立WebSocket连接'
  },
  reconnecting: {
    icon: RefreshCw,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    label: '重连中',
    description: '正在尝试重新连接'
  },
  disconnected: {
    icon: WifiOff,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    label: '已断开',
    description: 'WebSocket连接已断开'
  }
};

export function StatusSyncIndicator({
  conversationId,
  className,
  showDetails = false,
  compact = false,
  onForceSync,
  onResolveConflicts
}: StatusSyncIndicatorProps) {
  const [showPopover, setShowPopover] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

  const {
    syncState,
    forcSync,
    getPendingOperationsCount,
    getConflictsCount
  } = useRealTimeSync({
    conversationId,
    onSyncStatusChanged: (status) => {
      if (status === 'synced') {
        setLastSyncTime(new Date());
      }
    }
  });

  const pendingCount = getPendingOperationsCount();
  const conflictsCount = getConflictsCount();

  // 获取同步状态配置
  const syncConfig = syncStatusConfig[syncState.status];
  const connectionConfig = connectionStatusConfig[syncState.connectionStatus];

  // 处理强制同步
  const handleForceSync = () => {
    forcSync();
    onForceSync?.();
  };

  // 处理解决冲突
  const handleResolveConflicts = () => {
    onResolveConflicts?.();
  };

  // 格式化时间
  const formatTime = (date: Date | null) => {
    if (!date) return '从未';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return date.toLocaleDateString();
  };

  // 计算同步进度
  const getSyncProgress = () => {
    if (syncState.status === 'synced') return 100;
    if (syncState.status === 'syncing' && pendingCount > 0) {
      // 这里可以根据实际同步进度计算
      return Math.max(10, Math.min(90, (Date.now() % 5000) / 50));
    }
    return 0;
  };

  // 紧凑模式渲染
  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-md text-xs",
              syncConfig.bgColor,
              className
            )}>
              <syncConfig.icon className={cn("w-3 h-3", syncConfig.color)} />
              {pendingCount > 0 && (
                <Badge variant="secondary" className="text-xs h-4 px-1">
                  {pendingCount}
                </Badge>
              )}
              {conflictsCount > 0 && (
                <AlertTriangle className="w-3 h-3 text-orange-500" />
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="text-sm">
              <div className="font-medium">{syncConfig.label}</div>
              <div className="text-gray-500 dark:text-gray-400">{syncConfig.description}</div>
              {pendingCount > 0 && (
                <div className="text-orange-600">
                  {pendingCount} 个待处理操作
                </div>
              )}
              {conflictsCount > 0 && (
                <div className="text-red-600 dark:text-red-400">
                  {conflictsCount} 个冲突需要解决
                </div>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // 详细模式渲染
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* 同步状态指示器 */}
      <Popover open={showPopover} onOpenChange={setShowPopover}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              "h-8 px-2 gap-2",
              syncConfig.bgColor,
              "hover:opacity-80"
            )}
          >
            <syncConfig.icon 
              className={cn(
                "w-4 h-4", 
                syncConfig.color,
                syncState.status === 'syncing' && "animate-spin"
              )} 
            />
            <span className={cn("text-sm font-medium", syncConfig.color)}>
              {syncConfig.label}
            </span>
            
            {/* 待处理操作计数 */}
            {pendingCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {pendingCount}
              </Badge>
            )}
            
            {/* 冲突指示器 */}
            {conflictsCount > 0 && (
              <AlertTriangle className="w-4 h-4 text-orange-500" />
            )}
          </Button>
        </PopoverTrigger>
        
        <PopoverContent className="w-80" align="end">
          <div className="space-y-4">
            {/* 标题 */}
            <div className="flex items-center gap-2">
              <syncConfig.icon className={cn("w-5 h-5", syncConfig.color)} />
              <h3 className="font-semibold">同步状态</h3>
            </div>
            
            {/* 同步状态详情 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">状态</span>
                <div className="flex items-center gap-2">
                  <syncConfig.icon className={cn("w-4 h-4", syncConfig.color)} />
                  <span className={cn("text-sm font-medium", syncConfig.color)}>
                    {syncConfig.label}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">连接状态</span>
                <div className="flex items-center gap-2">
                  <connectionConfig.icon className={cn("w-4 h-4", connectionConfig.color)} />
                  <span className={cn("text-sm", connectionConfig.color)}>
                    {connectionConfig.label}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">最后同步</span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {formatTime(lastSyncTime)}
                </span>
              </div>
            </div>
            
            {/* 同步进度 */}
            {syncState.status === 'syncing' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">同步进度</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {Math.round(getSyncProgress())}%
                  </span>
                </div>
                <Progress value={getSyncProgress()} className="h-2" />
              </div>
            )}
            
            {/* 待处理操作 */}
            {pendingCount > 0 && (
              <div className="space-y-2">
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-orange-500" />
                    <span className="text-sm font-medium">待处理操作</span>
                  </div>
                  <Badge variant="secondary">{pendingCount}</Badge>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  有 {pendingCount} 个操作等待同步到服务器
                </p>
              </div>
            )}
            
            {/* 冲突提醒 */}
            {conflictsCount > 0 && (
              <div className="space-y-2">
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-500 dark:text-red-400" />
                    <span className="text-sm font-medium text-red-600 dark:text-red-400">数据冲突</span>
                  </div>
                  <Badge variant="destructive">{conflictsCount}</Badge>
                </div>
                <p className="text-xs text-red-600 dark:text-red-400">
                  发现 {conflictsCount} 个数据冲突，需要手动解决
                </p>
                <Button 
                  size="sm" 
                  variant="outline"
                  className="w-full"
                  onClick={handleResolveConflicts}
                >
                  解决冲突
                </Button>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="space-y-2">
              <Separator />
              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="flex-1"
                  onClick={handleForceSync}
                  disabled={syncState.status === 'syncing' || !syncState.isOnline}
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  强制同步
                </Button>
                
                <Button 
                  size="sm" 
                  variant="ghost"
                  onClick={() => setShowPopover(false)}
                >
                  <Settings className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {/* 帮助信息 */}
            <div className="bg-blue-50 p-3 rounded-md dark:bg-blue-900/20">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-600 mt-0.5 dark:text-blue-400" />
                <div className="text-xs text-blue-700 dark:text-blue-300">
                  <p className="font-medium mb-1">同步说明</p>
                  <p>
                    系统会自动同步您的操作到服务器。离线时的操作会在网络恢复后自动同步。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>
      
      {/* 网络状态指示器 */}
      {!syncState.isOnline && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 px-2 py-1 bg-orange-100 rounded-md">
                <WifiOff className="w-3 h-3 text-orange-600" />
                <span className="text-xs text-orange-600">离线</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>网络连接已断开，操作将在恢复连接后同步</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}

/**
 * 简化的状态指示器 - 仅显示图标
 */
export function SimpleStatusIndicator({ 
  conversationId, 
  className 
}: { 
  conversationId?: number; 
  className?: string; 
}) {
  return (
    <StatusSyncIndicator
      conversationId={conversationId}
      className={className}
      compact={true}
    />
  );
}

/**
 * 详细的状态面板 - 显示完整信息
 */
export function DetailedStatusPanel({ 
  conversationId, 
  className,
  onForceSync,
  onResolveConflicts
}: { 
  conversationId?: number; 
  className?: string;
  onForceSync?: () => void;
  onResolveConflicts?: () => void;
}) {
  return (
    <StatusSyncIndicator
      conversationId={conversationId}
      className={className}
      showDetails={true}
      onForceSync={onForceSync}
      onResolveConflicts={onResolveConflicts}
    />
  );
}