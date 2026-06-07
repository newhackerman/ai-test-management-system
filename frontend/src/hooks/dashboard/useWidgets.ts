import { useState, useEffect, useCallback } from 'react';
import { widgetService, WidgetDefinition, WidgetAvailability } from '@/services/dashboard/widgetService';
import { toast } from 'react-hot-toast';

export interface EnhancedWidgetDefinition extends WidgetDefinition {
  availability?: WidgetAvailability;
}

export const useWidgets = (roleType?: string, userId?: number) => {
  const [widgets, setWidgets] = useState<EnhancedWidgetDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load widget definitions
  const loadWidgets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let widgetDefinitions: WidgetDefinition[];
      
      if (roleType) {
        widgetDefinitions = await widgetService.getWidgetDefinitionsForRole(roleType);
      } else {
        widgetDefinitions = await widgetService.getWidgetDefinitions();
      }

      // Check availability for each widget
      const enhancedWidgets = await Promise.all(
        widgetDefinitions.map(async (widget) => {
          try {
            const availability = await widgetService.checkWidgetAvailability(widget.type, userId);
            return {
              ...widget,
              availability
            };
          } catch (error) {
            // If availability check fails, assume available
            return {
              ...widget,
              availability: { available: true }
            };
          }
        })
      );

      setWidgets(enhancedWidgets);
    } catch (err: any) {
      setError(err.message || '加载组件定义失败');
      toast.error('加载组件定义失败');
    } finally {
      setLoading(false);
    }
  }, [roleType, userId]);

  // Get widget preview data
  const getWidgetPreview = useCallback(async (widgetType: string, config?: any) => {
    try {
      return await widgetService.getWidgetPreview(widgetType, config);
    } catch (error: any) {
      toast.error('获取组件预览失败');
      throw error;
    }
  }, []);

  // Validate widget configuration
  const validateWidgetConfig = useCallback(async (widgetType: string, config: any) => {
    try {
      return await widgetService.validateWidgetConfig(widgetType, config);
    } catch (error: any) {
      toast.error('验证组件配置失败');
      throw error;
    }
  }, []);

  // Filter widgets by category
  const getWidgetsByCategory = useCallback((category: string) => {
    if (category === 'all') {
      return widgets;
    }
    return widgets.filter(widget => widget.category === category);
  }, [widgets]);

  // Filter available widgets only
  const getAvailableWidgets = useCallback(() => {
    return widgets.filter(widget => widget.availability?.available);
  }, [widgets]);

  // Search widgets
  const searchWidgets = useCallback((searchTerm: string) => {
    if (!searchTerm.trim()) {
      return widgets;
    }

    const searchLower = searchTerm.toLowerCase();
    return widgets.filter(widget => 
      widget.name.toLowerCase().includes(searchLower) ||
      widget.description.toLowerCase().includes(searchLower) ||
      widget.tags?.some(tag => tag.toLowerCase().includes(searchLower))
    );
  }, [widgets]);

  // Sort widgets
  const sortWidgets = useCallback((widgets: EnhancedWidgetDefinition[], sortBy: 'name' | 'popularity' | 'recent') => {
    return [...widgets].sort((a, b) => {
      switch (sortBy) {
        case 'popularity':
          return (b.popularity || 0) - (a.popularity || 0);
        case 'recent':
          return new Date(b.lastUpdated || 0).getTime() - new Date(a.lastUpdated || 0).getTime();
        case 'name':
        default:
          return a.name.localeCompare(b.name);
      }
    });
  }, []);

  // Get widget categories with counts
  const getCategories = useCallback((showOnlyAvailable: boolean = false) => {
    const targetWidgets = showOnlyAvailable ? getAvailableWidgets() : widgets;
    const availableWidgets = getAvailableWidgets();

    const categories = [
      'statistics', 'charts', 'status', 'lists', 'other'
    ];

    return [
      {
        id: 'all',
        name: '全部',
        count: targetWidgets.length,
        availableCount: availableWidgets.length
      },
      ...categories.map(category => ({
        id: category,
        name: getCategoryDisplayName(category),
        count: targetWidgets.filter(w => w.category === category).length,
        availableCount: availableWidgets.filter(w => w.category === category).length
      }))
    ];
  }, [widgets, getAvailableWidgets]);

  const getCategoryDisplayName = (category: string): string => {
    const names: { [key: string]: string } = {
      statistics: '统计',
      charts: '图表',
      status: '状态',
      lists: '列表',
      other: '其他'
    };
    return names[category] || category;
  };

  useEffect(() => {
    loadWidgets();
  }, [loadWidgets]);

  return {
    widgets,
    loading,
    error,
    loadWidgets,
    getWidgetPreview,
    validateWidgetConfig,
    getWidgetsByCategory,
    getAvailableWidgets,
    searchWidgets,
    sortWidgets,
    getCategories
  };
};