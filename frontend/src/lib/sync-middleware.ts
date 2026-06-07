/**
 * 统一的状态同步中间件
 * 处理前后端数据一致性和冲突解决
 */

import { EventEmitter } from './event-emitter';
import { apiClient } from './api-client';
import { websocketClient } from './websocket-client';

export interface DataVersion {
  entityType: string;
  entityId: number | string;
  version: number;
  lastModified: string;
  checksum: string;
}

export enum ConflictResolution {
  SERVER_WINS = 'server_wins',
  CLIENT_WINS = 'client_wins',
  MERGE = 'merge',
  MANUAL = 'manual'
}

export interface ConflictItem {
  id: string;
  entityType: string;
  entityId: number | string;
  localData: any;
  remoteData: any;
  conflictType: 'version' | 'concurrent_edit' | 'deleted';
  timestamp: string;
}

export interface Operation {
  id: string;
  type: 'create' | 'update' | 'delete';
  entityType: string;
  entityId: number | string;
  data: any;
  timestamp: string;
  retryCount: number;
  maxRetries: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface SyncState {
  pendingOperations: Operation[];
  conflictedItems: ConflictItem[];
  lastSyncTimestamp: string;
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  isOnline: boolean;
  syncInProgress: boolean;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

class SyncMiddleware extends EventEmitter {
  private syncState: SyncState = {
    pendingOperations: [],
    conflictedItems: [],
    lastSyncTimestamp: '',
    connectionStatus: 'disconnected',
    isOnline: navigator.onLine,
    syncInProgress: false
  };

  private versionCache = new Map<string, DataVersion>();
  private syncTimer: NodeJS.Timeout | null = null;
  private retryTimer: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.setupEventListeners();
    this.startPeriodicSync();
  }

  private setupEventListeners() {
    // 监听网络状态变化
    window.addEventListener('online', () => {
      this.syncState.isOnline = true;
      this.emit('networkStatusChanged', true);
      this.processPendingOperations();
    });

    window.addEventListener('offline', () => {
      this.syncState.isOnline = false;
      this.emit('networkStatusChanged', false);
    });

    // 监听WebSocket连接状态
    websocketClient.on('connected', () => {
      this.syncState.connectionStatus = 'connected';
      this.emit('connectionStatusChanged', 'connected');
      this.processPendingOperations();
    });

    websocketClient.on('disconnected', () => {
      this.syncState.connectionStatus = 'disconnected';
      this.emit('connectionStatusChanged', 'disconnected');
    });

    websocketClient.on('reconnecting', () => {
      this.syncState.connectionStatus = 'reconnecting';
      this.emit('connectionStatusChanged', 'reconnecting');
    });

    // 监听服务器推送的数据更新
    websocketClient.on('data_updated', (data) => {
      this.handleRemoteDataUpdate(data);
    });
  }

  private startPeriodicSync() {
    // 每30秒进行一次同步检查
    this.syncTimer = setInterval(() => {
      if (this.syncState.isOnline && this.syncState.connectionStatus === 'connected') {
        this.syncWithServer();
      }
    }, 30000);
  }

  /**
   * 添加操作到队列
   */
  public queueOperation(operation: Omit<Operation, 'id' | 'timestamp' | 'retryCount' | 'status'>): string {
    const operationId = `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const fullOperation: Operation = {
      ...operation,
      id: operationId,
      timestamp: new Date().toISOString(),
      retryCount: 0,
      status: 'pending'
    };

    this.syncState.pendingOperations.push(fullOperation);
    this.emit('operationQueued', fullOperation);

    // 如果在线，立即尝试处理
    if (this.syncState.isOnline && this.syncState.connectionStatus === 'connected') {
      this.processPendingOperations();
    }

    return operationId;
  }

  /**
   * 处理待处理的操作
   */
  private async processPendingOperations() {
    if (this.syncState.syncInProgress || this.syncState.pendingOperations.length === 0) {
      return;
    }

    this.syncState.syncInProgress = true;
    this.emit('syncStarted');

    const operations = [...this.syncState.pendingOperations];
    
    for (const operation of operations) {
      if (operation.status === 'pending' || operation.status === 'failed') {
        await this.processOperation(operation);
      }
    }

    this.syncState.syncInProgress = false;
    this.emit('syncCompleted');

    // 如果还有失败的操作，安排重试
    this.scheduleRetry();
  }

  /**
   * 处理单个操作
   */
  private async processOperation(operation: Operation): Promise<void> {
    try {
      operation.status = 'processing';
      this.emit('operationProcessing', operation);

      let response;
      const endpoint = this.getEndpoint(operation.entityType, operation.entityId);

      switch (operation.type) {
        case 'create':
          response = await apiClient.post(endpoint, operation.data);
          break;
        case 'update':
          response = await apiClient.patch(endpoint, operation.data);
          break;
        case 'delete':
          response = await apiClient.delete(endpoint);
          break;
      }

      if (response.data.success) {
        // 操作成功，从队列中移除
        this.removeOperation(operation.id);
        operation.status = 'completed';
        this.emit('operationCompleted', operation);

        // 更新版本信息
        if (response.data.data && response.data.data.version) {
          this.updateVersionCache(operation.entityType, operation.entityId, response.data.data);
        }
      } else {
        throw new Error(response.data.message || '操作失败');
      }
    } catch (error) {
      operation.retryCount++;
      
      if (operation.retryCount >= operation.maxRetries) {
        operation.status = 'failed';
        this.emit('operationFailed', operation, error);
      } else {
        operation.status = 'pending';
        this.emit('operationRetry', operation, error);
      }
    }
  }

  /**
   * 处理远程数据更新
   */
  private handleRemoteDataUpdate(data: any) {
    const { entityType, entityId, version, lastModified } = data;
    const cacheKey = `${entityType}:${entityId}`;
    const cachedVersion = this.versionCache.get(cacheKey);

    if (cachedVersion && cachedVersion.version !== version) {
      // 检测到版本冲突
      this.detectConflict(entityType, entityId, data, cachedVersion);
    } else {
      // 正常更新
      this.updateVersionCache(entityType, entityId, data);
      this.emit('remoteDataUpdated', data);
    }
  }

  /**
   * 检测并处理冲突
   */
  private detectConflict(entityType: string, entityId: number | string, remoteData: any, localVersion: DataVersion) {
    const conflictId = `conflict_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const conflict: ConflictItem = {
      id: conflictId,
      entityType,
      entityId,
      localData: localVersion,
      remoteData,
      conflictType: 'version',
      timestamp: new Date().toISOString()
    };

    this.syncState.conflictedItems.push(conflict);
    this.emit('conflictDetected', conflict);
  }

  /**
   * 解决冲突
   */
  public resolveConflict(
    conflictId: string, 
    resolution: ConflictResolution, 
    mergedData?: any
  ): void {
    const conflictIndex = this.syncState.conflictedItems.findIndex(c => c.id === conflictId);
    if (conflictIndex === -1) return;

    const conflict = this.syncState.conflictedItems[conflictIndex];
    let resolvedData: any;

    switch (resolution) {
      case ConflictResolution.SERVER_WINS:
        resolvedData = conflict.remoteData;
        break;
      case ConflictResolution.CLIENT_WINS:
        resolvedData = conflict.localData;
        break;
      case ConflictResolution.MERGE:
        resolvedData = mergedData || { ...conflict.localData, ...conflict.remoteData };
        break;
      case ConflictResolution.MANUAL:
        resolvedData = mergedData;
        break;
    }

    // 更新版本缓存
    this.updateVersionCache(conflict.entityType, conflict.entityId, resolvedData);

    // 从冲突列表中移除
    this.syncState.conflictedItems.splice(conflictIndex, 1);

    this.emit('conflictResolved', conflict, resolution, resolvedData);
  }

  /**
   * 与服务器同步
   */
  private async syncWithServer(): Promise<void> {
    try {
      const response = await apiClient.get('/api/v1/sync/status', {
        params: {
          last_sync: this.syncState.lastSyncTimestamp
        }
      });

      if (response.data.success && response.data.data) {
        const { updates, timestamp } = response.data.data;
        
        // 处理服务器更新
        for (const update of updates) {
          this.handleRemoteDataUpdate(update);
        }

        this.syncState.lastSyncTimestamp = timestamp;
        this.emit('syncCompleted');
      }
    } catch (error) {
      this.emit('syncError', error);
    }
  }

  /**
   * 强制同步
   */
  public async forceSync(): Promise<void> {
    await this.syncWithServer();
    await this.processPendingOperations();
  }

  /**
   * 更新版本缓存
   */
  private updateVersionCache(entityType: string, entityId: number | string, data: any): void {
    const cacheKey = `${entityType}:${entityId}`;
    const version: DataVersion = {
      entityType,
      entityId,
      version: data.version || 1,
      lastModified: data.updated_at || new Date().toISOString(),
      checksum: this.calculateChecksum(data)
    };

    this.versionCache.set(cacheKey, version);
  }

  /**
   * 计算数据校验和
   */
  private calculateChecksum(data: any): string {
    const str = JSON.stringify(data, Object.keys(data).sort());
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(36);
  }

  /**
   * 获取API端点
   */
  private getEndpoint(entityType: string, entityId: number | string): string {
    const endpoints: Record<string, string> = {
      conversation: `/api/v1/ai-assistant/conversations/${entityId}`,
      message: `/api/v1/ai-assistant/messages/${entityId}`,
      suggestion: `/api/v1/ai-assistant/suggestions/${entityId}`,
      analysis: `/api/v1/ai-assistant/analysis/${entityId}`
    };

    return endpoints[entityType] || `/api/v1/${entityType}/${entityId}`;
  }

  /**
   * 从队列中移除操作
   */
  private removeOperation(operationId: string): void {
    const index = this.syncState.pendingOperations.findIndex(op => op.id === operationId);
    if (index !== -1) {
      this.syncState.pendingOperations.splice(index, 1);
    }
  }

  /**
   * 安排重试
   */
  private scheduleRetry(): void {
    const failedOperations = this.syncState.pendingOperations.filter(
      op => op.status === 'failed' && op.retryCount < op.maxRetries
    );

    if (failedOperations.length > 0 && !this.retryTimer) {
      this.retryTimer = setTimeout(() => {
        this.retryTimer = null;
        this.processPendingOperations();
      }, 5000); // 5秒后重试
    }
  }

  /**
   * 获取同步状态
   */
  public getSyncState(): SyncState {
    return { ...this.syncState };
  }

  /**
   * 获取待处理操作数量
   */
  public getPendingOperationsCount(): number {
    return this.syncState.pendingOperations.length;
  }

  /**
   * 获取冲突数量
   */
  public getConflictsCount(): number {
    return this.syncState.conflictedItems.length;
  }

  /**
   * 清理资源
   */
  public destroy(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }

    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }

    this.removeAllListeners();
  }
}

// 创建全局实例
export const syncMiddleware = new SyncMiddleware();
