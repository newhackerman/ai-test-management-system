// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bell,
  BellOff,
  ChevronLeft,
  ChevronRight,
  Download,
  Grid3X3,
  List,
  Maximize2,
  Menu,
  MoreVertical,
  Palette,
  Plus,
  RefreshCw,
  Settings,
  Share,
  X,
} from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Widget } from '@/hooks/dashboard/useDashboard';
import { useResponsive } from '@/hooks/useResponsive';
import { touchFeedback, useTouchGesture } from '@/utils/touchGestures';
import WidgetContent from '../Widgets/WidgetContent';
import '../../../styles/mobile.css';

interface MobileDashboardProps {
  widgets: Widget[];
  realtimeData?: any;
  onAddWidget?: () => void;
  onShowColorSchemes?: () => void;
  onShowSettings?: () => void;
  onRefresh?: () => void | Promise<void>;
  onShare?: (widgetId: string) => void;
  onExport?: (widgetId: string) => void;
  isLoading?: boolean;
  connectionStatus?: 'connected' | 'connecting' | 'disconnected';
  notificationsEnabled?: boolean;
  onToggleNotifications?: () => void;
}

const connectionText = {
  connected: '已连接',
  connecting: '连接中',
  disconnected: '未连接',
};

const MobileDashboard: React.FC<MobileDashboardProps> = ({
  widgets,
  realtimeData = {},
  onAddWidget,
  onShowColorSchemes,
  onShowSettings,
  onRefresh,
  onShare,
  onExport,
  isLoading = false,
  connectionStatus = 'disconnected',
  notificationsEnabled = true,
  onToggleNotifications,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [currentWidgetIndex, setCurrentWidgetIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'swipe' | 'grid' | 'list'>('swipe');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showWidgetActions, setShowWidgetActions] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [pullToRefreshDistance, setPullToRefreshDistance] = useState(0);
  const [isPulling, setIsPulling] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const { orientation } = useResponsive();
  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGesture();

  const filteredWidgets = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword) return widgets;

    return widgets.filter((widget) =>
      `${widget.title} ${widget.type}`.toLowerCase().includes(keyword),
    );
  }, [searchQuery, widgets]);

  useEffect(() => {
    if (currentWidgetIndex >= filteredWidgets.length) {
      setCurrentWidgetIndex(0);
    }
  }, [currentWidgetIndex, filteredWidgets.length]);

  const nextWidget = useCallback(() => {
    if (filteredWidgets.length <= 1) return;
    setCurrentWidgetIndex((prev) => (prev < filteredWidgets.length - 1 ? prev + 1 : 0));
    touchFeedback.vibrate(10);
  }, [filteredWidgets.length]);

  const prevWidget = useCallback(() => {
    if (filteredWidgets.length <= 1) return;
    setCurrentWidgetIndex((prev) => (prev > 0 ? prev - 1 : filteredWidgets.length - 1));
    touchFeedback.vibrate(10);
  }, [filteredWidgets.length]);

  const handlePullToRefresh = useCallback(async () => {
    if (isRefreshing || !onRefresh) return;

    setIsRefreshing(true);
    touchFeedback.vibrate([10, 50, 10]);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
      setPullToRefreshDistance(0);
      setIsPulling(false);
    }
  }, [isRefreshing, onRefresh]);

  const handleSwipeGesture = useCallback(
    (result: any) => {
      if (result.type === 'swipe' && viewMode === 'swipe') {
        if (result.direction === 'left') nextWidget();
        if (result.direction === 'right') prevWidget();
        if (result.direction === 'down' && result.distance > 100) handlePullToRefresh();
      }

      if (result.type === 'longPress') {
        const currentWidget = filteredWidgets[currentWidgetIndex];
        if (currentWidget) {
          setShowWidgetActions(currentWidget.id);
          touchFeedback.vibrate([50, 100, 50]);
        }
      }
    },
    [currentWidgetIndex, filteredWidgets, handlePullToRefresh, nextWidget, prevWidget, viewMode],
  );

  const handleTouchStartPull = useCallback(
    (event: React.TouchEvent) => {
      if (!containerRef.current || containerRef.current.scrollTop === 0) {
        handleTouchStart(event, handleSwipeGesture);
      }
    },
    [handleSwipeGesture, handleTouchStart],
  );

  const handleTouchMovePull = useCallback(
    (event: React.TouchEvent) => {
      handleTouchMove(event, (result: any) => {
        if (result.type === 'pan' && result.deltaY > 0 && (!containerRef.current || containerRef.current.scrollTop === 0)) {
          const distance = Math.min(result.deltaY * 0.5, 100);
          setPullToRefreshDistance(distance);
          setIsPulling(distance > 50);
        }
      });
    },
    [handleTouchMove],
  );

  const handleTouchEndPull = useCallback(
    (event: React.TouchEvent) => {
      handleTouchEnd(event, handleSwipeGesture);
      if (isPulling && pullToRefreshDistance > 50) {
        handlePullToRefresh();
      } else {
        setPullToRefreshDistance(0);
        setIsPulling(false);
      }
    },
    [handlePullToRefresh, handleSwipeGesture, handleTouchEnd, isPulling, pullToRefreshDistance],
  );

  const handleWidgetAction = useCallback(
    (action: 'share' | 'export' | 'fullscreen', widgetId: string) => {
      if (action === 'share') onShare?.(widgetId);
      if (action === 'export') onExport?.(widgetId);
      if (action === 'fullscreen') {
        const element = document.querySelector(`[data-widget-id="${widgetId}"]`) as HTMLElement | null;
        element?.requestFullscreen?.();
      }
      setShowWidgetActions(null);
    },
    [onExport, onShare],
  );

  const renderEmpty = (title: string, description: string) => (
    <div className="mobile-empty-state flex h-full items-center justify-center p-6 text-center">
      <div>
        <div className="mb-4 text-4xl">□</div>
        <h3 className="mb-2 text-lg font-medium">{title}</h3>
        <p className="mb-4 text-gray-600">{description}</p>
        {!searchQuery && onAddWidget && (
          <Button onClick={onAddWidget} className="touch-optimized">
            <Plus className="mr-2 h-4 w-4" />
            添加组件
          </Button>
        )}
      </div>
    </div>
  );

  const renderWidgetActions = (widget: Widget) =>
    showWidgetActions === widget.id && (
      <div className="fixed inset-0 z-50 flex items-end bg-black/50">
        <div className="safe-area-bottom w-full rounded-t-lg bg-white p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-medium">{widget.title}</h3>
            <Button variant="ghost" size="sm" onClick={() => setShowWidgetActions(null)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="outline" onClick={() => handleWidgetAction('share', widget.id)} className="touch-optimized justify-center gap-2">
              <Share className="h-4 w-4" />
              分享
            </Button>
            <Button variant="outline" onClick={() => handleWidgetAction('export', widget.id)} className="touch-optimized justify-center gap-2">
              <Download className="h-4 w-4" />
              导出
            </Button>
            <Button variant="outline" onClick={() => handleWidgetAction('fullscreen', widget.id)} className="touch-optimized col-span-2 justify-center gap-2">
              <Maximize2 className="h-4 w-4" />
              全屏查看
            </Button>
          </div>
        </div>
      </div>
    );

  const renderWidgetContent = (widget: Widget, className = '') => (
    <div data-widget-id={widget.id} className={className}>
      {isLoading ? (
        <div className="mobile-loading">
          <div className="mobile-loading-spinner" />
          <p className="text-sm text-gray-500">加载中...</p>
        </div>
      ) : (
        <WidgetContent widget={widget} realtimeData={realtimeData[widget.type]} />
      )}
    </div>
  );

  const pullIndicator = (
    <div
      className={`pull-to-refresh-indicator ${isPulling ? 'pulling' : ''} ${isRefreshing ? 'refreshing' : ''}`}
      style={{ transform: `translateY(${pullToRefreshDistance - 60}px)` }}
    >
      <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
    </div>
  );

  const renderSwipeView = () => {
    if (filteredWidgets.length === 0) {
      return renderEmpty(
        searchQuery ? '未找到匹配的组件' : '暂无组件',
        searchQuery ? `没有找到包含“${searchQuery}”的组件` : '添加组件后即可在移动端查看仪表盘。',
      );
    }

    const currentWidget = filteredWidgets[currentWidgetIndex];

    return (
      <div className="touch-optimized flex flex-1 flex-col" onTouchStart={handleTouchStartPull} onTouchMove={handleTouchMovePull} onTouchEnd={handleTouchEndPull}>
        {pullIndicator}
        <div className="safe-area-top flex items-center justify-between border-b bg-white p-4">
          <Button variant="ghost" size="sm" onClick={prevWidget} disabled={filteredWidgets.length <= 1} className="touch-optimized tap-feedback">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0 flex-1 text-center">
            <h3 className="truncate font-medium">{currentWidget.title}</h3>
            <p className="text-xs text-gray-500">
              {currentWidgetIndex + 1} / {filteredWidgets.length}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowWidgetActions(currentWidget.id)} className="touch-optimized">
              <MoreVertical className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={nextWidget} disabled={filteredWidgets.length <= 1} className="touch-optimized tap-feedback">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden p-4">
          <Card className={`mobile-card h-full ${orientation === 'landscape' ? 'landscape-compact' : ''}`}>
            <CardContent className="smooth-scroll h-full overflow-auto p-4">
              {renderWidgetContent(currentWidget, 'h-full')}
            </CardContent>
          </Card>
        </div>
        <div className="safe-area-bottom flex justify-center gap-2 p-4">
          {filteredWidgets.map((widget, index) => (
            <button
              key={widget.id}
              onClick={() => {
                setCurrentWidgetIndex(index);
                touchFeedback.vibrate(5);
              }}
              className={`touch-optimized h-3 w-3 rounded-full transition-all ${index === currentWidgetIndex ? 'scale-125 bg-blue-500' : 'bg-gray-300'}`}
              aria-label={`切换到 ${widget.title}`}
            />
          ))}
        </div>
        {renderWidgetActions(currentWidget)}
      </div>
    );
  };

  const renderGridView = () => (
    <div className="smooth-scroll flex-1 overflow-auto p-4" ref={containerRef} onTouchStart={handleTouchStartPull} onTouchMove={handleTouchMovePull} onTouchEnd={handleTouchEndPull}>
      {pullIndicator}
      {filteredWidgets.length === 0 ? (
        renderEmpty('未找到组件', '请调整搜索条件或添加新的仪表盘组件。')
      ) : (
        <div className={`grid gap-4 ${orientation === 'landscape' ? 'grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2'}`}>
          {filteredWidgets.map((widget) => (
            <Card key={widget.id} className={`mobile-card touch-optimized tap-feedback ${orientation === 'landscape' ? 'h-48 landscape-compact' : 'h-64'}`}>
              <CardHeader className="mobile-card-header pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="truncate text-sm">{widget.title}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowWidgetActions(widget.id)} className="h-7 w-7 p-0">
                    <MoreVertical className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className={`mobile-card-content overflow-hidden ${orientation === 'landscape' ? 'h-32' : 'h-48'}`}>
                {renderWidgetContent(widget, 'h-full')}
              </CardContent>
              {renderWidgetActions(widget)}
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  const renderListView = () => (
    <div className="smooth-scroll flex-1 overflow-auto" ref={containerRef} onTouchStart={handleTouchStartPull} onTouchMove={handleTouchMovePull} onTouchEnd={handleTouchEndPull}>
      {pullIndicator}
      {filteredWidgets.length === 0 ? (
        renderEmpty('列表为空', '没有找到匹配的组件。')
      ) : (
        filteredWidgets.map((widget) => (
          <div key={widget.id} className="touch-optimized border-b border-gray-200 last:border-b-0">
            <div className="p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="min-w-0 flex-1 truncate font-medium">{widget.title}</h3>
                <Button variant="ghost" size="sm" onClick={() => setShowWidgetActions(widget.id)} className="ml-2 h-7 w-7 p-0">
                  <MoreVertical className="h-3 w-3" />
                </Button>
              </div>
              {renderWidgetContent(widget, `${orientation === 'landscape' ? 'h-24' : 'h-32'} overflow-hidden`)}
            </div>
            {renderWidgetActions(widget)}
          </div>
        ))
      )}
    </div>
  );

  return (
    <div className="safe-area-all flex h-screen flex-col bg-gray-50">
      <div className="safe-area-top flex items-center justify-between border-b bg-white px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-lg font-semibold">仪表盘</h1>
            <span
              className={`h-2 w-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-500' : connectionStatus === 'connecting' ? 'animate-pulse bg-yellow-500' : 'bg-red-500'
              }`}
              title={connectionText[connectionStatus]}
            />
          </div>
          <p className="text-xs text-gray-500">
            {filteredWidgets.length} 个组件 · {orientation === 'landscape' ? '横屏' : '竖屏'}模式
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              type="text"
              placeholder="搜索组件..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="w-32 rounded-lg border border-gray-300 px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2">
                <X className="h-3 w-3 text-gray-400" />
              </button>
            )}
          </div>

          <Button variant="ghost" size="sm" onClick={onToggleNotifications} className="touch-optimized" title={notificationsEnabled ? '关闭通知' : '开启通知'}>
            {notificationsEnabled ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
          </Button>

          <div className="flex rounded-lg bg-gray-100 p-1">
            <ViewButton active={viewMode === 'swipe'} onClick={() => setViewMode('swipe')} label="滑动视图">
              <ChevronLeft className="h-4 w-4" />
            </ViewButton>
            <ViewButton active={viewMode === 'grid'} onClick={() => setViewMode('grid')} label="网格视图">
              <Grid3X3 className="h-4 w-4" />
            </ViewButton>
            <ViewButton active={viewMode === 'list'} onClick={() => setViewMode('list')} label="列表视图">
              <List className="h-4 w-4" />
            </ViewButton>
          </div>

          <Button variant="ghost" size="sm" onClick={() => setShowMenu((value) => !value)} className="touch-optimized">
            {showMenu ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {showMenu && (
        <div className="animate-in slide-in-from-top border-b bg-white p-4 duration-200">
          <div className="grid grid-cols-2 gap-3">
            <MenuButton icon={<Plus className="h-4 w-4" />} label="添加组件" onClick={onAddWidget} close={() => setShowMenu(false)} />
            <MenuButton icon={<Palette className="h-4 w-4" />} label="配色方案" onClick={onShowColorSchemes} close={() => setShowMenu(false)} />
            <MenuButton icon={<RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />} label="刷新数据" onClick={handlePullToRefresh} close={() => setShowMenu(false)} disabled={isRefreshing} />
            <MenuButton icon={<Settings className="h-4 w-4" />} label="设置" onClick={onShowSettings} close={() => setShowMenu(false)} />
          </div>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        {viewMode === 'swipe' && renderSwipeView()}
        {viewMode === 'grid' && renderGridView()}
        {viewMode === 'list' && renderListView()}
      </div>

      {viewMode === 'swipe' && filteredWidgets.length > 1 && (
        <div className="gesture-hint">左右滑动切换组件，下拉刷新数据</div>
      )}
    </div>
  );
};

const ViewButton: React.FC<{ active: boolean; onClick: () => void; label: string; children: React.ReactNode }> = ({ active, onClick, label, children }) => (
  <button
    type="button"
    onClick={() => {
      onClick();
      touchFeedback.vibrate(5);
    }}
    className={`touch-optimized rounded p-1 ${active ? 'bg-white shadow-sm' : ''}`}
    title={label}
  >
    {children}
  </button>
);

const MenuButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  onClick?: () => void | Promise<void>;
  close: () => void;
  disabled?: boolean;
}> = ({ icon, label, onClick, close, disabled }) => (
  <Button
    variant="outline"
    size="sm"
    disabled={disabled}
    onClick={async () => {
      await onClick?.();
      close();
      touchFeedback.vibrate(10);
    }}
    className="touch-optimized justify-center gap-2"
  >
    {icon}
    {label}
  </Button>
);

export default MobileDashboard;
