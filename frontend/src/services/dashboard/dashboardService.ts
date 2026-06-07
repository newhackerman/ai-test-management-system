// @ts-nocheck
import { apiService } from '@/services/api-service';

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

export interface SaveLayoutRequest {
  layout_config: any;
  widget_configs: any[];
  refresh_interval?: number;
}

class DashboardService {
  private baseUrl = '/api/v1/dashboards';

  /**
   * Get dashboard configuration for a specific role
   */
  async getDashboardConfig(roleType: string): Promise<DashboardConfig> {
    try {
      const response = await apiService.get(`${this.baseUrl}/config/${roleType}`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        // No custom config found, return default
        return this.createDefaultConfig(roleType);
      }
      throw new Error(error.response?.data?.detail || '获取仪表盘配置失败');
    }
  }

  /**
   * Save dashboard layout configuration
   */
  async saveDashboardLayout(roleType: string, request: SaveLayoutRequest): Promise<void> {
    try {
      await apiService.post(`${this.baseUrl}/config/${roleType}/layout`, request);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '淇濆瓨浠〃鏉垮竷灞€澶辫触');
    }
  }

  /**
   * Reset dashboard layout to default
   */
  async resetDashboardLayout(roleType: string): Promise<void> {
    try {
      await apiService.post(`${this.baseUrl}/config/${roleType}/reset`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '閲嶇疆浠〃鏉垮竷灞€澶辫触');
    }
  }

  /**
   * Get overview data for dashboard
   */
  async getOverviewData(roleType: string, projectIds?: number[]): Promise<any> {
    try {
      const params = new URLSearchParams();
      params.append('role_type', roleType);
      if (projectIds && projectIds.length > 0) {
        projectIds.forEach(id => params.append('project_ids', id.toString()));
      }

      const response = await apiService.get(`${this.baseUrl}/data/overview?${params}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '鑾峰彇姒傝鏁版嵁澶辫触');
    }
  }

  /**
   * Get metrics data for specific metric type
   */
  async getMetricsData(
    metricType: string, 
    projectIds?: number[], 
    timeRange?: string
  ): Promise<any> {
    try {
      const params = new URLSearchParams();
      if (projectIds && projectIds.length > 0) {
        projectIds.forEach(id => params.append('project_ids', id.toString()));
      }
      if (timeRange) {
        params.append('time_range', timeRange);
      }

      const response = await apiService.get(`${this.baseUrl}/data/metrics/${metricType}?${params}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '鑾峰彇鎸囨爣鏁版嵁澶辫触');
    }
  }

  /**
   * Create default dashboard configuration
   */
  private createDefaultConfig(roleType: string): DashboardConfig {
    const defaultWidgets = this.getDefaultWidgets(roleType);
    
    return {
      id: 0,
      user_id: 0,
      role_type: roleType,
      dashboard_name: `${roleType}仪表盘`,
      is_default: true,
      layout_config: {},
      widget_configs: defaultWidgets,
      theme_config: {},
      refresh_interval: 30,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
  }

  /**
   * Get default widgets for each role
   */
  private getDefaultWidgets(roleType: string): any[] {
    const commonWidgets = [
      {
        id: 'overview-stats',
        type: 'stat_card',
        title: '姒傝缁熻',
        config: { metrics: ['total_projects', 'active_users', 'completion_rate'] },
        position: { x: 0, y: 0, w: 12, h: 2 }
      }
    ];

    switch (roleType.toUpperCase()) {
      case 'ADMIN':
        return [
          ...commonWidgets,
          {
            id: 'system-health',
            type: 'status_panel',
            title: '系统健康状态',
            config: { showServices: true, showResources: true },
            position: { x: 0, y: 2, w: 6, h: 4 }
          },
          {
            id: 'user-activity',
            type: 'trend_chart',
            title: '用户活跃度',
            config: { chartType: 'line', timeRange: '7d' },
            position: { x: 6, y: 2, w: 6, h: 4 }
          }
        ];

      case 'PROJECT_MANAGER':
        return [
          ...commonWidgets,
          {
            id: 'project-progress',
            type: 'progress_chart',
            title: '椤圭洰杩涘害',
            config: { showMilestones: true },
            position: { x: 0, y: 2, w: 8, h: 4 }
          },
          {
            id: 'team-workload',
            type: 'pie_chart',
            title: '鍥㈤槦宸ヤ綔璐熻浇',
            config: { showPercentage: true },
            position: { x: 8, y: 2, w: 4, h: 4 }
          }
        ];

      case 'DEVELOPER':
        return [
          ...commonWidgets,
          {
            id: 'my-tasks',
            type: 'task_list',
            title: '鎴戠殑浠诲姟',
            config: { showPriority: true, limit: 10 },
            position: { x: 0, y: 2, w: 6, h: 6 }
          },
          {
            id: 'code-quality',
            type: 'gauge_chart',
            title: '浠ｇ爜璐ㄩ噺',
            config: { showTrends: true },
            position: { x: 6, y: 2, w: 6, h: 3 }
          }
        ];

      case 'TESTER':
        return [
          ...commonWidgets,
          {
            id: 'test-execution',
            type: 'bar_chart',
            title: '娴嬭瘯鎵ц鎯呭喌',
            config: { showPassRate: true },
            position: { x: 0, y: 2, w: 8, h: 4 }
          },
          {
            id: 'defect-trends',
            type: 'line_chart',
            title: '缂洪櫡瓒嬪娍',
            config: { timeRange: '30d' },
            position: { x: 8, y: 2, w: 4, h: 4 }
          }
        ];

      default:
        return commonWidgets;
    }
  }
}

export const dashboardService = new DashboardService();
