import { Construction, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'

interface ComingSoonProps {
  title: string
}

export function ComingSoon({ title }: ComingSoonProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-6">
        <div className="space-y-2">
          <Construction className="w-16 h-16 text-primary mx-auto" />
          <h1 className="text-3xl font-bold text-foreground">{title}</h1>
        </div>

        <div className="flex items-center justify-center space-x-4">
          <Button asChild>
            <Link to="/">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回首页
            </Link>
          </Button>
        </div>

      </div>
    </div>
  )
}

export default ComingSoon
