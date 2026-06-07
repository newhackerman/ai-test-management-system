import { EventEmitter } from './event-emitter'

/**
 * WebSocket客户端类
 * 提供企业级的WebSocket连接管理、自动重连、消息队列等功能
 */

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

export interface WebSocketMessage {
  type: string
  payload: any
  timestamp: string
  id?: string
}

export interface WebSocketConfig {
  url: string
  protocols?: string[]
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
  messageQueueSize?: number
  timeout?: number
}

export interface WebSocketEventHandlers {
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onMessage?: (message: WebSocketMessage) => void
  onStateChange?: (state: ConnectionState) => void
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private handlers: WebSocketEventHandlers = {}
  private messageQueue: WebSocketMessage[] = []
  private reconnectTimer: NodeJS.Timeout | null = null
  private heartbeatTimer: NodeJS.Timeout | null = null
  private reconnectAttempts = 0
  private state: ConnectionState = 'disconnected'
  private lastError: string | null = null

  constructor(config: WebSocketConfig) {
    this.config = {
      protocols: [],
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      timeout: 10000,
      ...config
    }
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.setState('connecting')
      this.lastError = null

      try {
        this.ws = new WebSocket(this.config.url, this.config.protocols)
        
        const timeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close()
            this.setState('error')
            this.lastError = 'Connection timeout'
            reject(new Error('WebSocket connection timeout'))
          }
        }, this.config.timeout)

        this.ws.onopen = (event) => {
          clearTimeout(timeout)
          this.setState('connected')
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.processMessageQueue()
          
          if (this.handlers.onOpen) {
            this.handlers.onOpen(event)
          }
          
          resolve()
        }

        this.ws.onclose = (event) => {
          clearTimeout(timeout)
          this.stopHeartbeat()
          
          if (this.state !== 'disconnected') {
            this.setState('disconnected')
          }
          
          if (this.handlers.onClose) {
            this.handlers.onClose(event)
          }

          // 自动重连
          if (!event.wasClean && this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (event) => {
          clearTimeout(timeout)
          this.setState('error')
          this.lastError = 'WebSocket error occurred'
          
          if (this.handlers.onError) {
            this.handlers.onError(event)
          }
          
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error('WebSocket connection failed'))
          }
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            
            if (this.handlers.onMessage) {
              this.handlers.onMessage(message)
            }
          } catch (error) {
            console.warn('Failed to parse WebSocket message:', error)
          }
        }

      } catch (error) {
        this.setState('error')
        this.lastError = error instanceof Error ? error.message : 'Unknown error'
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopReconnect()
    this.stopHeartbeat()
    
    if (this.ws) {
      this.setState('disconnected')
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  /**
   * 发送消息
   */
  send(message: Omit<WebSocketMessage, 'timestamp' | 'id'>): boolean {
    const fullMessage: WebSocketMessage = {
      ...message,
      timestamp: new Date().toISOString(),
      id: this.generateMessageId()
    }

    if (this.isConnected()) {
      try {
        this.ws!.send(JSON.stringify(fullMessage))
        return true
      } catch (error) {
        console.error('Failed to send WebSocket message:', error)
        this.queueMessage(fullMessage)
        return false
      }
    } else {
      this.queueMessage(fullMessage)
      return false
    }
  }

  /**
   * 设置事件处理器
   */
  setHandlers(handlers: WebSocketEventHandlers): void {
    this.handlers = { ...this.handlers, ...handlers }
  }

  /**
   * 获取连接状态
   */
  getState(): ConnectionState {
    return this.state
  }

  /**
   * 获取最后的错误
   */
  getLastError(): string | null {
    return this.lastError
  }

  /**
   * 获取重连尝试次数
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 手动重连
   */
  async reconnect(): Promise<void> {
    this.disconnect()
    await new Promise(resolve => setTimeout(resolve, 1000))
    return this.connect()
  }

  /**
   * 设置连接状态
   */
  private setState(state: ConnectionState): void {
    if (this.state !== state) {
      this.state = state
      if (this.handlers.onStateChange) {
        this.handlers.onStateChange(state)
      }
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.setState('reconnecting')
    this.reconnectAttempts++

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000
    )

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {
        // 重连失败，会触发下一次重连或放弃
      })
    }, delay)
  }

  /**
   * 停止重连
   */
  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 开始心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'ping',
          payload: { timestamp: Date.now() }
        })
      }
    }, this.config.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 将消息加入队列
   */
  private queueMessage(message: WebSocketMessage): void {
    this.messageQueue.push(message)
    
    // 限制队列大小
    if (this.messageQueue.length > this.config.messageQueueSize) {
      this.messageQueue.shift()
    }
  }

  /**
   * 处理消息队列
   */
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift()!
      try {
        this.ws!.send(JSON.stringify(message))
      } catch (error) {
        console.error('Failed to send queued message:', error)
        // 重新加入队列头部
        this.messageQueue.unshift(message)
        break
      }
    }
  }

  /**
   * 生成消息ID
   */
  private generateMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 销毁客户端
   */
  destroy(): void {
    this.disconnect()
    this.messageQueue = []
    this.handlers = {}
  }
}

export default WebSocketClient

export const websocketClient = new EventEmitter()
