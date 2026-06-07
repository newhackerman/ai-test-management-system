// @ts-nocheck
import React from 'react';
import { Widget } from '@/hooks/dashboard/useDashboard';
import { StatCard } from './StatCard';
import { LineChart } from './Charts/LineChart';
import { BarChart } from './Charts/BarChart';
import { PieChart } from './Charts/PieChart';
import { GaugeChart } from './Charts/GaugeChart';
import { ProgressBar } from './ProgressBar';
import { StatusPanel } from './StatusPanel';
import { TaskList } from './TaskList';
import { RankingList } from './RankingList';
import { CalendarView } from './CalendarView';
import { DataTable } from './DataTable';
import { AlertPanel } from './AlertPanel';

interface WidgetContentProps {
  widget: Widget;
  realtimeData?: any;
  isLoading?: boolean;
}

const WidgetContent: React.FC<WidgetContentProps> = ({
  widget,
  realtimeData,
  isLoading = false
}) => {
  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Render appropriate widget based on type
  switch (widget.type) {
    case 'stat_card':
      return (
        <StatCard
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'line_chart':
      return (
        <LineChart
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'bar_chart':
      return (
        <BarChart
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'pie_chart':
      return (
        <PieChart
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'gauge_chart':
      return (
        <GaugeChart
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'progress_bar':
      return (
        <ProgressBar
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'status_panel':
      return (
        <StatusPanel
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'task_list':
      return (
        <TaskList
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'ranking_list':
      return (
        <RankingList
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'calendar_view':
      return (
        <CalendarView
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'data_table':
      return (
        <DataTable
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    case 'alert_panel':
      return (
        <AlertPanel
          config={widget.config}
          data={realtimeData || widget.data}
        />
      );

    default:
      return (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <div className="text-2xl mb-2">馃敡</div>
            <p className="text-sm">鏈煡缁勪欢绫诲瀷: {widget.type}</p>
          </div>
        </div>
      );
  }
};

export default WidgetContent;