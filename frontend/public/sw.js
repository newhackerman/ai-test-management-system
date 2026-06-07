/**
 * Service Worker for Resource Optimization
 * 
 * 实现静态资源缓存、API缓存和离线支持
 */

const CACHE_NAME = 'dashboard-v1';
const STATIC_CACHE_NAME = 'dashboard-static-v1';
const API_CACHE_NAME = 'dashboard-api-v1';
const IMAGE_CACHE_NAME = 'dashboard-images-v1';

// 需要缓存的静态资源
const STATIC_RESOURCES = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/js/main.js',
  '/static/css/main.css',
  '/fonts/inter-var.woff2',
];

// 需要缓存的API路径模式
const API_CACHE_PATTERNS = [
  /^\/api\/v1\/dashboards/,
  /^\/api\/v1\/widgets/,
  /^\/api\/v1\/projects/,
  /^\/api\/v1\/metrics/,
];

// 图片资源模式
const IMAGE_PATTERNS = [
  /\.(?:png|jpg|jpeg|svg|gif|webp|avif)$/,
];

// 缓存策略配置
const CACHE_STRATEGIES = {
  static: 'cache-first',
  api: 'network-first',
  images: 'cache-first',
  default: 'network-first',
};

// 缓存TTL配置（毫秒）
const CACHE_TTL = {
  static: 7 * 24 * 60 * 60 * 1000, // 7天
  api: 5 * 60 * 1000, // 5分钟
  images: 30 * 24 * 60 * 60 * 1000, // 30天
};

// 安装事件
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    Promise.all([
      // 缓存静态资源
      caches.open(STATIC_CACHE_NAME).then((cache) => {
        return cache.addAll(STATIC_RESOURCES);
      }),
      // 跳过等待，立即激活
      self.skipWaiting(),
    ])
  );
});

// 激活事件
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    Promise.all([
      // 清理旧缓存
      cleanupOldCaches(),
      // 立即控制所有客户端
      self.clients.claim(),
    ])
  );
});

// 拦截网络请求
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // 只处理同源请求
  if (url.origin !== location.origin) {
    return;
  }
  
  // 根据请求类型选择缓存策略
  if (isStaticResource(request)) {
    event.respondWith(handleStaticResource(request));
  } else if (isAPIRequest(request)) {
    event.respondWith(handleAPIRequest(request));
  } else if (isImageRequest(request)) {
    event.respondWith(handleImageRequest(request));
  } else {
    event.respondWith(handleDefaultRequest(request));
  }
});

// 处理消息
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'CACHE_URLS':
      handleCacheUrls(data.urls);
      break;
    case 'CLEAR_CACHE':
      handleClearCache();
      break;
    case 'GET_CACHE_STATS':
      handleGetCacheStats().then(stats => {
        event.ports[0].postMessage(stats);
      });
      break;
    default:
      console.log('Unknown message type:', type);
  }
});

// 判断是否为静态资源
function isStaticResource(request) {
  const url = new URL(request.url);
  return (
    request.method === 'GET' &&
    (url.pathname.startsWith('/static/') ||
     url.pathname.startsWith('/fonts/') ||
     url.pathname === '/' ||
     url.pathname === '/index.html' ||
     url.pathname === '/manifest.json')
  );
}

// 判断是否为API请求
function isAPIRequest(request) {
  const url = new URL(request.url);
  return API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// 判断是否为图片请求
function isImageRequest(request) {
  const url = new URL(request.url);
  return IMAGE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// 处理静态资源请求（缓存优先）
async function handleStaticResource(request) {
  try {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse && !isExpired(cachedResponse, CACHE_TTL.static)) {
      return cachedResponse;
    }
    
    // 尝试从网络获取
    try {
      const networkResponse = await fetch(request);
      if (networkResponse.ok) {
        // 更新缓存
        const responseClone = networkResponse.clone();
        await cache.put(request, addTimestamp(responseClone));
      }
      return networkResponse;
    } catch (networkError) {
      // 网络失败，返回缓存（即使过期）
      if (cachedResponse) {
        return cachedResponse;
      }
      throw networkError;
    }
  } catch (error) {
    console.error('Static resource handling failed:', error);
    return new Response('Resource not available', { status: 503 });
  }
}

// 处理API请求（网络优先）
async function handleAPIRequest(request) {
  try {
    // 先尝试网络请求
    try {
      const networkResponse = await fetch(request);
      
      if (networkResponse.ok) {
        // 缓存成功的响应
        const cache = await caches.open(API_CACHE_NAME);
        const responseClone = networkResponse.clone();
        await cache.put(request, addTimestamp(responseClone));
      }
      
      return networkResponse;
    } catch (networkError) {
      // 网络失败，尝试从缓存获取
      const cache = await caches.open(API_CACHE_NAME);
      const cachedResponse = await cache.match(request);
      
      if (cachedResponse && !isExpired(cachedResponse, CACHE_TTL.api)) {
        // 添加离线标识
        const response = cachedResponse.clone();
        response.headers.set('X-Served-By', 'service-worker-cache');
        return response;
      }
      
      throw networkError;
    }
  } catch (error) {
    console.error('API request handling failed:', error);
    return new Response(
      JSON.stringify({ error: 'Service temporarily unavailable' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// 处理图片请求（缓存优先）
async function handleImageRequest(request) {
  try {
    const cache = await caches.open(IMAGE_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse && !isExpired(cachedResponse, CACHE_TTL.images)) {
      return cachedResponse;
    }
    
    // 尝试从网络获取
    try {
      const networkResponse = await fetch(request);
      if (networkResponse.ok) {
        // 缓存图片
        const responseClone = networkResponse.clone();
        await cache.put(request, addTimestamp(responseClone));
      }
      return networkResponse;
    } catch (networkError) {
      // 网络失败，返回缓存（即使过期）
      if (cachedResponse) {
        return cachedResponse;
      }
      
      // 返回占位图片
      return new Response(
        '<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg"><rect width="200" height="200" fill="#f0f0f0"/><text x="100" y="100" text-anchor="middle" fill="#999">Image not available</text></svg>',
        {
          headers: {
            'Content-Type': 'image/svg+xml',
            'Cache-Control': 'no-cache',
          },
        }
      );
    }
  } catch (error) {
    console.error('Image request handling failed:', error);
    return new Response('Image not available', { status: 503 });
  }
}

// 处理默认请求（网络优先）
async function handleDefaultRequest(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.error('Default request handling failed:', error);
    return new Response('Service not available', { status: 503 });
  }
}

// 添加时间戳到响应头
function addTimestamp(response) {
  const headers = new Headers(response.headers);
  headers.set('sw-cache-timestamp', Date.now().toString());
  
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: headers,
  });
}

// 检查缓存是否过期
function isExpired(response, ttl) {
  const timestamp = response.headers.get('sw-cache-timestamp');
  if (!timestamp) {
    return true; // 没有时间戳，认为过期
  }
  
  const cacheTime = parseInt(timestamp, 10);
  const now = Date.now();
  
  return (now - cacheTime) > ttl;
}

// 清理旧缓存
async function cleanupOldCaches() {
  const cacheNames = await caches.keys();
  const currentCaches = [CACHE_NAME, STATIC_CACHE_NAME, API_CACHE_NAME, IMAGE_CACHE_NAME];
  
  const deletePromises = cacheNames
    .filter(cacheName => !currentCaches.includes(cacheName))
    .map(cacheName => caches.delete(cacheName));
  
  await Promise.all(deletePromises);
  console.log('Old caches cleaned up');
}

// 处理缓存URL消息
async function handleCacheUrls(urls) {
  try {
    const cache = await caches.open(STATIC_CACHE_NAME);
    await cache.addAll(urls);
    console.log('URLs cached successfully:', urls);
  } catch (error) {
    console.error('Failed to cache URLs:', error);
  }
}

// 处理清理缓存消息
async function handleClearCache() {
  try {
    const cacheNames = await caches.keys();
    const deletePromises = cacheNames.map(cacheName => caches.delete(cacheName));
    await Promise.all(deletePromises);
    console.log('All caches cleared');
  } catch (error) {
    console.error('Failed to clear caches:', error);
  }
}

// 获取缓存统计
async function handleGetCacheStats() {
  try {
    const stats = {
      static: await getCacheStats(STATIC_CACHE_NAME),
      api: await getCacheStats(API_CACHE_NAME),
      images: await getCacheStats(IMAGE_CACHE_NAME),
    };
    
    return stats;
  } catch (error) {
    console.error('Failed to get cache stats:', error);
    return {};
  }
}

// 获取单个缓存的统计信息
async function getCacheStats(cacheName) {
  try {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    
    let totalSize = 0;
    let expiredCount = 0;
    
    for (const request of keys) {
      const response = await cache.match(request);
      if (response) {
        // 估算响应大小
        const text = await response.clone().text();
        totalSize += text.length;
        
        // 检查是否过期
        const ttl = cacheName.includes('static') ? CACHE_TTL.static :
                   cacheName.includes('api') ? CACHE_TTL.api :
                   CACHE_TTL.images;
        
        if (isExpired(response, ttl)) {
          expiredCount++;
        }
      }
    }
    
    return {
      count: keys.length,
      totalSize,
      expiredCount,
      hitRate: 0, // 需要在实际使用中统计
    };
  } catch (error) {
    console.error(`Failed to get stats for cache ${cacheName}:`, error);
    return { count: 0, totalSize: 0, expiredCount: 0, hitRate: 0 };
  }
}

// 定期清理过期缓存
setInterval(async () => {
  try {
    const cacheNames = [STATIC_CACHE_NAME, API_CACHE_NAME, IMAGE_CACHE_NAME];
    
    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      
      const ttl = cacheName.includes('static') ? CACHE_TTL.static :
                 cacheName.includes('api') ? CACHE_TTL.api :
                 CACHE_TTL.images;
      
      for (const request of keys) {
        const response = await cache.match(request);
        if (response && isExpired(response, ttl)) {
          await cache.delete(request);
        }
      }
    }
    
    console.log('Expired cache entries cleaned up');
  } catch (error) {
    console.error('Failed to cleanup expired cache entries:', error);
  }
}, 60 * 60 * 1000); // 每小时清理一次