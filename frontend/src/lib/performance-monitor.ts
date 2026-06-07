// @ts-nocheck
/**
 * 鍓嶇鎬ц兘鐩戞帶宸ュ叿
 * 
 * 鎻愪緵缁勪欢娓叉煋鎬ц兘銆丄PI璇锋眰鎬ц兘銆佸唴瀛樹娇鐢ㄧ瓑鐩戞帶鍔熻兘
 */

import React from 'react';

// 鎬ц兘鎸囨爣鎺ュ彛
interface PerformanceMetrics {
  renderTime: number;
  apiResponseTime: number;
  memoryUsage: number;
  cacheHitRate: number;
  errorRate: number;
  timestamp: number;
}

// 缁勪欢鎬ц兘鎸囨爣
interface ComponentMetrics {
  componentName: string;
  renderCount: number;
  averageRenderTime: number;
  maxRenderTime: number;
  minRenderTime: number;
  lastRenderTime: number;
}

// API鎬ц兘鎸囨爣
interface ApiMetrics {
  endpoint: string;
  requestCount: number;
  averageResponseTime: number;
  maxResponseTime: number;
  minResponseTime: number;
  errorCount: number;
  successRate: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private componentMetrics: Map<string, ComponentMetrics> = new Map();
  private apiMetrics: Map<string, ApiMetrics> = new Map();
  private observers: PerformanceObserver[] = [];
  private isEnabled: boolean = true;
  private maxMetricsCount: number = 1000;

  constructor() {
    this.initializeObservers();
    this.startMemoryMonitoring();
  }

  // 鍒濆鍖栨€ц兘瑙傚療鍣?
  private initializeObservers() {
    if (typeof window === 'undefined') return;

    try {
      // 瑙傚療瀵艰埅鎬ц兘
      if ('PerformanceObserver' in window) {
        const navigationObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.entryType === 'navigation') {
              this.recordNavigationMetrics(entry as PerformanceNavigationTiming);
            }
          });
        });
        navigationObserver.observe({ entryTypes: ['navigation'] });
        this.observers.push(navigationObserver);

        // 瑙傚療璧勬簮鍔犺浇鎬ц兘
        const resourceObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.entryType === 'resource') {
              this.recordResourceMetrics(entry as PerformanceResourceTiming);
            }
          });
        });
        resourceObserver.observe({ entryTypes: ['resource'] });
        this.observers.push(resourceObserver);

        // 瑙傚療闀夸换鍔?
        const longTaskObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.entryType === 'longtask') {
              this.recordLongTask(entry);
            }
          });
        });
        longTaskObserver.observe({ entryTypes: ['longtask'] });
        this.observers.push(longTaskObserver);
      }
    } catch (error) {
      console.warn('Performance observer initialization failed:', error);
    }
  }

  // 璁板綍瀵艰埅鎬ц兘鎸囨爣
  private recordNavigationMetrics(entry: PerformanceNavigationTiming) {
    const metrics: PerformanceMetrics = {
      renderTime: entry.loadEventEnd - entry.loadEventStart,
      apiResponseTime: entry.responseEnd - entry.requestStart,
      memoryUsage: this.getMemoryUsage(),
      cacheHitRate: 0, // 灏嗗湪鍏朵粬鍦版柟璁＄畻
      errorRate: 0, // 灏嗗湪鍏朵粬鍦版柟璁＄畻
      timestamp: Date.now(),
    };

    this.addMetrics(metrics);
  }

  // 璁板綍璧勬簮鍔犺浇鎬ц兘鎸囨爣
  private recordResourceMetrics(entry: PerformanceResourceTiming) {
    if (entry.name.includes('/api/')) {
      const endpoint = this.extractEndpoint(entry.name);
      const responseTime = entry.responseEnd - entry.requestStart;
      this.recordApiMetrics(endpoint, responseTime, entry.responseStatus === 200);
    }
  }

  // 璁板綍闀夸换鍔?
  private recordLongTask(entry: PerformanceEntry) {
    console.warn(`Long task detected: ${entry.duration}ms at ${entry.startTime}`);
  }

  // 鎻愬彇API绔偣
  private extractEndpoint(url: string): string {
    try {
      const urlObj = new URL(url);
      return urlObj.pathname;
    } catch {
      return url;
    }
  }

  // 寮€濮嬪唴瀛樼洃鎺?
  private startMemoryMonitoring() {
    if (typeof window === 'undefined') return;

    setInterval(() => {
      const memoryUsage = this.getMemoryUsage();
      if (memoryUsage > 0) {
        this.addMetrics({
          renderTime: 0,
          apiResponseTime: 0,
          memoryUsage,
          cacheHitRate: 0,
          errorRate: 0,
          timestamp: Date.now(),
        });
      }
    }, 30000); // 姣?0绉掕褰曚竴娆″唴瀛樹娇鐢?
  }

  // 鑾峰彇鍐呭瓨浣跨敤鎯呭喌
  private getMemoryUsage(): number {
    if (typeof window === 'undefined') return 0;
    
    try {
      // @ts-ignore
      if (performance.memory) {
        // @ts-ignore
        return performance.memory.usedJSHeapSize / 1024 / 1024; // MB
      }
    } catch (error) {
      console.warn('Memory usage monitoring not supported');
    }
    return 0;
  }

  // 娣诲姞鎬ц兘鎸囨爣
  private addMetrics(metrics: PerformanceMetrics) {
    if (!this.isEnabled) return;

    this.metrics.push(metrics);
    
    // 闄愬埗鎸囨爣鏁伴噺
    if (this.metrics.length > this.maxMetricsCount) {
      this.metrics = this.metrics.slice(-this.maxMetricsCount);
    }
  }

  // 璁板綍缁勪欢娓叉煋鎬ц兘
  recordComponentRender(componentName: string, renderTime: number) {
    if (!this.isEnabled) return;

    const existing = this.componentMetrics.get(componentName);
    if (existing) {
      existing.renderCount++;
      existing.averageRenderTime = 
        (existing.averageRenderTime * (existing.renderCount - 1) + renderTime) / existing.renderCount;
      existing.maxRenderTime = Math.max(existing.maxRenderTime, renderTime);
      existing.minRenderTime = Math.min(existing.minRenderTime, renderTime);
      existing.lastRenderTime = renderTime;
    } else {
      this.componentMetrics.set(componentName, {
        componentName,
        renderCount: 1,
        averageRenderTime: renderTime,
        maxRenderTime: renderTime,
        minRenderTime: renderTime,
        lastRenderTime: renderTime,
      });
    }
  }

  // 璁板綍API鎬ц兘
  recordApiMetrics(endpoint: string, responseTime: number, success: boolean) {
    if (!this.isEnabled) return;

    const existing = this.apiMetrics.get(endpoint);
    if (existing) {
      existing.requestCount++;
      existing.averageResponseTime = 
        (existing.averageResponseTime * (existing.requestCount - 1) + responseTime) / existing.requestCount;
      existing.maxResponseTime = Math.max(existing.maxResponseTime, responseTime);
      existing.minResponseTime = Math.min(existing.minResponseTime, responseTime);
      
      if (!success) {
        existing.errorCount++;
      }
      existing.successRate = (existing.requestCount - existing.errorCount) / existing.requestCount;
    } else {
      this.apiMetrics.set(endpoint, {
        endpoint,
        requestCount: 1,
        averageResponseTime: responseTime,
        maxResponseTime: responseTime,
        minResponseTime: responseTime,
        errorCount: success ? 0 : 1,
        successRate: success ? 1 : 0,
      });
    }
  }

  // 鑾峰彇鎬ц兘鎶ュ憡
  getPerformanceReport() {
    const recentMetrics = this.metrics.slice(-100); // 鏈€杩?00鏉¤褰?
    
    const avgRenderTime = recentMetrics.reduce((sum, m) => sum + m.renderTime, 0) / recentMetrics.length || 0;
    const avgApiResponseTime = recentMetrics.reduce((sum, m) => sum + m.apiResponseTime, 0) / recentMetrics.length || 0;
    const avgMemoryUsage = recentMetrics.reduce((sum, m) => sum + m.memoryUsage, 0) / recentMetrics.length || 0;

    return {
      summary: {
        averageRenderTime: avgRenderTime,
        averageApiResponseTime: avgApiResponseTime,
        averageMemoryUsage: avgMemoryUsage,
        totalMetrics: this.metrics.length,
      },
      components: Array.from(this.componentMetrics.values())
        .sort((a, b) => b.averageRenderTime - a.averageRenderTime),
      apis: Array.from(this.apiMetrics.values())
        .sort((a, b) => b.averageResponseTime - a.averageResponseTime),
      recentMetrics: recentMetrics.slice(-20), // 鏈€杩?0鏉¤褰?
    };
  }

  // 鑾峰彇鎱㈢粍浠?
  getSlowComponents(threshold: number = 16): ComponentMetrics[] {
    return Array.from(this.componentMetrics.values())
      .filter(component => component.averageRenderTime > threshold)
      .sort((a, b) => b.averageRenderTime - a.averageRenderTime);
  }

  // 鑾峰彇鎱PI
  getSlowApis(threshold: number = 1000): ApiMetrics[] {
    return Array.from(this.apiMetrics.values())
      .filter(api => api.averageResponseTime > threshold)
      .sort((a, b) => b.averageResponseTime - a.averageResponseTime);
  }

  // 娓呴櫎鎸囨爣
  clearMetrics() {
    this.metrics = [];
    this.componentMetrics.clear();
    this.apiMetrics.clear();
  }

  // 鍚敤/绂佺敤鐩戞帶
  setEnabled(enabled: boolean) {
    this.isEnabled = enabled;
  }

  // 閿€姣佺洃鎺у櫒
  destroy() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.clearMetrics();
  }

  // 瀵煎嚭鎬ц兘鏁版嵁
  exportMetrics() {
    const report = this.getPerformanceReport();
    const blob = new Blob([JSON.stringify(report, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-report-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// 鍏ㄥ眬鎬ц兘鐩戞帶瀹炰緥
export const performanceMonitor = new PerformanceMonitor();

// React Hook for component performance monitoring
export const usePerformanceMonitor = (componentName: string) => {
  const startTime = React.useRef<number>(0);

  React.useEffect(() => {
    startTime.current = performance.now();
  });

  React.useLayoutEffect(() => {
    const renderTime = performance.now() - startTime.current;
    performanceMonitor.recordComponentRender(componentName, renderTime);
  });

  return {
    recordRender: (customRenderTime?: number) => {
      const renderTime = customRenderTime || (performance.now() - startTime.current);
      performanceMonitor.recordComponentRender(componentName, renderTime);
    },
    getComponentMetrics: () => performanceMonitor.getPerformanceReport().components
      .find(c => c.componentName === componentName),
  };
};

// API鎬ц兘鐩戞帶瑁呴グ鍣?
export const withApiPerformanceMonitor = <T extends (...args: any[]) => Promise<any>>(
  apiFunction: T,
  endpoint: string
): T => {
  return (async (...args: any[]) => {
    const startTime = performance.now();
    try {
      const result = await apiFunction(...args);
      const responseTime = performance.now() - startTime;
      performanceMonitor.recordApiMetrics(endpoint, responseTime, true);
      return result;
    } catch (error) {
      const responseTime = performance.now() - startTime;
      performanceMonitor.recordApiMetrics(endpoint, responseTime, false);
      throw error;
    }
  }) as T;
};

// 鎬ц兘璀﹀憡闃堝€?
export const PERFORMANCE_THRESHOLDS = {
  RENDER_TIME: 16, // 16ms (60fps)
  API_RESPONSE_TIME: 1000, // 1绉?
  MEMORY_USAGE: 100, // 100MB
  LONG_TASK: 50, // 50ms
};

// 鎬ц兘浼樺寲寤鸿
export const getPerformanceRecommendations = () => {
  const report = performanceMonitor.getPerformanceReport();
  const recommendations: string[] = [];

  // 妫€鏌ユ參缁勪欢
  const slowComponents = performanceMonitor.getSlowComponents();
  if (slowComponents.length > 0) {
    recommendations.push(
      `发现 ${slowComponents.length} 个渲染较慢的组件，建议使用 React.memo 或优化渲染逻辑`
    );
  }

  // 妫€鏌ユ參API
  const slowApis = performanceMonitor.getSlowApis();
  if (slowApis.length > 0) {
    recommendations.push(
      `发现 ${slowApis.length} 个响应较慢的 API，建议优化后端性能或增加缓存`
    );
  }

  // 妫€鏌ュ唴瀛樹娇鐢?
  if (report.summary.averageMemoryUsage > PERFORMANCE_THRESHOLDS.MEMORY_USAGE) {
    recommendations.push(
      `内存使用较高 (${report.summary.averageMemoryUsage.toFixed(2)}MB)，建议检查内存泄漏`
    );
  }

  return recommendations;
};

export default performanceMonitor;
