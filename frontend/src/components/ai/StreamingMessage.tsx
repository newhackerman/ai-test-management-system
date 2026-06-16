import React, { useEffect, useState } from 'react';
import { AlertCircle, Bot, Loader2, User, Zap } from 'lucide-react';

import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import { StreamingMessage as StreamingMessageType } from '../../services/streaming-service';

interface StreamingMessageProps {
  message: StreamingMessageType;
  className?: string;
}

export function StreamingMessage({ message, className }: StreamingMessageProps) {
  const [showCursor, setShowCursor] = useState(false);
  const isUser = message.role === 'user';
  const isStreaming = Boolean(message.isStreaming && !message.isComplete);
  const isError = Boolean(message.isError);

  useEffect(() => {
    if (!isStreaming) {
      setShowCursor(false);
      return;
    }

    setShowCursor(true);
    const timer = window.setInterval(() => setShowCursor((prev) => !prev), 500);
    return () => window.clearInterval(timer);
  }, [isStreaming]);

  return (
    <div className={cn('mb-4 flex gap-3', isUser ? 'justify-end' : 'justify-start', className)}>
      {!isUser && (
        <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full', isError ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30')}>
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
          ) : isError ? (
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
          ) : (
            <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          )}
        </div>
      )}

      <div
        className={cn(
          'relative max-w-[75%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-blue-600 text-white'
            : isError
              ? 'border border-red-200 bg-red-50 text-red-800 dark:text-red-300 dark:bg-red-900/20 dark:border-red-800'
              : 'bg-gray-100 text-gray-900 dark:text-gray-100 dark:bg-gray-800',
        )}
      >
        {isStreaming && !isUser && (
          <div className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full bg-green-500">
            <Zap className="h-2.5 w-2.5 text-white" />
          </div>
        )}

        <div className="whitespace-pre-wrap break-words">
          {message.content}
          {isStreaming && showCursor && <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current align-middle" />}
        </div>

        {isError && message.error && (
          <div className="mt-2 rounded bg-red-100 p-2 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/30">
            <AlertCircle className="mr-1 inline h-4 w-4" />
            {message.error}
          </div>
        )}

        <div className={cn('mt-2 flex flex-wrap items-center gap-2 text-xs', isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400')}>
          <span>{new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
          {!isUser && message.metadata?.provider && <Badge variant="secondary">{message.metadata.provider}</Badge>}
          {!isUser && message.metadata?.model && <Badge variant="outline">{message.metadata.model}</Badge>}
          {!isUser && message.metadata?.tokens_used != null && <span>{message.metadata.tokens_used} tokens</span>}
        </div>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600">
          <User className="h-4 w-4 text-white" />
        </div>
      )}
    </div>
  );
}
