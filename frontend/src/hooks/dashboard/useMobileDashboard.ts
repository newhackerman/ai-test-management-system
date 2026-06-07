import { useState, useEffect, useCallback, useRef } from 'react';
import { useResponsive } from '@/hooks/useResponsive';
import { useTouchGesture, touchFeedback } from '@/utils/touchGestures';

interface MobileDashboardState {
  viewMode: 'swipe' | 'grid' | 'list';
  currentWidgetIndex: number;
  searchQuery: string;
  isRefreshing: boolean;
  showWidgetActions: string | null;
  pullToRefreshDistance: number;
  isPulling: boolean;
  notificationsEnabled: boolean;
}

interface MobileDashboardOptions {
  widgets: any[];
  onRefresh?: () => Promise<void>;
  onShare?: (widgetId: string) => void;
  onExport?: (widgetId: string) => void;
  autoSaveViewMode?: boolean;
}

/**
 * Mobile Dashboard Hook
 * 提供移动端仪表板的状态管理和交互逻辑
 */
export const useMobileDashboard = (options: MobileDashboardOptions) => {
  const { widgets, onRefresh, onShare, onExport, autoSaveViewMode = true } = options;
  const { isMobile, orientation, screenWidth, screenHeight } = useResponsive();
  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGesture();

  // State
  const [state, setState] = useState<MobileDashboardState>(() => {
    const savedViewMode = autoSaveViewMode 
      ? localStorage.getItem('mobile-dashboard-view-mode') as 'swipe' | 'grid' | 'list'
      : null;
    
    return {
      viewMode: savedViewMode || 'swipe',
      currentWidgetIndex: 0,
      searchQuery: '',
      isRefreshing: false,
      showWidgetActions: null,
      pullToRefreshDistance: 0,
      isPulling: false,
      notificationsEnabled: localStorage.getItem('mobile-notifications-enabled') !== 'false'
    };
  });

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const refreshTimeoutRef = useRef<NodeJS.Timeout>();

  // Filtered widgets based on search
  const filteredWidgets = widgets.filter(widget => 
    !state.searchQuery || 
    widget.title.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
    widget.type.toLowerCase().includes(state.searchQuery.toLowerCase())
  );

  // Update current widget index when filtered widgets change
  useEffect(() => {
    if (state.currentWidgetIndex >= filteredWidgets.length && filteredWidgets.length > 0) {
      setState(prev => ({ ...prev, currentWidgetIndex: 0 }));
    }
  }, [filteredWidgets.length, state.currentWidgetIndex]);

  // Save view mode to localStorage
  useEffect(() => {
    if (autoSaveViewMode) {
      localStorage.setItem('mobile-dashboard-view-mode', state.viewMode);
    }
  }, [state.viewMode, autoSaveViewMode]);

  // Save notifications preference
  useEffect(() => {
    localStorage.setItem('mobile-notifications-enabled', state.notificationsEnabled.toString());
  }, [state.notificationsEnabled]);

  // Navigation functions
  const nextWidget = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentWidgetIndex: prev.currentWidgetIndex < filteredWidgets.length - 1 
        ? prev.currentWidgetIndex + 1 
        : 0
    }));
    touchFeedback.vibrate(10);
  }, [filteredWidgets.length]);

  const prevWidget = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentWidgetIndex: prev.currentWidgetIndex > 0 
        ? prev.currentWidgetIndex - 1 
        : filteredWidgets.length - 1
    }));
    touchFeedback.vibrate(10);
  }, [filteredWidgets.length]);

  const goToWidget = useCallback((index: number) => {
    if (index >= 0 && index < filteredWidgets.length) {
      setState(prev => ({ ...prev, currentWidgetIndex: index }));
      touchFeedback.vibrate(5);
    }
  }, [filteredWidgets.length]);

  // View mode functions
  const setViewMode = useCallback((mode: 'swipe' | 'grid' | 'list') => {
    setState(prev => ({ ...prev, viewMode: mode }));
    touchFeedback.vibrate(5);
  }, []);

  // Search functions
  const setSearchQuery = useCallback((query: string) => {
    setState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const clearSearch = useCallback(() => {
    setState(prev => ({ ...prev, searchQuery: '' }));
  }, []);

  // Pull to refresh
  const handlePullToRefresh = useCallback(async () => {
    if (state.isRefreshing || !onRefresh) return;
    
    setState(prev => ({ ...prev, isRefreshing: true }));
    touchFeedback.vibrate([10, 50, 10]);
    
    try {
      await onRefresh();
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setState(prev => ({
        ...prev,
        isRefreshing: false,
        pullToRefreshDistance: 0,
        isPulling: false
      }));
    }
  }, [state.isRefreshing, onRefresh]);

  // Touch gesture handlers
  const handleSwipeGesture = useCallback((result: any) => {
    if (result.type === 'swipe' && state.viewMode === 'swipe') {
      if (result.direction === 'left') {
        nextWidget();
      } else if (result.direction === 'right') {
        prevWidget();
      } else if (result.direction === 'down' && result.distance > 100) {
        handlePullToRefresh();
      }
    } else if (result.type === 'longPress') {
      const currentWidget = filteredWidgets[state.currentWidgetIndex];
      if (currentWidget) {
        setState(prev => ({ ...prev, showWidgetActions: currentWidget.id }));
        touchFeedback.vibrate([50, 100, 50]);
      }
    }
  }, [state.viewMode, nextWidget, prevWidget, handlePullToRefresh, filteredWidgets, state.currentWidgetIndex]);

  // Touch event handlers for pull-to-refresh
  const handleTouchStartPull = useCallback((e: React.TouchEvent) => {
    if (containerRef.current?.scrollTop === 0) {
      handleTouchStart(e, handleSwipeGesture);
    }
  }, [handleTouchStart, handleSwipeGesture]);

  const handleTouchMovePull = useCallback((e: React.TouchEvent) => {
    handleTouchMove(e, (result) => {
      if (result.type === 'pan' && result.deltaY > 0 && containerRef.current?.scrollTop === 0) {
        const distance = Math.min(result.deltaY * 0.5, 100);
        setState(prev => ({
          ...prev,
          pullToRefreshDistance: distance,
          isPulling: distance > 50
        }));
      }
    });
  }, [handleTouchMove]);

  const handleTouchEndPull = useCallback((e: React.TouchEvent) => {
    const result = handleTouchEnd(e, handleSwipeGesture);
    
    if (state.isPulling && state.pullToRefreshDistance > 50) {
      handlePullToRefresh();
    } else {
      setState(prev => ({
        ...prev,
        pullToRefreshDistance: 0,
        isPulling: false
      }));
    }
  }, [handleTouchEnd, handleSwipeGesture, state.isPulling, state.pullToRefreshDistance, handlePullToRefresh]);

  // Widget actions
  const handleWidgetAction = useCallback((action: string, widgetId: string) => {
    switch (action) {
      case 'share':
        onShare?.(widgetId);
        break;
      case 'export':
        onExport?.(widgetId);
        break;
      case 'fullscreen':
        // Handle fullscreen view
        break;
    }
    setState(prev => ({ ...prev, showWidgetActions: null }));
  }, [onShare, onExport]);

  const closeWidgetActions = useCallback(() => {
    setState(prev => ({ ...prev, showWidgetActions: null }));
  }, []);

  // Notifications
  const toggleNotifications = useCallback(() => {
    setState(prev => ({ ...prev, notificationsEnabled: !prev.notificationsEnabled }));
    touchFeedback.vibrate(10);
  }, []);

  // Performance optimization: Auto-refresh management
  const startAutoRefresh = useCallback((interval: number = 30000) => {
    if (refreshTimeoutRef.current) {
      clearInterval(refreshTimeoutRef.current);
    }
    
    refreshTimeoutRef.current = setInterval(() => {
      if (!state.isRefreshing && document.visibilityState === 'visible') {
        handlePullToRefresh();
      }
    }, interval);
  }, [state.isRefreshing, handlePullToRefresh]);

  const stopAutoRefresh = useCallback(() => {
    if (refreshTimeoutRef.current) {
      clearInterval(refreshTimeoutRef.current);
      refreshTimeoutRef.current = undefined;
    }
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current) {
        clearInterval(refreshTimeoutRef.current);
      }
    };
  }, []);

  // Responsive adjustments
  const getOptimalViewMode = useCallback(() => {
    if (screenWidth < 480) return 'swipe';
    if (screenWidth < 768) return orientation === 'landscape' ? 'grid' : 'swipe';
    return 'grid';
  }, [screenWidth, orientation]);

  const shouldShowGestureHints = useCallback(() => {
    return state.viewMode === 'swipe' && filteredWidgets.length > 1;
  }, [state.viewMode, filteredWidgets.length]);

  return {
    // State
    ...state,
    filteredWidgets,
    currentWidget: filteredWidgets[state.currentWidgetIndex],
    
    // Device info
    isMobile,
    orientation,
    screenWidth,
    screenHeight,
    
    // Refs
    containerRef,
    
    // Navigation
    nextWidget,
    prevWidget,
    goToWidget,
    
    // View mode
    setViewMode,
    getOptimalViewMode,
    
    // Search
    setSearchQuery,
    clearSearch,
    
    // Refresh
    handlePullToRefresh,
    startAutoRefresh,
    stopAutoRefresh,
    
    // Touch handlers
    handleTouchStartPull,
    handleTouchMovePull,
    handleTouchEndPull,
    
    // Widget actions
    handleWidgetAction,
    closeWidgetActions,
    setShowWidgetActions: (widgetId: string | null) => 
      setState(prev => ({ ...prev, showWidgetActions: widgetId })),
    
    // Notifications
    toggleNotifications,
    
    // Utilities
    shouldShowGestureHints
  };
};

export default useMobileDashboard;