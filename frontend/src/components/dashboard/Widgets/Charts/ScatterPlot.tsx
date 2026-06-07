import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import * as echarts from 'echarts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, generateSampleData, handleChartClick } from './chartUtils';

interface ScatterPlotConfig extends ChartConfig {
  xAxisKey?: string;
  yAxisKey?: string;
  sizeKey?: string;
  categoryKey?: string;
  symbolSize?: number | [number, number];
  showRegression?: boolean;
  xAxisName?: string;
  yAxisName?: string;
  bubble?: boolean;
  series?: Array<{
    name: string;
    data: Array<[number, number] | [number, number, number]>;
  }>;
}

interface ScatterPlotProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: ScatterPlotConfig;
}

const ScatterPlot: React.FC<ScatterPlotProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const {
    xAxisKey = 'x',
    yAxisKey = 'y',
    sizeKey = 'size',
    categoryKey = 'category',
    symbolSize = 8,
    showRegression = false,
    xAxisName = 'X轴',
    yAxisName = 'Y轴',
    bubble = false,
    series = [],
    colorScheme = getColorScheme('default'),
    showLegend = true,
    showGrid = true,
    animation = true,
    theme
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && (data.series || Array.isArray(data))) {
      if (Array.isArray(data)) {
        // Convert array data to series format
        const categories = Array.from(new Set(data.map(item => item[categoryKey] || '默认')));
        return categories.map(category => ({
          name: category,
          data: data
            .filter(item => (item[categoryKey] || '默认') === category)
            .map(item => bubble 
              ? [item[xAxisKey], item[yAxisKey], item[sizeKey] || 10]
              : [item[xAxisKey], item[yAxisKey]]
            )
        }));
      }
      return data.series;
    }

    // Generate sample scatter data
    const sampleData = generateSampleData('scatter', 50);
    const categories = ['类别A', '类别B', '类别C'];
    
    return categories.map((category, categoryIndex) => ({
      name: category,
      data: sampleData
        .filter((_, index) => index % 3 === categoryIndex)
        .map(item => bubble 
          ? [item.x, item.y, item.z]
          : [item.x, item.y]
        )
    }));
  }, [data, xAxisKey, yAxisKey, sizeKey, categoryKey, bubble]);

  const handleChartClick = useCallback((params: any) => {
    if (onDrillDown) {
      onDrillDown(params);
    }
  }, [onDrillDown]);

  // Calculate regression line if needed
  const regressionData = useMemo(() => {
    if (!showRegression || !chartData.length) return null;

    // Combine all data points
    const allPoints = chartData.flatMap((series: any) => series.data);
    if (allPoints.length < 2) return null;

    // Calculate linear regression
    const n = allPoints.length;
    const sumX = allPoints.reduce((sum: number, point: any) => sum + point[0], 0);
    const sumY = allPoints.reduce((sum: number, point: any) => sum + point[1], 0);
    const sumXY = allPoints.reduce((sum: number, point: any) => sum + point[0] * point[1], 0);
    const sumXX = allPoints.reduce((sum: number, point: any) => sum + point[0] * point[0], 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Get x range
    const xValues = allPoints.map((point: any) => point[0]);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);

    return [
      [minX, slope * minX + intercept],
      [maxX, slope * maxX + intercept]
    ];
  }, [chartData, showRegression]);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

    // Prepare series data
    const seriesData = chartData.map((seriesItem: any, index: number) => ({
      name: seriesItem.name,
      type: 'scatter',
      data: seriesItem.data,
      symbolSize: bubble 
        ? function(data: any) {
            return Math.sqrt(data[2]) * 2; // Scale bubble size
          }
        : symbolSize,
      itemStyle: {
        color: colorScheme[index % colorScheme.length],
        opacity: 0.8
      },
      emphasis: {
        itemStyle: {
          opacity: 1,
          borderColor: '#374151',
          borderWidth: 2
        }
      },
      animationDuration: animation ? 1000 : 0,
      animationEasing: 'cubicOut'
    }));

    // Add regression line if enabled
    if (regressionData) {
      seriesData.push({
        name: '趋势线',
        type: 'line',
        data: regressionData,
        symbolSize: 0,
        itemStyle: {
          color: '#ef4444',
          opacity: 0.8
        },
        lineStyle: {
          type: 'dashed',
          width: 2
        },
        animationDuration: animation ? 1000 : 0
      } as any);
    }

    // Chart options
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      color: colorScheme,
      
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        borderRadius: 6,
        textStyle: {
          color: '#374151',
          fontSize: 12
        },
        formatter: function(params: any) {
          if (params.componentType === 'series') {
            const { seriesName, data } = params;
            let html = `<div style="font-weight: 600; margin-bottom: 4px;">${seriesName}</div>`;
            
            html += `<div style="color: #6b7280;">
              ${xAxisName}: ${formatNumber(data[0])}<br/>
              ${yAxisName}: ${formatNumber(data[1])}`;
            
            if (bubble && data[2] !== undefined) {
              html += `<br/>大小: ${formatNumber(data[2])}`;
            }
            
            html += '</div>';
            return html;
          }
          return '';
        }
      },

      legend: showLegend ? {
        orient: 'horizontal',
        bottom: 10,
        textStyle: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 12
        },
        itemGap: 20
      } : undefined,

      grid: {
        left: '10%',
        right: '10%',
        bottom: showLegend ? '15%' : '10%',
        top: '10%',
        containLabel: true
      },

      xAxis: {
        type: 'value',
        name: xAxisName,
        nameLocation: 'middle',
        nameGap: 30,
        nameTextStyle: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 12,
          fontWeight: 500
        },
        axisLine: {
          show: false
        },
        axisTick: {
          show: false
        },
        axisLabel: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 11,
          formatter: (value: number) => formatNumber(value, 'compact')
        },
        splitLine: showGrid ? {
          lineStyle: {
            color: theme?.grid || '#f3f4f6',
            type: 'solid'
          }
        } : { show: false }
      },

      yAxis: {
        type: 'value',
        name: yAxisName,
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 12,
          fontWeight: 500
        },
        axisLine: {
          show: false
        },
        axisTick: {
          show: false
        },
        axisLabel: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 11,
          formatter: (value: number) => formatNumber(value, 'compact')
        },
        splitLine: showGrid ? {
          lineStyle: {
            color: theme?.grid || '#f3f4f6',
            type: 'solid'
          }
        } : { show: false }
      },

      series: seriesData
    };

    // Set chart options
    chart.setOption(option, true);

    // Add click event
    chart.off('click');
    chart.on('click', handleChartClick);

    // Handle resize
    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.off('click');
    };
  }, [chartData, regressionData, colorScheme, symbolSize, bubble, showRegression, xAxisName, yAxisName, showLegend, showGrid, animation, theme, handleChartClick]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  return (
    <BaseChart config={config} {...baseProps}>
      <div
        ref={chartRef}
        className="w-full h-full"
        style={{ minHeight: '300px' }}
      />
    </BaseChart>
  );
};

export default ScatterPlot;