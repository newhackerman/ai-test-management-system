import * as React from 'react'
import { ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

export interface AccordionProps {
  type?: 'single' | 'multiple'
  value?: string | string[]
  onValueChange?: (value: string | string[]) => void
  children: React.ReactNode
  className?: string
  collapsible?: boolean
}

const AccordionContext = React.createContext<{
  type: 'single' | 'multiple'
  value?: string | string[]
  onValueChange?: (value: string | string[]) => void
  collapsible?: boolean
}>({
  type: 'single'
})

export function Accordion({ 
  type = 'single', 
  value, 
  onValueChange, 
  children, 
  className,
  collapsible = false
}: AccordionProps) {
  return (
    <AccordionContext.Provider value={{ type, value, onValueChange, collapsible }}>
      <div className={cn('w-full', className)}>
        {children}
      </div>
    </AccordionContext.Provider>
  )
}

export interface AccordionItemProps
  extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

export function AccordionItem({ 
  className, 
  value: itemValue, 
  ...props 
}: AccordionItemProps) {
  return (
    <div
      className={cn('border-b', className)}
      {...props}
    />
  )
}

export interface AccordionTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

export function AccordionTrigger({ 
  className, 
  value: triggerValue,
  children,
  ...props 
}: AccordionTriggerProps) {
  const { type, value, onValueChange, collapsible } = React.useContext(AccordionContext)
  
  const isOpen = type === 'single' 
    ? value === triggerValue
    : Array.isArray(value) && value.includes(triggerValue)

  const handleClick = () => {
    if (!onValueChange) return

    if (type === 'single') {
      const newValue = isOpen && collapsible ? '' : triggerValue
      onValueChange(newValue)
    } else {
      const currentValue = Array.isArray(value) ? value : []
      const newValue = isOpen
        ? currentValue.filter(v => v !== triggerValue)
        : [...currentValue, triggerValue]
      onValueChange(newValue)
    }
  }

  return (
    <button
      className={cn(
        'flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline [&[data-state=open]>svg]:rotate-180',
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {children}
      <ChevronDown className={cn(
        'h-4 w-4 shrink-0 transition-transform duration-200',
        isOpen && 'rotate-180'
      )} />
    </button>
  )
}

export interface AccordionContentProps
  extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

export function AccordionContent({ 
  className, 
  value: contentValue,
  children,
  ...props 
}: AccordionContentProps) {
  const { type, value } = React.useContext(AccordionContext)
  
  const isOpen = type === 'single' 
    ? value === contentValue
    : Array.isArray(value) && value.includes(contentValue)

  if (!isOpen) {
    return null
  }

  return (
    <div
      className={cn(
        'overflow-hidden text-sm transition-all animate-in slide-in-from-top-1',
        className
      )}
      {...props}
    >
      <div className="pb-4 pt-0">
        {children}
      </div>
    </div>
  )
}