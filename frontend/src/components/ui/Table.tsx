import * as React from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, MoreHorizontal, Download } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from './Button'
import { Checkbox } from './Checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './DropdownMenu'

// 基础表格组件
export interface TableProps extends React.HTMLAttributes<HTMLTableElement> {}

const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table
        ref={ref}
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
)
Table.displayName = 'Table'

export interface TableHeaderProps extends React.HTMLAttributes<HTMLTableSectionElement> {}

const TableHeader = React.forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ className, ...props }, ref) => (
    <thead ref={ref} className={cn('[&_tr]:border-b', className)} {...props} />
  )
)
TableHeader.displayName = 'TableHeader'

export interface TableBodyProps extends React.HTMLAttributes<HTMLTableSectionElement> {}

const TableBody = React.forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className, ...props }, ref) => (
    <tbody
      ref={ref}
      className={cn('[&_tr:last-child]:border-0', className)}
      {...props}
    />
  )
)
TableBody.displayName = 'TableBody'

export interface TableFooterProps extends React.HTMLAttributes<HTMLTableSectionElement> {}

const TableFooter = React.forwardRef<HTMLTableSectionElement, TableFooterProps>(
  ({ className, ...props }, ref) => (
    <tfoot
      ref={ref}
      className={cn('bg-primary font-medium text-primary-foreground', className)}
      {...props}
    />
  )
)
TableFooter.displayName = 'TableFooter'

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {}

const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted',
        className
      )}
      {...props}
    />
  )
)
TableRow.displayName = 'TableRow'

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {}

const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        'h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0',
        className
      )}
      {...props}
    />
  )
)
TableHead.displayName = 'TableHead'

export interface TableCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {}

const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, ...props }, ref) => (
    <td
      ref={ref}
      className={cn('p-4 align-middle [&:has([role=checkbox])]:pr-0', className)}
      {...props}
    />
  )
)
TableCell.displayName = 'TableCell'

export interface TableCaptionProps extends React.HTMLAttributes<HTMLTableCaptionElement> {}

const TableCaption = React.forwardRef<HTMLTableCaptionElement, TableCaptionProps>(
  ({ className, ...props }, ref) => (
    <caption
      ref={ref}
      className={cn('mt-4 text-sm text-muted-foreground', className)}
      {...props}
    />
  )
)
TableCaption.displayName = 'TableCaption'

// 高级数据表格组件
export interface Column<T = any> {
  key: string
  title: string
  dataIndex?: string
  render?: (value: any, record: T, index: number) => React.ReactNode
  sortable?: boolean
  filterable?: boolean
  width?: number | string
  align?: 'left' | 'center' | 'right'
  fixed?: 'left' | 'right'
}

export interface DataTableProps<T = any> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  pagination?: {
    current: number
    pageSize: number
    total: number
    onChange: (page: number, pageSize: number) => void
  }
  rowSelection?: {
    selectedRowKeys: React.Key[]
    onChange: (selectedRowKeys: React.Key[], selectedRows: T[]) => void
    getCheckboxProps?: (record: T) => { disabled?: boolean }
  }
  onSort?: (key: string, direction: 'asc' | 'desc' | null) => void
  onFilter?: (key: string, value: any) => void
  rowKey?: string | ((record: T) => React.Key)
  className?: string
  size?: 'small' | 'middle' | 'large'
  bordered?: boolean
  showHeader?: boolean
  scroll?: { x?: number | string; y?: number | string }
}

export function DataTable<T = any>({
  columns,
  data,
  loading = false,
  pagination,
  rowSelection,
  onSort,
  onFilter,
  rowKey = 'id',
  className,
  size = 'middle',
  bordered = false,
  showHeader = true,
  scroll
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = React.useState<{
    key: string
    direction: 'asc' | 'desc' | null
  }>({ key: '', direction: null })

  const getRowKey = (record: T, index: number): React.Key => {
    if (typeof rowKey === 'function') {
      return rowKey(record)
    }
    return (record as any)[rowKey] || index
  }

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' | null = 'asc'
    
    if (sortConfig.key === key) {
      if (sortConfig.direction === 'asc') {
        direction = 'desc'
      } else if (sortConfig.direction === 'desc') {
        direction = null
      }
    }

    setSortConfig({ key, direction })
    onSort?.(key, direction)
  }

  const getSortIcon = (key: string) => {
    if (sortConfig.key !== key) {
      return <ChevronsUpDown className="ml-2 h-4 w-4" />
    }
    
    if (sortConfig.direction === 'asc') {
      return <ChevronUp className="ml-2 h-4 w-4" />
    } else if (sortConfig.direction === 'desc') {
      return <ChevronDown className="ml-2 h-4 w-4" />
    }
    
    return <ChevronsUpDown className="ml-2 h-4 w-4" />
  }

  const isAllSelected = rowSelection && data.length > 0 && 
    data.every(record => rowSelection.selectedRowKeys.includes(getRowKey(record, 0)))

  const isIndeterminate = rowSelection && rowSelection.selectedRowKeys.length > 0 && 
    !isAllSelected

  const handleSelectAll = (checked: boolean) => {
    if (!rowSelection) return
    
    if (checked) {
      const allKeys = data.map((record, index) => getRowKey(record, index))
      rowSelection.onChange(allKeys, data)
    } else {
      rowSelection.onChange([], [])
    }
  }

  const handleSelectRow = (record: T, index: number, checked: boolean) => {
    if (!rowSelection) return
    
    const key = getRowKey(record, index)
    let newSelectedKeys = [...rowSelection.selectedRowKeys]
    let newSelectedRows: T[] = []

    if (checked) {
      newSelectedKeys.push(key)
    } else {
      newSelectedKeys = newSelectedKeys.filter(k => k !== key)
    }

    newSelectedRows = data.filter((record, index) => 
      newSelectedKeys.includes(getRowKey(record, index))
    )

    rowSelection.onChange(newSelectedKeys, newSelectedRows)
  }

  const sizeClasses = {
    small: 'text-xs',
    middle: 'text-sm',
    large: 'text-base'
  }

  return (
    <div className={cn('w-full', className)}>
      <div className={cn(
        'rounded-md border',
        bordered && 'border-border',
        !bordered && 'border-transparent'
      )}>
        <Table className={sizeClasses[size]}>
          {showHeader && (
            <TableHeader>
              <TableRow>
                {rowSelection && (
                  <TableHead className="w-12">
                    <Checkbox
                      checked={isAllSelected}
                      // indeterminate={isIndeterminate}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                    />
                  </TableHead>
                )}
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className={cn(
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      column.sortable && 'cursor-pointer select-none hover:bg-muted/50'
                    )}
                    style={{ width: column.width }}
                    onClick={() => column.sortable && handleSort(column.key)}
                  >
                    <div className="flex items-center">
                      {column.title}
                      {column.sortable && getSortIcon(column.key)}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
          )}
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell 
                  colSpan={columns.length + (rowSelection ? 1 : 0)}
                  className="h-24 text-center"
                >
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                    <span className="ml-2">加载中...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell 
                  colSpan={columns.length + (rowSelection ? 1 : 0)}
                  className="h-24 text-center text-muted-foreground"
                >
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data.map((record, index) => {
                const key = getRowKey(record, index)
                const isSelected = rowSelection?.selectedRowKeys.includes(key)
                
                return (
                  <TableRow
                    key={key}
                    data-state={isSelected ? 'selected' : undefined}
                  >
                    {rowSelection && (
                      <TableCell>
                        <Checkbox
                          checked={isSelected}
                          disabled={rowSelection.getCheckboxProps?.(record)?.disabled}
                          onChange={(e) => handleSelectRow(record, index, e.target.checked)}
                        />
                      </TableCell>
                    )}
                    {columns.map((column) => {
                      const value = column.dataIndex ? (record as any)[column.dataIndex] : record
                      const content = column.render 
                        ? column.render(value, record, index)
                        : value

                      return (
                        <TableCell
                          key={column.key}
                          className={cn(
                            column.align === 'center' && 'text-center',
                            column.align === 'right' && 'text-right'
                          )}
                        >
                          {content}
                        </TableCell>
                      )
                    })}
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {pagination && (
        <div className="flex items-center justify-between px-2 py-4">
          <div className="text-sm text-muted-foreground">
            共 {pagination.total} 条记录
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onChange(pagination.current - 1, pagination.pageSize)}
              disabled={pagination.current <= 1}
            >
              上一页
            </Button>
            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.ceil(pagination.total / pagination.pageSize) }, (_, i) => i + 1)
                .filter(page => {
                  const current = pagination.current
                  return page === 1 || page === Math.ceil(pagination.total / pagination.pageSize) ||
                    (page >= current - 2 && page <= current + 2)
                })
                .map((page, index, array) => {
                  const showEllipsis = index > 0 && page - array[index - 1] > 1
                  return (
                    <React.Fragment key={page}>
                      {showEllipsis && <span className="px-2">...</span>}
                      <Button
                        variant={page === pagination.current ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => pagination.onChange(page, pagination.pageSize)}
                      >
                        {page}
                      </Button>
                    </React.Fragment>
                  )
                })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onChange(pagination.current + 1, pagination.pageSize)}
              disabled={pagination.current >= Math.ceil(pagination.total / pagination.pageSize)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}