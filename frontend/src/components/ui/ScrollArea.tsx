import React from 'react'
import { cn } from '@/lib/utils'

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  orientation?: 'vertical' | 'horizontal' | 'both'
  className?: string
}

export function ScrollArea({ 
  children, 
  orientation = 'vertical', 
  className, 
  ...props 
}: ScrollAreaProps) {
  const scrollClasses = {
    vertical: 'overflow-y-auto overflow-x-hidden',
    horizontal: 'overflow-x-auto overflow-y-hidden',
    both: 'overflow-auto'
  }

  return (
    <div
      className={cn(
        'custom-scrollbar',
        scrollClasses[orientation],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

interface ScrollAreaViewportProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  className?: string
}

export function ScrollAreaViewport({ 
  children, 
  className, 
  ...props 
}: ScrollAreaViewportProps) {
  return (
    <div
      className={cn('min-h-0 min-w-0', className)}
      {...props}
    >
      {children}
    </div>
  )
}

// 水平滚动容器
export function HorizontalScrollArea({ 
  children, 
  className, 
  ...props 
}: ScrollAreaProps) {
  return (
    <ScrollArea 
      orientation="horizontal" 
      className={cn('w-full', className)}
      {...props}
    >
      <div className="flex space-x-4 pb-2">
        {children}
      </div>
    </ScrollArea>
  )
}

// 垂直滚动容器
export function VerticalScrollArea({ 
  children, 
  className, 
  ...props 
}: ScrollAreaProps) {
  return (
    <ScrollArea 
      orientation="vertical" 
      className={cn('h-full', className)}
      {...props}
    >
      {children}
    </ScrollArea>
  )
}

// 表格滚动容器
export function TableScrollArea({ 
  children, 
  className, 
  ...props 
}: ScrollAreaProps) {
  return (
    <ScrollArea 
      orientation="both" 
      className={cn('w-full border rounded-md', className)}
      {...props}
    >
      <div className="min-w-full">
        {children}
      </div>
    </ScrollArea>
  )
}