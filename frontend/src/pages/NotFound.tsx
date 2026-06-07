import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Home, ArrowLeft } from 'lucide-react'

const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-gray-300 dark:text-gray-700">
            404
          </h1>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mt-4">
            页面未找到
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            抱歉，您访问的页面不存在或已被移除。
          </p>
        </div>

        <div className="space-y-4">
          <Button asChild className="w-full">
            <Link to="/" className="flex items-center justify-center space-x-2">
              <Home className="w-4 h-4" />
              <span>返回首页</span>
            </Link>
          </Button>
          
          <Button variant="outline" onClick={() => window.history.back()} className="w-full">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回上一页
          </Button>
        </div>
      </div>
    </div>
  )
}

export default NotFound