import React from 'react'
import { LucideIcon, Inbox } from 'lucide-react'
import { Button } from '@/components/ui/Button'

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 图标组件，默认 Inbox */
  icon?: LucideIcon
  /** 图标颜色类名，默认 text-muted-foreground/40 */
  iconClassName?: string
  /** 图标大小，默认 h-12 w-12 */
  iconSize?: string
  /** 主标题 */
  title?: string
  /** 副标题/描述 */
  description?: string
  /** CTA 按钮文字 */
  actionLabel?: string
  /** CTA 按钮点击回调 */
  onAction?: () => void
  /** CTA 按钮自定义路径（作为 Link 使用） */
  actionHref?: string
  /** 变体：default | compact | card */
  variant?: 'default' | 'compact' | 'card'
  /** 次要按钮文字 */
  secondaryActionLabel?: string
  /** 次要按钮回调 */
  onSecondaryAction?: () => void
  secondaryActionHref?: string
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  iconClassName = 'text-muted-foreground/40',
  iconSize = 'h-12 w-12',
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  variant = 'default',
  secondaryActionLabel,
  onSecondaryAction,
  secondaryActionHref,
  className = '',
  children,
  ...rest
}) => {
  const actionButton = (label: string, handler?: () => void, href?: string) => {
    if (href) {
      return (
        <Button asChild>
          <a href={href}>{label}</a>
        </Button>
      )
    }
    return <Button onClick={handler}>{label}</Button>
  }

  if (variant === 'compact') {
    return (
      <div className={`flex flex-col items-center justify-center py-6 text-center ${className}`} {...rest}>
        {Icon && <Icon className={`${iconSize} ${iconClassName} mb-2`} strokeWidth={1.5} />}
        {title && <p className="text-sm font-medium text-muted-foreground">{title}</p>}
        {description && <p className="mt-1 text-xs text-muted-foreground/70">{description}</p>}
        {actionLabel && <div className="mt-3">{actionButton(actionLabel, onAction, actionHref)}</div>}
        {children}
      </div>
    )
  }

  if (variant === 'card') {
    return (
      <div className={`rounded-lg border-2 border-dashed border-muted-foreground/20 p-8 flex flex-col items-center justify-center text-center ${className}`} {...rest}>
        {Icon && <Icon className={`${iconSize} ${iconClassName} mb-4`} strokeWidth={1} />}
        {title && <h3 className="text-base font-semibold text-foreground">{title}</h3>}
        {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
        {(actionLabel || secondaryActionLabel) && (
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            {actionLabel && actionButton(actionLabel, onAction, actionHref)}
            {secondaryActionLabel && <Button variant="outline" onClick={onSecondaryAction}>{secondaryActionLabel}</Button>}
          </div>
        )}
        {children}
      </div>
    )
  }

  // default variant
  return (
    <div className={`flex flex-col items-center justify-center py-10 sm:py-16 text-center ${className}`} {...rest}>
      {Icon && <Icon className={`${iconSize} ${iconClassName} mb-4`} strokeWidth={1.5} />}
      {title && <h3 className="text-lg font-semibold text-foreground">{title}</h3>}
      {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
      {(actionLabel || secondaryActionLabel) && (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {actionLabel && actionButton(actionLabel, onAction, actionHref)}
          {secondaryActionLabel && <Button variant="outline" onClick={onSecondaryAction}>{secondaryActionLabel}</Button>}
        </div>
      )}
      {children}
    </div>
  )
}

export default EmptyState
