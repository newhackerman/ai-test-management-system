import React from 'react'
import { Check, Minus } from 'lucide-react'

interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  checked?: boolean
  indeterminate?: boolean
  onCheckedChange?: (checked: boolean) => void
  onChange?: React.ChangeEventHandler<HTMLInputElement>
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

export const Checkbox: React.FC<CheckboxProps> = ({
  checked = false,
  indeterminate = false,
  onCheckedChange,
  onChange,
  disabled = false,
  className = '',
  'aria-label': ariaLabel,
  ...props
}) => {
  const handleClick = () => {
    if (!disabled && onCheckedChange) {
      onCheckedChange(!checked)
    }
    if (!disabled && onChange) {
      onChange({ target: { checked: !checked } } as React.ChangeEvent<HTMLInputElement>)
    }
  }

  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={indeterminate ? 'mixed' : checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={handleClick}
      id={props.id}
      className={`
        inline-flex items-center justify-center w-4 h-4 border border-gray-300 rounded
        ${checked || indeterminate ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-500'}
        ${className}
      `}
    >
      {indeterminate ? (
        <Minus className="w-3 h-3" />
      ) : checked ? (
        <Check className="w-3 h-3" />
      ) : null}
    </button>
  )
}
