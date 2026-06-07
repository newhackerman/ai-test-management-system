// @ts-nocheck
import { toast } from 'sonner'

import { WebSocketMessage } from './websocket-client'

type NotificationListener = (...args: any[]) => void

class BrowserEventEmitter {
  private listeners: Map<string, Set<NotificationListener>> = new Map()

  on(eventName: string, listener: NotificationListener) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set())
    }
    this.listeners.get(eventName)!.add(listener)
    return this
  }

  off(eventName: string, listener: NotificationListener) {
    this.listeners.get(eventName)?.delete(listener)
    return this
  }

  emit(eventName: string, ...args: any[]) {
    this.listeners.get(eventName)?.forEach((listener) => listener(...args))
    return this
  }
}

export interface RealtimeNotification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  data?: any
  timestamp: string
  read: boolean
  persistent?: boolean
  actions?: NotificationAction[]
}

export interface NotificationAction {
  label: string
  action: () => void
  variant?: 'default' | 'destructive'
}

export interface QueuedMessage {
  id: string
  message: WebSocketMessage
  timestamp: string
  retries: number
  maxRetries: number
  processed: boolean
}

export type MessageHandler = (message: WebSocketMessage) => Promise<void> | void

export class RealtimeNotificationManager extends BrowserEventEmitter {
  private notifications: Map<string, RealtimeNotification> = new Map()
  private messageQueue: Map<string, QueuedMessage> = new Map()
  private messageHandlers: Map<string, MessageHandler[]> = new Map()
  private processingQueue = false

  constructor() {
    super()
    setInterval(() => this.processMessageQueue(), 1000)
  }

  addNotification(notification: Omit<RealtimeNotification, 'id' | 'timestamp' | 'read'>) {
    const id = this.generateId()
    const fullNotification: RealtimeNotification = {
      ...notification,
      id,
      timestamp: new Date().toISOString(),
      read: false,
    }

    this.notifications.set(id, fullNotification)
    this.emit('notification:added', fullNotification)
    this.showToastNotification(fullNotification)
    return id
  }

  markAsRead(id: string) {
    const notification = this.notifications.get(id)
    if (!notification) return
    notification.read = true
    this.notifications.set(id, notification)
    this.emit('notification:read', notification)
  }

  removeNotification(id: string) {
    const notification = this.notifications.get(id)
    if (!notification) return
    this.notifications.delete(id)
    this.emit('notification:removed', notification)
  }

  clearNotifications() {
    this.notifications.clear()
    this.emit('notifications:cleared')
  }

  getNotifications(): RealtimeNotification[] {
    return Array.from(this.notifications.values()).sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    )
  }

  getUnreadCount(): number {
    return Array.from(this.notifications.values()).filter((notification) => !notification.read).length
  }

  handleWebSocketMessage(message: WebSocketMessage) {
    const queueItem: QueuedMessage = {
      id: this.generateId(),
      message,
      timestamp: new Date().toISOString(),
      retries: 0,
      maxRetries: 3,
      processed: false,
    }
    this.messageQueue.set(queueItem.id, queueItem)
    this.processMessageQueue()
  }

  registerMessageHandler(messageType: string, handler: MessageHandler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType)!.push(handler)
  }

  unregisterMessageHandler(messageType: string, handler: MessageHandler) {
    const handlers = this.messageHandlers.get(messageType)
    if (!handlers) return
    this.messageHandlers.set(messageType, handlers.filter((item) => item !== handler))
  }

  private showToastNotification(notification: RealtimeNotification) {
    const options: any = {
      description: notification.message,
      duration: notification.persistent ? 0 : 5000,
    }

    if (notification.actions?.length) {
      options.action = {
        label: notification.actions[0].label,
        onClick: notification.actions[0].action,
      }
    }

    if (notification.type === 'success') toast.success(notification.title, options)
    else if (notification.type === 'warning') toast.warning(notification.title, options)
    else if (notification.type === 'error') toast.error(notification.title, options)
    else toast.info(notification.title, options)
  }

  private async processMessageQueue() {
    if (this.processingQueue) return
    this.processingQueue = true

    try {
      const unprocessedMessages = Array.from(this.messageQueue.values())
        .filter((item) => !item.processed)
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

      for (const queueItem of unprocessedMessages) {
        try {
          await this.processMessage(queueItem)
          queueItem.processed = true
        } catch (error) {
          queueItem.retries += 1
          if (queueItem.retries >= queueItem.maxRetries) {
            console.error('Failed to process message after max retries:', error)
            queueItem.processed = true
          }
        }
      }

      this.cleanupProcessedMessages()
    } finally {
      this.processingQueue = false
    }
  }

  private async processMessage(queueItem: QueuedMessage) {
    const { message } = queueItem

    if (message.type === 'notification') this.handleNotificationMessage(message)
    if (message.type === 'data_update') this.handleDataUpdateMessage(message)
    if (message.type === 'user_message') this.handleUserMessage(message)

    const handlers = this.messageHandlers.get(message.type) || []
    for (const handler of handlers) {
      await handler(message)
    }

    this.emit('message:processed', message)
  }

  private handleNotificationMessage(message: WebSocketMessage) {
    const payload = message.payload || {}
    this.addNotification({
      type: payload.type || 'info',
      title: payload.title || '新通知',
      message: payload.message,
      data: payload.data,
      persistent: payload.persistent,
      actions: payload.actions,
    })
  }

  private handleDataUpdateMessage(message: WebSocketMessage) {
    const payload = message.payload || {}
    this.emit('data:update', {
      type: payload.entityType,
      action: payload.action,
      data: payload.data,
      id: payload.id,
    })

    if (payload.showNotification === false) return

    const actionLabel = payload.action === 'created' ? '新建' : payload.action === 'deleted' ? '删除' : '更新'
    const type = payload.action === 'created' ? 'success' : payload.action === 'deleted' ? 'warning' : 'info'
    this.addNotification({
      type,
      title: `${actionLabel}${payload.entityType || '项目'}`,
      message: payload.message,
      data: payload.data,
    })
  }

  private handleUserMessage(message: WebSocketMessage) {
    const payload = message.payload || {}
    this.addNotification({
      type: 'info',
      title: `来自 ${payload.from || '系统'} 的消息`,
      message: payload.content,
      data: payload,
      actions: payload.actions,
    })
  }

  private cleanupProcessedMessages() {
    const now = Date.now()
    const maxAge = 5 * 60 * 1000

    for (const [id, queueItem] of this.messageQueue.entries()) {
      const age = now - new Date(queueItem.timestamp).getTime()
      if (queueItem.processed && age > maxAge) {
        this.messageQueue.delete(id)
      }
    }
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
  }

  getQueueStats() {
    const messages = Array.from(this.messageQueue.values())
    return {
      total: messages.length,
      processed: messages.filter((message) => message.processed).length,
      pending: messages.filter((message) => !message.processed).length,
      failed: messages.filter((message) => message.retries >= message.maxRetries).length,
    }
  }
}

export const realtimeNotificationManager = new RealtimeNotificationManager()

realtimeNotificationManager.registerMessageHandler('test_result', (message) => {
  const payload = message.payload || {}
  realtimeNotificationManager.addNotification({
    type: payload.status === 'passed' ? 'success' : 'error',
    title: '测试结果',
    message: `测试用例“${payload.testName || ''}”${payload.status === 'passed' ? '通过' : '失败'}`,
    data: payload,
  })
})

realtimeNotificationManager.registerMessageHandler('system_alert', (message) => {
  const payload = message.payload || {}
  realtimeNotificationManager.addNotification({
    type: payload.level || 'warning',
    title: '系统警告',
    message: payload.message,
    persistent: payload.critical,
    data: payload,
  })
})

export default realtimeNotificationManager
