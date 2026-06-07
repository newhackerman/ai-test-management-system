import React, { useEffect, useState } from 'react'
import { LoginPage } from './LoginPage'
import { Loading } from '@/components/ui/Loading'

interface SimpleAuthGuardProps {
  children: React.ReactNode
}

export const SimpleAuthGuard: React.FC<SimpleAuthGuardProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // 简单检查localStorage中是否有token
    const checkAuth = () => {
      try {
        const token = localStorage.getItem('auth-access-token')
        const tokenExpiry = localStorage.getItem('auth-token-expiry')
        
        if (!token || !tokenExpiry) {
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }
        
        // 检查token是否过期
        const expiryTime = parseInt(tokenExpiry)
        const isExpired = Date.now() >= expiryTime
        
        setIsAuthenticated(!isExpired)
        setIsLoading(false)
      } catch (error) {
        console.error('认证检查失败:', error)
        setIsAuthenticated(false)
        setIsLoading(false)
      }
    }

    // 延迟一点检查，避免初始化冲突
    const timer = setTimeout(checkAuth, 100)
    
    return () => clearTimeout(timer)
  }, [])

  // 监听登录成功事件
  useEffect(() => {
    const handleLogin = () => {
      setIsAuthenticated(true)
    }
    
    const handleLogout = () => {
      setIsAuthenticated(false)
    }
    
    window.addEventListener('auth:login', handleLogin)
    window.addEventListener('auth:logout', handleLogout)
    
    return () => {
      window.removeEventListener('auth:login', handleLogin)
      window.removeEventListener('auth:logout', handleLogout)
    }
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center space-y-4">
          <Loading className="w-8 h-8 mx-auto" />
          <p className="text-gray-600 dark:text-gray-400">正在检查登录状态...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return <>{children}</>
}

export default SimpleAuthGuard