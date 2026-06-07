import * as React from 'react'

import { cn } from '@/lib/utils'

export interface RadioProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  description?: string
}

const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ className, label, description, ...props }, ref) => {
    const id = React.useId()
    const inputId = props.id || id

    return (
      <div className="flex items-start space-x-2">
        <div className="relative">
          <input
            type="radio"
            className="sr-only"
            ref={ref}
            id={inputId}
            {...props}
          />
          <div
            className={cn(
              'peer h-4 w-4 shrink-0 rounded-full border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
              'flex items-center justify-center',
              'transition-colors duration-200',
              'cursor-pointer',
              className
            )}
            onClick={() => {
              const input = document.getElementById(inputId) as HTMLInputElement
              if (input) {
                input.click()
              }
            }}
          >
            <div className="h-2 w-2 rounded-full bg-primary opacity-0 peer-checked:opacity-100 transition-opacity" />
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
Radio.displayName = 'Radio'

export { Radio }

// Radio Group Component
export interface RadioGroupProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  className?: string
  name?: string
}

export function RadioGroup({ 
  value, 
  onValueChange, 
  children, 
  className,
  name 
}: RadioGroupProps) {
  return (
    <div className={cn('grid gap-2', className)}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child) && child.type === Radio) {
          return React.cloneElement(child, {
            ...child.props,
            name: name || 'radio-group',
            checked: child.props.value === value,
            onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
              if (e.target.checked && onValueChange) {
                onValueChange(child.props.value)
              }
              child.props.onChange?.(e)
            }
          })
        }
        return child
      })}
    </div>
  )
}