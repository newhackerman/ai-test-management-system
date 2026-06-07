/**
 * Mobile Performance Optimization Utilities
 * 移动端性能优化工具集
 */

// Intersection Observer for lazy loading
let intersectionObserver: IntersectionObserver | null = null;

/**
 * 初始化 Intersection Observer
 */
export const initIntersectionObserver = (callback: IntersectionObserverCallback) => {
  if (typeof window === 'undefined') return null;
  
  if (!intersectionObserver) {
    intersectionObserver = new IntersectionObserver(callback, {
      root: null,
      rootMargin: '50px',
      threshold: 0.1
    });
  }
  
  return intersectionObserver;
};

/**
 * 懒加载组件
 */
export const lazyLoadComponent = (element: Element, callback: () => void) => {
  const observer = initIntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        callback();
        observer?.unobserve(entry.target);
      }
    });
  });
  
  if (observer) {
    observer.observe(element);
  }
};

/**
 * 图片懒加载
 */
export const lazyLoadImage = (img: HTMLImageElement, src: string) => {
  const observer = initIntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const image = entry.target as HTMLImageElement;
        image.src = src;
        image.onload = () => {
          image.classList.add('loaded');
        };
        observer?.unobserve(image);
      }
    });
  });
  
  if (observer) {
    observer.observe(img);
  }
};

/**
 * 防抖函数
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate?: boolean
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null;
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };
    
    const callNow = immediate && !timeout;
    
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    
    if (callNow) func(...args);
  };
};

/**
 * 节流函数
 */
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

/**
 * 虚拟滚动管理器
 */
export class VirtualScrollManager {
  private container: HTMLElement;
  private items: any[];
  private itemHeight: number;
  private visibleCount: number;
  private scrollTop: number = 0;
  private startIndex: number = 0;
  private endIndex: number = 0;
  
  constructor(
    container: HTMLElement,
    items: any[],
    itemHeight: number,
    visibleCount: number
  ) {
    this.container = container;
    this.items = items;
    this.itemHeight = itemHeight;
    this.visibleCount = visibleCount;
    this.endIndex = Math.min(visibleCount, items.length);
    
    this.setupScrollListener();
  }
  
  private setupScrollListener() {
    const handleScroll = throttle(() => {
      this.scrollTop = this.container.scrollTop;
      this.updateVisibleRange();
    }, 16); // 60fps
    
    this.container.addEventListener('scroll', handleScroll, { passive: true });
  }
  
  private updateVisibleRange() {
    const newStartIndex = Math.floor(this.scrollTop / this.itemHeight);
    const newEndIndex = Math.min(
      newStartIndex + this.visibleCount + 1,
      this.items.length
    );
    
    if (newStartIndex !== this.startIndex || newEndIndex !== this.endIndex) {
      this.startIndex = newStartIndex;
      this.endIndex = newEndIndex;
      this.render();
    }
  }
  
  private render() {
    // 实现虚拟滚动渲染逻辑
    // 这里应该触发组件重新渲染
  }
  
  getVisibleItems() {
    return this.items.slice(this.startIndex, this.endIndex);
  }
  
  getTransformOffset() {
    return this.startIndex * this.itemHeight;
  }
  
  getTotalHeight() {
    return this.items.length * this.itemHeight;
  }
}

/**
 * 内存管理工具
 */
export class MemoryManager {
  private cache = new Map<string, any>();
  private maxSize: number;
  private currentSize: number = 0;
  
  constructor(maxSize: number = 50) {
    this.maxSize = maxSize;
  }
  
  set(key: string, value: any) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.currentSize >= this.maxSize) {
      // 删除最旧的项目
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
      this.currentSize--;
    }
    
    this.cache.set(key, value);
    this.currentSize++;
  }
  
  get(key: string) {
    if (this.cache.has(key)) {
      // 移动到最新位置
      const value = this.cache.get(key);
      this.cache.delete(key);
      this.cache.set(key, value);
      return value;
    }
    return null;
  }
  
  clear() {
    this.cache.clear();
    this.currentSize = 0;
  }
  
  size() {
    return this.currentSize;
  }
}

/**
 * 图片压缩工具
 */
export const compressImage = (
  file: File,
  maxWidth: number = 800,
  maxHeight: number = 600,
  quality: number = 0.8
): Promise<Blob> => {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;
    const img = new Image();
    
    img.onload = () => {
      // 计算新尺寸
      let { width, height } = img;
      
      if (width > height) {
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          width = (width * maxHeight) / height;
          height = maxHeight;
        }
      }
      
      canvas.width = width;
      canvas.height = height;
      
      // 绘制并压缩
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob(resolve, 'image/jpeg', quality);
    };
    
    img.src = URL.createObjectURL(file);
  });
};

/**
 * 网络状态检测
 */
export class NetworkMonitor {
  private callbacks: ((online: boolean) => void)[] = [];
  private isOnline: boolean = navigator.onLine;
  
  constructor() {
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }
  
  private handleOnline = () => {
    this.isOnline = true;
    this.notifyCallbacks(true);
  };
  
  private handleOffline = () => {
    this.isOnline = false;
    this.notifyCallbacks(false);
  };
  
  private notifyCallbacks(online: boolean) {
    this.callbacks.forEach(callback => callback(online));
  }
  
  onStatusChange(callback: (online: boolean) => void) {
    this.callbacks.push(callback);
    
    // 返回取消订阅函数
    return () => {
      const index = this.callbacks.indexOf(callback);
      if (index > -1) {
        this.callbacks.splice(index, 1);
      }
    };
  }
  
  getStatus() {
    return this.isOnline;
  }
  
  destroy() {
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
    this.callbacks = [];
  }
}

/**
 * 电池状态监控
 */
export class BatteryMonitor {
  private battery: any = null;
  private callbacks: ((batteryInfo: any) => void)[] = [];
  
  async init() {
    if ('getBattery' in navigator) {
      try {
        this.battery = await (navigator as any).getBattery();
        this.setupListeners();
      } catch (error) {
        console.warn('Battery API not supported');
      }
    }
  }
  
  private setupListeners() {
    if (!this.battery) return;
    
    const updateBatteryInfo = () => {
      const info = {
        level: this.battery.level,
        charging: this.battery.charging,
        chargingTime: this.battery.chargingTime,
        dischargingTime: this.battery.dischargingTime
      };
      
      this.callbacks.forEach(callback => callback(info));
    };
    
    this.battery.addEventListener('chargingchange', updateBatteryInfo);
    this.battery.addEventListener('levelchange', updateBatteryInfo);
    this.battery.addEventListener('chargingtimechange', updateBatteryInfo);
    this.battery.addEventListener('dischargingtimechange', updateBatteryInfo);
  }
  
  onBatteryChange(callback: (batteryInfo: any) => void) {
    this.callbacks.push(callback);
    
    return () => {
      const index = this.callbacks.indexOf(callback);
      if (index > -1) {
        this.callbacks.splice(index, 1);
      }
    };
  }
  
  getBatteryInfo() {
    if (!this.battery) return null;
    
    return {
      level: this.battery.level,
      charging: this.battery.charging,
      chargingTime: this.battery.chargingTime,
      dischargingTime: this.battery.dischargingTime
    };
  }
}

/**
 * 性能监控工具
 */
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();
  
  startTiming(label: string) {
    performance.mark(`${label}-start`);
  }
  
  endTiming(label: string) {
    performance.mark(`${label}-end`);
    performance.measure(label, `${label}-start`, `${label}-end`);
    
    const measure = performance.getEntriesByName(label)[0];
    const duration = measure.duration;
    
    if (!this.metrics.has(label)) {
      this.metrics.set(label, []);
    }
    
    const times = this.metrics.get(label)!;
    times.push(duration);
    
    // 只保留最近100次测量
    if (times.length > 100) {
      times.shift();
    }
    
    return duration;
  }
  
  getAverageTime(label: string): number {
    const times = this.metrics.get(label);
    if (!times || times.length === 0) return 0;
    
    return times.reduce((sum, time) => sum + time, 0) / times.length;
  }
  
  getMetrics() {
    const result: Record<string, { average: number; count: number }> = {};
    
    this.metrics.forEach((times, label) => {
      result[label] = {
        average: this.getAverageTime(label),
        count: times.length
      };
    });
    
    return result;
  }
  
  clear() {
    this.metrics.clear();
    performance.clearMarks();
    performance.clearMeasures();
  }
}

// 全局实例
export const memoryManager = new MemoryManager();
export const networkMonitor = new NetworkMonitor();
export const batteryMonitor = new BatteryMonitor();
export const performanceMonitor = new PerformanceMonitor();

// 初始化电池监控
batteryMonitor.init();

/**
 * 移动端优化配置
 */
export const mobileOptimizationConfig = {
  // 图片懒加载配置
  lazyLoading: {
    rootMargin: '50px',
    threshold: 0.1
  },
  
  // 虚拟滚动配置
  virtualScroll: {
    itemHeight: 100,
    overscan: 5
  },
  
  // 缓存配置
  cache: {
    maxSize: 50,
    ttl: 5 * 60 * 1000 // 5分钟
  },
  
  // 性能配置
  performance: {
    throttleDelay: 16, // 60fps
    debounceDelay: 300,
    maxConcurrentRequests: 3
  },
  
  // 图片压缩配置
  imageCompression: {
    maxWidth: 800,
    maxHeight: 600,
    quality: 0.8
  }
};

export default {
  lazyLoadComponent,
  lazyLoadImage,
  debounce,
  throttle,
  VirtualScrollManager,
  MemoryManager,
  compressImage,
  NetworkMonitor,
  BatteryMonitor,
  PerformanceMonitor,
  memoryManager,
  networkMonitor,
  batteryMonitor,
  performanceMonitor,
  mobileOptimizationConfig
};