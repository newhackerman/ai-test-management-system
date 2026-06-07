export interface WidgetDefinition {
  id: string
  type: string
  name: string
  description: string
  category: string
  icon: string
  defaultConfig: Record<string, unknown>
  supportedRoles: string[]
  minSize: { w: number; h: number }
  maxSize: { w: number; h: number }
  preview?: string
  tags?: string[]
  popularity?: number
  lastUpdated?: string
  configSchema?: Record<string, {
    type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect'
    label: string
    description?: string
    default?: unknown
    options?: Array<{ value: unknown; label: string }>
    required?: boolean
  }>
}

export interface WidgetAvailability {
  available: boolean
  reason?: string
}

const definitions: WidgetDefinition[] = [
  {
    id: 'stat_card',
    type: 'stat_card',
    name: '统计卡片',
    description: '展示关键指标、趋势和目标完成情况。',
    category: 'statistics',
    icon: 'BarChart3',
    defaultConfig: { title: '关键指标', dataSource: 'overview', unit: '' },
    supportedRoles: ['ADMIN', 'USER', 'TESTER', 'PROJECT_MANAGER'],
    minSize: { w: 2, h: 1 },
    maxSize: { w: 4, h: 2 },
    tags: ['指标', '概览'],
    popularity: 98,
    lastUpdated: '2026-06-01',
  },
  {
    id: 'line_chart',
    type: 'line_chart',
    name: '趋势图',
    description: '展示测试执行、缺陷或项目进度的时间趋势。',
    category: 'charts',
    icon: 'TrendingUp',
    defaultConfig: { title: '趋势分析', metric: 'executions' },
    supportedRoles: ['ADMIN', 'USER', 'TESTER', 'PROJECT_MANAGER'],
    minSize: { w: 4, h: 3 },
    maxSize: { w: 8, h: 5 },
    tags: ['趋势', '图表'],
    popularity: 91,
    lastUpdated: '2026-06-01',
  },
  {
    id: 'task_list',
    type: 'task_list',
    name: '任务列表',
    description: '显示待办任务、负责人、优先级和截止时间。',
    category: 'lists',
    icon: 'List',
    defaultConfig: { title: '我的任务', limit: 8 },
    supportedRoles: ['ADMIN', 'USER', 'TESTER', 'PROJECT_MANAGER'],
    minSize: { w: 3, h: 3 },
    maxSize: { w: 6, h: 6 },
    tags: ['任务', '列表'],
    popularity: 87,
    lastUpdated: '2026-06-01',
  },
  {
    id: 'status_panel',
    type: 'status_panel',
    name: '状态面板',
    description: '按状态汇总项目、用例、缺陷或任务。',
    category: 'status',
    icon: 'Activity',
    defaultConfig: { title: '状态概览', target: 'projects' },
    supportedRoles: ['ADMIN', 'USER', 'TESTER', 'PROJECT_MANAGER'],
    minSize: { w: 3, h: 2 },
    maxSize: { w: 6, h: 4 },
    tags: ['状态', '汇总'],
    popularity: 82,
    lastUpdated: '2026-06-01',
  },
]

class WidgetService {
  async getWidgetDefinitions(): Promise<WidgetDefinition[]> {
    return definitions
  }

  async getWidgetDefinitionsForRole(roleType: string): Promise<WidgetDefinition[]> {
    const role = roleType.toUpperCase()
    return definitions.filter((widget) => widget.supportedRoles.includes(role) || widget.supportedRoles.includes('USER'))
  }

  async checkWidgetAvailability(widgetType: string, userId?: number): Promise<WidgetAvailability> {
    const exists = definitions.some((widget) => widget.type === widgetType)
    return exists ? { available: true } : { available: false, reason: `未找到组件：${widgetType}` }
  }

  async getWidgetPreview(widgetType: string, config: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
    return {
      widgetType,
      config,
      summary: {
        total: 128,
        completed: 96,
        failed: 7,
        trend: 12,
      },
      series: [
        { name: '周一', value: 24 },
        { name: '周二', value: 31 },
        { name: '周三', value: 28 },
        { name: '周四', value: 39 },
        { name: '周五', value: 46 },
      ],
    }
  }

  async validateWidgetConfig(widgetType: string, config: Record<string, unknown>): Promise<{ valid: boolean; errors?: string[] }> {
    const definition = definitions.find((widget) => widget.type === widgetType)
    if (!definition) return { valid: false, errors: ['组件类型不存在'] }

    const errors = Object.entries(definition.configSchema || {})
      .filter(([, schema]) => schema.required)
      .filter(([key]) => config[key] == null || config[key] === '')
      .map(([, schema]) => `${schema.label} 为必填项`)

    return { valid: errors.length === 0, errors }
  }
}

export const widgetService = new WidgetService()
export default widgetService
