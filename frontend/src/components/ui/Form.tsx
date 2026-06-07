import * as React from 'react'
import {
  Controller,
  FormProvider,
  useFormContext,
  useFormState,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
  type UseFormReturn,
} from 'react-hook-form'
import { cn } from '@/lib/utils'
import { Label } from './Label'

interface LegacyFormContextType {
  errors: Record<string, string[]>
  touched: Record<string, boolean>
  setFieldTouched: (field: string, touched?: boolean) => void
}

const LegacyFormContext = React.createContext<LegacyFormContextType | undefined>(undefined)
const FormFieldContext = React.createContext<{ name: string } | undefined>(undefined)

export interface FormProps
  extends Omit<React.FormHTMLAttributes<HTMLFormElement>, 'onSubmit'>,
    Partial<UseFormReturn<any>> {
  errors?: Record<string, string[]>
  touched?: Record<string, boolean>
  onFieldTouched?: (field: string, touched?: boolean) => void
  onSubmit?: React.FormEventHandler<HTMLFormElement>
}

export function Form({
  className,
  errors = {},
  touched = {},
  onFieldTouched,
  children,
  ...props
}: FormProps) {
  if (props.control && props.handleSubmit) {
    return <FormProvider {...(props as UseFormReturn<any>)}>{children}</FormProvider>
  }

  return (
    <LegacyFormContext.Provider value={{ errors, touched, setFieldTouched: onFieldTouched || (() => {}) }}>
      <form className={cn('space-y-6', className)} {...props}>
        {children}
      </form>
    </LegacyFormContext.Provider>
  )
}

export interface FormItemProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string
  label?: string
  required?: boolean
  description?: string
  error?: string
}

export function FormItem({
  className,
  name,
  label,
  required,
  description,
  error: propError,
  children,
  ...props
}: FormItemProps) {
  const legacyContext = React.useContext(LegacyFormContext)
  const fieldContext = React.useContext(FormFieldContext)
  const fieldName = name || fieldContext?.name
  const fieldError = fieldName && legacyContext?.errors[fieldName]?.[0]
  const isFieldTouched = fieldName && legacyContext?.touched[fieldName]
  const showLegacyError = isFieldTouched && (propError || fieldError)

  return (
    <div className={cn('space-y-2', className)} {...props}>
      {label && (
        <Label className={cn(required && "after:content-['*'] after:text-destructive after:ml-1")}>
          {label}
        </Label>
      )}
      {children}
      {description && !showLegacyError && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      {showLegacyError && (
        <p className="text-sm text-destructive">{propError || fieldError}</p>
      )}
    </div>
  )
}

export interface FormControlProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string
}

export function FormControl({ className, name, children, ...props }: FormControlProps) {
  const legacyContext = React.useContext(LegacyFormContext)

  const enhancedChildren = React.Children.map(children, (child) => {
    if (legacyContext && React.isValidElement(child) && name) {
      return React.cloneElement(child, {
        ...child.props,
        onBlur: (event: React.FocusEvent) => {
          child.props.onBlur?.(event)
          legacyContext.setFieldTouched(name, true)
        },
      })
    }
    return child
  })

  return (
    <div className={className} {...props}>
      {enhancedChildren}
    </div>
  )
}

export interface FormMessageProps extends React.HTMLAttributes<HTMLParagraphElement> {
  type?: 'error' | 'warning' | 'info' | 'success'
}

const getPathValue = (source: any, path?: string) => {
  if (!path) return undefined
  return path.split('.').reduce((value, key) => value?.[key], source)
}

export function FormMessage({ className, type = 'error', children, ...props }: FormMessageProps) {
  const fieldContext = React.useContext(FormFieldContext)
  let hookFormError: string | undefined

  try {
    const form = useFormContext()
    const { errors } = useFormState({ control: form.control, name: fieldContext?.name })
    hookFormError = getPathValue(errors, fieldContext?.name)?.message
  } catch {
    hookFormError = undefined
  }

  const body = children || hookFormError
  if (!body) return null

  const typeClasses = {
    error: 'text-destructive',
    warning: 'text-warning',
    info: 'text-info',
    success: 'text-success',
  }

  return (
    <p className={cn('text-sm', typeClasses[type], className)} {...props}>
      {body}
    </p>
  )
}

export interface FormDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export function FormDescription({ className, ...props }: FormDescriptionProps) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />
}

export interface FormLabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean
}

export function FormLabel({ className, required, children, ...props }: FormLabelProps) {
  return (
    <Label
      className={cn(
        required && "after:content-['*'] after:text-destructive after:ml-1",
        className
      )}
      {...props}
    >
      {children}
    </Label>
  )
}

type HookFormFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> = ControllerProps<TFieldValues, TName>

type LegacyFormFieldProps = {
  name: string
  label?: string
  required?: boolean
  description?: string
  error?: string
  children: React.ReactNode
  className?: string
}

export function FormField(props: LegacyFormFieldProps): JSX.Element
export function FormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>(props: HookFormFieldProps<TFieldValues, TName>): JSX.Element
export function FormField(props: any) {
  if (props.render && props.control) {
    return (
      <FormFieldContext.Provider value={{ name: props.name }}>
        <Controller {...props} />
      </FormFieldContext.Provider>
    )
  }

  const { name, label, required, description, error, children, className } = props
  return (
    <FormItem
      name={name}
      label={label}
      required={required}
      description={description}
      error={error}
      className={className}
    >
      <FormControl name={name}>{children}</FormControl>
    </FormItem>
  )
}
