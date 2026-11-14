// @ts-nocheck
import { apiClient } from '@/services/api/client'

export interface WebRTCConfig {
  iceServers: RTCIceServer[]
  mediaConstraints: MediaStreamConstraints
  signalingUrl: string
  roomId: string
}

export interface ScreenShareConfig {
  audio?: boolean
  video?: boolean
  displaySurface?: 'monitor' | 'window' | 'application'
}

export interface MediaQualitySettings {
  video: {
    width: number
    height: number
    frameRate: number
    bitrate: number
  }
  audio: {
    sampleRate: number
    bitrate: number
    echoCancellation: boolean
    noiseSuppression: boolean
  }
}

export class WebRTCService {
  private baseUrl = '/api/v1/meetings'
  private websocket: WebSocket | null = null
  // Mesh 通话：每个远端对端一个 RTCPeerConnection（单 PC 无法同时
  // 连多个对端）。key 为对端 user_id。
  private peerConnections: Map<number, RTCPeerConnection> = new Map()
  private localStream: MediaStream | null = null
  private remoteStreams: Map<string, MediaStream> = new Map()
  private eventListeners: Map<string, Function[]> = new Map()
  // WS 加入房间后后端在 room-joined 消息里给的会话 ID，屏幕共享等
  // REST 调用需要它。
  private sessionId: string | null = null

  getSessionId(): string | null {
    return this.sessionId
  }

  // WebRTC配置获取：后端返回 snake_case（ice_servers / media_constraints /
  // room_config / session_config），这里映射成前端的 camelCase。
  async getWebRTCConfig(meetingId: number): Promise<WebRTCConfig> {
    const response = await apiClient.get<any>(
      `${this.baseUrl}/${meetingId}/webrtc/config`
    )
    const body = response.data ?? response
    return {
      iceServers: (body.ice_servers ?? []).map((s: any) => ({
        urls: s.urls,
        username: s.username,
        credential: s.credential,
      })),
      mediaConstraints: body.media_constraints ?? {
        audio: { echoCancellation: true, noiseSuppression: true },
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      },
      signalingUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/meetings/${meetingId}/webrtc/ws`,
      roomId: body.room_config?.room_id ?? `room_${meetingId}`,
    }
  }

  // 建立WebSocket连接：后端真实地址是
  // /api/v1/meetings/{meeting_id}/webrtc/ws?token=...（此前连的是不
  // 存在的 /meetings/ws/{meetingCode}）。
  async connectSignaling(meetingId: number, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsBaseUrl = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1`
      const wsUrl = `${wsBaseUrl}/meetings/${meetingId}/webrtc/ws?token=${encodeURIComponent(token)}`

      this.websocket = new WebSocket(wsUrl)
      
      this.websocket.onopen = () => {
        console.log('WebSocket 连接已建立')
        resolve()
      }
      
      this.websocket.onerror = (error) => {
        console.error('WebSocket 连接错误:', error)
        reject(error)
      }
      
      this.websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleSignalingMessage(message)
        } catch (error) {
          console.error('解析信令消息失败:', error)
        }
      }
      
      this.websocket.onclose = () => {
        console.log('WebSocket 连接已关闭')
        this.emit('disconnected')
      }
    })
  }

  // 鏂紑WebSocket杩炴帴
  disconnectSignaling(): void {
    if (this.websocket) {
      this.websocket.close()
      this.websocket = null
    }
  }

  // 初始化与某一位对端的 PeerConnection（mesh：每位对端一个 PC）
  async initializePeerConnection(config: WebRTCConfig, targetUserId: number): Promise<RTCPeerConnection> {
    const existing = this.peerConnections.get(targetUserId)
    if (existing) return existing

    const pc = new RTCPeerConnection({
      iceServers: config.iceServers
    })
    this.peerConnections.set(targetUserId, pc)

    // 处理ICE候选：带上目标用户，后端才知道转发给谁
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendSignalingMessage({
          type: 'ice-candidate',
          candidate: event.candidate,
          target_user_id: targetUserId,
        })
      }
    }

    // 处理远程流
    pc.ontrack = (event) => {
      const [remoteStream] = event.streams
      this.remoteStreams.set(String(targetUserId), remoteStream)
      this.emit('remoteStreamAdded', { participantId: targetUserId, stream: remoteStream })
    }

    // 处理连接状态变化
    pc.onconnectionstatechange = () => {
      const state = pc.connectionState
      console.log('PeerConnection状态?', state)
      this.emit('connectionStateChanged', { targetUserId, state })
    }

    // 本地流已存在则加上去
    this.addLocalStreamToPeer(targetUserId)
    return pc
  }

  getPeerConnection(targetUserId: number): RTCPeerConnection | null {
    return this.peerConnections.get(targetUserId) ?? null
  }

  // 获取本地媒体流
  async getLocalStream(constraints?: MediaStreamConstraints): Promise<MediaStream> {
    try {
      const defaultConstraints: MediaStreamConstraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia(
        constraints || defaultConstraints
      )

      this.localStream = stream
      // 新拿到的本地流要加到已建好的各对端 PC 上
      this.peerConnections.forEach((_, targetUserId) => {
        this.addLocalStreamToPeer(targetUserId)
      })
      this.emit('localStreamReady', stream)

      return stream
    } catch (error) {
      // 无摄像头/无权限在自动化与部分机器上是预期情况，用 warn 而
      // 不是 error，避免巡游把“无媒体设备”当成页面错误。
      console.warn('获取本地媒体流失败:', error)
      throw error
    }
  }

  // 添加本地流到指定对端的 PeerConnection（已加过的轨道不再重复加）
  addLocalStreamToPeer(targetUserId: number): void {
    const pc = this.peerConnections.get(targetUserId)
    if (!this.localStream || !pc) return
    const existing = new Set(pc.getSenders().map((s) => s.track))
    this.localStream.getTracks().forEach(track => {
      if (!existing.has(track)) {
        pc.addTrack(track, this.localStream!)
      }
    })
  }

  // 创建Offer（发给指定对端）
  async createOffer(targetUserId: number): Promise<RTCSessionDescriptionInit> {
    const pc = this.peerConnections.get(targetUserId)
    if (!pc) {
      throw new Error('PeerConnection 未初始化')
    }

    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    this.sendSignalingMessage({
      type: 'offer',
      sdp: offer,
      target_user_id: targetUserId,
    })

    return offer
  }

  // 创建Answer（回给发 offer 的对端）
  async createAnswer(offer: RTCSessionDescriptionInit, fromUserId?: number): Promise<RTCSessionDescriptionInit> {
    const targetUserId = fromUserId ?? 0
    const pc = this.peerConnections.get(targetUserId)
    if (!pc) {
      throw new Error('PeerConnection 未初始化')
    }

    await pc.setRemoteDescription(offer)
    const answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    this.sendSignalingMessage({
      type: 'answer',
      sdp: answer,
      target_user_id: targetUserId,
    })

    return answer
  }

  // 处理Answer（按发来的对端找 PC）
  async handleAnswer(answer: RTCSessionDescriptionInit, fromUserId?: number): Promise<void> {
    const pc = this.peerConnections.get(fromUserId ?? 0)
    if (!pc) {
      throw new Error('PeerConnection 未初始化')
    }

    await pc.setRemoteDescription(answer)
  }

  // 添加ICE候选（按发来的对端找 PC）
  async addIceCandidate(candidate: RTCIceCandidateInit, fromUserId?: number): Promise<void> {
    const pc = this.peerConnections.get(fromUserId ?? 0)
    if (!pc) {
      throw new Error('PeerConnection 未初始化')
    }

    await pc.addIceCandidate(candidate)
  }
  // 灞忓箷鍏变韩
  async startScreenShare(config?: ScreenShareConfig): Promise<MediaStream> {
    try {
      const constraints: DisplayMediaStreamConstraints = {
        video: {
          displaySurface: config?.displaySurface || 'monitor'
        },
        audio: config?.audio || false
      }

      const screenStream = await navigator.mediaDevices.getDisplayMedia(constraints)
      
      // 替换各对端 PC 上的视频轨道为屏幕流
      if (this.localStream) {
        const videoTrack = screenStream.getVideoTracks()[0]
        for (const pc of this.peerConnections.values()) {
          const sender = pc.getSenders().find(s =>
            s.track && s.track.kind === 'video'
          )
          if (sender) {
            await sender.replaceTrack(videoTrack)
          }
        }
      }

      // 鐩戝惉灞忓箷鍏变韩缁撴潫
      screenStream.getVideoTracks()[0].onended = () => {
        this.stopScreenShare()
      }

      this.emit('screenShareStarted', screenStream)
      return screenStream
    } catch (error) {
      console.error('寮€濮嬪睆骞曞叡浜け璐?', error)
      throw error
    }
  }

  // 鍋滄灞忓箷鍏变韩
  async stopScreenShare(): Promise<void> {
    try {
      // 恢复摄像头轨道到各对端 PC
      if (this.localStream) {
        const videoTrack = this.localStream.getVideoTracks()[0]
        for (const pc of this.peerConnections.values()) {
          const sender = pc.getSenders().find(s =>
            s.track && s.track.kind === 'video'
          )
          if (sender && videoTrack) {
            await sender.replaceTrack(videoTrack)
          }
        }
      }

      this.emit('screenShareStopped')
    } catch (error) {
      console.error('鍋滄灞忓箷鍏变韩澶辫触:', error)
      throw error
    }
  }

  // 闊抽鎺у埗
  toggleAudio(enabled?: boolean): boolean {
    if (!this.localStream) return false

    const audioTrack = this.localStream.getAudioTracks()[0]
    if (audioTrack) {
      audioTrack.enabled = enabled !== undefined ? enabled : !audioTrack.enabled
      this.emit('audioToggled', audioTrack.enabled)
      return audioTrack.enabled
    }
    return false
  }

  // 瑙嗛鎺у埗
  toggleVideo(enabled?: boolean): boolean {
    if (!this.localStream) return false

    const videoTrack = this.localStream.getVideoTracks()[0]
    if (videoTrack) {
      videoTrack.enabled = enabled !== undefined ? enabled : !videoTrack.enabled
      this.emit('videoToggled', videoTrack.enabled)
      return videoTrack.enabled
    }
    return false
  }

  // 鑾峰彇濯掍綋璁惧鍒楄〃
  async getMediaDevices(): Promise<{
    audioInputs: MediaDeviceInfo[]
    videoInputs: MediaDeviceInfo[]
    audioOutputs: MediaDeviceInfo[]
  }> {
    const devices = await navigator.mediaDevices.enumerateDevices()
    
    return {
      audioInputs: devices.filter(d => d.kind === 'audioinput'),
      videoInputs: devices.filter(d => d.kind === 'videoinput'),
      audioOutputs: devices.filter(d => d.kind === 'audiooutput')
    }
  }

  // 鍒囨崲濯掍綋璁惧
  async switchMediaDevice(deviceId: string, kind: 'audio' | 'video'): Promise<void> {
    if (!this.localStream || this.peerConnections.size === 0) return

    const constraints: MediaStreamConstraints = {}
    
    if (kind === 'audio') {
      constraints.audio = { deviceId: { exact: deviceId } }
    } else {
      constraints.video = { deviceId: { exact: deviceId } }
    }

    try {
      const newStream = await navigator.mediaDevices.getUserMedia(constraints)
      const newTrack = newStream.getTracks()[0]
      
      // 在各对端 PC 上替换轨道
      let replaced = false
      for (const pc of this.peerConnections.values()) {
        const sender = pc.getSenders().find(s =>
          s.track && s.track.kind === kind
        )
        if (sender) {
          await sender.replaceTrack(newTrack)
          replaced = true
        }
      }

      if (replaced) {
        // 更新本地流
        const oldTrack = this.localStream.getTracks().find(t => t.kind === kind)
        if (oldTrack) {
          this.localStream.removeTrack(oldTrack)
          oldTrack.stop()
        }
        this.localStream.addTrack(newTrack)
      }
    } catch (error) {
      console.error('鍒囨崲濯掍綋璁惧澶辫触:', error)
      throw error
    }
  }

  // 网络质量监控
  async getConnectionStats(): Promise<any> {
    if (this.peerConnections.size === 0) return null

    const result: any = {}
    for (const [targetUserId, pc] of this.peerConnections) {
      const stats = await pc.getStats()
      const entry: any = {}
      stats.forEach((report) => {
        if (report.type === 'inbound-rtp' || report.type === 'outbound-rtp') {
          entry[report.type] = {
            bytesReceived: report.bytesReceived,
            bytesSent: report.bytesSent,
            packetsReceived: report.packetsReceived,
            packetsSent: report.packetsSent,
            packetsLost: report.packetsLost,
            jitter: report.jitter,
            roundTripTime: report.roundTripTime
          }
        }
      })
      result[targetUserId] = entry
    }

    return result
  }

  // 处理信令消息：offer/answer/ice 按 from_user_id 找到对应的 PC；
  // room-joined 携带自己的 session_id 与已在场者，供上层发起 offer。
  private handleSignalingMessage(message: any): void {
    switch (message.type) {
      case 'room-joined':
        this.sessionId = message.session_id ?? null
        this.emit('roomJoined', message)
        break
      case 'offer':
        this.createAnswer(message.sdp, message.from_user_id)
          .catch((e) => console.warn('处理 offer 失败:', e))
        break
      case 'answer':
        this.handleAnswer(message.sdp, message.from_user_id)
          .catch((e) => console.warn('处理 answer 失败:', e))
        break
      case 'ice-candidate':
        this.addIceCandidate(message.candidate, message.from_user_id)
          .catch((e) => console.warn('处理 ICE 失败:', e))
        break
      case 'participant-joined':
        this.emit('participantJoined', message)
        break
      case 'participant-left':
        this.emit('participantLeft', message)
        break
      case 'screen-share-started':
        this.emit('remoteScreenShareStarted', message)
        break
      case 'screen-share-stopped':
        this.emit('remoteScreenShareStopped', message)
        break
      case 'pong':
        break
      default:
        console.log('未知信令消息类型:', message.type)
    }
  }

  // 鍙戦€佷俊浠ゆ秷鎭?
  sendSignalingMessage(message: any): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message))
    }
  }

  // 浜嬩欢绯荤粺
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(callback)
  }

  off(event: string, callback: Function): void {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      const index = listeners.indexOf(callback)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  private emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      listeners.forEach(callback => callback(data))
    }
  }

  // 娓呯悊璧勬簮
  cleanup(): void {
    // 鍋滄鏈湴娴?
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop())
      this.localStream = null
    }

    // 关闭全部 PeerConnection
    this.peerConnections.forEach((pc) => pc.close())
    this.peerConnections.clear()
    this.sessionId = null

    // 鏂紑WebSocket
    this.disconnectSignaling()

    // 娓呯悊杩滅▼娴?
    this.remoteStreams.clear()

    // 娓呯悊浜嬩欢鐩戝惉鍣?
    this.eventListeners.clear()
  }
}

// 鍒涘缓鍗曚緥瀹炰緥
export const webrtcService = new WebRTCService()

// 瀵煎嚭榛樿瀹炰緥
export default webrtcService
