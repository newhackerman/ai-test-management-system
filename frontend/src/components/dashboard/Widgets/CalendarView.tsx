import React from 'react';

interface CalendarViewProps {
  config: {
    title?: string;
    view?: string;
    showEvents?: boolean;
  };
  data?: any;
}

const CalendarView: React.FC<CalendarViewProps> = ({ config, data }) => {
  return (
    <div className="h-full flex items-center justify-center text-gray-500">
      <div className="text-center">
        <div className="text-2xl mb-2">📅</div>
        <p className="text-sm">日历组件</p>
        <p className="text-xs text-gray-400 mt-1">开发中...</p>
      </div>
    </div>
  );
};

export default CalendarView;