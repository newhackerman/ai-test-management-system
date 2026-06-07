/**
 * 懒加载项目组件
 * 
 * 使用React.lazy实现组件懒加载，减少初始包大小
 */
import React, { Suspense } from 'react';
import { Spin } from 'antd';

// 懒加载组件
const ProjectList = React.lazy(() => import('../ProjectList'));
const ProjectDetail = React.lazy(() => import('../ProjectDetail'));
const ProjectCreateModal = React.lazy(() => import('../ProjectCreateModal'));
const TaskBoard = React.lazy(() => import('../TaskBoard'));
const TaskManagement = React.lazy(() => import('../TaskManagement'));
const TeamManagement = React.lazy(() => import('../TeamManagement'));
const GanttChart = React.lazy(() => import('../GanttChart'));
const StatisticsDashboard = React.lazy(() => import('../StatisticsDashboard'));
const ProgressTrackingDashboard = React.lazy(() => import('../ProgressTrackingDashboard'));
const RiskMatrix = React.lazy(() => import('../RiskMatrix'));
const MilestoneTimeline = React.lazy(() => import('../MilestoneTimeline'));
const PerformanceAnalysis = React.lazy(() => import('../PerformanceAnalysis'));

// 加载中组件
const LoadingSpinner: React.FC<{ tip?: string }> = ({ tip = '加载中...' }) => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    minHeight: '200px' 
  }}>
    <Spin size="large" tip={tip} />
  </div>
);

// 错误边界组件
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('组件加载错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ 
          padding: '20px', 
          textAlign: 'center', 
          color: '#ff4d4f' 
        }}>
          组件加载失败，请刷新页面重试
        </div>
      );
    }

    return this.props.children;
  }
}

// 懒加载包装器
const withLazyLoading = <P extends object>(
  Component: React.LazyExoticComponent<React.ComponentType<P>>,
  loadingTip?: string,
  fallback?: React.ReactNode
) => {
  return React.forwardRef<any, P>((props, ref) => (
    <ErrorBoundary fallback={fallback}>
      <Suspense fallback={<LoadingSpinner tip={loadingTip} />}>
        <Component {...props} ref={ref} />
      </Suspense>
    </ErrorBoundary>
  ));
};

// 导出懒加载组件
export const LazyProjectList = withLazyLoading(
  ProjectList, 
  '加载项目列表...'
);

export const LazyProjectDetail = withLazyLoading(
  ProjectDetail, 
  '加载项目详情...'
);

export const LazyProjectCreateModal = withLazyLoading(
  ProjectCreateModal, 
  '加载创建表单...'
);

export const LazyTaskBoard = withLazyLoading(
  TaskBoard, 
  '加载任务看板...'
);

export const LazyTaskManagement = withLazyLoading(
  TaskManagement, 
  '加载任务管理...'
);

export const LazyTeamManagement = withLazyLoading(
  TeamManagement, 
  '加载团队管理...'
);

export const LazyGanttChart = withLazyLoading(
  GanttChart, 
  '加载甘特图...'
);

export const LazyStatisticsDashboard = withLazyLoading(
  StatisticsDashboard, 
  '加载统计面板...'
);

export const LazyProgressTrackingDashboard = withLazyLoading(
  ProgressTrackingDashboard, 
  '加载进度跟踪...'
);

export const LazyRiskMatrix = withLazyLoading(
  RiskMatrix, 
  '加载风险矩阵...'
);

export const LazyMilestoneTimeline = withLazyLoading(
  MilestoneTimeline, 
  '加载里程碑时间轴...'
);

export const LazyPerformanceAnalysis = withLazyLoading(
  PerformanceAnalysis, 
  '加载性能分析...'
);

// 预加载函数
export const preloadComponents = {
  projectList: () => import('../ProjectList'),
  projectDetail: () => import('../ProjectDetail'),
  taskBoard: () => import('../TaskBoard'),
  ganttChart: () => import('../GanttChart'),
  statistics: () => import('../StatisticsDashboard'),
  progressTracking: () => import('../ProgressTrackingDashboard'),
  riskMatrix: () => import('../RiskMatrix'),
  milestoneTimeline: () => import('../MilestoneTimeline'),
  performanceAnalysis: () => import('../PerformanceAnalysis'),
};

// 预加载策略
export const preloadStrategy = {
  // 立即预加载核心组件
  immediate: () => {
    preloadComponents.projectList();
    preloadComponents.projectDetail();
  },
  
  // 延迟预加载次要组件
  delayed: () => {
    setTimeout(() => {
      preloadComponents.taskBoard();
      preloadComponents.statistics();
    }, 2000);
  },
  
  // 按需预加载
  onDemand: (componentName: keyof typeof preloadComponents) => {
    return preloadComponents[componentName]();
  },
  
  // 预加载所有组件
  all: () => {
    Object.values(preloadComponents).forEach(preload => preload());
  }
};

// 组件预加载Hook
export const useComponentPreload = () => {
  React.useEffect(() => {
    // 页面加载后立即预加载核心组件
    preloadStrategy.immediate();
    
    // 延迟预加载次要组件
    preloadStrategy.delayed();
    
    // 监听用户交互，预加载可能需要的组件
    const handleUserInteraction = () => {
      preloadStrategy.onDemand('ganttChart');
      preloadStrategy.onDemand('progressTracking');
    };
    
    // 监听鼠标移动和点击事件
    document.addEventListener('mousemove', handleUserInteraction, { once: true });
    document.addEventListener('click', handleUserInteraction, { once: true });
    
    return () => {
      document.removeEventListener('mousemove', handleUserInteraction);
      document.removeEventListener('click', handleUserInteraction);
    };
  }, []);
  
  return { preloadComponent: preloadStrategy.onDemand };
};

export default {
  LazyProjectList,
  LazyProjectDetail,
  LazyProjectCreateModal,
  LazyTaskBoard,
  LazyTaskManagement,
  LazyTeamManagement,
  LazyGanttChart,
  LazyStatisticsDashboard,
  LazyProgressTrackingDashboard,
  LazyRiskMatrix,
  LazyMilestoneTimeline,
  LazyPerformanceAnalysis,
  preloadStrategy,
  useComponentPreload
};