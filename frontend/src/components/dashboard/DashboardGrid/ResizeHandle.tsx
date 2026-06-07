import React, { useState, useCallback, useRef } from 'react';
import { Move } from 'lucide-react';

interface ResizeHandleProps {
  onResize: (newSize: { w: number; h: number }) => void;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
  currentSize: { w: number; h: number };
  minSize: { w: number; h: number };
  maxSize: { w: number; h: number };
  colWidth?: number;
  rowHeight?: number;
}

const ResizeHandle: React.FC<ResizeHandleProps> = ({
  onResize,
  onResizeStart,
  onResizeEnd,
  currentSize,
  minSize,
  maxSize,
  colWidth = 100,
  rowHeight = 60
}) => {
  const [isResizing, setIsResizing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [startSize, setStartSize] = useState({ w: 0, h: 0 });
  const handleRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const initialPos = { x: e.clientX, y: e.clientY };
    const initialSize = { w: currentSize.w, h: currentSize.h };

    setIsResizing(true);
    setStartPos(initialPos);
    setStartSize(initialSize);
    
    onResizeStart?.();

    // Add global mouse event listeners
    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - initialPos.x;
      const deltaY = e.clientY - initialPos.y;

      // Calculate new size based on mouse movement
      const newW = Math.max(
        minSize.w,
        Math.min(
          maxSize.w,
          initialSize.w + Math.round(deltaX / (colWidth + 16)) // 16 is margin
        )
      );

      const newH = Math.max(
        minSize.h,
        Math.min(
          maxSize.h,
          initialSize.h + Math.round(deltaY / (rowHeight + 16)) // 16 is margin
        )
      );

      if (newW !== currentSize.w || newH !== currentSize.h) {
        onResize({ w: newW, h: newH });
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      onResizeEnd?.();
      
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [
    currentSize,
    minSize,
    maxSize,
    colWidth,
    rowHeight,
    onResize,
    onResizeStart,
    onResizeEnd
  ]);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const touch = e.touches[0];
    const initialPos = { x: touch.clientX, y: touch.clientY };
    const initialSize = { w: currentSize.w, h: currentSize.h };

    setIsResizing(true);
    setStartPos(initialPos);
    setStartSize(initialSize);
    
    onResizeStart?.();

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 0) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - initialPos.x;
      const deltaY = touch.clientY - initialPos.y;

      const newW = Math.max(
        minSize.w,
        Math.min(
          maxSize.w,
          initialSize.w + Math.round(deltaX / (colWidth + 16))
        )
      );

      const newH = Math.max(
        minSize.h,
        Math.min(
          maxSize.h,
          initialSize.h + Math.round(deltaY / (rowHeight + 16))
        )
      );

      if (newW !== currentSize.w || newH !== currentSize.h) {
        onResize({ w: newW, h: newH });
      }
    };

    const handleTouchEnd = () => {
      setIsResizing(false);
      onResizeEnd?.();
      
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };

    document.addEventListener('touchmove', handleTouchMove);
    document.addEventListener('touchend', handleTouchEnd);
  }, [
    currentSize,
    minSize,
    maxSize,
    colWidth,
    rowHeight,
    onResize,
    onResizeStart,
    onResizeEnd
  ]);

  return (
    <div
      ref={handleRef}
      className={`absolute bottom-0 right-0 w-4 h-4 cursor-se-resize group ${
        isResizing ? 'bg-blue-500' : 'bg-gray-400 hover:bg-gray-600'
      } transition-colors duration-200`}
      style={{
        clipPath: 'polygon(100% 0%, 0% 100%, 100% 100%)'
      }}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      title="拖拽调整大小"
    >
      {/* Resize indicator */}
      <div className="absolute bottom-0 right-0 p-0.5">
        <Move className="h-2 w-2 text-white opacity-70 group-hover:opacity-100" />
      </div>
      
      {/* Visual feedback during resize */}
      {isResizing && (
        <div className="absolute -top-8 -right-2 bg-black text-white text-xs px-2 py-1 rounded shadow-lg pointer-events-none">
          {currentSize.w} × {currentSize.h}
        </div>
      )}
    </div>
  );
};

export default ResizeHandle;