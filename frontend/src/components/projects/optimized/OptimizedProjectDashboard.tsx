// @ts-nocheck
/**
 * 浼樺寲鐨勯」鐩华琛ㄦ澘缁勪欢
 * 
 * 闆嗘垚鎵€鏈夋€ц兘浼樺寲鎶€鏈殑椤圭洰绠＄悊涓荤晫闈?
 */
import React, { Suspense, useState, useCallback, useMemo, useEffect } from 'react';
import { Layout, Tabs, Spin, Alert, Button, Space } from 'antd';
import { 
  ProjectOutlined, 
  BarChartOutlined, 
  TeamOutlined, 
  SettingOutlined,
  ReloadOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import { ErrorBoundary } from 'react-error-boundary';

// 鎳掑姞杞界粍浠?
import { 
  LazyProjectList,
  LazyStatisticsDashboard,
  LazyTeamManagement,
  useComponentPreload
} from './LazyProjectComponents';
import { VirtualizedProjectList } from './VirtualizedProjectList';
import { useOptimizedProjectList, useProjectPerformanceMonitor } from '../../hooks/projects/useOptimizedProjects';
import { usePerformanceMonitor } from '../../lib/performance-monitor';
import { Project } from '../../types/project';

const { Content } = Layout;
const { TabPane } = Tabs;

// 閿欒鍥為€€缁勪欢
const ErrorFallback: React.FC<{ error: Error; resetErrorBoundary: () => void }> = ({ 
  error, 
  resetErrorBoundary 
}) => (
  <Alert
    message="缁勪欢鍔犺浇澶辫触"
    description={error.message}
    type="error"
    showIcon
    action={
      <Button size="small" onClick={resetErrorBoundary}>
        閲嶈瘯
      </Button>
    }
  />
);

// 鍔犺浇涓粍浠?
const LoadingFallback: React.FC<{ tip?: string }> = ({ tip = '鍔犺浇涓?..' }) => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    minHeight: '400px' 
  }}>
    <Spin size="large" tip={tip} />
  </div>
);

// 鎬ц兘鐩戞帶闈㈡澘
const PerformancePanel: React.FC = React.memo(() => {
  const { metrics } = useProjectPerformanceMonitor();
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div style={{ 
      position: 'fixed', 
      top: 20, 
      right: 20, 
      background: 'rgba(0,0,0,0.8)', 
      color: 'white', 
      padding: '8px 12px', 
      borderRadius: '4px', 
      fontSize: '12px',
      zIndex: 1000,
      minWidth: '200px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>鎬ц兘鐩戞帶</span>
        <Button 
          type="text" 
          size="small" 
          icon={<ThunderboltOutlined />}
          onClick={() => setShowDetails(!showDetails)}
          style={{ color: 'white' }}
        />
      </div>
      
      {showDetails && (
        <div style={{ marginTop: 8, fontSize: '11px' }}>
          <div>娓叉煋鏃堕棿: {metrics.renderTime.toFixed(2)}ms</div>
          <div>鏌ヨ鏃堕棿: {metrics.queryTime.toFixed(2)}ms</div>
          <div>缂撳瓨鍛戒腑鐜? {(metrics.cacheHitRate * 100).toFixed(1)}%</div>
          <div>閿欒鐜? {(metrics.errorRate * 100).toFixed(1)}%</div>
        </div>
      )}
    </div>
  );
});

PerformancePanel.displayName = 'PerformancePanel';

// 涓荤粍浠?
export const OptimizedProjectDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('projects');
  const [useVirtualization, setUseVirtualization] = useState(false);
  
  // 棰勫姞杞界粍浠?
  useComponentPreload();
  
  // 鎬ц兘鐩戞帶
  usePerformanceMonitor('OptimizedProjectDashboard');
  
  // 椤圭洰鏁版嵁
  const {
    projects,
    total,
    isLoading,
    isFetching,
    error,
    params,
    refetch,
    updateSearch,
    updateFilters,
    updatePagination,
    updateSort,
    prefetchNextPage,
  } = useOptimizedProjectList({
    size: useVirtualization ? 100 : 20, // 铏氭嫙鍖栨椂鍔犺浇鏇村鏁版嵁
  });

  // 椤圭洰鎿嶄綔澶勭悊
  const handleProjectClick = useCallback((project: Project) => {
    console.log('Project clicked:', project);
    // 杩欓噷鍙互瀵艰埅鍒伴」鐩鎯呴〉
  }, []);

  const handleProjectEdit = useCallback((project: Project) => {
    console.log('Project edit:', project);
    // 杩欓噷鍙互鎵撳紑缂栬緫妯℃€佹
  }, []);

  const handleProjectDelete = useCallback((project: Project) => {
    console.log('Project delete:', project);
    // 杩欓噷鍙互鏄剧ず鍒犻櫎纭瀵硅瘽妗?
  }, []);

  // 鎼滅储澶勭悊
  const handleSearch = useCallback((value: string) => {
    updateSearch(value);
  }, [updateSearch]);

  // 杩囨护澶勭悊
  const handleStatusFilter = useCallback((status: string[]) => {
    updateFilters({ status });
  }, [updateFilters]);

  const handleTypeFilter = useCallback((type: string[]) => {
    updateFilters({ project_type: type });
  }, [updateFilters]);

  const handlePriorityFilter = useCallback((priority: string[]) => {
    updateFilters({ priority });
  }, [updateFilters]);

  // 鍒锋柊澶勭悊
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // 鍒囨崲铏氭嫙鍖?
  const toggleVirtualization = useCallback(() => {
    setUseVirtualization(prev => !prev);
  }, []);

  // 棰勫姞杞戒笅涓€椤?
  useEffect(() => {
    if (projects.length > 0 && !isFetching) {
      const timer = setTimeout(() => {
        prefetchNextPage();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [projects.length, isFetching, prefetchNextPage]);

  // 鏍囩椤甸厤缃?
  const tabItems = useMemo(() => [
    {
      key: 'projects',
      label: (
        <span>
          <ProjectOutlined />
          椤圭洰鍒楄〃 ({total})
        </span>
      ),
      children: (
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <Suspense fallback={<LoadingFallback tip="鍔犺浇椤圭洰鍒楄〃..." />}>
            <div>
              <div style={{ marginBottom: 16 }}>
                <Space>
                  <Button
                    type={useVirtualization ? 'primary' : 'default'}
                    onClick={toggleVirtualization}
                    icon={<ThunderboltOutlined />}
                  >
                    {useVirtualization ? '虚拟化已启用' : '启用虚拟化'}
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    loading={isFetching}
                  >
                    鍒锋柊
                  </Button>
                </Space>
              </div>

              {useVirtualization ? (
                <VirtualizedProjectList
                  projects={projects}
                  loading={isLoading}
                  onProjectClick={handleProjectClick}
                  onProjectEdit={handleProjectEdit}
                  onProjectDelete={handleProjectDelete}
                  onRefresh={handleRefresh}
                  height={600}
                />
              ) : (
                <LazyProjectList
                  projects={projects}
                  loading={isLoading}
                  total={total}
                  params={params}
                  onProjectClick={handleProjectClick}
                  onProjectEdit={handleProjectEdit}
                  onProjectDelete={handleProjectDelete}
                  onSearch={handleSearch}
                  onStatusFilter={handleStatusFilter}
                  onTypeFilter={handleTypeFilter}
                  onPriorityFilter={handlePriorityFilter}
                  onPaginationChange={updatePagination}
                  onSortChange={updateSort}
                  onRefresh={handleRefresh}
                />
              )}
            </div>
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: 'statistics',
      label: (
        <span>
          <BarChartOutlined />
          缁熻鍒嗘瀽
        </span>
      ),
      children: (
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <Suspense fallback={<LoadingFallback tip="鍔犺浇缁熻闈㈡澘..." />}>
            <LazyStatisticsDashboard />
          </Suspense>
        </ErrorBoundary>
      ),
    },
    {
      key: 'team',
      label: (
        <span>
          <TeamOutlined />
          鍥㈤槦绠＄悊
        </span>
      ),
      children: (
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <Suspense fallback={<LoadingFallback tip="鍔犺浇鍥㈤槦绠＄悊..." />}>
            <LazyTeamManagement />
          </Suspense>
        </ErrorBoundary>
      ),
    },
  ], [
    total,
    useVirtualization,
    projects,
    isLoading,
    isFetching,
    params,
    handleProjectClick,
    handleProjectEdit,
    handleProjectDelete,
    handleRefresh,
    handleSearch,
    handleStatusFilter,
    handleTypeFilter,
    handlePriorityFilter,
    updatePagination,
    updateSort,
    toggleVirtualization,
  ]);

  // 閿欒澶勭悊
  if (error) {
    return (
      <Alert
        message="鏁版嵁鍔犺浇澶辫触"
        description={error.message}
        type="error"
        showIcon
        action={
          <Button onClick={handleRefresh} loading={isFetching}>
            閲嶈瘯
          </Button>
        }
      />
    );
  }

  return (
    <Layout>
      <Content style={{ padding: '24px' }}>
        <div style={{ background: '#fff', minHeight: '100vh', padding: '24px' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            size="large"
            tabBarStyle={{ marginBottom: '24px' }}
          />
        </div>
      </Content>
      
      {/* 鎬ц兘鐩戞帶闈㈡澘 */}
      {process.env.NODE_ENV === 'development' && <PerformancePanel />}
    </Layout>
  );
};

export default React.memo(OptimizedProjectDashboard);
