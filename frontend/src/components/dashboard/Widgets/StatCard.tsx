import React, { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  config: {
    title?: string;
    metrics?: string[];
    showTrend?: boolean;
    unit?: string;
  };
  data?: any;
}

const StatCard: React.FC<StatCardProps> = ({ config, data }) => {
  const {
    metrics = ['total_count'],
    showTrend = true,
    unit = ''
  } = config;

  // Process data for display
  const stats = useMemo(() => {
    if (data && typeof data === 'object') {
      return metrics.map(metric => ({
        key: metric,
        value: data[metric] || 0,
        trend: data[`${metric}_trend`] || 0,
        label: metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      }));
    }

    // Generate sample data
    return metrics.map(metric => ({
      key: metric,
      value: Math.floor(Math.random() * 1000) + 100,
      trend: (Math.random() - 0.5) * 20,
      label: metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }));
  }, [data, metrics]);

  const formatValue = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  const getTrendIcon = (trend: number) => {
    if (trend > 0) {
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    } else if (trend < 0) {
      return <TrendingDown className="h-4 w-4 text-red-500 dark:text-red-400" />;
    } else {
      return <Minus className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
    }
  };

  const getTrendColor = (trend: number) => {
    if (trend > 0) return 'text-green-600';
    if (trend < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  if (stats.length === 1) {
    // Single metric display
    const stat = stats[0];
    return (
      <div className="h-full flex flex-col justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-900 mb-1 dark:text-gray-100">
            {formatValue(stat.value)}{unit}
          </div>
          <div className="text-sm text-gray-600 mb-2 dark:text-gray-400">
            {stat.label}
          </div>
          {showTrend && (
            <div className={`flex items-center justify-center space-x-1 text-sm ${getTrendColor(stat.trend)}`}>
              {getTrendIcon(stat.trend)}
              <span>{Math.abs(stat.trend).toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Multiple metrics display
  return (
    <div className="h-full">
      <div className="grid grid-cols-1 gap-3 h-full">
        {stats.map((stat, index) => (
          <div key={stat.key} className="flex items-center justify-between p-2 bg-gray-50 rounded dark:bg-gray-800/50">
            <div className="flex-1">
              <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {formatValue(stat.value)}{unit}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {stat.label}
              </div>
            </div>
            {showTrend && (
              <div className={`flex items-center space-x-1 text-xs ${getTrendColor(stat.trend)}`}>
                {getTrendIcon(stat.trend)}
                <span>{Math.abs(stat.trend).toFixed(1)}%</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default StatCard;