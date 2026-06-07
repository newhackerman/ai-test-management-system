import * as React from 'react'

import { cn } from '@/lib/utils'

export interface SwitchProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  description?: string
  onCheckedChange?: (checked: boolean) => void
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, description, onCheckedChange, onChange, ...props }, ref) => {
    const id = React.useId()
    const inputId = props.id || id

    return (
      <div className="flex items-center space-x-2">
        <div className="relative">
          <input
            type="checkbox"
            className="sr-only"
            ref={ref}
            id={inputId}
            onChange={(event) => {
              onChange?.(event)
              onCheckedChange?.(event.target.checked)
            }}
            {...props}
          />
          <div
            className={cn(
              'peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
              'bg-input peer-checked:bg-primary',
              className
            )}
            onClick={() => {
              const input = document.getElementById(inputId) as HTMLInputElement
              if (input) {
                input.click()
              }
            }}
          >
            <div
              className={cn(
                'pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform',
                'translate-x-0 peer-checked:translate-x-5'
              )}
            />
          </div>
        </div>
        {(label || description) && (
          <div className="grid gap-1.5 leading-none">
            {label && (
              <label
                htmlFor={inputId}
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-xs text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }
)
Switch.displayName = 'Switch'

export { Switch }
