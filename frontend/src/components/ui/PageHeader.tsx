import React from 'react'
import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem {
  label: string
  href?: string
}

export interface PageHeaderProps {
  /** 页面标题 */
  title: string
  /** 页面描述 */
  description?: string
  /** 面包屑导航 */
  breadcrumbs?: BreadcrumbItem[]
  /** 右侧操作区 */
  actions?: React.ReactNode
  /** 额外的底部区域（如 tabs、统计卡片） */
  extra?: React.ReactNode
  className?: string
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  breadcrumbs,
  actions,
  extra,
  className = '',
}) => {
  return (
    <div className={`mb-6 ${className}`}>
      {/* 面包屑 */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-2 flex items-center gap-1 text-sm text-muted-foreground" aria-label="面包屑">
          {breadcrumbs.map((item, index) => (
            <React.Fragment key={index}>
              {index > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
              {item.href ? (
                <Link
                  to={item.href}
                  className="truncate hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span className="truncate text-foreground font-medium">
                  {item.label}
                </span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}

      {/* 标题行 */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl truncate">
            {title}
          </h1>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-2 mt-2 sm:mt-0">
            {actions}
          </div>
        )}
      </div>

      {/* 额外区域 */}
      {extra && <div className="mt-4">{extra}</div>}
    </div>
  )
}

export default PageHeader
