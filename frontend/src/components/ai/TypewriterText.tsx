/**
 * 打字机效果组件
 * 
 * 提供流畅的打字机文本显示效果，支持：
 * 1. 可配置的打字速度
 * 2. 暂停/恢复功能
 * 3. 完成回调
 * 4. 光标闪烁效果
 * 5. 支持Markdown和HTML内容
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';

interface TypewriterTextProps {
  /** 要显示的文本内容 */
  text: string;
  /** 打字速度（字符/秒），默认50 */
  speed?: number;
  /** 是否显示光标，默认true */
  showCursor?: boolean;
  /** 光标字符，默认'|' */
  cursor?: string;
  /** 光标闪烁间隔（毫秒），默认500 */
  cursorBlinkInterval?: number;
  /** 是否暂停打字，默认false */
  paused?: boolean;
  /** 是否立即显示全部文本，默认false */
  instant?: boolean;
  /** 打字完成回调 */
  onComplete?: () => void;
  /** 打字进度回调 */
  onProgress?: (progress: number) => void;
  /** 自定义样式类名 */
  className?: string;
  /** 是否保留换行符，默认true */
  preserveLineBreaks?: true;
  /** 是否支持HTML内容，默认false */
  dangerouslySetInnerHTML?: boolean;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 50,
  showCursor = true,
  cursor = '|',
  cursorBlinkInterval = 500,
  paused = false,
  instant = false,
  onComplete,
  onProgress,
  className = '',
  preserveLineBreaks = true,
  dangerouslySetInnerHTML = false
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [showCursorState, setShowCursorState] = useState(true);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const cursorIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastUpdateTimeRef = useRef<number>(Date.now());

  // 清理定时器
  const clearIntervals = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (cursorIntervalRef.current) {
      clearInterval(cursorIntervalRef.current);
      cursorIntervalRef.current = null;
    }
  }, []);

  // 启动光标闪烁
  const startCursorBlink = useCallback(() => {
    if (!showCursor) return;
    
    clearIntervals();
    cursorIntervalRef.current = setInterval(() => {
      setShowCursorState(prev => !prev);
    }, cursorBlinkInterval);
  }, [showCursor, cursorBlinkInterval, clearIntervals]);

  // 停止光标闪烁
  const stopCursorBlink = useCallback(() => {
    if (cursorIntervalRef.current) {
      clearInterval(cursorIntervalRef.current);
      cursorIntervalRef.current = null;
    }
    setShowCursorState(true);
  }, []);

  // 重置状态
  const reset = useCallback(() => {
    setDisplayedText('');
    setCurrentIndex(0);
    setIsComplete(false);
    setShowCursorState(true);
    clearIntervals();
    lastUpdateTimeRef.current = Date.now();
  }, [clearIntervals]);

  // 立即显示全部文本
  const showInstant = useCallback(() => {
    setDisplayedText(text);
    setCurrentIndex(text.length);
    setIsComplete(true);
    stopCursorBlink();
    onComplete?.();
    onProgress?.(100);
  }, [text, onComplete, onProgress, stopCursorBlink]);

  // 打字机效果主逻辑
  const startTypewriter = useCallback(() => {
    if (paused || isComplete || currentIndex >= text.length) {
      return;
    }

    const interval = 1000 / speed; // 计算间隔时间（毫秒）
    
    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const timeSinceLastUpdate = now - lastUpdateTimeRef.current;
      
      // 如果时间间隔足够，添加下一个字符
      if (timeSinceLastUpdate >= interval) {
        setCurrentIndex(prevIndex => {
          const newIndex = prevIndex + 1;
          const newDisplayedText = text.slice(0, newIndex);
          
          setDisplayedText(newDisplayedText);
          
          // 更新进度
          const progress = (newIndex / text.length) * 100;
          onProgress?.(progress);
          
          // 检查是否完成
          if (newIndex >= text.length) {
            setIsComplete(true);
            clearIntervals();
            startCursorBlink();
            onComplete?.();
          }
          
          lastUpdateTimeRef.current = now;
          return newIndex;
        });
      }
    }, Math.min(interval, 16)); // 最小16ms间隔，保证流畅性
  }, [text, speed, paused, isComplete, currentIndex, onComplete, onProgress, clearIntervals, startCursorBlink]);

  // 处理文本变化
  useEffect(() => {
    if (instant) {
      showInstant();
      return;
    }

    // 如果文本发生变化，重置状态
    if (text !== displayedText && currentIndex === 0) {
      reset();
    }

    // 如果文本增长（流式更新），继续打字
    if (text.length > displayedText.length && !isComplete) {
      startTypewriter();
    }

    return () => {
      clearIntervals();
    };
  }, [text, instant, showInstant, reset, startTypewriter, clearIntervals, displayedText, currentIndex, isComplete]);

  // 处理暂停/恢复
  useEffect(() => {
    if (paused) {
      clearIntervals();
      stopCursorBlink();
    } else if (!isComplete && currentIndex < text.length) {
      startTypewriter();
    }
  }, [paused, isComplete, currentIndex, text.length, startTypewriter, clearIntervals, stopCursorBlink]);

  // 处理速度变化
  useEffect(() => {
    if (!paused && !isComplete && currentIndex < text.length) {
      clearIntervals();
      startTypewriter();
    }
  }, [speed, paused, isComplete, currentIndex, text.length, clearIntervals, startTypewriter]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      clearIntervals();
    };
  }, [clearIntervals]);

  // 格式化显示文本
  const formatText = (text: string) => {
    if (!preserveLineBreaks) {
      return text;
    }
    
    // 将换行符转换为<br>标签
    return text.replace(/\n/g, '<br>');
  };

  // 渲染内容
  const renderContent = () => {
    const formattedText = formatText(displayedText);
    const cursorElement = showCursor && showCursorState ? cursor : '';
    
    if (dangerouslySetInnerHTML) {
      return (
        <span
          dangerouslySetInnerHTML={{
            __html: formattedText + cursorElement
          }}
        />
      );
    }
    
    if (preserveLineBreaks) {
      return (
        <span
          dangerouslySetInnerHTML={{
            __html: formattedText + cursorElement
          }}
        />
      );
    }
    
    return (
      <span>
        {displayedText}
        {showCursor && showCursorState && cursor}
      </span>
    );
  };

  return (
    <span className={`typewriter-text ${className}`}>
      {renderContent()}
    </span>
  );
};

// 高阶组件：为现有组件添加打字机效果
export const withTypewriter = <P extends object>(
  Component: React.ComponentType<P>,
  defaultProps?: Partial<TypewriterTextProps>
) => {
  return React.forwardRef<any, P & { typewriterProps?: TypewriterTextProps }>((props, ref) => {
    const { typewriterProps, ...componentProps } = props;
    
    return (
      <Component
        {...(componentProps as P)}
        ref={ref}
        typewriterText={(text: string) => (
          <TypewriterText
            text={text}
            {...defaultProps}
            {...typewriterProps}
          />
        )}
      />
    );
  });
};

// Hook：使用打字机效果
export const useTypewriter = (
  text: string,
  options?: Partial<TypewriterTextProps>
) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);

  const typewriterRef = useRef<{
    reset: () => void;
    pause: () => void;
    resume: () => void;
    complete: () => void;
  }>();

  const controls = {
    reset: () => typewriterRef.current?.reset(),
    pause: () => typewriterRef.current?.pause(),
    resume: () => typewriterRef.current?.resume(),
    complete: () => typewriterRef.current?.complete(),
  };

  const TypewriterComponent = (
    <TypewriterText
      text={text}
      onProgress={setProgress}
      onComplete={() => setIsComplete(true)}
      {...options}
    />
  );

  return {
    displayedText,
    isComplete,
    progress,
    controls,
    TypewriterComponent
  };
};

export default TypewriterText;