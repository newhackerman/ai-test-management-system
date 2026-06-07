/**
 * 流式响应相关的React Hooks
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { streamingService, StreamingMessage, StreamingOptions } from '../services/streaming-service';

export interface UseStreamingOptions {
  onMessage?: (message: StreamingMessage) => void;
  onError?: (error: string) => void;
  onComplete?: (message: StreamingMessage) => void;
  onStart?: () => void;
  onEnd?: () => void;
}

export function useStreaming(options: UseStreamingOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeStreamId = useRef<string | null>(null);
  
  // 开始流式对话
  const startStreaming = useCallback(async (
    conversationId: number,
    content: string,
    metadata?: Record<string, any>
  ) => {
    try {
      setIsStreaming(true);
      setError(null);
      setStreamingMessage(null);
      
      const streamOptions: StreamingOptions = {
        onStart: () => {
          options.onStart?.();
        },
        
        onMessage: (message: StreamingMessage) => {
          setStreamingMessage({ ...message });
          options.onMessage?.(message);
        },
        
        onComplete: (message: StreamingMessage) => {
          setStreamingMessage({ ...message });
          setIsStreaming(false);
          options.onComplete?.(message);
        },
        
        onError: (errorMessage: string) => {
          setError(errorMessage);
          setIsStreaming(false);
          options.onError?.(errorMessage);
        },
        
        onEnd: () => {
          setIsStreaming(false);
          activeStreamId.current = null;
          options.onEnd?.();
        }
      };
      
      const streamId = await streamingService.startStreaming(
        conversationId,
        content,
        streamOptions,
        metadata
      );
      
      activeStreamId.current = streamId;
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '启动流式对话失败';
      setError(errorMessage);
      setIsStreaming(false);
      options.onError?.(errorMessage);
    }
  }, [options]);
  
  // 停止流式对话
  const stopStreaming = useCallback(() => {
    if (activeStreamId.current) {
      streamingService.stopStreaming(activeStreamId.current);
      activeStreamId.current = null;
    }
    setIsStreaming(false);
  }, []);
  
  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
  }, []);
  
  // 重置状态
  const reset = useCallback(() => {
    stopStreaming();
    setStreamingMessage(null);
    setError(null);
  }, [stopStreaming]);
  
  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (activeStreamId.current) {
        streamingService.stopStreaming(activeStreamId.current);
      }
    };
  }, []);
  
  return {
    isStreaming,
    streamingMessage,
    error,
    startStreaming,
    stopStreaming,
    clearError,
    reset,
    hasActiveStream: !!activeStreamId.current
  };
}

/**
 * 流式消息管理Hook
 */
export function useStreamingMessages() {
  const [messages, setMessages] = useState<StreamingMessage[]>([]);
  const [isAnyStreaming, setIsAnyStreaming] = useState(false);
  
  // 添加用户消息
  const addUserMessage = useCallback((content: string) => {
    const userMessage: StreamingMessage = {
      content,
      role: 'user',
      timestamp: new Date().toISOString(),
      isComplete: true
    };
    
    setMessages(prev => [...prev, userMessage]);
    return userMessage;
  }, []);
  
  // 添加或更新流式消息
  const updateStreamingMessage = useCallback((message: StreamingMessage) => {
    setMessages(prev => {
      const existingIndex = prev.findIndex(m => 
        m.role === 'assistant' && 
        (m.id === message.id || (!m.id && !message.id && m === prev[prev.length - 1]))
      );
      
      if (existingIndex >= 0) {
        // 更新现有消息
        const newMessages = [...prev];
        newMessages[existingIndex] = { ...message };
        return newMessages;
      } else {
        // 添加新消息
        return [...prev, { ...message }];
      }
    });
    
    setIsAnyStreaming(message.isStreaming || false);
  }, []);
  
  // 清除所有消息
  const clearMessages = useCallback(() => {
    setMessages([]);
    setIsAnyStreaming(false);
  }, []);
  
  // 移除指定消息
  const removeMessage = useCallback((messageId: number | string) => {
    setMessages(prev => prev.filter(m => m.id !== messageId));
  }, []);
  
  return {
    messages,
    isAnyStreaming,
    addUserMessage,
    updateStreamingMessage,
    clearMessages,
    removeMessage
  };
}

/**
 * 流式对话Hook - 结合消息管理和流式功能
 */
export function useStreamingChat(conversationId: number) {
  const {
    messages,
    isAnyStreaming,
    addUserMessage,
    updateStreamingMessage,
    clearMessages
  } = useStreamingMessages();
  
  const {
    isStreaming,
    error,
    startStreaming,
    stopStreaming,
    clearError,
    reset
  } = useStreaming({
    onMessage: updateStreamingMessage,
    onError: (error) => {
      console.error('Streaming error:', error);
    }
  });
  
  // 发送消息并开始流式响应
  const sendMessage = useCallback(async (
    content: string,
    metadata?: Record<string, any>
  ) => {
    if (!content.trim() || isStreaming) return;
    
    // 添加用户消息
    addUserMessage(content);
    
    // 开始流式AI响应
    await startStreaming(conversationId, content, metadata);
  }, [conversationId, isStreaming, addUserMessage, startStreaming]);
  
  return {
    messages,
    isStreaming: isStreaming || isAnyStreaming,
    error,
    sendMessage,
    stopStreaming,
    clearError,
    clearMessages,
    reset
  };
}