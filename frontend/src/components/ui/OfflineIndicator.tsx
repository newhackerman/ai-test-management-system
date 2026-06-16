import React, { useState } from 'react'
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Database,
  Trash2
} from 'lucide-react'
import { Button } from './Button'
import { Badge } from './Badge'
import { Card, CardContent, CardHeader, CardTitle } from './Card'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from './DropdownMenu'
import { Progress } from './Progress'
import { useOffline } from '@/hooks/useOffline'
import { useToast } from '@/hooks/useToast'
import { cn } from '@/lib/utils'

interface OfflineIndicatorProps {
  className?: string
  showDetails?: boolean
  compact?: boolean
}

/**
 * 离线状态指示器组件
 */
export const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  className,
  showDetails = false,
  compact = false
}) => {
  const { 
    syncStatus, 
    isOnline, 
    hasPendingOperations, 
    isSyncing,
    forceSync,
    clearOfflineData,
    getCacheStats
  } = useOffline()
  
  const { toast } = useToast()
  const [cacheStats, setCacheStats] = useState<{
    cacheCount: number
    operationsCount: number
    totalSize: number
  } | null>(null)

  // 获取缓存统计
  const handleGetCacheStats = async () => {
    const stats = await getCacheStats()
    setCacheStats(stats)
  }

  // 强制同步
  const handleForceSync = async () => {
    const success = await forceSync()
    if (success) {
      toast({
        title: '同步成功',
        description: '离线数据已成功同步'
      })
    } else {
      toast({
        title: '同步失败',
        description: '无法同步离线数据，请稍后重试',
        variant: 'destructive'
      })
    }
  }

  // 清空离线数据
  const handleClearOfflineData = async () => {
    if (confirm('确定要清空所有离线数据吗？这将删除所有缓存和待同步的操作。')) {
      const success = await clearOfflineData()
      if (success) {
        setCacheStats(null)
        toast({
          title: '清空成功',
          description: '所有离线数据已清空'
        })
      } else {
        toast({
          title: '清空失败',
          description: '无法清空离线数据',
          variant: 'destructive'
        })
      }
    }
  }

  // 格式化文件大小
  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 格式化时间
  const formatTime = (timestamp: number): string => {
    if (timestamp === 0) return '从未同步'
    const now = Date.now()
    const diff = now - timestamp
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}天前`
    if (hours > 0) return `${hours}小时前`
    if (minutes > 0) return `${minutes}分钟前`
    return '刚刚'
  }

  // 紧凑模式
  if (compact) {
    return (
      <div className={cn('flex items-center space-x-2', className)}>
        {isOnline ? (
          <Wifi className="w-4 h-4 text-green-500 dark:text-green-400" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-500 dark:text-red-400" />
        )}
        
        {hasPendingOperations && (
          <Badge variant="outline" className="text-xs">
            {syncStatus.pendingOperations}
          </Badge>
        )}
        
        {isSyncing && (
          <RefreshCw className="w-4 h-4 animate-spin text-blue-500 dark:text-blue-400" />
        )}
      </div>
    )
  }

  // 详细模式
  if (showDetails) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center space-x-2">
            {isOnline ? (
              <Wifi className="w-5 h-5 text-green-500 dark:text-green-400" />
            ) : (
              <WifiOff className="w-5 h-5 text-red-500 dark:text-red-400" />
            )}
            <span>离线状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">网络状态</span>
              <div className="font-medium">
                {isOnline ? (
                  <span className="text-green-600 dark:text-green-400">在线</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">离线</span>
                )}
              </div>
            </div>
            
            <div>
              <span className="text-muted-foreground">待同步操作</span>
              <div className="font-medium">
                {syncStatus.pendingOperations} 个
              </div>
            </div>
            
            <div>
              <span className="text-muted-foreground">最后同步</span>
              <div className="font-medium">
                {formatTime(syncStatus.lastSync)}
              </div>
            </div>
            
            <div>
              <span className="text-muted-foreground">同步状态</span>
              <div className="font-medium">
                {isSyncing ? (
                  <span className="text-blue-600 dark:text-blue-400">同步中</span>
                ) : (
                  <span className="text-gray-600 dark:text-gray-400">空闲</span>
                )}
              </div>
            </div>
          </div>

          {cacheStats && (
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">缓存统计</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>缓存项: {cacheStats.cacheCount}</div>
                <div>操作队列: {cacheStats.operationsCount}</div>
                <div className="col-span-2">
                  总大小: {formatSize(cacheStats.totalSize)}
                </div>
              </div>
            </div>
          )}

          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleForceSync}
              disabled={!isOnline || isSyncing}
              className="flex-1"
            >
              {isSyncing ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              同步
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleGetCacheStats}
              className="flex-1"
            >
              <Database className="w-4 h-4 mr-2" />
              统计
            </Button>
          </div>

          <Button
            variant="destructive"
            size="sm"
            onClick={handleClearOfflineData}
            className="w-full"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            清空离线数据
          </Button>
        </CardContent>
      </Card>
    )
  }

  // 默认模式（下拉菜单）
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="sm" 
          className={cn('relative', className)}
        >
          {isOnline ? (
            <Wifi className="w-4 h-4 text-green-500 dark:text-green-400" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500 dark:text-red-400" />
          )}
          
          {hasPendingOperations && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 w-5 h-5 p-0 text-xs flex items-center justify-center"
            >
              {syncStatus.pendingOperations}
            </Badge>
          )}
          
          {isSyncing && (
            <RefreshCw className="absolute -bottom-1 -right-1 w-3 h-3 animate-spin text-blue-500 dark:text-blue-400" />
          )}
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-64">
        <div className="px-3 py-2">
          <div className="flex items-center space-x-2 mb-2">
            {isOnline ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400" />
                <span className="font-medium text-green-600 dark:text-green-400">在线</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400" />
                <span className="font-medium text-red-600 dark:text-red-400">离线</span>
              </>
            )}
          </div>
          
          <div className="space-y-1 text-sm text-muted-foreground">
            <div className="flex justify-between">
              <span>待同步操作:</span>
              <span>{syncStatus.pendingOperations} 个</span>
            </div>
            <div className="flex justify-between">
              <span>最后同步:</span>
              <span>{formatTime(syncStatus.lastSync)}</span>
            </div>
          </div>
          
          {isSyncing && (
            <div className="mt-2">
              <div className="flex items-center space-x-2 text-sm text-blue-600 dark:text-blue-400">
                <RefreshCw className="w-3 h-3 animate-spin" />
                <span>同步中...</span>
              </div>
              <Progress value={50} className="mt-1 h-1" />
            </div>
          )}
        </div>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem 
          onClick={handleForceSync}
          disabled={!isOnline || isSyncing}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          强制同步
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={handleGetCacheStats}>
          <Database className="w-4 h-4 mr-2" />
          查看缓存统计
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem 
          onClick={handleClearOfflineData}
          className="text-destructive"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          清空离线数据
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/**
 * 简单的网络状态指示器
 */
export const NetworkStatusIndicator: React.FC<{ className?: string }> = ({ className }) => {
  const { isOnline } = useOffline()
  
  return (
    <div className={cn('flex items-center space-x-2', className)}>
      {isOnline ? (
        <>
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-sm text-green-600 dark:text-green-400">在线</span>
        </>
      ) : (
        <>
          <div className="w-2 h-2 bg-red-500 rounded-full" />
          <span className="text-sm text-red-600 dark:text-red-400">离线</span>
        </>
      )}
    </div>
  )
}

/**
 * 同步进度指示器
 */
export const SyncProgressIndicator: React.FC<{ className?: string }> = ({ className }) => {
  const { syncStatus, isSyncing } = useOffline()
  
  if (!isSyncing && syncStatus.pendingOperations === 0) {
    return null
  }
  
  return (
    <div className={cn('flex items-center space-x-2 text-sm', className)}>
      {isSyncing ? (
        <>
          <RefreshCw className="w-4 h-4 animate-spin text-blue-500 dark:text-blue-400" />
          <span className="text-blue-600 dark:text-blue-400">同步中...</span>
        </>
      ) : (
        <>
          <Clock className="w-4 h-4 text-orange-500 dark:text-orange-400" />
          <span className="text-orange-600 dark:text-orange-400">
            {syncStatus.pendingOperations} 个操作待同步
          </span>
        </>
      )}
    </div>
  )
}

export default OfflineIndicator