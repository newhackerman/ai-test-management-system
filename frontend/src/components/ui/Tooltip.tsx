import * as React from 'react'

import { cn } from '@/lib/utils'

export interface TooltipProps {
  content?: React.ReactNode
  children: React.ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  delayDuration?: number
  className?: string
}

export function Tooltip({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 700,
  className
}: TooltipProps) {
  if (content === undefined) {
    return <div className="relative inline-block">{children}</div>
  }

  const [isVisible, setIsVisible] = React.useState(false)
  const [timeoutId, setTimeoutId] = React.useState<NodeJS.Timeout | null>(null)
  const tooltipRef = React.useRef<HTMLDivElement>(null)

  const showTooltip = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    const id = setTimeout(() => {
      setIsVisible(true)
    }, delayDuration)
    setTimeoutId(id)
  }

  const hideTooltip = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      setTimeoutId(null)
    }
    setIsVisible(false)
  }

  const getTooltipClasses = () => {
    const baseClasses = 'absolute z-50 overflow-hidden rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95'
    
    const sideClasses = {
      top: 'bottom-full mb-2',
      right: 'left-full ml-2',
      bottom: 'top-full mt-2',
      left: 'right-full mr-2'
    }

    const alignClasses = {
      start: side === 'top' || side === 'bottom' ? 'left-0' : 'top-0',
      center: side === 'top' || side === 'bottom' ? 'left-1/2 -translate-x-1/2' : 'top-1/2 -translate-y-1/2',
      end: side === 'top' || side === 'bottom' ? 'right-0' : 'bottom-0'
    }

    return cn(baseClasses, sideClasses[side], alignClasses[align], className)
  }

  return (
    <div 
      className="relative inline-block"
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}
      {isVisible && (
        <div
          ref={tooltipRef}
          className={getTooltipClasses()}
          role="tooltip"
        >
          {content}
        </div>
      )}
    </div>
  )
}

// Simple tooltip hook for programmatic usage
export function useTooltip() {
  const [isVisible, setIsVisible] = React.useState(false)
  const [position, setPosition] = React.useState({ x: 0, y: 0 })

  const showTooltip = (event: React.MouseEvent) => {
    setPosition({ x: event.clientX, y: event.clientY })
    setIsVisible(true)
  }

  const hideTooltip = () => {
    setIsVisible(false)
  }

  return {
    isVisible,
    position,
    showTooltip,
    hideTooltip
  }
}

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}

export function TooltipTrigger({ asChild, children }: { asChild?: boolean; children: React.ReactElement }) {
  if (asChild && React.isValidElement(children)) {
    return children
  }
  return <span>{children}</span>
}

export function TooltipContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md', className)}>
      {children}
    </div>
  )
}
