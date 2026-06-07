import { FunnelChart } from 'recharts';

import HeatMap from './HeatMap';

import ScatterPlot from './ScatterPlot';

import { RadarChart } from 'recharts';

import GaugeChart from './GaugeChart';

import { AreaChart } from 'lucide-react';

import { PieChart } from 'lucide-react';

import { BarChart } from 'lucide-react';

import { LineChart } from 'lucide-react';

// Chart Components Export
export { default as BaseChart } from './BaseChart';
export type { ChartConfig, ChartTheme } from './BaseChart';

// Recharts-based components
export { default as LineChart } from './LineChart';
export { default as BarChart } from './BarChart';
export { default as PieChart } from './PieChart';
export { default as AreaChart } from './AreaChart';
export { default as GaugeChart } from './GaugeChart';

// D3.js-based components
export { default as HeatMap } from './HeatMap';

// ECharts-based components
export { default as RadarChart } from './RadarChart';
export { default as ScatterPlot } from './ScatterPlot';
export { default as FunnelChart } from './FunnelChart';

// Chart utilities
export * from './chartUtils';

// Chart type definitions for widget library
export const CHART_TYPES = {
  // Basic charts
  LINE: 'line-chart',
  BAR: 'bar-chart',
  PIE: 'pie-chart',
  AREA: 'area-chart',
  
  // Advanced charts
  GAUGE: 'gauge-chart',
  RADAR: 'radar-chart',
  SCATTER: 'scatter-plot',
  HEATMAP: 'heat-map',
  FUNNEL: 'funnel-chart'
} as const;

export type ChartType = typeof CHART_TYPES[keyof typeof CHART_TYPES];

// Chart component mapping
export const CHART_COMPONENTS = {
  [CHART_TYPES.LINE]: LineChart,
  [CHART_TYPES.BAR]: BarChart,
  [CHART_TYPES.PIE]: PieChart,
  [CHART_TYPES.AREA]: AreaChart,
  [CHART_TYPES.GAUGE]: GaugeChart,
  [CHART_TYPES.RADAR]: RadarChart,
  [CHART_TYPES.SCATTER]: ScatterPlot,
  [CHART_TYPES.HEATMAP]: HeatMap,
  [CHART_TYPES.FUNNEL]: FunnelChart
};

// Chart metadata for widget library
export const CHART_METADATA = {
  [CHART_TYPES.LINE]: {
    name: '折线图',
    description: '显示数据随时间变化的趋势',
    category: 'charts',
    library: 'recharts',
    features: ['时间序列', '多系列', '数据钻取', '缩放', '参考线'],
    defaultConfig: {
      showDataPoints: true,
      smoothCurve: false,
      showGrid: true,
      showLegend: true,
      animation: true
    }
  },
  [CHART_TYPES.BAR]: {
    name: '柱状图',
    description: '比较不同类别的数据值',
    category: 'charts',
    library: 'recharts',
    features: ['分类对比', '堆叠', '水平/垂直', '数据标签', '参考线'],
    defaultConfig: {
      orientation: 'vertical',
      showValues: true,
      showGrid: true,
      showLegend: true,
      animation: true
    }
  },
  [CHART_TYPES.PIE]: {
    name: '饼图',
    description: '显示数据的组成比例',
    category: 'charts',
    library: 'recharts',
    features: ['比例展示', '环形图', '交互选择', '数据标签', '图例'],
    defaultConfig: {
      showLegend: true,
      showPercentage: true,
      donut: false,
      showTotal: true,
      animation: true
    }
  },
  [CHART_TYPES.AREA]: {
    name: '面积图',
    description: '显示数据量的变化趋势',
    category: 'charts',
    library: 'recharts',
    features: ['趋势展示', '堆叠面积', '渐变填充', '缩放', '参考线'],
    defaultConfig: {
      stacked: false,
      gradient: true,
      smoothCurve: true,
      showGrid: true,
      animation: true
    }
  },
  [CHART_TYPES.GAUGE]: {
    name: '仪表盘',
    description: '显示单一指标的当前状态',
    category: 'charts',
    library: 'custom',
    features: ['状态指示', '阈值设置', '多种样式', '动画效果'],
    defaultConfig: {
      min: 0,
      max: 100,
      thresholds: [30, 70],
      gaugeType: 'semicircle',
      showThresholds: true,
      animation: true
    }
  },
  [CHART_TYPES.RADAR]: {
    name: '雷达图',
    description: '多维度数据对比分析',
    category: 'charts',
    library: 'echarts',
    features: ['多维对比', '面积填充', '多系列', '形状选择'],
    defaultConfig: {
      showSymbol: true,
      areaStyle: true,
      shape: 'polygon',
      showLegend: true,
      animation: true
    }
  },
  [CHART_TYPES.SCATTER]: {
    name: '散点图',
    description: '显示两个变量之间的关系',
    category: 'charts',
    library: 'echarts',
    features: ['相关性分析', '气泡图', '回归线', '分类着色'],
    defaultConfig: {
      bubble: false,
      showRegression: false,
      showGrid: true,
      showLegend: true,
      animation: true
    }
  },
  [CHART_TYPES.HEATMAP]: {
    name: '热力图',
    description: '通过颜色深浅显示数据密度',
    category: 'charts',
    library: 'd3',
    features: ['密度可视化', '颜色映射', '交互提示', '自定义配色'],
    defaultConfig: {
      showValues: false,
      cellPadding: 2,
      colorRange: ['#f0f9ff', '#1e40af'],
      animation: true
    }
  },
  [CHART_TYPES.FUNNEL]: {
    name: '漏斗图',
    description: '显示业务流程的转化情况',
    category: 'charts',
    library: 'echarts',
    features: ['转化分析', '排序选项', '标签位置', '转化率计算'],
    defaultConfig: {
      sort: 'descending',
      showLabels: true,
      labelPosition: 'inside',
      showLegend: true,
      animation: true
    }
  }
} as const;