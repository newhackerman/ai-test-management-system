// @ts-nocheck
/**
 * 鍥捐〃娓叉煋浼樺寲宸ュ叿
 * 
 * 瀹炵幇鍥捐〃铏氭嫙鍖栥€佹寜闇€娓叉煋銆佹€ц兘鐩戞帶鍜岀紦瀛樻満鍒?
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { debounce, throttle } from 'lodash-es';

// 鎬ц兘鐩戞帶鎺ュ彛
export interface ChartPerformanceMetrics {
  renderTime: number;
  dataProcessingTime: number;
  animationTime: number;
  memoryUsage: number;
  fps: number;
  lastRenderTimestamp: number;
}

// 铏氭嫙鍖栭厤缃?
export interface VirtualizationConfig {
  enabled: boolean;
  itemHeight: number;
  overscan: number;
  threshold: number; // 鏁版嵁閲忛槇鍊硷紝瓒呰繃姝ゅ€煎惎鐢ㄨ櫄鎷熷寲
}

// 娓叉煋浼樺寲閰嶇疆
export interface RenderOptimizationConfig {
  enableVirtualization: boolean;
  enableLazyLoading: boolean;
  enableDataSampling: boolean;
  enableAnimationOptimization: boolean;
  enableMemoryOptimization: boolean;
  maxDataPoints: number;
  samplingRate: number;
  animationDuration: number;
  debounceDelay: number;
  throttleDelay: number;
}

// 榛樿浼樺寲閰嶇疆
const DEFAULT_OPTIMIZATION_CONFIG: RenderOptimizationConfig = {
  enableVirtualization: true,
  enableLazyLoading: true,
  enableDataSampling: true,
  enableAnimationOptimization: true,
  enableMemoryOptimization: true,
  maxDataPoints: 1000,
  samplingRate: 0.1,
  animationDuration: 300,
  debounceDelay: 300,
  throttleDelay: 100,
};

// 鍥捐〃缂撳瓨绠＄悊鍣?
class ChartCacheManager {
  private cache = new Map<string, any>();
  private maxSize = 100;
  private accessOrder = new Map<string, number>();

  set(key: string, value: any): void {
    // LRU娣樻卑绛栫暐
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const oldestKey = this.getOldestKey();
      if (oldestKey) {
        this.cache.delete(oldestKey);
        this.accessOrder.delete(oldestKey);
      }
    }

    this.cache.set(key, value);
    this.accessOrder.set(key, Date.now());
  }

  get(key: string): any {
    const value = this.cache.get(key);
    if (value !== undefined) {
      this.accessOrder.set(key, Date.now());
    }
    return value;
  }

  has(key: string): boolean {
    return this.cache.has(key);
  }

  delete(key: string): boolean {
    this.accessOrder.delete(key);
    return this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
    this.accessOrder.clear();
  }

  private getOldestKey(): string | undefined {
    let oldestKey: string | undefined;
    let oldestTime = Infinity;

    for (const [key, time] of this.accessOrder) {
      if (time < oldestTime) {
        oldestTime = time;
        oldestKey = key;
      }
    }

    return oldestKey;
  }

  getStats() {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hitRate: 0, // 闇€瑕佸湪浣跨敤鏃剁粺璁?
    };
  }
}

// 鍏ㄥ眬鍥捐〃缂撳瓨瀹炰緥
const chartCache = new ChartCacheManager();

// 鎬ц兘鐩戞帶鍣?
class ChartPerformanceMonitor {
  private metrics: Map<string, ChartPerformanceMetrics> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();

  startMonitoring(chartId: string): void {
    if (typeof window === 'undefined' || !window.performance) return;

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      for (const entry of entries) {
        if (entry.name.includes(chartId)) {
          this.updateMetrics(chartId, entry);
        }
      }
    });

    observer.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
    this.observers.set(chartId, observer);
  }

  stopMonitoring(chartId: string): void {
    const observer = this.observers.get(chartId);
    if (observer) {
      observer.disconnect();
      this.observers.delete(chartId);
    }
  }

  private updateMetrics(chartId: string, entry: PerformanceEntry): void {
    const current = this.metrics.get(chartId) || {
      renderTime: 0,
      dataProcessingTime: 0,
      animationTime: 0,
      memoryUsage: 0,
      fps: 0,
      lastRenderTimestamp: 0,
    };

    // 鏇存柊鎸囨爣
    if (entry.name.includes('render')) {
      current.renderTime = entry.duration;
    } else if (entry.name.includes('data')) {
      current.dataProcessingTime = entry.duration;
    } else if (entry.name.includes('animation')) {
      current.animationTime = entry.duration;
    }

    current.lastRenderTimestamp = Date.now();
    this.metrics.set(chartId, current);
  }

  getMetrics(chartId: string): ChartPerformanceMetrics | undefined {
    return this.metrics.get(chartId);
  }

  getAllMetrics(): Map<string, ChartPerformanceMetrics> {
    return new Map(this.metrics);
  }

  clearMetrics(chartId?: string): void {
    if (chartId) {
      this.metrics.delete(chartId);
    } else {
      this.metrics.clear();
    }
  }
}

// 鍏ㄥ眬鎬ц兘鐩戞帶瀹炰緥
const performanceMonitor = new ChartPerformanceMonitor();

// 鏁版嵁閲囨牱宸ュ叿
export const sampleData = (data: any[], maxPoints: number, strategy: 'uniform' | 'adaptive' = 'adaptive'): any[] => {
  if (data.length <= maxPoints) return data;

  if (strategy === 'uniform') {
    // 鍧囧寑閲囨牱
    const step = Math.ceil(data.length / maxPoints);
    return data.filter((_, index) => index % step === 0);
  } else {
    // 鑷€傚簲閲囨牱 - 淇濈暀閲嶈鏁版嵁鐐?
    const sampled: any[] = [];
    const step = data.length / maxPoints;
    
    for (let i = 0; i < maxPoints; i++) {
      const index = Math.floor(i * step);
      if (index < data.length) {
        sampled.push(data[index]);
      }
    }
    
    return sampled;
  }
};

// 鏁版嵁鍒嗛〉宸ュ叿
export const paginateData = (data: any[], page: number, pageSize: number): any[] => {
  const start = page * pageSize;
  const end = start + pageSize;
  return data.slice(start, end);
};

// 铏氭嫙鍖朒ook
export const useVirtualization = (
  data: any[],
  config: VirtualizationConfig,
  containerHeight: number
) => {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 0 });
  const [scrollTop, setScrollTop] = useState(0);

  const visibleCount = Math.ceil(containerHeight / config.itemHeight);
  const totalHeight = data.length * config.itemHeight;

  const updateVisibleRange = useCallback(
    throttle((scrollTop: number) => {
      const start = Math.floor(scrollTop / config.itemHeight);
      const end = Math.min(
        start + visibleCount + config.overscan,
        data.length
      );
      
      setVisibleRange({
        start: Math.max(0, start - config.overscan),
        end,
      });
    }, 16), // 60fps
    [config.itemHeight, config.overscan, visibleCount, data.length]
  );

  useEffect(() => {
    updateVisibleRange(scrollTop);
  }, [scrollTop, updateVisibleRange]);

  const visibleData = useMemo(() => {
    return data.slice(visibleRange.start, visibleRange.end);
  }, [data, visibleRange]);

  return {
    visibleData,
    visibleRange,
    totalHeight,
    setScrollTop,
    updateVisibleRange,
  };
};

// 鍥捐〃娓叉煋浼樺寲Hook
export const useChartOptimization = (
  chartId: string,
  data: any[],
  config: Partial<RenderOptimizationConfig> = {}
) => {
  const optimizationConfig = { ...DEFAULT_OPTIMIZATION_CONFIG, ...config };
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const renderCountRef = useRef(0);
  const lastRenderTimeRef = useRef(0);

  // 鏁版嵁澶勭悊浼樺寲
  const optimizedData = useMemo(() => {
    const startTime = performance.now();
    performance.mark(`${chartId}-data-start`);

    let processedData = data;

    // 鏁版嵁閲囨牱
    if (optimizationConfig.enableDataSampling && data.length > optimizationConfig.maxDataPoints) {
      processedData = sampleData(data, optimizationConfig.maxDataPoints);
    }

    // 缂撳瓨澶勭悊缁撴灉
    const cacheKey = `${chartId}-${data.length}-${JSON.stringify(optimizationConfig)}`;
    if (chartCache.has(cacheKey)) {
      return chartCache.get(cacheKey);
    }

    chartCache.set(cacheKey, processedData);

    performance.mark(`${chartId}-data-end`);
    performance.measure(`${chartId}-data-processing`, `${chartId}-data-start`, `${chartId}-data-end`);

    const endTime = performance.now();
    console.debug(`Data processing time for ${chartId}: ${endTime - startTime}ms`);

    return processedData;
  }, [data, optimizationConfig, chartId]);

  // 闃叉姈娓叉煋
  const debouncedRender = useCallback(
    debounce((renderFn: () => void) => {
      const startTime = performance.now();
      performance.mark(`${chartId}-render-start`);

      renderFn();
      renderCountRef.current++;
      lastRenderTimeRef.current = Date.now();

      performance.mark(`${chartId}-render-end`);
      performance.measure(`${chartId}-render`, `${chartId}-render-start`, `${chartId}-render-end`);

      const endTime = performance.now();
      console.debug(`Render time for ${chartId}: ${endTime - startTime}ms`);
    }, optimizationConfig.debounceDelay),
    [chartId, optimizationConfig.debounceDelay]
  );

  // 鑺傛祦鏇存柊
  const throttledUpdate = useCallback(
    throttle((updateFn: () => void) => {
      updateFn();
    }, optimizationConfig.throttleDelay),
    [optimizationConfig.throttleDelay]
  );

  // 鎬ц兘鐩戞帶
  useEffect(() => {
    performanceMonitor.startMonitoring(chartId);
    return () => {
      performanceMonitor.stopMonitoring(chartId);
    };
  }, [chartId]);

  // 鍐呭瓨浼樺寲
  useEffect(() => {
    if (optimizationConfig.enableMemoryOptimization) {
      const cleanup = () => {
        // 娓呯悊鏃х殑缂撳瓨鏉＄洰
        if (renderCountRef.current > 100) {
          chartCache.clear();
          renderCountRef.current = 0;
        }
      };

      const interval = setInterval(cleanup, 60000); // 姣忓垎閽熸竻鐞嗕竴娆?
      return () => clearInterval(interval);
    }
  }, [optimizationConfig.enableMemoryOptimization]);

  // 鑾峰彇鎬ц兘鎸囨爣
  const getPerformanceMetrics = useCallback(() => {
    return performanceMonitor.getMetrics(chartId);
  }, [chartId]);

  // 鑾峰彇缂撳瓨缁熻
  const getCacheStats = useCallback(() => {
    return chartCache.getStats();
  }, []);

  return {
    optimizedData,
    isLoading,
    error,
    debouncedRender,
    throttledUpdate,
    getPerformanceMetrics,
    getCacheStats,
    renderCount: renderCountRef.current,
    lastRenderTime: lastRenderTimeRef.current,
  };
};

// 鎳掑姞杞紿ook
export const useLazyChart = (threshold: number = 100) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const elementRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          // 寤惰繜鍔犺浇浠ラ伩鍏嶅悓鏃舵覆鏌撳涓浘琛?
          setTimeout(() => setIsLoaded(true), Math.random() * 200);
        }
      },
      {
        rootMargin: `${threshold}px`,
      }
    );

    observer.observe(element);

    return () => {
      observer.unobserve(element);
    };
  }, [threshold]);

  return {
    elementRef,
    isVisible,
    isLoaded,
  };
};

// 鍔ㄧ敾浼樺寲Hook
export const useAnimationOptimization = (enabled: boolean = true) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const animationFrameRef = useRef<number>();

  const startAnimation = useCallback((animationFn: () => void, duration: number = 300) => {
    if (!enabled) {
      animationFn();
      return;
    }

    setIsAnimating(true);
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      animationFn();

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [enabled]);

  const stopAnimation = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      setIsAnimating(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return {
    isAnimating,
    startAnimation,
    stopAnimation,
  };
};

// 鍥捐〃鎬ц兘鍒嗘瀽鍣?
export class ChartPerformanceAnalyzer {
  private static instance: ChartPerformanceAnalyzer;
  private reports: Map<string, any> = new Map();

  static getInstance(): ChartPerformanceAnalyzer {
    if (!ChartPerformanceAnalyzer.instance) {
      ChartPerformanceAnalyzer.instance = new ChartPerformanceAnalyzer();
    }
    return ChartPerformanceAnalyzer.instance;
  }

  analyzePerformance(chartId: string): any {
    const metrics = performanceMonitor.getMetrics(chartId);
    if (!metrics) return null;

    const analysis = {
      chartId,
      timestamp: Date.now(),
      performance: {
        renderTime: metrics.renderTime,
        dataProcessingTime: metrics.dataProcessingTime,
        animationTime: metrics.animationTime,
        totalTime: metrics.renderTime + metrics.dataProcessingTime + metrics.animationTime,
      },
      recommendations: this.generateRecommendations(metrics),
      score: this.calculatePerformanceScore(metrics),
    };

    this.reports.set(chartId, analysis);
    return analysis;
  }

  private generateRecommendations(metrics: ChartPerformanceMetrics): string[] {
    const recommendations: string[] = [];

    if (metrics.renderTime > 100) {
      recommendations.push('建议启用虚拟化以减少渲染时间');
    }

    if (metrics.dataProcessingTime > 50) {
      recommendations.push('建议启用数据采样以减少数据处理时间');
    }

    if (metrics.animationTime > 200) {
      recommendations.push('建议减少动画持续时间或禁用动画');
    }

    if (metrics.memoryUsage > 50 * 1024 * 1024) { // 50MB
      recommendations.push('建议启用内存优化以减少内存使用');
    }

    return recommendations;
  }

  private calculatePerformanceScore(metrics: ChartPerformanceMetrics): number {
    let score = 100;

    // 娓叉煋鏃堕棿璇勫垎
    if (metrics.renderTime > 100) score -= 20;
    else if (metrics.renderTime > 50) score -= 10;

    // 鏁版嵁澶勭悊鏃堕棿璇勫垎
    if (metrics.dataProcessingTime > 50) score -= 15;
    else if (metrics.dataProcessingTime > 25) score -= 8;

    // 鍔ㄧ敾鏃堕棿璇勫垎
    if (metrics.animationTime > 200) score -= 10;
    else if (metrics.animationTime > 100) score -= 5;

    // 鍐呭瓨浣跨敤璇勫垎
    if (metrics.memoryUsage > 50 * 1024 * 1024) score -= 15;
    else if (metrics.memoryUsage > 25 * 1024 * 1024) score -= 8;

    return Math.max(0, score);
  }

  getReport(chartId: string): any {
    return this.reports.get(chartId);
  }

  getAllReports(): Map<string, any> {
    return new Map(this.reports);
  }

  clearReports(): void {
    this.reports.clear();
  }
}

// 瀵煎嚭宸ュ叿鍑芥暟
export const chartOptimizationUtils = {
  sampleData,
  paginateData,
  chartCache,
  performanceMonitor,
  analyzer: ChartPerformanceAnalyzer.getInstance(),
};

export default chartOptimizationUtils;
