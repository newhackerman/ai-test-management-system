// @ts-nocheck
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  BarChart3,
  Pause,
  Play,
  Send,
  Settings,
  Square,
} from 'lucide-react';

import { TypewriterText } from './TypewriterText';
import {
  AIConnectionProvider,
  ConnectionQualityIndicator,
  ConnectionStatsPanel,
  ConnectionStatusIndicator,
  useAIConnection,
} from './ConnectionStatusManager';
import './TypewriterText.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface StreamConfig {
  processingMode: 'real_time' | 'buffered' | 'optimized';
  typingSpeed: number;
  bufferSize: number;
  flushInterval: number;
}

interface StreamMetrics {
  totalChunks: number;
  totalBytes: number;
  processingTime: number;
  throughput: number;
  chunkRate: number;
  errorCount: number;
}

interface StreamSession {
  sessionId: string;
  status: 'pending' | 'streaming' | 'paused' | 'completed' | 'error' | 'cancelled';
  websocketUrl?: string;
  sseUrl?: string;
  createdAt: string;
}

const statusLabel: Record<StreamSession['status'], string> = {
  pending: '等待中',
  streaming: '生成中',
  paused: '已暂停',
  completed: '已完成',
  error: '异常',
  cancelled: '已取消',
};

const formatTime = (date: Date) =>
  date.toLocaleTimeString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  });

const normalizeSession = (data: any): StreamSession => ({
  sessionId: data?.sessionId || data?.session_id || data?.id || `local-${Date.now()}`,
  status: data?.status || 'pending',
  websocketUrl: data?.websocketUrl || data?.websocket_url,
  sseUrl: data?.sseUrl || data?.sse_url,
  createdAt: data?.createdAt || data?.created_at || new Date().toISOString(),
});

const EnhancedStreamingChatInner: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [currentSession, setCurrentSession] = useState<StreamSession | null>(null);
  const [streamMetrics, setStreamMetrics] = useState<StreamMetrics | null>(null);
  const [streamConfig, setStreamConfig] = useState<StreamConfig>({
    processingMode: 'optimized',
    typingSpeed: 50,
    bufferSize: 1024,
    flushInterval: 0.1,
  });
  const [showSettings, setShowSettings] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showConnectionStats, setShowConnectionStats] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const { isConnected, connect, disconnect, send: sendConnectionMessage, subscribe } = useAIConnection();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const createStreamSession = async (userMessage: string): Promise<StreamSession> => {
    const response = await fetch('/api/v1/streaming/stream/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: userMessage }],
        stream: true,
        processing_mode: streamConfig.processingMode,
        typing_speed: streamConfig.typingSpeed,
        buffer_size: streamConfig.bufferSize,
        flush_interval: streamConfig.flushInterval,
      }),
    });

    if (!response.ok) {
      throw new Error('创建流式会话失败');
    }

    return normalizeSession(await response.json());
  };

  const appendAssistantChunk = useCallback((content: string) => {
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage?.role === 'assistant' && lastMessage.isStreaming) {
        return [...prev.slice(0, -1), { ...lastMessage, content: lastMessage.content + content }];
      }

      return [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content,
          timestamp: new Date(),
          isStreaming: true,
        },
      ];
    });
  }, []);

  const finishStreamingMessage = useCallback(() => {
    setMessages((prev) =>
      prev.map((message, index) =>
        index === prev.length - 1 && message.isStreaming
          ? { ...message, isStreaming: false }
          : message,
      ),
    );
  }, []);

  const handleStreamMessage = useCallback(
    (message: any) => {
      if (!message) return;

      switch (message.type) {
        case 'chunk':
          appendAssistantChunk(message.content || message.payload?.content || '');
          break;
        case 'status':
          setCurrentSession((prev) => (prev ? { ...prev, status: message.status || prev.status } : prev));
          break;
        case 'complete':
          finishStreamingMessage();
          setCurrentSession((prev) => (prev ? { ...prev, status: 'completed' } : prev));
          break;
        case 'error':
          finishStreamingMessage();
          setCurrentSession((prev) => (prev ? { ...prev, status: 'error' } : prev));
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              role: 'assistant',
              content: `生成失败：${message.error || message.message || '服务暂时不可用'}`,
              timestamp: new Date(),
            },
          ]);
          break;
        default:
          break;
      }
    },
    [appendAssistantChunk, finishStreamingMessage],
  );

  useEffect(() => {
    const unsubscribers = ['chunk', 'status', 'error', 'complete'].map((eventType) =>
      subscribe(eventType, handleStreamMessage),
    );
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [handleStreamMessage, subscribe]);

  const connectWebSocket = useCallback(
    async (sessionId: string) => {
      if (!isConnected) {
        await connect();
      }

      sendConnectionMessage({
        type: 'subscribe',
        payload: { session_id: sessionId },
      });
    },
    [connect, isConnected, sendConnectionMessage],
  );

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content || isSending) return;

    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date(),
      },
    ]);
    setInputValue('');

    try {
      const session = await createStreamSession(content);
      setCurrentSession({ ...session, status: 'streaming' });
      await connectWebSocket(session.sessionId);

      const startResponse = await fetch(`/api/v1/streaming/stream/${session.sessionId}/start`, {
        method: 'POST',
      });

      if (!startResponse.ok) {
        throw new Error('启动流式生成失败');
      }
    } catch (error: any) {
      setCurrentSession(null);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: error?.message || '消息发送失败，请稍后重试。',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const updateSessionStatus = async (action: 'pause' | 'resume' | 'cancel') => {
    if (!currentSession) return;

    const method = action === 'cancel' ? 'DELETE' : 'POST';
    const path = action === 'cancel' ? '' : `/${action}`;

    try {
      const response = await fetch(`/api/v1/streaming/stream/${currentSession.sessionId}${path}`, { method });
      if (!response.ok) throw new Error('操作失败');

      if (action === 'cancel') {
        finishStreamingMessage();
        disconnect();
        setCurrentSession({ ...currentSession, status: 'cancelled' });
      } else {
        setCurrentSession({
          ...currentSession,
          status: action === 'pause' ? 'paused' : 'streaming',
        });
      }
    } catch (error) {
      console.error(`Stream ${action} failed:`, error);
    }
  };

  const updateStreamConfig = async (newConfig: Partial<StreamConfig>) => {
    const nextConfig = { ...streamConfig, ...newConfig };
    setStreamConfig(nextConfig);

    if (!currentSession) return;

    try {
      await fetch(`/api/v1/streaming/stream/${currentSession.sessionId}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          processing_mode: nextConfig.processingMode,
          typing_speed: nextConfig.typingSpeed,
          buffer_size: nextConfig.bufferSize,
          flush_interval: nextConfig.flushInterval,
        }),
      });
    } catch (error) {
      console.error('Update stream config failed:', error);
    }
  };

  const fetchStreamMetrics = useCallback(async () => {
    if (!currentSession) return;

    try {
      const response = await fetch(`/api/v1/streaming/stream/${currentSession.sessionId}/metrics`);
      const data = await response.json();
      setStreamMetrics(data?.metrics || data);
    } catch (error) {
      console.error('Fetch stream metrics failed:', error);
    }
  }, [currentSession]);

  useEffect(() => {
    if (currentSession?.status !== 'streaming') return;
    const timer = window.setInterval(fetchStreamMetrics, 1000);
    return () => window.clearInterval(timer);
  }, [currentSession?.status, fetchStreamMetrics]);

  useEffect(() => () => disconnect(), [disconnect]);

  const isStreaming = currentSession?.status === 'streaming';

  return (
    <div className="flex h-screen flex-col bg-gray-50 dark:bg-gray-800/50">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white p-4 dark:bg-gray-800 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">增强流式 AI 助手</h1>
          <ConnectionStatusIndicator />
          <ConnectionQualityIndicator />
          {currentSession && (
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 dark:text-blue-300 dark:bg-blue-900/20">
              会话状态：{statusLabel[currentSession.status] || currentSession.status}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {currentSession?.status === 'streaming' && (
            <button className="rounded-lg p-2 hover:bg-gray-100 dark:bg-gray-800" title="暂停" onClick={() => updateSessionStatus('pause')}>
              <Pause className="h-4 w-4" />
            </button>
          )}
          {currentSession?.status === 'paused' && (
            <button className="rounded-lg p-2 hover:bg-gray-100 dark:bg-gray-800" title="继续" onClick={() => updateSessionStatus('resume')}>
              <Play className="h-4 w-4" />
            </button>
          )}
          {currentSession && ['streaming', 'paused'].includes(currentSession.status) && (
            <button className="rounded-lg p-2 text-red-600 hover:bg-red-50 dark:text-red-400 dark:bg-red-900/20" title="取消" onClick={() => updateSessionStatus('cancel')}>
              <Square className="h-4 w-4" />
            </button>
          )}
          <button className="rounded-lg p-2 hover:bg-gray-100 dark:bg-gray-800" title="性能指标" onClick={() => setShowMetrics((value) => !value)}>
            <BarChart3 className="h-4 w-4" />
          </button>
          <button className="rounded-lg p-2 hover:bg-gray-100 dark:bg-gray-800" title="连接统计" onClick={() => setShowConnectionStats((value) => !value)}>
            <Activity className="h-4 w-4" />
          </button>
          <button className="rounded-lg p-2 hover:bg-gray-100 dark:bg-gray-800" title="设置" onClick={() => setShowSettings((value) => !value)}>
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>

      {showSettings && (
        <div className="border-b border-gray-200 bg-white p-4 dark:bg-gray-800 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium">流式处理设置</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label className="text-sm">
              <span className="mb-2 block font-medium text-gray-700 dark:text-gray-300">处理模式</span>
              <select
                value={streamConfig.processingMode}
                onChange={(event) => updateStreamConfig({ processingMode: event.target.value as StreamConfig['processingMode'] })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 dark:border-gray-600"
              >
                <option value="real_time">实时模式</option>
                <option value="buffered">缓冲模式</option>
                <option value="optimized">优化模式</option>
              </select>
            </label>
            <Slider label={`打字速度：${streamConfig.typingSpeed} 字符/秒`} min={10} max={200} value={streamConfig.typingSpeed} onChange={(value) => updateStreamConfig({ typingSpeed: value })} />
            <Slider label={`缓冲区大小：${streamConfig.bufferSize} 字符`} min={256} max={4096} step={256} value={streamConfig.bufferSize} onChange={(value) => updateStreamConfig({ bufferSize: value })} />
            <Slider label={`刷新间隔：${streamConfig.flushInterval}s`} min={0.05} max={1} step={0.05} value={streamConfig.flushInterval} onChange={(value) => updateStreamConfig({ flushInterval: value })} />
          </div>
        </div>
      )}

      {showMetrics && (
        <div className="border-b border-gray-200 bg-white p-4 dark:bg-gray-800 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium">性能指标</h3>
          {streamMetrics ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
              <Metric label="数据块数" value={streamMetrics.totalChunks} />
              <Metric label="总字节数" value={streamMetrics.totalBytes} />
              <Metric label="处理时间" value={`${Number(streamMetrics.processingTime || 0).toFixed(2)}s`} />
              <Metric label="吞吐量" value={`${Number(streamMetrics.throughput || 0).toFixed(0)} B/s`} />
              <Metric label="块速率" value={`${Number(streamMetrics.chunkRate || 0).toFixed(1)}/s`} />
              <Metric label="错误数" value={streamMetrics.errorCount} />
            </div>
          ) : (
            <div className="text-sm text-gray-500 dark:text-gray-400">暂无指标数据，开始生成后会自动刷新。</div>
          )}
        </div>
      )}

      {showConnectionStats && (
        <div className="border-b border-gray-200 bg-white p-4 dark:bg-gray-800 dark:border-gray-700">
          <ConnectionStatsPanel />
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500 dark:text-gray-400 dark:bg-gray-800 dark:border-gray-600">
            输入问题后开始流式对话。
          </div>
        )}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[72ch] rounded-lg px-4 py-3 ${message.role === 'user' ? 'bg-blue-600 text-white' : 'border border-gray-200 bg-white text-gray-900'}`}>
              <div className="whitespace-pre-wrap">
                {message.role === 'assistant' && message.isStreaming ? (
                  <TypewriterText
                    text={message.content}
                    speed={streamConfig.typingSpeed}
                    showCursor
                    paused={currentSession?.status === 'paused'}
                    className="typewriter-theme-chat"
                    preserveLineBreaks
                  />
                ) : (
                  message.content
                )}
              </div>
              {message.isStreaming && (
                <div className="mt-2 flex items-center text-xs text-gray-500 dark:text-gray-400">
                  <Activity className="mr-1 h-3 w-3 animate-pulse" />
                  正在生成...
                </div>
              )}
              <div className={`mt-2 text-xs ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 bg-white p-4 dark:bg-gray-800 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') handleSendMessage();
            }}
            placeholder="输入消息..."
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600"
            disabled={isStreaming || isSending}
          />
          <button
            type="button"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isStreaming || isSending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

const Slider: React.FC<{
  label: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
}> = ({ label, min, max, step = 1, value, onChange }) => (
  <label className="text-sm">
    <span className="mb-2 block font-medium text-gray-700 dark:text-gray-300">{label}</span>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(event) => onChange(Number(event.target.value))}
      className="w-full"
    />
  </label>
);

const Metric: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-md border border-gray-200 p-3 text-center dark:border-gray-700">
    <div className="text-xl font-semibold text-blue-600 dark:text-blue-400">{value}</div>
    <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
  </div>
);

const EnhancedStreamingChat: React.FC = () => (
  <AIConnectionProvider
    wsUrl="/api/v1/ai-assistant/ws"
    config={{
      autoReconnect: true,
      maxReconnectAttempts: 5,
      enableNotifications: true,
      heartbeatInterval: 30000,
      qualityCheckInterval: 5000,
    }}
  >
    <EnhancedStreamingChatInner />
  </AIConnectionProvider>
);

export default EnhancedStreamingChat;
