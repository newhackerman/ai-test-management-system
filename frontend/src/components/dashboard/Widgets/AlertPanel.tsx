import React from 'react';

interface AlertPanelProps {
  config: {
    title?: string;
    severity?: string;
    limit?: number;
  };
  data?: any;
}

const AlertPanel: React.FC<AlertPanelProps> = ({ config, data }) => {
  return (
    <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
      <div className="text-center">
        <div className="text-2xl mb-2">🚨</div>
        <p className="text-sm">告警面板</p>
        <p className="text-xs text-gray-400 mt-1 dark:text-gray-500">开发中...</p>
      </div>
    </div>
  );
};

export default AlertPanel;