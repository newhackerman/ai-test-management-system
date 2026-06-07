import React, { useMemo, useRef, useCallback } from 'react';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  LabelList
} from 'recharts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, generateSampleData, handleChartClick } from './chartUtils';

interface BarChartConfig extends ChartConfig {
  orientation?: 'vertical' | 'horizontal';
  showValues?: boolean;
  xAxisKey?: string;
  yAxisKeys?: string[];
  stacked?: boolean;
  gradient?: boolean;
  showReferenceLine?: boolean;
  referenceValue?: number;
  barRadius?: number;
  barGap?: number;
}

interface BarChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: BarChartConfig;
}

const BarChart: React.FC<BarChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  
  const {
    orientation = 'vertical',
    showValues = true,
    colorScheme = getColorScheme('default'),
    xAxisKey = 'category',
    yAxisKeys = ['value'],
    stacked = false,
    gradient = false,
    showReferenceLine = false,
    referenceValue,
    barRadius = 4,
    barGap = 4,
    showGrid = true,
    showLegend = true,
    animation = true
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data;
    }

    return generateSampleData('bar', 8).map(item => ({
      ...item,
      [xAxisKey]: item.category || item[xAxisKey],
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

  const formatAxisTick = useCallback((value: any) => {
    if (typeof value === 'number') {
      return formatNumber(value, 'compact');
    }
    return value;
  }, []);

  const handleBarClick = useCallback((data: any) => {
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

  const CustomLabel = ({ x, y, width, height, value }: any) => {
    if (!showValues || !value) return null;
    
    const labelX = orientation === 'horizontal' ? x + width + 5 : x + width / 2;
    const labelY = orientation === 'horizontal' ? y + height / 2 : y - 5;
    
    return (
      <text
        x={labelX}
        y={labelY}
        fill="var(--chart-text-secondary, #6b7280)"
        textAnchor={orientation === 'horizontal' ? 'start' : 'middle'}
        dominantBaseline={orientation === 'horizontal' ? 'middle' : 'auto'}
        fontSize="11"
        fontWeight="500"
      >
        {formatNumber(value, 'compact')}
      </text>
    );
  };

  const gradientId = `barGradient-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <BaseChart config={config} {...baseProps}>
      <div ref={chartRef} className="w-full h-full">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 20,
            }}
            layout={orientation === 'horizontal' ? 'horizontal' : 'vertical'}
            barGap={barGap}
            onClick={handleBarClick}
          >
            {gradient && (
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colorScheme[0]} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={colorScheme[0]} stopOpacity={0.6}/>
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
            
            {orientation === 'vertical' ? (
              <>
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
                  tickFormatter={formatAxisTick}
                  tickLine={false}
                  axisLine={false}
                />
              </>
            ) : (
              <>
                <XAxis 
                  type="number"
                  tick={{ fontSize: 11, fill: 'var(--chart-text-secondary, #6b7280)' }}
                  stroke="var(--chart-border, #e5e7eb)"
                  tickFormatter={formatAxisTick}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  type="category"
                  dataKey={xAxisKey}
                  tick={{ fontSize: 11, fill: 'var(--chart-text-secondary, #6b7280)' }}
                  stroke="var(--chart-border, #e5e7eb)"
                  tickLine={false}
                  axisLine={false}
                />
              </>
            )}
            
            <Tooltip content={<CustomTooltip />} />
            
            {showLegend && yAxisKeys.length > 1 && (
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="rect"
              />
            )}
            
            {showReferenceLine && referenceValue !== undefined && (
              <ReferenceLine 
                y={orientation === 'vertical' ? referenceValue : undefined}
                x={orientation === 'horizontal' ? referenceValue : undefined}
                stroke="var(--chart-warning, #f59e0b)" 
                strokeDasharray="5 5"
                label={{ value: `目标: ${referenceValue}`, position: 'top' }}
              />
            )}
            
            {yAxisKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={gradient ? `url(#${gradientId})` : colorScheme[index % colorScheme.length]}
                name={key.charAt(0).toUpperCase() + key.slice(1)}
                stackId={stacked ? 'stack' : undefined}
                radius={barRadius}
                animationDuration={animation ? 750 : 0}
              >
                {showValues && <LabelList content={<CustomLabel />} />}
                
                {/* Add different colors for each bar if single series */}
                {yAxisKeys.length === 1 && !gradient && chartData.map((entry, entryIndex) => (
                  <Cell 
                    key={`cell-${entryIndex}`} 
                    fill={colorScheme[entryIndex % colorScheme.length]} 
                  />
                ))}
              </Bar>
            ))}
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </BaseChart>
  );
};

export default BarChart;