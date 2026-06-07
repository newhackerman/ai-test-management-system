import { create } from 'zustand'
import { useEffect, useCallback, useRef } from 'react'

export interface QueryState<T = any> {
  data: T | null
  error: Error | null
  isLoading: boolean
  isFetching: boolean
  isError: boolean
  isSuccess: boolean
  lastFetch: number
  staleTime: number
  gcTime: number
}

export interface QueryOptions {
  staleTime?: number // 数据被认为过期的时间（毫秒）
  gcTime?: number // 缓存保留时间（毫秒）
  refetchOnWindowFocus?: boolean
  refetchOnReconnect?: boolean
  retry?: number | boolean
  retryDelay?: number
  enabled?: boolean
}

export interface MutationState<T = any> {
  data: T | null
  error: Error | null
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
}

export interface QueryStore {
  queries: Record<string, QueryState>
  mutations: Record<string, MutationState>
  
  // Query actions
  setQueryData: <T>(key: string, data: T) => void
  setQueryError: (key: string, error: Error) => void
  setQueryLoading: (key: string, loading: boolean) => void
  setQueryFetching: (key: string, fetching: boolean) => void
  invalidateQuery: (key: string) => void
  removeQuery: (key: string) => void
  
  // Mutation actions
  setMutationData: <T>(key: string, data: T) => void
  setMutationError: (key: string, error: Error) => void
  setMutationLoading: (key: string, loading: boolean) => void
  removeMutation: (key: string) => void
  
  // Utility actions
  clearAll: () => void
  getQueryState: (key: string) => QueryState | undefined
  getMutationState: (key: string) => MutationState | undefined
}

const createInitialQueryState = (options: QueryOptions = {}): QueryState => ({
  data: null,
  error: null,
  isLoading: false,
  isFetching: false,
  isError: false,
  isSuccess: false,
  lastFetch: 0,
  staleTime: options.staleTime || 5 * 60 * 1000, // 5分钟
  gcTime: options.gcTime || 10 * 60 * 1000, // 10分钟
})

const createInitialMutationState = (): MutationState => ({
  data: null,
  error: null,
  isLoading: false,
  isError: false,
  isSuccess: false,
})

export const useQueryStore = create<QueryStore>((set, get) => ({
  queries: {},
  mutations: {},

  // Query actions
  setQueryData: (key, data) => {
    set(state => ({
      queries: {
        ...state.queries,
        [key]: {
          ...state.queries[key],
          data,
          error: null,
          isLoading: false,
          isFetching: false,
          isError: false,
          isSuccess: true,
          lastFetch: Date.now(),
        }
      }
    }))
  },

  setQueryError: (key, error) => {
    set(state => ({
      queries: {
        ...state.queries,
        [key]: {
          ...state.queries[key],
          error,
          isLoading: false,
          isFetching: false,
          isError: true,
          isSuccess: false,
        }
      }
    }))
  },

  setQueryLoading: (key, loading) => {
    set(state => ({
      queries: {
        ...state.queries,
        [key]: {
          ...(state.queries[key] || createInitialQueryState()),
          isLoading: loading,
          isError: false,
        }
      }
    }))
  },

  setQueryFetching: (key, fetching) => {
    set(state => ({
      queries: {
        ...state.queries,
        [key]: {
          ...(state.queries[key] || createInitialQueryState()),
          isFetching: fetching,
        }
      }
    }))
  },

  invalidateQuery: (key) => {
    set(state => ({
      queries: {
        ...state.queries,
        [key]: {
          ...state.queries[key],
          lastFetch: 0, // 标记为需要重新获取
        }
      }
    }))
  },

  removeQuery: (key) => {
    set(state => {
      const newQueries = { ...state.queries }
      delete newQueries[key]
      return { queries: newQueries }
    })
  },

  // Mutation actions
  setMutationData: (key, data) => {
    set(state => ({
      mutations: {
        ...state.mutations,
        [key]: {
          ...state.mutations[key],
          data,
          error: null,
          isLoading: false,
          isError: false,
          isSuccess: true,
        }
      }
    }))
  },

  setMutationError: (key, error) => {
    set(state => ({
      mutations: {
        ...state.mutations,
        [key]: {
          ...state.mutations[key],
          error,
          isLoading: false,
          isError: true,
          isSuccess: false,
        }
      }
    }))
  },

  setMutationLoading: (key, loading) => {
    set(state => ({
      mutations: {
        ...state.mutations,
        [key]: {
          ...(state.mutations[key] || createInitialMutationState()),
          isLoading: loading,
          isError: false,
        }
      }
    }))
  },

  removeMutation: (key) => {
    set(state => {
      const newMutations = { ...state.mutations }
      delete newMutations[key]
      return { mutations: newMutations }
    })
  },

  // Utility actions
  clearAll: () => {
    set({ queries: {}, mutations: {} })
  },

  getQueryState: (key) => {
    return get().queries[key]
  },

  getMutationState: (key) => {
    return get().mutations[key]
  },
}))

// Query Hook
export function useQuery<T = any>(
  key: string,
  queryFn: () => Promise<T>,
  options: QueryOptions = {}
) {
  const store = useQueryStore()
  const queryState = store.queries[key] || createInitialQueryState(options)

  const isStale = () => {
    if (queryState.lastFetch === 0) return true
    return Date.now() - queryState.lastFetch > queryState.staleTime
  }

  const shouldFetch = () => {
    return options.enabled !== false && (isStale() || !queryState.data)
  }

  const refetch = async () => {
    if (queryState.isLoading) return

    store.setQueryLoading(key, true)
    
    try {
      const data = await queryFn()
      store.setQueryData(key, data)
      return data
    } catch (error) {
      store.setQueryError(key, error as Error)
      throw error
    }
  }

  // 自动获取数据
  useEffect(() => {
    if (shouldFetch()) {
      refetch()
    }
  }, [key, options.enabled])

  return {
    ...queryState,
    refetch,
    isStale: isStale(),
  }
}

// Mutation Hook
export function useMutation<T = any, V = any>(
  key: string,
  mutationFn: (variables: V) => Promise<T>,
  options: {
    onSuccess?: (data: T, variables: V) => void
    onError?: (error: Error, variables: V) => void
    onSettled?: (data: T | null, error: Error | null, variables: V) => void
  } = {}
) {
  const store = useQueryStore()
  const mutationState = store.mutations[key] || createInitialMutationState()

  const mutate = async (variables: V) => {
    store.setMutationLoading(key, true)
    
    try {
      const data = await mutationFn(variables)
      store.setMutationData(key, data)
      options.onSuccess?.(data, variables)
      options.onSettled?.(data, null, variables)
      return data
    } catch (error) {
      const err = error as Error
      store.setMutationError(key, err)
      options.onError?.(err, variables)
      options.onSettled?.(null, err, variables)
      throw error
    }
  }

  const reset = () => {
    store.removeMutation(key)
  }

  return {
    ...mutationState,
    mutate,
    reset,
  }
}

// 工具函数
export const queryClient = {
  invalidateQueries: (pattern?: string) => {
    const store = useQueryStore.getState()
    const keys = Object.keys(store.queries)
    
    keys.forEach(key => {
      if (!pattern || key.includes(pattern)) {
        store.invalidateQuery(key)
      }
    })
  },

  removeQueries: (pattern?: string) => {
    const store = useQueryStore.getState()
    const keys = Object.keys(store.queries)
    
    keys.forEach(key => {
      if (!pattern || key.includes(pattern)) {
        store.removeQuery(key)
      }
    })
  },

  setQueryData: <T>(key: string, data: T) => {
    useQueryStore.getState().setQueryData(key, data)
  },

  getQueryData: <T>(key: string): T | null => {
    const state = useQueryStore.getState().getQueryState(key)
    return state?.data || null
  },

  clear: () => {
    useQueryStore.getState().clearAll()
  }
}

// 缓存清理定时器
let cacheCleanupTimer: NodeJS.Timeout | null = null

// 启动缓存清理
const startCacheCleanup = () => {
  if (cacheCleanupTimer) return
  
  cacheCleanupTimer = setInterval(() => {
    const store = useQueryStore.getState()
    const now = Date.now()
    
    Object.entries(store.queries).forEach(([key, query]) => {
      if (now - query.lastFetch > query.gcTime) {
        store.removeQuery(key)
      }
    })
  }, 60000) // 每分钟清理一次
}

// 停止缓存清理
const stopCacheCleanup = () => {
  if (cacheCleanupTimer) {
    clearInterval(cacheCleanupTimer)
    cacheCleanupTimer = null
  }
}

// 自动启动缓存清理
startCacheCleanup()

// 窗口焦点和网络重连处理
if (typeof window !== 'undefined') {
  window.addEventListener('focus', () => {
    const store = useQueryStore.getState()
    Object.keys(store.queries).forEach(key => {
      const query = store.queries[key]
      if (query.lastFetch > 0 && Date.now() - query.lastFetch > query.staleTime) {
        store.invalidateQuery(key)
      }
    })
  })
  
  window.addEventListener('online', () => {
    const store = useQueryStore.getState()
    Object.keys(store.queries).forEach(key => {
      store.invalidateQuery(key)
    })
  })
}