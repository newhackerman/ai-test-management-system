import { Button } from './Button'

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const safePage = Math.min(Math.max(currentPage, 1), Math.max(totalPages, 1))
  const pages = Array.from({ length: totalPages }, (_, index) => index + 1)

  return (
    <div className="flex items-center justify-center gap-2">
      <Button
        variant="outline"
        size="sm"
        disabled={safePage <= 1}
        onClick={() => onPageChange(safePage - 1)}
      >
        Previous
      </Button>
      {pages.map((page) => (
        <Button
          key={page}
          variant={page === safePage ? 'default' : 'outline'}
          size="sm"
          onClick={() => onPageChange(page)}
        >
          {page}
        </Button>
      ))}
      <Button
        variant="outline"
        size="sm"
        disabled={safePage >= totalPages}
        onClick={() => onPageChange(safePage + 1)}
      >
        Next
      </Button>
    </div>
  )
}
