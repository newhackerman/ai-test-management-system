// @ts-nocheck
// 楂樼骇鏌ヨ瀹㈡埛绔?- 绫讳技React Query鐨勫姛鑳?

import { useQueryStore, QueryOptions, QueryState, MutationState } from '@/stores/query'

export interface QueryKey {
    scope: string
    id?: string | number
    params?: Record<string, any>
}

export interface InfiniteQueryOptions extends QueryOptions {
    getNextPageParam?: (lastPage: any, allPages: any[]) => any
    getPreviousPageParam?: (firstPage: any, allPages: any[]) => any
}

export interface InfiniteQueryState<T = any> extends QueryState<T> {
    pages: T[]
    pageParams: any[]
    hasNextPage: boolean
    hasPreviousPage: boolean
    isFetchingNextPage: boolean
    isFetchingPreviousPage: boolean
}

// 鏌ヨ閿敓鎴愬櫒
export const createQueryKey = (key: QueryKey): string => {
    const parts = [key.scope]

    if (key.id !== undefined) {
        parts.push(String(key.id))
    }

    if (key.params) {
        const sortedParams = Object.keys(key.params)
            .sort()
            .map(k => `${k}:${JSON.stringify(key.params![k])}`)
            .join(',')
        parts.push(sortedParams)
    }

    return parts.join('|')
}

// 鏌ヨ閿尮閰嶅櫒
export const matchQueryKey = (pattern: string, key: string): boolean => {
    const patternParts = pattern.split('|')
    const keyParts = key.split('|')

    for (let i = 0; i < patternParts.length; i++) {
        const patternPart = patternParts[i]
        const keyPart = keyParts[i]

        if (patternPart === '*') continue
        if (patternPart !== keyPart) return false
    }

    return true
}

// 楂樼骇鏌ヨ瀹㈡埛绔?
export class QueryClient {
    private store = useQueryStore

    // 鑾峰彇鏌ヨ鏁版嵁
    getQueryData<T = any>(key: string | QueryKey): T | undefined {
        const queryKey = typeof key === 'string' ? key : createQueryKey(key)
        const state = this.store.getState().getQueryState(queryKey)
        return state?.data
    }

    // 璁剧疆鏌ヨ鏁版嵁
    setQueryData<T = any>(key: string | QueryKey, data: T | ((oldData: T | undefined) => T)): void {
        const queryKey = typeof key === 'string' ? key : createQueryKey(key)

        if (typeof data === 'function') {
            const oldData = this.getQueryData<T>(queryKey)
            const newData = (data as Function)(oldData)
            this.store.getState().setQueryData(queryKey, newData)
        } else {
            this.store.getState().setQueryData(queryKey, data)
        }
    }

    // 浣挎煡璇㈡棤鏁?
    invalidateQueries(pattern?: string | QueryKey): void {
        const patternKey = typeof pattern === 'string' ? pattern :
            pattern ? createQueryKey(pattern) : undefined

        const store = this.store.getState()
        const keys = Object.keys(store.queries)

        keys.forEach(key => {
            if (!patternKey || matchQueryKey(patternKey, key)) {
                store.invalidateQuery(key)
            }
        })
    }

    // 绉婚櫎鏌ヨ
    removeQueries(pattern?: string | QueryKey): void {
        const patternKey = typeof pattern === 'string' ? pattern :
            pattern ? createQueryKey(pattern) : undefined

        const store = this.store.getState()
        const keys = Object.keys(store.queries)

        keys.forEach(key => {
            if (!patternKey || matchQueryKey(patternKey, key)) {
                store.removeQuery(key)
            }
        })
    }

    // 閲嶆柊鑾峰彇鏌ヨ
    async refetchQueries(pattern?: string | QueryKey): Promise<void> {
        const patternKey = typeof pattern === 'string' ? pattern :
            pattern ? createQueryKey(pattern) : undefined

        const store = this.store.getState()
        const keys = Object.keys(store.queries)

        const promises = keys
            .filter(key => !patternKey || matchQueryKey(patternKey, key))
            .map(key => {
                // 杩欓噷闇€瑕佽Е鍙戦噸鏂拌幏鍙栵紝浣嗙敱浜庢垜浠病鏈夊瓨鍌ㄥ師濮嬬殑queryFn锛?
                // 瀹為檯鐨勯噸鏂拌幏鍙栭渶瑕佸湪缁勪欢灞傞潰澶勭悊
                store.invalidateQuery(key)
                return Promise.resolve()
            })

        await Promise.all(promises)
    }

    // 棰勫彇鏁版嵁
    async prefetchQuery<T = any>(
        key: string | QueryKey,
        queryFn: () => Promise<T>,
        options: QueryOptions = {}
    ): Promise<T> {
        const queryKey = typeof key === 'string' ? key : createQueryKey(key)
        const store = this.store.getState()
        const existingQuery = store.getQueryState(queryKey)

        // 濡傛灉鏁版嵁宸插瓨鍦ㄤ笖鏈繃鏈燂紝鐩存帴杩斿洖
        if (existingQuery?.data && !this.isStale(existingQuery)) {
            return existingQuery.data
        }

        // 鍚﹀垯鑾峰彇鏂版暟鎹?
        store.setQueryLoading(queryKey, true)

        try {
            const data = await queryFn()
            store.setQueryData(queryKey, data)
            return data
        } catch (error) {
            store.setQueryError(queryKey, error as Error)
            throw error
        }
    }

    // 妫€鏌ユ暟鎹槸鍚﹁繃鏈?
    private isStale(query: QueryState): boolean {
        if (query.lastFetch === 0) return true
        return Date.now() - query.lastFetch > query.staleTime
    }

    // 鑾峰彇鏌ヨ鐘舵€?
    getQueryState(key: string | QueryKey): QueryState | undefined {
        const queryKey = typeof key === 'string' ? key : createQueryKey(key)
        return this.store.getState().getQueryState(queryKey)
    }

    // 鑾峰彇鎵€鏈夋煡璇?
    getQueriesData(pattern?: string | QueryKey): Array<[string, any]> {
        const patternKey = typeof pattern === 'string' ? pattern :
            pattern ? createQueryKey(pattern) : undefined

        const store = this.store.getState()
        const keys = Object.keys(store.queries)

        return keys
            .filter(key => !patternKey || matchQueryKey(patternKey, key))
            .map(key => [key, store.queries[key].data])
            .filter(([, data]) => data !== null)
    }

    // 娓呴櫎鎵€鏈夋煡璇?
    clear(): void {
        this.store.getState().clearAll()
    }

    // 鍙栨秷鏌ヨ锛堟爣璁颁负宸插彇娑堬級
    cancelQueries(pattern?: string | QueryKey): void {
        const patternKey = typeof pattern === 'string' ? pattern :
            pattern ? createQueryKey(pattern) : undefined

        const store = this.store.getState()
        const keys = Object.keys(store.queries)

        keys.forEach(key => {
            if (!patternKey || matchQueryKey(patternKey, key)) {
                const query = store.queries[key]
                if (query.isLoading || query.isFetching) {
                    store.setQueryLoading(key, false)
                    store.setQueryFetching(key, false)
                }
            }
        })
    }

    // 鑾峰彇鏌ヨ缂撳瓨澶у皬
    getCacheSize(): number {
        const store = this.store.getState()
        return Object.keys(store.queries).length
    }

    // 鑾峰彇鏌ヨ缁熻淇℃伅
    getQueryStats(): {
        total: number
        loading: number
        error: number
        success: number
        stale: number
    } {
        const store = this.store.getState()
        const queries = Object.values(store.queries)

        return {
            total: queries.length,
            loading: queries.filter(q => q.isLoading).length,
            error: queries.filter(q => q.isError).length,
            success: queries.filter(q => q.isSuccess).length,
            stale: queries.filter(q => this.isStale(q)).length
        }
    }
}

// 鍏ㄥ眬鏌ヨ瀹㈡埛绔疄渚?
export const queryClient = new QueryClient()

// 鏌ヨ閿伐鍘?
export const queryKeys = {
  // 鐢ㄦ埛鐩稿叧
  users: {
    all: () => createQueryKey({ scope: 'users' }),
    lists: () => createQueryKey({ scope: 'users', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'users', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'users', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'users', id: 'detail', params: { id } }),
  },
  
  // 椤圭洰鐩稿叧
  projects: {
    all: () => createQueryKey({ scope: 'projects' }),
    lists: () => createQueryKey({ scope: 'projects', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'projects', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'projects', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'projects', id: 'detail', params: { id } }),
    members: (projectId: string | number) => createQueryKey({ scope: 'projects', id: 'members', params: { projectId } }),
  },
  
  // 娴嬭瘯鐢ㄤ緥鐩稿叧
  testCases: {
    all: () => createQueryKey({ scope: 'test-cases' }),
    lists: () => createQueryKey({ scope: 'test-cases', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'test-cases', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'test-cases', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'test-cases', id: 'detail', params: { id } }),
    byProject: (projectId: string | number) => createQueryKey({ scope: 'test-cases', id: 'by-project', params: { projectId } }),
  },
  
  // 娴嬭瘯杩愯鐩稿叧
  testRuns: {
    all: () => createQueryKey({ scope: 'test-runs' }),
    lists: () => createQueryKey({ scope: 'test-runs', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'test-runs', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'test-runs', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'test-runs', id: 'detail', params: { id } }),
    byProject: (projectId: string | number) => createQueryKey({ scope: 'test-runs', id: 'by-project', params: { projectId } }),
  },
  
  // 浠〃鏉跨浉鍏?
  dashboard: {
    stats: () => createQueryKey({ scope: 'dashboard', id: 'stats' }),
    charts: (type: string) => createQueryKey({ scope: 'dashboard', id: 'charts', params: { type } }),
    activities: () => createQueryKey({ scope: 'dashboard', id: 'activities' }),
  },
  
  // 闇€姹傜鐞嗙浉鍏?
  requirements: {
    all: () => createQueryKey({ scope: 'requirements' }),
    lists: () => createQueryKey({ scope: 'requirements', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'requirements', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'requirements', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'requirements', id: 'detail', params: { id } }),
    byProject: (projectId: string | number) => createQueryKey({ scope: 'requirements', id: 'by-project', params: { projectId } }),
  },
  
  // 浠诲姟绠＄悊鐩稿叧
  tasks: {
    all: () => createQueryKey({ scope: 'tasks' }),
    lists: () => createQueryKey({ scope: 'tasks', id: 'list' }),
    list: (filters: any) => createQueryKey({ scope: 'tasks', id: 'list', params: filters }),
    details: () => createQueryKey({ scope: 'tasks', id: 'detail' }),
    detail: (id: string | number) => createQueryKey({ scope: 'tasks', id: 'detail', params: { id } }),
    byProject: (projectId: string | number) => createQueryKey({ scope: 'tasks', id: 'by-project', params: { projectId } }),
    byAssignee: (userId: string | number) => createQueryKey({ scope: 'tasks', id: 'by-assignee', params: { userId } }),
  }
}