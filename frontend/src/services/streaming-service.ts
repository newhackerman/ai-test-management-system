/**
 * 流式响应服务
 */

export interface StreamingMessage {
  id?: number;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  isStreaming?: boolean;
  isComplete?: boolean;
  isError?: boolean;
  error?: string;
  metadata?: {
    provider?: string;
    model?: string;
    tokens_used?: number;
    confidence_score?: number;
    processing_time?: number;
  };
}

export interface StreamingEvent {
  type: 'user_message' | 'ai_start' | 'ai_content' | 'ai_metadata' | 'ai_complete' | 'error' | 'stream_end';
  data: any;
}

export interface StreamingOptions {
  onMessage?: (message: StreamingMessage) => void;
  onError?: (error: string) => void;
  onComplete?: (message: StreamingMessage) => void;
  onStart?: () => void;
  onEnd?: () => void;
}

export class StreamingService {
  private baseUrl = '/api/v1/streaming';
  private activeStreams = new Map<string, any>();

  /**
   * 开始流式对话
   */
  async startStreaming(
    conversationId: number,
    content: string,
    options: StreamingOptions = {},
    metadata?: Record<string, any>
  ): Promise<string> {
    const streamId = `${conversationId}_${Date.now()}`;
    
    try {
      // 构建请求参数
      const requestBody = {
        content,
        metadata: metadata || {}
      };
      
      // 构建请求URL，使用POST方式发送数据并接收流式响应
      const url = `${this.baseUrl}/conversations/${conversationId}/stream`;
      
      // 使用fetch发送POST请求并处理流式响应
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 处理流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }
      
      // 存储流式连接信息
      this.activeStreams.set(streamId, { reader, controller: new AbortController() });
      
      // 处理流式数据
      this.processStreamingResponse(reader, streamId, options);
      
      return streamId;
      
    } catch (error) {
      console.error('Error starting streaming:', error);
      options.onError?.('启动流式对话失败');
      throw error;
    }
  }
  
  /**
   * 处理流式响应
   */
  private async processStreamingResponse(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    streamId: string,
    options: StreamingOptions
  ): Promise<void> {
    const decoder = new TextDecoder();
    let buffer = '';
    
    // 初始化流式消息状态
    let currentMessage: StreamingMessage = {
      content: '',
      role: 'assistant',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      isComplete: false,
      metadata: {}
    };
    
    options.onStart?.();
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // 解码数据
        buffer += decoder.decode(value, { stream: true });
        
        // 处理SSE数据
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留不完整的行
        
        for (const line of lines) {
          if (line.trim() === '') continue;
          
          if (line.startsWith('event: ')) {
            const eventType = line.substring(7).trim();
            continue;
          }
          
          if (line.startsWith('data: ')) {
            const data = line.substring(6).trim();
            
            try {
              const eventData = JSON.parse(data);
              this.handleStreamEvent({ type: 'ai_content', data: eventData }, currentMessage, options);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error processing streaming response:', error);
      options.onError?.('处理流式响应时出错');
    } finally {
      this.activeStreams.delete(streamId);
      options.onEnd?.();
    }
  }
  
  /**
   * 停止流式对话
   */
  stopStreaming(streamId: string): void {
    const streamInfo = this.activeStreams.get(streamId);
    if (streamInfo) {
      if ('close' in streamInfo) {
        // EventSource
        (streamInfo as EventSource).close();
      } else {
        // ReadableStream
        const { reader, controller } = streamInfo as any;
        controller.abort();
        reader.cancel();
      }
      this.activeStreams.delete(streamId);
      console.log(`Stopped streaming: ${streamId}`);
    }
  }
  
  /**
   * 停止所有流式对话
   */
  stopAllStreaming(): void {
    this.activeStreams.forEach((streamInfo, streamId) => {
      if ('close' in streamInfo) {
        // EventSource
        (streamInfo as EventSource).close();
      } else {
        // ReadableStream
        const { reader, controller } = streamInfo as any;
        controller.abort();
        reader.cancel();
      }
      console.log(`Stopped streaming: ${streamId}`);
    });
    this.activeStreams.clear();
  }
  
  /**
   * 获取活跃的流式连接数
   */
  getActiveStreamCount(): number {
    return this.activeStreams.size;
  }
  
  /**
   * 检查是否有活跃的流式连接
   */
  hasActiveStreams(): boolean {
    return this.activeStreams.size > 0;
  }
  
  /**
   * 处理流式事件
   */
  private handleStreamEvent(
    event: StreamingEvent,
    currentMessage: StreamingMessage,
    options: StreamingOptions
  ): void {
    switch (event.type) {
      case 'user_message':
        // 用户消息确认，可以在这里更新UI状态
        break;
        
      case 'ai_start':
        currentMessage.metadata = {
          ...currentMessage.metadata,
          provider: event.data.provider,
          model: event.data.model
        };
        options.onMessage?.(currentMessage);
        break;
        
      case 'ai_content':
        currentMessage.content += event.data.delta || '';
        currentMessage.isStreaming = true;
        options.onMessage?.(currentMessage);
        break;
        
      case 'ai_metadata':
        currentMessage.metadata = {
          ...currentMessage.metadata,
          ...event.data
        };
        options.onMessage?.(currentMessage);
        break;
        
      case 'ai_complete':
        currentMessage.id = event.data.id;
        currentMessage.content = event.data.content;
        currentMessage.isStreaming = false;
        currentMessage.isComplete = true;
        currentMessage.metadata = {
          ...currentMessage.metadata,
          ...event.data
        };
        options.onMessage?.(currentMessage);
        options.onComplete?.(currentMessage);
        break;
        
      case 'error':
        currentMessage.isError = true;
        currentMessage.error = event.data.message;
        currentMessage.isStreaming = false;
        options.onMessage?.(currentMessage);
        options.onError?.(event.data.message);
        break;
        
      case 'stream_end':
        options.onEnd?.();
        break;
    }
  }
}

export const streamingService = new StreamingService();