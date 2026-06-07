// @ts-nocheck
import requirementService from './requirementService'
import offlineStorage from '@/lib/offline-storage'
import { 
  Requirement, 
  RequirementFilters, 
  CreateRequirementRequest, 
  UpdateRequirementRequest 
} from '@/types/requirement'

/**
 * 绂荤嚎鎰熺煡鐨勯渶姹傛湇鍔?
 * 鍦ㄥ師鏈夐渶姹傛湇鍔″熀纭€涓婃坊鍔犵绾挎敮鎸?
 */
class OfflineRequirementService {
  private cachePrefix = 'requirements'
  private defaultCacheExpiry = 30 * 60 * 1000 // 30鍒嗛挓

  /**
   * 鐢熸垚缂撳瓨閿?
   */
  private getCacheKey(key: string): string {
    return `${this.cachePrefix}:${key}`
  }

  /**
   * 鑾峰彇闇€姹傚垪琛紙绂荤嚎浼樺厛锛?
   */
  async getRequirements(filters: RequirementFilters = {}): Promise<{
    data: Requirement[]
    total: number
    page: number
    size: number
    fromCache?: boolean
  }> {
    const cacheKey = this.getCacheKey(`list:${JSON.stringify(filters)}`)
    
    try {
      // 灏濊瘯浠庣紦瀛樿幏鍙?
      const cachedData = await offlineStorage.getCachedData(cacheKey)
      
      if (navigator.onLine) {
        try {
          // 鍦ㄧ嚎鏃惰幏鍙栨渶鏂版暟鎹?
          const freshData = await requirementService.getRequirements(filters)
          
          // 缂撳瓨鏂版暟鎹?
          await offlineStorage.cacheData(cacheKey, freshData, Date.now() + this.defaultCacheExpiry)
          
          return freshData
        } catch (error) {
          // 缃戠粶璇锋眰澶辫触锛屽洖閫€鍒扮紦瀛?
          if (cachedData) {
            console.warn('Network request failed, using cached data:', error)
            return { ...cachedData, fromCache: true }
          }
          throw error
        }
      } else {
        // 绂荤嚎鏃朵娇鐢ㄧ紦瀛?
        if (cachedData) {
          return { ...cachedData, fromCache: true }
        }
        throw new Error('No cached data available offline')
      }
    } catch (error) {
      console.error('Failed to get requirements:', error)
      throw error
    }
  }

  /**
   * 鑾峰彇鍗曚釜闇€姹傦紙绂荤嚎浼樺厛锛?
   */
  async getRequirement(id: number): Promise<Requirement> {
    const cacheKey = this.getCacheKey(`detail:${id}`)
    
    try {
      // 灏濊瘯浠庣紦瀛樿幏鍙?
      const cachedData = await offlineStorage.getCachedData<Requirement>(cacheKey)
      
      if (navigator.onLine) {
        try {
          // 鍦ㄧ嚎鏃惰幏鍙栨渶鏂版暟鎹?
          const freshData = await requirementService.getRequirement(id)
          
          // 缂撳瓨鏂版暟鎹?
          await offlineStorage.cacheData(cacheKey, freshData, Date.now() + this.defaultCacheExpiry)
          
          return freshData
        } catch (error) {
          // 缃戠粶璇锋眰澶辫触锛屽洖閫€鍒扮紦瀛?
          if (cachedData) {
            console.warn('Network request failed, using cached data:', error)
            return cachedData
          }
          throw error
        }
      } else {
        // 绂荤嚎鏃朵娇鐢ㄧ紦瀛?
        if (cachedData) {
          return cachedData
        }
        throw new Error('No cached data available offline')
      }
    } catch (error) {
      console.error('Failed to get requirement:', error)
      throw error
    }
  }

  /**
   * 鍒涘缓闇€姹傦紙鏀寔绂荤嚎闃熷垪锛?
   */
  async createRequirement(data: CreateRequirementRequest): Promise<Requirement> {
    if (navigator.onLine) {
      try {
        const result = await requirementService.createRequirement(data)
        
        // 娓呴櫎鐩稿叧缂撳瓨
        await this.invalidateListCache()
        
        // 缂撳瓨鏂板垱寤虹殑闇€姹?
        const cacheKey = this.getCacheKey(`detail:${result.id}`)
        await offlineStorage.cacheData(cacheKey, result, Date.now() + this.defaultCacheExpiry)
        
        return result
      } catch (error) {
        // 鍦ㄧ嚎鍒涘缓澶辫触锛屾坊鍔犲埌绂荤嚎闃熷垪
        await this.addToOfflineQueue('CREATE', 'requirements', data)
        
        // 杩斿洖涓存椂闇€姹傚璞?
        const tempRequirement: Requirement = {
          id: Date.now(), // 涓存椂ID
          requirement_code: `TEMP-${Date.now()}`,
          project_id: data.project_id,
          title: data.title,
          description: data.description || '',
          acceptance_criteria: data.acceptance_criteria || '',
          requirement_type: data.requirement_type,
          category: data.category || '',
          priority: data.priority,
          business_value: data.business_value,
          status: 'DRAFT',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          creator_id: 0, // 涓存椂鍊?
          version: 1,
          tags: data.tags || [],
          custom_fields: data.custom_fields || {},
          _isOffline: true // 鏍囪涓虹绾垮垱寤?
        } as Requirement
        
        return tempRequirement
      }
    } else {
      // 绂荤嚎鏃剁洿鎺ユ坊鍔犲埌闃熷垪
      await this.addToOfflineQueue('CREATE', 'requirements', data)
      
      // 杩斿洖涓存椂闇€姹傚璞?
      const tempRequirement: Requirement = {
        id: Date.now(), // 涓存椂ID
        requirement_code: `TEMP-${Date.now()}`,
        project_id: data.project_id,
        title: data.title,
        description: data.description || '',
        acceptance_criteria: data.acceptance_criteria || '',
        requirement_type: data.requirement_type,
        category: data.category || '',
        priority: data.priority,
        business_value: data.business_value,
        status: 'DRAFT',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        creator_id: 0, // 涓存椂鍊?
        version: 1,
        tags: data.tags || [],
        custom_fields: data.custom_fields || {},
        _isOffline: true // 鏍囪涓虹绾垮垱寤?
      } as Requirement
      
      return tempRequirement
    }
  }

  /**
   * 鏇存柊闇€姹傦紙鏀寔绂荤嚎闃熷垪锛?
   */
  async updateRequirement(id: number, data: UpdateRequirementRequest): Promise<Requirement> {
    if (navigator.onLine) {
      try {
        const result = await requirementService.updateRequirement(id, data)
        
        // 鏇存柊缂撳瓨
        const cacheKey = this.getCacheKey(`detail:${id}`)
        await offlineStorage.cacheData(cacheKey, result, Date.now() + this.defaultCacheExpiry)
        
        // 娓呴櫎鍒楄〃缂撳瓨
        await this.invalidateListCache()
        
        return result
      } catch (error) {
        // 鍦ㄧ嚎鏇存柊澶辫触锛屾坊鍔犲埌绂荤嚎闃熷垪
        await this.addToOfflineQueue('UPDATE', 'requirements', { id, ...data })
        
        // 灏濊瘯浠庣紦瀛樿幏鍙栧綋鍓嶆暟鎹苟鏇存柊
        const cacheKey = this.getCacheKey(`detail:${id}`)
        const cachedData = await offlineStorage.getCachedData<Requirement>(cacheKey)
        
        if (cachedData) {
          const updatedData = { 
            ...cachedData, 
            ...data, 
            updated_at: new Date().toISOString(),
            _isOffline: true 
          }
          await offlineStorage.cacheData(cacheKey, updatedData, Date.now() + this.defaultCacheExpiry)
          return updatedData
        }
        
        throw error
      }
    } else {
      // 绂荤嚎鏃剁洿鎺ユ坊鍔犲埌闃熷垪
      await this.addToOfflineQueue('UPDATE', 'requirements', { id, ...data })
      
      // 灏濊瘯浠庣紦瀛樿幏鍙栧綋鍓嶆暟鎹苟鏇存柊
      const cacheKey = this.getCacheKey(`detail:${id}`)
      const cachedData = await offlineStorage.getCachedData<Requirement>(cacheKey)
      
      if (cachedData) {
        const updatedData = { 
          ...cachedData, 
          ...data, 
          updated_at: new Date().toISOString(),
          _isOffline: true 
        }
        await offlineStorage.cacheData(cacheKey, updatedData, Date.now() + this.defaultCacheExpiry)
        return updatedData
      }
      
      throw new Error('No cached data available for offline update')
    }
  }

  /**
   * 鍒犻櫎闇€姹傦紙鏀寔绂荤嚎闃熷垪锛?
   */
  async deleteRequirement(id: number): Promise<void> {
    if (navigator.onLine) {
      try {
        await requirementService.deleteRequirement(id)
        
        // 娓呴櫎缂撳瓨
        const cacheKey = this.getCacheKey(`detail:${id}`)
        await offlineStorage.removeCachedData(cacheKey)
        await this.invalidateListCache()
      } catch (error) {
        // 鍦ㄧ嚎鍒犻櫎澶辫触锛屾坊鍔犲埌绂荤嚎闃熷垪
        await this.addToOfflineQueue('DELETE', 'requirements', { id })
        
        // 鍦ㄧ紦瀛樹腑鏍囪涓哄凡鍒犻櫎
        const cacheKey = this.getCacheKey(`detail:${id}`)
        const cachedData = await offlineStorage.getCachedData<Requirement>(cacheKey)
        
        if (cachedData) {
          const deletedData = { 
            ...cachedData, 
            _isDeleted: true,
            _isOffline: true 
          }
          await offlineStorage.cacheData(cacheKey, deletedData, Date.now() + this.defaultCacheExpiry)
        }
      }
    } else {
      // 绂荤嚎鏃剁洿鎺ユ坊鍔犲埌闃熷垪
      await this.addToOfflineQueue('DELETE', 'requirements', { id })
      
      // 鍦ㄧ紦瀛樹腑鏍囪涓哄凡鍒犻櫎
      const cacheKey = this.getCacheKey(`detail:${id}`)
      const cachedData = await offlineStorage.getCachedData<Requirement>(cacheKey)
      
      if (cachedData) {
        const deletedData = { 
          ...cachedData, 
          _isDeleted: true,
          _isOffline: true 
        }
        await offlineStorage.cacheData(cacheKey, deletedData, Date.now() + this.defaultCacheExpiry)
      }
    }
  }

  /**
   * 澶嶅埗闇€姹傦紙鏀寔绂荤嚎闃熷垪锛?
   */
  async duplicateRequirement(id: number): Promise<Requirement> {
    if (navigator.onLine) {
      try {
        const result = await requirementService.duplicateRequirement(id)
        
        // 娓呴櫎鍒楄〃缂撳瓨
        await this.invalidateListCache()
        
        // 缂撳瓨鏂板鍒剁殑闇€姹?
        const cacheKey = this.getCacheKey(`detail:${result.id}`)
        await offlineStorage.cacheData(cacheKey, result, Date.now() + this.defaultCacheExpiry)
        
        return result
      } catch (error) {
        // 鍦ㄧ嚎澶嶅埗澶辫触锛屾坊鍔犲埌绂荤嚎闃熷垪
        await this.addToOfflineQueue('CREATE', 'requirements/duplicate', { id })
        
        // 灏濊瘯浠庣紦瀛樿幏鍙栧師闇€姹傛暟鎹苟鍒涘缓鍓湰
        const originalCacheKey = this.getCacheKey(`detail:${id}`)
        const originalData = await offlineStorage.getCachedData<Requirement>(originalCacheKey)
        
        if (originalData) {
          const duplicatedData: Requirement = {
            ...originalData,
            id: Date.now(), // 涓存椂ID
            requirement_code: `TEMP-COPY-${Date.now()}`,
            title: `${originalData.title} (鍓湰)`,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            _isOffline: true
          }
          
          return duplicatedData
        }
        
        throw error
      }
    } else {
      // 绂荤嚎鏃剁洿鎺ユ坊鍔犲埌闃熷垪
      await this.addToOfflineQueue('CREATE', 'requirements/duplicate', { id })
      
      // 灏濊瘯浠庣紦瀛樿幏鍙栧師闇€姹傛暟鎹苟鍒涘缓鍓湰
      const originalCacheKey = this.getCacheKey(`detail:${id}`)
      const originalData = await offlineStorage.getCachedData<Requirement>(originalCacheKey)
      
      if (originalData) {
        const duplicatedData: Requirement = {
          ...originalData,
          id: Date.now(), // 涓存椂ID
          requirement_code: `TEMP-COPY-${Date.now()}`,
          title: `${originalData.title} (鍓湰)`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          _isOffline: true
        }
        
        return duplicatedData
      }
      
      throw new Error('No cached data available for offline duplication')
    }
  }

  /**
   * 娣诲姞鎿嶄綔鍒扮绾块槦鍒?
   */
  private async addToOfflineQueue(
    type: 'CREATE' | 'UPDATE' | 'DELETE',
    resource: string,
    data: any
  ): Promise<void> {
    await offlineStorage.addOfflineOperation({
      type,
      resource,
      data,
      maxRetries: 3
    })
  }

  /**
   * 娓呴櫎鍒楄〃缂撳瓨
   */
  private async invalidateListCache(): Promise<void> {
    // 杩欓噷搴旇娓呴櫎鎵€鏈夊垪琛ㄧ浉鍏崇殑缂撳瓨
    // 鐢变簬缂撳瓨閿寘鍚煡璇㈠弬鏁帮紝鎴戜滑闇€瑕佷竴涓洿鏅鸿兘鐨勭紦瀛樺け鏁堟満鍒?
    // 鏆傛椂绠€鍖栧鐞?
    try {
      const stats = await offlineStorage.getCacheStats()
      console.log('Cache invalidation needed, current stats:', stats)
      // TODO: 瀹炵幇鏇寸簿纭殑缂撳瓨澶辨晥閫昏緫
    } catch (error) {
      console.error('Failed to invalidate cache:', error)
    }
  }

  /**
   * 棰勫姞杞介渶姹傛暟鎹?
   */
  async preloadRequirements(filters: RequirementFilters = {}): Promise<void> {
    if (navigator.onLine) {
      try {
        const data = await requirementService.getRequirements(filters)
        const cacheKey = this.getCacheKey(`list:${JSON.stringify(filters)}`)
        await offlineStorage.cacheData(cacheKey, data, Date.now() + this.defaultCacheExpiry)
        
        // 棰勫姞杞芥瘡涓渶姹傜殑璇︽儏
        for (const requirement of data.data) {
          const detailCacheKey = this.getCacheKey(`detail:${requirement.id}`)
          await offlineStorage.cacheData(detailCacheKey, requirement, Date.now() + this.defaultCacheExpiry)
        }
      } catch (error) {
        console.error('Failed to preload requirements:', error)
      }
    }
  }

  /**
   * 娓呴櫎鎵€鏈夐渶姹傜浉鍏崇紦瀛?
   */
  async clearCache(): Promise<void> {
    try {
      // TODO: 瀹炵幇鎸夊墠缂€娓呴櫎缂撳瓨鐨勫姛鑳?
      await offlineStorage.clearAllOfflineData()
    } catch (error) {
      console.error('Failed to clear cache:', error)
    }
  }
}

// 鍒涘缓骞跺鍑哄疄渚?
export const offlineRequirementService = new OfflineRequirementService()
export default offlineRequirementService