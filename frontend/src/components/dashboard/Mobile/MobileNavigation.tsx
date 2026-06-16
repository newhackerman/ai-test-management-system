import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  Home,
  BarChart3,
  Settings,
  Bell,
  BellOff,
  Search,
  Filter,
  Grid3X3,
  List,
  Layers,
  RefreshCw,
  Wifi,
  WifiOff,
  Menu,
  X
} from 'lucide-react';
import { touchFeedback } from '@/utils/touchGestures';

interface MobileNavigationProps {
  viewMode: 'swipe' | 'grid' | 'list';
  onViewModeChange: (mode: 'swipe' | 'grid' | 'list') => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  notificationsEnabled: boolean;
  onToggleNotifications: () => void;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  onRefresh?: () => void;
  isRefreshing?: boolean;
  widgetCount: number;
  onShowMenu?: () => void;
  onShowSettings?: () => void;
  onShowFilters?: () => void;
}

const MobileNavigation: React.FC<MobileNavigationProps> = ({
  viewMode,
  onViewModeChange,
  searchQuery,
  onSearchChange,
  notificationsEnabled,
  onToggleNotifications,
  connectionStatus,
  onRefresh,
  isRefreshing = false,
  widgetCount,
  onShowMenu,
  onShowSettings,
  onShowFilters
}) => {
  const [showSearch, setShowSearch] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);

  const handleViewModeChange = useCallback((mode: 'swipe' | 'grid' | 'list') => {
    onViewModeChange(mode);
    touchFeedback.vibrate(5);
  }, [onViewModeChange]);

  const handleRefresh = useCallback(() => {
    if (!isRefreshing && onRefresh) {
      onRefresh();
      touchFeedback.vibrate([10, 50, 10]);
    }
  }, [isRefreshing, onRefresh]);

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-500';
      case 'connecting': return 'bg-yellow-500 animate-pulse';
      case 'disconnected': return 'bg-red-500';
      default: return 'bg-gray-500 dark:bg-gray-800/50';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中';
      case 'disconnected': return '已断开';
      default: return '未知';
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 safe-area-top dark:bg-gray-800 dark:border-gray-700">
      {/* Main Navigation Bar */}
      <div className="px-4 py-3 flex items-center justify-between">
        {/* Left Section */}
        <div className="flex items-center space-x-3">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">仪表板</h1>
            <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
              <span>{widgetCount} 个组件</span>
              <div className={`w-1.5 h-1.5 rounded-full ${getConnectionStatusColor()}`} />
              <span>{getConnectionStatusText()}</span>
            </div>
          </div>
        </div>

        {/* Right Section */}
        <div className="flex items-center space-x-2">
          {/* Search Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setShowSearch(!showSearch);
              touchFeedback.vibrate(5);
            }}
            className={`touch-optimized ${showSearch ? 'bg-blue-50 text-blue-600' : ''}`}
          >
            <Search className="h-4 w-4" />
          </Button>

          {/* Notifications Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onToggleNotifications();
              touchFeedback.vibrate(10);
            }}
            className="touch-optimized"
          >
            {notificationsEnabled ? (
              <Bell className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            ) : (
              <BellOff className="h-4 w-4 text-gray-400 dark:text-gray-500" />
            )}
          </Button>

          {/* View Mode Selector */}
          <div className="flex bg-gray-100 rounded-lg p-1 dark:bg-gray-800">
            <button
              onClick={() => handleViewModeChange('swipe')}
              className={`p-1.5 rounded touch-optimized transition-colors ${
                viewMode === 'swipe' ? 'bg-white shadow-sm text-blue-600 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400'
              }`}
              title="滑动视图"
            >
              <Layers className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => handleViewModeChange('grid')}
              className={`p-1.5 rounded touch-optimized transition-colors ${
                viewMode === 'grid' ? 'bg-white shadow-sm text-blue-600 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400'
              }`}
              title="网格视图"
            >
              <Grid3X3 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => handleViewModeChange('list')}
              className={`p-1.5 rounded touch-optimized transition-colors ${
                viewMode === 'list' ? 'bg-white shadow-sm text-blue-600 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400'
              }`}
              title="列表视图"
            >
              <List className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Quick Actions Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setShowQuickActions(!showQuickActions);
              touchFeedback.vibrate(5);
            }}
            className="touch-optimized"
          >
            {showQuickActions ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      {showSearch && (
        <div className="px-4 pb-3 animate-in slide-in-from-top duration-200">
          <div className="relative">
            <input
              type="text"
              placeholder="搜索组件..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full px-4 py-2 pl-10 pr-10 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:border-gray-600"
              autoFocus
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 touch-optimized"
              >
                <X className="h-4 w-4 text-gray-400 dark:text-gray-500" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      {showQuickActions && (
        <div className="px-4 pb-3 animate-in slide-in-from-top duration-200">
          <div className="grid grid-cols-4 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex flex-col items-center space-y-1 h-auto py-2 touch-optimized"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="text-xs">刷新</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                onShowFilters?.();
                setShowQuickActions(false);
              }}
              className="flex flex-col items-center space-y-1 h-auto py-2 touch-optimized"
            >
              <Filter className="h-4 w-4" />
              <span className="text-xs">筛选</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                onShowSettings?.();
                setShowQuickActions(false);
              }}
              className="flex flex-col items-center space-y-1 h-auto py-2 touch-optimized"
            >
              <Settings className="h-4 w-4" />
              <span className="text-xs">设置</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                onShowMenu?.();
                setShowQuickActions(false);
              }}
              className="flex flex-col items-center space-y-1 h-auto py-2 touch-optimized"
            >
              <BarChart3 className="h-4 w-4" />
              <span className="text-xs">更多</span>
            </Button>
          </div>
        </div>
      )}

      {/* Connection Status Bar (when disconnected) */}
      {connectionStatus === 'disconnected' && (
        <div className="bg-red-50 border-t border-red-200 px-4 py-2 dark:bg-red-900/20 dark:border-red-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-red-700 dark:text-red-400">
              <WifiOff className="h-4 w-4" />
              <span className="text-sm">连接已断开</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="text-red-700 border-red-300 hover:bg-red-100 touch-optimized dark:text-red-400 dark:bg-red-900/30"
            >
              重连
            </Button>
          </div>
        </div>
      )}

      {/* Loading Bar (when refreshing) */}
      {isRefreshing && (
        <div className="h-1 bg-gray-200 dark:bg-gray-600">
          <div className="h-full bg-blue-500 animate-pulse" style={{ width: '100%' }} />
        </div>
      )}
    </div>
  );
};

export default MobileNavigation;