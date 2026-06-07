/**
 * 实时状态同步Hook
 * 处理前后端数据一致性和状态同步
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { 
  WSMessage, 
  WSMessageType, 
  SyncStatus, 
  ChatMessage, 
  Conversation,
  ConnectionStatus 
} from '../types/ai-assistant';
import { 
  realTimeSyncService, 
  SyncState as ServiceSyncState,
  SyncConflict,
  OptimisticUpdate 
} from '../services/real-time-sync-service';

interface SyncState {
  status: SyncStatus;
  lastSyncTime: string | null;
  pendingOperations: string[];
  conflictedItems: string[];
  isOnline: boolean;
  connectionStatus: ConnectionStatus;
}

interface UseRealTimeSyncOptions {
  conversationId?: number;
  onMessageReceived?: (message: ChatMessage) => void;
  onConversationUpdated?: (conversation: Conversation) => void;
  onSyncStatusChanged?: (status: SyncStatus) => void;
  onConflictDetected?: (conflictId: string, data: any) => void;
  onOptimisticUpdate?: (update: OptimisticUpdate) => void;
  onOptimisticUpdateFailed?: (updateId: string, reason: string) => void;
  onConnectionStatusChange?: (status: ConnectionStatus) => void;
}

interface UseRealTimeSyncReturn {
  syncState: SyncState;
  sendTypingIndicator: (isTyping: boolean) => void;
  markMessageAsRead: (messageId: number) => void;
  syncConversation: (conversationId: number) => void;
  resolveConflict: (conflictId: string, resolution: 'local' | 'remote' | 'merge', mergedData?: any) => void;
  isOnline: boolean;
  // 新增的乐观更新功能
  performOptimisticUpdate: (entity: string, entityId: number | string, updates: any, operation: any) => string;
  rollbackOptimisticUpdate: (updateId: string, reason?: string) => void;
  forcSync: () => void;
  getPendingOperationsCount: () => number;
  getConflictsCount: () => number;
}

export function useRealTimeSync(options: UseRealTimeSyncOptions = {}): UseRealTimeSyncReturn {
  const {
    conversationId,
    onMessageReceived,
    onConversationUpdated,
    onSyncStatusChanged,
    onConflictDetected,
    onOptimisticUpdate,
    onOptimisticUpdateFailed,
    onConnectionStatusChange
  } = options;

  const [syncState, setSyncState] = useState<SyncState>({
    status: 'offline',
    lastSyncTime: null,
    pendingOperations: [],
    conflictedItems: [],
    isOnline: navigator.onLine,
    connectionStatus: 'disconnected'
  });

  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const callbacksRef = useRef({
    onMessageReceived,
    onConversationUpdated,
    onSyncStatusChanged,
    onConflictDetected,
    onOptimisticUpdate,
    onOptimisticUpdateFailed,
    onConnectionStatusChange
  });

  useEffect(() => {
    callbacksRef.current = {
      onMessageReceived,
      onConversationUpdated,
      onSyncStatusChanged,
      onConflictDetected,
      onOptimisticUpdate,
      onOptimisticUpdateFailed,
      onConnectionStatusChange
    };
  }, [
    onMessageReceived,
    onConversationUpdated,
    onSyncStatusChanged,
    onConflictDetected,
    onOptimisticUpdate,
    onOptimisticUpdateFailed,
    onConnectionStatusChange
  ]);

  const { sendMessage, subscribe, isConnected, connectionStatus } = useWebSocket({
    onOpen: () => {
      realTimeSyncService.setConnectionStatus('connected');
    },
    onClose: () => {
      realTimeSyncService.setConnectionStatus('disconnected');
    },
    onMessage: (message) => {
      realTimeSyncService.handleWebSocketMessage(message);
    }
  });

  // 监听同步服务状态变化
  useEffect(() => {
    const handleSyncStateChange = (serviceSyncState: ServiceSyncState) => {
      setSyncState(prev => ({
        ...prev,
        status: serviceSyncState.status,
        lastSyncTime: serviceSyncState.lastSyncTime,
        pendingOperations: serviceSyncState.pendingOperations.map(op => op.id),
        conflictedItems: serviceSyncState.conflicts.map(c => c.id),
        isOnline: serviceSyncState.isOnline,
        connectionStatus: serviceSyncState.connectionStatus
      }));
      
      callbacksRef.current.onSyncStatusChanged?.(serviceSyncState.status);
      callbacksRef.current.onConnectionStatusChange?.(serviceSyncState.connectionStatus);
    };

    const handleOptimisticUpdate = (update: any) => {
      callbacksRef.current.onOptimisticUpdate?.(update);
    };

    const handleOptimisticUpdateFailed = (data: { updateId: string; reason: string }) => {
      callbacksRef.current.onOptimisticUpdateFailed?.(data.updateId, data.reason);
    };

    const handleSyncConflict = (conflict: SyncConflict) => {
      callbacksRef.current.onConflictDetected?.(conflict.id, conflict);
    };

    const handleRemoteMessageReceived = (message: ChatMessage) => {
      if (!conversationId || message.conversation_id === conversationId) {
        callbacksRef.current.onMessageReceived?.(message);
      }
    };

    // 注册事件监听器
    realTimeSyncService.on('syncStateChanged', handleSyncStateChange);
    realTimeSyncService.on('optimisticUpdate', handleOptimisticUpdate);
    realTimeSyncService.on('optimisticUpdateFailed', handleOptimisticUpdateFailed);
    realTimeSyncService.on('syncConflict', handleSyncConflict);
    realTimeSyncService.on('remoteMessageReceived', handleRemoteMessageReceived);

    // 初始化状态
    handleSyncStateChange(realTimeSyncService.getSyncState());

    return () => {
      realTimeSyncService.off('syncStateChanged', handleSyncStateChange);
      realTimeSyncService.off('optimisticUpdate', handleOptimisticUpdate);
      realTimeSyncService.off('optimisticUpdateFailed', handleOptimisticUpdateFailed);
      realTimeSyncService.off('syncConflict', handleSyncConflict);
      realTimeSyncService.off('remoteMessageReceived', handleRemoteMessageReceived);
    };
  }, [conversationId]);

  // 执行乐观更新
  const performOptimisticUpdate = useCallback((
    entity: string,
    entityId: number | string,
    updates: any,
    operation: any
  ): string => {
    return realTimeSyncService.performOptimisticUpdate(entity, entityId, updates, {
      ...operation,
      maxRetries: 3
    });
  }, []);

  // 回滚乐观更新
  const rollbackOptimisticUpdate = useCallback((updateId: string, reason?: string) => {
    realTimeSyncService.rollbackOptimisticUpdate(updateId, reason || '手动回滚');
  }, []);

  // 强制同步
  const forcSync = useCallback(() => {
    realTimeSyncService.forcSync();
  }, []);

  // 获取待处理操作数量
  const getPendingOperationsCount = useCallback(() => {
    return realTimeSyncService.getPendingOperationsCount();
  }, []);

  // 获取冲突数量
  const getConflictsCount = useCallback(() => {
    return realTimeSyncService.getConflictsCount();
  }, []);

  // 发送打字指示器
  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    if (!conversationId || !isConnected) return;

    // 清除之前的定时器
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    const message: WSMessage = {
      type: 'typing',
      conversation_id: conversationId,
      data: { is_typing: isTyping },
      timestamp: new Date().toISOString()
    };

    if (syncState.isOnline) {
      sendMessage(message);
    } else {
      // 离线时不发送打字指示器
    }

    // 如果开始打字，设置自动停止
    if (isTyping) {
      typingTimeoutRef.current = setTimeout(() => {
        sendTypingIndicator(false);
      }, 3000); // 3秒后自动停止打字指示器
    }
  }, [conversationId, isConnected, syncState.isOnline, sendMessage]);

  // 标记消息为已读
  const markMessageAsRead = useCallback((messageId: number) => {
    if (!conversationId) return;

    const operation = {
      type: 'update' as const,
      entity: 'message' as const,
      entityId: messageId,
      data: { read: true, read_at: new Date().toISOString() },
      maxRetries: 3
    };

    // 执行乐观更新
    performOptimisticUpdate('message', messageId, { read: true }, operation);
  }, [conversationId, performOptimisticUpdate]);

  // 同步对话状态
  const syncConversation = useCallback((targetConversationId: number) => {
    if (!isConnected) return;

    sendMessage({
      type: 'status',
      conversation_id: targetConversationId,
      data: { type: 'sync_request' },
      timestamp: new Date().toISOString()
    });
  }, [isConnected, sendMessage]);

  // 解决冲突
  const resolveConflict = useCallback((
    conflictId: string, 
    resolution: 'local' | 'remote' | 'merge',
    mergedData?: any
  ) => {
    realTimeSyncService.resolveConflict(conflictId, resolution, mergedData);
  }, []);

  // 订阅WebSocket消息
  useEffect(() => {
    const unsubscribeMessage = subscribe('message', (message: WSMessage) => {
      if (message.conversation_id === conversationId && message.data) {
        // 处理新消息
        if (message.data.type === 'new_message') {
          callbacksRef.current.onMessageReceived?.(message.data.message);
        }
      }
    });

    const unsubscribeTyping = subscribe('typing', (message: WSMessage) => {
      if (message.conversation_id === conversationId) {
        // 处理打字指示器
        console.log('Typing indicator:', message.data);
      }
    });

    const unsubscribeStatus = subscribe('status', (message: WSMessage) => {
      if (message.data) {
        switch (message.data.type) {
          case 'sync_complete':
            setSyncState(prev => ({
              ...prev,
              status: 'synced',
              lastSyncTime: new Date().toISOString()
            }));
            break;
          
          case 'sync_error':
            setSyncState(prev => ({ ...prev, status: 'error' }));
            break;
          
          case 'conflict_detected':
            setSyncState(prev => ({
              ...prev,
              conflictedItems: [...prev.conflictedItems, message.data.conflict_id]
            }));
            callbacksRef.current.onConflictDetected?.(message.data.conflict_id, message.data);
            break;
        }
      }
    });

    return () => {
      unsubscribeMessage();
      unsubscribeTyping();
      unsubscribeStatus();
    };
  }, [conversationId, subscribe]);

  // 监听同步状态变化
  useEffect(() => {
    callbacksRef.current.onSyncStatusChanged?.(syncState.status);
  }, [syncState.status]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return {
    syncState,
    sendTypingIndicator,
    markMessageAsRead,
    syncConversation,
    resolveConflict,
    isOnline: syncState.isOnline,
    performOptimisticUpdate,
    rollbackOptimisticUpdate,
    forcSync,
    getPendingOperationsCount,
    getConflictsCount
  };
}

/**
 * 简化版实时同步Hook - 仅用于对话
 */
export function useChatSync(conversationId: number) {
  const [typingUsers, setTypingUsers] = useState<number[]>([]);

  const sync = useRealTimeSync({
    conversationId,
    onMessageReceived: (message) => {
      console.log('New message received:', message);
    }
  });

  const { subscribe } = useWebSocket();

  // 监听打字指示器
  useEffect(() => {
    const unsubscribe = subscribe('typing', (message: WSMessage) => {
      if (message.conversation_id === conversationId && message.user_id) {
        if (message.data?.is_typing) {
          setTypingUsers(prev => 
            prev.includes(message.user_id!) ? prev : [...prev, message.user_id!]
          );
        } else {
          setTypingUsers(prev => prev.filter(id => id !== message.user_id));
        }
      }
    });

    return unsubscribe;
  }, [conversationId, subscribe]);

  return {
    ...sync,
    typingUsers
  };
}
