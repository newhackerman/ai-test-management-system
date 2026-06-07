// @ts-nocheck
// 楂樼骇鏌ヨhooks

import { useEffect, useCallback, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryStore, QueryOptions } from '@/stores/query'
import { queryClient, createQueryKey, QueryKey, InfiniteQueryOptions, InfiniteQueryState } from '@/lib/query-client'

// 渚濊禆鏌ヨhook
export function useDependentQuery<T = any>(
  key: string | QueryKey,
  queryFn: () => Promise<T>,
  dependencies: any[],
  options: QueryOptions = {}
) {
  const queryKey = typeof key === 'string' ? key : createQueryKey(key)
  const enabled = dependencies.every(dep => dep !== undefined && dep !== null)
  
  return useQuery(queryKey, queryFn, {
    ...options,
    enabled: enabled && options.enabled !== false
  })
}

// 骞惰鏌ヨhook
export function useQueries<T = any[]>(
  queries: Array<{
    key: string | QueryKey
    queryFn: () => Promise<any>
    options?: QueryOptions
  }>
): T {
  const results = queries.map(({ key, queryFn, options }) => {
    const queryKey = typeof key === 'string' ? key : createQueryKey(key)
    return useQuery(queryKey, queryFn, options)
  })
  
  return results as T
}

// 鏃犻檺鏌ヨhook
export function useInfiniteQuery<T = any>(
  key: string | QueryKey,
  queryFn: ({ pageParam }: { pageParam: any }) => Promise<T>,
  options: InfiniteQueryOptions = {}
) {
  const queryKey = typeof key === 'string' ? key : createQueryKey(key)
  const store = useQueryStore()
  const [state, setState] = useState<InfiniteQueryState<T>>(() => ({
    data: null,
    error: null,
    isLoading: false,
    isFetching: false,
    isError: false,
    isSuccess: false,
    lastFetch: 0,
    staleTime: options.staleTime || 5 * 60 * 1000,
    cacheTime: options.cacheTime || 10 * 60 * 1000,
    pages: [],
    pageParams: [],
    hasNextPage: false,
    hasPreviousPage: false,
    isFetchingNextPage: false,
    isFetchingPreviousPage: false
  }))
  
  const fetchNextPage = useCallback(async () => {
    if (state.isFetchingNextPage || !state.hasNextPage) return
    
    setState(prev => ({ ...prev, isFetchingNextPage: true }))
    
    try {
      const lastPage = state.pages[state.pages.length - 1]
      const nextPageParam = options.getNextPageParam?.(lastPage, state.pages)
      
      if (nextPageParam === undefined) {
        setState(prev => ({ ...prev, isFetchingNextPage: false, hasNextPage: false }))
        return
      }
      
      const newPage = await queryFn({ pageParam: nextPageParam })
      
      setState(prev => ({
        ...prev,
        pages: [...prev.pages, newPage],
        pageParams: [...prev.pageParams, nextPageParam],
        hasNextPage: options.getNextPageParam?.(newPage, [...prev.pages, newPage]) !== undefined,
        isFetchingNextPage: false,
        isSuccess: true,
        lastFetch: Date.now()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error as Error,
        isError: true,
        isFetchingNextPage: false
      }))
    }
  }, [state.pages, state.pageParams, state.isFetchingNextPage, state.hasNextPage, queryFn, options])
  
  const fetchPreviousPage = useCallback(async () => {
    if (state.isFetchingPreviousPage || !state.hasPreviousPage) return
    
    setState(prev => ({ ...prev, isFetchingPreviousPage: true }))
    
    try {
      const firstPage = state.pages[0]
      const previousPageParam = options.getPreviousPageParam?.(firstPage, state.pages)
      
      if (previousPageParam === undefined) {
        setState(prev => ({ ...prev, isFetchingPreviousPage: false, hasPreviousPage: false }))
        return
      }
      
      const newPage = await queryFn({ pageParam: previousPageParam })
      
      setState(prev => ({
        ...prev,
        pages: [newPage, ...prev.pages],
        pageParams: [previousPageParam, ...prev.pageParams],
        hasPreviousPage: options.getPreviousPageParam?.(newPage, [newPage, ...prev.pages]) !== undefined,
        isFetchingPreviousPage: false,
        isSuccess: true,
        lastFetch: Date.now()
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error as Error,
        isError: true,
        isFetchingPreviousPage: false
      }))
    }
  }, [state.pages, state.pageParams, state.isFetchingPreviousPage, state.hasPreviousPage, queryFn, options])
  
  const refetch = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null, isError: false }))
    
    try {
      const firstPage = await queryFn({ pageParam: undefined })
      
      setState({
        data: firstPage,
        error: null,
        isLoading: false,
        isFetching: false,
        isError: false,
        isSuccess: true,
        lastFetch: Date.now(),
        staleTime: options.staleTime || 5 * 60 * 1000,
        cacheTime: options.cacheTime || 10 * 60 * 1000,
        pages: [firstPage],
        pageParams: [undefined],
        hasNextPage: options.getNextPageParam?.(firstPage, [firstPage]) !== undefined,
        hasPreviousPage: false,
        isFetchingNextPage: false,
        isFetchingPreviousPage: false
      })
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error as Error,
        isError: true,
        isLoading: false
      }))
    }
  }, [queryFn, options])
  
  // 鍒濆鍔犺浇
  useEffect(() => {
    if (options.enabled !== false && state.pages.length === 0) {
      refetch()
    }
  }, [options.enabled, refetch, state.pages.length])
  
  return {
    ...state,
    fetchNextPage,
    fetchPreviousPage,
    refetch
  }
}

// 涔愯鏇存柊hook
export function useOptimisticMutation<T = any, V = any>(
  key: string,
  mutationFn: (variables: V) => Promise<T>,
  options: {
    onMutate?: (variables: V) => any
    onSuccess?: (data: T, variables: V, context: any) => void
    onError?: (error: Error, variables: V, context: any) => void
    onSettled?: (data: T | null, error: Error | null, variables: V, context: any) => void
  } = {}
) {
  const mutation = useMutation(key, mutationFn, {
    onSuccess: options.onSuccess,
    onError: options.onError,
    onSettled: options.onSettled
  })
  
  const mutateWithOptimisticUpdate = useCallback(async (variables: V) => {
    let context: any
    
    try {
      // 鎵ц涔愯鏇存柊
      context = options.onMutate?.(variables)
      
      // 鎵ц瀹為檯鐨刴utation
      const result = await mutation.mutate(variables)
      
      return result
    } catch (error) {
      // 濡傛灉澶辫触锛屽洖婊氫箰瑙傛洿鏂?
      throw error
    }
  }, [mutation, options])
  
  return {
    ...mutation,
    mutate: mutateWithOptimisticUpdate
  }
}

// 杞鏌ヨhook
export function usePollingQuery<T = any>(
  key: string | QueryKey,
  queryFn: () => Promise<T>,
  options: QueryOptions & {
    pollingInterval?: number
    pollingWhenHidden?: boolean
    pollingWhenOffline?: boolean
  } = {}
) {
  const queryKey = typeof key === 'string' ? key : createQueryKey(key)
  const query = useQuery(queryKey, queryFn, options)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  
  const startPolling = useCallback(() => {
    if (intervalRef.current || !options.pollingInterval) return
    
    setIsPolling(true)
    intervalRef.current = setInterval(() => {
      // 妫€鏌ユ槸鍚﹀簲璇ヨ疆璇?
      if (!options.pollingWhenHidden && document.hidden) return
      if (!options.pollingWhenOffline && !navigator.onLine) return
      
      query.refetch()
    }, options.pollingInterval)
  }, [options.pollingInterval, options.pollingWhenHidden, options.pollingWhenOffline, query])
  
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
      setIsPolling(false)
    }
  }, [])
  
  // 鑷姩寮€濮嬭疆璇?
  useEffect(() => {
    if (options.pollingInterval && options.enabled !== false) {
      startPolling()
    }
    
    return () => {
      stopPolling()
    }
  }, [options.pollingInterval, options.enabled, startPolling, stopPolling])
  
  // 椤甸潰鍙鎬у彉鍖栧鐞?
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (!options.pollingWhenHidden) {
          stopPolling()
        }
      } else {
        if (options.pollingInterval && options.enabled !== false) {
          startPolling()
        }
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [options.pollingInterval, options.pollingWhenHidden, options.enabled, startPolling, stopPolling])
  
  return {
    ...query,
    isPolling,
    startPolling,
    stopPolling
  }
}

// 鏌ヨ鐘舵€佽仛鍚坔ook
export function useQueryStatus(patterns: (string | QueryKey)[] = []) {
  const store = useQueryStore()
  const [status, setStatus] = useState({
    isLoading: false,
    isError: false,
    hasData: false,
    errorCount: 0,
    loadingCount: 0,
    successCount: 0
  })
  
  useEffect(() => {
    const unsubscribe = store.subscribe((state) => {
      const queries = Object.entries(state.queries)
      const relevantQueries = patterns.length > 0 
        ? queries.filter(([key]) => 
            patterns.some(pattern => {
              const patternKey = typeof pattern === 'string' ? pattern : createQueryKey(pattern)
              return key.includes(patternKey)
            })
          )
        : queries
      
      const stats = relevantQueries.reduce(
        (acc, [, query]) => {
          if (query.isLoading) acc.loadingCount++
          if (query.isError) acc.errorCount++
          if (query.isSuccess && query.data) acc.successCount++
          return acc
        },
        { loadingCount: 0, errorCount: 0, successCount: 0 }
      )
      
      setStatus({
        isLoading: stats.loadingCount > 0,
        isError: stats.errorCount > 0,
        hasData: stats.successCount > 0,
        ...stats
      })
    })
    
    return unsubscribe
  }, [patterns, store])
  
  return status
}

// 鏌ヨ閲嶈瘯hook
export function useRetryableQuery<T = any>(
  key: string | QueryKey,
  queryFn: () => Promise<T>,
  options: QueryOptions & {
    maxRetries?: number
    retryDelay?: number | ((attempt: number) => number)
    shouldRetry?: (error: Error, attempt: number) => boolean
  } = {}
) {
  const queryKey = typeof key === 'string' ? key : createQueryKey(key)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = options.maxRetries || 3
  
  const retryableQueryFn = useCallback(async (): Promise<T> => {
    let lastError: Error
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await queryFn()
        setRetryCount(0) // 閲嶇疆閲嶈瘯璁℃暟
        return result
      } catch (error) {
        lastError = error as Error
        
        // 妫€鏌ユ槸鍚﹀簲璇ラ噸璇?
        if (attempt < maxRetries && 
            (options.shouldRetry ? options.shouldRetry(lastError, attempt) : true)) {
          
          setRetryCount(attempt + 1)
          
          // 璁＄畻寤惰繜鏃堕棿
          const delay = typeof options.retryDelay === 'function' 
            ? options.retryDelay(attempt)
            : options.retryDelay || Math.pow(2, attempt) * 1000 // 鎸囨暟閫€閬?
          
          await new Promise(resolve => setTimeout(resolve, delay))
          continue
        }
        
        throw lastError
      }
    }
    
    throw lastError!
  }, [queryFn, maxRetries, options.retryDelay, options.shouldRetry])
  
  const query = useQuery(queryKey, retryableQueryFn, options)
  
  return {
    ...query,
    retryCount,
    maxRetries
  }
}