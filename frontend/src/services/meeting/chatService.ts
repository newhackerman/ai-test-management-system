import { apiClient } from '@/services/api/client'

export interface ChatMessage {
  id: string
  meetingId: number
  senderId: number
  senderName: string
  senderAvatar?: string
  content: string
  messageType: 'TEXT' | 'FILE' | 'IMAGE' | 'EMOJI' | 'SYSTEM'
  timestamp: string
  edited?: boolean
  editedAt?: string
  replyTo?: string
  mentions?: number[]
  attachments?: ChatAttachment[]
  reactions?: ChatReaction[]
}

export interface ChatAttachment {
  id: string
  name: string
  size: number
  type: string
  url: string
  thumbnailUrl?: string
}

export interface ChatReaction {
  emoji: string
  count: number
  users: number[]
}

export interface SendMessageRequest {
  content: string
  messageType?: 'TEXT' | 'FILE' | 'IMAGE' | 'EMOJI'
  replyTo?: string
  mentions?: number[]
  attachments?: File[]
}

export class ChatService {
  private baseUrl = '/api/v1/meetings'
  private websocket: WebSocket | null = null
  private eventListeners: Map<string, Function[]> = new Map()

  // WebSocket连接管理
  async connectChat(meetingId: number, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `${process.env.VITE_WS_URL}/meetings/${meetingId}/chat?token=${token}`
      
      this.websocket = new WebSocket(wsUrl)
      
      this.websocket.onopen = () => {
        console.log('聊天WebSocket连接已建立')
        resolve()
      }
      
      this.websocket.onerror = (error) => {
        console.error('聊天WebSocket连接错误:', error)
        reject(error)
      }
      
      this.websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleChatMessage(message)
        } catch (error) {
          console.error('解析聊天消息失败:', error)
        }
      }
      
      this.websocket.onclose = () => {
        console.log('聊天WebSocket连接已关闭')
        this.emit('disconnected')
      }
    })
  }

  disconnectChat(): void {
    if (this.websocket) {
      this.websocket.close()
      this.websocket = null
    }
  }

  // 消息发送
  async sendMessage(meetingId: number, message: SendMessageRequest): Promise<ChatMessage> {
    if (message.attachments && message.attachments.length > 0) {
      // 如果有附件，先上传附件
      const attachments = await this.uploadAttachments(meetingId, message.attachments)
      
      const response = await apiClient.post<ChatMessage>(
        `${this.baseUrl}/${meetingId}/chat/send`,
        {
          ...message,
          attachments: attachments.map(a => a.id)
        }
      )
      return response.data
    } else {
      const response = await apiClient.post<ChatMessage>(
        `${this.baseUrl}/${meetingId}/chat/send`,
        message
      )
      return response.data
    }
  }

  // 实时发送消息（通过WebSocket）
  sendMessageRealtime(message: SendMessageRequest): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify({
        type: 'send_message',
        data: message
      }))
    }
  }

  // 发送打字状态
  sendTypingStatus(meetingId: number, isTyping: boolean): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify({
        type: 'typing_status',
        data: { isTyping }
      }))
    }
  }

  // 消息管理
  async getChatHistory(meetingId: number, params?: {
    page?: number
    pageSize?: number
    before?: string // 消息ID
    after?: string // 消息ID
    messageType?: string
    searchQuery?: string
  }): Promise<{
    messages: ChatMessage[]
    total: number
    hasMore: boolean
  }> {
    const response = await apiClient.get(
      `${this.baseUrl}/${meetingId}/chat/history`,
      { params }
    )
    return response.data
  }

  async editMessage(meetingId: number, messageId: string, content: string): Promise<ChatMessage> {
    const response = await apiClient.put<ChatMessage>(
      `${this.baseUrl}/${meetingId}/chat/messages/${messageId}`,
      { content }
    )
    return response.data
  }

  async deleteMessage(meetingId: number, messageId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}`)
  }

  async pinMessage(meetingId: number, messageId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}/pin`)
  }

  async unpinMessage(meetingId: number, messageId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}/pin`)
  }

  async getPinnedMessages(meetingId: number): Promise<ChatMessage[]> {
    const response = await apiClient.get<ChatMessage[]>(
      `${this.baseUrl}/${meetingId}/chat/pinned`
    )
    return response.data
  }

  // 消息反应
  async addReaction(meetingId: number, messageId: string, emoji: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}/reactions`, {
      emoji
    })
  }

  async removeReaction(meetingId: number, messageId: string, emoji: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}/reactions/${emoji}`)
  }

  // 文件上传
  async uploadAttachments(meetingId: number, files: File[]): Promise<ChatAttachment[]> {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append(`files`, file)
    })

    const response = await apiClient.post<ChatAttachment[]>(
      `${this.baseUrl}/${meetingId}/chat/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  }

  async downloadAttachment(meetingId: number, attachmentId: string): Promise<string> {
    const response = await apiClient.get(
      `${this.baseUrl}/${meetingId}/chat/attachments/${attachmentId}/download`,
      { responseType: 'blob' }
    )
    
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    return url
  }

  // 消息搜索
  async searchMessages(meetingId: number, query: string, filters?: {
    messageType?: string
    senderId?: number
    dateFrom?: string
    dateTo?: string
    hasAttachments?: boolean
  }): Promise<{
    messages: ChatMessage[]
    total: number
    highlights: Record<string, string[]>
  }> {
    const response = await apiClient.get(
      `${this.baseUrl}/${meetingId}/chat/search`,
      { 
        params: { 
          query,
          ...filters
        }
      }
    )
    return response.data
  }

  // 消息导出
  async exportChatHistory(meetingId: number, format: 'JSON' | 'CSV' | 'PDF' | 'HTML'): Promise<string> {
    const response = await apiClient.get(
      `${this.baseUrl}/${meetingId}/chat/export`,
      { 
        params: { format },
        responseType: 'blob'
      }
    )
    
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    return url
  }

  // 聊天设置
  async updateChatSettings(meetingId: number, settings: {
    allowFileUpload?: boolean
    allowEmojis?: boolean
    allowMentions?: boolean
    maxMessageLength?: number
    allowedFileTypes?: string[]
    maxFileSize?: number
  }): Promise<void> {
    await apiClient.put(`${this.baseUrl}/${meetingId}/chat/settings`, settings)
  }

  async getChatSettings(meetingId: number): Promise<{
    allowFileUpload: boolean
    allowEmojis: boolean
    allowMentions: boolean
    maxMessageLength: number
    allowedFileTypes: string[]
    maxFileSize: number
  }> {
    const response = await apiClient.get(`${this.baseUrl}/${meetingId}/chat/settings`)
    return response.data
  }

  // 用户管理
  async muteUser(meetingId: number, userId: number, duration?: number): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/chat/users/${userId}/mute`, {
      duration
    })
  }

  async unmuteUser(meetingId: number, userId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/chat/users/${userId}/mute`)
  }

  async banUser(meetingId: number, userId: number, reason?: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/chat/users/${userId}/ban`, {
      reason
    })
  }

  async unbanUser(meetingId: number, userId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${meetingId}/chat/users/${userId}/ban`)
  }

  // 消息过滤和审核
  async reportMessage(meetingId: number, messageId: string, reason: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${meetingId}/chat/messages/${messageId}/report`, {
      reason
    })
  }

  async getReportedMessages(meetingId: number): Promise<Array<{
    message: ChatMessage
    reports: Array<{
      reporterId: number
      reason: string
      reportedAt: string
    }>
  }>> {
    const response = await apiClient.get(`${this.baseUrl}/${meetingId}/chat/reported`)
    return response.data
  }

  // 聊天统计
  async getChatStatistics(meetingId: number): Promise<{
    totalMessages: number
    totalParticipants: number
    messagesByType: Record<string, number>
    messagesByUser: Record<number, number>
    averageMessageLength: number
    mostActiveUsers: Array<{
      userId: number
      userName: string
      messageCount: number
    }>
    peakActivity: {
      time: string
      messageCount: number
    }
  }> {
    const response = await apiClient.get(`${this.baseUrl}/${meetingId}/chat/statistics`)
    return response.data
  }

  // 处理聊天消息
  private handleChatMessage(data: any): void {
    switch (data.type) {
      case 'new_message':
        this.emit('messageReceived', data.message)
        break
      case 'message_edited':
        this.emit('messageEdited', data.message)
        break
      case 'message_deleted':
        this.emit('messageDeleted', data.messageId)
        break
      case 'reaction_added':
        this.emit('reactionAdded', data)
        break
      case 'reaction_removed':
        this.emit('reactionRemoved', data)
        break
      case 'user_typing':
        this.emit('userTyping', data)
        break
      case 'user_stopped_typing':
        this.emit('userStoppedTyping', data)
        break
      case 'message_pinned':
        this.emit('messagePinned', data.messageId)
        break
      case 'message_unpinned':
        this.emit('messageUnpinned', data.messageId)
        break
      default:
        console.log('未知聊天消息类型:', data.type)
    }
  }

  // 事件系统
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

  // 清理资源
  cleanup(): void {
    this.disconnectChat()
    this.eventListeners.clear()
  }
}

// 创建单例实例
export const chatService = new ChatService()

// 导出默认实例
export default chatService