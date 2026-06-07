// @ts-nocheck
import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import * as echarts from 'echarts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, handleChartClick } from './chartUtils';

interface RadarChartConfig extends ChartConfig {
  indicators?: Array<{
    name: string;
    max?: number;
    min?: number;
  }>;
  showSymbol?: boolean;
  areaStyle?: boolean;
  splitNumber?: number;
  shape?: 'polygon' | 'circle';
  nameGap?: number;
  series?: Array<{
    name: string;
    data: number[];
  }>;
}

interface RadarChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: RadarChartConfig;
}

const RadarChart: React.FC<RadarChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const {
    indicators = [],
    showSymbol = true,
    areaStyle = true,
    splitNumber = 5,
    shape = 'polygon',
    nameGap = 15,
    series = [],
    colorScheme = getColorScheme('default'),
    showLegend = true,
    animation = true,
    theme
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && (data.indicators || data.series)) {
      return data;
    }

    // Generate sample radar data
    const sampleIndicators = [
      { name: '功能完整性', max: 100 },
      { name: '性能表现', max: 100 },
      { name: '用户体验', max: 100 },
      { name: '代码质量', max: 100 },
      { name: '测试覆盖', max: 100 },
      { name: '文档完善', max: 100 }
    ];

    const sampleSeries = [
      {
        name: '褰撳墠椤圭洰',
        data: [85, 78, 92, 88, 75, 82]
      },
      {
        name: '琛屼笟骞冲潎',
        data: [70, 75, 80, 75, 70, 75]
      }
    ];

    return {
      indicators: sampleIndicators,
      series: sampleSeries
    };
  }, [data]);

  const handleChartClick = useCallback((params: any) => {
    if (onDrillDown) {
      onDrillDown(params);
    }
  }, [onDrillDown]);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

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
          if (params.componentType === 'radar') {
            const { seriesName, data } = params;
            let html = `<div style="font-weight: 600; margin-bottom: 4px;">${seriesName}</div>`;
            
            data.value.forEach((value: number, index: number) => {
              const indicator = chartData.indicators[index];
              html += `<div style="display: flex; align-items: center; margin-bottom: 2px;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: ${colorScheme[params.seriesIndex % colorScheme.length]}; border-radius: 50%; margin-right: 6px;"></span>
                <span style="color: #6b7280; margin-right: 8px;">${indicator.name}:</span>
                <span style="font-weight: 500;">${formatNumber(value)}</span>
              </div>`;
            });
            
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

      radar: {
        indicator: chartData.indicators,
        shape: shape,
        splitNumber: splitNumber,
        center: ['50%', '50%'],
        radius: '70%',
        
        name: {
          textStyle: {
            color: theme?.textSecondary || '#6b7280',
            fontSize: 11,
            fontWeight: 500
          }
        },
        
        splitLine: {
          lineStyle: {
            color: theme?.grid || '#f3f4f6',
            width: 1
          }
        },
        
        splitArea: {
          show: true,
          areaStyle: {
            color: [
              'rgba(250, 250, 250, 0.1)',
              'rgba(200, 200, 200, 0.1)'
            ]
          }
        },
        
        axisLine: {
          lineStyle: {
            color: theme?.border || '#e5e7eb',
            width: 1
          }
        }
      },

      series: chartData.series.map((seriesItem: any, index: number) => ({
        name: seriesItem.name,
        type: 'radar',
        data: [{
          value: seriesItem.data,
          name: seriesItem.name
        }],
        symbol: showSymbol ? 'circle' : 'none',
        symbolSize: 4,
        lineStyle: {
          width: 2,
          color: colorScheme[index % colorScheme.length]
        },
        areaStyle: areaStyle ? {
          color: colorScheme[index % colorScheme.length],
          opacity: 0.1
        } : undefined,
        animationDuration: animation ? 1000 : 0,
        animationEasing: 'cubicOut'
      }))
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
  }, [chartData, colorScheme, showSymbol, areaStyle, splitNumber, shape, nameGap, showLegend, animation, theme, handleChartClick]);

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

export default RadarChart;
