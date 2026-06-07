// @ts-nocheck
/**
 * 鍓嶇璧勬簮浼樺寲宸ュ叿
 * 
 * 瀹炵幇浠ｇ爜鍒嗗壊銆佹噿鍔犺浇銆佸浘鐗囦紭鍖栥€丆DN缂撳瓨鍜屾€ц兘鐩戞帶
 */

import { lazy, ComponentType, LazyExoticComponent } from 'react';
import { debounce, throttle } from 'lodash-es';

// 鎬ц兘鐩戞帶鎺ュ彛
export interface PerformanceMetrics {
  loadTime: number;
  renderTime: number;
  memoryUsage: number;
  bundleSize: number;
  cacheHitRate: number;
  networkLatency: number;
  timestamp: number;
}

// 璧勬簮浼樺寲閰嶇疆
export interface ResourceOptimizationConfig {
  enableCodeSplitting: boolean;
  enableLazyLoading: boolean;
  enableImageOptimization: boolean;
  enableCDN: boolean;
  enableServiceWorker: boolean;
  enablePreloading: boolean;
  enableBundleAnalysis: boolean;
  chunkSizeLimit: number;
  imageQuality: number;
  cacheStrategy: 'aggressive' | 'moderate' | 'conservative';
}

// 榛樿閰嶇疆
const DEFAULT_CONFIG: ResourceOptimizationConfig = {
  enableCodeSplitting: true,
  enableLazyLoading: true,
  enableImageOptimization: true,
  enableCDN: true,
  enableServiceWorker: true,
  enablePreloading: true,
  enableBundleAnalysis: false,
  chunkSizeLimit: 244 * 1024, // 244KB
  imageQuality: 80,
  cacheStrategy: 'moderate',
};

// 浠ｇ爜鍒嗗壊绠＄悊鍣?
class CodeSplittingManager {
  private loadedChunks = new Set<string>();
  private loadingChunks = new Map<string, Promise<any>>();
  private chunkMetrics = new Map<string, PerformanceMetrics>();

  // 鍔ㄦ€佸鍏ョ粍浠?
  loadComponent<T extends ComponentType<any>>(
    importFn: () => Promise<{ default: T }>,
    chunkName?: string
  ): LazyExoticComponent<T> {
    return lazy(async () => {
      const startTime = performance.now();
      
      try {
        // 妫€鏌ユ槸鍚﹀凡缁忓湪鍔犺浇涓?
        if (chunkName && this.loadingChunks.has(chunkName)) {
          return await this.loadingChunks.get(chunkName)!;
        }

        // 寮€濮嬪姞杞?
        const loadPromise = importFn();
        if (chunkName) {
          this.loadingChunks.set(chunkName, loadPromise);
        }

        const module = await loadPromise;
        const loadTime = performance.now() - startTime;

        // 璁板綍鍔犺浇鎸囨爣
        if (chunkName) {
          this.loadedChunks.add(chunkName);
          this.loadingChunks.delete(chunkName);
          this.recordChunkMetrics(chunkName, loadTime);
        }

        return module;
      } catch (error) {
        if (chunkName) {
          this.loadingChunks.delete(chunkName);
        }
        throw error;
      }
    });
  }

  // 棰勫姞杞界粍浠?
  async preloadComponent(
    importFn: () => Promise<any>,
    chunkName?: string
  ): Promise<void> {
    if (chunkName && this.loadedChunks.has(chunkName)) {
      return; // 宸茬粡鍔犺浇
    }

    try {
      await importFn();
      if (chunkName) {
        this.loadedChunks.add(chunkName);
      }
    } catch (error) {
      console.warn(`Failed to preload chunk ${chunkName}:`, error);
    }
  }

  // 鑾峰彇鍔犺浇鐘舵€?
  getLoadingStatus(): {
    loaded: string[];
    loading: string[];
    metrics: Record<string, PerformanceMetrics>;
  } {
    return {
      loaded: Array.from(this.loadedChunks),
      loading: Array.from(this.loadingChunks.keys()),
      metrics: Object.fromEntries(this.chunkMetrics),
    };
  }

  private recordChunkMetrics(chunkName: string, loadTime: number): void {
    this.chunkMetrics.set(chunkName, {
      loadTime,
      renderTime: 0,
      memoryUsage: this.getMemoryUsage(),
      bundleSize: 0, // 闇€瑕佷粠缃戠粶璇锋眰涓幏鍙?
      cacheHitRate: 0,
      networkLatency: loadTime,
      timestamp: Date.now(),
    });
  }

  private getMemoryUsage(): number {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return 0;
  }
}

// 鍥剧墖浼樺寲绠＄悊鍣?
class ImageOptimizationManager {
  private imageCache = new Map<string, HTMLImageElement>();
  private loadingImages = new Map<string, Promise<HTMLImageElement>>();
  private observer?: IntersectionObserver;

  constructor(private config: ResourceOptimizationConfig) {
    this.initLazyLoading();
  }

  // 鍒濆鍖栨噿鍔犺浇
  private initLazyLoading(): void {
    if (!this.config.enableLazyLoading || typeof window === 'undefined') {
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement;
            this.loadImage(img);
            this.observer?.unobserve(img);
          }
        });
      },
      {
        rootMargin: '50px',
        threshold: 0.1,
      }
    );
  }

  // 浼樺寲鍥剧墖URL
  optimizeImageUrl(
    originalUrl: string,
    options: {
      width?: number;
      height?: number;
      quality?: number;
      format?: 'webp' | 'avif' | 'jpeg' | 'png';
    } = {}
  ): string {
    if (!this.config.enableImageOptimization) {
      return originalUrl;
    }

    const {
      width,
      height,
      quality = this.config.imageQuality,
      format = 'webp',
    } = options;

    // 濡傛灉鍚敤CDN锛屾瀯寤轰紭鍖朥RL
    if (this.config.enableCDN) {
      const params = new URLSearchParams();
      
      if (width) params.set('w', width.toString());
      if (height) params.set('h', height.toString());
      if (quality) params.set('q', quality.toString());
      if (format) params.set('f', format);

      return `${originalUrl}?${params.toString()}`;
    }

    return originalUrl;
  }

  // 鎳掑姞杞藉浘鐗?
  lazyLoadImage(img: HTMLImageElement): void {
    if (!this.observer) {
      this.loadImage(img);
      return;
    }

    this.observer.observe(img);
  }

  // 鍔犺浇鍥剧墖
  private async loadImage(img: HTMLImageElement): Promise<void> {
    const src = img.dataset.src || img.src;
    if (!src) return;

    try {
      // 妫€鏌ョ紦瀛?
      if (this.imageCache.has(src)) {
        const cachedImg = this.imageCache.get(src)!;
        img.src = cachedImg.src;
        img.classList.remove('loading');
        img.classList.add('loaded');
        return;
      }

      // 妫€鏌ユ槸鍚︽鍦ㄥ姞杞?
      if (this.loadingImages.has(src)) {
        await this.loadingImages.get(src);
        return;
      }

      // 寮€濮嬪姞杞?
      img.classList.add('loading');
      
      const loadPromise = this.createImageLoadPromise(src);
      this.loadingImages.set(src, loadPromise);

      const loadedImg = await loadPromise;
      
      // 缂撳瓨鍥剧墖
      this.imageCache.set(src, loadedImg);
      this.loadingImages.delete(src);

      // 鏇存柊DOM
      img.src = loadedImg.src;
      img.classList.remove('loading');
      img.classList.add('loaded');

    } catch (error) {
      console.error('Failed to load image:', src, error);
      img.classList.remove('loading');
      img.classList.add('error');
    }
  }

  private createImageLoadPromise(src: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  // 棰勫姞杞藉浘鐗?
  async preloadImages(urls: string[]): Promise<void> {
    const promises = urls.map(url => this.createImageLoadPromise(url));
    
    try {
      const images = await Promise.all(promises);
      images.forEach((img, index) => {
        this.imageCache.set(urls[index], img);
      });
    } catch (error) {
      console.warn('Some images failed to preload:', error);
    }
  }

  // 娓呯悊缂撳瓨
  clearCache(): void {
    this.imageCache.clear();
    this.loadingImages.clear();
  }

  // 鑾峰彇缂撳瓨缁熻
  getCacheStats(): {
    cached: number;
    loading: number;
    hitRate: number;
  } {
    return {
      cached: this.imageCache.size,
      loading: this.loadingImages.size,
      hitRate: 0, // 闇€瑕佸疄闄呯粺璁?
    };
  }
}

// CDN绠＄悊鍣?
class CDNManager {
  private cdnHosts: string[] = [];
  private currentHostIndex = 0;
  private hostMetrics = new Map<string, { latency: number; errors: number }>();

  constructor(hosts: string[] = []) {
    this.cdnHosts = hosts;
  }

  // 鑾峰彇CDN URL
  getCDNUrl(path: string): string {
    if (this.cdnHosts.length === 0) {
      return path;
    }

    const host = this.getBestHost();
    return `${host}${path.startsWith('/') ? '' : '/'}${path}`;
  }

  // 鑾峰彇鏈€浣矯DN涓绘満
  private getBestHost(): string {
    if (this.cdnHosts.length === 1) {
      return this.cdnHosts[0];
    }

    // 鍩轰簬寤惰繜鍜岄敊璇巼閫夋嫨鏈€浣充富鏈?
    let bestHost = this.cdnHosts[0];
    let bestScore = Infinity;

    for (const host of this.cdnHosts) {
      const metrics = this.hostMetrics.get(host) || { latency: 0, errors: 0 };
      const score = metrics.latency + metrics.errors * 1000; // 閿欒鏉冮噸鏇撮珮
      
      if (score < bestScore) {
        bestScore = score;
        bestHost = host;
      }
    }

    return bestHost;
  }

  // 娴嬭瘯CDN涓绘満鎬ц兘
  async testHosts(): Promise<void> {
    const promises = this.cdnHosts.map(host => this.testHost(host));
    await Promise.allSettled(promises);
  }

  private async testHost(host: string): Promise<void> {
    const startTime = performance.now();
    
    try {
      const response = await fetch(`${host}/health`, {
        method: 'HEAD',
        cache: 'no-cache',
      });
      
      const latency = performance.now() - startTime;
      const errors = response.ok ? 0 : 1;
      
      this.hostMetrics.set(host, { latency, errors });
    } catch (error) {
      this.hostMetrics.set(host, { latency: 5000, errors: 1 });
    }
  }
}

// Service Worker绠＄悊鍣?
class ServiceWorkerManager {
  private registration?: ServiceWorkerRegistration;

  async init(): Promise<void> {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    try {
      this.registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker registered successfully');
      
      // 鐩戝惉鏇存柊
      this.registration.addEventListener('updatefound', () => {
        console.log('Service Worker update found');
      });
      
    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }

  async updateCache(urls: string[]): Promise<void> {
    if (!this.registration) return;

    // 鍚慡ervice Worker鍙戦€佺紦瀛樻洿鏂版秷鎭?
    if (this.registration.active) {
      this.registration.active.postMessage({
        type: 'CACHE_URLS',
        urls,
      });
    }
  }

  async clearCache(): Promise<void> {
    if (!this.registration) return;

    if (this.registration.active) {
      this.registration.active.postMessage({
        type: 'CLEAR_CACHE',
      });
    }
  }
}

// 棰勫姞杞界鐞嗗櫒
class PreloadManager {
  private preloadedResources = new Set<string>();

  // 棰勫姞杞藉叧閿祫婧?
  preloadCriticalResources(resources: Array<{
    url: string;
    type: 'script' | 'style' | 'font' | 'image';
    priority?: 'high' | 'low';
  }>): void {
    resources.forEach(resource => {
      if (this.preloadedResources.has(resource.url)) {
        return;
      }

      const link = document.createElement('link');
      link.rel = 'preload';
      link.href = resource.url;
      
      switch (resource.type) {
        case 'script':
          link.as = 'script';
          break;
        case 'style':
          link.as = 'style';
          break;
        case 'font':
          link.as = 'font';
          link.crossOrigin = 'anonymous';
          break;
        case 'image':
          link.as = 'image';
          break;
      }

      if (resource.priority) {
        (link as any).fetchPriority = resource.priority;
      }

      document.head.appendChild(link);
      this.preloadedResources.add(resource.url);
    });
  }

  // 棰勮繛鎺ュ埌澶栭儴鍩熷悕
  preconnectToDomains(domains: string[]): void {
    domains.forEach(domain => {
      const link = document.createElement('link');
      link.rel = 'preconnect';
      link.href = domain;
      document.head.appendChild(link);
    });
  }

  // DNS棰勮В鏋?
  dnsPrefetch(domains: string[]): void {
    domains.forEach(domain => {
      const link = document.createElement('link');
      link.rel = 'dns-prefetch';
      link.href = domain;
      document.head.appendChild(link);
    });
  }
}

// 鎬ц兘鐩戞帶鍣?
class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private observer?: PerformanceObserver;

  init(): void {
    if (typeof window === 'undefined') return;

    // 鐩戞帶鎬ц兘鏉＄洰
    this.observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      this.processPerformanceEntries(entries);
    });

    this.observer.observe({ entryTypes: ['navigation', 'resource', 'measure'] });

    // 鐩戞帶鍐呭瓨浣跨敤
    this.monitorMemoryUsage();

    // 鐩戞帶缃戠粶鐘舵€?
    this.monitorNetworkStatus();
  }

  private processPerformanceEntries(entries: PerformanceEntry[]): void {
    entries.forEach(entry => {
      if (entry.entryType === 'navigation') {
        const navEntry = entry as PerformanceNavigationTiming;
        this.recordMetric({
          loadTime: navEntry.loadEventEnd - navEntry.loadEventStart,
          renderTime: navEntry.domContentLoadedEventEnd - navEntry.domContentLoadedEventStart,
          memoryUsage: this.getMemoryUsage(),
          bundleSize: 0,
          cacheHitRate: 0,
          networkLatency: navEntry.responseEnd - navEntry.requestStart,
          timestamp: Date.now(),
        });
      }
    });
  }

  private monitorMemoryUsage(): void {
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as any).memory;
        if (memory.usedJSHeapSize > memory.jsHeapSizeLimit * 0.9) {
          console.warn('High memory usage detected');
        }
      }, 10000); // 姣?0绉掓鏌ヤ竴娆?
    }
  }

  private monitorNetworkStatus(): void {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      
      const logNetworkInfo = () => {
        console.log('Network info:', {
          effectiveType: connection.effectiveType,
          downlink: connection.downlink,
          rtt: connection.rtt,
        });
      };

      connection.addEventListener('change', logNetworkInfo);
      logNetworkInfo();
    }
  }

  private recordMetric(metric: PerformanceMetrics): void {
    this.metrics.push(metric);
    
    // 淇濇寔鏈€杩?00鏉¤褰?
    if (this.metrics.length > 100) {
      this.metrics = this.metrics.slice(-100);
    }
  }

  private getMemoryUsage(): number {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return 0;
  }

  getMetrics(): PerformanceMetrics[] {
    return [...this.metrics];
  }

  getAverageMetrics(): Partial<PerformanceMetrics> {
    if (this.metrics.length === 0) return {};

    const totals = this.metrics.reduce(
      (acc, metric) => ({
        loadTime: acc.loadTime + metric.loadTime,
        renderTime: acc.renderTime + metric.renderTime,
        memoryUsage: acc.memoryUsage + metric.memoryUsage,
        networkLatency: acc.networkLatency + metric.networkLatency,
      }),
      { loadTime: 0, renderTime: 0, memoryUsage: 0, networkLatency: 0 }
    );

    const count = this.metrics.length;
    return {
      loadTime: totals.loadTime / count,
      renderTime: totals.renderTime / count,
      memoryUsage: totals.memoryUsage / count,
      networkLatency: totals.networkLatency / count,
    };
  }

  clearMetrics(): void {
    this.metrics = [];
  }
}

// 涓昏鐨勮祫婧愪紭鍖栫鐞嗗櫒
export class ResourceOptimizationManager {
  private config: ResourceOptimizationConfig;
  private codeSplitting: CodeSplittingManager;
  private imageOptimization: ImageOptimizationManager;
  private cdn: CDNManager;
  private serviceWorker: ServiceWorkerManager;
  private preload: PreloadManager;
  private performance: PerformanceMonitor;

  constructor(config: Partial<ResourceOptimizationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    this.codeSplitting = new CodeSplittingManager();
    this.imageOptimization = new ImageOptimizationManager(this.config);
    this.cdn = new CDNManager();
    this.serviceWorker = new ServiceWorkerManager();
    this.preload = new PreloadManager();
    this.performance = new PerformanceMonitor();
  }

  async init(): Promise<void> {
    // 鍒濆鍖栨€ц兘鐩戞帶
    this.performance.init();

    // 鍒濆鍖朣ervice Worker
    if (this.config.enableServiceWorker) {
      await this.serviceWorker.init();
    }

    // 娴嬭瘯CDN鎬ц兘
    if (this.config.enableCDN) {
      await this.cdn.testHosts();
    }

    // 棰勫姞杞藉叧閿祫婧?
    if (this.config.enablePreloading) {
      this.preloadCriticalResources();
    }
  }

  // 浠ｇ爜鍒嗗壊鐩稿叧鏂规硶
  loadComponent = this.codeSplitting.loadComponent.bind(this.codeSplitting);
  preloadComponent = this.codeSplitting.preloadComponent.bind(this.codeSplitting);

  // 鍥剧墖浼樺寲鐩稿叧鏂规硶
  optimizeImageUrl = this.imageOptimization.optimizeImageUrl.bind(this.imageOptimization);
  lazyLoadImage = this.imageOptimization.lazyLoadImage.bind(this.imageOptimization);
  preloadImages = this.imageOptimization.preloadImages.bind(this.imageOptimization);

  // CDN鐩稿叧鏂规硶
  getCDNUrl = this.cdn.getCDNUrl.bind(this.cdn);

  // 棰勫姞杞藉叧閿祫婧?
  private preloadCriticalResources(): void {
    // 棰勫姞杞藉瓧浣?
    this.preload.preloadCriticalResources([
      { url: '/fonts/inter-var.woff2', type: 'font', priority: 'high' },
    ]);

    // 棰勮繛鎺ュ埌澶栭儴鏈嶅姟
    this.preload.preconnectToDomains([
      'https://api.example.com',
      'https://cdn.example.com',
    ]);

    // DNS棰勮В鏋?
    this.preload.dnsPrefetch([
      'https://analytics.example.com',
    ]);
  }

  // 鑾峰彇鎬ц兘鎶ュ憡
  getPerformanceReport(): {
    codeSplitting: ReturnType<CodeSplittingManager['getLoadingStatus']>;
    imageCache: ReturnType<ImageOptimizationManager['getCacheStats']>;
    performance: {
      current: PerformanceMetrics[];
      average: Partial<PerformanceMetrics>;
    };
  } {
    return {
      codeSplitting: this.codeSplitting.getLoadingStatus(),
      imageCache: this.imageOptimization.getCacheStats(),
      performance: {
        current: this.performance.getMetrics(),
        average: this.performance.getAverageMetrics(),
      },
    };
  }

  // 娓呯悊缂撳瓨
  clearAllCaches(): void {
    this.imageOptimization.clearCache();
    this.serviceWorker.clearCache();
    this.performance.clearMetrics();
  }

  // 鏇存柊閰嶇疆
  updateConfig(newConfig: Partial<ResourceOptimizationConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
}

// 鍏ㄥ眬瀹炰緥
export const resourceOptimization = new ResourceOptimizationManager();

// 宸ュ叿鍑芥暟
export const createOptimizedImage = (
  src: string,
  options: Parameters<ImageOptimizationManager['optimizeImageUrl']>[1] = {}
) => {
  return resourceOptimization.optimizeImageUrl(src, options);
};

export const loadComponentWithSplitting = <T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  chunkName?: string
) => {
  return resourceOptimization.loadComponent(importFn, chunkName);
};

// React Hooks
export const useResourceOptimization = () => {
  return {
    loadComponent: resourceOptimization.loadComponent,
    optimizeImage: resourceOptimization.optimizeImageUrl,
    getCDNUrl: resourceOptimization.getCDNUrl,
    getPerformanceReport: resourceOptimization.getPerformanceReport,
  };
};

export default resourceOptimization;