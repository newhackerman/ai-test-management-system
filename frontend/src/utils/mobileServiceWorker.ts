// @ts-nocheck
/**
 * Mobile Service Worker Utilities
 * 绉诲姩绔?Service Worker 宸ュ叿
 */

// Service Worker 娉ㄥ唽
export const registerServiceWorker = async (): Promise<ServiceWorkerRegistration | null> => {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });
      
      console.log('Service Worker registered successfully:', registration);
      
      // 鐩戝惉鏇存柊
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // 鏂扮増鏈彲鐢?
              showUpdateNotification();
            }
          });
        }
      });
      
      return registration;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
      return null;
    }
  }
  
  return null;
};

// 鏄剧ず鏇存柊閫氱煡
const showUpdateNotification = () => {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('应用更新可用', {
      body: '点击刷新页面以获取最新版本',
      icon: '/icon-192x192.png',
      tag: 'app-update'
    });
  }
};

// 缂撳瓨绛栫暐
export const cacheStrategies = {
  // 缂撳瓨浼樺厛绛栫暐
  cacheFirst: (cacheName: string, request: Request): Promise<Response> => {
    return caches.open(cacheName).then(cache => {
      return cache.match(request).then(response => {
        if (response) {
          return response;
        }
        
        return fetch(request).then(networkResponse => {
          cache.put(request, networkResponse.clone());
          return networkResponse;
        });
      });
    });
  },
  
  // 缃戠粶浼樺厛绛栫暐
  networkFirst: (cacheName: string, request: Request): Promise<Response> => {
    return fetch(request).then(response => {
      return caches.open(cacheName).then(cache => {
        cache.put(request, response.clone());
        return response;
      });
    }).catch(() => {
      return caches.open(cacheName).then(cache => {
        return cache.match(request);
      });
    });
  },
  
  // 浠呯綉缁滅瓥鐣?
  networkOnly: (request: Request): Promise<Response> => {
    return fetch(request);
  },
  
  // 浠呯紦瀛樼瓥鐣?
  cacheOnly: (cacheName: string, request: Request): Promise<Response> => {
    return caches.open(cacheName).then(cache => {
      return cache.match(request);
    });
  }
};

// 棰勭紦瀛樿祫婧?
export const precacheResources = async (resources: string[]): Promise<void> => {
  const cache = await caches.open('dashboard-precache-v1');
  await cache.addAll(resources);
};

// 娓呯悊鏃х紦瀛?
export const cleanupOldCaches = async (currentCaches: string[]): Promise<void> => {
  const cacheNames = await caches.keys();
  
  await Promise.all(
    cacheNames.map(cacheName => {
      if (!currentCaches.includes(cacheName)) {
        return caches.delete(cacheName);
      }
    })
  );
};

// 绂荤嚎椤甸潰绠＄悊
export class OfflinePageManager {
  private offlinePage = '/offline.html';
  private cacheName = 'dashboard-offline-v1';
  
  async init() {
    await this.cacheOfflinePage();
  }
  
  private async cacheOfflinePage() {
    const cache = await caches.open(this.cacheName);
    await cache.add(this.offlinePage);
  }
  
  async getOfflinePage(): Promise<Response | undefined> {
    const cache = await caches.open(this.cacheName);
    return cache.match(this.offlinePage);
  }
}

// 鍚庡彴鍚屾绠＄悊
export class BackgroundSyncManager {
  private syncTag = 'dashboard-sync';
  
  async registerSync(data: any) {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      const registration = await navigator.serviceWorker.ready;
      
      // 瀛樺偍鍚屾鏁版嵁
      await this.storeSync(data);
      
      // 娉ㄥ唽鍚庡彴鍚屾
      await registration.sync.register(this.syncTag);
    } else {
      // 闄嶇骇澶勭悊锛氱珛鍗冲悓姝?
      await this.performSync(data);
    }
  }
  
  private async storeSync(data: any) {
    const syncData = {
      id: Date.now().toString(),
      data,
      timestamp: Date.now()
    };
    
    const stored = JSON.parse(localStorage.getItem('pending-syncs') || '[]');
    stored.push(syncData);
    localStorage.setItem('pending-syncs', JSON.stringify(stored));
  }
  
  private async performSync(data: any) {
    try {
      // 鎵ц鍚屾閫昏緫
      const response = await fetch('/api/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (response.ok) {
        // 鍚屾鎴愬姛锛屾竻鐞嗗瓨鍌ㄧ殑鏁版嵁
        this.clearSyncData(data.id);
      }
    } catch (error) {
      console.error('Sync failed:', error);
    }
  }
  
  private clearSyncData(id: string) {
    const stored = JSON.parse(localStorage.getItem('pending-syncs') || '[]');
    const filtered = stored.filter((item: any) => item.id !== id);
    localStorage.setItem('pending-syncs', JSON.stringify(filtered));
  }
}

// 鎺ㄩ€侀€氱煡绠＄悊
export class PushNotificationManager {
  private vapidPublicKey = process.env.REACT_APP_VAPID_PUBLIC_KEY;
  
  async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) {
      console.warn('This browser does not support notifications');
      return false;
    }
    
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  
  async subscribe(): Promise<PushSubscription | null> {
    if (!this.vapidPublicKey) {
      console.error('VAPID public key not configured');
      return null;
    }
    
    const registration = await navigator.serviceWorker.ready;
    
    try {
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
      });
      
      // 鍙戦€佽闃呬俊鎭埌鏈嶅姟鍣?
      await this.sendSubscriptionToServer(subscription);
      
      return subscription;
    } catch (error) {
      console.error('Failed to subscribe to push notifications:', error);
      return null;
    }
  }
  
  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  }
  
  private async sendSubscriptionToServer(subscription: PushSubscription) {
    await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(subscription)
    });
  }
}

// 搴旂敤鏇存柊绠＄悊
export class AppUpdateManager {
  private registration: ServiceWorkerRegistration | null = null;
  
  constructor(registration: ServiceWorkerRegistration | null) {
    this.registration = registration;
  }
  
  checkForUpdates() {
    if (this.registration) {
      this.registration.update();
    }
  }
  
  async skipWaiting() {
    if (this.registration?.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  }
  
  onUpdateAvailable(callback: () => void) {
    if (this.registration) {
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              callback();
            }
          });
        }
      });
    }
  }
}

// 鎬ц兘鐩戞帶
export class ServiceWorkerPerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();
  
  recordCacheHit(resource: string) {
    this.recordMetric('cache-hit', resource);
  }
  
  recordCacheMiss(resource: string) {
    this.recordMetric('cache-miss', resource);
  }
  
  recordNetworkTime(resource: string, time: number) {
    this.recordMetric('network-time', resource, time);
  }
  
  private recordMetric(type: string, resource: string, value: number = 1) {
    const key = `${type}-${resource}`;
    if (!this.metrics.has(key)) {
      this.metrics.set(key, []);
    }
    
    const values = this.metrics.get(key)!;
    values.push(value);
    
      // 只保留最近 100 条记录
    if (values.length > 100) {
      values.shift();
    }
  }
  
  getMetrics() {
    const result: Record<string, any> = {};
    
    this.metrics.forEach((values, key) => {
      result[key] = {
        count: values.length,
        average: values.reduce((sum, val) => sum + val, 0) / values.length,
        total: values.reduce((sum, val) => sum + val, 0)
      };
    });
    
    return result;
  }
}

// 鍏ㄥ眬瀹炰緥
export const offlinePageManager = new OfflinePageManager();
export const backgroundSyncManager = new BackgroundSyncManager();
export const pushNotificationManager = new PushNotificationManager();
export const performanceMonitor = new ServiceWorkerPerformanceMonitor();

// 鍒濆鍖?Service Worker
export const initMobileServiceWorker = async () => {
  const registration = await registerServiceWorker();
  
  if (registration) {
    await offlinePageManager.init();
    
    const updateManager = new AppUpdateManager(registration);
    
    updateManager.onUpdateAvailable(() => {
      // 鏄剧ず鏇存柊鎻愮ず
      if (confirm('发现新版本，是否立即更新？')) {
        updateManager.skipWaiting();
        window.location.reload();
      }
    });
    
    return {
      registration,
      updateManager,
      offlinePageManager,
      backgroundSyncManager,
      pushNotificationManager,
      performanceMonitor
    };
  }
  
  return null;
};

export default {
  registerServiceWorker,
  cacheStrategies,
  precacheResources,
  cleanupOldCaches,
  OfflinePageManager,
  BackgroundSyncManager,
  PushNotificationManager,
  AppUpdateManager,
  ServiceWorkerPerformanceMonitor,
  initMobileServiceWorker
};
