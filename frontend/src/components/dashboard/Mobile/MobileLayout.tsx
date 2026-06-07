import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useResponsive } from '@/hooks/useResponsive';
import { useMobileDashboard } from '@/hooks/dashboard/useMobileDashboard';
import { touchFeedback } from '@/utils/touchGestures';
import { performanceMonitor, networkMonitor } from '@/utils/mobileOptimization';
import MobileNavigation from './MobileNavigation';
import MobileWidgetCard from './MobileWidgetCard';
import { Button } from '@/components/ui/Button';
import { 
  RefreshCw, 
  Plus, 
  AlertTriangle, 
  Wifi, 
  WifiOff,
  Battery,
  BatteryLow
} from 'lucide-react';

interface MobileLayoutProps {
  widgets: any[];
  realtimeData?: any;
  isLoading?: boolean;
  connectionStatus?: 'connected' | 'connecting' | 'disconnected';
  onAddWidget?: () => void;
  onShowColorSchemes?: () => void;
  onShowSettings?: () => void;
  onRefresh?: () => Promise<void>;
  onShare?: (widgetId: string) => void;
  onExport?: (widgetId: string) => void;
  onWidgetAction?: (action: string, widgetId: string) => void;
}

const MobileLayout: React.FC<MobileLayoutProps> = ({
  widgets,
  realtimeData = {},
  isLoading = false,
  connectionStatus = 'disconnected',
  onAddWidget,
  onShowColorSchemes,
  onShowSettings,
  onRefresh,
  onShare,
  onExport,
  onWidgetAction
}) => {
  const { isMobile, orientation, screenWidth, screenHeight } = useResponsive();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [batteryInfo, setBatteryInfo] = useState<any>(null);
  const [showOfflineMessage, setShowOfflineMessage] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Mobile dashboard hook
  const {
    viewMode,
    currentWidgetIndex,
    searchQuery,
    isRefreshing,
    showWidgetActions,
    pullToRefreshDistance,
    isPulling,
    notificationsEnabled,
    filteredWidgets,
    currentWidget,
    setViewMode,
    setSearchQuery,
    handlePullToRefresh,
    handleTouchStartPull,
    handleTouchMovePull,
    handleTouchEndPull,
    handleWidgetAction,
    closeWidgetActions,
    toggleNotifications,
    nextWidget,
    prevWidget,
    goToWidget,
    shouldShowGestureHints
  } = useMobileDashboard({
    widgets,
    onRefresh,
    onShare,
    onExport
  });

  // Network status monitoring
  useEffect(() => {
    const unsubscribe = networkMonitor.onStatusChange((online) => {
      setIsOnline(online);
      if (!online) {
        setShowOfflineMessage(true);
        setTimeout(() => setShowOfflineMessage(false), 3000);
      }
    });

    return unsubscribe;
  }, []);

  // Battery monitoring
  useEffect(() => {
    const checkBattery = async () => {
      if ('getBattery' in navigator) {
        try {
          const battery = await (navigator as any).getBattery();
          setBatteryInfo({
            level: battery.level,
            charging: battery.charging
          });

          const updateBattery = () => {
            setBatteryInfo({
              level: battery.level,
              charging: battery.charging
            });
          };

          battery.addEventListener('levelchange', updateBattery);
          battery.addEventListener('chargingchange', updateBattery);

          return () => {
            battery.removeEventListener('levelchange', updateBattery);
            battery.removeEventListener('chargingchange', updateBattery);
          };
        } catch (error) {
          console.warn('Battery API not supported');
        }
      }
    };

    checkBattery();
  }, []);

  // Performance monitoring
  useEffect(() => {
    performanceMonitor.startTiming('mobile-layout-render');
    
    return () => {
      performanceMonitor.endTiming('mobile-layout-render');
    };
  });

  // Handle widget actions
  const handleWidgetActionInternal = useCallback((action: string, widgetId: string) => {
    performanceMonitor.startTiming(`widget-action-${action}`);
    
    handleWidgetAction(action, widgetId);
    onWidgetAction?.(action, widgetId);
    
    performanceMonitor.endTiming(`widget-action-${action}`);
  }, [handleWidgetAction, onWidgetAction]);

  // Render swipe view
  const renderSwipeView = () => {
    if (filteredWidgets.length === 0) {
      return (
        <div className="flex-1 flex items-center justify-center mobile-empty-state">
          <div className="text-center p-6">
            <div className="mobile-empty-state-icon text-4xl mb-4">📊</div>
            <h3 className="text-lg font-medium mb-2">
              {searchQuery ? '未找到匹配的组件' : '暂无组件'}
            </h3>
            <p className="text-gray-600 mb-4">
              {searchQuery 
                ? `没有找到包含"${searchQuery}"的组件` 
                : '添加一些组件来开始使用仪表板'
              }
            </p>
            {!searchQuery && (
              <Button onClick={onAddWidget} className="touch-optimized">
                <Plus className="h-4 w-4 mr-2" />
                添加组件
              </Button>
            )}
          </div>
        </div>
      );
    }

    return (
      <div 
        className="flex-1 flex flex-col touch-optimized"
        onTouchStart={handleTouchStartPull}
        onTouchMove={handleTouchMovePull}
        onTouchEnd={handleTouchEndPull}
        ref={containerRef}
      >
        {/* Pull to Refresh Indicator */}
        <div 
          className={`pull-to-refresh-indicator ${isPulling ? 'pulling' : ''} ${isRefreshing ? 'refreshing' : ''}`}
          style={{ transform: `translateY(${pullToRefreshDistance - 60}px)` }}
        >
          <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </div>

        {/* Widget Navigation */}
        <div className="flex items-center justify-between p-4 bg-white border-b">
          <Button
            variant="ghost"
            size="sm"
            onClick={prevWidget}
            disabled={filteredWidgets.length <= 1}
            className="touch-optimized tap-feedback"
          >
            ←
          </Button>
          
          <div className="text-center flex-1">
            <h3 className="font-medium truncate">{currentWidget?.title}</h3>
            <p className="text-xs text-gray-500">
              {currentWidgetIndex + 1} / {filteredWidgets.length}
            </p>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={nextWidget}
            disabled={filteredWidgets.length <= 1}
            className="touch-optimized tap-feedback"
          >
            →
          </Button>
        </div>

        {/* Widget Content */}
        <div className="flex-1 p-4">
          {currentWidget && (
            <MobileWidgetCard
              widget={currentWidget}
              realtimeData={realtimeData[currentWidget.type]}
              isLoading={isLoading}
              onAction={handleWidgetActionInternal}
              size="large"
              className="h-full"
            />
          )}
        </div>

        {/* Widget Indicators */}
        <div className="flex justify-center space-x-2 p-4 safe-area-bottom">
          {filteredWidgets.map((_, index) => (
            <button
              key={index}
              onClick={() => goToWidget(index)}
              className={`w-3 h-3 rounded-full transition-all duration-200 touch-optimized ${
                index === currentWidgetIndex 
                  ? 'bg-blue-500 scale-125' 
                  : 'bg-gray-300 hover:bg-gray-400'
              }`}
            />
          ))}
        </div>
      </div>
    );
  };

  // Render grid view
  const renderGridView = () => {
    return (
      <div 
        className="flex-1 p-4 overflow-auto smooth-scroll"
        onTouchStart={handleTouchStartPull}
        onTouchMove={handleTouchMovePull}
        onTouchEnd={handleTouchEndPull}
        ref={containerRef}
      >
        {/* Pull to Refresh Indicator */}
        <div 
          className={`pull-to-refresh-indicator ${isPulling ? 'pulling' : ''} ${isRefreshing ? 'refreshing' : ''}`}
          style={{ transform: `translateY(${pullToRefreshDistance - 60}px)` }}
        >
          <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </div>

        <div className={`grid gap-4 ${
          orientation === 'landscape' 
            ? 'grid-cols-2 lg:grid-cols-3' 
            : 'grid-cols-1 sm:grid-cols-2'
        }`}>
          {filteredWidgets.map((widget) => (
            <MobileWidgetCard
              key={widget.id}
              widget={widget}
              realtimeData={realtimeData[widget.type]}
              isLoading={isLoading}
              onAction={handleWidgetActionInternal}
              size={orientation === 'landscape' ? 'small' : 'medium'}
            />
          ))}
        </div>

        {filteredWidgets.length === 0 && (
          <div className="mobile-empty-state">
            <div className="mobile-empty-state-icon text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-medium mb-2">未找到组件</h3>
            <p className="text-gray-600">尝试调整搜索条件</p>
          </div>
        )}
      </div>
    );
  };

  // Render list view
  const renderListView = () => {
    return (
      <div 
        className="flex-1 overflow-auto smooth-scroll"
        onTouchStart={handleTouchStartPull}
        onTouchMove={handleTouchMovePull}
        onTouchEnd={handleTouchEndPull}
        ref={containerRef}
      >
        {/* Pull to Refresh Indicator */}
        <div 
          className={`pull-to-refresh-indicator ${isPulling ? 'pulling' : ''} ${isRefreshing ? 'refreshing' : ''}`}
          style={{ transform: `translateY(${pullToRefreshDistance - 60}px)` }}
        >
          <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </div>

        {filteredWidgets.map((widget) => (
          <div key={widget.id} className="border-b border-gray-200 last:border-b-0 p-4">
            <MobileWidgetCard
              widget={widget}
              realtimeData={realtimeData[widget.type]}
              isLoading={isLoading}
              onAction={handleWidgetActionInternal}
              size="small"
              className="h-32"
            />
          </div>
        ))}

        {filteredWidgets.length === 0 && (
          <div className="mobile-empty-state">
            <div className="mobile-empty-state-icon text-4xl mb-4">📋</div>
            <h3 className="text-lg font-medium mb-2">列表为空</h3>
            <p className="text-gray-600">没有找到匹配的组件</p>
          </div>
        )}
      </div>
    );
  };

  if (!isMobile) {
    return null; // 非移动端不渲染
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 safe-area-all">
      {/* Status Bar */}
      <div className="flex items-center justify-between px-4 py-1 bg-gray-900 text-white text-xs safe-area-top">
        <div className="flex items-center space-x-2">
          <span>{new Date().toLocaleTimeString()}</span>
          {!isOnline && <WifiOff className="h-3 w-3 text-red-400" />}
          {isOnline && <Wifi className="h-3 w-3 text-green-400" />}
        </div>
        
        <div className="flex items-center space-x-2">
          {batteryInfo && (
            <div className="flex items-center space-x-1">
              {batteryInfo.level < 0.2 ? (
                <BatteryLow className="h-3 w-3 text-red-400" />
              ) : (
                <Battery className="h-3 w-3" />
              )}
              <span>{Math.round(batteryInfo.level * 100)}%</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <MobileNavigation
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        notificationsEnabled={notificationsEnabled}
        onToggleNotifications={toggleNotifications}
        connectionStatus={connectionStatus}
        onRefresh={handlePullToRefresh}
        isRefreshing={isRefreshing}
        widgetCount={filteredWidgets.length}
        onShowSettings={onShowSettings}
      />

      {/* Offline Message */}
      {showOfflineMessage && (
        <div className="bg-red-500 text-white px-4 py-2 text-sm animate-in slide-in-from-top duration-300">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4" />
            <span>网络连接已断开，部分功能可能不可用</span>
          </div>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'swipe' && renderSwipeView()}
        {viewMode === 'grid' && renderGridView()}
        {viewMode === 'list' && renderListView()}
      </div>

      {/* Gesture Hints */}
      {shouldShowGestureHints() && (
        <div className="gesture-hint">
          左右滑动切换组件，下拉刷新数据
        </div>
      )}

      {/* Bottom Safe Area */}
      <div className="safe-area-bottom" />
    </div>
  );
};

export default MobileLayout;