// @ts-nocheck
import React from 'react'
import { useAuthStore } from '@/stores/auth'
import { Badge } from '@/components/ui/Badge'
import { Loading } from '@/components/ui/Loading'
import { 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Clock,
  Shield,
  User
} from 'lucide-react'

interface AuthStatusProps {
  showDetails?: boolean
  className?: string
}

export const AuthStatus: React.FC<AuthStatusProps> = ({ 
  showDetails = false,
  className = ''
}) => {
  const { 
    isAuthenticated, 
    isLoading, 
    user, 
    error 
  } = useAuthStore()

  const getStatusIcon = () => {
    if (isLoading) {
      return <Loading className="w-4 h-4" />
    }
    
    if (error) {
      return <XCircle className="w-4 h-4 text-red-500 dark:text-red-400" />
    }
    
    if (isAuthenticated && user) {
      return <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400" />
    }
    
    if (isAuthenticated && !user) {
      return <AlertCircle className="w-4 h-4 text-yellow-500" />
    }
    
    return <XCircle className="w-4 h-4 text-gray-400 dark:text-gray-500" />
  }

  const getStatusText = () => {
    if (isLoading) {
      return '验证中...'
    }
    
    if (error) {
      return '认证失败'
    }
    
    if (isAuthenticated && user) {
      return '已登录'
    }
    
    if (isAuthenticated && !user) {
      return '正在获取用户信息...'
    }
    
    return '未登录'
  }

  const getStatusVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    if (isLoading) {
      return 'outline'
    }
    
    if (error) {
      return 'destructive'
    }
    
    if (isAuthenticated && user) {
      return 'default'
    }
    
    return 'secondary'
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Badge variant={getStatusVariant()} className="flex items-center space-x-1">
        {getStatusIcon()}
        <span>{getStatusText()}</span>
      </Badge>
      
      {showDetails && user && (
        <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-1">
            <User className="w-3 h-3" />
            <span>{user.username}</span>
          </div>
          
          {user.role && (
            <div className="flex items-center space-x-1">
              <Shield className="w-3 h-3" />
              <span>{user.role}</span>
            </div>
          )}
          
          {user.lastLoginAt && (
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>
                {new Date(user.lastLoginAt).toLocaleString('zh-CN', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
            </div>
          )}
        </div>
      )}
      
      {showDetails && error && (
        <div className="text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}
    </div>
  )
}

export default AuthStatus
