// @ts-nocheck
/**
 * Service Worker 娉ㄥ唽鍜岀鐞嗗伐鍏?
 */

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(
    /^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/
  )
)

interface ServiceWorkerConfig {
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  onOfflineReady?: () => void
}

/**
 * 娉ㄥ唽 Service Worker
 */
export function registerSW(config?: ServiceWorkerConfig) {
  if ('serviceWorker' in navigator) {
    const publicUrl = new URL(process.env.PUBLIC_URL || '', window.location.href)
    if (publicUrl.origin !== window.location.origin) {
      return
    }

    window.addEventListener('load', () => {
      const swUrl = `${process.env.PUBLIC_URL}/sw.js`

      if (isLocalhost) {
        checkValidServiceWorker(swUrl, config)
        navigator.serviceWorker.ready.then(() => {
          console.log(
            'This web app is being served cache-first by a service ' +
            'worker. To learn more, visit https://cra.link/PWA'
          )
        })
      } else {
        registerValidSW(swUrl, config)
      }
    })
  }
}

/**
 * 娉ㄥ唽鏈夋晥鐨?Service Worker
 */
function registerValidSW(swUrl: string, config?: ServiceWorkerConfig) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      console.log('Service Worker registered successfully:', registration)
      
      registration.onupdatefound = () => {
        const installingWorker = registration.installing
        if (installingWorker == null) {
          return
        }

        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              console.log(
                'New content is available and will be used when all ' +
                'tabs for this page are closed. See https://cra.link/PWA.'
              )

              if (config && config.onUpdate) {
                config.onUpdate(registration)
              }
            } else {
              console.log('Content is cached for offline use.')

              if (config && config.onSuccess) {
                config.onSuccess(registration)
              }

              if (config && config.onOfflineReady) {
                config.onOfflineReady()
              }
            }
          }
        }
      }
    })
    .catch((error) => {
      console.error('Error during service worker registration:', error)
    })
}

/**
 * 妫€鏌ユ湁鏁堢殑 Service Worker
 */
function checkValidServiceWorker(swUrl: string, config?: ServiceWorkerConfig) {
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' }
  })
    .then((response) => {
      const contentType = response.headers.get('content-type')
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload()
          })
        })
      } else {
        registerValidSW(swUrl, config)
      }
    })
    .catch(() => {
      console.log(
        'No internet connection found. App is running in offline mode.'
      )
    })
}

/**
 * 娉ㄩ攢 Service Worker
 */
export function unregisterSW() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister()
      })
      .catch((error) => {
        console.error(error.message)
      })
  }
}

/**
 * 鏇存柊 Service Worker
 */
export function updateSW() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.update()
      })
      .catch((error) => {
        console.error('Error updating service worker:', error)
      })
  }
}

/**
 * 璺宠繃绛夊緟骞舵縺娲绘柊鐨?Service Worker
 */
export function skipWaitingAndReload() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        if (registration.waiting) {
          registration.waiting.postMessage({ type: 'SKIP_WAITING' })
          window.location.reload()
        }
      })
  }
}

/**
 * 鐩戝惉 Service Worker 娑堟伅
 */
export function listenForSWMessages(callback: (message: any) => void) {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      callback(event.data)
    })
  }
}

/**
 * 鍚?Service Worker 鍙戦€佹秷鎭?
 */
export function sendMessageToSW(message: any) {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage(message)
  }
}

/**
 * 璇锋眰鍚庡彴鍚屾
 */
export function requestBackgroundSync(tag: string) {
  if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
    navigator.serviceWorker.ready
      .then((registration) => {
        return registration.sync.register(tag)
      })
      .then(() => {
        console.log('Background sync registered:', tag)
      })
      .catch((error) => {
        console.error('Background sync registration failed:', error)
      })
  }
}

/**
 * 妫€鏌ユ槸鍚︽敮鎸佸悗鍙板悓姝?
 */
export function isBackgroundSyncSupported(): boolean {
  return 'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype
}

/**
 * 妫€鏌ユ槸鍚︽敮鎸佹帹閫侀€氱煡
 */
export function isPushNotificationSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window
}

/**
 * 璇锋眰鎺ㄩ€侀€氱煡鏉冮檺
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!('Notification' in window)) {
    throw new Error('This browser does not support notifications')
  }

  if (Notification.permission === 'granted') {
    return 'granted'
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission()
    return permission
  }

  return Notification.permission
}

/**
 * 璁㈤槄鎺ㄩ€侀€氱煡
 */
export async function subscribeToPushNotifications(vapidPublicKey: string) {
  if (!isPushNotificationSupported()) {
    throw new Error('Push notifications are not supported')
  }

  const permission = await requestNotificationPermission()
  if (permission !== 'granted') {
    throw new Error('Notification permission denied')
  }

  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
  })

  return subscription
}

/**
 * 鍙栨秷鎺ㄩ€侀€氱煡璁㈤槄
 */
export async function unsubscribeFromPushNotifications() {
  if (!isPushNotificationSupported()) {
    return
  }

  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.getSubscription()
  
  if (subscription) {
    await subscription.unsubscribe()
  }
}

/**
 * 鑾峰彇褰撳墠鎺ㄩ€佽闃?
 */
export async function getPushSubscription() {
  if (!isPushNotificationSupported()) {
    return null
  }

  const registration = await navigator.serviceWorker.ready
  return registration.pushManager.getSubscription()
}

/**
 * 宸ュ叿鍑芥暟锛氬皢 VAPID 鍏挜杞崲涓?Uint8Array
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

/**
 * 鏄剧ず鏈湴閫氱煡
 */
export function showLocalNotification(title: string, options?: NotificationOptions) {
  if ('Notification' in window && Notification.permission === 'granted') {
    return new Notification(title, options)
  }
}

/**
 * Service Worker 鐘舵€佺鐞嗙被
 */
export class ServiceWorkerManager {
  private registration: ServiceWorkerRegistration | null = null
  private updateAvailable = false
  private callbacks: {
    onUpdate?: () => void
    onOfflineReady?: () => void
    onMessage?: (message: any) => void
  } = {}

  constructor() {
    this.init()
  }

  private async init() {
    if ('serviceWorker' in navigator) {
      try {
        this.registration = await navigator.serviceWorker.ready
        this.setupMessageListener()
        this.checkForUpdates()
      } catch (error) {
        console.error('Service Worker initialization failed:', error)
      }
    }
  }

  private setupMessageListener() {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (this.callbacks.onMessage) {
        this.callbacks.onMessage(event.data)
      }

      // Handle specific message types
      switch (event.data.type) {
        case 'SW_UPDATE_AVAILABLE':
          this.updateAvailable = true
          if (this.callbacks.onUpdate) {
            this.callbacks.onUpdate()
          }
          break
        case 'SW_OFFLINE_READY':
          if (this.callbacks.onOfflineReady) {
            this.callbacks.onOfflineReady()
          }
          break
      }
    })
  }

  private checkForUpdates() {
    if (this.registration) {
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.updateAvailable = true
              if (this.callbacks.onUpdate) {
                this.callbacks.onUpdate()
              }
            }
          })
        }
      })
    }
  }

  public onUpdate(callback: () => void) {
    this.callbacks.onUpdate = callback
  }

  public onOfflineReady(callback: () => void) {
    this.callbacks.onOfflineReady = callback
  }

  public onMessage(callback: (message: any) => void) {
    this.callbacks.onMessage = callback
  }

  public async applyUpdate() {
    if (this.updateAvailable && this.registration?.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      window.location.reload()
    }
  }

  public async requestSync(tag: string) {
    if (this.registration && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        await this.registration.sync.register(tag)
        console.log('Background sync requested:', tag)
      } catch (error) {
        console.error('Background sync request failed:', error)
      }
    }
  }

  public sendMessage(message: any) {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage(message)
    }
  }

  public get isUpdateAvailable(): boolean {
    return this.updateAvailable
  }

  public get isRegistered(): boolean {
    return this.registration !== null
  }
}

// 鍒涘缓鍏ㄥ眬瀹炰緥
export const swManager = new ServiceWorkerManager()

export default {
  registerSW,
  unregisterSW,
  updateSW,
  skipWaitingAndReload,
  listenForSWMessages,
  sendMessageToSW,
  requestBackgroundSync,
  isBackgroundSyncSupported,
  isPushNotificationSupported,
  requestNotificationPermission,
  subscribeToPushNotifications,
  unsubscribeFromPushNotifications,
  getPushSubscription,
  showLocalNotification,
  ServiceWorkerManager,
  swManager
}