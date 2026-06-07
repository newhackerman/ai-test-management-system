// @ts-nocheck
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

interface RealtimeState {
  // WebSocket杩炴帴鐘舵€?
  isConnected: boolean
  isConnecting: boolean
  connectionError: string | null
  reconnectAttempts: number
  maxReconnectAttempts: number
  
  // 杩炴帴淇℃伅
  connectionId: string | null
  lastHeartbeat: Date | null
  connectionStartTime: Date | null
  
  // 璁㈤槄绠＄悊
  subscriptions: Set<string>
  eventHandlers: Record<string, ((data: any) => void)[]>
  
  // 鏁版嵁缂撳瓨
  realtimeData: Record<string, any>
  lastUpdate: Record<string, Date>
  
  // 娑堟伅闃熷垪
  messageQueue: Array<{
    id: string
    type: string
    data: any
    timestamp: Date
    retries: number
  }>
  
  // 绂荤嚎妯″紡
  isOffline: boolean
  offlineQueue: Array<{
    action: string
    data: any
    timestamp: Date
  }>
  
  // 鎬ц兘鐩戞帶
  latency: number
  messageCount: number
  errorCount: number
}

interface RealtimeActions {
  // 杩炴帴绠＄悊
  connect: (url: string, token: string) => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  
  // 杩炴帴鐘舵€?
  setConnected: (connected: boolean) => void
  setConnecting: (connecting: boolean) => void
  setConnectionError: (error: string | null) => void
  incrementReconnectAttempts: () => void
  resetReconnectAttempts: () => void
  
  // 蹇冭烦绠＄悊
  updateHeartbeat: () => void
  checkHeartbeat: () => boolean
  
  // 璁㈤槄绠＄悊
  subscribe: (eventTypes: string[]) => void
  unsubscribe: (eventTypes: string[]) => void
  addEventHandler: (eventType: string, handler: (data: any) => void) => () => void
  removeEventHandler: (eventType: string, handler: (data: any) => void) => void
  
  // 鏁版嵁绠＄悊
  updateRealtimeData: (key: string, data: any) => void
  getRealtimeData: (key: string) => any
  clearRealtimeData: (key?: string) => void
  
  // 娑堟伅澶勭悊
  handleMessage: (message: any) => void
  queueMessage: (type: string, data: any) => void
  processMessageQueue: () => void
  clearMessageQueue: () => void
  
  // 绂荤嚎妯″紡
  setOffline: (offline: boolean) => void
  queueOfflineAction: (action: string, data: any) => void
  processOfflineQueue: () => void
  clearOfflineQueue: () => void
  
  // 鎬ц兘鐩戞帶
  updateLatency: (latency: number) => void
  incrementMessageCount: () => void
  incrementErrorCount: () => void
  getPerformanceStats: () => {
    latency: number
    messageCount: number
    errorCount: number
    uptime: number
  }
  
  // 閲嶇疆
  reset: () => void
}

const initialState: RealtimeState = {
  isConnected: false,
  isConnecting: false,
  connectionError: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  
  connectionId: null,
  lastHeartbeat: null,
  connectionStartTime: null,
  
  subscriptions: new Set(),
  eventHandlers: {},
  
  realtimeData: {},
  lastUpdate: {},
  
  messageQueue: [],
  
  isOffline: false,
  offlineQueue: [],
  
  latency: 0,
  messageCount: 0,
  errorCount: 0
}

export const useRealtimeStore = create<RealtimeState & RealtimeActions>()(
  subscribeWithSelector(
    (set, get) => ({
      ...initialState,

      // 杩炴帴绠＄悊
      connect: async (url: string, token: string) => {
        const state = get()
        
        if (state.isConnected || state.isConnecting) {
          return
        }

        set((draft) => {
          draft.isConnecting = true
          draft.connectionError = null
          draft.connectionStartTime = new Date()
        })

        try {
          // 杩欓噷搴旇瀹炵幇瀹為檯鐨刉ebSocket杩炴帴閫昏緫
          // 鏆傛椂妯℃嫙杩炴帴鎴愬姛
          await new Promise(resolve => setTimeout(resolve, 1000))
          
          set((draft) => {
            draft.isConnected = true
            draft.isConnecting = false
            draft.connectionId = `conn_${Date.now()}`
            draft.lastHeartbeat = new Date()
            draft.reconnectAttempts = 0
          })
        } catch (error) {
          set((draft) => {
            draft.isConnecting = false
            draft.connectionError = error instanceof Error ? error.message : '杩炴帴澶辫触'
            draft.errorCount += 1
          })
          throw error
        }
      },

      disconnect: () => {
        set((draft) => {
          draft.isConnected = false
          draft.isConnecting = false
          draft.connectionId = null
          draft.lastHeartbeat = null
          draft.connectionStartTime = null
          draft.subscriptions.clear()
          draft.eventHandlers = {}
        })
      },

      reconnect: async () => {
        const state = get()
        
        if (state.reconnectAttempts >= state.maxReconnectAttempts) {
          set((draft) => {
            draft.connectionError = '閲嶈繛娆℃暟瓒呰繃闄愬埗'
          })
          return
        }

        set((draft) => {
          draft.reconnectAttempts += 1
        })

        // 鎸囨暟閫€閬块噸杩?
        const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 30000)
        await new Promise(resolve => setTimeout(resolve, delay))

        try {
          // 閲嶆柊杩炴帴閫昏緫
          await get().connect('', '') // 浣跨敤涔嬪墠鐨勮繛鎺ュ弬鏁?
        } catch (error) {
          // 閲嶈繛澶辫触锛屽彲鑳戒細鍐嶆灏濊瘯
        }
      },

      // 杩炴帴鐘舵€?
      setConnected: (connected) => {
        set((draft) => {
          draft.isConnected = connected
          if (!connected) {
            draft.connectionId = null
            draft.lastHeartbeat = null
          }
        })
      },

      setConnecting: (connecting) => {
        set((draft) => {
          draft.isConnecting = connecting
        })
      },

      setConnectionError: (error) => {
        set((draft) => {
          draft.connectionError = error
        })
      },

      incrementReconnectAttempts: () => {
        set((draft) => {
          draft.reconnectAttempts += 1
        })
      },

      resetReconnectAttempts: () => {
        set((draft) => {
          draft.reconnectAttempts = 0
        })
      },

      // 蹇冭烦绠＄悊
      updateHeartbeat: () => {
        set((draft) => {
          draft.lastHeartbeat = new Date()
        })
      },

      checkHeartbeat: () => {
        const state = get()
        if (!state.lastHeartbeat) return false
        
        const now = new Date()
        const timeDiff = now.getTime() - state.lastHeartbeat.getTime()
        return timeDiff < 60000 // 1鍒嗛挓鍐呮湁蹇冭烦璁や负杩炴帴姝ｅ父
      },

      // 璁㈤槄绠＄悊
      subscribe: (eventTypes) => {
        set((draft) => {
          eventTypes.forEach(type => {
            draft.subscriptions.add(type)
          })
        })
      },

      unsubscribe: (eventTypes) => {
        set((draft) => {
          eventTypes.forEach(type => {
            draft.subscriptions.delete(type)
            delete draft.eventHandlers[type]
          })
        })
      },

      addEventHandler: (eventType, handler) => {
        set((draft) => {
          if (!draft.eventHandlers[eventType]) {
            draft.eventHandlers[eventType] = []
          }
          draft.eventHandlers[eventType].push(handler)
        })

        // 杩斿洖鍙栨秷璁㈤槄鍑芥暟
        return () => {
          get().removeEventHandler(eventType, handler)
        }
      },

      removeEventHandler: (eventType, handler) => {
        set((draft) => {
          if (draft.eventHandlers[eventType]) {
            const index = draft.eventHandlers[eventType].indexOf(handler)
            if (index > -1) {
              draft.eventHandlers[eventType].splice(index, 1)
            }
            
            if (draft.eventHandlers[eventType].length === 0) {
              delete draft.eventHandlers[eventType]
            }
          }
        })
      },

      // 鏁版嵁绠＄悊
      updateRealtimeData: (key, data) => {
        set((draft) => {
          draft.realtimeData[key] = data
          draft.lastUpdate[key] = new Date()
        })
      },

      getRealtimeData: (key) => {
        return get().realtimeData[key]
      },

      clearRealtimeData: (key) => {
        set((draft) => {
          if (key) {
            delete draft.realtimeData[key]
            delete draft.lastUpdate[key]
          } else {
            draft.realtimeData = {}
            draft.lastUpdate = {}
          }
        })
      },

      // 娑堟伅澶勭悊
      handleMessage: (message) => {
        const state = get()
        
        set((draft) => {
          draft.messageCount += 1
        })

        try {
          const { type, data, timestamp } = message

          // 鏇存柊寤惰繜
          if (timestamp) {
            const latency = Date.now() - new Date(timestamp).getTime()
            get().updateLatency(latency)
          }

          // 澶勭悊涓嶅悓绫诲瀷鐨勬秷鎭?
          switch (type) {
            case 'heartbeat':
              get().updateHeartbeat()
              break
              
            case 'data_update':
              get().updateRealtimeData(data.key || 'default', data)
              break
              
            case 'event':
              // 瑙﹀彂浜嬩欢澶勭悊鍣?
              const handlers = state.eventHandlers[data.event_type] || []
              handlers.forEach(handler => {
                try {
                  handler(data)
                } catch (error) {
                  console.error('浜嬩欢澶勭悊鍣ㄦ墽琛屽け璐?', error)
                }
              })
              break
              
            default:
              console.warn('鏈煡娑堟伅绫诲瀷:', type)
          }
        } catch (error) {
          set((draft) => {
            draft.errorCount += 1
          })
          console.error('娑堟伅澶勭悊澶辫触:', error)
        }
      },

      queueMessage: (type, data) => {
        set((draft) => {
          draft.messageQueue.push({
            id: `msg_${Date.now()}_${Math.random()}`,
            type,
            data,
            timestamp: new Date(),
            retries: 0
          })
        })
      },

      processMessageQueue: () => {
        const state = get()
        
        if (!state.isConnected || state.messageQueue.length === 0) {
          return
        }

        set((draft) => {
          draft.messageQueue = draft.messageQueue.filter(message => {
            try {
              // 杩欓噷搴旇鍙戦€佹秷鎭埌WebSocket
              console.log('鍙戦€佹秷鎭?', message)
              return false // 鍙戦€佹垚鍔燂紝浠庨槦鍒椾腑绉婚櫎
            } catch (error) {
              message.retries += 1
              if (message.retries >= 3) {
                console.error('娑堟伅鍙戦€佸け璐ワ紝宸茶揪鍒版渶澶ч噸璇曟鏁?', message)
                return false // 绉婚櫎澶辫触鐨勬秷鎭?
              }
              return true // 淇濈暀鍦ㄩ槦鍒椾腑閲嶈瘯
            }
          })
        })
      },

      clearMessageQueue: () => {
        set((draft) => {
          draft.messageQueue = []
        })
      },

      // 绂荤嚎妯″紡
      setOffline: (offline) => {
        set((draft) => {
          draft.isOffline = offline
        })
      },

      queueOfflineAction: (action, data) => {
        set((draft) => {
          draft.offlineQueue.push({
            action,
            data,
            timestamp: new Date()
          })
        })
      },

      processOfflineQueue: () => {
        const state = get()
        
        if (state.isOffline || state.offlineQueue.length === 0) {
          return
        }

        set((draft) => {
          draft.offlineQueue.forEach(item => {
            // 澶勭悊绂荤嚎鏈熼棿鐨勬搷浣?
            console.log('澶勭悊绂荤嚎鎿嶄綔:', item)
          })
          draft.offlineQueue = []
        })
      },

      clearOfflineQueue: () => {
        set((draft) => {
          draft.offlineQueue = []
        })
      },

      // 鎬ц兘鐩戞帶
      updateLatency: (latency) => {
        set((draft) => {
          // 浣跨敤绉诲姩骞冲潎璁＄畻寤惰繜
          draft.latency = draft.latency === 0 ? latency : (draft.latency * 0.8 + latency * 0.2)
        })
      },

      incrementMessageCount: () => {
        set((draft) => {
          draft.messageCount += 1
        })
      },

      incrementErrorCount: () => {
        set((draft) => {
          draft.errorCount += 1
        })
      },

      getPerformanceStats: () => {
        const state = get()
        const uptime = state.connectionStartTime 
          ? Date.now() - state.connectionStartTime.getTime()
          : 0

        return {
          latency: state.latency,
          messageCount: state.messageCount,
          errorCount: state.errorCount,
          uptime
        }
      },

      // 閲嶇疆
      reset: () => {
        set(() => ({
          ...initialState,
          subscriptions: new Set(),
          eventHandlers: {}
        }))
      }
    }))
)

// 閫夋嫨鍣ㄥ嚱鏁?
export const realtimeSelectors = {
  isConnected: (state: RealtimeState & RealtimeActions) => state.isConnected,
  isConnecting: (state: RealtimeState & RealtimeActions) => state.isConnecting,
  connectionError: (state: RealtimeState & RealtimeActions) => state.connectionError,
  realtimeData: (state: RealtimeState & RealtimeActions) => state.realtimeData,
  subscriptions: (state: RealtimeState & RealtimeActions) => state.subscriptions,
  isOffline: (state: RealtimeState & RealtimeActions) => state.isOffline,
  latency: (state: RealtimeState & RealtimeActions) => state.latency
}

// 杩炴帴鐘舵€佺洃鍚櫒
export const subscribeToConnectionStatus = (callback: (isConnected: boolean) => void) => {
  return useRealtimeStore.subscribe(
    (state) => state.isConnected,
    callback
  )
}

// 瀹炴椂鏁版嵁鐩戝惉鍣?
export const subscribeToRealtimeData = (key: string, callback: (data: any) => void) => {
  return useRealtimeStore.subscribe(
    (state) => state.realtimeData[key],
    callback
  )
}

// 閿欒鐩戝惉鍣?
export const subscribeToConnectionErrors = (callback: (error: string | null) => void) => {
  return useRealtimeStore.subscribe(
    (state) => state.connectionError,
    callback
  )
}
