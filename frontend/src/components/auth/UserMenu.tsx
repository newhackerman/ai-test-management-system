// @ts-nocheck
import React from 'react'
import { useAuthStore, usePermissions } from '@/stores/auth'
import { 
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem
} from '@/components/ui/DropdownMenu'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { 
  User, 
  Settings, 
  LogOut, 
  Shield, 
  ChevronDown,
  Crown,
  UserCheck
} from 'lucide-react'

export const UserMenu: React.FC = () => {
  const { user, logout, isLoading } = useAuthStore()
  const { isAdmin, hasPermission } = usePermissions()

  if (!user) {
    return null
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('鐧诲嚭澶辫触:', error)
    }
  }

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'admin':
        return 'destructive'
      case 'user':
        return 'default'
      case 'viewer':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin':
        return <Crown className="w-3 h-3" />
      case 'user':
        return <UserCheck className="w-3 h-3" />
      default:
        return <User className="w-3 h-3" />
    }
  }

  const getRoleText = (role: string) => {
    switch (role) {
      case 'admin':
        return '管理员'
      case 'user':
        return '用户'
      case 'viewer':
        return '访客'
      default:
        return role
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          className="relative h-10 w-auto px-2 hover:bg-gray-100 dark:hover:bg-gray-800 dark:bg-gray-800"
          disabled={isLoading}
        >
          <div className="flex items-center space-x-2">
            <Avatar className="h-8 w-8">
              <AvatarImage src={user.avatar} alt={user.username} />
              <AvatarFallback>
                {user.username.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="hidden md:flex flex-col items-start">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {user.realName || user.username}
              </span>
              <div className="flex items-center space-x-1">
                <Badge 
                  variant={getRoleBadgeVariant(user.role)} 
                  className="text-xs px-1 py-0 h-4"
                >
                  <span className="flex items-center space-x-1">
                    {getRoleIcon(user.role)}
                    <span>{getRoleText(user.role)}</span>
                  </span>
                </Badge>
              </div>
            </div>
            <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </div>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-64" align="end" forceMount>
        {/* 鐢ㄦ埛淇℃伅 */}
        <div className="flex items-center space-x-3 p-3 border-b">
          <Avatar className="h-10 w-10">
            <AvatarImage src={user.avatar} alt={user.username} />
            <AvatarFallback>
              {user.username.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {user.realName || user.username}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {user.email}
            </p>
            <div className="flex items-center space-x-1 mt-1">
              <Badge 
                variant={getRoleBadgeVariant(user.role)} 
                className="text-xs px-1 py-0 h-4"
              >
                <span className="flex items-center space-x-1">
                  {getRoleIcon(user.role)}
                  <span>{getRoleText(user.role)}</span>
                </span>
              </Badge>
              {user.isActive && (
                <Badge variant="outline" className="text-xs px-1 py-0 h-4">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>
                  鍦ㄧ嚎
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* 鑿滃崟椤?*/}
        <div className="py-1">
          <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2">
            <User className="h-4 w-4" />
            <span>涓汉璧勬枡</span>
          </DropdownMenuItem>

          <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2">
            <Settings className="h-4 w-4" />
            <span>璐︽埛璁剧疆</span>
          </DropdownMenuItem>

          {isAdmin && (
            <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2">
              <Shield className="h-4 w-4" />
              <span>绯荤粺绠＄悊</span>
            </DropdownMenuItem>
          )}
        </div>

        {/* 鏉冮檺淇℃伅 */}
        {user.permissions && user.permissions.length > 0 && (
          <div className="border-t py-2">
            <div className="px-3 py-1">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                鏉冮檺
              </p>
              <div className="flex flex-wrap gap-1">
                {user.permissions.slice(0, 3).map((permission) => (
                  <Badge 
                    key={permission} 
                    variant="outline" 
                    className="text-xs px-1 py-0 h-4"
                  >
                    {permission}
                  </Badge>
                ))}
                {user.permissions.length > 3 && (
                  <Badge variant="outline" className="text-xs px-1 py-0 h-4">
                    +{user.permissions.length - 3}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 鐧诲嚭 */}
        <div className="border-t py-1">
          <DropdownMenuItem 
            className="flex items-center space-x-2 px-3 py-2 text-red-600 dark:text-red-400 focus:text-red-600 dark:focus:text-red-400"
            onClick={handleLogout}
            disabled={isLoading}
          >
            <LogOut className="h-4 w-4" />
            <span>退出登录</span>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default UserMenu
