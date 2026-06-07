// @ts-nocheck
/**
 * 寤鸿绠＄悊鐩稿叧鐨凴eact Hook
 */
import { useState, useCallback, useEffect } from 'react';
import { 
  Suggestion, 
  SuggestionFilters, 
  PaginationParams,
  PaginatedResponse,
  BatchOperationProgress,
  UpdateSuggestionRequest,
  APIResponse
} from '../types/ai-assistant';
import { apiClient } from '../lib/api-client';

interface SuggestionStats {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
  average_rating: number;
  implementation_rate: number;
}

interface UseSuggestionsOptions {
  autoLoad?: boolean;
  defaultFilters?: SuggestionFilters;
  defaultPagination?: PaginationParams;
}

interface UseSuggestionsReturn {
  // 鏁版嵁鐘舵€?
  suggestions: Suggestion[];
  stats: SuggestionStats | null;
  loading: boolean;
  error: string | null;
  
  // 鍒嗛〉淇℃伅
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  
  // 绛涢€夊拰鎺掑簭
  filters: SuggestionFilters;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  
  // 鏁版嵁鎿嶄綔
  fetchSuggestions: (filters?: SuggestionFilters, pagination?: PaginationParams) => Promise<void>;
  refreshSuggestions: () => Promise<void>;
  
  // 鍗曚釜寤鸿鎿嶄綔
  acceptSuggestion: (suggestionId: number) => Promise<void>;
  rejectSuggestion: (suggestionId: number) => Promise<void>;
  rateSuggestion: (suggestionId: number, rating: number) => Promise<void>;
  submitFeedback: (suggestionId: number, feedback: string) => Promise<void>;
  updateSuggestion: (suggestionId: number, updates: UpdateSuggestionRequest) => Promise<void>;
  
  // 鎵归噺鎿嶄綔
  batchAcceptSuggestions: (suggestionIds: number[]) => Promise<BatchOperationProgress>;
  batchRejectSuggestions: (suggestionIds: number[]) => Promise<BatchOperationProgress>;
  deleteSuggestions: (suggestionIds: number[]) => Promise<void>;
  
  // 鐘舵€佺鐞?
  setFilters: (filters: SuggestionFilters) => void;
  setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
  clearError: () => void;
  
  // 涔愯鏇存柊
  optimisticUpdate: (suggestionId: number, updates: Partial<Suggestion>) => void;
  rollbackOptimisticUpdate: (suggestionId: number) => void;
}

export function useSuggestions(options: UseSuggestionsOptions = {}): UseSuggestionsReturn {
  const {
    autoLoad = true,
    defaultFilters = {},
    defaultPagination = { page: 1, size: 20 }
  } = options;

  // 鐘舵€佺鐞?
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [stats, setStats] = useState<SuggestionStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<SuggestionFilters>(defaultFilters);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [pagination, setPagination] = useState({
    page: defaultPagination.page || 1,
    size: defaultPagination.size || 20,
    total: 0,
    pages: 0,
    hasNext: false,
    hasPrev: false
  });

  // 涔愯鏇存柊鐨勫浠芥暟鎹?
  const [optimisticBackups, setOptimisticBackups] = useState<Map<number, Suggestion>>(new Map());

  // 鑾峰彇寤鸿鍒楄〃
  const fetchSuggestions = useCallback(async (
    newFilters?: SuggestionFilters,
    newPagination?: PaginationParams
  ) => {
    try {
      setLoading(true);
      setError(null);

      const queryFilters = newFilters || filters;
      const queryPagination = newPagination || { page: pagination.page, size: pagination.size };

      const response = await apiClient.get<PaginatedResponse<Suggestion>>('/api/v1/ai-assistant/suggestions', {
        params: {
          ...queryFilters,
          page: queryPagination.page,
          size: queryPagination.size,
          sort_by: sortBy,
          sort_order: sortOrder
        }
      });

      if (response.data.success && response.data.data) {
        const data = response.data.data;
        setSuggestions(data.items);
        setPagination({
          page: data.page,
          size: data.size,
          total: data.total,
          pages: data.pages,
          hasNext: data.has_next,
          hasPrev: data.has_prev
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇寤鸿鍒楄〃澶辫触';
      setError(errorMessage);
      console.error('Failed to fetch suggestions:', err);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.size, sortBy, sortOrder]);

  // 鑾峰彇缁熻鏁版嵁
  const fetchStats = useCallback(async () => {
    try {
      const response = await apiClient.get<SuggestionStats>('/api/v1/ai-assistant/suggestions/stats', {
        params: filters
      });

      if (response.data.success && response.data.data) {
        setStats(response.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch suggestion stats:', err);
    }
  }, [filters]);

  // 鍒锋柊鏁版嵁
  const refreshSuggestions = useCallback(async () => {
    await Promise.all([
      fetchSuggestions(),
      fetchStats()
    ]);
  }, [fetchSuggestions, fetchStats]);

  // 涔愯鏇存柊
  const optimisticUpdate = useCallback((suggestionId: number, updates: Partial<Suggestion>) => {
    setSuggestions(prev => {
      const index = prev.findIndex(s => s.id === suggestionId);
      if (index === -1) return prev;

      // 澶囦唤鍘熷鏁版嵁
      setOptimisticBackups(backups => new Map(backups.set(suggestionId, prev[index])));

      // 搴旂敤鏇存柊
      const newSuggestions = [...prev];
      newSuggestions[index] = {
        ...newSuggestions[index],
        ...updates,
        _syncing: true,
        _lastSynced: new Date().toISOString()
      };
      return newSuggestions;
    });
  }, []);

  // 鍥炴粴涔愯鏇存柊
  const rollbackOptimisticUpdate = useCallback((suggestionId: number) => {
    const backup = optimisticBackups.get(suggestionId);
    if (!backup) return;

    setSuggestions(prev => {
      const index = prev.findIndex(s => s.id === suggestionId);
      if (index === -1) return prev;

      const newSuggestions = [...prev];
      newSuggestions[index] = backup;
      return newSuggestions;
    });

    setOptimisticBackups(prev => {
      const newBackups = new Map(prev);
      newBackups.delete(suggestionId);
      return newBackups;
    });
  }, [optimisticBackups]);

  // 鎺ュ彈寤鸿
  const acceptSuggestion = useCallback(async (suggestionId: number) => {
    // 涔愯鏇存柊
    optimisticUpdate(suggestionId, { 
      status: 'ACCEPTED' as const,
      _syncing: true 
    });

    try {
      const response = await apiClient.patch<Suggestion>(
        `/api/v1/ai-assistant/suggestions/${suggestionId}`,
        { status: 'ACCEPTED' }
      );

      if (response.data.success && response.data.data) {
        // 鏇存柊鎴愬姛锛屽簲鐢ㄦ湇鍔″櫒杩斿洖鐨勬暟鎹?
        setSuggestions(prev => prev.map(s => 
          s.id === suggestionId 
            ? { ...response.data.data!, _syncing: false }
            : s
        ));
        
        // 娓呴櫎澶囦唤
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          newBackups.delete(suggestionId);
          return newBackups;
        });
      }
    } catch (err) {
      // 鍥炴粴涔愯鏇存柊
      rollbackOptimisticUpdate(suggestionId);
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate]);

  // 鎷掔粷寤鸿
  const rejectSuggestion = useCallback(async (suggestionId: number) => {
    // 涔愯鏇存柊
    optimisticUpdate(suggestionId, { 
      status: 'REJECTED' as const,
      _syncing: true 
    });

    try {
      const response = await apiClient.patch<Suggestion>(
        `/api/v1/ai-assistant/suggestions/${suggestionId}`,
        { status: 'REJECTED' }
      );

      if (response.data.success && response.data.data) {
        setSuggestions(prev => prev.map(s => 
          s.id === suggestionId 
            ? { ...response.data.data!, _syncing: false }
            : s
        ));
        
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          newBackups.delete(suggestionId);
          return newBackups;
        });
      }
    } catch (err) {
      rollbackOptimisticUpdate(suggestionId);
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate]);

  // 璇勫垎寤鸿
  const rateSuggestion = useCallback(async (suggestionId: number, rating: number) => {
    // 涔愯鏇存柊
    optimisticUpdate(suggestionId, { 
      user_rating: rating,
      _syncing: true 
    });

    try {
      const response = await apiClient.patch<Suggestion>(
        `/api/v1/ai-assistant/suggestions/${suggestionId}`,
        { user_rating: rating }
      );

      if (response.data.success && response.data.data) {
        setSuggestions(prev => prev.map(s => 
          s.id === suggestionId 
            ? { ...response.data.data!, _syncing: false }
            : s
        ));
        
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          newBackups.delete(suggestionId);
          return newBackups;
        });
      }
    } catch (err) {
      rollbackOptimisticUpdate(suggestionId);
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate]);

  // 鎻愪氦鍙嶉
  const submitFeedback = useCallback(async (suggestionId: number, feedback: string) => {
    // 涔愯鏇存柊
    optimisticUpdate(suggestionId, { 
      user_feedback: feedback,
      _syncing: true 
    });

    try {
      const response = await apiClient.patch<Suggestion>(
        `/api/v1/ai-assistant/suggestions/${suggestionId}`,
        { user_feedback: feedback }
      );

      if (response.data.success && response.data.data) {
        setSuggestions(prev => prev.map(s => 
          s.id === suggestionId 
            ? { ...response.data.data!, _syncing: false }
            : s
        ));
        
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          newBackups.delete(suggestionId);
          return newBackups;
        });
      }
    } catch (err) {
      rollbackOptimisticUpdate(suggestionId);
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate]);

  // 鏇存柊寤鸿
  const updateSuggestion = useCallback(async (suggestionId: number, updates: UpdateSuggestionRequest) => {
    // 涔愯鏇存柊
    optimisticUpdate(suggestionId, { 
      ...updates,
      _syncing: true 
    });

    try {
      const response = await apiClient.patch<Suggestion>(
        `/api/v1/ai-assistant/suggestions/${suggestionId}`,
        updates
      );

      if (response.data.success && response.data.data) {
        setSuggestions(prev => prev.map(s => 
          s.id === suggestionId 
            ? { ...response.data.data!, _syncing: false }
            : s
        ));
        
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          newBackups.delete(suggestionId);
          return newBackups;
        });
      }
    } catch (err) {
      rollbackOptimisticUpdate(suggestionId);
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate]);

  // 鎵归噺鎺ュ彈寤鸿
  const batchAcceptSuggestions = useCallback(async (suggestionIds: number[]): Promise<BatchOperationProgress> => {
    // 涔愯鏇存柊鎵€鏈夐€変腑鐨勫缓璁?
    suggestionIds.forEach(id => {
      optimisticUpdate(id, { 
        status: 'ACCEPTED' as const,
        _syncing: true 
      });
    });

    try {
      const response = await apiClient.post<BatchOperationProgress>(
        '/api/v1/ai-assistant/suggestions/batch-accept',
        { suggestion_ids: suggestionIds }
      );

      if (response.data.success && response.data.data) {
        // 鍒锋柊鏁版嵁浠ヨ幏鍙栨渶鏂扮姸鎬?
        await refreshSuggestions();
        return response.data.data;
      }

      throw new Error('鎵归噺鎿嶄綔澶辫触');
    } catch (err) {
      // 鍥炴粴鎵€鏈変箰瑙傛洿鏂?
      suggestionIds.forEach(id => rollbackOptimisticUpdate(id));
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate, refreshSuggestions]);

  // 鎵归噺鎷掔粷寤鸿
  const batchRejectSuggestions = useCallback(async (suggestionIds: number[]): Promise<BatchOperationProgress> => {
    // 涔愯鏇存柊鎵€鏈夐€変腑鐨勫缓璁?
    suggestionIds.forEach(id => {
      optimisticUpdate(id, { 
        status: 'REJECTED' as const,
        _syncing: true 
      });
    });

    try {
      const response = await apiClient.post<BatchOperationProgress>(
        '/api/v1/ai-assistant/suggestions/batch-reject',
        { suggestion_ids: suggestionIds }
      );

      if (response.data.success && response.data.data) {
        await refreshSuggestions();
        return response.data.data;
      }

      throw new Error('鎵归噺鎿嶄綔澶辫触');
    } catch (err) {
      suggestionIds.forEach(id => rollbackOptimisticUpdate(id));
      throw err;
    }
  }, [optimisticUpdate, rollbackOptimisticUpdate, refreshSuggestions]);

  // 鍒犻櫎寤鸿
  const deleteSuggestions = useCallback(async (suggestionIds: number[]) => {
    try {
      const response = await apiClient.delete('/api/v1/ai-assistant/suggestions/batch-delete', {
        data: { suggestion_ids: suggestionIds }
      });

      if (response.data.success) {
        // 浠庢湰鍦扮姸鎬佷腑绉婚櫎宸插垹闄ょ殑寤鸿
        setSuggestions(prev => prev.filter(s => !suggestionIds.includes(s.id)));
        
        // 娓呴櫎鐩稿叧鐨勫浠芥暟鎹?
        setOptimisticBackups(prev => {
          const newBackups = new Map(prev);
          suggestionIds.forEach(id => newBackups.delete(id));
          return newBackups;
        });
      }
    } catch (err) {
      throw err;
    }
  }, []);

  // 璁剧疆鎺掑簭
  const setSorting = useCallback((newSortBy: string, newSortOrder: 'asc' | 'desc') => {
    setSortBy(newSortBy);
    setSortOrder(newSortOrder);
  }, []);

  // 娓呴櫎閿欒
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 鑷姩鍔犺浇鏁版嵁
  useEffect(() => {
    if (autoLoad) {
      refreshSuggestions();
    }
  }, [autoLoad, refreshSuggestions]);

  // 褰撶瓫閫夋潯浠舵垨鎺掑簭鏀瑰彉鏃堕噸鏂板姞杞芥暟鎹?
  useEffect(() => {
    if (autoLoad) {
      fetchSuggestions();
    }
  }, [filters, sortBy, sortOrder]);

  // 褰撶瓫閫夋潯浠舵敼鍙樻椂閲嶆柊鍔犺浇缁熻鏁版嵁
  useEffect(() => {
    if (autoLoad) {
      fetchStats();
    }
  }, [filters]);

  return {
    // 鏁版嵁鐘舵€?
    suggestions,
    stats,
    loading,
    error,
    
    // 鍒嗛〉淇℃伅
    pagination,
    
    // 绛涢€夊拰鎺掑簭
    filters,
    sortBy,
    sortOrder,
    
    // 鏁版嵁鎿嶄綔
    fetchSuggestions,
    refreshSuggestions,
    
    // 鍗曚釜寤鸿鎿嶄綔
    acceptSuggestion,
    rejectSuggestion,
    rateSuggestion,
    submitFeedback,
    updateSuggestion,
    
    // 鎵归噺鎿嶄綔
    batchAcceptSuggestions,
    batchRejectSuggestions,
    deleteSuggestions,
    
    // 鐘舵€佺鐞?
    setFilters,
    setSorting,
    clearError,
    
    // 涔愯鏇存柊
    optimisticUpdate,
    rollbackOptimisticUpdate
  };
}