// @ts-nocheck
/**
 * 绂荤嚎鏁版嵁缂撳瓨绠＄悊鍣?
 * 澶勭悊绂荤嚎鐘舵€佷笅鐨勬暟鎹紦瀛樺拰鍚屾
 */

import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface CacheSchema extends DBSchema {
  entities: {
    key: string; // entityType:entityId
    value: {
      id: string;
      entityType: string;
      entityId: number | string;
      data: any;
      version: number;
      lastModified: string;
      lastAccessed: string;
      syncStatus: 'synced' | 'pending' | 'conflict';
    };
  };
  operations: {
    key: string; // operation id
    value: {
      id: string;
      type: 'create' | 'update' | 'delete';
      entityType: string;
      entityId: number | string;
      data: any;
      timestamp: string;
      retryCount: number;
      maxRetries: number;
      status: 'pending' | 'processing' | 'completed' | 'failed';
    };
  };
  metadata: {
    key: string;
    value: {
      key: string;
      value: any;
      timestamp: string;
    };
  };
}

class OfflineCacheManager {
  private db: IDBPDatabase<CacheSchema> | null = null;
  private readonly DB_NAME = 'ai-assistant-cache';
  private readonly DB_VERSION = 1;

  async initialize(): Promise<void> {
    if (this.db) return;

    this.db = await openDB<CacheSchema>(this.DB_NAME, this.DB_VERSION, {
      upgrade(db) {
        // 瀹炰綋缂撳瓨瀛樺偍
        if (!db.objectStoreNames.contains('entities')) {
          const entityStore = db.createObjectStore('entities', { keyPath: 'id' });
          entityStore.createIndex('entityType', 'entityType');
          entityStore.createIndex('syncStatus', 'syncStatus');
          entityStore.createIndex('lastModified', 'lastModified');
        }

        // 鎿嶄綔闃熷垪瀛樺偍
        if (!db.objectStoreNames.contains('operations')) {
          const operationStore = db.createObjectStore('operations', { keyPath: 'id' });
          operationStore.createIndex('status', 'status');
          operationStore.createIndex('entityType', 'entityType');
          operationStore.createIndex('timestamp', 'timestamp');
        }

        // 鍏冩暟鎹瓨鍌?
        if (!db.objectStoreNames.contains('metadata')) {
          db.createObjectStore('metadata', { keyPath: 'key' });
        }
      },
    });
  }

  /**
   * 缂撳瓨瀹炰綋鏁版嵁
   */
  async cacheEntity(
    entityType: string,
    entityId: number | string,
    data: any,
    version: number = 1
  ): Promise<void> {
    if (!this.db) await this.initialize();

    const cacheKey = `${entityType}:${entityId}`;
    const now = new Date().toISOString();

    await this.db!.put('entities', {
      id: cacheKey,
      entityType,
      entityId,
      data,
      version,
      lastModified: data.updated_at || now,
      lastAccessed: now,
      syncStatus: 'synced'
    });
  }

  /**
   * 鑾峰彇缂撳瓨鐨勫疄浣撴暟鎹?
   */
  async getCachedEntity(
    entityType: string,
    entityId: number | string
  ): Promise<any | null> {
    if (!this.db) await this.initialize();

    const cacheKey = `${entityType}:${entityId}`;
    const cached = await this.db!.get('entities', cacheKey);

    if (cached) {
      // 鏇存柊鏈€鍚庤闂椂闂?
      cached.lastAccessed = new Date().toISOString();
      await this.db!.put('entities', cached);
      return cached.data;
    }

    return null;
  }

  /**
   * 鑾峰彇鎸囧畾绫诲瀷鐨勬墍鏈夌紦瀛樺疄浣?
   */
  async getCachedEntitiesByType(entityType: string): Promise<any[]> {
    if (!this.db) await this.initialize();

    const entities = await this.db!.getAllFromIndex('entities', 'entityType', entityType);
    return entities.map(entity => entity.data);
  }

  /**
   * 鏍囪瀹炰綋涓哄緟鍚屾鐘舵€?
   */
  async markEntityAsPending(
    entityType: string,
    entityId: number | string,
    updatedData: any
  ): Promise<void> {
    if (!this.db) await this.initialize();

    const cacheKey = `${entityType}:${entityId}`;
    const cached = await this.db!.get('entities', cacheKey);

    if (cached) {
      cached.data = { ...cached.data, ...updatedData };
      cached.syncStatus = 'pending';
      cached.lastModified = new Date().toISOString();
      await this.db!.put('entities', cached);
    } else {
      // 鍒涘缓鏂扮殑缂撳瓨鏉＄洰
      await this.cacheEntity(entityType, entityId, updatedData);
      await this.markEntityAsPending(entityType, entityId, updatedData);
    }
  }

  /**
   * 缂撳瓨鎿嶄綔鍒伴槦鍒?
   */
  async cacheOperation(operation: {
    id: string;
    type: 'create' | 'update' | 'delete';
    entityType: string;
    entityId: number | string;
    data: any;
    maxRetries?: number;
  }): Promise<void> {
    if (!this.db) await this.initialize();

    await this.db!.put('operations', {
      ...operation,
      timestamp: new Date().toISOString(),
      retryCount: 0,
      maxRetries: operation.maxRetries || 3,
      status: 'pending'
    });
  }

  /**
   * 鑾峰彇寰呭鐞嗙殑鎿嶄綔
   */
  async getPendingOperations(): Promise<any[]> {
    if (!this.db) await this.initialize();

    return await this.db!.getAllFromIndex('operations', 'status', 'pending');
  }

  /**
   * 鏇存柊鎿嶄綔鐘舵€?
   */
  async updateOperationStatus(
    operationId: string,
    status: 'pending' | 'processing' | 'completed' | 'failed',
    retryCount?: number
  ): Promise<void> {
    if (!this.db) await this.initialize();

    const operation = await this.db!.get('operations', operationId);
    if (operation) {
      operation.status = status;
      if (retryCount !== undefined) {
        operation.retryCount = retryCount;
      }
      await this.db!.put('operations', operation);
    }
  }

  /**
   * 鍒犻櫎宸插畬鎴愮殑鎿嶄綔
   */
  async removeCompletedOperations(): Promise<void> {
    if (!this.db) await this.initialize();

    const completedOperations = await this.db!.getAllFromIndex('operations', 'status', 'completed');
    const tx = this.db!.transaction('operations', 'readwrite');
    
    for (const operation of completedOperations) {
      await tx.store.delete(operation.id);
    }
    
    await tx.done;
  }

  /**
   * 娓呯悊杩囨湡鐨勭紦瀛樻暟鎹?
   */
  async cleanupExpiredCache(maxAge: number = 7 * 24 * 60 * 60 * 1000): Promise<void> {
    if (!this.db) await this.initialize();

    const cutoffTime = new Date(Date.now() - maxAge).toISOString();
    const tx = this.db!.transaction('entities', 'readwrite');
    const store = tx.store;
    
    let cursor = await store.openCursor();
    
    while (cursor) {
      const entity = cursor.value;
      if (entity.lastAccessed < cutoffTime && entity.syncStatus === 'synced') {
        await cursor.delete();
      }
      cursor = await cursor.continue();
    }
    
    await tx.done;
  }

  /**
   * 鑾峰彇缂撳瓨缁熻淇℃伅
   */
  async getCacheStats(): Promise<{
    totalEntities: number;
    pendingOperations: number;
    syncedEntities: number;
    pendingEntities: number;
    conflictEntities: number;
  }> {
    if (!this.db) await this.initialize();

    const [
      totalEntities,
      pendingOperations,
      syncedEntities,
      pendingEntities,
      conflictEntities
    ] = await Promise.all([
      this.db!.count('entities'),
      this.db!.countFromIndex('operations', 'status', 'pending'),
      this.db!.countFromIndex('entities', 'syncStatus', 'synced'),
      this.db!.countFromIndex('entities', 'syncStatus', 'pending'),
      this.db!.countFromIndex('entities', 'syncStatus', 'conflict')
    ]);

    return {
      totalEntities,
      pendingOperations,
      syncedEntities,
      pendingEntities,
      conflictEntities
    };
  }

  /**
   * 瀛樺偍鍏冩暟鎹?
   */
  async setMetadata(key: string, value: any): Promise<void> {
    if (!this.db) await this.initialize();

    await this.db!.put('metadata', {
      key,
      value,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * 鑾峰彇鍏冩暟鎹?
   */
  async getMetadata(key: string): Promise<any | null> {
    if (!this.db) await this.initialize();

    const metadata = await this.db!.get('metadata', key);
    return metadata?.value || null;
  }

  /**
   * 瀵煎嚭缂撳瓨鏁版嵁锛堢敤浜庤皟璇曪級
   */
  async exportCache(): Promise<{
    entities: any[];
    operations: any[];
    metadata: any[];
  }> {
    if (!this.db) await this.initialize();

    const [entities, operations, metadata] = await Promise.all([
      this.db!.getAll('entities'),
      this.db!.getAll('operations'),
      this.db!.getAll('metadata')
    ]);

    return { entities, operations, metadata };
  }

  /**
   * 娓呯┖鎵€鏈夌紦瀛樻暟鎹?
   */
  async clearAllCache(): Promise<void> {
    if (!this.db) await this.initialize();

    const tx = this.db!.transaction(['entities', 'operations', 'metadata'], 'readwrite');
    
    await Promise.all([
      tx.objectStore('entities').clear(),
      tx.objectStore('operations').clear(),
      tx.objectStore('metadata').clear()
    ]);
    
    await tx.done;
  }

  /**
   * 鍏抽棴鏁版嵁搴撹繛鎺?
   */
  async close(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// 鍒涘缓鍏ㄥ眬瀹炰緥
export const offlineCacheManager = new OfflineCacheManager();