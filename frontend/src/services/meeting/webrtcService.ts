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
  private peerConnection: RTCPeerConnection | null = null
  private localStream: MediaStream | null = null
  private remoteStreams: Map<string, MediaStream> = new Map()
  private eventListeners: Map<string, Function[]> = new Map()

  // WebRTC閰嶇疆鑾峰彇
  async getWebRTCConfig(meetingId: number): Promise<WebRTCConfig> {
    const response = await apiClient.get<WebRTCConfig>(
      `${this.baseUrl}/${meetingId}/webrtc/config`
    )
    return response.data
  }

  // 寤虹珛WebSocket杩炴帴
  async connectSignaling(meetingCode: string, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsBaseUrl = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1`
      const wsUrl = `${wsBaseUrl}/meetings/ws/${meetingCode}?token=${token}`
      
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

  // 鍒濆鍖朠eerConnection
  async initializePeerConnection(config: WebRTCConfig): Promise<void> {
    this.peerConnection = new RTCPeerConnection({
      iceServers: config.iceServers
    })

    // 澶勭悊ICE鍊欓€?
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendSignalingMessage({
          type: 'ice-candidate',
          candidate: event.candidate
        })
      }
    }

    // 澶勭悊杩滅▼娴?
    this.peerConnection.ontrack = (event) => {
      const [remoteStream] = event.streams
      const participantId = event.track.id // 鎴栦粠鍏朵粬鍦版柟鑾峰彇鍙備笌鑰匢D
      this.remoteStreams.set(participantId, remoteStream)
      this.emit('remoteStreamAdded', { participantId, stream: remoteStream })
    }

    // 澶勭悊杩炴帴鐘舵€佸彉鍖?
    this.peerConnection.onconnectionstatechange = () => {
      const state = this.peerConnection?.connectionState
      console.log('PeerConnection鐘舵€?', state)
      this.emit('connectionStateChanged', state)
    }
  }

  // 鑾峰彇鏈湴濯掍綋娴?
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
      this.emit('localStreamReady', stream)
      
      return stream
    } catch (error) {
      console.error('鑾峰彇鏈湴濯掍綋娴佸け璐?', error)
      throw error
    }
  }

  // 娣诲姞鏈湴娴佸埌PeerConnection
  addLocalStreamToPeer(): void {
    if (this.localStream && this.peerConnection) {
      this.localStream.getTracks().forEach(track => {
        this.peerConnection!.addTrack(track, this.localStream!)
      })
    }
  }

  // 鍒涘缓Offer
  async createOffer(): Promise<RTCSessionDescriptionInit> {
    if (!this.peerConnection) {
      throw new Error('PeerConnection 未初始化')
    }

    const offer = await this.peerConnection.createOffer()
    await this.peerConnection.setLocalDescription(offer)
    
    this.sendSignalingMessage({
      type: 'offer',
      sdp: offer
    })
    
    return offer
  }

  // 鍒涘缓Answer
  async createAnswer(offer: RTCSessionDescriptionInit): Promise<RTCSessionDescriptionInit> {
    if (!this.peerConnection) {
      throw new Error('PeerConnection 未初始化')
    }

    await this.peerConnection.setRemoteDescription(offer)
    const answer = await this.peerConnection.createAnswer()
    await this.peerConnection.setLocalDescription(answer)
    
    this.sendSignalingMessage({
      type: 'answer',
      sdp: answer
    })
    
    return answer
  }

  // 澶勭悊Answer
  async handleAnswer(answer: RTCSessionDescriptionInit): Promise<void> {
    if (!this.peerConnection) {
      throw new Error('PeerConnection 未初始化')
    }

    await this.peerConnection.setRemoteDescription(answer)
  }

  // 娣诲姞ICE鍊欓€?
  async addIceCandidate(candidate: RTCIceCandidateInit): Promise<void> {
    if (!this.peerConnection) {
      throw new Error('PeerConnection 未初始化')
    }

    await this.peerConnection.addIceCandidate(candidate)
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
      
      // 鏇挎崲瑙嗛杞ㄩ亾
      if (this.peerConnection && this.localStream) {
        const videoTrack = screenStream.getVideoTracks()[0]
        const sender = this.peerConnection.getSenders().find(s => 
          s.track && s.track.kind === 'video'
        )
        
        if (sender) {
          await sender.replaceTrack(videoTrack)
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
      // 鎭㈠鎽勫儚澶?
      if (this.localStream && this.peerConnection) {
        const videoTrack = this.localStream.getVideoTracks()[0]
        const sender = this.peerConnection.getSenders().find(s => 
          s.track && s.track.kind === 'video'
        )
        
        if (sender && videoTrack) {
          await sender.replaceTrack(videoTrack)
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
    if (!this.localStream || !this.peerConnection) return

    const constraints: MediaStreamConstraints = {}
    
    if (kind === 'audio') {
      constraints.audio = { deviceId: { exact: deviceId } }
    } else {
      constraints.video = { deviceId: { exact: deviceId } }
    }

    try {
      const newStream = await navigator.mediaDevices.getUserMedia(constraints)
      const newTrack = newStream.getTracks()[0]
      
      // 鏇挎崲杞ㄩ亾
      const sender = this.peerConnection.getSenders().find(s => 
        s.track && s.track.kind === kind
      )
      
      if (sender) {
        await sender.replaceTrack(newTrack)
        
        // 鏇存柊鏈湴娴?
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

  // 缃戠粶璐ㄩ噺鐩戞帶
  async getConnectionStats(): Promise<any> {
    if (!this.peerConnection) return null

    const stats = await this.peerConnection.getStats()
    const result: any = {}

    stats.forEach((report) => {
      if (report.type === 'inbound-rtp' || report.type === 'outbound-rtp') {
        result[report.type] = {
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

    return result
  }

  // 澶勭悊淇′护娑堟伅
  private handleSignalingMessage(message: any): void {
    switch (message.type) {
      case 'offer':
        this.createAnswer(message.sdp)
        break
      case 'answer':
        this.handleAnswer(message.sdp)
        break
      case 'ice-candidate':
        this.addIceCandidate(message.candidate)
        break
      case 'participant-joined':
        this.emit('participantJoined', message.participant)
        break
      case 'participant-left':
        this.emit('participantLeft', message.participant)
        break
      case 'screen-share-started':
        this.emit('remoteScreenShareStarted', message)
        break
      case 'screen-share-stopped':
        this.emit('remoteScreenShareStopped', message)
        break
      default:
        console.log('鏈煡淇′护娑堟伅绫诲瀷:', message.type)
    }
  }

  // 鍙戦€佷俊浠ゆ秷鎭?
  private sendSignalingMessage(message: any): void {
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

    // 鍏抽棴PeerConnection
    if (this.peerConnection) {
      this.peerConnection.close()
      this.peerConnection = null
    }

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
