// @ts-nocheck
// 鏌ヨ鏈嶅姟绯荤粺 - 瀹屾暣瀹炵幇

import { QueryClient, useQuery, useMutation, useInfiniteQuery, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query'
import { apiServices } from './api-services'
import { requestOptimizer, cacheUtils } from '@/lib/api-cache'
import type {
  User,
  Project,
  TestCase,
  TestResult,
  DashboardStats,
  PerformanceTest,
  SecurityScan,
  AIAnalysis,
  PaginatedResponse,
  SearchParams
} from '@/types'

/**
 * 鏌ヨ閿伐鍘?
 * 鐢ㄤ簬鐢熸垚涓€鑷寸殑鏌ヨ閿?
 */
export const queryKeys = {
  // 璁よ瘉鐩稿叧
  auth: {
    currentUser: () => ['auth', 'current-user'] as const,
    profile: () => ['auth', 'profile'] as const
  },

  // 浠〃鏉跨浉鍏?
  dashboard: {
    all: () => ['dashboard'] as const,
    stats: () => ['dashboard', 'stats'] as const,
    systemStatus: () => ['dashboard', 'system-status'] as const,
    testStats: (timeRange?: string) => ['dashboard', 'test-stats', timeRange] as const,
    performanceMetrics: () => ['dashboard', 'performance-metrics'] as const
  },

  // 椤圭洰鐩稿叧
  projects: {
    all: () => ['projects'] as const,
    lists: () => ['projects', 'list'] as const,
    list: (params?: any) => ['projects', 'list', params] as const,
    details: () => ['projects', 'detail'] as const,
    detail: (id: string) => ['projects', 'detail', id] as const,
    members: (projectId: string) => ['projects', 'members', projectId] as const
  },

  // 闇€姹傜浉鍏?
  requirements: {
    all: () => ['requirements'] as const,
    lists: () => ['requirements', 'list'] as const,
    list: (params?: any) => ['requirements', 'list', params] as const,
    details: () => ['requirements', 'detail'] as const,
    detail: (id: string) => ['requirements', 'detail', id] as const
  },

  // 娴嬭瘯鐢ㄤ緥鐩稿叧
  testCases: {
    all: () => ['test-cases'] as const,
    lists: () => ['test-cases', 'list'] as const,
    list: (params?: any) => ['test-cases', 'list', params] as const,
    details: () => ['test-cases', 'detail'] as const,
    detail: (id: string) => ['test-cases', 'detail', id] as const,
    history: (id: string) => ['test-cases', 'history', id] as const
  },

  // 娴嬭瘯缁撴灉鐩稿叧
  testResults: {
    all: () => ['test-results'] as const,
    lists: () => ['test-results', 'list'] as const,
    list: (params?: any) => ['test-results', 'list', params] as const,
    details: () => ['test-results', 'detail'] as const,
    detail: (id: string) => ['test-results', 'detail', id] as const,
    report: (id: string, format?: string) => ['test-results', 'report', id, format] as const
  },

  // 鎬ц兘娴嬭瘯鐩稿叧
  performance: {
    all: () => ['performance'] as const,
    lists: () => ['performance', 'list'] as const,
    list: (params?: any) => ['performance', 'list', params] as const,
    details: () => ['performance', 'detail'] as const,
    detail: (id: string) => ['performance', 'detail', id] as const,
    results: (id: string) => ['performance', 'results', id] as const
  },

  // 瀹夊叏娴嬭瘯鐩稿叧
  security: {
    all: () => ['security'] as const,
    lists: () => ['security', 'list'] as const,
    list: (params?: any) => ['security', 'list', params] as const,
    details: () => ['security', 'detail'] as const,
    detail: (id: string) => ['security', 'detail', id] as const,
    results: (id: string) => ['security', 'results', id] as const
  },

  // AI鏈嶅姟鐩稿叧
  ai: {
    all: () => ['ai'] as const,
    analyses: () => ['ai', 'analyses'] as const,
    analysesList: (params?: any) => ['ai', 'analyses', 'list', params] as const,
    analysis: (id: string) => ['ai', 'analysis', id] as const,
    chat: (sessionId?: string) => ['ai', 'chat', sessionId] as const,
    suggestions: (type: string, context: any) => ['ai', 'suggestions', type, context] as const
  },

  // 绯荤粺鐩稿叧
  system: {
    all: () => ['system'] as const,
    configs: (category?: string) => ['system', 'configs', category] as const,
    logs: (params?: any) => ['system', 'logs', params] as const,
    health: () => ['system', 'health'] as const
  },

  // 閫氱煡鐩稿叧
  notifications: {
    all: () => ['notifications'] as const,
    list: (params?: any) => ['notifications', 'list', params] as const,
    unreadCount: () => ['notifications', 'unread-count'] as const
  },

  // 鏂囦欢鐩稿叧
  files: {
    all: () => ['files'] as const,
    info: (id: string) => ['files', 'info', id] as const
  }
}

/**
 * 璁よ瘉鏌ヨhooks
 */
export const useAuthQueries = {
  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅
   */
  useCurrentUser: (options?: UseQueryOptions<User>) => {
    return useQuery({
      queryKey: queryKeys.auth.currentUser(),
      queryFn: () => apiServices.auth.getCurrentUser(),
      staleTime: 10 * 60 * 1000, // 10鍒嗛挓
      gcTime: 30 * 60 * 1000, // 30鍒嗛挓
      ...options
    })
  },

  /**
   * 鏇存柊鐢ㄦ埛璧勬枡
   */
  useUpdateProfile: (options?: UseMutationOptions<User, Error, Partial<User>>) => {
    return useMutation({
      mutationFn: (updates: Partial<User>) => apiServices.auth.updateProfile(updates),
      onSuccess: (data, variables, context) => {
        // 鏇存柊缂撳瓨
        queryServices.invalidateQueries(queryKeys.auth.currentUser())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  }
}

/**
 * 浠〃鏉挎煡璇ooks
 */
export const useDashboardQueries = {
  /**
   * 鑾峰彇浠〃鏉挎暟鎹?
   */
  useDashboardData: (options?: UseQueryOptions<DashboardStats>) => {
    return useQuery({
      queryKey: queryKeys.dashboard.stats(),
      queryFn: () => apiServices.dashboard.getDashboardData(),
      staleTime: 30 * 1000, // 30绉?
      gcTime: 5 * 60 * 1000, // 5鍒嗛挓
      refetchInterval: 60 * 1000, // 1鍒嗛挓鑷姩鍒锋柊
      ...options
    })
  },

  /**
   * 鑾峰彇绯荤粺鐘舵€?
   */
  useSystemStatus: (options?: UseQueryOptions<any>) => {
    return useQuery({
      queryKey: queryKeys.dashboard.systemStatus(),
      queryFn: () => apiServices.dashboard.getSystemStatus(),
      staleTime: 10 * 1000, // 10绉?
      gcTime: 1 * 60 * 1000, // 1鍒嗛挓
      refetchInterval: 30 * 1000, // 30绉掕嚜鍔ㄥ埛鏂?
      ...options
    })
  },

  /**
   * 鑾峰彇娴嬭瘯缁熻
   */
  useTestStats: (timeRange?: string, options?: UseQueryOptions<any>) => {
    return useQuery({
      queryKey: queryKeys.dashboard.testStats(timeRange),
      queryFn: () => apiServices.dashboard.getTestStats(timeRange),
      staleTime: 60 * 1000, // 1鍒嗛挓
      gcTime: 5 * 60 * 1000, // 5鍒嗛挓
      ...options
    })
  },

  /**
   * 鑾峰彇鎬ц兘鎸囨爣
   */
  usePerformanceMetrics: (options?: UseQueryOptions<any>) => {
    return useQuery({
      queryKey: queryKeys.dashboard.performanceMetrics(),
      queryFn: () => apiServices.dashboard.getPerformanceMetrics(),
      staleTime: 30 * 1000, // 30绉?
      gcTime: 2 * 60 * 1000, // 2鍒嗛挓
      refetchInterval: 60 * 1000, // 1鍒嗛挓鑷姩鍒锋柊
      ...options
    })
  }
}

/**
 * 椤圭洰鏌ヨhooks
 */
export const useProjectQueries = {
  /**
   * 鑾峰彇椤圭洰鍒楄〃
   */
  useProjects: (params?: any, options?: UseQueryOptions<PaginatedResponse<Project>>) => {
    return useQuery({
      queryKey: queryKeys.projects.list(params),
      queryFn: () => apiServices.project.getProjects(params),
      staleTime: 5 * 60 * 1000, // 5鍒嗛挓
      gcTime: 10 * 60 * 1000, // 10鍒嗛挓
      placeholderData: (previousData) => previousData,
      ...options
    })
  },

  /**
   * 鑾峰彇椤圭洰璇︽儏
   */
  useProject: (id: string, options?: UseQueryOptions<Project>) => {
    return useQuery({
      queryKey: queryKeys.projects.detail(id),
      queryFn: () => apiServices.project.getProject(id),
      staleTime: 10 * 60 * 1000, // 10鍒嗛挓
      gcTime: 30 * 60 * 1000, // 30鍒嗛挓
      enabled: !!id,
      ...options
    })
  },

  /**
   * 鑾峰彇椤圭洰鎴愬憳
   */
  useProjectMembers: (projectId: string, options?: UseQueryOptions<any[]>) => {
    return useQuery({
      queryKey: queryKeys.projects.members(projectId),
      queryFn: () => apiServices.project.getProjectMembers(projectId),
      staleTime: 5 * 60 * 1000, // 5鍒嗛挓
      gcTime: 15 * 60 * 1000, // 15鍒嗛挓
      enabled: !!projectId,
      ...options
    })
  },

  /**
   * 鍒涘缓椤圭洰
   */
  useCreateProject: (options?: UseMutationOptions<Project, Error, Omit<Project, 'id' | 'createdAt' | 'updatedAt'>>) => {
    return useMutation({
      mutationFn: (projectData) => apiServices.project.createProject(projectData),
      onSuccess: (data, variables, context) => {
        // 鍒锋柊椤圭洰鍒楄〃
        queryServices.invalidateQueries(queryKeys.projects.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  },

  /**
   * 鏇存柊椤圭洰
   */
  useUpdateProject: (options?: UseMutationOptions<Project, Error, { id: string; updates: Partial<Project> }>) => {
    return useMutation({
      mutationFn: ({ id, updates }) => apiServices.project.updateProject(id, updates),
      onSuccess: (data, variables, context) => {
        // 鏇存柊缂撳瓨
        queryServices.setQueryData(queryKeys.projects.detail(variables.id), data)
        queryServices.invalidateQueries(queryKeys.projects.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  },

  /**
   * 鍒犻櫎椤圭洰
   */
  useDeleteProject: (options?: UseMutationOptions<void, Error, string>) => {
    return useMutation({
      mutationFn: (id: string) => apiServices.project.deleteProject(id),
      onSuccess: (data, variables, context) => {
        // 绉婚櫎缂撳瓨骞跺埛鏂板垪琛?
        queryServices.removeQueries(queryKeys.projects.detail(variables))
        queryServices.invalidateQueries(queryKeys.projects.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  }
}

/**
 * 娴嬭瘯鐢ㄤ緥鏌ヨhooks
 */
export const useTestCaseQueries = {
  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥鍒楄〃
   */
  useTestCases: (params?: any, options?: UseQueryOptions<PaginatedResponse<TestCase>>) => {
    return useQuery({
      queryKey: queryKeys.testCases.list(params),
      queryFn: () => apiServices.testCase.getTestCases(params),
      staleTime: 3 * 60 * 1000, // 3鍒嗛挓
      gcTime: 10 * 60 * 1000, // 10鍒嗛挓
      placeholderData: (previousData) => previousData,
      ...options
    })
  },

  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥璇︽儏
   */
  useTestCase: (id: string, options?: UseQueryOptions<TestCase>) => {
    return useQuery({
      queryKey: queryKeys.testCases.detail(id),
      queryFn: () => apiServices.testCase.getTestCase(id),
      staleTime: 5 * 60 * 1000, // 5鍒嗛挓
      gcTime: 15 * 60 * 1000, // 15鍒嗛挓
      enabled: !!id,
      ...options
    })
  },

  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥鎵ц鍘嗗彶
   */
  useTestCaseHistory: (id: string, params?: any, options?: UseQueryOptions<PaginatedResponse<TestResult>>) => {
    return useQuery({
      queryKey: queryKeys.testCases.history(id),
      queryFn: () => apiServices.testCase.getTestCaseHistory(id, params),
      staleTime: 1 * 60 * 1000, // 1鍒嗛挓
      gcTime: 5 * 60 * 1000, // 5鍒嗛挓
      enabled: !!id,
      ...options
    })
  },

  /**
   * 鍒涘缓娴嬭瘯鐢ㄤ緥
   */
  useCreateTestCase: (options?: UseMutationOptions<TestCase, Error, Omit<TestCase, 'id' | 'createdAt' | 'updatedAt'>>) => {
    return useMutation({
      mutationFn: (testCaseData) => apiServices.testCase.createTestCase(testCaseData),
      onSuccess: (data, variables, context) => {
        // 鍒锋柊娴嬭瘯鐢ㄤ緥鍒楄〃
        queryServices.invalidateQueries(queryKeys.testCases.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  },

  /**
   * 鏇存柊娴嬭瘯鐢ㄤ緥
   */
  useUpdateTestCase: (options?: UseMutationOptions<TestCase, Error, { id: string; updates: Partial<TestCase> }>) => {
    return useMutation({
      mutationFn: ({ id, updates }) => apiServices.testCase.updateTestCase(id, updates),
      onSuccess: (data, variables, context) => {
        // 鏇存柊缂撳瓨
        queryServices.setQueryData(queryKeys.testCases.detail(variables.id), data)
        queryServices.invalidateQueries(queryKeys.testCases.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  },

  /**
   * 鎵ц娴嬭瘯鐢ㄤ緥
   */
  useExecuteTestCase: (options?: UseMutationOptions<any, Error, { id: string; config?: any }>) => {
    return useMutation({
      mutationFn: ({ id, config }) => apiServices.testCase.executeTestCase(id, config),
      onSuccess: (data, variables, context) => {
        // 鍒锋柊娴嬭瘯鐢ㄤ緥鍘嗗彶鍜岀粨鏋?
        queryServices.invalidateQueries(queryKeys.testCases.history(variables.id))
        queryServices.invalidateQueries(queryKeys.testResults.lists())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  }
}

/**
 * AI鏈嶅姟鏌ヨhooks
 */
export const useAIQueries = {
  /**
   * 鑾峰彇AI鍒嗘瀽鍒楄〃
   */
  useAIAnalyses: (params?: any, options?: UseQueryOptions<PaginatedResponse<AIAnalysis>>) => {
    return useQuery({
      queryKey: queryKeys.ai.analysesList(params),
      queryFn: () => apiServices.ai.getAIAnalyses(params),
      staleTime: 2 * 60 * 1000, // 2鍒嗛挓
      gcTime: 10 * 60 * 1000, // 10鍒嗛挓
      placeholderData: (previousData) => previousData,
      ...options
    })
  },

  /**
   * 鑾峰彇AI鍒嗘瀽缁撴灉
   */
  useAIAnalysis: (id: string, options?: UseQueryOptions<AIAnalysis>) => {
    return useQuery({
      queryKey: queryKeys.ai.analysis(id),
      queryFn: () => apiServices.ai.getAIAnalysisResult(id),
      staleTime: 30 * 1000, // 30绉?
      gcTime: 5 * 60 * 1000, // 5鍒嗛挓
      enabled: !!id,
      refetchInterval: (data) => {
        // 濡傛灉鍒嗘瀽杩樺湪杩涜涓紝姣?绉掑埛鏂颁竴娆?
        return data?.status === 'processing' ? 5000 : false
      },
      ...options
    })
  },

  /**
   * 鍒涘缓AI鍒嗘瀽
   */
  useCreateAIAnalysis: (options?: UseMutationOptions<AIAnalysis, Error, any>) => {
    return useMutation({
      mutationFn: (data) => apiServices.ai.createAIAnalysis(data),
      onSuccess: (data, variables, context) => {
        // 鍒锋柊AI鍒嗘瀽鍒楄〃
        queryServices.invalidateQueries(queryKeys.ai.analyses())
        options?.onSuccess?.(data, variables, context)
      },
      ...options
    })
  },

  /**
   * AI鑱婂ぉ
   */
  useChatWithAI: (options?: UseMutationOptions<any, Error, any>) => {
    return useMutation({
      mutationFn: (data) => apiServices.ai.chatWithAI(data),
      ...options
    })
  },

  /**
   * 鑾峰彇AI寤鸿
   */
  useGetAISuggestions: (options?: UseMutationOptions<any, Error, any>) => {
    return useMutation({
      mutationFn: (data) => apiServices.ai.getAISuggestions(data),
      ...options
    })
  }
}

/**
 * 鏃犻檺鏌ヨhooks
 */
export const useInfiniteQueries = {
  /**
   * 鏃犻檺婊氬姩椤圭洰鍒楄〃
   */
  useInfiniteProjects: (baseParams?: any, options?: any) => {
    return useInfiniteQuery({
      queryKey: queryKeys.projects.list({ ...baseParams, infinite: true }),
      queryFn: ({ pageParam = 1 }) => 
        apiServices.project.getProjects({ ...baseParams, page: pageParam }),
      getNextPageParam: (lastPage) => {
        const { pagination } = lastPage
        return pagination.page < pagination.totalPages ? pagination.page + 1 : undefined
      },
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      ...options
    })
  },

  /**
   * 鏃犻檺婊氬姩娴嬭瘯鐢ㄤ緥鍒楄〃
   */
  useInfiniteTestCases: (baseParams?: any, options?: any) => {
    return useInfiniteQuery({
      queryKey: queryKeys.testCases.list({ ...baseParams, infinite: true }),
      queryFn: ({ pageParam = 1 }) => 
        apiServices.testCase.getTestCases({ ...baseParams, page: pageParam }),
      getNextPageParam: (lastPage) => {
        const { pagination } = lastPage
        return pagination.page < pagination.totalPages ? pagination.page + 1 : undefined
      },
      staleTime: 3 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      ...options
    })
  }
}

/**
 * 鏌ヨ鏈嶅姟绠＄悊鍣?
 */
export class QueryServices {
  private queryClient: QueryClient

  constructor(queryClient: QueryClient) {
    this.queryClient = queryClient
  }

  /**
   * 浣跨紦瀛樺け鏁?
   */
  invalidateQueries(queryKey: readonly unknown[]) {
    return this.queryClient.invalidateQueries({ queryKey })
  }

  /**
   * 鍒锋柊鏌ヨ
   */
  refetchQueries(queryKey: readonly unknown[]) {
    return this.queryClient.refetchQueries({ queryKey })
  }

  /**
   * 璁剧疆鏌ヨ鏁版嵁
   */
  setQueryData<T>(queryKey: readonly unknown[], data: T) {
    return this.queryClient.setQueryData(queryKey, data)
  }

  /**
   * 鑾峰彇鏌ヨ鏁版嵁
   */
  getQueryData<T>(queryKey: readonly unknown[]): T | undefined {
    return this.queryClient.getQueryData<T>(queryKey)
  }

  /**
   * 绉婚櫎鏌ヨ
   */
  removeQueries(queryKey: readonly unknown[]) {
    return this.queryClient.removeQueries({ queryKey })
  }

  /**
   * 棰勫彇鏌ヨ
   */
  prefetchQuery<T>(queryKey: readonly unknown[], queryFn: () => Promise<T>, options?: any) {
    return this.queryClient.prefetchQuery({
      queryKey,
      queryFn,
      staleTime: 5 * 60 * 1000,
      ...options
    })
  }

  /**
   * 鎵归噺澶辨晥鐩稿叧鏌ヨ
   */
  invalidateRelatedQueries(resource: string, action: 'create' | 'update' | 'delete', id?: string) {
    switch (resource) {
      case 'project':
        this.invalidateQueries(queryKeys.projects.lists())
        if (id) {
          this.invalidateQueries(queryKeys.projects.detail(id))
          this.invalidateQueries(queryKeys.projects.members(id))
        }
        // 椤圭洰鍙樻洿鍙兘褰卞搷娴嬭瘯鐢ㄤ緥鍜岄渶姹?
        this.invalidateQueries(queryKeys.testCases.lists())
        this.invalidateQueries(queryKeys.requirements.lists())
        break

      case 'testCase':
        this.invalidateQueries(queryKeys.testCases.lists())
        if (id) {
          this.invalidateQueries(queryKeys.testCases.detail(id))
          this.invalidateQueries(queryKeys.testCases.history(id))
        }
        // 娴嬭瘯鐢ㄤ緥鍙樻洿鍙兘褰卞搷娴嬭瘯缁撴灉
        this.invalidateQueries(queryKeys.testResults.lists())
        break

      case 'testResult':
        this.invalidateQueries(queryKeys.testResults.lists())
        if (id) {
          this.invalidateQueries(queryKeys.testResults.detail(id))
        }
        // 娴嬭瘯缁撴灉鍙樻洿鍙兘褰卞搷浠〃鏉跨粺璁?
        this.invalidateQueries(queryKeys.dashboard.stats())
        this.invalidateQueries(queryKeys.dashboard.testStats())
        break

      default:
        console.warn(`鏈煡鐨勮祫婧愮被鍨? ${resource}`)
    }
  }

  /**
   * 娓呯悊杩囨湡缂撳瓨
   */
  clearStaleQueries() {
    this.queryClient.clear()
  }

  /**
   * 鑾峰彇鏌ヨ缁熻淇℃伅
   */
  getQueryStats() {
    const cache = this.queryClient.getQueryCache()
    const queries = cache.getAll()
    
    return {
      totalQueries: queries.length,
      activeQueries: queries.filter(q => q.getObserversCount() > 0).length,
      staleQueries: queries.filter(q => q.isStale()).length,
      errorQueries: queries.filter(q => q.state.status === 'error').length,
      loadingQueries: queries.filter(q => q.state.status === 'loading').length
    }
  }
}

// 鍒涘缓鍏ㄥ眬鏌ヨ鏈嶅姟瀹炰緥
let queryServicesInstance: QueryServices | null = null

export const createQueryServices = (queryClient: QueryClient): QueryServices => {
  queryServicesInstance = new QueryServices(queryClient)
  return queryServicesInstance
}

export const getQueryServices = (): QueryServices => {
  if (!queryServicesInstance) {
    throw new Error('QueryServices鏈垵濮嬪寲锛岃鍏堣皟鐢╟reateQueryServices')
  }
  return queryServicesInstance
}

// 瀵煎嚭鏌ヨ鏈嶅姟瀹炰緥
export const queryServices = {
  invalidateQueries: (queryKey: readonly unknown[]) => getQueryServices().invalidateQueries(queryKey),
  refetchQueries: (queryKey: readonly unknown[]) => getQueryServices().refetchQueries(queryKey),
  setQueryData: <T>(queryKey: readonly unknown[], data: T) => getQueryServices().setQueryData(queryKey, data),
  getQueryData: <T>(queryKey: readonly unknown[]) => getQueryServices().getQueryData<T>(queryKey),
  removeQueries: (queryKey: readonly unknown[]) => getQueryServices().removeQueries(queryKey),
  prefetchQuery: <T>(queryKey: readonly unknown[], queryFn: () => Promise<T>, options?: any) => 
    getQueryServices().prefetchQuery(queryKey, queryFn, options),
  invalidateRelatedQueries: (resource: string, action: 'create' | 'update' | 'delete', id?: string) =>
    getQueryServices().invalidateRelatedQueries(resource, action, id),
  clearStaleQueries: () => getQueryServices().clearStaleQueries(),
  getQueryStats: () => getQueryServices().getQueryStats()
}

// 瀵煎嚭鎵€鏈夋煡璇ooks
export const queries = {
  auth: useAuthQueries,
  dashboard: useDashboardQueries,
  projects: useProjectQueries,
  testCases: useTestCaseQueries,
  ai: useAIQueries,
  infinite: useInfiniteQueries
}

export default queryServices