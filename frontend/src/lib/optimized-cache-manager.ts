// @ts-nocheck
/**
 * 浼樺寲鐨勭紦瀛樼鐞嗗櫒
 * 
 * 鎻愪緵鏅鸿兘缂撳瓨绛栫暐銆佸唴瀛樼鐞嗗拰鏁版嵁鍚屾鍔熻兘
 */
import { QueryClient } from '@tanstack/react-query';

// 缂撳瓨绛栫暐閰嶇疆
interface CacheStrategy {
  staleTime: number;
  cacheTime: number;
  refetchOnWindowFocus: boolean;
  refetchOnMount: boolean;
  retry: number;
  retryDelay: (attemptIndex: number) => number;
}

// 缂撳瓨浼樺厛绾?
enum CachePriority {
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4,
}

// 缂撳瓨閰嶇疆鏄犲皠
const CACHE_STRATEGIES: Record<string, CacheStrategy> = {
  // 椤圭洰鍒楄〃 - 涓瓑浼樺厛绾э紝5鍒嗛挓杩囨湡
  projects: {
    staleTime: 5 * 60 * 1000,
    cacheTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  
  // 椤圭洰璇︽儏 - 楂樹紭鍏堢骇锛?鍒嗛挓杩囨湡
  projectDetail: {
    staleTime: 2 * 60 * 1000,
    cacheTime: 15 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchOnMount: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  
  // 椤圭洰缁熻 - 涓瓑浼樺厛绾э紝1鍒嗛挓杩囨湡
  projectStats: {
    staleTime: 1 * 60 * 1000,
    cacheTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  
  // 鐢ㄦ埛淇℃伅 - 楂樹紭鍏堢骇锛?0鍒嗛挓杩囨湡
  user: {
    staleTime: 10 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  
  // 閰嶇疆鏁版嵁 - 浣庝紭鍏堢骇锛?0鍒嗛挓杩囨湡
  config: {
    staleTime: 30 * 60 * 1000,
    cacheTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: 1,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
};

class OptimizedCacheManager {
  private queryClient: QueryClient;
  private memoryThreshold: number = 50 * 1024 * 1024; // 50MB
  private cleanupInterval: number = 5 * 60 * 1000; // 5鍒嗛挓
  private cleanupTimer: NodeJS.Timeout | null = null;
  private cacheMetrics: Map<string, { hits: number; misses: number; lastAccess: number }> = new Map();

  constructor(queryClient: QueryClient) {
    this.queryClient = queryClient;
    this.startCleanupTimer();
    this.setupMemoryMonitoring();
  }

  // 鑾峰彇缂撳瓨绛栫暐
  getCacheStrategy(type: string): CacheStrategy {
    return CACHE_STRATEGIES[type] || CACHE_STRATEGIES.projects;
  }

  // 鏅鸿兘棰勫姞杞?
  async intelligentPrefetch(queryKey: string[], queryFn: () => Promise<any>, priority: CachePriority = CachePriority.MEDIUM) {
    const cacheKey = JSON.stringify(queryKey);
    const existing = this.queryClient.getQueryData(queryKey);
    
    // 濡傛灉鏁版嵁宸插瓨鍦ㄤ笖鏈繃鏈燂紝璺宠繃棰勫姞杞?
    if (existing) {
      const queryState = this.queryClient.getQueryState(queryKey);
      if (queryState && !queryState.isStale) {
        this.recordCacheHit(cacheKey);
        return existing;
      }
    }

    // 鏍规嵁浼樺厛绾у喅瀹氭槸鍚︾珛鍗抽鍔犺浇
    const shouldPrefetch = this.shouldPrefetch(priority);
    if (!shouldPrefetch) {
      this.recordCacheMiss(cacheKey);
      return null;
    }

    try {
      await this.queryClient.prefetchQuery({
        queryKey,
        queryFn,
        ...this.getCacheStrategy('projects'),
      });
      this.recordCacheHit(cacheKey);
    } catch (error) {
      this.recordCacheMiss(cacheKey);
      console.warn('Prefetch failed:', error);
    }
  }

  // 鎵归噺棰勫姞杞?
  async batchPrefetch(queries: Array<{ queryKey: string[]; queryFn: () => Promise<any>; priority?: CachePriority }>) {
    const highPriorityQueries = queries.filter(q => (q.priority || CachePriority.MEDIUM) >= CachePriority.HIGH);
    const lowPriorityQueries = queries.filter(q => (q.priority || CachePriority.MEDIUM) < CachePriority.HIGH);

    // 鍏堟墽琛岄珮浼樺厛绾ф煡璇?
    await Promise.all(
      highPriorityQueries.map(query => 
        this.intelligentPrefetch(query.queryKey, query.queryFn, query.priority)
      )
    );

    // 寤惰繜鎵ц浣庝紭鍏堢骇鏌ヨ
    setTimeout(() => {
      Promise.all(
        lowPriorityQueries.map(query => 
          this.intelligentPrefetch(query.queryKey, query.queryFn, query.priority)
        )
      );
    }, 1000);
  }

  // 鏅鸿兘缂撳瓨澶辨晥
  intelligentInvalidate(pattern: string | RegExp) {
    const cache = this.queryClient.getQueryCache();
    const queries = cache.getAll();

    queries.forEach(query => {
      const queryKey = JSON.stringify(query.queryKey);
      const shouldInvalidate = typeof pattern === 'string' 
        ? queryKey.includes(pattern)
        : pattern.test(queryKey);

      if (shouldInvalidate) {
        // 妫€鏌ユ煡璇㈢殑浣跨敤棰戠巼锛岄绻佷娇鐢ㄧ殑鏌ヨ寤惰繜澶辨晥
        const metrics = this.cacheMetrics.get(queryKey);
        if (metrics && metrics.hits > 10 && Date.now() - metrics.lastAccess < 60000) {
          // 寤惰繜1鍒嗛挓澶辨晥
          setTimeout(() => {
            this.queryClient.invalidateQueries({ queryKey: query.queryKey });
          }, 60000);
        } else {
          this.queryClient.invalidateQueries({ queryKey: query.queryKey });
        }
      }
    });
  }

  // 鍐呭瓨浼樺寲娓呯悊
  performMemoryCleanup() {
    const cache = this.queryClient.getQueryCache();
    const queries = cache.getAll();
    
    // 鎸夋渶鍚庤闂椂闂存帓搴?
    const sortedQueries = queries
      .map(query => ({
        query,
        lastAccess: this.cacheMetrics.get(JSON.stringify(query.queryKey))?.lastAccess || 0,
        size: this.estimateQuerySize(query),
      }))
      .sort((a, b) => a.lastAccess - b.lastAccess);

    let totalSize = sortedQueries.reduce((sum, item) => sum + item.size, 0);
    
    // 濡傛灉瓒呰繃鍐呭瓨闃堝€硷紝娓呯悊鏈€涔呮湭璁块棶鐨勬煡璇?
    while (totalSize > this.memoryThreshold && sortedQueries.length > 0) {
      const oldest = sortedQueries.shift();
      if (oldest) {
        this.queryClient.removeQueries({ queryKey: oldest.query.queryKey });
        totalSize -= oldest.size;
      }
    }
  }

  // 浼扮畻鏌ヨ鏁版嵁澶у皬
  private estimateQuerySize(query: any): number {
    try {
      const data = query.state.data;
      if (!data) return 0;
      
      const jsonString = JSON.stringify(data);
      return jsonString.length * 2; // 绮楃暐浼扮畻锛屾瘡涓瓧绗?瀛楄妭
    } catch {
      return 1024; // 榛樿1KB
    }
  }

  // 鍒ゆ柇鏄惁搴旇棰勫姞杞?
  private shouldPrefetch(priority: CachePriority): boolean {
    // 妫€鏌ョ綉缁滅姸鎬?
    if (navigator.connection) {
      const connection = navigator.connection as any;
      if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
        return priority >= CachePriority.HIGH;
      }
    }

    // 妫€鏌ュ唴瀛樹娇鐢ㄦ儏鍐?
    if (this.isMemoryPressure()) {
      return priority >= CachePriority.CRITICAL;
    }

    return true;
  }

  // 妫€鏌ュ唴瀛樺帇鍔?
  private isMemoryPressure(): boolean {
    try {
      // @ts-ignore
      if (performance.memory) {
        // @ts-ignore
        const { usedJSHeapSize, totalJSHeapSize } = performance.memory;
        return usedJSHeapSize / totalJSHeapSize > 0.8;
      }
    } catch {
      // 濡傛灉鏃犳硶鑾峰彇鍐呭瓨淇℃伅锛屽亣璁炬病鏈夊唴瀛樺帇鍔?
    }
    return false;
  }

  // 璁板綍缂撳瓨鍛戒腑
  private recordCacheHit(cacheKey: string) {
    const metrics = this.cacheMetrics.get(cacheKey) || { hits: 0, misses: 0, lastAccess: 0 };
    metrics.hits++;
    metrics.lastAccess = Date.now();
    this.cacheMetrics.set(cacheKey, metrics);
  }

  // 璁板綍缂撳瓨鏈懡涓?
  private recordCacheMiss(cacheKey: string) {
    const metrics = this.cacheMetrics.get(cacheKey) || { hits: 0, misses: 0, lastAccess: 0 };
    metrics.misses++;
    metrics.lastAccess = Date.now();
    this.cacheMetrics.set(cacheKey, metrics);
  }

  // 鍚姩娓呯悊瀹氭椂鍣?
  private startCleanupTimer() {
    this.cleanupTimer = setInterval(() => {
      this.performMemoryCleanup();
      this.cleanupMetrics();
    }, this.cleanupInterval);
  }

  // 娓呯悊杩囨湡鎸囨爣
  private cleanupMetrics() {
    const now = Date.now();
    const oneHour = 60 * 60 * 1000;
    
    for (const [key, metrics] of this.cacheMetrics.entries()) {
      if (now - metrics.lastAccess > oneHour) {
        this.cacheMetrics.delete(key);
      }
    }
  }

  // 璁剧疆鍐呭瓨鐩戞帶
  private setupMemoryMonitoring() {
    if (typeof window !== 'undefined') {
      // 鐩戝惉鍐呭瓨璀﹀憡浜嬩欢
      window.addEventListener('memorywarning', () => {
        this.performMemoryCleanup();
      });

      // 鐩戝惉椤甸潰鍙鎬у彉鍖?
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          // 椤甸潰闅愯棌鏃惰繘琛屾竻鐞?
          setTimeout(() => {
            if (document.hidden) {
              this.performMemoryCleanup();
            }
          }, 30000); // 30绉掑悗娓呯悊
        }
      });
    }
  }

  // 鑾峰彇缂撳瓨缁熻
  getCacheStats() {
    const cache = this.queryClient.getQueryCache();
    const queries = cache.getAll();
    
    let totalHits = 0;
    let totalMisses = 0;
    let totalSize = 0;
    
    for (const [key, metrics] of this.cacheMetrics.entries()) {
      totalHits += metrics.hits;
      totalMisses += metrics.misses;
    }
    
    queries.forEach(query => {
      totalSize += this.estimateQuerySize(query);
    });

    return {
      totalQueries: queries.length,
      totalHits,
      totalMisses,
      hitRate: totalHits / (totalHits + totalMisses) || 0,
      totalSize,
      memoryUsage: totalSize / this.memoryThreshold,
    };
  }

  // 閿€姣佺紦瀛樼鐞嗗櫒
  destroy() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    this.cacheMetrics.clear();
  }
}

// 鍒涘缓浼樺寲鐨勬煡璇㈠鎴风
export const createOptimizedQueryClient = (): QueryClient => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5鍒嗛挓
        cacheTime: 10 * 60 * 1000, // 10鍒嗛挓
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        retry: (failureCount, error: any) => {
          // 鏍规嵁閿欒绫诲瀷鍐冲畾鏄惁閲嶈瘯
          if (error?.status === 404 || error?.status === 403) {
            return false;
          }
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
      mutations: {
        retry: 1,
        retryDelay: 1000,
      },
    },
  });

  // 鍒涘缓缂撳瓨绠＄悊鍣?
  const cacheManager = new OptimizedCacheManager(queryClient);

  // 灏嗙紦瀛樼鐞嗗櫒闄勫姞鍒版煡璇㈠鎴风
  (queryClient as any).cacheManager = cacheManager;

  return queryClient;
};

// 鑾峰彇缂撳瓨绠＄悊鍣?
export const getCacheManager = (queryClient: QueryClient): OptimizedCacheManager => {
  return (queryClient as any).cacheManager;
};

// 缂撳瓨閿伐鍘?
export const createCacheKeyFactory = (prefix: string) => ({
  all: [prefix] as const,
  lists: () => [prefix, 'list'] as const,
  list: (params: any) => [prefix, 'list', params] as const,
  details: () => [prefix, 'detail'] as const,
  detail: (id: string | number) => [prefix, 'detail', id] as const,
  infinite: (params: any) => [prefix, 'infinite', params] as const,
});

export { OptimizedCacheManager, CachePriority };