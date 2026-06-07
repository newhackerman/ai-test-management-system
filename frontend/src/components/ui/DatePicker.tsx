import React from 'react'
import { Input } from './Input'

interface DatePickerProps {
  selected?: Date
  onSelect?: (date: Date | undefined) => void
  placeholder?: string
  className?: string
}

export const DatePicker: React.FC<DatePickerProps> = ({
  selected,
  onSelect,
  placeholder = "选择日期",
  className
}) => {
  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    if (value) {
      onSelect?.(new Date(value))
    } else {
      onSelect?.(undefined)
    }
  }

  const formatDate = (date: Date): string => {
    return date.toISOString().split('T')[0]
  }

  return (
    <Input
      type="date"
      value={selected ? formatDate(selected) : ''}
      onChange={handleDateChange}
      placeholder={placeholder}
      className={className}
    />
  )
}

export default DatePicker