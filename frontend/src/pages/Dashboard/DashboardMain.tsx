// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  Settings, 
  Edit3, 
  RotateCcw, 
  Plus, 
  Palette, 
  Wifi, 
  WifiOff,
  Layout,
  Save
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { RealtimeProvider, useRealtimeContext, WebSocketClient } from '@/components/dashboard/Realtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import WidgetLibrary from '@/components/dashboard/WidgetLibrary';
import ColorSchemeSelector from '@/components/dashboard/ColorSchemeSelector';
import MobileDashboard from '@/components/dashboard/Mobile/MobileDashboard';
import MobileLayout from '@/components/dashboard/Mobile/MobileLayout';

interface DashboardMainProps {
  roleType?: string;
}

// 鍐呴儴缁勪欢锛屼娇鐢≧ealtimeContext
const DashboardMainContent: React.FC<DashboardMainProps> = ({ roleType }) => {
  const { user } = useAuth();
  const {
    dashboardConfig,
    widgets,
    loading,
    error,
    saveDashboardLayout,
    resetDashboard,
    addWidget,
    removeWidget,
    updateWidget
  } = useDashboard(roleType || user?.role || 'USER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe,
    connectionStatus,
    connectionMetrics,
    retryConnection
  } = useRealtimeContext();

  const [editMode, setEditMode] = useState(false);
  const [showWidgetLibrary, setShowWidgetLibrary] = useState(false);
  const [showColorSchemes, setShowColorSchemes] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Subscribe to real-time data updates when connected
    if (isConnected) {
      const events = ['project_update', 'requirement_update', 'test_update', 'system_update'];
      subscribe(events);
    }
    
    return () => {
      if (isConnected) {
        const events = ['project_update', 'requirement_update', 'test_update', 'system_update'];
        unsubscribe(events);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Check for mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleLayoutChange = (newLayout: any) => {
    if (editMode) {
      setHasUnsavedChanges(true);
      // Store layout changes temporarily
    }
  };

  const handleSaveLayout = async () => {
    try {
      await saveDashboardLayout();
      setHasUnsavedChanges(false);
      setEditMode(false);
    } catch (error) {
      console.error('淇濆瓨甯冨眬澶辫触:', error);
    }
  };

  const handleResetLayout = async () => {
    try {
      await resetDashboard();
      setHasUnsavedChanges(false);
      setEditMode(false);
    } catch (error) {
      console.error('閲嶇疆甯冨眬澶辫触:', error);
    }
  };

  const handleAddWidget = async (widgetType: string, config: any) => {
    try {
      await addWidget(widgetType, config);
      setShowWidgetLibrary(false);
    } catch (error) {
      console.error('娣诲姞缁勪欢澶辫触:', error);
    }
  };

  const handleRemoveWidget = async (widgetId: string) => {
    try {
      await removeWidget(widgetId);
    } catch (error) {
      console.error('鍒犻櫎缁勪欢澶辫触:', error);
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-500';
      case 'connecting': return 'bg-yellow-500';
      case 'disconnected': return 'bg-red-500';
      default: return 'bg-gray-500 dark:bg-gray-800/50';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中...';
      case 'disconnected': return '已断开';
      default: return '未知状态';
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-gray-300 to-gray-400 rounded-lg h-32"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-300 rounded-lg h-24"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <div className="text-red-500 mb-4 dark:text-red-400">
              <Settings className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold mb-2">鍔犺浇澶辫触</h3>
            <p className="text-gray-600 mb-4 dark:text-gray-400">{error}</p>
            <Button onClick={() => window.location.reload()}>
              閲嶆柊鍔犺浇
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render mobile version
  if (isMobile) {
    return (
      <>
        <MobileLayout
          widgets={widgets}
          realtimeData={realtimeData}
          isLoading={loading}
          connectionStatus={connectionStatus}
          onAddWidget={() => setShowWidgetLibrary(true)}
          onShowColorSchemes={() => setShowColorSchemes(true)}
          onShowSettings={() => setShowColorSchemes(true)}
          onRefresh={async () => {
            // Implement refresh logic
            window.location.reload();
          }}
          onShare={(widgetId) => {
            // Implement share logic
            if (navigator.share) {
              navigator.share({
                title: '仪表盘组件',
                text: `查看我的 ${widgets.find(w => w.id === widgetId)?.title || '仪表盘'} 组件`,
                url: window.location.href
              });
            }
          }}
          onExport={(widgetId) => {
            // Implement export logic
            console.log('Export widget:', widgetId);
          }}
          onWidgetAction={(action, widgetId) => {
            console.log('Widget action:', action, widgetId);
          }}
        />
        
        {/* Modals */}
        {showWidgetLibrary && (
          <WidgetLibrary
            isOpen={showWidgetLibrary}
            onClose={() => setShowWidgetLibrary(false)}
            onAddWidget={handleAddWidget}
            roleType={roleType || user?.role}
          />
        )}

        {showColorSchemes && (
          <ColorSchemeSelector
            isOpen={showColorSchemes}
            onClose={() => setShowColorSchemes(false)}
          />
        )}
      </>
    );
  }

  return (
    <WebSocketClient
      autoReconnect={true}
      reconnectInterval={3000}
      maxReconnectAttempts={5}
      enableHeartbeat={true}
      heartbeatInterval={30000}
    >
      <div className="dashboard-main min-h-screen bg-gray-50 dark:bg-gray-800/50">
        {/* Dashboard Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 dark:bg-gray-800 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {dashboardConfig?.dashboard_name || '我的仪表盘'}
                </h1>
              </div>
              
              {/* Enhanced Connection Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${getConnectionStatusColor()}`}>
                  {connectionStatus === 'connecting' && (
                    <div className="w-full h-full rounded-full animate-ping bg-current opacity-75"></div>
                  )}
                </div>
                <span className="text-sm text-gray-600 flex items-center space-x-1 dark:text-gray-400">
                  {isConnected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                  <span>{getConnectionStatusText()}</span>
                  {isConnected && connectionMetrics.uptime > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {Math.floor(connectionMetrics.uptime / 60)}:{(connectionMetrics.uptime % 60).toString().padStart(2, '0')}
                    </Badge>
                  )}
                </span>
                {!isConnected && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={retryConnection}
                    className="text-xs"
                  >
                    閲嶈繛
                  </Button>
                )}
              </div>
            </div>
          
          {/* Header Actions */}
          <div className="flex items-center space-x-2">
            {hasUnsavedChanges && (
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                鏈繚瀛樼殑鏇存敼
              </Badge>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowColorSchemes(true)}
              className="flex items-center space-x-1"
            >
              <Palette className="h-4 w-4" />
              <span>閰嶈壊</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowWidgetLibrary(true)}
              disabled={!editMode}
              className="flex items-center space-x-1"
            >
              <Plus className="h-4 w-4" />
              <span>缁勪欢</span>
            </Button>
            
            {editMode && hasUnsavedChanges && (
              <Button
                size="sm"
                onClick={handleSaveLayout}
                className="flex items-center space-x-1"
              >
                <Save className="h-4 w-4" />
                <span>淇濆瓨</span>
              </Button>
            )}
            
            {editMode && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetLayout}
                className="flex items-center space-x-1 text-red-600 border-red-600 hover:bg-red-50 dark:text-red-400 dark:bg-red-900/20"
              >
                <RotateCcw className="h-4 w-4" />
                <span>閲嶇疆</span>
              </Button>
            )}
            
            <Button
              variant={editMode ? "default" : "outline"}
              size="sm"
              onClick={() => {
                if (editMode && hasUnsavedChanges) {
                  // Show confirmation dialog
                  if (window.confirm('当前有未保存的更改，确定要退出编辑模式吗？')) {
                    setEditMode(false);
                    setHasUnsavedChanges(false);
                  }
                } else {
                  setEditMode(!editMode);
                }
              }}
              className="flex items-center space-x-1"
            >
              {editMode ? <Layout className="h-4 w-4" /> : <Edit3 className="h-4 w-4" />}
              <span>{editMode ? '完成编辑' : '编辑布局'}</span>
            </Button>
          </div>
        </div>

        </div>
        {/* Dashboard Content */}
        <div className="p-6">
          <DashboardGrid
            widgets={widgets}
            editMode={editMode}
            onLayoutChange={handleLayoutChange}
            onRemoveWidget={handleRemoveWidget}
            onUpdateWidget={updateWidget}
            realtimeData={realtimeData}
          />
        </div>

        {/* Modals */}
        {showWidgetLibrary && (
          <WidgetLibrary
            isOpen={showWidgetLibrary}
            onClose={() => setShowWidgetLibrary(false)}
            onAddWidget={handleAddWidget}
            roleType={roleType || user?.role}
          />
        )}

        {showColorSchemes && (
          <ColorSchemeSelector
            isOpen={showColorSchemes}
            onClose={() => setShowColorSchemes(false)}
          />
        )}
      </div>
    </WebSocketClient>
  );
};

// 涓荤粍浠讹紝鍖呰RealtimeProvider
const DashboardMain: React.FC<DashboardMainProps> = (props) => {
  return (
    <RealtimeProvider
      enableAnimations={true}
      enableNotifications={true}
      notificationDuration={3000}
    >
      <DashboardMainContent {...props} />
    </RealtimeProvider>
  );
};

export default DashboardMain;
