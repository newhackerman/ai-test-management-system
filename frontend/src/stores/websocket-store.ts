// @ts-nocheck
// WebSocket鐘舵€佺鐞?- 瀹屾暣瀹炵幇

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { WebSocketClient, ConnectionState, WebSocketMessage } from '@/lib/websocket-client'

export interface WebSocketState {
  // 杩炴帴鐘舵€?
  connectionState: ConnectionState
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean

  // 閲嶈繛淇℃伅
  reconnectAttempts: number
  maxReconnectAttempts: number
  nextReconnectDelay: number

  // 閿欒淇℃伅
  lastError: Error | null
  errorHistory: Array<{
    error: Error
    timestamp: Date
  }>

  // 缁熻淇℃伅
  stats: WebSocketStats

  // 娑堟伅鍘嗗彶
  messageHistory: WebSocketMessage[]
  maxHistorySize: number
  messages: WebSocketMessage[]

  // 瀹㈡埛绔紩鐢?
  client: WebSocketClient | null

  // 蹇冭烦淇℃伅
  lastHeartbeat: number

  // 閰嶇疆
  config: {
    url: string
    debug: boolean
    autoConnect: boolean
    heartbeatInterval: number
  }
}

export interface WebSocketActions {
  // 杩炴帴绠＄悊
  connect: () => void
  disconnect: () => void
  reconnect: () => void

  // 娑堟伅鍙戦€?
  sendMessage: (message: Omit<WebSocketMessage, 'timestamp' | 'id'>) => boolean

  // 鐘舵€佹洿鏂?
  setConnectionState: (state: ConnectionState) => void
  setConnected: (connected: boolean) => void
  setReconnectAttempts: (attempts: number) => void
  setError: (error: Error | null) => void
  setLastError: (error: Error | null) => void
  updateStats: (stats: WebSocketStats) => void

  // 娑堟伅绠＄悊
  addMessage: (message: WebSocketMessage) => void
  clearMessageHistory: () => void
  clearMessages: () => void

  // 閰嶇疆绠＄悊
  updateConfig: (config: Partial<WebSocketState['config']>) => void

  // 瀹㈡埛绔鐞?
  setClient: (client: WebSocketClient | null) => void
  getClient: () => WebSocketClient | null

  // 閲嶇疆鐘舵€?
  reset: () => void
}

export type WebSocketStore = WebSocketState & WebSocketActions

const initialState: WebSocketState = {
  connectionState: 'disconnected' as ConnectionState,
  isConnected: false,
  isConnecting: false,
  isReconnecting: false,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  nextReconnectDelay: 1000,
  lastError: null,
  errorHistory: [],
  stats: {
    messagesReceived: 0,
    messagesSent: 0,
    reconnectCount: 0,
    totalUptime: 0,
    totalMessages: 0,
    totalErrors: 0,
    bytesReceived: 0,
    bytesSent: 0,
    uptime: 0
  },
  messageHistory: [],
  maxHistorySize: 100,
  messages: [],
  client: null,
  lastHeartbeat: 0,
  config: {
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/ws',
    debug: import.meta.env.DEV || false,
    autoConnect: true,
    heartbeatInterval: 30000
  }
}

/**
 * WebSocket鐘舵€佺鐞唖tore
 */
export const useWebSocketStore = create<WebSocketStore>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    // 杩炴帴绠＄悊
    connect: () => {
      const { client, config } = get()

      if (client && client.isConnected()) {
        console.warn('WebSocket宸茬粡杩炴帴')
        return
      }

      set({ isConnecting: true, connectionState: 'connecting' as ConnectionState })

      if (client) {
        client.connect()
      }
    },

    disconnect: () => {
      const { client } = get()

      if (client) {
        client.disconnect()
      }

      set({
        isConnected: false,
        isConnecting: false,
        isReconnecting: false,
        connectionState: 'disconnected' as ConnectionState
      })
    },

    reconnect: () => {
      const { client } = get()

      if (client) {
        set({ isReconnecting: true, connectionState: 'reconnecting' as ConnectionState })
        client.connect()
      }
    },

    // 娑堟伅鍙戦€?
    sendMessage: (message) => {
      const { client, isConnected } = get()

      if (!client || !isConnected) {
        console.warn('WebSocket 未连接，无法发送消息')
        return false
      }

      const fullMessage: WebSocketMessage = {
        ...message,
        timestamp: new Date().toISOString(),
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      }

      const success = client.send(fullMessage)

      if (success) {
        // 娣诲姞鍒版秷鎭巻鍙?
        get().addMessage(fullMessage)
      }

      return success
    },

    // 鐘舵€佹洿鏂?
    setConnectionState: (connectionState) => {
      set({
        connectionState,
        isConnected: connectionState === 'connected',
        isConnecting: connectionState === 'connecting',
        isReconnecting: connectionState === 'reconnecting'
      })
    },

    setConnected: (isConnected) => {
      set({
        isConnected,
        connectionState: isConnected ? 'connected' as ConnectionState : 'disconnected' as ConnectionState,
        isConnecting: false,
        isReconnecting: false
      })
    },

    setReconnectAttempts: (reconnectAttempts) => {
      set({ reconnectAttempts })
    },

    setError: (error) => {
      const { errorHistory } = get()

      set({
        lastError: error,
        errorHistory: error
          ? [...errorHistory, { error, timestamp: new Date() }].slice(-10) // 淇濈暀鏈€杩?0涓敊璇?
          : errorHistory
      })
    },

    setLastError: (error) => {
      set({ lastError: error })
    },

    updateStats: (stats) => {
      set({ stats })
    },

    // 娑堟伅绠＄悊
    addMessage: (message) => {
      const { messageHistory, maxHistorySize } = get()

      const newHistory = [...messageHistory, message]

      // 闄愬埗鍘嗗彶娑堟伅鏁伴噺
      if (newHistory.length > maxHistorySize) {
        newHistory.splice(0, newHistory.length - maxHistorySize)
      }

      set({ messageHistory: newHistory })
    },

    clearMessageHistory: () => {
      set({ messageHistory: [] })
    },

    clearMessages: () => {
      set({ messages: [], messageHistory: [] })
    },

    // 閰嶇疆绠＄悊
    updateConfig: (newConfig) => {
      const { config } = get()
      set({ config: { ...config, ...newConfig } })
    },

    // 瀹㈡埛绔鐞?
    setClient: (client) => {
      set({ client })
    },

    getClient: () => {
      return get().client
    },

    // 閲嶇疆鐘舵€?
    reset: () => {
      const { client } = get()

      if (client) {
        client.disconnect()
      }

      set({
        ...initialState,
        client: null
      })
    }
  }))
)

/**
 * WebSocket瀹㈡埛绔紩鐢ㄧ鐞?
 */
let webSocketClientRef: WebSocketClient | null = null

export const setWebSocketClientRef = (client: WebSocketClient | null) => {
  webSocketClientRef = client
  useWebSocketStore.getState().setClient(client)
}

export const getWebSocketClientRef = (): WebSocketClient | null => {
  return webSocketClientRef
}

/**
 * 閫夋嫨鍣ㄥ嚱鏁?
 */
export const selectConnectionState = (state: WebSocketStore) => state.connectionState
export const selectIsConnected = (state: WebSocketStore) => state.isConnected
export const selectIsConnecting = (state: WebSocketStore) => state.isConnecting
export const selectIsReconnecting = (state: WebSocketStore) => state.isReconnecting
export const selectReconnectAttempts = (state: WebSocketStore) => state.reconnectAttempts
export const selectLastError = (state: WebSocketStore) => state.lastError
export const selectStats = (state: WebSocketStore) => state.stats
export const selectMessageHistory = (state: WebSocketStore) => state.messageHistory
export const selectConfig = (state: WebSocketStore) => state.config

/**
 * 璁㈤槄杩炴帴鐘舵€佸彉鍖?
 */
export const subscribeToConnectionState = (callback: (state: ConnectionState) => void) => {
  return useWebSocketStore.subscribe(
    selectConnectionState,
    callback
  )
}

/**
 * 璁㈤槄娑堟伅鍘嗗彶鍙樺寲
 */
export const subscribeToMessages = (callback: (messages: WebSocketMessage[]) => void) => {
  return useWebSocketStore.subscribe(
    selectMessageHistory,
    callback
  )
}

/**
 * 鑾峰彇WebSocket鐘舵€佺殑渚挎嵎鍑芥暟
 */
export const getWebSocketState = () => {
  const store = useWebSocketStore.getState()
  return {
    connectionState: store.connectionState,
    isConnected: store.isConnected,
    isConnecting: store.isConnecting,
    isReconnecting: store.isReconnecting,
    reconnectAttempts: store.reconnectAttempts,
    lastError: store.lastError,
    stats: store.stats
  }
}

/**
 * WebSocket鐘舵€佺鐞嗙殑宸ュ叿鍑芥暟
 */
export const webSocketUtils = {
  // 妫€鏌ユ槸鍚﹀彲浠ュ彂閫佹秷鎭?
  canSendMessage: (): boolean => {
    const { isConnected } = useWebSocketStore.getState()
    return isConnected
  },

  // 鑾峰彇杩炴帴鐘舵€佹枃鏈?
  getConnectionStateText: (state: ConnectionState): string => {
    switch (state) {
      case 'connecting':
        return '连接中'
      case 'connected':
        return '已连接'
      case 'disconnected':
        return '已断开'
      case 'reconnecting':
        return '重连中'
      case 'error':
        return '连接错误'
      default:
        return '未知状态'
    }
  },

  // 鑾峰彇杩炴帴鐘舵€侀鑹?
  getConnectionStateColor: (state: ConnectionState): string => {
    switch (state) {
      case 'connecting':
        return 'text-yellow-500'
      case 'connected':
        return 'text-green-500'
      case 'disconnected':
        return 'text-gray-500'
      case 'reconnecting':
        return 'text-blue-500'
      case 'error':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  },

  // 鏍煎紡鍖栫粺璁′俊鎭?
  formatStats: (stats: WebSocketStats) => {
    return {
      messagesReceived: stats.messagesReceived.toLocaleString(),
      messagesSent: stats.messagesSent.toLocaleString(),
      reconnectCount: stats.reconnectCount.toLocaleString(),
      uptime: stats.totalUptime ? `${Math.floor(stats.totalUptime / 1000)}秒` : '0秒',
      lastConnected: stats.lastConnectedAt?.toLocaleString() || '从未连接',
      lastDisconnected: stats.lastDisconnectedAt?.toLocaleString() || '从未断开'
    }
  }
}
