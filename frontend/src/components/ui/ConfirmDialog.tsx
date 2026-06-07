import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from './Button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './Dialog'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'destructive'
  onConfirm: () => void
  onCancel: () => void
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  description,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'default',
  onConfirm,
  onCancel,
}) => {
  if (!open) return null

  return (
    <Dialog open={open} onOpenChange={onCancel}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            {variant === 'destructive' && <AlertTriangle className="h-5 w-5 text-red-600" />}
            <span>{title}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="py-4">
          <p className="text-gray-600">{description}</p>
        </div>

        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>
            {cancelText}
          </Button>
          <Button variant={variant} onClick={onConfirm}>
            {confirmText}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default ConfirmDialog
