// @ts-nocheck
/**
 * 浼樺寲鐨勯」鐩暟鎹鐞咹ook
 * 
 * 鎻愪緵楂樻€ц兘鐨勯」鐩暟鎹幏鍙栥€佺紦瀛樺拰鐘舵€佺鐞?
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { debounce } from 'lodash-es';
import { Project, ProjectQueryParams, CreateProjectRequest, UpdateProjectRequest } from '../../types/project';
import { projectService } from '../../services/projectService';

// 鏌ヨ閿伐鍘?
const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (params: ProjectQueryParams) => [...projectKeys.lists(), params] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: number) => [...projectKeys.details(), id] as const,
  statistics: () => [...projectKeys.all, 'statistics'] as const,
  statistic: (id: number) => [...projectKeys.statistics(), id] as const,
};

// 缂撳瓨閰嶇疆
const CACHE_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5鍒嗛挓
  cacheTime: 10 * 60 * 1000, // 10鍒嗛挓
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  retry: 2,
};

// 椤圭洰鍒楄〃Hook
export const useOptimizedProjectList = (initialParams?: Partial<ProjectQueryParams>) => {
  const [params, setParams] = useState<ProjectQueryParams>({
    page: 1,
    size: 20,
    sort_by: 'updated_at',
    sort_order: 'desc',
    ...initialParams,
  });

  const queryClient = useQueryClient();
  const abortControllerRef = useRef<AbortController | null>(null);

  // 鏌ヨ椤圭洰鍒楄〃
  const {
    data,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: projectKeys.list(params),
    queryFn: async ({ signal }) => {
      // 鍙栨秷涔嬪墠鐨勮姹?
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      abortControllerRef.current = new AbortController();
      
      try {
        const response = await projectService.getProjects(params, {
          signal: abortControllerRef.current.signal,
        });
        return response;
      } catch (error: any) {
        if (error.name === 'AbortError') {
          throw new Error('Request cancelled');
        }
        throw error;
      }
    },
    ...CACHE_CONFIG,
    keepPreviousData: true, // 淇濇寔涔嬪墠鐨勬暟鎹紝閬垮厤闂儊
  });

  // 闃叉姈鏇存柊鍙傛暟
  const debouncedSetParams = useMemo(
    () => debounce((newParams: Partial<ProjectQueryParams>) => {
      setParams(prev => ({ ...prev, ...newParams, page: 1 })); // 閲嶇疆椤电爜
    }, 300),
    []
  );

  // 鏇存柊鎼滅储鍙傛暟
  const updateSearch = useCallback((search: string) => {
    debouncedSetParams({ search });
  }, [debouncedSetParams]);

  // 鏇存柊杩囨护鍙傛暟
  const updateFilters = useCallback((filters: Partial<ProjectQueryParams>) => {
    debouncedSetParams(filters);
  }, [debouncedSetParams]);

  // 鏇存柊鍒嗛〉鍙傛暟
  const updatePagination = useCallback((page: number, size?: number) => {
    setParams(prev => ({ ...prev, page, ...(size && { size }) }));
  }, []);

  // 鏇存柊鎺掑簭鍙傛暟
  const updateSort = useCallback((sort_by: string, sort_order: 'asc' | 'desc') => {
    setParams(prev => ({ ...prev, sort_by, sort_order }));
  }, []);

  // 棰勫姞杞戒笅涓€椤?
  const prefetchNextPage = useCallback(() => {
    if (data && params.page * params.size < data.total) {
      const nextPageParams = { ...params, page: params.page + 1 };
      queryClient.prefetchQuery({
        queryKey: projectKeys.list(nextPageParams),
        queryFn: () => projectService.getProjects(nextPageParams),
        ...CACHE_CONFIG,
      });
    }
  }, [data, params, queryClient]);

  // 娓呯悊鍑芥暟
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      debouncedSetParams.cancel();
    };
  }, [debouncedSetParams]);

  return {
    // 鏁版嵁
    projects: data?.projects || [],
    total: data?.total || 0,
    totalPages: data?.total_pages || 0,
    
    // 鐘舵€?
    isLoading,
    isFetching,
    error,
    
    // 鍙傛暟
    params,
    
    // 鎿嶄綔
    refetch,
    updateSearch,
    updateFilters,
    updatePagination,
    updateSort,
    prefetchNextPage,
  };
};

// 椤圭洰璇︽儏Hook
export const useOptimizedProjectDetail = (projectId: number | null) => {
  const queryClient = useQueryClient();

  const {
    data: project,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: projectKeys.detail(projectId!),
    queryFn: () => projectService.getProject(projectId!),
    enabled: !!projectId,
    ...CACHE_CONFIG,
  });

  // 棰勫姞杞介」鐩粺璁?
  const prefetchStatistics = useCallback(() => {
    if (projectId) {
      queryClient.prefetchQuery({
        queryKey: projectKeys.statistic(projectId),
        queryFn: () => projectService.getProjectStatistics(projectId),
        ...CACHE_CONFIG,
      });
    }
  }, [projectId, queryClient]);

  return {
    project,
    isLoading,
    error,
    refetch,
    prefetchStatistics,
  };
};

// 椤圭洰缁熻Hook
export const useOptimizedProjectStatistics = (projectId: number | null) => {
  const {
    data: statistics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: projectKeys.statistic(projectId!),
    queryFn: () => projectService.getProjectStatistics(projectId!),
    enabled: !!projectId,
    ...CACHE_CONFIG,
    staleTime: 2 * 60 * 1000, // 缁熻鏁版嵁2鍒嗛挓杩囨湡
  });

  return {
    statistics,
    isLoading,
    error,
    refetch,
  };
};

// 椤圭洰鎿嶄綔Hook
export const useOptimizedProjectMutations = () => {
  const queryClient = useQueryClient();

  // 鍒涘缓椤圭洰
  const createMutation = useMutation({
    mutationFn: (data: CreateProjectRequest) => projectService.createProject(data),
    onSuccess: () => {
      // 娓呴櫎鍒楄〃缂撳瓨
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });

  // 鏇存柊椤圭洰
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateProjectRequest }) =>
      projectService.updateProject(id, data),
    onSuccess: (updatedProject) => {
      // 鏇存柊璇︽儏缂撳瓨
      queryClient.setQueryData(
        projectKeys.detail(updatedProject.id),
        updatedProject
      );
      
      // 娓呴櫎鍒楄〃缂撳瓨
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });

  // 鍒犻櫎椤圭洰
  const deleteMutation = useMutation({
    mutationFn: (id: number) => projectService.deleteProject(id),
    onSuccess: (_, deletedId) => {
      // 绉婚櫎璇︽儏缂撳瓨
      queryClient.removeQueries({ queryKey: projectKeys.detail(deletedId) });
      
      // 娓呴櫎鍒楄〃缂撳瓨
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });

  // 鎵归噺鎿嶄綔
  const batchUpdateMutation = useMutation({
    mutationFn: (updates: Array<{ id: number; data: UpdateProjectRequest }>) =>
      Promise.all(updates.map(({ id, data }) => projectService.updateProject(id, data))),
    onSuccess: () => {
      // 娓呴櫎鎵€鏈夐」鐩浉鍏崇紦瀛?
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });

  return {
    createProject: createMutation.mutateAsync,
    updateProject: updateMutation.mutateAsync,
    deleteProject: deleteMutation.mutateAsync,
    batchUpdate: batchUpdateMutation.mutateAsync,
    
    // 鐘舵€?
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isBatchUpdating: batchUpdateMutation.isPending,
    
    // 閿欒
    createError: createMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error,
    batchError: batchUpdateMutation.error,
  };
};

// 椤圭洰缂撳瓨绠＄悊Hook
export const useProjectCacheManager = () => {
  const queryClient = useQueryClient();

  // 棰勫姞杞介」鐩?
  const prefetchProject = useCallback(async (projectId: number) => {
    await queryClient.prefetchQuery({
      queryKey: projectKeys.detail(projectId),
      queryFn: () => projectService.getProject(projectId),
      ...CACHE_CONFIG,
    });
  }, [queryClient]);

  // 棰勫姞杞介」鐩垪琛?
  const prefetchProjectList = useCallback(async (params: ProjectQueryParams) => {
    await queryClient.prefetchQuery({
      queryKey: projectKeys.list(params),
      queryFn: () => projectService.getProjects(params),
      ...CACHE_CONFIG,
    });
  }, [queryClient]);

  // 娓呴櫎椤圭洰缂撳瓨
  const clearProjectCache = useCallback((projectId?: number) => {
    if (projectId) {
      queryClient.removeQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.removeQueries({ queryKey: projectKeys.statistic(projectId) });
    } else {
      queryClient.removeQueries({ queryKey: projectKeys.all });
    }
  }, [queryClient]);

  // 鍒锋柊椤圭洰缂撳瓨
  const refreshProjectCache = useCallback((projectId?: number) => {
    if (projectId) {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.statistic(projectId) });
    } else {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    }
  }, [queryClient]);

  // 鑾峰彇缂撳瓨鐘舵€?
  const getCacheStatus = useCallback(() => {
    const cache = queryClient.getQueryCache();
    const projectQueries = cache.findAll({ queryKey: projectKeys.all });
    
    return {
      totalQueries: projectQueries.length,
      activeQueries: projectQueries.filter(q => q.state.fetchStatus === 'fetching').length,
      staleQueries: projectQueries.filter(q => q.isStale()).length,
      errorQueries: projectQueries.filter(q => q.state.status === 'error').length,
    };
  }, [queryClient]);

  return {
    prefetchProject,
    prefetchProjectList,
    clearProjectCache,
    refreshProjectCache,
    getCacheStatus,
  };
};

// 椤圭洰鎬ц兘鐩戞帶Hook
export const useProjectPerformanceMonitor = () => {
  const [metrics, setMetrics] = useState({
    renderTime: 0,
    queryTime: 0,
    cacheHitRate: 0,
    errorRate: 0,
  });

  const queryClient = useQueryClient();

  // 璁板綍娓叉煋鏃堕棿
  const recordRenderTime = useCallback((startTime: number) => {
    const renderTime = performance.now() - startTime;
    setMetrics(prev => ({ ...prev, renderTime }));
  }, []);

  // 璁板綍鏌ヨ鏃堕棿
  const recordQueryTime = useCallback((startTime: number) => {
    const queryTime = performance.now() - startTime;
    setMetrics(prev => ({ ...prev, queryTime }));
  }, []);

  // 璁＄畻缂撳瓨鍛戒腑鐜?
  const calculateCacheHitRate = useCallback(() => {
    const cache = queryClient.getQueryCache();
    const projectQueries = cache.findAll({ queryKey: projectKeys.all });
    
    const totalQueries = projectQueries.length;
    const cachedQueries = projectQueries.filter(q => 
      q.state.dataUpdatedAt > 0 && !q.isStale()
    ).length;
    
    const hitRate = totalQueries > 0 ? cachedQueries / totalQueries : 0;
    setMetrics(prev => ({ ...prev, cacheHitRate: hitRate }));
  }, [queryClient]);

  // 璁＄畻閿欒鐜?
  const calculateErrorRate = useCallback(() => {
    const cache = queryClient.getQueryCache();
    const projectQueries = cache.findAll({ queryKey: projectKeys.all });
    
    const totalQueries = projectQueries.length;
    const errorQueries = projectQueries.filter(q => q.state.status === 'error').length;
    
    const errorRate = totalQueries > 0 ? errorQueries / totalQueries : 0;
    setMetrics(prev => ({ ...prev, errorRate }));
  }, [queryClient]);

  // 瀹氭湡鏇存柊鎸囨爣
  useEffect(() => {
    const interval = setInterval(() => {
      calculateCacheHitRate();
      calculateErrorRate();
    }, 10000); // 姣?0绉掓洿鏂颁竴娆?

    return () => clearInterval(interval);
  }, [calculateCacheHitRate, calculateErrorRate]);

  return {
    metrics,
    recordRenderTime,
    recordQueryTime,
    calculateCacheHitRate,
    calculateErrorRate,
  };
};