// @ts-nocheck
// 鐧芥澘鏈嶅姟 - 澶勭悊鐧芥澘鏁版嵁鐨勪繚瀛樸€佸悓姝ュ拰鍒嗕韩
import { api } from './api'
import type { WhiteboardData } from '@/hooks/meeting/useWhiteboard'

export interface WhiteboardSaveRequest {
  meetingId: number
  name: string
  data: WhiteboardData
  isPublic?: boolean
}

export interface WhiteboardShareRequest {
  whiteboardId: string
  permissions: {
    canView: boolean
    canEdit: boolean
    canDownload: boolean
  }
  expiresAt?: string
}

export interface SavedWhiteboard {
  id: string
  meetingId: number
  name: string
  data: WhiteboardData
  createdBy: number
  createdAt: string
  updatedAt: string
  isPublic: boolean
  shareUrl?: string
}

export interface WhiteboardSyncEvent {
  type: 'element_added' | 'element_updated' | 'element_deleted' | 'canvas_cleared' | 'view_changed'
  data: any
  userId: number
  timestamp: number
}

class WhiteboardService {
  private wsConnection: WebSocket | null = null
  private syncCallbacks: ((event: WhiteboardSyncEvent) => void)[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  /**
   * 淇濆瓨鐧芥澘鍒版湇鍔″櫒
   */
  async saveWhiteboard(request: WhiteboardSaveRequest): Promise<SavedWhiteboard> {
    try {
      const response = await api.post('/meetings/whiteboard/save', request)
      return response.data
    } catch (error) {
      console.error('Failed to save whiteboard:', error)
      throw new Error('淇濆瓨鐧芥澘澶辫触')
    }
  }

  /**
   * 鍔犺浇鐧芥澘鏁版嵁
   */
  async loadWhiteboard(whiteboardId: string): Promise<SavedWhiteboard> {
    try {
      const response = await api.get(`/meetings/whiteboard/${whiteboardId}`)
      return response.data
    } catch (error) {
      console.error('Failed to load whiteboard:', error)
      throw new Error('鍔犺浇鐧芥澘澶辫触')
    }
  }

  /**
   * 鑾峰彇浼氳鐨勭櫧鏉垮垪琛?
   */
  async getMeetingWhiteboards(meetingId: number): Promise<SavedWhiteboard[]> {
    try {
      const response = await api.get(`/meetings/${meetingId}/whiteboards`)
      return response.data
    } catch (error) {
      console.error('Failed to get meeting whiteboards:', error)
      throw new Error('鑾峰彇鐧芥澘鍒楄〃澶辫触')
    }
  }

  /**
   * 鍒嗕韩鐧芥澘
   */
  async shareWhiteboard(request: WhiteboardShareRequest): Promise<{ shareUrl: string }> {
    try {
      const response = await api.post('/meetings/whiteboard/share', request)
      return response.data
    } catch (error) {
      console.error('Failed to share whiteboard:', error)
      throw new Error('鍒嗕韩鐧芥澘澶辫触')
    }
  }

  /**
   * 鍒犻櫎鐧芥澘
   */
  async deleteWhiteboard(whiteboardId: string): Promise<void> {
    try {
      await api.delete(`/meetings/whiteboard/${whiteboardId}`)
    } catch (error) {
      console.error('Failed to delete whiteboard:', error)
      throw new Error('鍒犻櫎鐧芥澘澶辫触')
    }
  }

  /**
   * 杩炴帴瀹炴椂鍚屾
   */
  connectSync(meetingId: number, userId: number): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = `${process.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/meetings/${meetingId}/whiteboard`
      this.wsConnection = new WebSocket(wsUrl)

      this.wsConnection.onopen = () => {
        console.log('Whiteboard sync connected')
        this.reconnectAttempts = 0
        
        // 鍙戦€佽璇佷俊鎭?
        this.sendSyncMessage({
          type: 'auth',
          userId,
          timestamp: Date.now()
        })
      }

      this.wsConnection.onmessage = (event) => {
        try {
          const syncEvent: WhiteboardSyncEvent = JSON.parse(event.data)
          this.handleSyncEvent(syncEvent)
        } catch (error) {
          console.error('Failed to parse sync message:', error)
        }
      }

      this.wsConnection.onclose = () => {
        console.log('Whiteboard sync disconnected')
        this.handleReconnect(meetingId, userId)
      }

      this.wsConnection.onerror = (error) => {
        console.error('Whiteboard sync error:', error)
      }
    } catch (error) {
      console.error('Failed to connect whiteboard sync:', error)
    }
  }

  /**
   * 鏂紑瀹炴椂鍚屾
   */
  disconnectSync(): void {
    if (this.wsConnection) {
      this.wsConnection.close()
      this.wsConnection = null
    }
    this.syncCallbacks = []
    this.reconnectAttempts = 0
  }

  /**
   * 鍙戦€佸悓姝ユ秷鎭?
   */
  sendSyncMessage(message: any): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify(message))
    }
  }

  /**
   * 鍚屾鐧芥澘鍏冪礌娣诲姞
   */
  syncElementAdded(element: any, userId: number): void {
    this.sendSyncMessage({
      type: 'element_added',
      data: element,
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 鍚屾鐧芥澘鍏冪礌鏇存柊
   */
  syncElementUpdated(element: any, userId: number): void {
    this.sendSyncMessage({
      type: 'element_updated',
      data: element,
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 鍚屾鐧芥澘鍏冪礌鍒犻櫎
   */
  syncElementDeleted(elementId: string, userId: number): void {
    this.sendSyncMessage({
      type: 'element_deleted',
      data: { elementId },
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 鍚屾鐢诲竷娓呯┖
   */
  syncCanvasCleared(userId: number): void {
    this.sendSyncMessage({
      type: 'canvas_cleared',
      data: {},
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 鍚屾瑙嗗浘鍙樺寲锛堢缉鏀俱€佸钩绉伙級
   */
  syncViewChanged(view: { zoom: number; pan: { x: number; y: number } }, userId: number): void {
    this.sendSyncMessage({
      type: 'view_changed',
      data: view,
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 鍚屾鍏夋爣浣嶇疆
   */
  syncCursorPosition(position: { x: number; y: number }, userId: number): void {
    this.sendSyncMessage({
      type: 'cursor_moved',
      data: position,
      userId,
      timestamp: Date.now()
    })
  }

  /**
   * 娣诲姞鍚屾浜嬩欢鐩戝惉鍣?
   */
  onSyncEvent(callback: (event: WhiteboardSyncEvent) => void): void {
    this.syncCallbacks.push(callback)
  }

  /**
   * 绉婚櫎鍚屾浜嬩欢鐩戝惉鍣?
   */
  offSyncEvent(callback: (event: WhiteboardSyncEvent) => void): void {
    const index = this.syncCallbacks.indexOf(callback)
    if (index > -1) {
      this.syncCallbacks.splice(index, 1)
    }
  }

  /**
   * 澶勭悊鍚屾浜嬩欢
   */
  private handleSyncEvent(event: WhiteboardSyncEvent): void {
    this.syncCallbacks.forEach(callback => {
      try {
        callback(event)
      } catch (error) {
        console.error('Sync callback error:', error)
      }
    })
  }

  /**
   * 澶勭悊閲嶈繛
   */
  private handleReconnect(meetingId: number, userId: number): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      setTimeout(() => {
        console.log(`Attempting to reconnect whiteboard sync (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        this.connectSync(meetingId, userId)
      }, delay)
    } else {
      console.error('Max reconnection attempts reached for whiteboard sync')
    }
  }

  /**
   * 瀵煎嚭鐧芥澘涓哄浘鐗?
   */
  async exportAsImage(canvas: HTMLCanvasElement, format: 'png' | 'jpeg' = 'png'): Promise<Blob> {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('Failed to export canvas as image'))
        }
      }, `image/${format}`)
    })
  }

  /**
   * 瀵煎嚭鐧芥澘涓篜DF
   */
  async exportAsPDF(canvas: HTMLCanvasElement, filename: string = 'whiteboard.pdf'): Promise<void> {
    try {
      // 鍔ㄦ€佸鍏?jsPDF 浠ュ噺灏戝寘澶у皬
      const { jsPDF } = await import('jspdf')
      
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height]
      })
      
      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height)
      pdf.save(filename)
    } catch (error) {
      console.error('Failed to export as PDF:', error)
      throw new Error('瀵煎嚭PDF澶辫触')
    }
  }

  /**
   * 鑾峰彇鐧芥澘缁熻淇℃伅
   */
  async getWhiteboardStats(whiteboardId: string): Promise<{
    elementCount: number
    collaboratorCount: number
    lastModified: string
    viewCount: number
  }> {
    try {
      const response = await api.get(`/meetings/whiteboard/${whiteboardId}/stats`)
      return response.data
    } catch (error) {
      console.error('Failed to get whiteboard stats:', error)
      throw new Error('鑾峰彇鐧芥澘缁熻澶辫触')
    }
  }
}

// 鍒涘缓鍗曚緥瀹炰緥
export const whiteboardService = new WhiteboardService()

// 瀵煎嚭绫诲瀷鍜屾湇鍔?
export default whiteboardService
export type { WhiteboardSyncEvent, SavedWhiteboard }