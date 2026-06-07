// 图表组件库导出
export { default as BarChart } from './BarChart'
export { default as PieChart } from './PieChart'
export { default as LineChart } from './LineChart'
export { default as HeatMap } from './HeatMap'

// 图表类型定义
export interface ChartData {
  [key: string]: any
}

export interface ChartConfig {
  type: 'bar' | 'pie' | 'line' | 'heatmap'
  title?: string
  data: ChartData[]
  options?: Record<string, any>
  colors?: string[]
}

// 通用图表属性
export interface BaseChartProps {
  title?: string
  height?: number
  className?: string
}

// 颜色主题
export const chartColors = {
  primary: '#3B82F6',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#06B6D4',
  purple: '#8B5CF6',
  pink: '#EC4899',
  gray: '#6B7280'
}

export const chartColorPalette = [
  chartColors.primary,
  chartColors.success,
  chartColors.warning,
  chartColors.danger,
  chartColors.info,
  chartColors.purple,
  chartColors.pink,
  chartColors.gray
]