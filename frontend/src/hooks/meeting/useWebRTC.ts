// WebRTC连接管理Hook
import { useState, useEffect, useCallback, useRef } from 'react'
import { WebSocketConnectionManager } from '@/services/websocket-connection-manager'
import type { WebRTCConfig } from '@/types/meeting'

interface NetworkQuality {
  bandwidth: number
  packetLoss: number
  latency: number
  jitter: number
  quality: 'excellent' | 'good' | 'fair' | 'poor'
}

interface ConnectionStats {
  bytesReceived: number
  bytesSent: number
  packetsReceived: number
  packetsSent: number
  packetsLost: number
  timestamp: number
}

interface WebRTCState {
  localStream: MediaStream | null
  remoteStreams: Map<string, MediaStream>
  isConnecting: boolean
  isConnected: boolean
  error: string | null
  networkQuality: NetworkQuality | null
  connectionStats: ConnectionStats | null
  signalingState: RTCSignalingState | null
  iceConnectionState: RTCIceConnectionState | null
  reconnectAttempts: number
}

interface SignalingMessage {
  type: 'offer' | 'answer' | 'ice-candidate' | 'join-room' | 'leave-room' | 'user-joined' | 'user-left'
  data: any
  from?: string
  to?: string
  roomId: string
}

interface WebRTCHook extends WebRTCState {
  connect: (config: WebRTCConfig) => Promise<void>
  disconnect: () => Promise<void>
  reconnect: () => Promise<void>
  addIceCandidate: (candidate: RTCIceCandidate, fromUserId?: string) => Promise<void>
  createOffer: (toUserId?: string) => Promise<RTCSessionDescriptionInit>
  createAnswer: (offer: RTCSessionDescriptionInit, fromUserId?: string) => Promise<RTCSessionDescriptionInit>
  setRemoteDescription: (description: RTCSessionDescriptionInit, fromUserId?: string) => Promise<void>
  sendSignalingMessage: (message: Omit<SignalingMessage, 'roomId'>) => void
  toggleAudio: () => Promise<void>
  toggleVideo: () => Promise<void>
  replaceVideoTrack: (newTrack: MediaStreamTrack) => Promise<void>
  getNetworkQuality: () => NetworkQuality | null
  getConnectionStats: () => Promise<ConnectionStats | null>
}

export const useWebRTC = (): WebRTCHook => {
  const [state, setState] = useState<WebRTCState>({
    localStream: null,
    remoteStreams: new Map(),
    isConnecting: false,
    isConnected: false,
    error: null,
    networkQuality: null,
    connectionStats: null,
    signalingState: null,
    iceConnectionState: null,
    reconnectAttempts: 0
  })

  const peerConnectionsRef = useRef<Map<string, RTCPeerConnection>>(new Map())
  const localStreamRef = useRef<MediaStream | null>(null)
  const configRef = useRef<WebRTCConfig | null>(null)
  const signalingManagerRef = useRef<WebSocketConnectionManager | null>(null)
  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const qualityMonitorRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  // 清理资源
  const cleanup = useCallback(() => {
    // 清理所有PeerConnection
    peerConnectionsRef.current.forEach((pc, userId) => {
      pc.close()
    })
    peerConnectionsRef.current.clear()

    // 停止本地媒体流
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop())
      localStreamRef.current = null
    }

    // 断开信令连接
    if (signalingManagerRef.current) {
      signalingManagerRef.current.disconnect()
      signalingManagerRef.current = null
    }

    // 清理定时器
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current)
      statsIntervalRef.current = null
    }

    if (qualityMonitorRef.current) {
      clearInterval(qualityMonitorRef.current)
      qualityMonitorRef.current = null
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    setState(prev => ({
      ...prev,
      localStream: null,
      remoteStreams: new Map(),
      isConnected: false,
      isConnecting: false,
      networkQuality: null,
      connectionStats: null,
      signalingState: null,
      iceConnectionState: null,
      reconnectAttempts: 0
    }))
  }, [])

  // 创建PeerConnection
  const createPeerConnection = useCallback((userId: string, config: WebRTCConfig) => {
    const peerConnection = new RTCPeerConnection({
      iceServers: config.ice_servers,
      iceCandidatePoolSize: 10,
      bundlePolicy: 'max-bundle',
      rtcpMuxPolicy: 'require'
    })

    // ICE候选事件
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && signalingManagerRef.current) {
        sendSignalingMessage({
          type: 'ice-candidate',
          data: {
            candidate: event.candidate.candidate,
            sdpMLineIndex: event.candidate.sdpMLineIndex,
            sdpMid: event.candidate.sdpMid
          },
          to: userId
        })
      }
    }

    // ICE连接状态变化
    peerConnection.oniceconnectionstatechange = () => {
      const iceState = peerConnection.iceConnectionState
      console.log(`ICE connection state for ${userId}:`, iceState)
      
      setState(prev => ({
        ...prev,
        iceConnectionState: iceState,
        isConnected: iceState === 'connected' || iceState === 'completed',
        isConnecting: iceState === 'checking'
      }))

      // 处理连接失败
      if (iceState === 'failed' || iceState === 'disconnected') {
        handleConnectionFailure(userId)
      }
    }

    // 信令状态变化
    peerConnection.onsignalingstatechange = () => {
      setState(prev => ({
        ...prev,
        signalingState: peerConnection.signalingState
      }))
    }

    // 连接状态变化
    peerConnection.onconnectionstatechange = () => {
      const connectionState = peerConnection.connectionState
      console.log(`Connection state for ${userId}:`, connectionState)
      
      if (connectionState === 'failed') {
        setState(prev => ({
          ...prev,
          error: `与用户 ${userId} 的连接失败`
        }))
        handleConnectionFailure(userId)
      }
    }

    // 接收远程流
    peerConnection.ontrack = (event) => {
      console.log(`Received remote stream from ${userId}:`, event.streams[0])
      setState(prev => {
        const newRemoteStreams = new Map(prev.remoteStreams)
        newRemoteStreams.set(userId, event.streams[0])
        return {
          ...prev,
          remoteStreams: newRemoteStreams
        }
      })
    }

    // 添加本地流到PeerConnection
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStreamRef.current!)
      })
    }

    return peerConnection
  }, [])

  // 处理连接失败
  const handleConnectionFailure = useCallback(async (userId: string) => {
    console.log(`Handling connection failure for user ${userId}`)
    
    // 移除失败的连接
    const pc = peerConnectionsRef.current.get(userId)
    if (pc) {
      pc.close()
      peerConnectionsRef.current.delete(userId)
    }

    // 移除远程流
    setState(prev => {
      const newRemoteStreams = new Map(prev.remoteStreams)
      newRemoteStreams.delete(userId)
      return {
        ...prev,
        remoteStreams: newRemoteStreams
      }
    })

    // 尝试重连
    if (state.reconnectAttempts < maxReconnectAttempts) {
      setState(prev => ({
        ...prev,
        reconnectAttempts: prev.reconnectAttempts + 1
      }))

      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectToPeer(userId)
      }, reconnectDelay * (state.reconnectAttempts + 1))
    }
  }, [state.reconnectAttempts])

  // 重连到特定用户
  const reconnectToPeer = useCallback(async (userId: string) => {
    if (!configRef.current) return

    try {
      console.log(`Attempting to reconnect to user ${userId}`)
      
      // 创建新的PeerConnection
      const pc = createPeerConnection(userId, configRef.current)
      peerConnectionsRef.current.set(userId, pc)

      // 创建新的offer
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      // 发送offer
      sendSignalingMessage({
        type: 'offer',
        data: offer,
        to: userId
      })

    } catch (error) {
      console.error(`Failed to reconnect to user ${userId}:`, error)
      setState(prev => ({
        ...prev,
        error: `重连到用户 ${userId} 失败`
      }))
    }
  }, [])

  // 获取本地媒体流
  const getLocalStream = useCallback(async (constraints: MediaStreamConstraints) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      localStreamRef.current = stream
      
      setState(prev => ({
        ...prev,
        localStream: stream,
        error: null
      }))

      return stream
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取媒体流失败'
      setState(prev => ({
        ...prev,
        error: errorMessage
      }))
      throw error
    }
  }, [])

  // 初始化信令连接
  const initializeSignaling = useCallback(async (config: WebRTCConfig) => {
    try {
      const signalingManager = new WebSocketConnectionManager({
        url: config.signaling_url,
        reconnectInterval: 3000,
        maxReconnectAttempts: 10,
        heartbeatInterval: 30000
      })

      // 监听信令消息
      signalingManager.subscribe('message', handleSignalingMessage)
      signalingManager.subscribe('message', handleUserJoined)
      signalingManager.subscribe('message', handleUserLeft)

      // 监听连接状态
      signalingManager.on('connected', () => {
        console.log('Signaling connected')
        // 加入房间
        signalingManager.send({
          type: 'message',
          data: {
            type: 'join-room',
            roomId: config.room_id
          }
        })
      })

      signalingManager.on('disconnected', () => {
        console.log('Signaling disconnected')
        setState(prev => ({
          ...prev,
          isConnected: false,
          error: '信令服务器连接断开'
        }))
      })

      signalingManager.on('error', (error) => {
        console.error('Signaling error:', error)
        setState(prev => ({
          ...prev,
          error: '信令服务器错误'
        }))
      })

      await signalingManager.connect()
      signalingManagerRef.current = signalingManager

    } catch (error) {
      console.error('Failed to initialize signaling:', error)
      throw new Error('信令服务器连接失败')
    }
  }, [])

  // 处理信令消息
  const handleSignalingMessage = useCallback(async (message: any) => {
    const signalingData: SignalingMessage = message.data
    
    try {
      switch (signalingData.type) {
        case 'offer':
          await handleOffer(signalingData.data, signalingData.from!)
          break
        case 'answer':
          await handleAnswer(signalingData.data, signalingData.from!)
          break
        case 'ice-candidate':
          await handleIceCandidate(signalingData.data, signalingData.from!)
          break
        default:
          console.log('Unknown signaling message type:', signalingData.type)
      }
    } catch (error) {
      console.error('Error handling signaling message:', error)
    }
  }, [])

  // 处理用户加入
  const handleUserJoined = useCallback(async (message: any) => {
    const { userId } = message.data
    console.log(`User ${userId} joined the room`)
    
    if (!configRef.current) return

    // 为新用户创建PeerConnection
    const pc = createPeerConnection(userId, configRef.current)
    peerConnectionsRef.current.set(userId, pc)

    // 创建offer
    try {
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      sendSignalingMessage({
        type: 'offer',
        data: offer,
        to: userId
      })
    } catch (error) {
      console.error(`Failed to create offer for user ${userId}:`, error)
    }
  }, [])

  // 处理用户离开
  const handleUserLeft = useCallback((message: any) => {
    const { userId } = message.data
    console.log(`User ${userId} left the room`)
    
    // 关闭PeerConnection
    const pc = peerConnectionsRef.current.get(userId)
    if (pc) {
      pc.close()
      peerConnectionsRef.current.delete(userId)
    }

    // 移除远程流
    setState(prev => {
      const newRemoteStreams = new Map(prev.remoteStreams)
      newRemoteStreams.delete(userId)
      return {
        ...prev,
        remoteStreams: newRemoteStreams
      }
    })
  }, [])

  // 处理Offer
  const handleOffer = useCallback(async (offer: RTCSessionDescriptionInit, fromUserId: string) => {
    if (!configRef.current) return

    let pc = peerConnectionsRef.current.get(fromUserId)
    if (!pc) {
      pc = createPeerConnection(fromUserId, configRef.current)
      peerConnectionsRef.current.set(fromUserId, pc)
    }

    await pc.setRemoteDescription(offer)
    const answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    sendSignalingMessage({
      type: 'answer',
      data: answer,
      to: fromUserId
    })
  }, [])

  // 处理Answer
  const handleAnswer = useCallback(async (answer: RTCSessionDescriptionInit, fromUserId: string) => {
    const pc = peerConnectionsRef.current.get(fromUserId)
    if (pc) {
      await pc.setRemoteDescription(answer)
    }
  }, [])

  // 处理ICE候选
  const handleIceCandidate = useCallback(async (candidateData: any, fromUserId: string) => {
    const pc = peerConnectionsRef.current.get(fromUserId)
    if (pc) {
      const candidate = new RTCIceCandidate({
        candidate: candidateData.candidate,
        sdpMLineIndex: candidateData.sdpMLineIndex,
        sdpMid: candidateData.sdpMid
      })
      await pc.addIceCandidate(candidate)
    }
  }, [])

  // 发送信令消息
  const sendSignalingMessage = useCallback((message: Omit<SignalingMessage, 'roomId'>) => {
    if (signalingManagerRef.current && configRef.current) {
      signalingManagerRef.current.send({
        type: 'message',
        data: {
          ...message,
          roomId: configRef.current.room_id
        }
      })
    }
  }, [])

  // 连接WebRTC
  const connect = useCallback(async (config: WebRTCConfig) => {
    try {
      setState(prev => ({
        ...prev,
        isConnecting: true,
        error: null,
        reconnectAttempts: 0
      }))

      configRef.current = config

      // 获取本地媒体流
      await getLocalStream(config.media_constraints)

      // 初始化信令连接
      await initializeSignaling(config)

      // 开始网络质量监控
      startNetworkQualityMonitoring()

      // 开始统计监控
      startStatsMonitoring()

      setState(prev => ({
        ...prev,
        isConnecting: false,
        isConnected: true
      }))

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '连接失败'
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: errorMessage
      }))
    }
  }, [getLocalStream, initializeSignaling])

  // 网络质量监控
  const startNetworkQualityMonitoring = useCallback(() => {
    qualityMonitorRef.current = setInterval(async () => {
      if (peerConnectionsRef.current.size === 0) return

      try {
        let totalBandwidth = 0
        let totalPacketLoss = 0
        let totalLatency = 0
        let totalJitter = 0
        let connectionCount = 0

        for (const [userId, pc] of Array.from(peerConnectionsRef.current.entries())) {
          const stats = await pc.getStats()
          
          stats.forEach((report: any) => {
            if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
              const bandwidth = report.bytesReceived ? (report.bytesReceived * 8) / 1000 : 0
              const packetLoss = report.packetsLost || 0
              const jitter = report.jitter || 0

              totalBandwidth += bandwidth
              totalPacketLoss += packetLoss
              totalJitter += jitter
              connectionCount++
            }

            if (report.type === 'candidate-pair' && report.state === 'succeeded') {
              totalLatency += report.currentRoundTripTime || 0
            }
          })
        }

        if (connectionCount > 0) {
          const avgBandwidth = totalBandwidth / connectionCount
          const avgPacketLoss = totalPacketLoss / connectionCount
          const avgLatency = totalLatency / connectionCount
          const avgJitter = totalJitter / connectionCount

          let quality: NetworkQuality['quality'] = 'excellent'
          if (avgPacketLoss > 5 || avgLatency > 300 || avgBandwidth < 500) {
            quality = 'poor'
          } else if (avgPacketLoss > 2 || avgLatency > 150 || avgBandwidth < 1000) {
            quality = 'fair'
          } else if (avgPacketLoss > 1 || avgLatency > 100 || avgBandwidth < 2000) {
            quality = 'good'
          }

          setState(prev => ({
            ...prev,
            networkQuality: {
              bandwidth: avgBandwidth,
              packetLoss: avgPacketLoss,
              latency: avgLatency,
              jitter: avgJitter,
              quality
            }
          }))
        }
      } catch (error) {
        console.error('Error monitoring network quality:', error)
      }
    }, 5000) // 每5秒检查一次
  }, [])

  // 统计监控
  const startStatsMonitoring = useCallback(() => {
    statsIntervalRef.current = setInterval(async () => {
      if (peerConnectionsRef.current.size === 0) return

      try {
        let totalBytesReceived = 0
        let totalBytesSent = 0
        let totalPacketsReceived = 0
        let totalPacketsSent = 0
        let totalPacketsLost = 0

        for (const [, pc] of Array.from(peerConnectionsRef.current.entries())) {
          const stats = await pc.getStats()
          
          stats.forEach((report: any) => {
            if (report.type === 'inbound-rtp') {
              totalBytesReceived += report.bytesReceived || 0
              totalPacketsReceived += report.packetsReceived || 0
              totalPacketsLost += report.packetsLost || 0
            }
            
            if (report.type === 'outbound-rtp') {
              totalBytesSent += report.bytesSent || 0
              totalPacketsSent += report.packetsSent || 0
            }
          })
        }

        setState(prev => ({
          ...prev,
          connectionStats: {
            bytesReceived: totalBytesReceived,
            bytesSent: totalBytesSent,
            packetsReceived: totalPacketsReceived,
            packetsSent: totalPacketsSent,
            packetsLost: totalPacketsLost,
            timestamp: Date.now()
          }
        }))
      } catch (error) {
        console.error('Error collecting connection stats:', error)
      }
    }, 10000) // 每10秒收集一次统计
  }, [])

  // 断开连接
  const disconnect = useCallback(async () => {
    // 发送离开房间消息
    if (signalingManagerRef.current && configRef.current) {
      sendSignalingMessage({
        type: 'leave-room',
        data: { roomId: configRef.current.room_id }
      })
    }

    cleanup()
  }, [cleanup, sendSignalingMessage])

  // 重连
  const reconnect = useCallback(async () => {
    if (!configRef.current) {
      throw new Error('No configuration available for reconnection')
    }

    console.log('Attempting to reconnect...')
    
    // 清理现有连接
    cleanup()
    
    // 等待一段时间后重连
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 重新连接
    await connect(configRef.current)
  }, [cleanup, connect])

  // 添加ICE候选
  const addIceCandidate = useCallback(async (candidate: RTCIceCandidate, fromUserId?: string) => {
    if (!fromUserId) {
      // 如果没有指定用户ID，添加到所有连接
      for (const [userId, pc] of Array.from(peerConnectionsRef.current.entries())) {
        try {
          await pc.addIceCandidate(candidate)
        } catch (error) {
          console.error(`Error adding ICE candidate for user ${userId}:`, error)
        }
      }
    } else {
      const pc = peerConnectionsRef.current.get(fromUserId)
      if (pc) {
        try {
          await pc.addIceCandidate(candidate)
        } catch (error) {
          console.error(`Error adding ICE candidate for user ${fromUserId}:`, error)
        }
      }
    }
  }, [])

  // 创建Offer
  const createOffer = useCallback(async (toUserId?: string): Promise<RTCSessionDescriptionInit> => {
    if (!configRef.current) {
      throw new Error('WebRTC not initialized')
    }

    if (!toUserId) {
      throw new Error('Target user ID is required')
    }

    let pc = peerConnectionsRef.current.get(toUserId)
    if (!pc) {
      pc = createPeerConnection(toUserId, configRef.current)
      peerConnectionsRef.current.set(toUserId, pc)
    }

    try {
      const offer = await pc.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: true
      })
      await pc.setLocalDescription(offer)
      return offer
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '创建Offer失败'
      setState(prev => ({
        ...prev,
        error: errorMessage
      }))
      throw error
    }
  }, [createPeerConnection])

  // 创建Answer
  const createAnswer = useCallback(async (offer: RTCSessionDescriptionInit, fromUserId?: string): Promise<RTCSessionDescriptionInit> => {
    if (!configRef.current || !fromUserId) {
      throw new Error('WebRTC not initialized or user ID missing')
    }

    let pc = peerConnectionsRef.current.get(fromUserId)
    if (!pc) {
      pc = createPeerConnection(fromUserId, configRef.current)
      peerConnectionsRef.current.set(fromUserId, pc)
    }

    try {
      await pc.setRemoteDescription(offer)
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      return answer
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '创建Answer失败'
      setState(prev => ({
        ...prev,
        error: errorMessage
      }))
      throw error
    }
  }, [createPeerConnection])

  // 设置远程描述
  const setRemoteDescription = useCallback(async (description: RTCSessionDescriptionInit, fromUserId?: string) => {
    if (!fromUserId) {
      throw new Error('User ID is required')
    }

    const pc = peerConnectionsRef.current.get(fromUserId)
    if (!pc) {
      throw new Error(`PeerConnection for user ${fromUserId} not found`)
    }

    try {
      await pc.setRemoteDescription(description)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '设置远程描述失败'
      setState(prev => ({
        ...prev,
        error: errorMessage
      }))
      throw error
    }
  }, [])

  // 切换音频
  const toggleAudio = useCallback(async () => {
    if (!localStreamRef.current) return

    const audioTrack = localStreamRef.current.getAudioTracks()[0]
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled
      
      // 通知所有连接更新音频状态
      for (const [userId, pc] of Array.from(peerConnectionsRef.current.entries())) {
        const sender = pc.getSenders().find((s: RTCRtpSender) => s.track === audioTrack)
        if (sender) {
          try {
            await sender.replaceTrack(audioTrack.enabled ? audioTrack : null)
          } catch (error) {
            console.error(`Failed to update audio track for user ${userId}:`, error)
          }
        }
      }
    }
  }, [])

  // 切换视频
  const toggleVideo = useCallback(async () => {
    if (!localStreamRef.current) return

    const videoTrack = localStreamRef.current.getVideoTracks()[0]
    if (videoTrack) {
      videoTrack.enabled = !videoTrack.enabled
      
      // 通知所有连接更新视频状态
      for (const [userId, pc] of Array.from(peerConnectionsRef.current.entries())) {
        const sender = pc.getSenders().find((s: RTCRtpSender) => s.track === videoTrack)
        if (sender) {
          try {
            await sender.replaceTrack(videoTrack.enabled ? videoTrack : null)
          } catch (error) {
            console.error(`Failed to update video track for user ${userId}:`, error)
          }
        }
      }
    }
  }, [])

  // 替换视频轨道
  const replaceVideoTrack = useCallback(async (newTrack: MediaStreamTrack) => {
    if (!localStreamRef.current) return

    const oldTrack = localStreamRef.current.getVideoTracks()[0]
    if (oldTrack) {
      // 停止旧轨道
      oldTrack.stop()
      
      // 从流中移除旧轨道
      localStreamRef.current.removeTrack(oldTrack)
    }

    // 添加新轨道到流
    localStreamRef.current.addTrack(newTrack)

    // 更新所有PeerConnection的发送器
    for (const [userId, pc] of Array.from(peerConnectionsRef.current.entries())) {
      const sender = pc.getSenders().find((s: RTCRtpSender) => s.track === oldTrack)
      if (sender) {
        try {
          await sender.replaceTrack(newTrack)
        } catch (error) {
          console.error(`Failed to replace video track for user ${userId}:`, error)
        }
      }
    }

    // 更新状态
    setState(prev => ({
      ...prev,
      localStream: localStreamRef.current
    }))
  }, [])

  // 获取网络质量
  const getNetworkQuality = useCallback(() => {
    return state.networkQuality
  }, [state.networkQuality])

  // 获取连接统计
  const getConnectionStats = useCallback(async (): Promise<ConnectionStats | null> => {
    return state.connectionStats
  }, [state.connectionStats])

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  return {
    ...state,
    connect,
    disconnect,
    reconnect,
    addIceCandidate,
    createOffer,
    createAnswer,
    setRemoteDescription,
    sendSignalingMessage,
    toggleAudio,
    toggleVideo,
    replaceVideoTrack,
    getNetworkQuality,
    getConnectionStats
  }
}