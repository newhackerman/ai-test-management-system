import React from 'react'
import { X } from 'lucide-react'

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
  children: React.ReactNode
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

interface DialogDescriptionProps {
  children: React.ReactNode
}

interface DialogFooterProps {
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
        className="fixed inset-0 bg-black bg-opacity-50"
        onClick={() => context?.onOpenChange(false)}
      />
      <div className={`relative z-10 bg-white rounded-lg shadow-lg p-6 w-full max-w-md mx-4 ${className}`}>
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

export const DialogHeader: React.FC<DialogHeaderProps> = ({ children }) => {
  return (
    <div className="mb-4">
      {children}
    </div>
  )
}

export const DialogTitle: React.FC<DialogTitleProps> = ({ className = '', children, ...props }) => {
  return (
    <h2 className={`text-lg font-semibold text-gray-900 ${className}`} {...props}>
      {children}
    </h2>
  )
}

export const DialogDescription: React.FC<DialogDescriptionProps> = ({ children }) => {
  return (
    <p className="text-sm text-gray-600 mt-2">
      {children}
    </p>
  )
}

export const DialogFooter: React.FC<DialogFooterProps> = ({ children }) => {
  return (
    <div className="flex justify-end space-x-2 mt-6">
      {children}
    </div>
  )
}
