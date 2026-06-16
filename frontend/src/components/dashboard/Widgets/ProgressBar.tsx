import React, { useMemo } from 'react';

interface ProgressBarProps {
  config: {
    title?: string;
    showPercentage?: boolean;
    colorScheme?: string;
    thresholds?: { value: number; color: string; label: string }[];
  };
  data?: any;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ config, data }) => {
  const {
    showPercentage = true,
    colorScheme = 'default',
    thresholds = [
      { value: 30, color: '#EF4444', label: '低' },
      { value: 70, color: '#F59E0B', label: '中' },
      { value: 100, color: '#10B981', label: '高' }
    ]
  } = config;

  // Process data
  const progressData = useMemo(() => {
    if (data && Array.isArray(data)) {
      return data;
    }
    
    if (data && typeof data === 'object') {
      if (data.items && Array.isArray(data.items)) {
        return data.items;
      }
      
      // Single progress item
      return [{
        label: data.label || '进度',
        value: data.value || 0,
        total: data.total || 100,
        description: data.description
      }];
    }

    // Generate sample data
    return [
      { label: '项目完成度', value: 75, total: 100, description: '15/20 任务完成' },
      { label: '测试覆盖率', value: 85, total: 100, description: '850/1000 用例' },
      { label: '代码质量', value: 92, total: 100, description: '质量评分' }
    ];
  }, [data]);

  const getProgressColor = (percentage: number) => {
    if (colorScheme !== 'default') {
      return colorScheme;
    }

    // Find appropriate color based on thresholds
    for (let i = thresholds.length - 1; i >= 0; i--) {
      if (percentage >= thresholds[i].value) {
        return thresholds[i].color;
      }
    }
    return thresholds[0].color;
  };

  const getProgressLabel = (percentage: number) => {
    for (let i = thresholds.length - 1; i >= 0; i--) {
      if (percentage >= thresholds[i].value) {
        return thresholds[i].label;
      }
    }
    return thresholds[0].label;
  };

  return (
    <div className="h-full space-y-4">
      {progressData.map((item, index) => {
        const percentage = (item.value / item.total) * 100;
        const color = getProgressColor(percentage);
        const label = getProgressLabel(percentage);

        return (
          <div key={index} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {item.label}
              </span>
              <div className="flex items-center space-x-2">
                {showPercentage && (
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {percentage.toFixed(1)}%
                  </span>
                )}
                <span 
                  className="text-xs px-2 py-1 rounded-full text-white"
                  style={{ backgroundColor: color }}
                >
                  {label}
                </span>
              </div>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${Math.min(100, percentage)}%`,
                  backgroundColor: color
                }}
              />
            </div>
            
            {item.description && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {item.description}
              </div>
            )}
          </div>
        );
      })}
      
      {/* Legend for thresholds */}
      {progressData.length === 1 && (
        <div className="flex items-center justify-center space-x-4 mt-4 text-xs">
          {thresholds.map((threshold, index) => (
            <div key={index} className="flex items-center space-x-1">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: threshold.color }}
              />
              <span className="text-gray-600 dark:text-gray-400">
                {threshold.label} ({threshold.value}%+)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;