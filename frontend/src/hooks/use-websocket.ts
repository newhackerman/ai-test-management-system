/**
 * WebSocket React Hooks
 * 提供React组件中使用WebSocket的便捷hooks
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { WebSocketClient, ConnectionState, WebSocketMessage, WebSocketConfig } from '@/lib/websocket-client'

export interface UseWebSocketOptions extends Partial<WebSocketConfig> {
  autoConnect?: boolean
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onMessage?: (message: WebSocketMessage) => void
}

export interface UseWebSocketReturn {
  client: WebSocketClient | null
  connectionState: ConnectionState
  lastMessage: WebSocketMessage | null
  reconnectAttempts: number
  lastError: string | null
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  send: (message: Omit<WebSocketMessage, 'timestamp' | 'id'>) => boolean
  isConnected: boolean
}

/**
 * WebSocket Hook
 */
export function useWebSocket(url: string, options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    onOpen,
    onClose,
    onError,
    onMessage,
    ...config
  } = options

  const clientRef = useRef<WebSocketClient | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastError, setLastError] = useState<string | null>(null)

  // 初始化WebSocket客户端
  useEffect(() => {
    if (!url) return

    const client = new WebSocketClient({
      url,
      ...config
    })

    client.setHandlers({
      onOpen: (event) => {
        setLastError(null)
        onOpen?.(event)
      },
      onClose: (event) => {
        onClose?.(event)
      },
      onError: (event) => {
        onError?.(event)
      },
      onMessage: (message) => {
        setLastMessage(message)
        onMessage?.(message)
      },
      onStateChange: (state) => {
        setConnectionState(state)
        setReconnectAttempts(client.getReconnectAttempts())
        setLastError(client.getLastError())
      }
    })

    clientRef.current = client

    if (autoConnect) {
      client.connect().catch((error) => {
        console.error('WebSocket auto-connect failed:', error)
      })
    }

    return () => {
      client.destroy()
      clientRef.current = null
    }
  }, [url, autoConnect])

  const connect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.connect()
    }
  }, [])

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
    }
  }, [])

  const reconnect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.reconnect()
    }
  }, [])

  const send = useCallback((message: Omit<WebSocketMessage, 'timestamp' | 'id'>) => {
    if (clientRef.current) {
      return clientRef.current.send(message)
    }
    return false
  }, [])

  const isConnected = connectionState === 'connected'

  return {
    client: clientRef.current,
    connectionState,
    lastMessage,
    reconnectAttempts,
    lastError,
    connect,
    disconnect,
    reconnect,
    send,
    isConnected
  }
}

/**
 * WebSocket状态Hook
 */
export function useWebSocketState(client: WebSocketClient | null) {
  const [state, setState] = useState<ConnectionState>('disconnected')
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastError, setLastError] = useState<string | null>(null)

  useEffect(() => {
    if (!client) return

    const updateState = () => {
      setState(client.getState())
      setReconnectAttempts(client.getReconnectAttempts())
      setLastError(client.getLastError())
    }

    client.setHandlers({
      onStateChange: updateState
    })

    // 初始状态
    updateState()

    return () => {
      client.setHandlers({})
    }
  }, [client])

  return {
    state,
    reconnectAttempts,
    lastError,
    isConnected: state === 'connected',
    isConnecting: state === 'connecting',
    isReconnecting: state === 'reconnecting',
    hasError: state === 'error'
  }
}

/**
 * WebSocket消息监听Hook
 */
export function useWebSocketMessage<T = any>(
  client: WebSocketClient | null,
  messageType: string,
  handler: (payload: T) => void
) {
  useEffect(() => {
    if (!client) return

    const messageHandler = (message: WebSocketMessage) => {
      if (message.type === messageType) {
        handler(message.payload)
      }
    }

    client.setHandlers({
      onMessage: messageHandler
    })

    return () => {
      client.setHandlers({
        onMessage: undefined
      })
    }
  }, [client, messageType, handler])
}

/**
 * WebSocket订阅Hook
 */
export function useWebSocketSubscription<T = any>(
  client: WebSocketClient | null,
  subscription: {
    type: string
    payload?: any
  },
  handler: (data: T) => void
) {
  const [isSubscribed, setIsSubscribed] = useState(false)

  useEffect(() => {
    if (!client || !client.isConnected()) return

    // 发送订阅消息
    const success = client.send({
      type: 'subscribe',
      payload: subscription
    })

    if (success) {
      setIsSubscribed(true)
    }

    // 监听订阅消息
    const messageHandler = (message: WebSocketMessage) => {
      if (message.type === subscription.type) {
        handler(message.payload)
      }
    }

    client.setHandlers({
      onMessage: messageHandler
    })

    return () => {
      // 取消订阅
      if (client.isConnected()) {
        client.send({
          type: 'unsubscribe',
          payload: subscription
        })
      }
      
      setIsSubscribed(false)
      client.setHandlers({
        onMessage: undefined
      })
    }
  }, [client, subscription.type, subscription.payload])

  return { isSubscribed }
}

export default useWebSocket