/**
 * 打字指示器组件
 * 显示AI或其他用户正在输入的状态
 */
import React, { useEffect, useState } from 'react';
import { Bot, User, Users } from 'lucide-react';
import { cn } from '../../lib/utils';

interface TypingIndicatorProps {
  isVisible?: boolean;
  typingUsers?: Array<{
    id: number;
    name: string;
    avatar?: string;
    type: 'user' | 'ai';
  }>;
  className?: string;
}

export function TypingIndicator({ 
  isVisible = false, 
  typingUsers = [],
  className 
}: TypingIndicatorProps) {
  const [dots, setDots] = useState('');

  // 动画效果：循环显示1-3个点
  useEffect(() => {
    if (!isVisible) {
      setDots('');
      return;
    }

    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '.';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible || typingUsers.length === 0) {
    return null;
  }

  // 渲染单个用户的打字状态
  const renderSingleUser = (user: typeof typingUsers[0]) => {
    const isAI = user.type === 'ai';
    
    return (
      <div className="flex gap-3 mb-4">
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
          isAI ? "bg-blue-100" : "bg-gray-100"
        )}>
          {isAI ? (
            <Bot className="w-4 h-4 text-blue-600" />
          ) : (
            <User className="w-4 h-4 text-gray-600" />
          )}
        </div>
        
        <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-[200px]">
          <div className="flex items-center gap-2">
            {/* 跳动的点动画 */}
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-sm text-gray-600">
              {isAI ? 'AI正在思考' : `${user.name}正在输入`}{dots}
            </span>
          </div>
        </div>
      </div>
    );
  };

  // 渲染多个用户的打字状态
  const renderMultipleUsers = () => {
    const aiUsers = typingUsers.filter(u => u.type === 'ai');
    const humanUsers = typingUsers.filter(u => u.type === 'user');
    
    return (
      <div className="flex gap-3 mb-4">
        <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
          <Users className="w-4 h-4 text-gray-600" />
        </div>
        
        <div className="bg-gray-100 rounded-lg px-4 py-2">
          <div className="flex items-center gap-2">
            {/* 跳动的点动画 */}
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                   style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-sm text-gray-600">
              {aiUsers.length > 0 && humanUsers.length > 0 
                ? `AI和${humanUsers.length}个用户正在输入${dots}`
                : aiUsers.length > 0
                  ? `AI正在思考${dots}`
                  : `${humanUsers.length}个用户正在输入${dots}`
              }
            </span>
          </div>
          
          {/* 显示具体的用户名 */}
          {humanUsers.length > 0 && humanUsers.length <= 3 && (
            <div className="text-xs text-gray-500 mt-1">
              {humanUsers.map(u => u.name).join(', ')}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={cn('animate-fade-in', className)}>
      {typingUsers.length === 1 
        ? renderSingleUser(typingUsers[0])
        : renderMultipleUsers()
      }
    </div>
  );
}

/**
 * 简化版打字指示器 - 仅显示AI正在输入
 */
export function SimpleTypingIndicator({ 
  isVisible = false, 
  message = 'AI正在思考',
  className 
}: {
  isVisible?: boolean;
  message?: string;
  className?: string;
}) {
  if (!isVisible) return null;

  return (
    <div className={cn('flex gap-3 mb-4 animate-fade-in', className)}>
      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-blue-600" />
      </div>
      
      <div className="bg-gray-100 rounded-lg px-4 py-2">
        <div className="flex items-center gap-2">
          {/* 跳动的点动画 */}
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                 style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                 style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                 style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm text-gray-600">{message}...</span>
        </div>
      </div>
    </div>
  );
}