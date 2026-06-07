import React, { useMemo, useCallback } from 'react';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, handleChartClick } from './chartUtils';

interface GaugeChartConfig extends ChartConfig {
  min?: number;
  max?: number;
  thresholds?: number[];
  unit?: string;
  valueKey?: string;
  showThresholds?: boolean;
  showScale?: boolean;
  gaugeType?: 'semicircle' | 'circle' | 'arc';
  strokeWidth?: number;
  size?: number;
}

interface GaugeChartProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: GaugeChartConfig;
}

const GaugeChart: React.FC<GaugeChartProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const {
    min = 0,
    max = 100,
    thresholds = [30, 70],
    unit = '%',
    valueKey = 'value',
    showThresholds = true,
    showScale = true,
    gaugeType = 'semicircle',
    strokeWidth = 20,
    size = 200,
    colorScheme = ['#EF4444', '#F59E0B', '#10B981'], // red, yellow, green
    animation = true
  } = config;

  // Get current value from data
  const currentValue = useMemo(() => {
    if (data && typeof data === 'object') {
      return data[valueKey] || data.value || data.current || 0;
    }
    if (typeof data === 'number') {
      return data;
    }
    // Generate sample value
    return Math.floor(Math.random() * (max - min)) + min;
  }, [data, valueKey, min, max]);

  // Calculate percentage and color
  const percentage = ((currentValue - min) / (max - min)) * 100;
  const clampedPercentage = Math.max(0, Math.min(100, percentage));

  const getColor = useCallback(() => {
    if (currentValue <= thresholds[0]) {
      return colorScheme[0]; // Red
    } else if (currentValue <= thresholds[1]) {
      return colorScheme[1]; // Yellow
    } else {
      return colorScheme[2]; // Green
    }
  }, [currentValue, thresholds, colorScheme]);

  const getStatus = useCallback(() => {
    if (currentValue <= thresholds[0]) {
      return '危险';
    } else if (currentValue <= thresholds[1]) {
      return '警告';
    } else {
      return '正常';
    }
  }, [currentValue, thresholds]);

  const handleGaugeClick = useCallback(() => {
    handleChartClick({ value: currentValue, status: getStatus() }, onDrillDown);
  }, [currentValue, getStatus, onDrillDown]);

  // SVG gauge parameters
  const radius = (size - strokeWidth) / 2;
  const circumference = gaugeType === 'semicircle' ? radius * Math.PI : radius * 2 * Math.PI;
  const strokeDasharray = `${circumference} ${circumference}`;
  const strokeDashoffset = circumference - (clampedPercentage / 100) * circumference;

  const renderGauge = () => {
    const svgHeight = gaugeType === 'semicircle' ? size / 2 + strokeWidth : size;
    const centerX = size / 2;
    const centerY = gaugeType === 'semicircle' ? size / 2 : size / 2;
    
    let backgroundPath, progressPath;
    
    if (gaugeType === 'semicircle') {
      backgroundPath = `M ${strokeWidth / 2} ${centerY} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${centerY}`;
      progressPath = backgroundPath;
    } else if (gaugeType === 'circle') {
      backgroundPath = `M ${centerX} ${strokeWidth / 2} A ${radius} ${radius} 0 1 1 ${centerX} ${size - strokeWidth / 2} A ${radius} ${radius} 0 1 1 ${centerX} ${strokeWidth / 2}`;
      progressPath = backgroundPath;
    } else { // arc
      const startAngle = -135;
      const endAngle = 135;
      const startX = centerX + radius * Math.cos((startAngle * Math.PI) / 180);
      const startY = centerY + radius * Math.sin((startAngle * Math.PI) / 180);
      const endX = centerX + radius * Math.cos((endAngle * Math.PI) / 180);
      const endY = centerY + radius * Math.sin((endAngle * Math.PI) / 180);
      
      backgroundPath = `M ${startX} ${startY} A ${radius} ${radius} 0 1 1 ${endX} ${endY}`;
      progressPath = backgroundPath;
    }

    return (
      <div className="relative cursor-pointer" onClick={handleGaugeClick}>
        <svg
          width={size}
          height={svgHeight}
          className={gaugeType === 'semicircle' ? "transform -rotate-90" : ""}
          style={{ overflow: 'visible' }}
        >
          {/* Background arc */}
          <path
            d={backgroundPath}
            fill="none"
            stroke="var(--chart-grid, #e5e7eb)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          
          {/* Progress arc */}
          <path
            d={progressPath}
            fill="none"
            stroke={getColor()}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            style={{
              transition: animation ? 'stroke-dashoffset 0.75s ease-in-out, stroke 0.3s ease-in-out' : 'none'
            }}
          />
          
          {/* Threshold markers */}
          {showThresholds && thresholds.map((threshold, index) => {
            const thresholdPercentage = ((threshold - min) / (max - min)) * 100;
            const thresholdOffset = circumference - (thresholdPercentage / 100) * circumference;
            
            return (
              <path
                key={index}
                d={progressPath}
                fill="none"
                stroke="white"
                strokeWidth={strokeWidth + 4}
                strokeLinecap="round"
                strokeDasharray="2 1000"
                strokeDashoffset={thresholdOffset}
                opacity={0.8}
              />
            );
          })}
        </svg>

        {/* Center value */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <div className="text-3xl font-bold" style={{ color: getColor() }}>
            {formatNumber(currentValue, 'default')}{unit}
          </div>
          <div className="text-sm text-gray-500 mt-1 font-medium">
            {getStatus()}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {clampedPercentage.toFixed(1)}%
          </div>
        </div>
      </div>
    );
  };

  return (
    <BaseChart config={config} {...baseProps}>
      <div className="w-full h-full flex flex-col items-center justify-center p-4">
        {renderGauge()}

        {/* Scale indicators */}
        {showScale && (
          <div className="flex justify-between w-full max-w-[240px] mt-4 text-xs text-gray-500">
            <span>{formatNumber(min)}{unit}</span>
            {thresholds.map((threshold, index) => (
              <span key={index}>{formatNumber(threshold)}{unit}</span>
            ))}
            <span>{formatNumber(max)}{unit}</span>
          </div>
        )}

        {/* Threshold legend */}
        {showThresholds && (
          <div className="flex items-center justify-center space-x-6 mt-4 text-xs">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colorScheme[0] }}
              />
              <span className="text-gray-600 font-medium">危险 (≤{formatNumber(thresholds[0])})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colorScheme[1] }}
              />
              <span className="text-gray-600 font-medium">警告 (≤{formatNumber(thresholds[1])})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colorScheme[2] }}
              />
              <span className="text-gray-600 font-medium">正常 (&gt;{formatNumber(thresholds[1])})</span>
            </div>
          </div>
        )}
      </div>
    </BaseChart>
  );
};

export default GaugeChart;