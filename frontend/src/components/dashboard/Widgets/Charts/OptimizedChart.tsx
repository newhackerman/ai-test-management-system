// @ts-nocheck
/**
 * 浼樺寲鐨勫浘琛ㄧ粍浠?
 * 
 * 闆嗘垚铏氭嫙鍖栥€佹噿鍔犺浇銆佹€ц兘鐩戞帶绛変紭鍖栧姛鑳?
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BaseChart, BaseChartProps, ChartConfig } from './BaseChart';
import {
  useChartOptimization,
  useLazyChart,
  useVirtualization,
  useAnimationOptimization,
  VirtualizationConfig,
  RenderOptimizationConfig,
  ChartPerformanceAnalyzer,
} from '@/utils/chartOptimization';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { 
  Activity, 
  Zap, 
  Database, 
  Clock, 
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle 
} from 'lucide-react';

// 鎵╁睍鐨勫浘琛ㄩ厤缃?
export interface OptimizedChartConfig extends ChartConfig {
  optimization?: Partial<RenderOptimizationConfig>;
  virtualization?: VirtualizationConfig;
  enablePerformanceMonitoring?: boolean;
  enableLazyLoading?: boolean;
  lazyLoadThreshold?: number;
}

// 鎵╁睍鐨勫浘琛ㄥ睘鎬?
export interface OptimizedChartProps extends Omit<BaseChartProps, 'config'> {
  config: OptimizedChartConfig;
  chartId: string;
  onPerformanceUpdate?: (metrics: any) => void;
  showPerformancePanel?: boolean;
}

// 鎬ц兘闈㈡澘缁勪欢
const PerformancePanel: React.FC<{
  chartId: string;
  metrics: any;
  cacheStats: any;
  onClose: () => void;
}> = ({ chartId, metrics, cacheStats, onClose }) => {
  const [analysis, setAnalysis] = useState<any>(null);

  useEffect(() => {
    const analyzer = ChartPerformanceAnalyzer.getInstance();
    const result = analyzer.analyzePerformance(chartId);
    setAnalysis(result);
  }, [chartId, metrics]);

  if (!analysis) return null;

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreIcon = (score: number) => {
    if (score >= 90) return <CheckCircle className="w-4 h-4 text-green-600" />;
    if (score >= 70) return <TrendingUp className="w-4 h-4 text-yellow-600" />;
    return <AlertTriangle className="w-4 h-4 text-red-600" />;
  };

  return (
    <Card className="absolute top-0 right-0 w-80 p-4 bg-white shadow-lg border z-50">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold flex items-center">
          <Activity className="w-4 h-4 mr-2" />
          鎬ц兘鐩戞帶
        </h4>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
          脳
        </Button>
      </div>

      {/* 鎬ц兘璇勫垎 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">鎬ц兘璇勫垎</span>
          <div className="flex items-center">
            {getScoreIcon(analysis.score)}
            <span className={`ml-1 font-semibold ${getScoreColor(analysis.score)}`}>
              {analysis.score}/100
            </span>
          </div>
        </div>
        <Progress value={analysis.score} className="h-2" />
      </div>

      {/* 鎬ц兘鎸囨爣 */}
      <div className="space-y-3 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center text-gray-600">
            <Clock className="w-3 h-3 mr-1" />
            娓叉煋鏃堕棿
          </span>
          <span className="font-mono">
            {analysis.performance.renderTime.toFixed(1)}ms
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center text-gray-600">
            <Database className="w-3 h-3 mr-1" />
            鏁版嵁澶勭悊
          </span>
          <span className="font-mono">
            {analysis.performance.dataProcessingTime.toFixed(1)}ms
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center text-gray-600">
            <Zap className="w-3 h-3 mr-1" />
            鍔ㄧ敾鏃堕棿
          </span>
          <span className="font-mono">
            {analysis.performance.animationTime.toFixed(1)}ms
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center text-gray-600">
            <BarChart3 className="w-3 h-3 mr-1" />
            鎬绘椂闂?
          </span>
          <span className="font-mono font-semibold">
            {analysis.performance.totalTime.toFixed(1)}ms
          </span>
        </div>
      </div>

      {/* 缂撳瓨缁熻 */}
      <div className="mb-4 p-2 bg-gray-50 rounded">
        <div className="text-xs text-gray-600 mb-1">缂撳瓨缁熻</div>
        <div className="flex justify-between text-xs">
          <span>澶у皬: {cacheStats.size}/{cacheStats.maxSize}</span>
          <span>鍛戒腑鐜? {(cacheStats.hitRate || 0).toFixed(1)}%</span>
        </div>
      </div>

      {/* 浼樺寲寤鸿 */}
      {analysis.recommendations.length > 0 && (
        <div>
          <div className="text-xs text-gray-600 mb-2">浼樺寲寤鸿</div>
          <div className="space-y-1">
            {analysis.recommendations.map((rec: string, index: number) => (
              <Badge key={index} variant="outline" className="text-xs">
                {rec}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

// 铏氭嫙鍖栧鍣ㄧ粍浠?
const VirtualizedContainer: React.FC<{
  data: any[];
  config: VirtualizationConfig;
  height: number;
  renderItem: (item: any, index: number) => React.ReactNode;
}> = ({ data, config, height, renderItem }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(height);

  const {
    visibleData,
    visibleRange,
    totalHeight,
    setScrollTop,
  } = useVirtualization(data, config, containerHeight);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, [setScrollTop]);

  useEffect(() => {
    if (containerRef.current) {
      setContainerHeight(containerRef.current.clientHeight);
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="overflow-auto"
      style={{ height }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div
          style={{
            transform: `translateY(${visibleRange.start * config.itemHeight}px)`,
          }}
        >
          {visibleData.map((item, index) =>
            renderItem(item, visibleRange.start + index)
          )}
        </div>
      </div>
    </div>
  );
};

// 涓昏鐨勪紭鍖栧浘琛ㄧ粍浠?
export const OptimizedChart: React.FC<OptimizedChartProps> = ({
  config,
  data = [],
  chartId,
  onPerformanceUpdate,
  showPerformancePanel = false,
  children,
  ...props
}) => {
  const [showPerformance, setShowPerformance] = useState(showPerformancePanel);
  const [isRendering, setIsRendering] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);

  // 浼樺寲閰嶇疆
  const optimizationConfig = config.optimization || {};
  const virtualizationConfig = config.virtualization || {
    enabled: false,
    itemHeight: 50,
    overscan: 5,
    threshold: 100,
  };

  // 鎳掑姞杞?
  const {
    elementRef,
    isVisible,
    isLoaded,
  } = useLazyChart(config.lazyLoadThreshold);

  // 鍥捐〃浼樺寲
  const {
    optimizedData,
    isLoading,
    error,
    debouncedRender,
    throttledUpdate,
    getPerformanceMetrics,
    getCacheStats,
    renderCount,
    lastRenderTime,
  } = useChartOptimization(chartId, data, optimizationConfig);

  // 鍔ㄧ敾浼樺寲
  const {
    isAnimating,
    startAnimation,
    stopAnimation,
  } = useAnimationOptimization(optimizationConfig.enableAnimationOptimization);

  // 鎬ц兘鐩戞帶
  useEffect(() => {
    if (config.enablePerformanceMonitoring && onPerformanceUpdate) {
      const interval = setInterval(() => {
        const metrics = getPerformanceMetrics();
        if (metrics) {
          onPerformanceUpdate({
            ...metrics,
            renderCount,
            lastRenderTime,
            cacheStats: getCacheStats(),
          });
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [
    config.enablePerformanceMonitoring,
    onPerformanceUpdate,
    getPerformanceMetrics,
    getCacheStats,
    renderCount,
    lastRenderTime,
  ]);

  // 娓叉煋鍑芥暟
  const renderChart = useCallback(() => {
    setIsRendering(true);
    
    const render = () => {
      // 瀹為檯鐨勫浘琛ㄦ覆鏌撻€昏緫
      setIsRendering(false);
    };

    if (config.animation !== false) {
      startAnimation(render, optimizationConfig.animationDuration);
    } else {
      render();
    }
  }, [config.animation, startAnimation, optimizationConfig.animationDuration]);

  // 闃叉姈娓叉煋
  useEffect(() => {
    if (isLoaded && optimizedData.length > 0) {
      debouncedRender(renderChart);
    }
  }, [optimizedData, isLoaded, debouncedRender, renderChart]);

  // 濡傛灉鍚敤鎳掑姞杞戒絾鏈姞杞斤紝鏄剧ず鍗犱綅绗?
  if (config.enableLazyLoading && !isLoaded) {
    return (
      <div
        ref={elementRef}
        className="flex items-center justify-center h-64 bg-gray-50 rounded-lg"
      >
        <div className="text-center">
          <BarChart3 className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">鍥捐〃鍔犺浇涓?..</p>
        </div>
      </div>
    );
  }

  // 濡傛灉鍚敤铏氭嫙鍖栦笖鏁版嵁閲忓ぇ
  if (
    virtualizationConfig.enabled &&
    optimizedData.length > virtualizationConfig.threshold
  ) {
    return (
      <div ref={chartRef} className="relative">
        <BaseChart
          {...props}
          config={config}
          data={optimizedData}
          loading={isLoading || isRendering}
          error={error}
        >
          <VirtualizedContainer
            data={optimizedData}
            config={virtualizationConfig}
            height={config.height || 300}
            renderItem={(item, index) => (
              <div key={index} style={{ height: virtualizationConfig.itemHeight }}>
                {/* 铏氭嫙鍖栭」鐩覆鏌?*/}
                {children}
              </div>
            )}
          />
        </BaseChart>

        {/* 鎬ц兘闈㈡澘 */}
        {showPerformance && (
          <PerformancePanel
            chartId={chartId}
            metrics={getPerformanceMetrics()}
            cacheStats={getCacheStats()}
            onClose={() => setShowPerformance(false)}
          />
        )}

        {/* 鎬ц兘鐩戞帶鎸夐挳 */}
        {config.enablePerformanceMonitoring && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 h-8 w-8 p-0"
            onClick={() => setShowPerformance(!showPerformance)}
          >
            <Activity className="w-4 h-4" />
          </Button>
        )}
      </div>
    );
  }

  // 鏍囧噯娓叉煋
  return (
    <div ref={chartRef} className="relative">
      <BaseChart
        {...props}
        config={config}
        data={optimizedData}
        loading={isLoading || isRendering}
        error={error}
      >
        {children}
      </BaseChart>

      {/* 鎬ц兘闈㈡澘 */}
      {showPerformance && (
        <PerformancePanel
          chartId={chartId}
          metrics={getPerformanceMetrics()}
          cacheStats={getCacheStats()}
          onClose={() => setShowPerformance(false)}
        />
      )}

      {/* 鎬ц兘鐩戞帶鎸夐挳 */}
      {config.enablePerformanceMonitoring && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-8 w-8 p-0"
          onClick={() => setShowPerformance(!showPerformance)}
        >
          <Activity className="w-4 h-4" />
        </Button>
      )}

      {/* 娓叉煋鐘舵€佹寚绀哄櫒 */}
      {isRendering && (
        <div className="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center">
          <div className="flex items-center text-sm text-gray-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
            娓叉煋涓?..
          </div>
        </div>
      )}

      {/* 鍔ㄧ敾鐘舵€佹寚绀哄櫒 */}
      {isAnimating && (
        <div className="absolute top-2 left-2">
          <Badge variant="outline" className="text-xs">
            <Zap className="w-3 h-3 mr-1" />
            鍔ㄧ敾涓?
          </Badge>
        </div>
      )}
    </div>
  );
};

export default OptimizedChart;