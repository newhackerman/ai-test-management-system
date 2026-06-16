import React, { useMemo, useRef, useCallback, useState } from 'react';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Sector
} from 'recharts';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, generateSampleData, handleChartClick } from './chartUtils';

interface PieChartConfig extends ChartConfig {
  showPercentage?: boolean;
  innerRadius?: number;
  outerRadius?: number;
  nameKey?: string;
  valueKey?: string;
  donut?: boolean;
  showTotal?: boolean;
  activeShape?: boolean;
  startAngle?: number;
  endAngle?: number;
}

interface PieChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: PieChartConfig;
}

const PieChart: React.FC<PieChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  
  const {
    showLegend = true,
    showPercentage = true,
    colorScheme = getColorScheme('default'),
    innerRadius = 0,
    outerRadius = 80,
    nameKey = 'name',
    valueKey = 'value',
    donut = false,
    showTotal = true,
    activeShape = true,
    startAngle = 0,
    endAngle = 360,
    animation = true
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data;
    }

    return generateSampleData('pie').map(item => ({
      [nameKey]: item.name || item[nameKey],
      [valueKey]: item.value || item[valueKey]
    }));
  }, [data, nameKey, valueKey]);

  const total = useMemo(() => {
    return chartData.reduce((sum, item) => sum + (item[valueKey] || 0), 0);
  }, [chartData, valueKey]);

  const formatTooltipValue = useCallback((value: any, name: string) => {
    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
    return [`${formatNumber(value)} (${percentage}%)`, name];
  }, [total]);

  const handlePieClick = useCallback((data: any, index: number) => {
    setActiveIndex(activeIndex === index ? -1 : index);
    handleChartClick(data, onDrillDown);
  }, [activeIndex, onDrillDown]);

  const onPieEnter = useCallback((data: any, index: number) => {
    if (activeShape) {
      setActiveIndex(index);
    }
  }, [activeShape]);

  const onPieLeave = useCallback(() => {
    if (activeShape) {
      setActiveIndex(-1);
    }
  }, [activeShape]);

  const renderActiveShape = (props: any) => {
    const RADIAN = Math.PI / 180;
    const { cx, cy, midAngle, innerRadius, outerRadius, startAngle, endAngle, fill, payload, percent, value } = props;
    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);
    const sx = cx + (outerRadius + 10) * cos;
    const sy = cy + (outerRadius + 10) * sin;
    const mx = cx + (outerRadius + 30) * cos;
    const my = cy + (outerRadius + 30) * sin;
    const ex = mx + (cos >= 0 ? 1 : -1) * 22;
    const ey = my;
    const textAnchor = cos >= 0 ? 'start' : 'end';

    return (
      <g>
        <text x={cx} y={cy} dy={8} textAnchor="middle" fill={fill} className="text-sm font-medium">
          {payload[nameKey]}
        </text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius + 6}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
        <Sector
          cx={cx}
          cy={cy}
          startAngle={startAngle}
          endAngle={endAngle}
          innerRadius={outerRadius + 6}
          outerRadius={outerRadius + 10}
          fill={fill}
        />
        <path d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`} stroke={fill} fill="none" />
        <circle cx={ex} cy={ey} r={2} fill={fill} stroke="none" />
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} textAnchor={textAnchor} fill="var(--chart-text, #1f2937)" className="text-xs">
          {`${formatNumber(value)}`}
        </text>
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} dy={18} textAnchor={textAnchor} fill="var(--chart-text-secondary, #6b7280)" className="text-xs">
          {`(${(percent * 100).toFixed(1)}%)`}
        </text>
      </g>
    );
  };

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (!showPercentage || percent < 0.05) return null; // Don't show label for slices < 5%
    
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize="11"
        fontWeight="600"
        className="drop-shadow-sm"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const renderLegend = (props: any) => {
    const { payload } = props;
    
    return (
      <div className="flex flex-wrap justify-center gap-3 mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={`legend-${index}`} className="flex items-center text-sm">
            <div 
              className="w-3 h-3 rounded-full mr-2"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-700 font-medium dark:text-gray-300">{entry.value}</span>
            <span className="text-gray-500 ml-1 dark:text-gray-400">
              ({formatNumber(chartData[index]?.[valueKey] || 0)})
            </span>
          </div>
        ))}
      </div>
    );
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg dark:bg-gray-800 dark:border-gray-700">
          <div className="flex items-center mb-2">
            <div 
              className="w-3 h-3 rounded-full mr-2" 
              style={{ backgroundColor: data.color }}
            />
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{data.name}</span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <div>数值: {formatNumber(data.value)}</div>
            <div>占比: {((data.value / total) * 100).toFixed(1)}%</div>
          </div>
        </div>
      );
    }
    return null;
  };

  const actualInnerRadius = donut ? (innerRadius || outerRadius * 0.6) : innerRadius;

  return (
    <BaseChart config={config} {...baseProps}>
      <div ref={chartRef} className="w-full h-full flex flex-col">
        <div className="flex-1 relative">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsPieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={!activeShape ? renderCustomLabel : false}
                outerRadius={outerRadius}
                innerRadius={actualInnerRadius}
                fill="#8884d8"
                dataKey={valueKey}
                nameKey={nameKey}
                startAngle={startAngle}
                endAngle={endAngle}
                onClick={handlePieClick}
                onMouseEnter={onPieEnter}
                onMouseLeave={onPieLeave}
                animationDuration={animation ? 750 : 0}
                activeIndex={activeIndex}
                activeShape={activeShape ? renderActiveShape : false}
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={colorScheme[index % colorScheme.length]}
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              {showLegend && (
                <Legend 
                  content={renderLegend}
                  wrapperStyle={{ paddingTop: '10px' }}
                />
              )}
            </RechartsPieChart>
          </ResponsiveContainer>
          
          {/* Center label for donut chart */}
          {donut && showTotal && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(total)}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">总计</div>
              </div>
            </div>
          )}
        </div>
        
        {/* Summary */}
        {!donut && showTotal && (
          <div className="text-center text-sm text-gray-500 mt-2 border-t pt-2 dark:text-gray-400">
            总计: {formatNumber(total)}
          </div>
        )}
      </div>
    </BaseChart>
  );
};

export default PieChart;