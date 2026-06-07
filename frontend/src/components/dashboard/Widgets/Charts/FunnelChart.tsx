import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import * as echarts from 'echarts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, handleChartClick } from './chartUtils';

interface FunnelChartConfig extends ChartConfig {
  nameKey?: string;
  valueKey?: string;
  sort?: 'ascending' | 'descending' | 'none';
  gap?: number;
  funnelAlign?: 'left' | 'center' | 'right';
  showLabels?: boolean;
  labelPosition?: 'inside' | 'outside';
  minSize?: string;
  maxSize?: string;
}

interface FunnelChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: FunnelChartConfig;
}

const FunnelChart: React.FC<FunnelChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const {
    nameKey = 'name',
    valueKey = 'value',
    sort = 'descending',
    gap = 2,
    funnelAlign = 'center',
    showLabels = true,
    labelPosition = 'inside',
    minSize = '0%',
    maxSize = '100%',
    colorScheme = getColorScheme('default'),
    showLegend = true,
    animation = true,
    theme
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data.map(item => ({
        name: item[nameKey],
        value: item[valueKey]
      }));
    }

    // Generate sample funnel data
    return [
      { name: '访问量', value: 1000 },
      { name: '浏览量', value: 800 },
      { name: '注册量', value: 600 },
      { name: '购买量', value: 400 },
      { name: '复购量', value: 200 }
    ];
  }, [data, nameKey, valueKey]);

  const handleChartClick = useCallback((params: any) => {
    if (onDrillDown) {
      onDrillDown(params);
    }
  }, [onDrillDown]);

  // Calculate conversion rates
  const conversionRates = useMemo(() => {
    if (chartData.length < 2) return [];
    
    return chartData.slice(1).map((item, index) => {
      const prevValue = chartData[index].value;
      const currentValue = item.value;
      const rate = prevValue > 0 ? (currentValue / prevValue * 100) : 0;
      return {
        name: item.name,
        rate: rate.toFixed(1)
      };
    });
  }, [chartData]);

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
          const { name, value, dataIndex } = params;
          let html = `<div style="font-weight: 600; margin-bottom: 4px;">${name}</div>`;
          html += `<div style="color: #6b7280;">数量: ${formatNumber(value)}</div>`;
          
          // Add conversion rate if available
          if (dataIndex > 0 && conversionRates[dataIndex - 1]) {
            html += `<div style="color: #6b7280;">转化率: ${conversionRates[dataIndex - 1].rate}%</div>`;
          }
          
          return html;
        }
      },

      legend: showLegend ? {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: {
          color: theme?.textSecondary || '#6b7280',
          fontSize: 12
        },
        itemGap: 10,
        formatter: function(name: string) {
          const item = chartData.find(d => d.name === name);
          return `${name}: ${formatNumber(item?.value || 0)}`;
        }
      } : undefined,

      series: [{
        name: '漏斗图',
        type: 'funnel',
        left: '10%',
        top: '10%',
        right: showLegend ? '25%' : '10%',
        bottom: '10%',
        width: showLegend ? '65%' : '80%',
        height: '80%',
        
        // Funnel configuration
        min: 0,
        max: Math.max(...chartData.map(d => d.value)),
        minSize: minSize,
        maxSize: maxSize,
        sort: sort,
        gap: gap,
        funnelAlign: funnelAlign,
        
        // Label configuration
        label: showLabels ? {
          show: true,
          position: labelPosition === 'inside' ? 'inner' : 'outer',
          color: labelPosition === 'inside' ? '#fff' : (theme?.text || '#374151'),
          fontSize: 12,
          fontWeight: 500,
          formatter: function(params: any) {
            const { name, value, dataIndex } = params;
            let text = `${name}\n${formatNumber(value)}`;
            
            // Add conversion rate for inside labels
            if (labelPosition === 'inside' && dataIndex > 0 && conversionRates[dataIndex - 1]) {
              text += `\n(${conversionRates[dataIndex - 1].rate}%)`;
            }
            
            return text;
          }
        } : { show: false },
        
        // Label line for outside labels
        labelLine: labelPosition === 'outside' ? {
          show: true,
          length: 10,
          lineStyle: {
            color: theme?.border || '#e5e7eb'
          }
        } : { show: false },
        
        // Item style
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1,
          opacity: 0.9
        },
        
        // Emphasis style
        emphasis: {
          itemStyle: {
            opacity: 1,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        
        // Animation
        animationDuration: animation ? 1000 : 0,
        animationEasing: 'cubicOut',
        
        data: chartData
      }]
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
  }, [chartData, conversionRates, colorScheme, sort, gap, funnelAlign, showLabels, labelPosition, minSize, maxSize, showLegend, animation, theme, handleChartClick]);

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
      <div className="w-full h-full flex flex-col">
        <div
          ref={chartRef}
          className="flex-1"
          style={{ minHeight: '300px' }}
        />
        
        {/* Conversion rates summary */}
        {conversionRates.length > 0 && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 mb-2">转化率统计</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {conversionRates.map((item, index) => (
                <div key={index} className="text-center">
                  <div className="text-xs text-gray-500">{item.name}</div>
                  <div className="text-sm font-medium text-gray-900">{item.rate}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </BaseChart>
  );
};

export default FunnelChart;