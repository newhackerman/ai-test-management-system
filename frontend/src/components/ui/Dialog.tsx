import React from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

const DialogContext = React.createContext<{
  open: boolean
  onOpenChange: (open: boolean) => void
} | null>(null)

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps {
  className?: string
  children: React.ReactNode
}

interface DialogHeaderProps {
  className?: string
  children: React.ReactNode
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

interface DialogDescriptionProps {
  children: React.ReactNode
}

interface DialogFooterProps {
  className?: string
  children: React.ReactNode
}

export const Dialog: React.FC<DialogProps> = ({ open, onOpenChange, children }) => {
  return (
    <DialogContext.Provider value={{ open, onOpenChange }}>
      {children}
    </DialogContext.Provider>
  )
}

export const DialogContent: React.FC<DialogContentProps> = ({ className = '', children }) => {
  const context = React.useContext(DialogContext)
  if (context && !context.open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div 
        className="fixed inset-0 bg-black/50"
        onClick={() => context?.onOpenChange(false)}
      />
      <div
        className={cn(
          'relative z-10 mx-4 max-h-[calc(100vh-2rem)] w-full max-w-md overflow-auto rounded-lg border bg-card p-4 text-card-foreground shadow-lg',
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}

export const DialogTrigger: React.FC<{ asChild?: boolean; children: React.ReactElement }> = ({ asChild, children }) => {
  const context = React.useContext(DialogContext)
  const onClick = () => context?.onOpenChange(true)

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, { onClick } as any)
  }

  return <button type="button" onClick={onClick}>{children}</button>
}

export const DialogHeader: React.FC<DialogHeaderProps> = ({ className = '', children }) => {
  return (
    <div className={cn('mb-3', className)}>
      {children}
    </div>
  )
}

export const DialogTitle: React.FC<DialogTitleProps> = ({ className = '', children, ...props }) => {
  return (
    <h2 className={`text-lg font-semibold text-foreground ${className}`} {...props}>
      {children}
    </h2>
  )
}

export const DialogDescription: React.FC<DialogDescriptionProps> = ({ children }) => {
  return (
    <p className="mt-1 text-sm text-muted-foreground">
      {children}
    </p>
  )
}

export const DialogFooter: React.FC<DialogFooterProps> = ({ className = '', children }) => {
  return (
    <div className={cn('mt-4 flex justify-end space-x-2', className)}>
      {children}
    </div>
  )
}
