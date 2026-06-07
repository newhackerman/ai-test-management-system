// @ts-nocheck
/**
 * 娴佸紡鑱婂ぉ缁勪欢
 * 
 * 婕旂ずAI鍔╂墜鐨勬祦寮忓搷搴斿姛鑳斤紝鍖呮嫭锛?
 * 1. WebSocket瀹炴椂閫氫俊
 * 2. Server-Sent Events (SSE)
 * 3. 鎵撳瓧鏈烘晥鏋?
 * 4. 娴佺姸鎬佺鐞?
 * 5. 杩炴帴鐘舵€佺鐞?
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Square, Loader2, Settings } from 'lucide-react';
import { TypewriterText } from './TypewriterText';
import { 
  AIConnectionProvider, 
  useAIConnection, 
  ConnectionStatusIndicator,
  ConnectionQualityIndicator 
} from './ConnectionStatusManager';
import './TypewriterText.css';

interface StreamMessage {
  type: 'chunk' | 'status' | 'error' | 'complete';
  session_id: string;
  data: any;
  timestamp: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  isComplete?: boolean;
}

interface StreamingChatProps {
  apiBaseUrl?: string;
  useWebSocket?: boolean; // true for WebSocket, false for SSE
  typewriterSpeed?: number; // 鎵撳瓧鏈洪€熷害锛岄粯璁?0瀛楃/绉?
  enableTypewriter?: boolean; // 鏄惁鍚敤鎵撳瓧鏈烘晥鏋滐紝榛樿true
}

// 鍐呴儴鑱婂ぉ缁勪欢
const StreamingChatInner: React.FC<StreamingChatProps> = ({
  apiBaseUrl = '/api/v1/streaming',
  useWebSocket = true,
  typewriterSpeed = 50,
  enableTypewriter = true
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [showConnectionSettings, setShowConnectionSettings] = useState(false);
  const [sseConnectionStatus, setSseConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');
  
  // 浣跨敤AI杩炴帴绠＄悊鍣?
  const { 
    isConnected, 
    isConnecting, 
    connectionState,
    connect, 
    disconnect, 
    send: sendMessage, 
    subscribe 
  } = useAIConnection();
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentMessageRef = useRef<string>('');

  // 婊氬姩鍒板簳閮?
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 澶勭悊娴佹秷鎭?
  const handleStreamMessage = useCallback((message: StreamMessage) => {
    console.log('Received stream message:', message);

    switch (message.type) {
      case 'chunk':
        const chunkContent = message.data.content || '';
        currentMessageRef.current += chunkContent;
        
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          
          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
            lastMessage.content = currentMessageRef.current;
          } else {
            newMessages.push({
              id: `msg-${Date.now()}`,
              role: 'assistant',
              content: currentMessageRef.current,
              timestamp: new Date().toISOString(),
              isStreaming: true,
              isComplete: false
            });
          }
          
          return newMessages;
        });
        break;

      case 'status':
        if (message.data.status === 'completed') {
          setIsStreaming(false);
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage && lastMessage.role === 'assistant') {
              lastMessage.isStreaming = false;
              lastMessage.isComplete = true;
            }
            return newMessages;
          });
          currentMessageRef.current = '';
        }
        break;

      case 'error':
        setIsStreaming(false);
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `閿欒: ${message.data.error}`,
          timestamp: new Date().toISOString(),
          isStreaming: false,
          isComplete: true
        }]);
        currentMessageRef.current = '';
        break;

      case 'complete':
        setIsStreaming(false);
        currentMessageRef.current = '';
        break;
    }
  }, []);

  // 璁㈤槄娴佹秷鎭?
  useEffect(() => {
    const unsubscribeChunk = subscribe('chunk', handleStreamMessage);
    const unsubscribeStatus = subscribe('status', handleStreamMessage);
    const unsubscribeError = subscribe('error', handleStreamMessage);
    const unsubscribeComplete = subscribe('complete', handleStreamMessage);
    
    return () => {
      unsubscribeChunk();
      unsubscribeStatus();
      unsubscribeError();
      unsubscribeComplete();
    };
  }, [subscribe, handleStreamMessage]);

  // 杩炴帴WebSocket (浣跨敤杩炴帴绠＄悊鍣?
  const connectWebSocket = useCallback(async (sessionId: string) => {
    try {
      if (!isConnected) {
        await connect();
      }
      
      // 璁㈤槄娴佷細璇?
      sendMessage({
        type: 'subscribe',
        payload: { session_id: sessionId }
      });
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      throw error;
    }
  }, [isConnected, connect, sendMessage]);

  // SSE杩炴帴
  const connectSSE = useCallback((sessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setSseConnectionStatus('connecting');
    const sseUrl = `http://localhost:8000${apiBaseUrl}/sse/${sessionId}`;
    
    try {
      eventSourceRef.current = new EventSource(sseUrl);

      eventSourceRef.current.onopen = () => {
        console.log('SSE connected');
        setSseConnectionStatus('connected');
      };

      eventSourceRef.current.onmessage = (event) => {
        try {
          const message: StreamMessage = JSON.parse(event.data);
          handleStreamMessage(message);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      eventSourceRef.current.onerror = (error) => {
        console.error('SSE error:', error);
        setSseConnectionStatus('disconnected');
      };
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      setSseConnectionStatus('disconnected');
    }
  }, [apiBaseUrl, handleStreamMessage]);

  // 鍙戦€佹秷鎭?
  const sendChatMessage = async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);
    currentMessageRef.current = '';

    try {
      // 鍒涘缓娴佷細璇?
      const response = await fetch(`http://localhost:8000${apiBaseUrl}/stream/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            { role: 'user', content: userMessage.content }
          ],
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const sessionData = await response.json();
      const sessionId = sessionData.session_id;
      setCurrentSessionId(sessionId);

      // 寤虹珛杩炴帴
      if (useWebSocket) {
        await connectWebSocket(sessionId);
      } else {
        connectSSE(sessionId);
      }

      // 鍚姩娴佸鐞?
      await fetch(`http://localhost:8000${apiBaseUrl}/stream/${sessionId}/start`, {
        method: 'POST'
      });

    } catch (error) {
      console.error('Failed to send message:', error);
      setIsStreaming(false);
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `发送消息失败: ${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toISOString(),
        isStreaming: false,
        isComplete: true
      }]);
    }
  };

  // 鍋滄娴佸紡鍝嶅簲
  const stopStreaming = async () => {
    if (!currentSessionId) return;

    try {
      await fetch(`http://localhost:8000${apiBaseUrl}/stream/${currentSessionId}`, {
        method: 'DELETE'
      });
      
      setIsStreaming(false);
      
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    } catch (error) {
      console.error('Failed to stop streaming:', error);
    }
  };

  // 娓呯悊杩炴帴
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // 澶勭悊閿洏浜嬩欢
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      {/* 澶撮儴 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <h2 className="text-lg font-semibold text-gray-800">AI鍔╂墜娴佸紡瀵硅瘽</h2>
          <span className="text-sm text-gray-500">
            ({useWebSocket ? 'WebSocket' : 'SSE'})
          </span>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* 杩炴帴鐘舵€佹寚绀哄櫒 */}
          <ConnectionStatusIndicator />
          
          {/* 杩炴帴璐ㄩ噺鎸囩ず鍣?*/}
          <ConnectionQualityIndicator />
          
          {/* 璁剧疆鎸夐挳 */}
          <button
            onClick={() => setShowConnectionSettings(!showConnectionSettings)}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
            title="杩炴帴璁剧疆"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 杩炴帴璁剧疆闈㈡澘 */}
      {showConnectionSettings && (
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">杩炴帴璁剧疆</h3>
            <span className="text-xs text-gray-500">
              状态: {useWebSocket ? connectionState : sseConnectionStatus}
            </span>
          </div>
          <div className="text-xs text-gray-600">
            杩炴帴妯″紡: {useWebSocket ? 'WebSocket' : 'Server-Sent Events'}
          </div>
          {!isConnected && (
            <button
              onClick={connect}
              disabled={isConnecting}
              className="mt-2 px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {isConnecting ? '杩炴帴涓?..' : '鎵嬪姩杩炴帴'}
            </button>
          )}
        </div>
      )}

      {/* 娑堟伅鍒楄〃 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <p>寮€濮嬩笌AI鍔╂墜瀵硅瘽鍚э紒</p>
            <p className="text-sm mt-2">支持实时流式响应，体验更流畅的对话</p>
          </div>
        )}
        
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <div className="whitespace-pre-wrap">
                {message.role === 'assistant' && enableTypewriter && message.isStreaming ? (
                  <TypewriterText
                    text={message.content}
                    speed={typewriterSpeed}
                    showCursor={message.isStreaming}
                    className="typewriter-theme-chat"
                    preserveLineBreaks={true}
                  />
                ) : (
                  message.content
                )}
              </div>
              
              {message.isStreaming && (
                <div className="flex items-center mt-2 text-xs opacity-70">
                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                  姝ｅ湪杈撳叆...
                </div>
              )}
              
              <div className="text-xs opacity-70 mt-1">
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 杈撳叆鍖哄煙 */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="杈撳叆鎮ㄧ殑闂..."
            className="flex-1 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={2}
            disabled={isStreaming}
          />
          
          {isStreaming ? (
            <button
              onClick={stopStreaming}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Square className="w-4 h-4" />
              <span>鍋滄</span>
            </button>
          ) : (
            <button
              onClick={sendChatMessage}
              disabled={!inputValue.trim() || !isConnected}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="w-4 h-4" />
              <span>发送</span>
            </button>
          )}
        </div>
        
        <div className="mt-2 text-xs text-gray-500">
          鎸?Enter 鍙戦€侊紝Shift + Enter 鎹㈣
        </div>
      </div>
    </div>
  );
};

// 涓荤粍浠讹紝鍖呰浜嗚繛鎺ョ鐞嗗櫒
export const StreamingChat: React.FC<StreamingChatProps> = (props) => {
  return (
    <AIConnectionProvider 
      wsUrl="/api/v1/ai-assistant/ws"
      config={{
        autoReconnect: true,
        maxReconnectAttempts: 5,
        enableNotifications: true
      }}
    >
      <StreamingChatInner {...props} />
    </AIConnectionProvider>
  );
};
