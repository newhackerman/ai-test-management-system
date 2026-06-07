import React, { useMemo } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { MoreHorizontal, Download, Maximize2, RefreshCw } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/DropdownMenu';

export interface ChartTheme {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  grid: string;
}

export interface ChartConfig {
  title?: string;
  subtitle?: string;
  showLegend?: boolean;
  showTooltip?: boolean;
  showGrid?: boolean;
  colorScheme?: string[];
  theme?: ChartTheme;
  interactive?: boolean;
  drillDown?: boolean;
  exportable?: boolean;
  refreshable?: boolean;
  height?: number;
  animation?: boolean;
  responsive?: boolean;
}

export interface BaseChartProps {
  config: ChartConfig;
  data?: any;
  loading?: boolean;
  error?: string;
  onDrillDown?: (data: any) => void;
  onExport?: (format: 'png' | 'svg' | 'pdf' | 'excel') => void;
  onRefresh?: () => void;
  className?: string;
  children: React.ReactNode;
}

const defaultTheme: ChartTheme = {
  primary: '#3B82F6',
  secondary: '#10B981',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#06B6D4',
  background: '#FFFFFF',
  surface: '#F8FAFC',
  text: '#1F2937',
  textSecondary: '#6B7280',
  border: '#E5E7EB',
  grid: '#F3F4F6'
};

export const BaseChart: React.FC<BaseChartProps> = ({
  config,
  data,
  loading = false,
  error,
  onDrillDown,
  onExport,
  onRefresh,
  className = '',
  children
}) => {
  const {
    title,
    subtitle,
    exportable = true,
    refreshable = true,
    height = 300,
    theme = defaultTheme
  } = config;

  const chartStyle = useMemo(() => ({
    height: `${height}px`,
    '--chart-primary': theme.primary,
    '--chart-secondary': theme.secondary,
    '--chart-success': theme.success,
    '--chart-warning': theme.warning,
    '--chart-error': theme.error,
    '--chart-info': theme.info,
    '--chart-background': theme.background,
    '--chart-surface': theme.surface,
    '--chart-text': theme.text,
    '--chart-text-secondary': theme.textSecondary,
    '--chart-border': theme.border,
    '--chart-grid': theme.grid,
  } as React.CSSProperties), [theme, height]);

  const handleExport = (format: 'png' | 'svg' | 'pdf' | 'excel') => {
    if (onExport) {
      onExport(format);
    }
  };

  if (error) {
    return (
      <Card className={`p-4 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          {title && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
            </div>
          )}
        </div>
        <div className="flex items-center justify-center h-48 text-red-500">
          <div className="text-center">
            <p className="text-lg font-medium">加载失败</p>
            <p className="text-sm text-gray-500 mt-1">{error}</p>
            {refreshable && onRefresh && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                className="mt-2"
              >
                <RefreshCw className="w-4 h-4 mr-1" />
                重试
              </Button>
            )}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`p-4 ${className}`} style={chartStyle}>
      {/* Chart Header */}
      <div className="flex items-center justify-between mb-4">
        {(title || subtitle) && (
          <div className="flex-1">
            {title && (
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-gray-500">{subtitle}</p>
            )}
          </div>
        )}
        
        {/* Chart Actions */}
        <div className="flex items-center space-x-2">
          {refreshable && onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={loading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          )}
          
          {exportable && onExport && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleExport('png')}>
                  <Download className="w-4 h-4 mr-2" />
                  导出为 PNG
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('svg')}>
                  <Download className="w-4 h-4 mr-2" />
                  导出为 SVG
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('pdf')}>
                  <Download className="w-4 h-4 mr-2" />
                  导出为 PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('excel')}>
                  <Download className="w-4 h-4 mr-2" />
                  导出为 Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* Chart Content */}
      <div className="relative" style={{ height: `${height - 80}px` }}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
              <p className="text-sm text-gray-500">加载中...</p>
            </div>
          </div>
        ) : (
          children
        )}
      </div>
    </Card>
  );
};

export default BaseChart;