// WebSocket提供者组件

import React, { createContext, useContext, useEffect, useState } from 'react'
import { WebSocketClient, ConnectionState, WebSocketMessage } from '@/lib/websocket-client'
import { useWebSocket } from '@/hooks/use-websocket'
import { useAuthStore } from '@/stores/auth'
import { toast } from 'react-hot-toast'

// WebSocket上下文接口
interface WebSocketContextType {
  client: WebSocketClient | null
  isConnected: boolean
  connectionState: ConnectionState
  reconnectAttempts: number
  lastError: string | null
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  send: (message: Omit<WebSocketMessage, 'timestamp' | 'id'>) => boolean
  subscribe: (type: string, handler: (payload: any) => void) => () => void
}

const noopWebSocketContext: WebSocketContextType = {
  client: null,
  isConnected: false,
  connectionState: 'disconnected',
  reconnectAttempts: 0,
  lastError: null,
  connect: async () => {},
  disconnect: () => {},
  reconnect: async () => {},
  send: () => false,
  subscribe: () => () => {}
}

// 创建WebSocket上下文
const WebSocketContext = createContext<WebSocketContextType>(noopWebSocketContext)

// WebSocket提供者属性
interface WebSocketProviderProps {
  children: React.ReactNode
  url?: string
  autoConnect?: boolean
  enableNotifications?: boolean
  enableReconnect?: boolean
  maxReconnectAttempts?: number
}

/**
 * WebSocket提供者组件
 */
export function WebSocketProvider({
  children,
  url,
  autoConnect = true,
  enableNotifications = true,
  enableReconnect = true,
  maxReconnectAttempts = 5
}: WebSocketProviderProps) {
  const { isAuthenticated, token } = useAuthStore()
  const [wsUrl, setWsUrl] = useState<string | undefined>(url)
  const [messageHandlers, setMessageHandlers] = useState<Map<string, Set<(payload: any) => void>>>(new Map())
  
  // 构建WebSocket URL（包含认证token）
  useEffect(() => {
    if (url && isAuthenticated && token) {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.host
      const baseUrl = url.startsWith('ws') ? url : `${wsProtocol}//${wsHost}${url}`
      
      // 添加认证token到URL
      const urlObj = new URL(baseUrl)
      urlObj.searchParams.set('token', token)
      setWsUrl(urlObj.toString())
    } else {
      setWsUrl(undefined)
    }
  }, [url, isAuthenticated, token])

  // WebSocket连接配置
  const {
    client,
    connectionState,
    reconnectAttempts,
    lastError,
    connect,
    disconnect,
    reconnect,
    send,
    isConnected
  } = useWebSocket(wsUrl || '', {
    autoConnect: autoConnect && !!wsUrl,
    maxReconnectAttempts,
    onOpen: () => {
      if (enableNotifications) {
        toast.success('WebSocket连接已建立')
      }
    },
    onClose: () => {
      if (enableNotifications && isAuthenticated) {
        toast.error('WebSocket连接已断开')
      }
    },
    onError: () => {
      if (enableNotifications) {
        toast.error('WebSocket连接错误')
      }
    },
    onMessage: (message) => {
      // 分发消息给订阅者
      const handlers = messageHandlers.get(message.type)
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(message.payload)
          } catch (error) {
            console.error('WebSocket message handler error:', error)
          }
        })
      }
    }
  })

  // 订阅消息类型
  const subscribe = (type: string, handler: (payload: any) => void) => {
    setMessageHandlers(prev => {
      const newMap = new Map(prev)
      if (!newMap.has(type)) {
        newMap.set(type, new Set())
      }
      newMap.get(type)!.add(handler)
      return newMap
    })

    // 返回取消订阅函数
    return () => {
      setMessageHandlers(prev => {
        const newMap = new Map(prev)
        const handlers = newMap.get(type)
        if (handlers) {
          handlers.delete(handler)
          if (handlers.size === 0) {
            newMap.delete(type)
          }
        }
        return newMap
      })
    }
  }

  // 当认证状态改变时处理连接
  useEffect(() => {
    if (!isAuthenticated && client) {
      disconnect()
    }
  }, [isAuthenticated, client, disconnect])

  const contextValue: WebSocketContextType = {
    client,
    isConnected,
    connectionState,
    reconnectAttempts,
    lastError,
    connect,
    disconnect,
    reconnect,
    send,
    subscribe
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}

/**
 * 使用WebSocket上下文的Hook
 */
export function useWebSocketContext(): WebSocketContextType {
  return useContext(WebSocketContext)
}

/**
 * WebSocket状态指示器组件
 */
export function WebSocketStatusIndicator() {
  const { connectionState, reconnectAttempts, lastError, reconnect } = useWebSocketContext()

  if (connectionState === 'connected') {
    return null // 连接正常时不显示
  }

  const getStatusColor = () => {
    switch (connectionState) {
      case 'connecting':
        return 'bg-yellow-500'
      case 'reconnecting':
        return 'bg-orange-500'
      case 'error':
        return 'bg-red-500'
      case 'disconnected':
        return 'bg-gray-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = () => {
    switch (connectionState) {
      case 'connecting':
        return '连接中...'
      case 'reconnecting':
        return `重连中... (${reconnectAttempts}/5)`
      case 'error':
        return lastError || '连接错误'
      case 'disconnected':
        return '连接断开'
      default:
        return '未知状态'
    }
  }

  return (
    <div className="fixed bottom-4 left-4 z-50">
      <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 shadow-lg">
        <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {getStatusText()}
        </span>
        {(connectionState === 'error' || connectionState === 'disconnected') && (
          <button
            onClick={reconnect}
            className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            重连
          </button>
        )}
      </div>
    </div>
  )
}

export default WebSocketProvider
