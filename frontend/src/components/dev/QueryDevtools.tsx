// @ts-nocheck
// React Query寮€鍙戝伐鍏?- 瀹屾暣瀹炵幇

import React, { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Bug, 
  Database, 
  RefreshCw, 
  Trash2, 
  Eye, 
  EyeOff, 
  Clock,
  AlertCircle,
  CheckCircle,
  Loader,
  X,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  BarChart3
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Separator } from '@/components/ui/Separator'
import { cn } from '@/lib/utils'

interface QueryInfo {
  queryKey: readonly unknown[]
  queryHash: string
  status: 'idle' | 'loading' | 'error' | 'success'
  dataUpdatedAt: number
  errorUpdatedAt: number
  fetchStatus: 'idle' | 'fetching' | 'paused'
  isStale: boolean
  observersCount: number
  data?: any
  error?: any
}

interface QueryDevtoolsProps {
  initialIsOpen?: boolean
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  panelProps?: React.HTMLAttributes<HTMLDivElement>
  closeButtonProps?: React.ButtonHTMLAttributes<HTMLButtonElement>
  toggleButtonProps?: React.ButtonHTMLAttributes<HTMLButtonElement>
}

/**
 * React Query寮€鍙戝伐鍏风粍浠?
 */
export function QueryDevtools({
  initialIsOpen = false,
  position = 'bottom-right',
  panelProps,
  closeButtonProps,
  toggleButtonProps
}: QueryDevtoolsProps) {
  const [isOpen, setIsOpen] = useState(initialIsOpen)
  const [selectedQuery, setSelectedQuery] = useState<QueryInfo | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [queries, setQueries] = useState<QueryInfo[]>([])
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    stale: 0,
    error: 0,
    loading: 0
  })

  const queryClient = useQueryClient()

  // 鏇存柊鏌ヨ鍒楄〃
  const updateQueries = () => {
    const cache = queryClient.getQueryCache()
    const allQueries = cache.getAll()

    const queryInfos: QueryInfo[] = allQueries.map(query => ({
      queryKey: query.queryKey,
      queryHash: query.queryHash,
      status: query.state.status,
      dataUpdatedAt: query.state.dataUpdatedAt,
      errorUpdatedAt: query.state.errorUpdatedAt,
      fetchStatus: query.state.fetchStatus,
      isStale: query.isStale(),
      observersCount: query.getObserversCount(),
      data: query.state.data,
      error: query.state.error
    }))

    setQueries(queryInfos)

    // 鏇存柊缁熻淇℃伅
    setStats({
      total: queryInfos.length,
      active: queryInfos.filter(q => q.observersCount > 0).length,
      stale: queryInfos.filter(q => q.isStale).length,
      error: queryInfos.filter(q => q.status === 'error').length,
      loading: queryInfos.filter(q => q.status === 'loading').length
    })
  }

  // 鐩戝惉鏌ヨ鍙樺寲
  useEffect(() => {
    if (!isOpen) return

    updateQueries()
    
    const unsubscribe = queryClient.getQueryCache().subscribe(() => {
      updateQueries()
    })

    const interval = setInterval(updateQueries, 1000)

    return () => {
      unsubscribe()
      clearInterval(interval)
    }
  }, [isOpen, queryClient])

  // 杩囨护鏌ヨ
  const filteredQueries = queries.filter(query => {
    const matchesSearch = searchTerm === '' || 
      JSON.stringify(query.queryKey).toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || query.status === statusFilter

    return matchesSearch && matchesStatus
  })

  // 鑾峰彇鐘舵€侀鑹?
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-500 dark:text-green-400'
      case 'error': return 'text-red-500 dark:text-red-400'
      case 'loading': return 'text-blue-500 dark:text-blue-400'
      default: return 'text-gray-500 dark:text-gray-400'
    }
  }

  // 鑾峰彇鐘舵€佸浘鏍?
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-4 w-4" />
      case 'error': return <AlertCircle className="h-4 w-4" />
      case 'loading': return <Loader className="h-4 w-4 animate-spin" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  // 鏍煎紡鍖栨椂闂?
  const formatTime = (timestamp: number) => {
    if (!timestamp) return 'Never'
    const now = Date.now()
    const diff = now - timestamp
    
    if (diff < 1000) return 'Just now'
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    return `${Math.floor(diff / 3600000)}h ago`
  }

  // 鍒囨崲闈㈡澘
  const togglePanel = () => {
    setIsOpen(!isOpen)
    if (!isOpen) {
      setSelectedQuery(null)
    }
  }

  // 鍒锋柊鏌ヨ
  const refetchQuery = (queryKey: readonly unknown[]) => {
    queryClient.refetchQueries({ queryKey })
  }

  // 浣挎煡璇㈠け鏁?
  const invalidateQuery = (queryKey: readonly unknown[]) => {
    queryClient.invalidateQueries({ queryKey })
  }

  // 绉婚櫎鏌ヨ
  const removeQuery = (queryKey: readonly unknown[]) => {
    queryClient.removeQueries({ queryKey })
    setSelectedQuery(null)
  }

  // 娓呴櫎鎵€鏈夋煡璇?
  const clearAllQueries = () => {
    queryClient.clear()
    setSelectedQuery(null)
  }

  // 鑾峰彇浣嶇疆鏍峰紡
  const getPositionStyles = () => {
    switch (position) {
      case 'top-left':
        return 'top-4 left-4'
      case 'top-right':
        return 'top-4 right-4'
      case 'bottom-left':
        return 'bottom-4 left-4'
      case 'bottom-right':
      default:
        return 'bottom-4 right-4'
    }
  }

  if (process.env.NODE_ENV === 'production') {
    return null
  }

  return (
    <>
      {/* 鍒囨崲鎸夐挳 */}
      <motion.div
        className={cn('fixed z-50', getPositionStyles())}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      >
        <Button
          onClick={togglePanel}
          size="icon"
          variant={isOpen ? 'default' : 'outline'}
          className="h-12 w-12 rounded-full shadow-lg"
          {...toggleButtonProps}
        >
          <Database className="h-5 w-5" />
        </Button>
      </motion.div>

      {/* 寮€鍙戝伐鍏烽潰鏉?*/}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-4 z-40 bg-background border rounded-lg shadow-2xl overflow-hidden"
            {...panelProps}
          >
            <div className="flex h-full">
              {/* 宸︿晶闈㈡澘 - 鏌ヨ鍒楄〃 */}
              <div className="w-1/2 border-r flex flex-col">
                {/* 澶撮儴 */}
                <div className="p-4 border-b bg-muted/50">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Database className="h-5 w-5" />
                      <h2 className="text-lg font-semibold">Query Devtools</h2>
                    </div>
                    <Button
                      onClick={togglePanel}
                      size="icon"
                      variant="ghost"
                      {...closeButtonProps}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* 缁熻淇℃伅 */}
                  <div className="grid grid-cols-5 gap-2 mb-4">
                    <div className="text-center">
                      <div className="text-lg font-bold">{stats.total}</div>
                      <div className="text-xs text-muted-foreground">Total</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-500 dark:text-blue-400">{stats.active}</div>
                      <div className="text-xs text-muted-foreground">Active</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-yellow-500">{stats.stale}</div>
                      <div className="text-xs text-muted-foreground">Stale</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-red-500 dark:text-red-400">{stats.error}</div>
                      <div className="text-xs text-muted-foreground">Error</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-500 dark:text-blue-400">{stats.loading}</div>
                      <div className="text-xs text-muted-foreground">Loading</div>
                    </div>
                  </div>

                  {/* 鎼滅储鍜岃繃婊?*/}
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search queries..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="px-3 py-2 border rounded-md bg-background"
                    >
                      <option value="all">All</option>
                      <option value="success">Success</option>
                      <option value="error">Error</option>
                      <option value="loading">Loading</option>
                      <option value="idle">Idle</option>
                    </select>
                  </div>

                  {/* 鎿嶄綔鎸夐挳 */}
                  <div className="flex gap-2 mt-4">
                    <Button
                      onClick={updateQueries}
                      size="sm"
                      variant="outline"
                      className="flex items-center gap-1"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Refresh
                    </Button>
                    <Button
                      onClick={clearAllQueries}
                      size="sm"
                      variant="outline"
                      className="flex items-center gap-1"
                    >
                      <Trash2 className="h-3 w-3" />
                      Clear All
                    </Button>
                  </div>
                </div>

                {/* 鏌ヨ鍒楄〃 */}
                <div className="flex-1 overflow-auto">
                  {filteredQueries.map((query) => (
                    <div
                      key={query.queryHash}
                      onClick={() => setSelectedQuery(query)}
                      className={cn(
                        'p-3 border-b cursor-pointer hover:bg-muted/50 transition-colors',
                        selectedQuery?.queryHash === query.queryHash && 'bg-muted'
                      )}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={getStatusColor(query.status)}>
                            {getStatusIcon(query.status)}
                          </div>
                          <Badge variant={query.isStale ? 'destructive' : 'secondary'}>
                            {query.isStale ? 'Stale' : 'Fresh'}
                          </Badge>
                          {query.observersCount > 0 && (
                            <Badge variant="outline">
                              {query.observersCount} observer{query.observersCount > 1 ? 's' : ''}
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatTime(query.dataUpdatedAt)}
                        </div>
                      </div>
                      <div className="text-sm font-mono text-muted-foreground truncate">
                        {JSON.stringify(query.queryKey)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 鍙充晶闈㈡澘 - 鏌ヨ璇︽儏 */}
              <div className="w-1/2 flex flex-col">
                {selectedQuery ? (
                  <>
                    {/* 鏌ヨ璇︽儏澶撮儴 */}
                    <div className="p-4 border-b bg-muted/50">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={getStatusColor(selectedQuery.status)}>
                            {getStatusIcon(selectedQuery.status)}
                          </div>
                          <span className="font-semibold">Query Details</span>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => refetchQuery(selectedQuery.queryKey)}
                            size="sm"
                            variant="outline"
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Refetch
                          </Button>
                          <Button
                            onClick={() => invalidateQuery(selectedQuery.queryKey)}
                            size="sm"
                            variant="outline"
                          >
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Invalidate
                          </Button>
                          <Button
                            onClick={() => removeQuery(selectedQuery.queryKey)}
                            size="sm"
                            variant="outline"
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            Remove
                          </Button>
                        </div>
                      </div>
                      <div className="text-sm font-mono bg-background p-2 rounded border">
                        {JSON.stringify(selectedQuery.queryKey, null, 2)}
                      </div>
                    </div>

                    {/* 鏌ヨ璇︽儏鍐呭 */}
                    <div className="flex-1 overflow-auto p-4">
                      <Tabs defaultValue="data" className="h-full">
                        <TabsList className="grid w-full grid-cols-4">
                          <TabsTrigger value="data">Data</TabsTrigger>
                          <TabsTrigger value="error">Error</TabsTrigger>
                          <TabsTrigger value="info">Info</TabsTrigger>
                          <TabsTrigger value="actions">Actions</TabsTrigger>
                        </TabsList>

                        <TabsContent value="data" className="mt-4">
                          <Card>
                            <CardHeader>
                              <CardTitle className="text-sm">Query Data</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-96">
                                {selectedQuery.data 
                                  ? JSON.stringify(selectedQuery.data, null, 2)
                                  : 'No data'
                                }
                              </pre>
                            </CardContent>
                          </Card>
                        </TabsContent>

                        <TabsContent value="error" className="mt-4">
                          <Card>
                            <CardHeader>
                              <CardTitle className="text-sm">Query Error</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-96">
                                {selectedQuery.error 
                                  ? JSON.stringify(selectedQuery.error, null, 2)
                                  : 'No error'
                                }
                              </pre>
                            </CardContent>
                          </Card>
                        </TabsContent>

                        <TabsContent value="info" className="mt-4">
                          <div className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle className="text-sm">Query Information</CardTitle>
                              </CardHeader>
                              <CardContent className="space-y-2">
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Status:</span>
                                  <Badge variant={selectedQuery.status === 'success' ? 'default' : 'destructive'}>
                                    {selectedQuery.status}
                                  </Badge>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Fetch Status:</span>
                                  <span className="text-sm">{selectedQuery.fetchStatus}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Is Stale:</span>
                                  <Badge variant={selectedQuery.isStale ? 'destructive' : 'secondary'}>
                                    {selectedQuery.isStale ? 'Yes' : 'No'}
                                  </Badge>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Observers:</span>
                                  <span className="text-sm">{selectedQuery.observersCount}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Data Updated:</span>
                                  <span className="text-sm">{formatTime(selectedQuery.dataUpdatedAt)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm text-muted-foreground">Error Updated:</span>
                                  <span className="text-sm">{formatTime(selectedQuery.errorUpdatedAt)}</span>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        </TabsContent>

                        <TabsContent value="actions" className="mt-4">
                          <div className="space-y-2">
                            <Button
                              onClick={() => refetchQuery(selectedQuery.queryKey)}
                              className="w-full justify-start"
                              variant="outline"
                            >
                              <RefreshCw className="h-4 w-4 mr-2" />
                              Refetch Query
                            </Button>
                            <Button
                              onClick={() => invalidateQuery(selectedQuery.queryKey)}
                              className="w-full justify-start"
                              variant="outline"
                            >
                              <AlertCircle className="h-4 w-4 mr-2" />
                              Invalidate Query
                            </Button>
                            <Button
                              onClick={() => removeQuery(selectedQuery.queryKey)}
                              className="w-full justify-start"
                              variant="outline"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Remove Query
                            </Button>
                            <Separator />
                            <Button
                              onClick={() => {
                                navigator.clipboard.writeText(JSON.stringify(selectedQuery.queryKey))
                              }}
                              className="w-full justify-start"
                              variant="outline"
                            >
                              Copy Query Key
                            </Button>
                            <Button
                              onClick={() => {
                                navigator.clipboard.writeText(JSON.stringify(selectedQuery.data, null, 2))
                              }}
                              className="w-full justify-start"
                              variant="outline"
                            >
                              Copy Query Data
                            </Button>
                          </div>
                        </TabsContent>
                      </Tabs>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Select a query to view details</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

/**
 * Query Devtools Provider
 * 鐢ㄤ簬鍦ㄥ紑鍙戠幆澧冧腑鎻愪緵鏌ヨ寮€鍙戝伐鍏?
 */
export function QueryDevtoolsProvider({ 
  children,
  ...devtoolsProps 
}: { 
  children: React.ReactNode 
} & QueryDevtoolsProps) {
  return (
    <>
      {children}
      <QueryDevtools {...devtoolsProps} />
    </>
  )
}

export default QueryDevtools