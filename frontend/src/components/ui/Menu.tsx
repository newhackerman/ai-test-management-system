import * as React from 'react'
import { Check, ChevronRight } from 'lucide-react'

import { cn } from '@/lib/utils'

export interface MenuProps {
  children: React.ReactNode
  className?: string
}

export function Menu({ children, className }: MenuProps) {
  return (
    <div className={cn('min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md', className)}>
      {children}
    </div>
  )
}

export interface MenuItemProps
  extends React.HTMLAttributes<HTMLDivElement> {
  disabled?: boolean
  checked?: boolean
  icon?: React.ReactNode
  shortcut?: string
}

export function MenuItem({ 
  className, 
  disabled = false, 
  checked = false,
  icon,
  shortcut,
  children,
  ...props 
}: MenuItemProps) {
  return (
    <div
      className={cn(
        'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors',
        disabled 
          ? 'pointer-events-none opacity-50' 
          : 'hover:bg-accent hover:text-accent-foreground cursor-pointer',
        className
      )}
      {...props}
    >
      {checked && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <Check className="h-4 w-4" />
        </span>
      )}
      {icon && (
        <span className="mr-2 h-4 w-4">
          {icon}
        </span>
      )}
      <span className={cn(checked && 'pl-6')}>{children}</span>
      {shortcut && (
        <span className="ml-auto text-xs tracking-widest opacity-60">
          {shortcut}
        </span>
      )}
    </div>
  )
}

export interface MenuSeparatorProps
  extends React.HTMLAttributes<HTMLDivElement> {}

export function MenuSeparator({ className, ...props }: MenuSeparatorProps) {
  return (
    <div
      className={cn('-mx-1 my-1 h-px bg-muted', className)}
      {...props}
    />
  )
}

export interface MenuLabelProps
  extends React.HTMLAttributes<HTMLDivElement> {}

export function MenuLabel({ className, ...props }: MenuLabelProps) {
  return (
    <div
      className={cn('px-2 py-1.5 text-sm font-semibold', className)}
      {...props}
    />
  )
}

export interface SubMenuProps {
  trigger: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function SubMenu({ trigger, children, className }: SubMenuProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const timeoutRef = React.useRef<NodeJS.Timeout>()

  const handleMouseEnter = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setIsOpen(true)
  }

  const handleMouseLeave = () => {
    timeoutRef.current = setTimeout(() => {
      setIsOpen(false)
    }, 100)
  }

  return (
    <div 
      className="relative"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground">
        {trigger}
        <ChevronRight className="ml-auto h-4 w-4" />
      </div>
      {isOpen && (
        <div className="absolute left-full top-0 ml-1">
          <Menu className={className}>
            {children}
          </Menu>
        </div>
      )}
    </div>
  )
}