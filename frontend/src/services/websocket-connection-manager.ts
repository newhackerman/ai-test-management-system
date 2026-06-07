/**
 * WebSocket连接管理器
 * 提供企业级WebSocket连接管理、自动重连、消息队列、健康监控等功能
 */

import { EventEmitter } from '../lib/event-emitter';
import { WSMessage, WSMessageType, ConnectionStatus } from '../types/ai-assistant';

export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  connectionTimeout?: number;
  enableCompression?: boolean;
  enableBinaryMessages?: boolean;
}

export interface ConnectionMetrics {
  connectedAt?: Date;
  disconnectedAt?: Date;
  reconnectAttempts: number;
  totalReconnects: number;
  messagesSent: number;
  messagesReceived: number;
  bytesTransferred: number;
  averageLatency: number;
  lastHeartbeat?: Date;
  uptime: number;
}

export interface QueuedMessage extends WSMessage {
  id: string;
  attempts: number;
  queuedAt: Date;
  priority: 'low' | 'normal' | 'high' | 'critical';
}

export class WebSocketConnectionManager extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private connectionStatus: ConnectionStatus = 'disconnected';
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionTimer: NodeJS.Timeout | null = null;
  private messageQueue: QueuedMessage[] = [];
  private metrics: ConnectionMetrics;
  private isManualDisconnect = false;
  private subscribers = new Map<WSMessageType, Set<(message: WSMessage) => void>>();
  private latencyMeasurements: number[] = [];
  private lastPingTime = 0;

  constructor(config: WebSocketConfig) {
    super();
    
    this.config = {
      protocols: [],
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 1000,
      connectionTimeout: 10000,
      enableCompression: true,
      enableBinaryMessages: false,
      ...config
    };

    this.metrics = {
      reconnectAttempts: 0,
      totalReconnects: 0,
      messagesSent: 0,
      messagesReceived: 0,
      bytesTransferred: 0,
      averageLatency: 0,
      uptime: 0
    };

    // 监听页面可见性变化
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }

    // 监听网络状态变化
    if (typeof navigator !== 'undefined' && 'onLine' in navigator) {
      window.addEventListener('online', this.handleNetworkOnline.bind(this));
      window.addEventListener('offline', this.handleNetworkOffline.bind(this));
    }
  }

  /**
   * 连接WebSocket
   */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    this.isManualDisconnect = false;
    this.setConnectionStatus('connecting');
    this.clearTimers();

    return new Promise((resolve, reject) => {
      try {
        console.log(`Connecting to WebSocket: ${this.config.url}`);
        
        this.ws = new WebSocket(this.config.url, this.config.protocols);
        
        // 设置连接超时
        this.connectionTimer = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            this.handleConnectionTimeout();
            reject(new Error('Connection timeout'));
          }
        }, this.config.connectionTimeout);

        this.ws.onopen = (event) => {
          this.clearTimers();
          this.handleConnectionOpen(event);
          resolve();
        };

        this.ws.onclose = (event) => {
          this.clearTimers();
          this.handleConnectionClose(event);
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error(`Connection failed: ${event.code} ${event.reason}`));
          }
        };

        this.ws.onerror = (event) => {
          console.error('WebSocket error:', event);
          this.emit('error', new Error('WebSocket connection error'));
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error('WebSocket connection error'));
          }
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

      } catch (error) {
        this.setConnectionStatus('disconnected');
        this.emit('error', error);
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualDisconnect = true;
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.setConnectionStatus('disconnected');
    this.metrics.disconnectedAt = new Date();
    this.emit('disconnected', { manual: true });
  }

  /**
   * 发送消息
   */
  send(message: Omit<WSMessage, 'timestamp'>): boolean {
    const fullMessage: WSMessage = {
      ...message,
      timestamp: new Date().toISOString()
    };

    if (this.isConnected()) {
      return this.sendImmediate(fullMessage);
    } else {
      this.queueMessage(fullMessage);
      return false;
    }
  }

  /**
   * 订阅消息类型
   */
  subscribe(messageType: WSMessageType, callback: (message: WSMessage) => void): () => void {
    if (!this.subscribers.has(messageType)) {
      this.subscribers.set(messageType, new Set());
    }
    
    const subscribers = this.subscribers.get(messageType)!;
    subscribers.add(callback);

    // 返回取消订阅函数
    return () => {
      subscribers.delete(callback);
      if (subscribers.size === 0) {
        this.subscribers.delete(messageType);
      }
    };
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * 获取连接指标
   */
  getMetrics(): ConnectionMetrics {
    return {
      ...this.metrics,
      uptime: this.metrics.connectedAt 
        ? Date.now() - this.metrics.connectedAt.getTime()
        : 0
    };
  }

  /**
   * 获取消息队列状态
   */
  getQueueStatus(): {
    size: number;
    maxSize: number;
    oldestMessage?: Date;
    newestMessage?: Date;
  } {
    return {
      size: this.messageQueue.length,
      maxSize: this.config.messageQueueSize,
      oldestMessage: this.messageQueue[0]?.queuedAt,
      newestMessage: this.messageQueue[this.messageQueue.length - 1]?.queuedAt
    };
  }

  /**
   * 清空消息队列
   */
  clearQueue(): void {
    this.messageQueue = [];
    this.emit('queueCleared');
  }

  /**
   * 手动重连
   */
  async reconnect(): Promise<void> {
    this.disconnect();
    await new Promise(resolve => setTimeout(resolve, 1000));
    return this.connect();
  }

  /**
   * 检查连接是否正常
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * 销毁连接管理器
   */
  destroy(): void {
    this.disconnect();
    this.clearQueue();
    this.removeAllListeners();
    
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }
    
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleNetworkOnline.bind(this));
      window.removeEventListener('offline', this.handleNetworkOffline.bind(this));
    }
  }

  // ============================================================================
  // 私有方法
  // ============================================================================

  private setConnectionStatus(status: ConnectionStatus): void {
    if (this.connectionStatus !== status) {
      const previousStatus = this.connectionStatus;
      this.connectionStatus = status;
      this.emit('statusChange', { status, previousStatus });
    }
  }

  private handleConnectionOpen(event: Event): void {
    console.log('WebSocket connected successfully');
    
    this.setConnectionStatus('connected');
    this.metrics.connectedAt = new Date();
    this.metrics.reconnectAttempts = 0;
    
    // 开始心跳
    this.startHeartbeat();
    
    // 处理消息队列
    this.processMessageQueue();
    
    this.emit('connected', { event, metrics: this.getMetrics() });
  }

  private handleConnectionClose(event: CloseEvent): void {
    console.log(`WebSocket disconnected: ${event.code} ${event.reason}`);
    
    this.setConnectionStatus('disconnected');
    this.metrics.disconnectedAt = new Date();
    this.clearTimers();
    
    this.emit('disconnected', { 
      event, 
      manual: this.isManualDisconnect,
      metrics: this.getMetrics()
    });

    // 自动重连
    if (!this.isManualDisconnect && this.shouldReconnect(event)) {
      this.scheduleReconnect();
    }
  }

  private handleConnectionTimeout(): void {
    console.warn('WebSocket connection timeout');
    this.setConnectionStatus('disconnected');
    this.emit('timeout');
    
    if (!this.isManualDisconnect) {
      this.scheduleReconnect();
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);
      
      this.metrics.messagesReceived++;
      this.metrics.bytesTransferred += event.data.length;
      
      // 处理心跳响应
      if (message.type === 'status' && message.data?.type === 'pong') {
        this.handlePongMessage(message);
        return;
      }
      
      // 分发消息给订阅者
      this.distributeMessage(message);
      
      this.emit('message', message);
      
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.emit('error', new Error('Message parsing failed'));
    }
  }

  private handlePongMessage(message: WSMessage): void {
    if (this.lastPingTime > 0) {
      const latency = Date.now() - this.lastPingTime;
      this.latencyMeasurements.push(latency);
      
      // 保留最近20次测量
      if (this.latencyMeasurements.length > 20) {
        this.latencyMeasurements.shift();
      }
      
      // 计算平均延迟
      this.metrics.averageLatency = this.latencyMeasurements.reduce((a, b) => a + b, 0) / this.latencyMeasurements.length;
      this.metrics.lastHeartbeat = new Date();
      
      this.emit('heartbeat', { latency, averageLatency: this.metrics.averageLatency });
    }
  }

  private distributeMessage(message: WSMessage): void {
    const subscribers = this.subscribers.get(message.type);
    if (subscribers) {
      subscribers.forEach(callback => {
        try {
          callback(message);
        } catch (error) {
          console.error('Error in message subscriber:', error);
        }
      });
    }
  }

  private sendImmediate(message: WSMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      const data = JSON.stringify(message);
      this.ws.send(data);
      
      this.metrics.messagesSent++;
      this.metrics.bytesTransferred += data.length;
      
      this.emit('messageSent', message);
      return true;
      
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      this.emit('error', new Error('Message sending failed'));
      return false;
    }
  }

  private queueMessage(message: WSMessage, priority: QueuedMessage['priority'] = 'normal'): void {
    const queuedMessage: QueuedMessage = {
      ...message,
      id: this.generateMessageId(),
      attempts: 0,
      queuedAt: new Date(),
      priority
    };

    // 按优先级插入队列
    const insertIndex = this.findInsertIndex(priority);
    this.messageQueue.splice(insertIndex, 0, queuedMessage);

    // 限制队列大小
    if (this.messageQueue.length > this.config.messageQueueSize) {
      const removed = this.messageQueue.splice(0, this.messageQueue.length - this.config.messageQueueSize);
      this.emit('messagesDropped', removed);
    }

    this.emit('messageQueued', queuedMessage);
  }

  private findInsertIndex(priority: QueuedMessage['priority']): number {
    const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
    const targetPriority = priorityOrder[priority];

    for (let i = 0; i < this.messageQueue.length; i++) {
      if (priorityOrder[this.messageQueue[i].priority] > targetPriority) {
        return i;
      }
    }

    return this.messageQueue.length;
  }

  private processMessageQueue(): void {
    if (this.messageQueue.length === 0) return;

    console.log(`Processing ${this.messageQueue.length} queued messages`);
    
    const messagesToSend = [...this.messageQueue];
    this.messageQueue = [];

    let successCount = 0;
    let failureCount = 0;

    for (const queuedMessage of messagesToSend) {
      queuedMessage.attempts++;
      
      if (this.sendImmediate(queuedMessage)) {
        successCount++;
      } else {
        failureCount++;
        // 重新加入队列（如果尝试次数未超限）
        if (queuedMessage.attempts < 3) {
          this.messageQueue.push(queuedMessage);
        }
      }
    }

    this.emit('queueProcessed', { 
      total: messagesToSend.length, 
      success: successCount, 
      failure: failureCount 
    });
  }

  private shouldReconnect(event: CloseEvent): boolean {
    // 正常关闭不重连
    if (event.code === 1000) return false;
    
    // 超过最大重连次数
    if (this.metrics.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.emit('maxReconnectAttemptsReached');
      return false;
    }
    
    return true;
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.setConnectionStatus('reconnecting');
    this.metrics.reconnectAttempts++;
    this.metrics.totalReconnects++;

    // 指数退避算法
    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.metrics.reconnectAttempts - 1),
      30000 // 最大30秒
    );

    console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.metrics.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnect failed:', error);
        this.emit('reconnectFailed', { error, attempt: this.metrics.reconnectAttempts });
      });
    }, delay);

    this.emit('reconnectScheduled', { delay, attempt: this.metrics.reconnectAttempts });
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.sendHeartbeat();
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private sendHeartbeat(): void {
    this.lastPingTime = Date.now();
    
    const heartbeatMessage: WSMessage = {
      type: 'status',
      data: { type: 'ping', timestamp: this.lastPingTime },
      timestamp: new Date().toISOString()
    };

    this.sendImmediate(heartbeatMessage);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
    
    this.stopHeartbeat();
  }

  private handleVisibilityChange(): void {
    if (document.hidden) {
      // 页面隐藏时降低心跳频率
      this.stopHeartbeat();
    } else {
      // 页面显示时恢复心跳并检查连接
      if (this.isConnected()) {
        this.startHeartbeat();
        this.sendHeartbeat(); // 立即发送一次心跳
      } else if (!this.isManualDisconnect) {
        // 如果连接断开且非手动断开，尝试重连
        this.connect().catch(console.error);
      }
    }
  }

  private handleNetworkOnline(): void {
    console.log('Network is back online');
    this.emit('networkOnline');
    
    if (!this.isConnected() && !this.isManualDisconnect) {
      this.connect().catch(console.error);
    }
  }

  private handleNetworkOffline(): void {
    console.log('Network went offline');
    this.emit('networkOffline');
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * WebSocket连接管理器工厂函数
 */
export function createWebSocketManager(config: WebSocketConfig): WebSocketConnectionManager {
  return new WebSocketConnectionManager(config);
}

/**
 * 默认配置
 */
export const defaultWebSocketConfig: Partial<WebSocketConfig> = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 1000,
  connectionTimeout: 10000,
  enableCompression: true,
  enableBinaryMessages: false
};
