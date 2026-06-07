import React, { useMemo, useRef, useCallback } from 'react';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
  ReferenceLine
} from 'recharts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, formatDate, generateSampleData, handleChartClick } from './chartUtils';

interface LineChartConfig extends ChartConfig {
  showDataPoints?: boolean;
  smoothCurve?: boolean;
  xAxisKey?: string;
  yAxisKeys?: string[];
  showBrush?: boolean;
  showReferenceLine?: boolean;
  referenceValue?: number;
  areaFill?: boolean;
  gradient?: boolean;
  zoom?: boolean;
  connectNulls?: boolean;
}

interface LineChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: LineChartConfig;
}

const LineChart: React.FC<LineChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  
  const {
    showDataPoints = true,
    smoothCurve = false,
    colorScheme = getColorScheme('default'),
    xAxisKey = 'date',
    yAxisKeys = ['value'],
    showBrush = false,
    showReferenceLine = false,
    referenceValue,
    areaFill = false,
    gradient = false,
    zoom = false,
    connectNulls = true,
    showGrid = true,
    showLegend = true,
    animation = true
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data;
    }

    return generateSampleData('line', 30).map(item => ({
      ...item,
      [xAxisKey]: item.date || item[xAxisKey],
      ...yAxisKeys.reduce((acc, key, index) => ({
        ...acc,
        [key]: item[`value${index > 0 ? index + 1 : ''}`] || Math.floor(Math.random() * 100) + 20
      }), {})
    }));
  }, [data, xAxisKey, yAxisKeys]);

  const formatTooltipValue = useCallback((value: any, name: string) => {
    if (typeof value === 'number') {
      return [formatNumber(value), name];
    }
    return [value, name];
  }, []);

  const formatYAxisTick = useCallback((value: any) => {
    if (typeof value === 'number') {
      return formatNumber(value, 'compact');
    }
    return value;
  }, []);

  const handleLineClick = useCallback((data: any) => {
    handleChartClick(data, onDrillDown);
  }, [onDrillDown]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="text-sm font-medium text-gray-900 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center text-sm">
              <div 
                className="w-3 h-3 rounded-full mr-2" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-600 mr-2">{entry.name}:</span>
              <span className="font-medium">{formatTooltipValue(entry.value, entry.name)[0]}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const gradientId = `lineGradient-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <BaseChart config={config} {...baseProps}>
      <div ref={chartRef} className="w-full h-full">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsLineChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: showBrush ? 60 : 20,
            }}
            onClick={handleLineClick}
          >
            {gradient && (
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colorScheme[0]} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={colorScheme[0]} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
            )}
            
            {showGrid && (
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="var(--chart-grid, #f3f4f6)" 
                opacity={0.5}
              />
            )}
            
            <XAxis 
              dataKey={xAxisKey}
              tick={{ fontSize: 11, fill: 'var(--chart-text-secondary, #6b7280)' }}
              stroke="var(--chart-border, #e5e7eb)"
              tickLine={false}
              axisLine={false}
            />
            
            <YAxis 
              tick={{ fontSize: 11, fill: 'var(--chart-text-secondary, #6b7280)' }}
              stroke="var(--chart-border, #e5e7eb)"
              tickFormatter={formatYAxisTick}
              tickLine={false}
              axisLine={false}
            />
            
            <Tooltip content={<CustomTooltip />} />
            
            {showLegend && yAxisKeys.length > 1 && (
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="line"
              />
            )}
            
            {showReferenceLine && referenceValue !== undefined && (
              <ReferenceLine 
                y={referenceValue} 
                stroke="var(--chart-warning, #f59e0b)" 
                strokeDasharray="5 5"
                label={{ value: `目标: ${referenceValue}`, position: 'top' }}
              />
            )}
            
            {yAxisKeys.map((key, index) => (
              <Line
                key={key}
                type={smoothCurve ? "monotone" : "linear"}
                dataKey={key}
                stroke={colorScheme[index % colorScheme.length]}
                strokeWidth={2}
                dot={showDataPoints ? { 
                  r: 3, 
                  strokeWidth: 2, 
                  fill: colorScheme[index % colorScheme.length] 
                } : false}
                activeDot={{ 
                  r: 5, 
                  strokeWidth: 0, 
                  fill: colorScheme[index % colorScheme.length] 
                }}
                name={key.charAt(0).toUpperCase() + key.slice(1)}
                connectNulls={connectNulls}
                fill={areaFill && gradient ? `url(#${gradientId})` : 'none'}
                animationDuration={animation ? 750 : 0}
              />
            ))}
            
            {showBrush && (
              <Brush 
                dataKey={xAxisKey} 
                height={30} 
                stroke={colorScheme[0]}
                fill="var(--chart-surface, #f8fafc)"
              />
            )}
          </RechartsLineChart>
        </ResponsiveContainer>
      </div>
    </BaseChart>
  );
};

export default LineChart;