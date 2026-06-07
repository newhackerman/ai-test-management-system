import { useState, useEffect, useCallback } from 'react';
import { dashboardService } from '@/services/dashboard/dashboardService';
import { toast } from 'react-hot-toast';

export interface DashboardConfig {
  id: number;
  user_id: number;
  role_type: string;
  dashboard_name: string;
  is_default: boolean;
  layout_config: any;
  widget_configs: any[];
  theme_config: any;
  refresh_interval: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Widget {
  id: string;
  type: string;
  title: string;
  config: any;
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  data?: any;
}

export const useDashboard = (roleType: string) => {
  const [dashboardConfig, setDashboardConfig] = useState<DashboardConfig | null>(null);
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingLayout, setPendingLayout] = useState<any>(null);

  // Load dashboard configuration
  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const config = await dashboardService.getDashboardConfig(roleType);
      setDashboardConfig(config);
      
      // Convert widget configs to widgets
      if (config.widget_configs) {
        const widgetList: Widget[] = config.widget_configs.map((widgetConfig: any, index: number) => ({
          id: widgetConfig.id || `widget-${index}`,
          type: widgetConfig.type,
          title: widgetConfig.title || widgetConfig.type,
          config: widgetConfig.config || {},
          position: widgetConfig.position || {
            x: (index % 4) * 3,
            y: Math.floor(index / 4) * 3,
            w: 3,
            h: 3
          }
        }));
        setWidgets(widgetList);
      }
    } catch (err: any) {
      setError(err.message || '加载仪表板配置失败');
      toast.error('加载仪表板配置失败');
    } finally {
      setLoading(false);
    }
  }, [roleType]);

  // Save dashboard layout
  const saveDashboardLayout = useCallback(async (layout?: any) => {
    try {
      const layoutToSave = layout || pendingLayout;
      if (!layoutToSave && !widgets.length) return;

      const widgetConfigs = widgets.map(widget => ({
        id: widget.id,
        type: widget.type,
        title: widget.title,
        config: widget.config,
        position: widget.position
      }));

      await dashboardService.saveDashboardLayout(roleType, {
        layout_config: layoutToSave || {},
        widget_configs: widgetConfigs
      });

      setPendingLayout(null);
      toast.success('布局保存成功');
      
      // Reload to get updated config
      await loadDashboard();
    } catch (err: any) {
      setError(err.message || '保存布局失败');
      toast.error('保存布局失败');
      throw err;
    }
  }, [roleType, widgets, pendingLayout, loadDashboard]);

  // Reset dashboard to default
  const resetDashboard = useCallback(async () => {
    try {
      await dashboardService.resetDashboardLayout(roleType);
      toast.success('布局重置成功');
      await loadDashboard();
    } catch (err: any) {
      setError(err.message || '重置布局失败');
      toast.error('重置布局失败');
      throw err;
    }
  }, [roleType, loadDashboard]);

  // Add widget
  const addWidget = useCallback(async (widgetType: string, config: any) => {
    try {
      const newWidget: Widget = {
        id: `widget-${Date.now()}`,
        type: widgetType,
        title: config.title || widgetType,
        config: config,
        position: {
          x: 0,
          y: 0,
          w: config.defaultWidth || 4,
          h: config.defaultHeight || 3
        }
      };

      setWidgets(prev => [...prev, newWidget]);
      toast.success('组件添加成功');
    } catch (err: any) {
      setError(err.message || '添加组件失败');
      toast.error('添加组件失败');
      throw err;
    }
  }, []);

  // Remove widget
  const removeWidget = useCallback(async (widgetId: string) => {
    try {
      setWidgets(prev => prev.filter(widget => widget.id !== widgetId));
      toast.success('组件删除成功');
    } catch (err: any) {
      setError(err.message || '删除组件失败');
      toast.error('删除组件失败');
      throw err;
    }
  }, []);

  // Update widget
  const updateWidget = useCallback(async (widgetId: string, updates: Partial<Widget>) => {
    try {
      setWidgets(prev => prev.map(widget => 
        widget.id === widgetId 
          ? { ...widget, ...updates }
          : widget
      ));
    } catch (err: any) {
      setError(err.message || '更新组件失败');
      toast.error('更新组件失败');
      throw err;
    }
  }, []);

  // Update layout (for drag and drop)
  const updateLayout = useCallback((layout: any) => {
    setPendingLayout(layout);
    
    // Update widget positions based on layout
    if (layout && Array.isArray(layout)) {
      setWidgets(prev => prev.map(widget => {
        const layoutItem = layout.find((item: any) => item.i === widget.id);
        if (layoutItem) {
          return {
            ...widget,
            position: {
              x: layoutItem.x,
              y: layoutItem.y,
              w: layoutItem.w,
              h: layoutItem.h
            }
          };
        }
        return widget;
      }));
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return {
    dashboardConfig,
    widgets,
    loading,
    error,
    saveDashboardLayout,
    resetDashboard,
    addWidget,
    removeWidget,
    updateWidget,
    updateLayout,
    reload: loadDashboard
  };
};