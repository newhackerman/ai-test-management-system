import React, { createContext, useContext, useState } from 'react'
import { X } from 'lucide-react'
import { Button } from './Button'

interface SheetContextType {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const SheetContext = createContext<SheetContextType | undefined>(undefined)

const useSheet = () => {
  const context = useContext(SheetContext)
  if (!context) {
    throw new Error('Sheet components must be used within a Sheet')
  }
  return context
}

interface SheetProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

export const Sheet: React.FC<SheetProps> = ({ 
  open: controlledOpen, 
  onOpenChange, 
  children 
}) => {
  const [internalOpen, setInternalOpen] = useState(false)
  
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = onOpenChange || setInternalOpen

  return (
    <SheetContext.Provider value={{ open, onOpenChange: setOpen }}>
      {children}
    </SheetContext.Provider>
  )
}

interface SheetTriggerProps {
  asChild?: boolean
  children: React.ReactNode
}

export const SheetTrigger: React.FC<SheetTriggerProps> = ({ 
  asChild, 
  children 
}) => {
  const { onOpenChange } = useSheet()

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...children.props,
      onClick: (e: React.MouseEvent) => {
        children.props.onClick?.(e)
        onOpenChange(true)
      }
    })
  }

  return (
    <button onClick={() => onOpenChange(true)}>
      {children}
    </button>
  )
}

interface SheetContentProps {
  className?: string
  children: React.ReactNode
}

export const SheetContent: React.FC<SheetContentProps> = ({ 
  className = '', 
  children 
}) => {
  const { open, onOpenChange } = useSheet()

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={() => onOpenChange(false)}
      />
      
      {/* Sheet */}
      <div className={`fixed right-0 top-0 h-full bg-background border-l shadow-lg z-50 ${className}`}>
        <div className="flex items-center justify-between p-4 border-b">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="h-8 w-8 p-0"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        {children}
      </div>
    </>
  )
}

interface SheetHeaderProps {
  children: React.ReactNode
}

export const SheetHeader: React.FC<SheetHeaderProps> = ({ children }) => {
  return (
    <div className="px-4 py-2 border-b">
      {children}
    </div>
  )
}

interface SheetTitleProps {
  children: React.ReactNode
}

export const SheetTitle: React.FC<SheetTitleProps> = ({ children }) => {
  return (
    <h2 className="text-lg font-semibold">
      {children}
    </h2>
  )
}