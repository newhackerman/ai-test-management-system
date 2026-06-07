import { useState } from 'react'
import { Construction, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'

interface ComingSoonProps {
  title: string
  description?: string
}

export function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-6">
        <div className="space-y-2">
          <Construction className="w-16 h-16 text-primary mx-auto" />
          <h1 className="text-3xl font-bold text-foreground">{title}</h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            {description || '此功能正在开发中，敬请期待！我们正在努力为您提供更好的体验。'}
          </p>
        </div>

        <div className="flex items-center justify-center space-x-4">
          <Button asChild>
            <Link to="/">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回首页
            </Link>
          </Button>
        </div>

        <div className="pt-8 border-t border-border">
          <p className="text-sm text-muted-foreground">
            预计完成时间：2024年3月
          </p>
        </div>
      </div>
    </div>
  )
}

export default ComingSoon