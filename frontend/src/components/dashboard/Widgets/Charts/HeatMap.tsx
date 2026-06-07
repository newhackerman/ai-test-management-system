import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import BaseChart, { BaseChartProps, ChartConfig } from './BaseChart';
import { getColorScheme, formatNumber, generateSampleData, handleChartClick } from './chartUtils';

interface HeatMapConfig extends ChartConfig {
  xAxisKey?: string;
  yAxisKey?: string;
  valueKey?: string;
  cellSize?: number;
  cellPadding?: number;
  showValues?: boolean;
  colorRange?: [string, string];
  domain?: [number, number];
}

interface HeatMapProps extends Omit<BaseChartProps, 'config' | 'children'> {
  config: HeatMapConfig;
}

interface HeatMapDataPoint {
  [key: string]: any;
  x: string | number;
  y: string | number;
  value: number;
}

const HeatMap: React.FC<HeatMapProps> = ({ config, data, onDrillDown, ...baseProps }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const {
    xAxisKey = 'x',
    yAxisKey = 'y',
    valueKey = 'value',
    cellSize = 20,
    cellPadding = 2,
    showValues = false,
    colorRange = ['#f0f9ff', '#1e40af'],
    domain,
    colorScheme = getColorScheme('cool'),
    animation = true
  } = config;

  // Generate sample data if no data provided
  const chartData = useMemo((): HeatMapDataPoint[] => {
    if (data && Array.isArray(data)) {
      return data.map(item => ({
        ...item,
        x: item[xAxisKey],
        y: item[yAxisKey],
        value: item[valueKey]
      }));
    }

    // Generate sample heatmap data
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const sampleData: HeatMapDataPoint[] = [];

    days.forEach(day => {
      hours.forEach(hour => {
        sampleData.push({
          x: hour,
          y: day,
          value: Math.floor(Math.random() * 100)
        });
      });
    });

    return sampleData;
  }, [data, xAxisKey, yAxisKey, valueKey]);

  // Get unique x and y values
  const xValues = useMemo(() => {
    return Array.from(new Set(chartData.map(d => d.x))).sort();
  }, [chartData]);

  const yValues = useMemo(() => {
    return Array.from(new Set(chartData.map(d => d.y))).sort();
  }, [chartData]);

  // Create value domain
  const valueDomain = useMemo(() => {
    if (domain) return domain;
    const values = chartData.map(d => d.value);
    return [Math.min(...values), Math.max(...values)];
  }, [chartData, domain]);

  // Color scale
  const colorScale = useMemo(() => {
    return d3.scaleSequential()
      .domain(valueDomain)
      .interpolator(d3.interpolateRgb(colorRange[0], colorRange[1]));
  }, [valueDomain, colorRange]);

  const handleCellClick = useCallback((d: HeatMapDataPoint) => {
    handleChartClick(d, onDrillDown);
  }, [onDrillDown]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const svg = d3.select(svgRef.current);
    
    // Clear previous content
    svg.selectAll('*').remove();

    // Get container dimensions
    const containerRect = container.getBoundingClientRect();
    const margin = { top: 40, right: 40, bottom: 60, left: 80 };
    const width = containerRect.width - margin.left - margin.right;
    const height = containerRect.height - margin.top - margin.bottom;

    // Calculate cell dimensions
    const cellWidth = Math.max(cellSize, (width - cellPadding * (xValues.length - 1)) / xValues.length);
    const cellHeight = Math.max(cellSize, (height - cellPadding * (yValues.length - 1)) / yValues.length);

    // Create scales
    const xScale = d3.scaleBand()
      .domain(xValues.map(String))
      .range([0, width])
      .padding(cellPadding / cellWidth);

    const yScale = d3.scaleBand()
      .domain(yValues.map(String))
      .range([0, height])
      .padding(cellPadding / cellHeight);

    // Create main group
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create tooltip
    const tooltip = d3.select('body').selectAll('.heatmap-tooltip')
      .data([0])
      .join('div')
      .attr('class', 'heatmap-tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '8px 12px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('z-index', '1000');

    // Create cells
    const cells = g.selectAll('.cell')
      .data(chartData)
      .join('rect')
      .attr('class', 'cell')
      .attr('x', d => xScale(String(d.x)) || 0)
      .attr('y', d => yScale(String(d.y)) || 0)
      .attr('width', xScale.bandwidth())
      .attr('height', yScale.bandwidth())
      .attr('fill', d => colorScale(d.value))
      .attr('stroke', 'white')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .attr('stroke-width', 2)
          .attr('stroke', '#374151');
        
        tooltip
          .style('visibility', 'visible')
          .html(`
            <div><strong>${d.x} - ${d.y}</strong></div>
            <div>值: ${formatNumber(d.value)}</div>
          `);
      })
      .on('mousemove', function(event) {
        tooltip
          .style('top', (event.pageY - 10) + 'px')
          .style('left', (event.pageX + 10) + 'px');
      })
      .on('mouseout', function() {
        d3.select(this)
          .attr('stroke-width', 1)
          .attr('stroke', 'white');
        
        tooltip.style('visibility', 'hidden');
      })
      .on('click', function(event, d) {
        handleCellClick(d);
      });

    // Add animation
    if (animation) {
      cells
        .attr('opacity', 0)
        .transition()
        .duration(750)
        .delay((d, i) => i * 2)
        .attr('opacity', 1);
    }

    // Add cell values if enabled
    if (showValues) {
      g.selectAll('.cell-text')
        .data(chartData)
        .join('text')
        .attr('class', 'cell-text')
        .attr('x', d => (xScale(String(d.x)) || 0) + xScale.bandwidth() / 2)
        .attr('y', d => (yScale(String(d.y)) || 0) + yScale.bandwidth() / 2)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('fill', d => d3.lab(colorScale(d.value)).l > 50 ? '#374151' : 'white')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(d => formatNumber(d.value, 'compact'))
        .style('pointer-events', 'none');
    }

    // Add X axis
    const xAxis = d3.axisBottom(xScale)
      .tickSize(0)
      .tickPadding(8);

    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', 'var(--chart-text-secondary, #6b7280)')
      .style('font-size', '11px');

    // Add Y axis
    const yAxis = d3.axisLeft(yScale)
      .tickSize(0)
      .tickPadding(8);

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', 'var(--chart-text-secondary, #6b7280)')
      .style('font-size', '11px');

    // Remove axis lines
    g.selectAll('.domain').remove();

    // Add color legend
    const legendWidth = 200;
    const legendHeight = 10;
    const legendX = width - legendWidth;
    const legendY = -30;

    const legendScale = d3.scaleLinear()
      .domain(valueDomain)
      .range([0, legendWidth]);

    const legendAxis = d3.axisBottom(legendScale)
      .ticks(5)
      .tickSize(3)
      .tickFormat(d => formatNumber(d as number, 'compact'));

    // Create gradient for legend
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', 'heatmap-gradient')
      .attr('x1', '0%')
      .attr('x2', '100%')
      .attr('y1', '0%')
      .attr('y2', '0%');

    gradient.selectAll('stop')
      .data(d3.range(0, 1.1, 0.1))
      .join('stop')
      .attr('offset', d => `${d * 100}%`)
      .attr('stop-color', d => colorScale(valueDomain[0] + d * (valueDomain[1] - valueDomain[0])));

    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${legendX},${legendY})`);

    legend.append('rect')
      .attr('width', legendWidth)
      .attr('height', legendHeight)
      .attr('fill', 'url(#heatmap-gradient)')
      .attr('stroke', 'var(--chart-border, #e5e7eb)');

    legend.append('g')
      .attr('transform', `translate(0,${legendHeight})`)
      .call(legendAxis)
      .selectAll('text')
      .attr('fill', 'var(--chart-text-secondary, #6b7280)')
      .style('font-size', '10px');

    // Cleanup function
    return () => {
      tooltip.remove();
    };
  }, [chartData, xValues, yValues, colorScale, cellSize, cellPadding, showValues, animation, handleCellClick]);

  return (
    <BaseChart config={config} {...baseProps}>
      <div ref={containerRef} className="w-full h-full">
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          className="overflow-visible"
        />
      </div>
    </BaseChart>
  );
};

export default HeatMap;